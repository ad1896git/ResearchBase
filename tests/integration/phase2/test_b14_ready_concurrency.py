"""Observed PostgreSQL lock ordering, races, snapshot reads and bounded UoW retries."""

# SQL assertions retain the reviewed literal lock/guard protocol.
# ruff: noqa: E501

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Barrier, Event
from uuid import uuid4

import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import DBAPIError

from researchbase.application.internal_review import ReviewIssueRequest
from researchbase.application.publication import GetPublicationReadyTransitionQuery
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.approval_repository import B13_SHARE_SQL, SqlAlchemyApprovalRepository
from researchbase.persistence.publication_repository import SqlAlchemyPublicationRepository
from tests.integration.phase2.test_b14_publication_ready import (
    b04_env,
    b05_env,
    conclusion_env,
    counts,
    create,
    decision_env,
    issued,
    phase2_database_url,
    revision_env,
)
from tests.integration.phase2.test_pr2_14_internal_review import _wait_for_pg_blocker

_FIXTURES = (b04_env, b05_env, conclusion_env, phase2_database_url, decision_env, revision_env)
pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)
pytestmark = pytest.mark.integration


# SSI predicate locks can survive a prior SERIALIZABLE transaction on a pooled
# backend. They never exclude another transaction; only the modes below violate
# the read contract. PostgreSQL 18 §13.2.3 documents this distinction.
_READ_EXCLUSION_SQL = """SELECT locktype,mode FROM pg_locks
 WHERE pid=pg_backend_pid() AND (
 locktype='advisory' OR (locktype='tuple' AND mode<>'SIReadLock')
 OR (locktype='relation' AND mode NOT IN ('AccessShareLock','SIReadLock')))"""


def test_first_sql_and_read_locks_are_exact(b05_env, monkeypatch):
    env = b05_env
    app, cmd, _, _ = issued(env)
    statements, locks = [], []
    writer_pids = set()
    # Keep a read/write SERIALIZABLE transaction overlapping the effect so the
    # writer's predicate locks deterministically survive its commit.
    overlap = (
        env[5]
        .connect()
        .execution_options(isolation_level="SERIALIZABLE", postgresql_readonly=False)
    )
    overlap.execute(text("SELECT count(*) FROM publications"))

    def capture(conn, cursor, sql, params, context, many):
        if cursor.connection.isolation_level.name == "SERIALIZABLE":
            writer_pids.add(cursor.connection.info.backend_pid)
        statements.append(
            (sql, cursor.connection.isolation_level.name, cursor.connection.read_only)
        )

    event.listen(env[5], "before_cursor_execute", capture)
    try:
        saved = app.transition_publication_ready(env[2], cmd)
        writer = [s for s, i, _ in statements if i == "SERIALIZABLE"]
        assert writer[:3] == [
            B13_SHARE_SQL,
            "LOCK TABLE publications IN SHARE ROW EXCLUSIVE MODE",
            "LOCK TABLE approval_decisions,approval_request_reviews,approval_requests IN SHARE MODE",
        ]
        target = next(
            i for i, s in enumerate(writer) if "FROM manuscript_versions" in s and "FOR UPDATE" in s
        )
        parent = next(
            i for i, s in enumerate(writer) if "FROM publications" in s and "FOR UPDATE" in s
        )
        assert target < parent
        assert len(writer_pids) == 1
        # Observe retained writer locks from the already-overlapping backend,
        # outside the readback statement capture. They must not be attributed to
        # a subsequent REPEATABLE READ transaction using the same pooled backend.
        event.remove(env[5], "before_cursor_execute", capture)
        predicates = overlap.execute(
            text("SELECT locktype,mode FROM pg_locks WHERE pid=:pid AND mode='SIReadLock'"),
            {"pid": next(iter(writer_pids))},
        ).all()
        assert predicates
        event.listen(env[5], "before_cursor_execute", capture)
        statements.clear()
        original = SqlAlchemyPublicationRepository.ready_event

        def observe(self, *args):
            locks.extend(self._session.execute(text(_READ_EXCLUSION_SQL)).all())
            return original(self, *args)

        monkeypatch.setattr(SqlAlchemyPublicationRepository, "ready_event", observe)
        assert app.transition_publication_ready(env[2], cmd) == saved
        assert (
            app.get_publication_ready_transition(
                env[2], GetPublicationReadyTransitionQuery(cmd.project_id, saved.id)
            ).consumption
            == saved
        )
        assert all(i == "REPEATABLE_READ" and r for _, i, r in statements)
        assert not locks
        assert not any(
            t in s.upper()
            for s, _, _ in statements
            for t in ("LOCK TABLE", "PG_ADVISORY", "FOR SHARE", "FOR UPDATE")
        )
    finally:
        if event.contains(env[5], "before_cursor_execute", capture):
            event.remove(env[5], "before_cursor_execute", capture)
        overlap.close()


