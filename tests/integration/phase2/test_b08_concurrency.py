"""Observed PostgreSQL waits, snapshot reads and atomic disposition failures."""

# SQL literals retain the reviewed relational predicates.
# ruff: noqa: E501

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Event, get_ident
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event, text

from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.approval_repository import B09_SNAPSHOT_TABLES
from tests.integration.phase2.b08_support import (
    approval_env,
    conclusion_env,
    decision_env,
    disposition_case,
    phase2_database_url,
    revision_env,
)
from tests.integration.phase2.test_pr2_14_internal_review import _wait_for_pg_blocker

pytestmark = pytest.mark.integration
pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)
_FIXTURES = (conclusion_env, decision_env, phase2_database_url, revision_env, approval_env)


def test_creation_and_uuid_replay_begin_with_exact_share_inventory(revision_env):
    service, actor, cmd, base, _ = disposition_case(revision_env)
    from tests.integration.phase2.pr2_20_support import capture

    tables = tuple(
        t for t in B09_SNAPSHOT_TABLES if t not in {"review_issues", "review_issue_events"}
    )
    inventory = "LOCK TABLE " + ",".join(tables) + " IN SHARE MODE"
    with capture(base[8]) as observed:
        service.record_issue_disposition(actor, cmd)
    writers = [tx for tx in observed.transactions if inventory in tx]
    assert len(writers) == 1 and writers[0][0] == inventory
    assert "SET LOCAL lock_timeout='10s'" in writers[0]
    assert "SET LOCAL statement_timeout='30s'" in writers[0]
    with capture(base[8]) as observed:
        service.record_issue_disposition(actor, cmd)
    assert len(observed.transactions) == 1
    assert not any(
        "LOCK TABLE" in q or "pg_advisory" in q or "FOR UPDATE" in q or "FOR SHARE" in q
        for q, _ in observed.statements
    )
    with base[8].connect() as conn:
        assert conn.execute(text("SHOW lock_timeout")).scalar_one() == "0"
        assert conn.execute(text("SHOW statement_timeout")).scalar_one() == "0"


@pytest.mark.parametrize("same_uuid", [False, True])
def test_observed_same_issue_race_commits_one_terminal_event(revision_env, same_uuid):
    service, actor, cmd, base, _ = disposition_case(revision_env)
    entered, release = Event(), Event()
    holder = {}

    def pause(conn, cursor, statement, parameters, context, many):
        if not entered.is_set() and statement.startswith("INSERT INTO review_issue_events"):
            holder["pid"] = conn.connection.driver_connection.info.backend_pid
            entered.set()
            assert release.wait(10)

    event.listen(base[8], "after_cursor_execute", pause)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(service.record_issue_disposition, actor, cmd)
            assert entered.wait(10)
            second = pool.submit(
                service.record_issue_disposition,
                actor,
                cmd if same_uuid else replace(cmd, id=uuid4()),
            )
            witness = _wait_for_pg_blocker(
                base[8], holder["pid"], "advisory" if same_uuid else "transactionid"
            )
            assert witness["pid"] != holder["pid"]
            release.set()
            saved = first.result(timeout=15)
            if same_uuid:
                assert second.result(timeout=15) == saved
            else:
                with pytest.raises(ResearchBaseError) as caught:
                    second.result(timeout=15)
                assert caught.value.code == ErrorCode.INVALID_STATE_TRANSITION
    finally:
        release.set()
        event.remove(base[8], "after_cursor_execute", pause)
    assert len(service.get_issue_history(actor, base[5], cmd.review_issue_id).events) == 2


@pytest.mark.parametrize("first_writer", ["disposition", "correction"])
def test_correction_and_disposition_both_commit_orders_without_action_lock_cycle(
    revision_env, first_writer
):
    service, actor, cmd, base, action = disposition_case(revision_env)
    correction = replace(action, id=uuid4(), supersedes_revision_action_id=cmd.revision_action_id)

    def dispose():
        return service.record_issue_disposition(actor, cmd)

    def correct():
        return revision_env[0].record_revision_action(base[3], correction)

    entered, release = Event(), Event()
    holder = {}
    match = (
        "INSERT INTO review_issue_events"
        if first_writer == "disposition"
        else "INSERT INTO revision_actions"
    )

    def pause(conn, cursor, statement, parameters, context, many):
        if not entered.is_set() and statement.startswith(match):
            holder["pid"] = conn.connection.driver_connection.info.backend_pid
            entered.set()
            assert release.wait(10)

    event.listen(base[8], "after_cursor_execute", pause)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(dispose if first_writer == "disposition" else correct)
            assert entered.wait(10)
            second = pool.submit(correct if first_writer == "disposition" else dispose)
            _wait_for_pg_blocker(
                base[8],
                holder["pid"],
                "relation" if first_writer == "disposition" else "transactionid",
            )
            release.set()
            assert first.result(timeout=15)
            if first_writer == "disposition":
                assert second.result(timeout=15)
                assert service.record_issue_disposition(actor, cmd).has_superseding_action
            else:
                with pytest.raises(ResearchBaseError) as caught:
                    second.result(timeout=15)
                assert caught.value.code == ErrorCode.INVALID_STATE_TRANSITION
                assert (
                    service.get_issue_history(actor, base[5], cmd.review_issue_id).status == "OPEN"
                )
    finally:
        release.set()
        event.remove(base[8], "after_cursor_execute", pause)


