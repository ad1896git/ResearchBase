"""Observe lock-free historical reads and exact writer SQL order."""

# SQL protocol assertions are literal.
# ruff: noqa: E501
from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import event, text

from researchbase.application.revision_action import (
    RecordConcernReReviewCommand,
    RecordNoveltyRevisionCommand,
    RevisionActionService,
)
from researchbase.persistence.novelty_repository import N
from tests.integration.phase2.test_b23_novelty_review import _review, _root

pytest_plugins = ("tests.integration.phase2.pr2_18_fixtures",)


def test_first_statement_all_writers_and_lock_free_reads(novelty_env):
    e = novelty_env
    c, root = _root(e)
    statements = []

    def trace(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(e["engine"], "before_cursor_execute", trace)
    try:
        service, review = _review(e, root)
        assert statements[0] == "LOCK TABLE " + ",".join(N) + " IN SHARE MODE"
        assert (
            statements[1]
            == "LOCK TABLE internal_review_records,review_issue_events,review_issues IN ROW EXCLUSIVE MODE"
        )
        result = e["service"].record_novelty_assessment(
            e["author"], replace(c, id=uuid4(), supersedes_assessment_id=root.id)
        )
        actions = RevisionActionService(e["factory"], e["credentials"], e["literature"])
        statements.clear()
        action = actions.record_novelty_revision(
            e["author"],
            RecordNoveltyRevisionCommand(uuid4(), e["project"], review.issues[0].id, result.id),
        )
        assert statements[0] == "LOCK TABLE " + ",".join(N) + " IN SHARE MODE"
        assert statements[1] == "LOCK TABLE revision_actions IN ROW EXCLUSIVE MODE"
        _, new_review = _review(e, result, issues=())
        statements.clear()
        actions.record_concern_re_review(
            e["reviewer"],
            RecordConcernReReviewCommand(e["project"], action.id, new_review.id),
            novelty=True,
        )
        assert statements[0] == "LOCK TABLE " + ",".join(N) + " IN SHARE MODE"
        assert statements[1] == "LOCK TABLE revision_action_re_reviews IN ROW EXCLUSIVE MODE"
        statements.clear()
        # These SHARE ROW EXCLUSIVE locks conflict with writer reservations, but not SELECT.
        with e["race_engine"].begin() as conn:
            conn.execute(
                text(
                    "LOCK TABLE internal_review_records,revision_actions,revision_action_re_reviews IN SHARE ROW EXCLUSIVE MODE"
                )
            )
            assert (
                service.read(e["reviewer"], e["project"], review.id).content_hash
                == review.content_hash
            )
            assert (
                actions.read_revision_action(e["reviewer"], e["project"], action.id).id == action.id
            )
            assert (
                actions.read_novelty_re_review(
                    e["reviewer"], e["project"], action.id, new_review.id
                ).review.id
                == new_review.id
            )
        assert not any(
            s.lstrip().upper().startswith("LOCK ")
            or "FOR UPDATE" in s.upper()
            or "FOR SHARE" in s.upper()
            or "PG_ADVISORY" in s.upper()
            for s in statements
        )
    finally:
        event.remove(e["engine"], "before_cursor_execute", trace)


@pytest.mark.parametrize("kind", ["review", "revision", "link"])
@pytest.mark.parametrize("authority", ["credential", "role"])
def test_post_target_wait_expiry_has_database_witness(novelty_env, monkeypatch, kind, authority):
    from concurrent.futures import ThreadPoolExecutor
    from datetime import timedelta
    from threading import Event
    from time import monotonic

    from researchbase.foundation.errors import ErrorCode, ResearchBaseError
    from researchbase.persistence.novelty_repository import SqlAlchemyNoveltyRepository
    from tests.integration.phase2.test_pr2_18_concurrency import _witness

    e = novelty_env
    c, root = _root(e)
    _, review = _review(e, root)
    successor = e["service"].record_novelty_assessment(
        e["author"], replace(c, id=uuid4(), supersedes_assessment_id=root.id)
    )
    actions = RevisionActionService(e["factory"], e["credentials"], e["literature"])
    action_command = RecordNoveltyRevisionCommand(
        uuid4(), e["project"], review.issues[0].id, successor.id
    )
    action = (
        actions.record_novelty_revision(e["author"], action_command) if kind == "link" else None
    )
    new_review = _review(e, successor, issues=())[1] if kind == "link" else None
    acquired = []
    from researchbase.persistence.internal_review_repository import (
        SqlAlchemyInternalReviewRepository,
    )

    lock_targets = SqlAlchemyInternalReviewRepository.lock_novelty_targets

    def observe_lock(repo, *args):
        result = lock_targets(repo, *args)
        acquired.append(repo._session.execute(text("SELECT clock_timestamp()")).scalar_one())
        return result

    monkeypatch.setattr(SqlAlchemyInternalReviewRepository, "lock_novelty_targets", observe_lock)
    checks = []
    original = SqlAlchemyNoveltyRepository.at

    def clock(repo):
        at = original(repo)
        checks.append(at)
        return at

    monkeypatch.setattr(SqlAlchemyNoveltyRepository, "at", clock)

    def operation():
        if kind == "review":
            return _review(e, root)[1]
        if kind == "revision":
            return actions.record_novelty_revision(e["author"], action_command)
        assert action is not None and new_review is not None
        return actions.record_concern_re_review(
            e["reviewer"],
            RecordConcernReReviewCommand(e["project"], action.id, new_review.id),
            novelty=True,
        )

    with e["race_engine"].connect() as holder, ThreadPoolExecutor(max_workers=1) as pool:
        holder.execute(
            text("SELECT id FROM claim_versions WHERE id=:id FOR UPDATE"), {"id": e["claim"]}
        )
        holder_pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
        expiry = holder.execute(text("SELECT clock_timestamp()")).scalar_one() + timedelta(
            seconds=2
        )
        if authority == "credential":
            e["credentials"].expires_at = expiry
        else:
            actor = e["author"] if kind == "revision" else e["reviewer"]
            with e["engine"].begin() as role_conn:
                role_id = role_conn.execute(
                    text(
                        "UPDATE project_role_assignments SET effective_until=:expiry,row_version=row_version+1 WHERE actor_id=:actor AND effective_until IS NULL RETURNING id"
                    ),
                    {"expiry": expiry, "actor": actor.actor_id},
                ).scalar_one()
                role_conn.execute(
                    text(
                        "INSERT INTO project_role_events(id,role_assignment_id,actor_id,event_kind,occurred_at,reason,request_id) VALUES (:id,:role,:actor,'CLOSED',:expiry,'Scheduled expiry',:request)"
                    ),
                    {
                        "id": uuid4(),
                        "role": role_id,
                        "actor": actor.actor_id,
                        "expiry": expiry,
                        "request": uuid4(),
                    },
                )
        pending = pool.submit(operation)
        waiter_pid = _witness(e["race_engine"], holder_pid, expiry)
        with e["race_engine"].connect() as observer:
            tx_started, wait_started = observer.execute(
                text("SELECT xact_start,clock_timestamp() FROM pg_stat_activity WHERE pid=:id"),
                {"id": waiter_pid},
            ).one()
            deadline = monotonic() + 5
            while observer.execute(text("SELECT clock_timestamp()")).scalar_one() < expiry:
                assert monotonic() < deadline
                Event().wait(0.01)
            released_at = observer.execute(text("SELECT clock_timestamp()")).scalar_one()
        holder.commit()
        with pytest.raises(ResearchBaseError) as error:
            pending.result(timeout=10)
        assert error.value.code is ErrorCode.FORBIDDEN
    assert (
        tx_started < expiry and wait_started < expiry <= released_at <= acquired[-1] <= checks[-1]
    )
    assert any(at < expiry for at in checks)
    with e["engine"].connect() as conn:
        count = conn.execute(text("SELECT count(*) FROM revision_action_re_reviews")).scalar_one()
        assert count == 0
        if kind == "revision":
            assert conn.execute(text("SELECT count(*) FROM revision_actions")).scalar_one() == 0
        if kind == "review":
            assert (
                conn.execute(text("SELECT count(*) FROM internal_review_records")).scalar_one() == 1
            )
    print(
        "B23_EXPIRY_EVIDENCE",
        dict(
            command=kind,
            authority=authority,
            tx_started_at=tx_started.isoformat(),
            expiry_at=expiry.isoformat(),
            lock_wait_started_at=wait_started.isoformat(),
            lock_released_at=released_at.isoformat(),
            lock_acquired_at=acquired[-1].isoformat(),
            authorization_checked_at=checks[-1].isoformat(),
            outcome="FORBIDDEN",
            new_effects=0,
        ),
    )


@pytest.mark.parametrize("kind", ["review", "revision", "link"])
def test_concurrent_same_key_replay_has_one_effect(novelty_env, kind):
    from concurrent.futures import ThreadPoolExecutor

    from tests.integration.phase2.test_pr2_18_concurrency import _witness

    e = novelty_env
    c, root = _root(e)
    request = uuid4()
    _, review = _review(e, root)
    successor = e["service"].record_novelty_assessment(
        e["author"], replace(c, id=uuid4(), supersedes_assessment_id=root.id)
    )
    actions = RevisionActionService(e["factory"], e["credentials"], e["literature"])
    cmd = RecordNoveltyRevisionCommand(uuid4(), e["project"], review.issues[0].id, successor.id)
    action = actions.record_novelty_revision(e["author"], cmd) if kind == "link" else None
    new_review = _review(e, successor, issues=())[1] if kind == "link" else None

    def operation():
        if kind == "review":
            return _review(e, root, request)[1]
        if kind == "revision":
            return actions.record_novelty_revision(e["author"], cmd)
        assert action is not None and new_review is not None
        return actions.record_concern_re_review(
            e["reviewer"],
            RecordConcernReReviewCommand(e["project"], action.id, new_review.id),
            novelty=True,
        )

    with e["race_engine"].connect() as holder, ThreadPoolExecutor(max_workers=2) as pool:
        holder.execute(
            text("SELECT id FROM claim_versions WHERE id=:id FOR UPDATE"), {"id": e["claim"]}
        )
        pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
        first = pool.submit(operation)
        _witness(e["race_engine"], pid)
        second = pool.submit(operation)
        holder.commit()
        left, right = first.result(timeout=15), second.result(timeout=15)
    if kind == "link":
        from researchbase.application.revision_action import NoveltyReReviewReadback

        assert isinstance(left, NoveltyReReviewReadback) and isinstance(
            right, NoveltyReReviewReadback
        )
        assert left.recorded_at == right.recorded_at
    else:
        from researchbase.application.revision_action import NoveltyReReviewReadback

        assert not isinstance(left, NoveltyReReviewReadback) and not isinstance(
            right, NoveltyReReviewReadback
        )
        assert left.id == right.id and left.content_hash == right.content_hash
    with e["engine"].connect() as conn:
        expected = {"review": (2, 0, 0), "revision": (1, 1, 0), "link": (2, 1, 1)}[kind]
        for table, count in zip(
            ("internal_review_records", "revision_actions", "revision_action_re_reviews"),
            expected,
            strict=True,
        ):
            assert conn.execute(text("SELECT count(*) FROM " + table)).scalar_one() == count


@pytest.mark.parametrize("change", ["comparison", "evidence", "CORRECTED", "RETRACTED"])
def test_result_validity_writer_wait_is_reread_before_action(novelty_env, monkeypatch, change):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event, local

    from researchbase.domain.source_version import SourceVersionKind
    from researchbase.foundation.errors import ErrorCode, ResearchBaseError
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork
    from tests.integration.phase2.b19_basis_support import record, setup, source_change
    from tests.integration.phase2.test_pr2_18_concurrency import _witness

    e = novelty_env
    c, rc, comparison, _ = setup(e)
    root = record(e, c)
    _, review = _review(e, root)
    result = record(e, replace(c, id=uuid4(), supersedes_assessment_id=root.id))
    actions = RevisionActionService(e["factory"], e["credentials"], e["literature"])
    cmd = RecordNoveltyRevisionCommand(uuid4(), e["project"], review.issues[0].id, result.id)
    source_service, freeze = (
        source_change(e, SourceVersionKind(change))
        if change in {"CORRECTED", "RETRACTED"}
        else (None, None)
    )
    ready, release = Event(), Event()
    state = local()
    pids = []
    commit = SqlAlchemyUnitOfWork.commit

    def held_commit(uow):
        if getattr(state, "invalidating", False):
            pids.append(
                uow._require_session().execute(text("SELECT pg_backend_pid()")).scalar_one()
            )
            ready.set()
            assert release.wait(10)
        return commit(uow)

    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", held_commit)

    def invalidate():
        state.invalidating = True
        if change == "comparison":
            return e["service"].record_prior_art_relation(
                e["author"], replace(rc, id=uuid4(), supersedes_prior_art_relation_id=comparison.id)
            )
        if change == "evidence":
            return e["literature"].review(
                e["reviewer"], e["project"], e["evidence"], "DISPUTED", "Later inspection", uuid4()
            )
        assert source_service is not None and freeze is not None
        return source_service.freeze(freeze)

    with ThreadPoolExecutor(max_workers=2) as pool:
        invalidator = pool.submit(invalidate)
        pending = None
        try:
            assert ready.wait(10)
            pending = pool.submit(actions.record_novelty_revision, e["researcher"], cmd)
            _witness(e["race_engine"], pids[0])
        finally:
            release.set()
        invalidator.result(timeout=10)
        with pytest.raises(ResearchBaseError) as error:
            pending.result(timeout=15)
        assert error.value.code is ErrorCode.INVALID_STATE_TRANSITION
    with e["engine"].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM revision_actions")).scalar_one() == 0
        assert (
            conn.execute(
                text("SELECT status FROM review_issues WHERE id=:id"), {"id": review.issues[0].id}
            ).scalar_one()
            == "OPEN"
        )


@pytest.mark.parametrize("order", ["legacy_first", "novelty_first"])
def test_legacy_review_writer_and_novelty_review_share_target_order(novelty_env, order):
    from concurrent.futures import ThreadPoolExecutor

    from researchbase.application.internal_review import InternalReviewService
    from tests.integration.phase2.test_pr2_18_concurrency import _witness

    e = novelty_env
    _, root = _root(e)
    reviews = InternalReviewService(e["factory"], e["credentials"], e["literature"])

    def legacy():
        return reviews.create(
            e["reviewer"],
            e["project"],
            "CLAIM_VERSION",
            e["claim"],
            "SCIENTIFIC",
            "UNCERTAIN",
            "Legacy exact claim",
            (),
            uuid4(),
        )

    def novelty():
        return _review(e, root)[1]

    operations = (legacy, novelty) if order == "legacy_first" else (novelty, legacy)
    with e["race_engine"].connect() as holder, ThreadPoolExecutor(max_workers=2) as pool:
        holder.execute(
            text("SELECT id FROM claim_versions WHERE id=:id FOR UPDATE"), {"id": e["claim"]}
        )
        pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
        first = pool.submit(operations[0])
        _witness(e["race_engine"], pid)
        second = pool.submit(operations[1])
        holder.commit()
        assert first.result(timeout=15).id != second.result(timeout=15).id


@pytest.mark.parametrize("race", ["predecessors", "correction_first", "link_first"])
def test_corrections_and_links_serialize_without_forks(novelty_env, monkeypatch, race):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event, local

    from researchbase.foundation.errors import ErrorCode, ResearchBaseError
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork
    from tests.integration.phase2.test_pr2_18_concurrency import _witness

    e = novelty_env
    c, root = _root(e)
    _, original = _review(e, root)
    result = e["service"].record_novelty_assessment(
        e["author"], replace(c, id=uuid4(), supersedes_assessment_id=root.id)
    )
    actions = RevisionActionService(e["factory"], e["credentials"], e["literature"])
    cmd = RecordNoveltyRevisionCommand(uuid4(), e["project"], original.issues[0].id, result.id)
    action = actions.record_novelty_revision(e["researcher"], cmd)
    _, review = _review(e, result, issues=())
    link_cmd = RecordConcernReReviewCommand(e["project"], action.id, review.id)
    ready, release = Event(), Event()
    state = local()
    pids = []
    commit = SqlAlchemyUnitOfWork.commit

    def held_commit(uow):
        if getattr(state, "first", False):
            pids.append(
                uow._require_session().execute(text("SELECT pg_backend_pid()")).scalar_one()
            )
            ready.set()
            assert release.wait(10)
        return commit(uow)

    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", held_commit)

    def correction():
        return actions.record_novelty_revision(
            e["researcher"], replace(cmd, id=uuid4(), supersedes_revision_action_id=action.id)
        )

    def link():
        return actions.record_concern_re_review(e["reviewer"], link_cmd, novelty=True)

    def first():
        state.first = True
        return (link if race == "link_first" else correction)()

    with ThreadPoolExecutor(max_workers=2) as pool:
        winner = pool.submit(first)
        try:
            assert ready.wait(10)
            loser = pool.submit(correction if race in {"predecessors", "link_first"} else link)
            _witness(e["race_engine"], pids[0])
        finally:
            release.set()
        winner.result(timeout=10)
        if race == "link_first":
            loser.result(timeout=15)
            saved = actions.read_novelty_re_review(e["viewer"], e["project"], action.id, review.id)
            assert saved.action.has_superseding_action
        else:
            with pytest.raises(ResearchBaseError) as error:
                loser.result(timeout=15)
            assert error.value.code is ErrorCode.INVALID_STATE_TRANSITION
    with e["engine"].connect() as conn:
        assert (
            conn.execute(
                text(
                    "SELECT count(*) FROM revision_actions WHERE supersedes_revision_action_id=:id"
                ),
                {"id": action.id},
            ).scalar_one()
            == 1
        )
        assert conn.execute(
            text("SELECT count(*) FROM revision_action_re_reviews")
        ).scalar_one() == (1 if race == "link_first" else 0)
        assert (
            conn.execute(
                text("SELECT status FROM review_issues WHERE id=:id"), {"id": original.issues[0].id}
            ).scalar_one()
            == "OPEN"
        )


@pytest.mark.parametrize("kind", ["review", "revision", "link"])
def test_fixed_snapshot_inventory_wait_is_first_for_each_writer(novelty_env, kind):
    from concurrent.futures import ThreadPoolExecutor

    from tests.integration.phase2.test_pr2_18_concurrency import _witness

    e = novelty_env
    c, root = _root(e)
    _, old = _review(e, root)
    result = e["service"].record_novelty_assessment(
        e["author"], replace(c, id=uuid4(), supersedes_assessment_id=root.id)
    )
    actions = RevisionActionService(e["factory"], e["credentials"], e["literature"])
    cmd = RecordNoveltyRevisionCommand(uuid4(), e["project"], old.issues[0].id, result.id)
    action = actions.record_novelty_revision(e["researcher"], cmd) if kind == "link" else None
    review = _review(e, result, issues=())[1] if kind == "link" else None

    def operation():
        if kind == "review":
            return _review(e, root)[1]
        if kind == "revision":
            return actions.record_novelty_revision(e["researcher"], cmd)
        assert action is not None and review is not None
        return actions.record_concern_re_review(
            e["reviewer"],
            RecordConcernReReviewCommand(e["project"], action.id, review.id),
            novelty=True,
        )

    with e["race_engine"].connect() as holder, ThreadPoolExecutor(max_workers=1) as pool:
        holder.execute(text("LOCK TABLE projects IN ROW EXCLUSIVE MODE"))
        pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
        pending = pool.submit(operation)
        waiter = _witness(e["race_engine"], pid)
        with e["race_engine"].connect() as observer:
            sql = observer.execute(
                text("SELECT query FROM pg_stat_activity WHERE pid=:pid"), {"pid": waiter}
            ).scalar_one()
            assert sql == "LOCK TABLE " + ",".join(N) + " IN SHARE MODE"
        holder.commit()
        pending.result(timeout=15)


@pytest.mark.parametrize("kind", ["review", "revision", "link"])
@pytest.mark.parametrize("state", ["40001", "40P01", "55P03"])
def test_failures_rollback_all_effects_and_retry_only_allowed_states(
    novelty_env, monkeypatch, kind, state
):
    from sqlalchemy.exc import OperationalError

    from researchbase.persistence.internal_review_repository import (
        SqlAlchemyInternalReviewRepository,
    )

    e = novelty_env
    c, root = _root(e)
    _, old = _review(e, root)
    result = e["service"].record_novelty_assessment(
        e["author"], replace(c, id=uuid4(), supersedes_assessment_id=root.id)
    )
    actions = RevisionActionService(e["factory"], e["credentials"], e["literature"])
    cmd = RecordNoveltyRevisionCommand(uuid4(), e["project"], old.issues[0].id, result.id)
    action = actions.record_novelty_revision(e["researcher"], cmd) if kind == "link" else None
    review = _review(e, result, issues=())[1] if kind == "link" else None
    calls = []
    original = SqlAlchemyInternalReviewRepository.force_novelty_constraints

    class DatabaseFault(Exception):
        sqlstate = state
        diag = None

    def fail_after_insert(repo):
        original(repo)
        calls.append(repo._session.execute(text("SELECT pg_current_xact_id()::text")).scalar_one())
        if len(calls) <= 2:
            raise OperationalError("secret SQL", {}, DatabaseFault("secret database detail"))

    monkeypatch.setattr(
        SqlAlchemyInternalReviewRepository, "force_novelty_constraints", fail_after_insert
    )

    def operation():
        if kind == "review":
            return _review(e, root)[1]
        if kind == "revision":
            return actions.record_novelty_revision(e["researcher"], cmd)
        assert action is not None and review is not None
        return actions.record_concern_re_review(
            e["reviewer"],
            RecordConcernReReviewCommand(e["project"], action.id, review.id),
            novelty=True,
        )

    if state == "55P03":
        with pytest.raises(RuntimeError, match="recover by exact entitled read"):
            operation()
        assert len(calls) == 1
    else:
        operation()
        assert len(calls) == len(set(calls)) == 3
    with e["engine"].connect() as conn:
        expected = (
            {"review": (2, 0, 0), "revision": (1, 1, 0), "link": (2, 1, 1)}[kind]
            if state != "55P03"
            else {"review": (1, 0, 0), "revision": (1, 0, 0), "link": (2, 1, 0)}[kind]
        )
        for table, count in zip(
            ("internal_review_records", "revision_actions", "revision_action_re_reviews"),
            expected,
            strict=True,
        ):
            assert conn.execute(text("SELECT count(*) FROM " + table)).scalar_one() == count
        assert conn.execute(text("SELECT count(*) FROM review_issue_events")).scalar_one() == (
            2 if kind == "review" and state != "55P03" else 1
        )


@pytest.mark.parametrize("deferred", ["decision", "ADDRESSED", "DISMISSED"])
def test_legacy_governance_paths_deny_while_b23_records_action(novelty_env, deferred):
    from concurrent.futures import ThreadPoolExecutor

    from researchbase.application.decision import DecisionService, RecordRevisionDecisionCommand
    from researchbase.application.internal_review import (
        InternalReviewService,
        RecordIssueDispositionCommand,
    )
    from researchbase.foundation.errors import ErrorCode, ResearchBaseError
    from tests.integration.phase2.test_pr2_18_concurrency import _witness

    e = novelty_env
    c, root = _root(e)
    _, original = _review(e, root)
    result = e["service"].record_novelty_assessment(
        e["author"], replace(c, id=uuid4(), supersedes_assessment_id=root.id)
    )
    actions = RevisionActionService(e["factory"], e["credentials"], e["literature"])
    cmd = RecordNoveltyRevisionCommand(uuid4(), e["project"], original.issues[0].id, result.id)

    def unsupported():
        if deferred == "decision":
            service = DecisionService(e["factory"], e["credentials"], e["literature"])
            return service.record_revision_decision(
                e["owner"],
                RecordRevisionDecisionCommand(
                    uuid4(),
                    e["project"],
                    original.issues[0].id,
                    "Concern?",
                    "Still deferred",
                    "REQUIRE_CHANGE",
                ),
            )
        reviews = InternalReviewService(e["factory"], e["credentials"], e["literature"])
        return reviews.record_issue_disposition(
            e["reviewer"],
            RecordIssueDispositionCommand(
                uuid4(),
                e["project"],
                original.issues[0].id,
                deferred,
                cmd.id,
                uuid4(),
                "Still deferred",
                uuid4() if deferred == "DISMISSED" else None,
            ),
        )

    with e["race_engine"].connect() as holder, ThreadPoolExecutor(max_workers=2) as pool:
        holder.execute(
            text("SELECT id FROM claim_versions WHERE id=:id FOR UPDATE"), {"id": e["claim"]}
        )
        pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
        pending = pool.submit(actions.record_novelty_revision, e["researcher"], cmd)
        _witness(e["race_engine"], pid)
        denied = pool.submit(unsupported)
        holder.commit()
        pending.result(timeout=15)
        with pytest.raises(ResearchBaseError) as error:
            denied.result(timeout=15)
        assert error.value.code is ErrorCode.INVALID_STATE_TRANSITION
    with e["engine"].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM revision_actions")).scalar_one() == 1
        assert conn.execute(text("SELECT count(*) FROM decision_records")).scalar_one() == 0
        assert conn.execute(text("SELECT count(*) FROM review_issue_events")).scalar_one() == 1
        assert (
            conn.execute(
                text("SELECT status FROM review_issues WHERE id=:id"), {"id": original.issues[0].id}
            ).scalar_one()
            == "OPEN"
        )