@pytest.mark.parametrize("lock", ["advisory", "row", "table"])
def test_read_lock_observer_detects_real_exclusion(b05_env, lock):
    env = b05_env
    with env[5].connect() as connection:
        if lock == "advisory":
            connection.execute(text("SELECT pg_advisory_xact_lock(914062)"))
        elif lock == "row":
            connection.execute(text("SELECT id FROM publications FOR UPDATE"))
        else:
            connection.execute(text("LOCK TABLE publications IN SHARE UPDATE EXCLUSIVE MODE"))
        observed = connection.execute(text(_READ_EXCLUSION_SQL)).all()
        assert observed
        assert any(
            kind == "advisory"
            if lock == "advisory"
            else mode == ("RowShareLock" if lock == "row" else "ShareUpdateExclusiveLock")
            for kind, mode in observed
        )


@pytest.mark.parametrize("race", ["same", "changed", "two_keys"])
def test_racing_commands_have_one_effect(b05_env, race):
    env = b05_env
    app, cmd, _, _ = issued(env)
    other = (
        cmd
        if race == "same"
        else replace(cmd, result_id=uuid4())
        if race == "changed"
        else replace(cmd, command_key=uuid4())
    )
    barrier = Barrier(2)

    def run(command):
        barrier.wait(5)
        try:
            return app.transition_publication_ready(env[2], command)
        except ResearchBaseError as error:
            return error.code

    with ThreadPoolExecutor(2) as pool:
        results = [f.result(20) for f in (pool.submit(run, cmd), pool.submit(run, other))]
    if race == "same":
        assert results[0] == results[1]
    elif race == "two_keys":
        assert ErrorCode.GRANT_INVALID in results
    else:
        assert any(
            r in {ErrorCode.IDEMPOTENCY_CONFLICT, ErrorCode.APPROVAL_PURPOSE_TARGET_COMMAND_INVALID}
            for r in results
        )
    assert counts(env) == (1, 3, 2)


@pytest.mark.parametrize("state,attempts", [("40001", 3), ("40P01", 3), ("55P03", 1), ("57014", 1)])
def test_whole_uow_retry_limit(b05_env, monkeypatch, state, attempts):
    env = b05_env
    app, cmd, _, _ = issued(env)
    sessions = []

    class DriverFailure(Exception):
        sqlstate: str

    def fail(self, *args):
        sessions.append(self._session)
        orig = DriverFailure("injected")
        orig.sqlstate = state
        raise DBAPIError("injected", None, orig)

    monkeypatch.setattr(SqlAlchemyPublicationRepository, "transition_ready", fail)
    with pytest.raises(ResearchBaseError) as error:
        app.transition_publication_ready(env[2], cmd)
    assert error.value.code == ErrorCode.CONCURRENT_MODIFICATION
    assert len(sessions) == attempts and len({id(s) for s in sessions}) == attempts
    assert counts(env) == (0, 2, 1)


@pytest.mark.parametrize(
    "table",
    [
        "internal_review_records",
        "review_issues",
        "audit_findings",
        "project_role_assignments",
        "manuscript_versions",
        "approval_decisions",
    ],
)
def test_pre_snapshot_wait_rechecks_actual_issuer_credential(b05_env, table):
    env = b05_env
    app, cmd, _, approver = issued(env)
    with env[5].connect() as holder, ThreadPoolExecutor(1) as pool:
        holder.execute(text(f"LOCK TABLE {table} IN ROW EXCLUSIVE MODE"))
        pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
        future = pool.submit(app.transition_publication_ready, env[2], cmd)
        _wait_for_pg_blocker(env[5], pid, "relation")
        del env[9].principals[approver.actor_id]
        holder.rollback()
        with pytest.raises(ResearchBaseError) as error:
            future.result(15)
        assert error.value.code == ErrorCode.GRANT_STALE
    assert counts(env) == (0, 2, 1)