@pytest.mark.parametrize("reader", ["history", "disposition", "review"])
def test_lock_free_repeatable_read_allows_disposition_and_unrelated_insert_commit(
    revision_env, reader
):
    service, actor, cmd, base, _ = disposition_case(revision_env)
    # Disposition lookup must already exist; for the other readers snapshot starts OPEN.
    if reader == "disposition":
        service.record_issue_disposition(actor, cmd)
    entered, release = Event(), Event()
    state: dict[str, Any] = {"sql": []}
    new_actor = uuid4()
    writer_engine = create_engine(str(base[8].url))

    def capture(conn, cursor, statement, parameters, context, many):
        if get_ident() == state.get("thread"):
            state["sql"].append(statement)

    def pause(conn, cursor, statement, parameters, context, many):
        if (
            get_ident() == state.get("thread")
            and not entered.is_set()
            and "FROM actors a JOIN project_memberships" in statement
        ):
            state["pid"] = conn.connection.driver_connection.info.backend_pid
            entered.set()
            state["isolation"] = conn.execute(text("SHOW transaction_isolation")).scalar_one()
            state["readonly"] = conn.execute(text("SHOW transaction_read_only")).scalar_one()
            assert release.wait(10)
            state["visible"] = conn.execute(
                text("SELECT count(*) FROM actors WHERE id=:id"), {"id": new_actor}
            ).scalar_one()

    def read():
        state["thread"] = get_ident()
        if reader == "history":
            return service.get_issue_history(actor, base[5], cmd.review_issue_id)
        if reader == "disposition":
            return service.get_issue_disposition(actor, base[5], cmd.id)
        return service.read(actor, base[5], revision_env[3].id)

    event.listen(base[8], "before_cursor_execute", capture)
    event.listen(base[8], "after_cursor_execute", pause)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(read)
            assert entered.wait(10)
            with writer_engine.begin() as conn:
                assert conn.execute(text("SELECT pg_backend_pid()")).scalar_one() != state["pid"]
                conn.execute(
                    text(
                        "INSERT INTO actors(id,actor_type,display_name,created_at) "
                        "VALUES (:id,'HUMAN','Unrelated snapshot writer',clock_timestamp())"
                    ),
                    {"id": new_actor},
                )
            if reader != "disposition":
                saved = service.record_issue_disposition(actor, cmd)
                assert saved.id == cmd.id
            assert not pending.done()
            release.set()
            result = pending.result(timeout=15)
            if reader == "history":
                assert result.status == "OPEN" and len(result.events) == 1
            elif reader == "review":
                assert result.issues[0].status == "OPEN"
            assert all(
                token not in sql.upper()
                for sql in state["sql"]
                for token in ("LOCK TABLE", "FOR SHARE", "FOR UPDATE", "ADVISORY")
            )
        assert (
            service.get_issue_history(actor, base[5], cmd.review_issue_id).status == cmd.disposition
        )
        assert state["visible"] == 0
        assert state["isolation"] == "repeatable read" and state["readonly"] == "on"
        with writer_engine.connect() as conn:
            assert (
                conn.execute(
                    text("SELECT count(*) FROM actors WHERE id=:id"), {"id": new_actor}
                ).scalar_one()
                == 1
            )
    finally:
        release.set()
        writer_engine.dispose()
        event.remove(base[8], "before_cursor_execute", capture)
        event.remove(base[8], "after_cursor_execute", pause)


