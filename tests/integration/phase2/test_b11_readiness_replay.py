"""Immutable history stays readable without reapplying today's readiness gate."""

# SQL and independent literal hash vectors preserve contract spelling.
# ruff: noqa: E501

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import event, text

from researchbase.application.decision import GetReadyForSubmissionDecisionQuery
from researchbase.application.internal_review import ReviewIssueRequest
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.decision_repository import SqlAlchemyDecisionRepository
from tests.integration.phase2.test_b11_readiness_decision import (
    b04_env,
    b05_env,
    command,
    conclusion_env,
    create,
    phase2_database_url,
    read,
    record,
    seal,
    service,
)

_FIXTURES = (b04_env, b05_env, conclusion_env, phase2_database_url)
pytestmark = pytest.mark.integration


def test_restart_replay_and_new_adverse_blocker_history(b05_env):
    env = b05_env
    seal(env)
    create(env)
    cmd = command(env)
    saved = record(env, cmd)
    late = create(
        env,
        recommendation="REJECT",
        issues=(ReviewIssueRequest("BLOCKING", "OTHER", "New concern"),),
    )
    replay = record(env, cmd)
    assert replay.content_hash == saved.content_hash and replay.basis == saved.basis
    assert replay.current_blocking_issue_ids == (late.issues[0].id,)
    assert read(env, saved.id).content_hash == saved.content_hash
    for changed in (replace(cmd, rationale="Other"), replace(cmd, manuscript_version_id=uuid4())):
        with pytest.raises(ResearchBaseError) as exc:
            record(env, changed)
        assert exc.value.code == ErrorCode.IDEMPOTENCY_CONFLICT
    with pytest.raises(ResearchBaseError) as exc:
        record(env, cmd, env[2])
    assert exc.value.code == ErrorCode.FORBIDDEN


def test_different_uuid_scope_cannot_replace(b05_env):
    env = b05_env
    seal(env)
    create(env)
    saved = record(env)
    with pytest.raises(ResearchBaseError) as exc:
        record(env)
    assert exc.value.code == ErrorCode.IDEMPOTENCY_CONFLICT
    assert read(env, saved.id).content_hash == saved.content_hash


def test_lost_write_role_replay_read_and_lost_read_denial(b05_env):
    env = b05_env
    seal(env)
    create(env)
    cmd = command(env)
    saved = record(env, cmd)
    from researchbase.application.phase2_identity import AssignProjectRole, CloseProjectRole
    from tests.integration.phase2.test_pr2_15_decision import identity_service

    identity, _, _ = identity_service(env[5].url.render_as_string(hide_password=False))
    identity.assign_project_role(
        AssignProjectRole(
            env[3], env[1].project_id, env[3].actor_id, "VIEWER", "TEST ONLY", uuid4()
        )
    )

    def close_roles(roles):
        with env[5].connect() as conn:
            ids = conn.execute(
                text(
                    "SELECT id,role FROM project_role_assignments WHERE actor_id=:id AND effective_until IS NULL"
                ),
                {"id": env[3].actor_id},
            ).all()
        for identity_id, role in ids:
            if role in roles:
                identity.close_project_role(
                    CloseProjectRole(env[2], env[1].project_id, identity_id, "TEST ONLY", uuid4())
                )

    close_roles({"OWNER", "APPROVER"})
    assert record(env, cmd).content_hash == saved.content_hash
    with pytest.raises(ResearchBaseError) as exc:
        record(env)
    assert exc.value.code == ErrorCode.FORBIDDEN
    close_roles({"VIEWER", "RESEARCHER", "REVIEWER"})
    with pytest.raises(ResearchBaseError) as exc:
        read(env, saved.id)
    assert exc.value.code == ErrorCode.FORBIDDEN


def test_read_has_no_explicit_locks_in_nested_verifiers(b05_env, monkeypatch):
    env = b05_env
    seal(env)
    create(env)
    saved = record(env)
    statements = []

    def capture(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    original = SqlAlchemyDecisionRepository.applicable_manuscript_reviews
    observed = []

    def inspect(self, *args):
        rows = original(self, *args)
        assert (
            self._session.execute(text("SHOW transaction_isolation")).scalar_one()
            == "repeatable read"
        )
        assert self._session.execute(text("SHOW transaction_read_only")).scalar_one() == "on"
        observed.extend(
            self._session.execute(
                text(
                    "SELECT locktype,mode FROM pg_locks WHERE pid=pg_backend_pid() AND (locktype IN ('advisory','tuple') OR locktype='relation' AND mode IN ('ShareLock','RowShareLock','RowExclusiveLock','ShareRowExclusiveLock','ExclusiveLock','AccessExclusiveLock'))"
                )
            ).all()
        )
        return rows

    monkeypatch.setattr(SqlAlchemyDecisionRepository, "applicable_manuscript_reviews", inspect)
    event.listen(env[5], "before_cursor_execute", capture)
    try:
        assert read(env, saved.id).content_hash == saved.content_hash
    finally:
        event.remove(env[5], "before_cursor_execute", capture)
    assert not observed
    assert statements[0] == "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"
    assert not any(
        any(
            token in sql.upper()
            for token in ("LOCK TABLE", "FOR UPDATE", "FOR SHARE", "PG_ADVISORY")
        )
        for sql in statements
    )


def test_authorize_before_absence_and_foreign_scope(b05_env):
    env = b05_env
    seal(env)
    create(env)
    saved = record(env)
    for principal, query, code in (
        (
            object(),
            GetReadyForSubmissionDecisionQuery(env[1].project_id, uuid4()),
            ErrorCode.AUTHENTICATION_REQUIRED,
        ),
        (env[3], GetReadyForSubmissionDecisionQuery(uuid4(), saved.id), ErrorCode.FORBIDDEN),
        (
            env[3],
            GetReadyForSubmissionDecisionQuery(env[1].project_id, uuid4()),
            ErrorCode.NOT_FOUND,
        ),
    ):
        with pytest.raises(ResearchBaseError) as exc:
            service(env).get_ready_for_submission_decision(principal, query)
        assert exc.value.code == code


@pytest.mark.parametrize("changed", [False, True])
def test_named_primary_key_collision_reloads_fresh_history(b05_env, monkeypatch, changed):
    env = b05_env
    seal(env)
    create(env)
    cmd = command(env)
    saved = record(env, cmd)
    original = SqlAlchemyDecisionRepository.decision
    seen = []

    def hide_once(self, *args):
        seen.append(self._session)
        return None if len(seen) == 1 else original(self, *args)

    monkeypatch.setattr(SqlAlchemyDecisionRepository, "decision", hide_once)
    monkeypatch.setattr(SqlAlchemyDecisionRepository, "decision_exists", lambda *args: False)
    monkeypatch.setattr(SqlAlchemyDecisionRepository, "readiness_scope", lambda *args: None)
    if changed:
        with pytest.raises(ResearchBaseError) as exc:
            record(env, replace(cmd, rationale="Changed"))
        assert exc.value.code == ErrorCode.IDEMPOTENCY_CONFLICT
    else:
        assert record(env, cmd).content_hash == saved.content_hash
    assert len(seen) == 2 and seen[0] is not seen[1]