@pytest.mark.parametrize("ready_first", [False, True])
def test_zero_issue_review_insert_phantom_both_commit_orders(b05_env, monkeypatch, ready_first):
    env = b05_env
    app, cmd, _, _ = issued(env)
    entered, release = Event(), Event()
    holder = []
    original = SqlAlchemyPublicationRepository.transition_ready

    def pause(self, *args):
        holder.append(self._session.execute(text("SELECT pg_backend_pid()")).scalar_one())
        entered.set()
        assert release.wait(10)
        return original(self, *args)

    def pause_review(conn, cursor, sql, params, context, many):
        if sql.lstrip().upper().startswith("INSERT INTO INTERNAL_REVIEW_RECORDS"):
            holder.append(conn.execute(text("SELECT pg_backend_pid()")).scalar_one())
            entered.set()
            assert release.wait(10)

    def blocker():
        return create(env, issues=(ReviewIssueRequest("BLOCKING", "OTHER", "Racing concern"),))

    if ready_first:
        monkeypatch.setattr(SqlAlchemyPublicationRepository, "transition_ready", pause)
    else:
        event.listen(env[5], "after_cursor_execute", pause_review)
    try:
        with ThreadPoolExecutor(2) as pool:
            first = (
                pool.submit(app.transition_publication_ready, env[2], cmd)
                if ready_first
                else pool.submit(blocker)
            )
            assert entered.wait(10)
            second = (
                pool.submit(blocker)
                if ready_first
                else pool.submit(app.transition_publication_ready, env[2], cmd)
            )
            try:
                _wait_for_pg_blocker(env[5], holder[0], "relation")
            finally:
                release.set()
            first.result(15)
            if ready_first:
                second.result(15)
                assert counts(env) == (1, 3, 2)
            else:
                with pytest.raises(ResearchBaseError) as error:
                    second.result(15)
                assert error.value.code == ErrorCode.APPROVAL_GATE_FAILED
                assert counts(env) == (0, 2, 1)
    finally:
        release.set()
        if not ready_first:
            event.remove(env[5], "after_cursor_execute", pause_review)


def test_final_actual_issuer_credential_loss_rolls_back(b05_env, monkeypatch):
    env = b05_env
    app, cmd, _, approver = issued(env)
    original = SqlAlchemyApprovalRepository.force_constraints

    def revoke_after_check(self):
        original(self)
        del env[9].principals[approver.actor_id]

    monkeypatch.setattr(SqlAlchemyApprovalRepository, "force_constraints", revoke_after_check)
    with pytest.raises(ResearchBaseError) as error:
        app.transition_publication_ready(env[2], cmd)
    assert error.value.code == ErrorCode.GRANT_STALE and counts(env) == (0, 2, 1)


@pytest.mark.parametrize("wait_at", ["table", "scope", "target", "grant", "deferred"])
def test_required_real_wait_crosses_grant_expiry(b05_env, wait_at):
    from time import monotonic, sleep

    env = b05_env
    app, cmd, _, _ = issued(env, lifetime=2)
    with env[5].connect() as conn:
        until = conn.execute(
            text("SELECT valid_until FROM approval_grants WHERE id=:id"), {"id": cmd.grant_id}
        ).scalar_one()
    with env[5].connect() as holder, ThreadPoolExecutor(1) as pool:
        if wait_at == "table":
            holder.execute(text("LOCK TABLE internal_review_records IN ROW EXCLUSIVE MODE"))
        elif wait_at == "scope":
            holder.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
                {"key": f"pr216:scope:{cmd.project_id}:READY_FOR_SUBMISSION"},
            )
        elif wait_at == "target":
            holder.execute(
                text("SELECT id FROM manuscript_versions WHERE id=:id FOR UPDATE"),
                {"id": env[1].manuscript_version_id},
            )
        elif wait_at == "grant":
            holder.execute(
                text("SELECT id FROM approval_grants WHERE id=:id FOR UPDATE"), {"id": cmd.grant_id}
            )
        else:
            # Additional test constraint forces a genuine deferred wait; no production
            # guard is disabled or bypassed. The complete graph still must validate.
            with env[5].begin() as ddl:
                ddl.execute(
                    text(
                        "CREATE FUNCTION test_b14_deferred_wait() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN PERFORM pg_advisory_xact_lock(914062); RETURN NULL; END $$"
                    )
                )
                ddl.execute(
                    text(
                        "CREATE CONSTRAINT TRIGGER test_b14_wait AFTER INSERT ON approval_grant_consumptions DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION test_b14_deferred_wait()"
                    )
                )
            holder.execute(text("SELECT pg_advisory_xact_lock(914062)"))
        pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
        future = pool.submit(app.transition_publication_ready, env[2], cmd)
        witness = _wait_for_pg_blocker(
            env[5],
            pid,
            "relation"
            if wait_at == "table"
            else "advisory"
            if wait_at in {"scope", "deferred"}
            else "transactionid",
        )
        assert witness["pid"] != pid
        deadline = monotonic() + 5
        while True:
            with env[5].connect() as observer:
                at = observer.execute(text("SELECT clock_timestamp()")).scalar_one()
            if at >= until:
                break
            assert monotonic() < deadline
            sleep(0.01)
        holder.rollback()
        with pytest.raises(ResearchBaseError) as error:
            future.result(10)
        assert error.value.code == ErrorCode.GRANT_INVALID
    assert counts(env) == (0, 2, 1)