@pytest.mark.parametrize(
    "table",
    [
        "actor_subject_bindings",
        "project_role_assignments",
        "literature_sources",
        "literature_evidence",
        "impact_targets",
    ],
)
def test_first_inventory_wait_bounds_and_rechecks_revoked_credential(revision_env, table):
    service, actor, cmd, base, _ = disposition_case(revision_env)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with base[8].begin() as holder:
            pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
            holder.execute(text(f"LOCK TABLE {table} IN ROW EXCLUSIVE MODE"))
            future = pool.submit(service.record_issue_disposition, actor, cmd)
            witness = _wait_for_pg_blocker(base[8], pid, "relation")
            assert witness["query"].startswith("LOCK TABLE ")
            base[-1].enabled = False
        with pytest.raises(ResearchBaseError) as caught:
            future.result(timeout=15)
        assert caught.value.code == ErrorCode.FORBIDDEN
    with base[8].connect() as conn:
        assert (
            conn.execute(
                text("SELECT count(*) FROM review_issue_events WHERE prior_status='OPEN'")
            ).scalar_one()
            == 0
        )


@pytest.mark.parametrize("stage", ["event", "constraints", "readback"])
def test_injected_failure_rolls_back_event_and_projection(revision_env, stage):
    service, actor, cmd, base, _ = disposition_case(revision_env)

    def fail(conn, cursor, statement, parameters, context, many):
        if (
            (stage == "event" and statement.startswith("INSERT INTO review_issue_events"))
            or (stage == "constraints" and statement == "SET CONSTRAINTS ALL IMMEDIATE")
            or (stage == "readback" and statement.startswith("SELECT b08_check_history"))
        ):
            raise RuntimeError("injected failure")

    event.listen(base[8], "after_cursor_execute", fail)
    try:
        with pytest.raises(RuntimeError, match="injected failure"):
            service.record_issue_disposition(actor, cmd)
    finally:
        event.remove(base[8], "after_cursor_execute", fail)
    assert service.get_issue_history(actor, base[5], cmd.review_issue_id).status == "OPEN"
    assert len(service.get_issue_history(actor, base[5], cmd.review_issue_id).events) == 1


@pytest.mark.parametrize("order", ["disposition_first", "issue_first"])
def test_late_selected_review_issue_insert_is_excluded_and_reread(revision_env, order):
    service, actor, cmd, base, _ = disposition_case(revision_env)
    inserted = uuid4()

    def late_issue():
        with base[8].begin() as conn:
            conn.execute(
                text("""INSERT INTO review_issues(id,review_record_id,severity,issue_type,description,status,created_at,ordinal)
                VALUES (:id,:review,'MAJOR','OTHER','Late exact concern','OPEN',clock_timestamp(),0)"""),
                {"id": inserted, "review": cmd.re_review_record_id},
            )

    def dispose():
        return service.record_issue_disposition(actor, cmd)

    entered, release = Event(), Event()
    holder = {}

    def pause(conn, cursor, statement, parameters, context, many):
        match = (
            statement.startswith("INSERT INTO review_issue_events")
            if order == "disposition_first"
            else statement.startswith("INSERT INTO review_issues")
        )
        if match and not entered.is_set():
            holder["pid"] = conn.connection.driver_connection.info.backend_pid
            entered.set()
            assert release.wait(10)

    event.listen(base[8], "after_cursor_execute", pause)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(dispose if order == "disposition_first" else late_issue)
            assert entered.wait(10)
            second = pool.submit(late_issue if order == "disposition_first" else dispose)
            _wait_for_pg_blocker(base[8], holder["pid"], "transactionid")
            release.set()
            first.result(timeout=15)
            if order == "disposition_first":
                second.result(timeout=15)
                assert (
                    service.get_issue_history(actor, base[5], cmd.review_issue_id).status
                    == "ADDRESSED"
                )
                # Later and even backdated concern metadata cannot rewrite admitted history.
                assert service.get_issue_history(actor, base[5], inserted).status == "OPEN"
            else:
                with pytest.raises(ResearchBaseError) as caught:
                    second.result(timeout=15)
                assert caught.value.code == ErrorCode.INVALID_STATE_TRANSITION
    finally:
        release.set()
        event.remove(base[8], "after_cursor_execute", pause)


