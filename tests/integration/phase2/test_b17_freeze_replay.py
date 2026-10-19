"""Entitled immutable replay and transitive lock-free snapshot reads."""

# Literal SQL reads the exact current role inventory.
# ruff: noqa: E501

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import event

from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.b17_fixtures import (
    b04_env,
    b05_env,
    b17_env,
    conclusion_env,
    counts,
    decision_env,
    phase2_database_url,
    revision_env,
    withdraw_consent,
)

_FIXTURES = (
    b04_env,
    b05_env,
    b17_env,
    conclusion_env,
    decision_env,
    phase2_database_url,
    revision_env,
)
pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)
pytestmark = pytest.mark.integration


def test_replay_and_all_package_reads_have_no_transitive_locks(b17_env):
    f = b17_env
    receipt = f.app.freeze_prepared_submission(f.actor, f.command)
    before = counts(f)
    queries = []

    def capture(conn, cursor, statement, parameters, context, executemany):
        queries.append(statement.upper())

    event.listen(f.engine, "before_cursor_execute", capture)
    try:
        assert f.app.freeze_prepared_submission(f.actor, f.command) == receipt
        f.app.get_prepared_submission(f.actor, f.query)
        f.app.get_prepared_submission_history(f.actor, f.query)
        f.app.preview_prepared_submission(f.actor, f.query)
        f.approval.get_grant_consumption(f.actor, f.command.project_id, f.command.command_key)
    finally:
        event.remove(f.engine, "before_cursor_execute", capture)
    assert queries
    assert not any(
        any(
            token in query
            for token in (
                "LOCK TABLE",
                "PG_ADVISORY",
                "FOR UPDATE",
                "FOR SHARE",
                "INSERT INTO",
                "UPDATE PREPARED",
                "SET CONSTRAINTS",
            )
        )
        for query in queries
    )
    assert counts(f) == before


@pytest.mark.parametrize(
    "field", ["grant_id", "result_id", "expected_package_manifest_hash", "checked_review_ids"]
)
def test_changed_material_conflicts_without_effect(b17_env, field):
    f = b17_env
    f.app.freeze_prepared_submission(f.actor, f.command)
    before = counts(f)
    value = (
        "1" * 64
        if field == "expected_package_manifest_hash"
        else (uuid4(),)
        if field == "checked_review_ids"
        else uuid4()
    )
    with pytest.raises(ResearchBaseError) as exc:
        f.app.freeze_prepared_submission(f.actor, replace(f.command, **{field: value}))
    assert exc.value.code == ErrorCode.IDEMPOTENCY_CONFLICT
    assert counts(f) == before


def test_same_key_recovers_committed_result_after_consent_withdrawal(b17_env):
    f = b17_env
    saved = f.app.freeze_prepared_submission(f.actor, f.command)
    withdraw_consent(f)
    before = counts(f)
    assert f.app.freeze_prepared_submission(f.actor, f.command) == saved
    assert counts(f) == before


@pytest.mark.parametrize("retain_read", [False, True])
def test_completed_replay_needs_current_reader_but_no_writer(b17_env, retain_read):
    from sqlalchemy import text

    from researchbase.application.phase2_identity import AssignProjectRole, CloseProjectRole
    from tests.integration.phase2.test_pr2_00_challenges import _service

    f = b17_env
    saved = f.app.freeze_prepared_submission(f.actor, f.command)
    identity, _, _ = _service(f.engine.url.render_as_string(hide_password=False))
    if retain_read:
        identity.assign_project_role(
            AssignProjectRole(
                f.actor,
                f.command.project_id,
                f.actor.actor_id,
                "VIEWER",
                "Retained reader",
                uuid4(),
            )
        )
    with f.engine.connect() as conn:
        roles = (
            conn.execute(
                text(
                    "SELECT id FROM project_role_assignments WHERE actor_id=:actor AND project_id=:project AND role<>'VIEWER' AND effective_until IS NULL"
                ),
                {"actor": f.actor.actor_id, "project": f.command.project_id},
            )
            .scalars()
            .all()
        )
    for role in roles:
        identity.close_project_role(
            CloseProjectRole(f.actor, f.command.project_id, role, "Writer offboarding", uuid4())
        )
    if retain_read:
        assert f.app.freeze_prepared_submission(f.actor, f.command) == saved
    else:
        with pytest.raises(ResearchBaseError) as exc:
            f.app.freeze_prepared_submission(f.actor, f.command)
        assert exc.value.code == ErrorCode.FORBIDDEN


