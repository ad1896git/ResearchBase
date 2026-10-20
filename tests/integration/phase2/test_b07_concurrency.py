"""Observed backend waits, first-statement inventory and MVCC exact reads."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Event, get_ident
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event, text

from researchbase.application.revision_action import RecordConcernReReviewCommand
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.approval_repository import B09_SHARE_SQL
from tests.integration.phase2.test_b07_revision_decisions import decision_command
from tests.integration.phase2.test_pr2_14_internal_review import _wait_for_pg_blocker
from tests.integration.phase2.test_revision_action import (
    conclusion_env,
    decision_env,
    phase2_database_url,
    revision_env,
)

pytestmark = pytest.mark.integration
pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)
_FIXTURES = (conclusion_env, decision_env, phase2_database_url, revision_env)


@pytest.mark.parametrize("kind", ["decision", "action", "link"])
@pytest.mark.parametrize("owner", ["release", "review", "novelty"])
@pytest.mark.parametrize("order", ["b07_first", "owner_first"])
def test_real_governance_writers_overlap_without_scientific_lock_inversion(
    revision_env, kind, owner, order
):
    from researchbase.application.decision import RecordDecisionCommand
    from researchbase.application.novelty import NoveltyService, RecordPriorArtRelationCommand
    from researchbase.domain.novelty import PriorArtKind

    write, _ = prepared(revision_env, kind)
    _, _, env, _, revised = revision_env
    base = env[-1]

    def review(target, identity):
        return env[1].create(
            env[2],
            base[5],
            "SCIENTIFIC_CONCLUSION_VERSION",
            target,
            "SCIENTIFIC",
            "ACCEPT",
            "TEST ONLY concurrent independent review",
            (),
            identity,
        )

    owner_id = uuid4()
    if owner == "release":
        review(revised.version_id, uuid4())
        command = RecordDecisionCommand(
            owner_id, base[5], revised.version_id, "Proceed?", "TEST ONLY independent basis"
        )

        def release_write():
            return env[0].record_decision(env[2], command)

        owning_write: Any = release_write
        owner_pause = "FROM scientific_conclusion_versions v"
    elif owner == "review":
        # A late old-target review must be included only when it commits first.
        def review_write():
            return review(env[3].version_id, owner_id)

        owning_write = review_write
        owner_pause = "INSERT INTO internal_review_records"
    else:
        evidence = UUID(base[2].create(base[3], base[5], base[7], "improved recall", uuid4())["id"])
        base[2].review(
            base[4], base[5], evidence, "VERIFIED", "TEST ONLY inspected passage", uuid4()
        )
        novelty = NoveltyService(base[1], base[-1], base[2])
        prior_art = RecordPriorArtRelationCommand(
            owner_id,
            base[5],
            base[6],
            base[7],
            PriorArtKind.RELATED,
            "TEST ONLY exact prior work",
            (evidence,),
        )

        def novelty_write():
            return novelty.record_prior_art_relation(base[3], prior_art)

        owning_write = novelty_write
        owner_pause = "SELECT id FROM claim_versions WHERE id="

    entered, release = Event(), Event()
    holder = {}
    pids = {}

    def pause(conn, cursor, statement, parameters, context, many):
        if get_ident() != holder.get("thread") or entered.is_set():
            return
        match = (
            statement.startswith("LOCK TABLE ")
            if order == "b07_first"
            else owner_pause in statement and (owner == "review" or "FOR UPDATE" in statement)
        )
        if match:
            # Set the event only after collecting evidence; avoid recursive capture.
            holder["thread"] = None
            pids["first"] = conn.execute(text("SELECT pg_backend_pid()")).scalar_one()
            entered.set()
            assert release.wait(10)

    def run_first():
        holder["thread"] = get_ident()
        return write() if order == "b07_first" else owning_write()

    def capture_second(conn, cursor, statement, parameters, context, many):
        if get_ident() == pids.get("second_thread") and "second" not in pids:
            pids["second"] = conn.connection.driver_connection.info.backend_pid

    def run_second():
        pids["second_thread"] = get_ident()
        return owning_write() if order == "b07_first" else write()

    event.listen(base[8], "after_cursor_execute", pause)
    event.listen(base[8], "before_cursor_execute", capture_second)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(run_first)
            assert entered.wait(10)
            second = pool.submit(run_second)
            if owner == "review" or (
                owner == "release" and kind == "action" and order == "owner_first"
            ):
                witness = _wait_for_pg_blocker(
                    base[8], pids["first"], "relation" if owner == "review" else "transactionid"
                )
                assert witness["pid"] != pids["first"]
                assert not second.done()
                if owner == "review" and order == "b07_first":
                    assert witness["query"] == (
                        "LOCK TABLE internal_review_records IN ROW EXCLUSIVE MODE"
                    )
                    with base[8].connect() as observer:
                        assert (
                            observer.execute(
                                text(
                                    "SELECT count(*) FROM pg_locks WHERE pid=:pid "
                                    "AND granted AND mode='RowShareLock'"
                                ),
                                {"pid": witness["pid"]},
                            ).scalar_one()
                            == 0
                        )
                release.set()
                assert second.result(timeout=15)
            else:
                # Target-first owners must finish even while B07 holds SHARE(B),
                # and B07 must finish while an owner holds its scientific row.
                assert second.result(timeout=10)
                assert not first.done()
                with base[8].connect() as observer:
                    assert (
                        observer.execute(
                            text("SELECT state FROM pg_stat_activity WHERE pid=:pid"),
                            {"pid": pids["first"]},
                        ).scalar_one()
                        == "idle in transaction"
                    )
                release.set()
            result = first.result(timeout=15)
            assert pids["first"] != pids["second"]
        if owner == "review" and kind == "decision":
            saved = cast(Any, result if order == "b07_first" else second.result())
            review_id = second.result().id if order == "b07_first" else result.id
            assert (review_id in {ref.id for ref in saved.basis}) == (order == "owner_first")
    finally:
        release.set()
        event.remove(base[8], "after_cursor_execute", pause)
        event.remove(base[8], "before_cursor_execute", capture_second)


@pytest.mark.parametrize("kind", ["decision", "concern", "action", "link"])
def test_sql_guards_wait_for_reviews_before_locking_issue_or_action(revision_env, kind):
    from sqlalchemy.exc import DBAPIError

    from tests.integration.phase2.test_b06_revision_action import _normal_sql_clone
    from tests.integration.phase2.test_b07_schema import normal_role

    service, action, env, old_review, revised = revision_env
    base = env[-1]
    decision = env[0].record_revision_decision(
        env[2], decision_command(env, action.review_issue_id)
    )
    saved = service.record_revision_action(base[3], action)
    review = env[1].create(
        env[2],
        base[5],
        "SCIENTIFIC_CONCLUSION_VERSION",
        revised.version_id,
        "SCIENTIFIC",
        "ACCEPT",
        "TEST ONLY independent",
        (),
        uuid4(),
    )
    service.record_concern_re_review(
        env[2], RecordConcernReReviewCommand(base[5], saved.id, review.id)
    )

    def write():
        if kind == "action":
            return _normal_sql_clone(base, saved.id)
        try:
            with normal_role(base[8]) as conn:
                if kind == "decision":
                    conn.execute(
                        text("SELECT b07_validate_decision(:id,true)"), {"id": decision.id}
                    )
                elif kind == "concern":
                    identity = uuid4()
                    conn.execute(
                        text(
                            "INSERT INTO decision_records SELECT :id,project_id,decision_type,"
                            "question,decision,rationale,decided_by,decided_at,supersedes_decision_id,"
                            "basis_set_hash,content_hash,hash_scheme FROM decision_records "
                            "WHERE id=:old"
                        ),
                        {"id": identity, "old": decision.id},
                    )
                    conn.execute(
                        text("INSERT INTO decision_revision_concerns VALUES (:id,:issue)"),
                        {"id": identity, "issue": action.review_issue_id},
                    )
                else:
                    conn.execute(
                        text(
                            "INSERT INTO revision_action_re_reviews SELECT * FROM "
                            "revision_action_re_reviews WHERE revision_action_id=:id"
                        ),
                        {"id": saved.id},
                    )
        except DBAPIError as exc:
            # Duplicate membership is rejected only after BEFORE's ordered locks.
            assert kind in {"concern", "link"} and getattr(exc.orig, "sqlstate", None) == "23505"

    with ThreadPoolExecutor(max_workers=1) as pool:
        with base[8].begin() as holder:
            pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
            holder.execute(
                text("SELECT id FROM internal_review_records WHERE id=:id FOR UPDATE"),
                {"id": old_review.id},
            )
            pending = pool.submit(write)
            _wait_for_pg_blocker(base[8], pid, "transactionid")
            # These probes would raise 55P03 if the guard took either later lock
            # before waiting for the review. They observe SQL trigger behavior.
            with base[8].begin() as observer:
                observer.execute(
                    text("SELECT id FROM review_issues WHERE id=:id FOR UPDATE NOWAIT"),
                    {"id": action.review_issue_id},
                )
                observer.execute(
                    text("SELECT id FROM revision_actions WHERE id=:id FOR UPDATE NOWAIT"),
                    {"id": saved.id},
                )
        pending.result(timeout=15)


@pytest.mark.parametrize("target_kind", ["CLAIM_VERSION", "SCIENTIFIC_CONCLUSION_VERSION"])
def test_review_creation_and_replay_reserve_insert_before_any_row_locks(revision_env, target_kind):
    env = revision_env[2]
    base = env[-1]
    target = base[6] if target_kind == "CLAIM_VERSION" else env[3].version_id
    request = uuid4()
    statements = []

    def capture(conn, cursor, statement, parameters, context, many):
        statements.append(statement)

    event.listen(base[8], "before_cursor_execute", capture)
    try:
        results = []
        for _ in range(2):
            statements.clear()
            results.append(
                env[1].create(
                    env[2],
                    base[5],
                    target_kind,
                    target,
                    "SCIENTIFIC",
                    "ACCEPT",
                    "TEST ONLY reservation",
                    (),
                    request,
                )
            )
            assert statements[0] == "LOCK TABLE internal_review_records IN ROW EXCLUSIVE MODE"
        assert results[0] == results[1]
    finally:
        event.remove(base[8], "before_cursor_execute", capture)


def test_deferred_re_review_validation_is_nonlocking(revision_env):
    write, read = prepared(revision_env, "link")
    saved = write()
    base = revision_env[2][-1]

    def validate():
        with base[8].begin() as conn:
            conn.execute(text("SET TRANSACTION READ ONLY"))
            definition = conn.execute(
                text("SELECT pg_get_functiondef('b07_complete_re_review_fn()'::regprocedure)")
            ).scalar_one()
            assert "b07_validate_re_review(NEW,false)" in definition
            conn.execute(
                text(
                    "SELECT b07_validate_re_review(l,false) "
                    "FROM revision_action_re_reviews l WHERE revision_action_id=:id"
                ),
                {"id": saved.revision_action_id},
            ).one()

    with ThreadPoolExecutor(max_workers=1) as pool:
        with base[8].begin() as holder:
            holder.execute(
                text("SELECT id FROM revision_actions WHERE id=:id FOR UPDATE"),
                {"id": saved.revision_action_id},
            )
            holder.execute(
                text("SELECT id FROM internal_review_records WHERE id=:id FOR UPDATE"),
                {"id": saved.internal_review_record_id},
            )
            pool.submit(validate).result(timeout=10)
    assert read().actions[0].re_reviews


def prepared(env, kind):
    service, action, decision_env, _, revised = env
    base = decision_env[-1]
    if kind == "decision":
        cmd = decision_command(decision_env, action.review_issue_id)
        return lambda: decision_env[0].record_revision_decision(
            decision_env[2], cmd
        ), lambda: decision_env[0].get_revision_decision(decision_env[2], base[5], cmd.id)
    if kind == "action":
        return lambda: service.record_revision_action(
            base[3], action
        ), lambda: service.read_revision_action(base[3], base[5], action.id)
    result = service.record_revision_action(base[3], action)
    review = decision_env[1].create(
        decision_env[2],
        base[5],
        "SCIENTIFIC_CONCLUSION_VERSION",
        revised.version_id,
        "SCIENTIFIC",
        "REJECT",
        "Independent",
        (),
        uuid4(),
    )
    cmd = RecordConcernReReviewCommand(base[5], result.id, review.id)
    return lambda: service.record_concern_re_review(
        decision_env[2], cmd
    ), lambda: service.get_concern_carry_forward(decision_env[2], base[5], action.review_issue_id)


@pytest.mark.parametrize("kind", ["decision", "action", "link"])
def test_all_writes_and_replays_begin_with_inventory(revision_env, kind):
    write, _ = prepared(revision_env, kind)
    engine = revision_env[2][-1][8]
    from tests.integration.phase2.pr2_20_support import capture

    # M1 §12.2: decision/action/re-review use full B09, unlike disposition.
    inventory = B09_SHARE_SQL
    with capture(engine) as observed:
        first = write()
    writers = [tx for tx in observed.transactions if inventory in tx]
    assert len(writers) == 1 and writers[0][0] == inventory
    assert all(
        not ("FOR UPDATE" in q or "FOR SHARE" in q)
        or any(t in q for t in ("review_issues", "internal_review_records", "revision_actions"))
        for q in writers[0]
    )
    with capture(engine) as observed:
        assert write() == first
    assert len(observed.transactions) == 1
    assert not any(
        "LOCK TABLE" in q or "pg_advisory" in q or "FOR UPDATE" in q or "FOR SHARE" in q
        for q, _ in observed.statements
    )


@pytest.mark.parametrize("kind", ["decision", "action", "link"])
def test_each_exact_read_keeps_one_lock_free_snapshot_during_concurrent_insert(revision_env, kind):
    write, read = prepared(revision_env, kind)
    write()
    engine = revision_env[2][-1][8]
    entered, release = Event(), Event()
    reader = {}
    observation = {}
    statements = []
    inserted = uuid4()

    def pause(conn, cursor, statement, parameters, context, many):
        if get_ident() != reader.get("thread"):
            return
        statements.append(statement)
        if not entered.is_set() and "FROM actors a JOIN project_memberships" in statement:
            entered.set()
            observation["isolation"] = conn.execute(text("SHOW transaction_isolation")).scalar_one()
            observation["readonly"] = conn.execute(text("SHOW transaction_read_only")).scalar_one()
            observation["pid"] = conn.execute(text("SELECT pg_backend_pid()")).scalar_one()
            assert release.wait(10)
            observation["visible"] = conn.execute(
                text("SELECT count(*) FROM actors WHERE id=:id"), {"id": inserted}
            ).scalar_one()

    def run():
        reader["thread"] = get_ident()
        return read()

    event.listen(engine, "after_cursor_execute", pause)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(run)
            assert entered.wait(10)
            with engine.begin() as writer:
                observation["writer_pid"] = writer.execute(
                    text("SELECT pg_backend_pid()")
                ).scalar_one()
                writer.execute(
                    text(
                        "INSERT INTO actors(id,actor_type,display_name,created_at) VALUES "
                        "(:id,'HUMAN','TEST ONLY unrelated',clock_timestamp())"
                    ),
                    {"id": inserted},
                )
            assert not future.done()
            release.set()
            assert future.result(timeout=10)
        assert observation["pid"] != observation["writer_pid"]
        assert observation["isolation"] == "repeatable read" and observation["readonly"] == "on"
        assert observation["visible"] == 0
        assert not any(
            x in q
            for q in statements
            for x in ("LOCK TABLE", "FOR SHARE", "FOR UPDATE", "pg_advisory")
        )
    finally:
        release.set()
        event.remove(engine, "after_cursor_execute", pause)


@pytest.mark.parametrize("kind", ["decision", "action", "link"])
@pytest.mark.parametrize(
    "table",
    [
        "project_role_assignments",
        "source_versions",
        "literature_evidence",
        "impact_targets",
        "internal_review_records",
    ],
)
def test_mutable_inventory_writer_wait_has_backend_evidence_and_fresh_authority(
    revision_env, kind, table
):
    write, _ = prepared(revision_env, kind)
    base = revision_env[2][-1]
    with ThreadPoolExecutor(max_workers=1) as pool:
        with base[8].begin() as holder:
            pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
            holder.execute(text(f"LOCK TABLE {table} IN ROW EXCLUSIVE MODE"))
            future = pool.submit(write)
            witness = _wait_for_pg_blocker(base[8], pid, "relation")
            assert witness["query"].startswith("LOCK TABLE ")
            base[-1].enabled = False
        with pytest.raises(ResearchBaseError) as caught:
            future.result(timeout=10)
        assert caught.value.code == ErrorCode.FORBIDDEN
    with base[8].connect() as conn:
        assert conn.execute(text("SHOW lock_timeout")).scalar_one() == "0"
        assert conn.execute(text("SHOW statement_timeout")).scalar_one() == "0"


@pytest.mark.parametrize("same_uuid", [False, True])
def test_competing_decisions_same_concern_never_partially_commit(revision_env, same_uuid):
    _, action, env, _, _ = revision_env
    cmd = decision_command(env, action.review_issue_id)
    other = cmd if same_uuid else replace(cmd, id=uuid4())
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(env[0].record_revision_decision, env[2], c) for c in (cmd, other)]
        results = []
        for future in futures:
            try:
                results.append(future.result(timeout=15))
            except ResearchBaseError as error:
                assert not same_uuid and error.code == ErrorCode.IDEMPOTENCY_CONFLICT
        assert len(results) == (2 if same_uuid else 1)
    with env[-1][8].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM decision_records")).scalar_one() == 1
        assert (
            conn.execute(text("SELECT count(*) FROM decision_revision_concerns")).scalar_one() == 1
        )


@pytest.mark.parametrize("order", ["link_first", "correction_first"])
def test_link_and_predecessor_correction_serialize_on_exact_action(revision_env, order):
    service, action, env, _, revised = revision_env
    base = env[-1]
    saved = service.record_revision_action(base[3], action)
    review = env[1].create(
        env[2],
        base[5],
        "SCIENTIFIC_CONCLUSION_VERSION",
        revised.version_id,
        "SCIENTIFIC",
        "UNCERTAIN",
        "Independent",
        (),
        uuid4(),
    )
    link = RecordConcernReReviewCommand(base[5], saved.id, review.id)
    correction = replace(action, id=uuid4(), supersedes_revision_action_id=saved.id)
    entered, release = Event(), Event()
    observation = {}

    def pause(conn, cursor, statement, parameters, context, many):
        match = (
            (statement.startswith("SELECT id FROM revision_actions") and "FOR UPDATE" in statement)
            if order == "link_first"
            else ("FOR UPDATE OF a" in statement)
        )
        if match and not entered.is_set():
            observation["pid"] = conn.execute(text("SELECT pg_backend_pid()")).scalar_one()
            entered.set()
            assert release.wait(10)

    event.listen(base[8], "after_cursor_execute", pause)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = (
                pool.submit(service.record_concern_re_review, env[2], link)
                if order == "link_first"
                else pool.submit(service.record_revision_action, base[3], correction)
            )
            assert entered.wait(10)
            second = (
                pool.submit(service.record_revision_action, base[3], correction)
                if order == "link_first"
                else pool.submit(service.record_concern_re_review, env[2], link)
            )
            witness = _wait_for_pg_blocker(base[8], observation["pid"], "transactionid")
            assert witness["pid"] != observation["pid"]
            release.set()
            assert first.result(timeout=15)
            if order == "link_first":
                assert second.result(timeout=15)
                assert service.record_concern_re_review(env[2], link).has_superseding_action
            else:
                with pytest.raises(ResearchBaseError) as caught:
                    second.result(timeout=15)
                assert caught.value.code == ErrorCode.INVALID_STATE_TRANSITION
        carry = service.get_concern_carry_forward(env[2], base[5], action.review_issue_id)
        assert len(carry.actions) == 2
        assert len(carry.actions[0].re_reviews) == (1 if order == "link_first" else 0)
    finally:
        release.set()
        event.remove(base[8], "after_cursor_execute", pause)


def test_composite_request_race_reloads_same_immutable_link(revision_env):
    write, read = prepared(revision_env, "link")
    with ThreadPoolExecutor(max_workers=2) as pool:
        a, b = pool.submit(write), pool.submit(write)
        assert a.result(timeout=15) == b.result(timeout=15)
    assert len(read().actions[0].re_reviews) == 1


@pytest.mark.parametrize("kind", ["decision", "action", "link"])
def test_scheduled_expiry_is_rechecked_at_fresh_time_in_read_snapshot(revision_env, kind):
    write, _ = prepared(revision_env, kind)
    saved = write()
    service, action, env, _, _ = revision_env
    base = env[-1]
    actor = env[2]

    def read():
        if kind == "decision":
            return env[0].get_revision_decision(actor, base[5], saved.id)
        if kind == "action":
            return service.read_revision_action(actor, base[5], saved.id)
        return service.get_concern_carry_forward(actor, base[5], action.review_issue_id)

    with base[8].begin() as conn:
        role, until = conn.execute(
            text(
                "UPDATE project_role_assignments SET effective_until=clock_timestamp()+interval "
                "'2 seconds',row_version=row_version+1 WHERE actor_id=:actor AND "
                "project_id=:project AND role='OWNER' AND effective_until IS NULL RETURNING "
                "id,effective_until"
            ),
            {"actor": actor.actor_id, "project": base[5]},
        ).one()
        conn.execute(
            text(
                "INSERT INTO "
                "project_role_events(id,role_assignment_id,actor_id,event_kind,occurred_at,"
                "reason,request_id) VALUES (:id,:role,:actor,'CLOSED',:until,'TEST ONLY "
                "expiry',:request)"
            ),
            {
                "id": uuid4(),
                "role": role,
                "actor": actor.actor_id,
                "until": until,
                "request": uuid4(),
            },
        )
    observation = {}

    def advance(conn, cursor, statement, parameters, context, many):
        if (
            "SELECT a.* FROM revision_actions" in statement
            or "SELECT * FROM decision_records WHERE id" in statement
        ):
            if observation.get("advanced"):
                return
            observation["advanced"] = True
            before = conn.execute(text("SELECT clock_timestamp()")).scalar_one()
            assert before < until
            conn.execute(
                text(
                    "SELECT pg_sleep(GREATEST(0,EXTRACT(EPOCH FROM "
                    "(:until-clock_timestamp()))+0.1))"
                ),
                {"until": until},
            )
            assert conn.execute(text("SELECT clock_timestamp()")).scalar_one() >= until

    event.listen(base[8], "after_cursor_execute", advance)
    try:
        with pytest.raises(ResearchBaseError) as caught:
            read()
        assert caught.value.code == ErrorCode.FORBIDDEN and observation["advanced"]
    finally:
        event.remove(base[8], "after_cursor_execute", advance)