@pytest.mark.parametrize("wait_at", ["inventory", "request", "review", "issue"])
def test_expiry_after_each_admission_wait_denies_without_partial_write(revision_env, wait_at):
    from datetime import timedelta

    service, actor, cmd, base, _ = disposition_case(revision_env)
    expiry = None
    original = base[-1].is_valid

    def credential(principal, at):
        return original(principal, at) and (expiry is None or at < expiry)

    base[-1].is_valid = credential
    with ThreadPoolExecutor(max_workers=1) as pool:
        with base[8].begin() as holder:
            pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
            if wait_at == "inventory":
                holder.execute(text("LOCK TABLE projects IN ROW EXCLUSIVE MODE"))
                lock_kind = "relation"
            elif wait_at == "request":
                holder.execute(
                    text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
                    {"key": f"b08:disposition:{cmd.id}"},
                )
                lock_kind = "advisory"
            elif wait_at == "review":
                holder.execute(
                    text("SELECT id FROM internal_review_records WHERE id=:id FOR UPDATE"),
                    {"id": cmd.re_review_record_id},
                )
                lock_kind = "transactionid"
            else:
                holder.execute(
                    text("SELECT id FROM review_issues WHERE id=:id FOR UPDATE"),
                    {"id": cmd.review_issue_id},
                )
                lock_kind = "transactionid"
            started = holder.execute(text("SELECT clock_timestamp()")).scalar_one()
            expiry = started + timedelta(seconds=1)
            future = pool.submit(service.record_issue_disposition, actor, cmd)
            witness = _wait_for_pg_blocker(base[8], pid, lock_kind)
            holder.execute(
                text(
                    "SELECT pg_sleep(GREATEST(0,EXTRACT(EPOCH FROM (:expiry-clock_timestamp()))+0.05))"
                ),
                {"expiry": expiry},
            )
            acquired_after = holder.execute(text("SELECT clock_timestamp()")).scalar_one()
            assert started < expiry <= acquired_after and witness["observed_at"] < acquired_after
        with pytest.raises(ResearchBaseError) as caught:
            future.result(timeout=15)
        assert caught.value.code == ErrorCode.FORBIDDEN
    with base[8].connect() as conn:
        assert (
            conn.execute(
                text("SELECT count(*) FROM review_issue_events WHERE prior_status='OPEN'")
            ).scalar_one()
            == 0
        )


@pytest.mark.parametrize("reader", ["history", "disposition"])
def test_snapshot_reader_rechecks_scheduled_expiry_at_fresh_database_time(revision_env, reader):
    from datetime import timedelta

    service, actor, cmd, base, _ = disposition_case(revision_env)
    service.record_issue_disposition(actor, cmd)
    original = base[-1].is_valid
    with base[8].connect() as conn:
        expiry = conn.execute(text("SELECT clock_timestamp()")).scalar_one() + timedelta(seconds=1)
    base[-1].is_valid = lambda principal, at: original(principal, at) and at < expiry
    advanced = []

    def advance(conn, cursor, statement, parameters, context, many):
        if not advanced and (
            "SELECT e.*,r.project_id FROM review_issue_events" in statement
            or "SELECT b08_check_history" in statement
        ):
            advanced.append(True)
            conn.execute(
                text(
                    "SELECT pg_sleep(GREATEST(0,EXTRACT(EPOCH FROM (:expiry-clock_timestamp()))+0.05))"
                ),
                {"expiry": expiry},
            )

    event.listen(base[8], "after_cursor_execute", advance)
    try:
        with pytest.raises(ResearchBaseError) as caught:
            if reader == "history":
                service.get_issue_history(actor, base[5], cmd.review_issue_id)
            else:
                service.get_issue_disposition(actor, base[5], cmd.id)
        assert caught.value.code == ErrorCode.FORBIDDEN and advanced
    finally:
        event.remove(base[8], "after_cursor_execute", advance)