def test_expiry_precedes_missing_consent_and_digest_drift(b05_env):
    from time import monotonic, sleep

    from sqlalchemy import text

    from tests.integration.phase2.b17_fixtures import build

    f = build(b05_env, consent=False, lifetime=1)
    with f.engine.connect() as conn:
        expiry = conn.execute(
            text("SELECT valid_until FROM approval_grants WHERE id=:id"), {"id": f.command.grant_id}
        ).scalar_one()
    deadline = monotonic() + 5
    while True:
        with f.engine.connect() as conn:
            at = conn.execute(text("SELECT clock_timestamp()")).scalar_one()
        if at >= expiry:
            break
        assert monotonic() < deadline
        sleep(0.01)
    before = counts(f)
    with pytest.raises(ResearchBaseError) as exc:
        f.app.freeze_prepared_submission(
            f.actor, replace(f.command, expected_package_manifest_hash="f" * 64)
        )
    assert exc.value.code == ErrorCode.GRANT_INVALID and counts(f) == before


def test_altered_authorized_actor_conflicts_with_original_request(b17_env):
    f = b17_env
    f.app.freeze_prepared_submission(f.actor, f.command)
    with pytest.raises(ResearchBaseError) as exc:
        f.app.freeze_prepared_submission(f.env[3], f.command)
    assert exc.value.code == ErrorCode.IDEMPOTENCY_CONFLICT


def test_uncertain_commit_requires_explicit_same_key_recovery(b17_env, monkeypatch):
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork

    f = b17_env
    calls = []
    before = counts(f)
    commit = SqlAlchemyUnitOfWork.commit

    def lose_ack(self):
        commit(self)
        calls.append(self)
        raise RuntimeError("commit acknowledgement lost")

    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", lose_ack)
    with pytest.raises(RuntimeError, match="acknowledgement lost"):
        f.app.freeze_prepared_submission(f.actor, f.command)
    assert len(calls) == 1
    saved = f.app.freeze_prepared_submission(f.actor, f.command)
    assert saved.result_prepared_submission_version_id == f.command.result_id
    assert len(calls) == 1
    after = counts(f)
    assert after[3] == before[3] + 1 and after[2] == before[2] + 1


def test_exact_multi_review_permutations_replay_after_expiry(b05_env):
    from time import monotonic, sleep

    from sqlalchemy import text

    from tests.integration.phase2.b17_fixtures import build

    f = build(b05_env, lifetime=30, extra_reviews=1)
    reversed_command = replace(f.command, checked_review_ids=f.command.checked_review_ids[::-1])
    saved = f.app.freeze_prepared_submission(f.actor, reversed_command)
    with f.engine.connect() as conn:
        expiry, observed_at = conn.execute(
            text("SELECT valid_until,clock_timestamp() FROM approval_grants WHERE id=:id"),
            {"id": f.command.grant_id},
        ).one()
    deadline = monotonic() + max(0, (expiry - observed_at).total_seconds()) + 10
    while True:
        with f.engine.connect() as conn:
            at = conn.execute(text("SELECT clock_timestamp()")).scalar_one()
        if at >= expiry:
            break
        assert monotonic() < deadline
        sleep(0.01)
    before = counts(f)
    assert f.app.freeze_prepared_submission(f.actor, f.command) == saved
    assert f.app.freeze_prepared_submission(f.actor, reversed_command) == saved
    assert counts(f) == before