def test_real_legacy_target_first_deadlock_retries_one_effect(b05_env, monkeypatch):
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork

    env = b05_env
    app, cmd, _, _ = issued(env)
    original = SqlAlchemyApprovalRepository.lock_grant_chain
    normalize = SqlAlchemyUnitOfWork._command_database_error
    states, sessions = [], []

    def target(self, *args):
        sessions.append(self._session)
        self._session.execute(text("SET LOCAL deadlock_timeout='100ms'"))
        return original(self, *args)

    def observed(self, exc):
        states.append(getattr(exc.orig, "sqlstate", None))
        return normalize(self, exc)

    monkeypatch.setattr(SqlAlchemyApprovalRepository, "lock_grant_chain", target)
    monkeypatch.setattr(SqlAlchemyUnitOfWork, "_command_database_error", observed)
    with env[5].connect() as legacy:
        legacy.execute(text("SET LOCAL deadlock_timeout='5s'"))
        legacy.execute(
            text("SELECT id FROM manuscript_versions WHERE id=:id FOR UPDATE"),
            {"id": env[1].manuscript_version_id},
        )
        pid = legacy.execute(text("SELECT pg_backend_pid()")).scalar_one()
        with ThreadPoolExecutor(1) as pool:
            future = pool.submit(app.transition_publication_ready, env[2], cmd)
            try:
                _wait_for_pg_blocker(env[5], pid, "transactionid")
                legacy.execute(text("LOCK TABLE publications IN ROW EXCLUSIVE MODE"))
            finally:
                legacy.rollback()
            saved = future.result(15)
    assert "40P01" in states
    assert 2 <= len(sessions) <= 3 and len({id(s) for s in sessions}) == len(sessions)
    assert counts(env) == (1, 3, 2)
    assert app.transition_publication_ready(env[2], cmd) == saved


@pytest.mark.parametrize("concurrent", [False, True])
def test_two_grants_one_publication_one_winner_unused_permission_is_retained(b05_env, concurrent):
    from researchbase.application.approval import RequestApprovalCommand
    from tests.integration.phase2.test_b14r_ready_approval import decide

    env = b05_env
    app, cmd, approval, approver = issued(env)
    with env[5].connect() as conn:
        basis = conn.execute(
            text(
                "SELECT r.basis_decision_id FROM approval_grants g JOIN approval_decisions d ON d.id=g.approval_decision_id JOIN approval_requests r ON r.id=d.approval_request_id WHERE g.id=:id"
            ),
            {"id": cmd.grant_id},
        ).scalar_one()
    request = RequestApprovalCommand(
        uuid4(),
        cmd.project_id,
        None,
        basis,
        cmd.checked_review_ids,
        approval_purpose="READY_FOR_SUBMISSION",
        manuscript_version_id=env[1].manuscript_version_id,
    )
    approval.request_approval(env[2], request)
    second = approval.decide_approval(approver, decide(request)).grant
    assert second is not None
    other = replace(cmd, command_key=uuid4(), grant_id=second.id)

    def run(command):
        try:
            return app.transition_publication_ready(env[2], command)
        except ResearchBaseError as error:
            return error.code

    if concurrent:
        barrier = Barrier(2)

        def race(command):
            barrier.wait(5)
            return run(command)

        with ThreadPoolExecutor(2) as pool:
            results = [f.result(20) for f in (pool.submit(race, cmd), pool.submit(race, other))]
    else:
        results = [run(cmd), run(other)]
    assert sum(result == ErrorCode.APPROVAL_GATE_FAILED for result in results) == 1
    assert counts(env) == (1, 3, 3)
    with env[5].connect() as conn:
        assert sorted(conn.execute(text("SELECT status FROM approval_grants")).scalars()) == [
            "ACTIVE",
            "CONSUMED",
        ]