@pytest.mark.parametrize("mutation", ["role", "validity", "evidence", "source"])
@pytest.mark.parametrize("order", ["disposition_first", "mutation_first"])
def test_actual_mutable_writers_both_commit_orders(revision_env, mutation, order):
    from researchbase.application.phase2_identity import CloseProjectRole
    from tests.integration.phase2.b08_support import changed_case
    from tests.integration.phase2.test_pr2_00_challenges import _service as identity_service
    from tests.integration.phase2.test_pr2_15_decision import _stale

    service, actor, cmd, base, action = (
        changed_case(revision_env, "SOURCE_CHANGE")
        if mutation in {"source", "evidence"}
        else disposition_case(revision_env)
    )
    expected_source_current = None
    source_reservations = []
    if mutation == "role":
        identity, _, _ = identity_service(str(base[8].url))
        identity._uow_factory = base[1]
        with base[8].connect() as conn:
            role = conn.execute(
                text(
                    "SELECT id FROM project_role_assignments WHERE actor_id=:actor AND project_id=:project AND role='OWNER' AND effective_until IS NULL"
                ),
                {"actor": actor.actor_id, "project": base[5]},
            ).scalar_one()

        def mutate_role():
            return identity.close_project_role(
                CloseProjectRole(base[3], base[5], role, "Current owner closed", uuid4())
            )

        mutate = mutate_role
        marker = "UPDATE project_role_assignments"
    elif mutation == "validity":

        def mutate_validity():
            return _stale(revision_env[2])

        mutate = mutate_validity
        marker = "INSERT INTO impact_assessments"
    elif mutation == "evidence":
        with base[8].connect() as conn:
            evidence = conn.execute(
                text("SELECT id FROM literature_evidence WHERE source_version_id=:id"),
                {"id": action.result_source_version_id},
            ).scalar_one()

        def mutate_evidence():
            return base[2].review(
                base[4], base[5], evidence, "DISPUTED", "New evidence concern", uuid4()
            )

        mutate = mutate_evidence
        marker = "INSERT INTO literature_evidence_review_events"
    else:
        from uuid import UUID

        from researchbase.application.source_version import (
            CreateSourceVersion,
            SourceVersionService,
            TransitionSourceVersion,
            _material_from_row,
        )
        from researchbase.domain.source_version import FrozenSourceReference, SourceVersionKind

        sources = SourceVersionService(base[1], base[-1])
        with base[1]() as uow:
            previous = uow.source_version.version(action.result_source_version_id)
            material = replace(
                _material_from_row(uow.source_version, previous),
                version_kind=SourceVersionKind.RETRACTED,
                predecessor_source_version=FrozenSourceReference(
                    previous["id"], previous["content_hash"]
                ),
            )
        draft = sources.create(CreateSourceVersion(base[3], base[5], material, uuid4()))
        expected_source_current = (
            previous["literature_source_id"],
            UUID(str(draft["source_version_id"])),
        )

        def mutate_source():
            return sources.freeze(
                TransitionSourceVersion(
                    base[3], base[5], UUID(str(draft["source_version_id"])), uuid4()
                )
            )

        mutate = mutate_source
        # Keep the pause BEFORE the current-pointer UPDATE. The regression must
        # exercise the formerly unsafe partial-freeze point, not hide its cycle.
        marker = "UPDATE source_versions"
    entered, release = Event(), Event()
    holder = {}

    def dispose():
        return service.record_issue_disposition(actor, cmd)

    def pause(conn, cursor, statement, parameters, context, many):
        if statement == "LOCK TABLE literature_sources,source_versions IN ROW EXCLUSIVE MODE":
            source_reservations.append(statement)
        if get_ident() != holder.get("thread") or entered.is_set():
            return
        matched = (
            statement.startswith("LOCK TABLE ")
            if order == "disposition_first"
            else marker in statement
        )
        if matched:
            holder["pid"] = conn.connection.driver_connection.info.backend_pid
            entered.set()
            assert release.wait(10)

    def first_write():
        holder["thread"] = get_ident()
        return dispose() if order == "disposition_first" else mutate()

    event.listen(base[8], "after_cursor_execute", pause)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(first_write)
            assert entered.wait(10)
            second = pool.submit(mutate if order == "disposition_first" else dispose)
            _wait_for_pg_blocker(base[8], holder["pid"], "relation")
            release.set()
            first.result(timeout=15)
            if order == "disposition_first":
                second.result(timeout=15)
            else:
                with pytest.raises(ResearchBaseError) as caught:
                    second.result(timeout=15)
                assert caught.value.code == (
                    ErrorCode.FORBIDDEN
                    if mutation == "role"
                    else ErrorCode.PROVENANCE_CLOSURE_VIOLATION
                )
    finally:
        release.set()
        event.remove(base[8], "after_cursor_execute", pause)
    with base[8].connect() as conn:
        if expected_source_current is not None:
            assert len(source_reservations) == 1
            assert (
                conn.execute(
                    text("SELECT current_version_id FROM literature_sources WHERE id=:id"),
                    {"id": expected_source_current[0]},
                ).scalar_one()
                == expected_source_current[1]
            )
        assert conn.execute(
            text("SELECT count(*) FROM review_issue_events WHERE id=:id"), {"id": cmd.id}
        ).scalar_one() == (1 if order == "disposition_first" else 0)


@pytest.mark.parametrize("order", ["disposition_first", "mapping_first"])
def test_new_mapping_and_disposition_never_invert_action_and_issue_locks(revision_env, order):
    from researchbase.application.revision_action import RecordConcernReReviewCommand

    service, actor, cmd, base, _ = disposition_case(revision_env)
    review = service.create(
        actor,
        base[5],
        "SCIENTIFIC_CONCLUSION_VERSION",
        revision_env[4].version_id,
        "SCIENTIFIC",
        "ACCEPT",
        "Additional independent review",
        (),
        uuid4(),
    )

    def map_review():
        return revision_env[0].record_concern_re_review(
            actor, RecordConcernReReviewCommand(base[5], cmd.revision_action_id, review.id)
        )

    def dispose():
        return service.record_issue_disposition(actor, cmd)

    entered, release = Event(), Event()
    holder = {}

    def first_write():
        holder["thread"] = get_ident()
        return dispose() if order == "disposition_first" else map_review()

    def pause(conn, cursor, statement, parameters, context, many):
        if get_ident() == holder.get("thread") and not entered.is_set():
            match = (
                statement.startswith("INSERT INTO review_issue_events")
                if order == "disposition_first"
                else statement.startswith("SELECT id FROM revision_actions")
                and "FOR UPDATE" in statement
            )
            if match:
                holder["pid"] = conn.connection.driver_connection.info.backend_pid
                entered.set()
                assert release.wait(10)

    event.listen(base[8], "after_cursor_execute", pause)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(first_write)
            assert entered.wait(10)
            second = pool.submit(map_review if order == "disposition_first" else dispose)
            _wait_for_pg_blocker(
                base[8],
                holder["pid"],
                "relation" if order == "disposition_first" else "transactionid",
            )
            release.set()
            assert first.result(timeout=15)
            assert second.result(timeout=15)
    finally:
        release.set()
        event.remove(base[8], "after_cursor_execute", pause)


