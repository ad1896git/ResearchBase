"""Real failed waits followed by one entitled, read-only receipt lookup."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Event, get_ident
from uuid import uuid4

import pytest
from sqlalchemy import event, text

from researchbase.application.revision_action import RecordConcernReReviewCommand
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.test_b07_revision_decisions import decision_command
from tests.integration.phase2.test_b11_readiness_decision import (
    b04_env,
    b05_env,
    command,
    create,
    seal,
    service,
)
from tests.integration.phase2.test_pr2_14_internal_review import _wait_for_pg_blocker
from tests.integration.phase2.test_revision_action import (
    conclusion_env,
    decision_env,
    phase2_database_url,
    revision_env,
)

pytestmark = pytest.mark.integration
_FIXTURES = (b04_env, b05_env, conclusion_env, decision_env, phase2_database_url, revision_env)
OUTCOMES = ("replay", "changed", "revoked", "absent", "uncommitted")


def failed_wait_case(engine, credentials, write, read, outcome, changed=None):
    """A failed lock wait must roll back before looking for the winner's receipt."""
    entered, release = Event(), Event()
    timed_out, deliver_error = Event(), Event()
    holder = {}
    waiter = {}
    recovery_sql = []
    recovery_transactions = []
    waiting_command = changed if outcome == "changed" else None

    def pause(conn, cursor, statement, parameters, context, many):
        if get_ident() == waiter.get("thread") and timed_out.is_set():
            recovery_sql.append(statement)
        if get_ident() == waiter.get("thread") and "SET LOCAL statement_timeout" in statement:
            # Test-only acceleration of the real PostgreSQL 55P03 failure in CI.
            conn.execute(text("SET LOCAL lock_timeout='5s'"))
        if (
            statement.startswith(
                (
                    "INSERT INTO decision_records",
                    "INSERT INTO revision_actions",
                    "INSERT INTO revision_action_re_reviews",
                )
            )
            and not entered.is_set()
        ):
            holder["pid"] = conn.connection.driver_connection.info.backend_pid
            entered.set()
            assert release.wait(30)
            if outcome == "absent":
                raise RuntimeError("winner rolled back")

    def before_statement(conn, cursor, statement, parameters, context, many):
        if get_ident() == waiter.get("thread") and "pg_advisory_xact_lock" in statement:
            conn.execute(text("SET LOCAL lock_timeout='5s'"))

    def begin_recovery(conn):
        if get_ident() == waiter.get("thread") and timed_out.is_set():
            recovery_transactions.append(conn.get_execution_options().get("postgresql_readonly"))

    def failed_wait(context):
        if get_ident() == waiter.get("thread"):
            assert getattr(context.original_exception, "sqlstate", None) == "55P03"
            timed_out.set()
            assert deliver_error.wait(20)

    def follow():
        waiter["thread"] = get_ident()
        return write(waiting_command)

    event.listen(engine, "after_cursor_execute", pause)
    event.listen(engine, "handle_error", failed_wait)
    event.listen(engine, "before_cursor_execute", before_statement)
    event.listen(engine, "begin", begin_recovery)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            winner = pool.submit(write, None)
            try:
                assert entered.wait(10)
                pending = pool.submit(follow)
                witness = _wait_for_pg_blocker(engine, holder["pid"], "advisory")
                assert "pg_advisory_xact_lock" in witness["query"]
                assert timed_out.wait(10)
                if outcome == "uncommitted":
                    # The single snapshot must finish while the winner still
                    # holds its lock: no eventual-success or mutation retry loop.
                    deliver_error.set()
                    with pytest.raises(ResearchBaseError) as caught:
                        pending.result(timeout=10)
                    assert caught.value.code == ErrorCode.CONCURRENT_MODIFICATION
                    assert caught.value.details is None
                    assert not winner.done()
                # The waiter is still handling its failed SQL statement. Commit the
                # winner before allowing rollback and Application error handling.
                release.set()
                if outcome == "absent":
                    with pytest.raises(RuntimeError, match="winner rolled back"):
                        winner.result(timeout=15)
                    saved = None
                else:
                    saved = winner.result(timeout=15)
                if outcome == "revoked":
                    credentials.enabled = False
            finally:
                release.set()
                deliver_error.set()
            if outcome == "uncommitted":
                pass  # Already checked before releasing the winner.
            elif outcome == "replay":
                assert_receipt(pending.result(timeout=15), saved)
            else:
                with pytest.raises(ResearchBaseError) as caught:
                    pending.result(timeout=15)
                assert (
                    caught.value.code
                    == {
                        "changed": ErrorCode.IDEMPOTENCY_CONFLICT,
                        "revoked": ErrorCode.FORBIDDEN,
                        "absent": ErrorCode.CONCURRENT_MODIFICATION,
                    }[outcome]
                )
    finally:
        release.set()
        deliver_error.set()
        credentials.enabled = True
        event.remove(engine, "after_cursor_execute", pause)
        event.remove(engine, "handle_error", failed_wait)
        event.remove(engine, "before_cursor_execute", before_statement)
        event.remove(engine, "begin", begin_recovery)
    assert_receipt(read(), saved)
    assert recovery_transactions == [True]
    assert recovery_sql
    assert not any(
        token in sql.upper()
        for sql in recovery_sql
        for token in ("LOCK TABLE", "ADVISORY", "FOR UPDATE", "FOR SHARE", "INSERT", "UPDATE ")
    )
    assert sum("SET LOCAL statement_timeout" in sql for sql in recovery_sql) == 0