@pytest.mark.parametrize("order", ["primary_first", "secondary_first"])
def test_sorted_mixed_issue_pass_serializes_selected_concern_disposition(revision_env, order):
    from researchbase.application.decision import RecordRevisionDecisionCommand
    from researchbase.application.internal_review import (
        RecordIssueDispositionCommand,
        ReviewIssueRequest,
    )
    from researchbase.application.revision_action import (
        RecordConcernReReviewCommand,
        RecordRevisionActionCommand,
    )

    service, actor, primary, base, _ = disposition_case(
        revision_env, issues=(ReviewIssueRequest("MAJOR", "OTHER", "Selected concern"),)
    )
    selected = service.read(actor, base[5], primary.re_review_record_id)
    secondary_issue = selected.issues[0].id
    d = revision_env[2][0].record_revision_decision(
        actor,
        RecordRevisionDecisionCommand(
            uuid4(),
            base[5],
            secondary_issue,
            "Accept unchanged?",
            "Exact selected concern",
            "ACCEPT_NO_CHANGE",
        ),
    )
    action = revision_env[0].record_revision_action(
        base[3], RecordRevisionActionCommand(uuid4(), base[5], "NO_CHANGE", decision_record_id=d.id)
    )
    review = service.create(
        actor,
        base[5],
        "SCIENTIFIC_CONCLUSION_VERSION",
        selected.target_id,
        "SCIENTIFIC",
        "ACCEPT",
        "Independent no-change re-review",
        (),
        uuid4(),
    )
    revision_env[0].record_concern_re_review(
        actor, RecordConcernReReviewCommand(base[5], action.id, review.id)
    )
    secondary = RecordIssueDispositionCommand(
        uuid4(),
        base[5],
        secondary_issue,
        "DISMISSED",
        action.id,
        review.id,
        "Attest selected concern dismissed",
        d.id,
    )
    entered, release = Event(), Event()
    holder = {}

    def run(command, first=False):
        if first:
            holder["thread"] = get_ident()
        return service.record_issue_disposition(actor, command)

    def pause(conn, cursor, statement, parameters, context, many):
        if (
            get_ident() == holder.get("thread")
            and not entered.is_set()
            and "SELECT a.* FROM revision_actions" in statement
        ):
            holder["pid"] = conn.connection.driver_connection.info.backend_pid
            entered.set()
            assert release.wait(10)

    event.listen(base[8], "after_cursor_execute", pause)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(run, primary if order == "primary_first" else secondary, True)
            assert entered.wait(10)
            second = pool.submit(run, secondary if order == "primary_first" else primary)
            _wait_for_pg_blocker(base[8], holder["pid"], "transactionid")
            release.set()
            if order == "primary_first":
                with pytest.raises(ResearchBaseError) as caught:
                    first.result(timeout=15)
                assert caught.value.code == ErrorCode.INVALID_STATE_TRANSITION
            else:
                assert first.result(timeout=15)
            assert second.result(timeout=15)
    finally:
        release.set()
        event.remove(base[8], "after_cursor_execute", pause)


@pytest.mark.parametrize("order", ["disposition_first", "release_first"])
def test_release_and_disposition_keep_independent_blocker_gate_both_orders(revision_env, order):
    from researchbase.application.decision import RecordDecisionCommand
    from tests.integration.phase2.b08_support import current_disposition_case

    service, actor, cmd, base, _ = current_disposition_case(revision_env, dismiss=True)
    release_command = RecordDecisionCommand(
        uuid4(), base[5], revision_env[4].version_id, "Proceed?", "Independent release basis"
    )

    def release_decision():
        return revision_env[2][0].record_decision(actor, release_command)

    def dispose():
        return service.record_issue_disposition(actor, cmd)

    entered, release = Event(), Event()
    holder = {}

    def pause_after(conn, cursor, statement, parameters, context, many):
        if (
            order == "disposition_first"
            and get_ident() == holder.get("thread")
            and not entered.is_set()
            and statement.startswith("INSERT INTO review_issue_events")
        ):
            holder["pid"] = conn.connection.driver_connection.info.backend_pid
            entered.set()
            assert release.wait(10)

    def pause_before(conn, cursor, statement, parameters, context, many):
        if (
            order == "release_first"
            and get_ident() == holder.get("thread")
            and not entered.is_set()
            and "i.status='OPEN'" in statement
        ):
            holder["pid"] = conn.connection.driver_connection.info.backend_pid
            entered.set()
            assert release.wait(10)

    def run_first():
        holder["thread"] = get_ident()
        return dispose() if order == "disposition_first" else release_decision()

    event.listen(base[8], "after_cursor_execute", pause_after)
    event.listen(base[8], "before_cursor_execute", pause_before)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(run_first)
            assert entered.wait(10)
            second = pool.submit(release_decision if order == "disposition_first" else dispose)
            _wait_for_pg_blocker(base[8], holder["pid"], "relation")
            release.set()
            if order == "release_first":
                with pytest.raises(ResearchBaseError) as caught:
                    first.result(timeout=15)
                assert caught.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION
            else:
                assert first.result(timeout=15)
            assert second.result(timeout=15)
        assert release_decision().decision == "PROCEED"
    finally:
        release.set()
        event.remove(base[8], "after_cursor_execute", pause_after)
        event.remove(base[8], "before_cursor_execute", pause_before)


@pytest.mark.parametrize("order", ["disposition_first", "approval_first"])
def test_approval_and_disposition_both_orders_preserve_grant_gate(approval_env, order):
    from researchbase.application.approval import DecideApprovalCommand
    from researchbase.application.decision import RecordRevisionDecisionCommand
    from researchbase.application.internal_review import (
        RecordIssueDispositionCommand,
        ReviewIssueRequest,
    )
    from researchbase.application.revision_action import (
        RecordConcernReReviewCommand,
        RecordRevisionActionCommand,
        RevisionActionService,
    )

    approval, requester, approver, request, env = approval_env
    base = env[-1]
    actor = env[2]
    service = env[1]
    approval.request_approval(requester, request)
    old = service.create(
        actor,
        base[5],
        "SCIENTIFIC_CONCLUSION_VERSION",
        env[3].version_id,
        "SCIENTIFIC",
        "REJECT",
        "New exact blocker",
        (ReviewIssueRequest("BLOCKING", "OTHER", "Still open"),),
        uuid4(),
    )
    d = env[0].record_revision_decision(
        actor,
        RecordRevisionDecisionCommand(
            uuid4(), base[5], old.issues[0].id, "No change?", "Exact concern", "ACCEPT_NO_CHANGE"
        ),
    )
    revisions = RevisionActionService(base[1], base[-1], base[2])
    action = revisions.record_revision_action(
        base[3], RecordRevisionActionCommand(uuid4(), base[5], "NO_CHANGE", decision_record_id=d.id)
    )
    review = service.create(
        actor,
        base[5],
        "SCIENTIFIC_CONCLUSION_VERSION",
        env[3].version_id,
        "SCIENTIFIC",
        "ACCEPT",
        "Exact independent unchanged re-review",
        (),
        uuid4(),
    )
    revisions.record_concern_re_review(
        actor, RecordConcernReReviewCommand(base[5], action.id, review.id)
    )
    cmd = RecordIssueDispositionCommand(
        uuid4(),
        base[5],
        old.issues[0].id,
        "DISMISSED",
        action.id,
        review.id,
        "Attest explicit no-change dismissal",
        d.id,
    )
    approve_cmd = DecideApprovalCommand(uuid4(), base[5], request.id, "APPROVE", "Independent gate")

    def approve():
        return approval.decide_approval(approver, approve_cmd)

    def dispose():
        return service.record_issue_disposition(actor, cmd)

    entered, release = Event(), Event()
    holder = {}

    def pause(conn, cursor, statement, parameters, context, many):
        if get_ident() != holder.get("thread") or entered.is_set():
            return
        match = (
            statement.startswith("INSERT INTO review_issue_events")
            if order == "disposition_first"
            else "i.status='OPEN'" in statement
        )
        if match:
            holder["pid"] = conn.connection.driver_connection.info.backend_pid
            entered.set()
            assert release.wait(10)

    def run_first():
        holder["thread"] = get_ident()
        return dispose() if order == "disposition_first" else approve()

    event.listen(
        base[8],
        "after_cursor_execute" if order == "disposition_first" else "before_cursor_execute",
        pause,
    )
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(run_first)
            assert entered.wait(10)
            second = pool.submit(approve if order == "disposition_first" else dispose)
            # B09's input SHARE locks serialize the approval gate with the
            # disposition writer. Witness that wait before releasing the holder.
            _wait_for_pg_blocker(base[8], holder["pid"], "relation")
            release.set()
            if order == "disposition_first":
                assert first.result(timeout=15)
                assert second.result(timeout=15).grant is not None
            else:
                with pytest.raises(ResearchBaseError) as caught:
                    first.result(timeout=15)
                assert caught.value.code == ErrorCode.APPROVAL_GATE_FAILED
                assert second.result(timeout=15)
                with base[8].connect() as conn:
                    assert (
                        conn.execute(text("SELECT count(*) FROM approval_grants")).scalar_one() == 0
                    )
        assert approve().grant is not None
    finally:
        release.set()
        event.remove(
            base[8],
            "after_cursor_execute" if order == "disposition_first" else "before_cursor_execute",
            pause,
        )