@pytest.mark.parametrize("outcome", OUTCOMES)
def test_revision_decision_failed_wait_receipt(revision_env, outcome):
    _, action, env, _, _ = revision_env
    base = env[-1]
    cmd = decision_command(env, action.review_issue_id)
    failed_wait_case(
        base[8],
        base[-1],
        lambda change: env[0].record_revision_decision(env[2], change or cmd),
        lambda: _optional(lambda: env[0].get_revision_decision(env[2], base[5], cmd.id)),
        outcome,
        replace(cmd, rationale="Changed material"),
    )


@pytest.mark.parametrize("outcome", OUTCOMES)
def test_revision_action_failed_wait_receipt(revision_env, outcome):
    revisions, cmd, env, _, _ = revision_env
    base = env[-1]
    failed_wait_case(
        base[8],
        base[-1],
        lambda change: revisions.record_revision_action(base[3], change or cmd),
        lambda: _optional(lambda: revisions.read_revision_action(base[3], base[5], cmd.id)),
        outcome,
        replace(cmd, result_scientific_conclusion_version_id=uuid4()),
    )


@pytest.mark.parametrize("outcome", ("replay", "revoked", "absent", "uncommitted"))
def test_concern_re_review_failed_wait_receipt(revision_env, outcome):
    revisions, action, env, _, revised = revision_env
    base = env[-1]
    revisions.record_revision_action(base[3], action)
    review = env[1].create(
        env[2],
        base[5],
        "SCIENTIFIC_CONCLUSION_VERSION",
        revised.version_id,
        "SCIENTIFIC",
        "REJECT",
        "Independent",
        (),
        uuid4(),
    )
    cmd = RecordConcernReReviewCommand(base[5], action.id, review.id)
    # Every material field is part of the exact pair key; there is no mutable
    # payload to conflict for this command. A different pair is a different key.
    failed_wait_case(
        base[8],
        base[-1],
        lambda change: revisions.record_concern_re_review(env[2], change or cmd, novelty=False),
        lambda: _optional(lambda: revisions.get_concern_re_review(env[2], cmd)),
        outcome,
    )


@pytest.mark.parametrize("outcome", OUTCOMES)
def test_readiness_decision_failed_wait_receipt(b05_env, outcome):
    env = b05_env
    seal(env)
    create(env)
    decisions = service(env)
    cmd = command(env)
    from researchbase.application.decision import GetReadyForSubmissionDecisionQuery

    failed_wait_case(
        env[5],
        env[9],
        lambda change: decisions.record_ready_for_submission_decision(env[3], change or cmd),
        lambda: _optional(
            lambda: decisions.get_ready_for_submission_decision(
                env[3], GetReadyForSubmissionDecisionQuery(cmd.project_id, cmd.id)
            )
        ),
        outcome,
        replace(cmd, rationale="Changed material"),
    )


def _optional(read):
    try:
        return read()
    except ResearchBaseError as error:
        if error.code != ErrorCode.NOT_FOUND:
            raise
        return None


def assert_receipt(actual, expected):
    # Readiness exposes the time of the fresh validity evaluation in addition
    # to immutable receipt material. Check both contracts explicitly.
    if expected is not None and hasattr(expected, "evaluated_at"):
        assert actual.evaluated_at >= expected.evaluated_at
        assert actual.evaluated_at.tzinfo is not None
        assert replace(actual, evaluated_at=expected.evaluated_at) == expected
    else:
        assert actual == expected