@pytest.mark.parametrize("operation", ["source_create", "source_update", "document_import"])
@pytest.mark.parametrize("order", ["disposition_first", "owner_first"])
def test_same_actor_writers_reserve_before_authority_and_event_fk(revision_env, operation, order):
    """An unrelated write by the disposer must not deadlock its event actor FK."""
    service, actor, cmd, base, _ = disposition_case(revision_env)
    if operation == "document_import":

        def import_document():
            return base[2].import_document(
                actor,
                base[5],
                b"Unrelated B08 writer document",
                "text/plain",
                "Test local rights",
                uuid4(),
            )

        owning_write = import_document
        reservation = "LOCK TABLE artifact_versions,artifacts IN ROW EXCLUSIVE MODE"
    else:
        from uuid import UUID

        from researchbase.application.source_version import (
            CreateSourceVersion,
            SourceVersionService,
            UpdateSourceVersionDraft,
            _material_from_row,
        )
        from researchbase.domain.source_version import FrozenSourceReference, SourceVersionKind

        sources = SourceVersionService(base[1], base[-1])
        with base[1]() as uow:
            previous = uow.source_version.version(base[7])
            material = replace(
                _material_from_row(uow.source_version, previous),
                version_kind=SourceVersionKind.OTHER,
                title="Unrelated source draft",
                predecessor_source_version=FrozenSourceReference(
                    previous["id"], previous["content_hash"]
                ),
            )
        if operation == "source_create":

            def create_source():
                return sources.create(CreateSourceVersion(actor, base[5], material, uuid4()))

            owning_write = create_source
        else:
            draft = sources.create(CreateSourceVersion(actor, base[5], material, uuid4()))

            def update_source():
                return sources.update(
                    UpdateSourceVersionDraft(
                        actor,
                        base[5],
                        UUID(str(draft["source_version_id"])),
                        replace(material, title="Updated unrelated draft"),
                        uuid4(),
                    )
                )

            owning_write = update_source
        reservation = "LOCK TABLE source_versions IN ROW EXCLUSIVE MODE"
    entered, release = Event(), Event()
    holder = {}
    owner_statements = []

    def owner():
        holder["owner_thread"] = get_ident()
        return owning_write()

    def dispose():
        return service.record_issue_disposition(actor, cmd)

    def first_write():
        holder["first_thread"] = get_ident()
        return dispose() if order == "disposition_first" else owner()

    def pause(conn, cursor, statement, parameters, context, many):
        if get_ident() == holder.get("owner_thread"):
            owner_statements.append(statement)
        if get_ident() != holder.get("first_thread") or entered.is_set():
            return
        match = (
            statement.startswith("LOCK TABLE ")
            if order == "disposition_first"
            else "FORUPDATEOFa,m,r,b" in "".join(statement.split())
        )
        if match:
            holder["pid"] = conn.connection.driver_connection.info.backend_pid
            entered.set()
            assert release.wait(10)

    event.listen(base[8], "after_cursor_execute", pause)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(first_write)
            assert entered.wait(10)
            second = pool.submit(owner if order == "disposition_first" else dispose)
            witness = _wait_for_pg_blocker(base[8], holder["pid"], "relation")
            assert witness["pid"] != holder["pid"]
            release.set()
            assert first.result(timeout=15)
            assert second.result(timeout=15)
    finally:
        release.set()
        event.remove(base[8], "after_cursor_execute", pause)
    authority_index = next(
        i for i, sql in enumerate(owner_statements) if "FORUPDATEOFa,m,r,b" in "".join(sql.split())
    )
    assert owner_statements.index(reservation) < authority_index
    assert service.get_issue_disposition(actor, base[5], cmd.id).id == cmd.id
