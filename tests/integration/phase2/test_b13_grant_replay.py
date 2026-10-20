"""Entitled immutable replay is independent of current first-use gates."""

from dataclasses import replace
from uuid import uuid4

import pytest

from researchbase.application.approval import EvaluateApprovalGrantCommand
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.test_b13_grant_consumption import (
    approval_env as approval_env,
)
from tests.integration.phase2.test_b13_grant_consumption import (
    conclusion_env as conclusion_env,
)
from tests.integration.phase2.test_b13_grant_consumption import (
    counts,
    issued,
)
from tests.integration.phase2.test_b13_grant_consumption import (
    decision_env as decision_env,
)
from tests.integration.phase2.test_b13_grant_consumption import (
    phase2_database_url as phase2_database_url,
)

_FIXTURES = (approval_env, conclusion_env, decision_env, phase2_database_url)
pytestmark = pytest.mark.integration


def test_saved_replay_after_invalidity_and_service_restart(approval_env):
    from researchbase.application.scientific_conclusion import ScientificConclusionService
    from tests.integration.phase2.test_pr2_15_decision import _stale

    owner, actor, cmd, _ = issued(approval_env)
    result = owner.record_internal_scientific_release(actor, cmd)
    _stale(approval_env[-1])
    base = approval_env[-1][-1]
    restarted = ScientificConclusionService(base[1], base[9], base[2])
    assert restarted.record_internal_scientific_release(actor, cmd) == result
    assert (
        approval_env[0].get_grant_consumption(approval_env[2], cmd.project_id, cmd.command_key)
        == result
    )
    assert (
        approval_env[0]
        .evaluate_approval_grant(actor, EvaluateApprovalGrantCommand(cmd.project_id, cmd.grant_id))
        .grant.status
        == "CONSUMED"
    )


@pytest.mark.parametrize("field", ["grant_id", "result_id", "checked_review_ids"])
def test_changed_material_conflicts(approval_env, field):
    owner, actor, cmd, _ = issued(approval_env)
    owner.record_internal_scientific_release(actor, cmd)
    value = (uuid4(),) if field == "checked_review_ids" else uuid4()
    with pytest.raises(ResearchBaseError) as error:
        owner.record_internal_scientific_release(actor, replace(cmd, **{field: value}))
    assert error.value.code == ErrorCode.IDEMPOTENCY_CONFLICT
    assert counts(approval_env) == (1, 2, 1)


def test_other_actor_replay_forbidden_but_audit_read_allowed(approval_env):
    owner, actor, cmd, _ = issued(approval_env)
    result = owner.record_internal_scientific_release(actor, cmd)
    with pytest.raises(ResearchBaseError) as error:
        owner.record_internal_scientific_release(approval_env[2], cmd)
    assert error.value.code == ErrorCode.FORBIDDEN
    assert (
        approval_env[0].get_grant_consumption(approval_env[2], cmd.project_id, cmd.command_key)
        == result
    )


def test_different_key_cannot_reuse_consumed_grant(approval_env):
    owner, actor, cmd, _ = issued(approval_env)
    owner.record_internal_scientific_release(actor, cmd)
    with pytest.raises(ResearchBaseError) as error:
        owner.record_internal_scientific_release(actor, replace(cmd, command_key=uuid4()))
    assert error.value.code == ErrorCode.GRANT_INVALID


def test_credential_loss_denies_history(approval_env):
    owner, actor, cmd, _ = issued(approval_env)
    owner.record_internal_scientific_release(actor, cmd)
    del approval_env[-1][-1][9].principals[actor.actor_id]
    with pytest.raises(ResearchBaseError) as error:
        owner.record_internal_scientific_release(actor, cmd)
    assert error.value.code == ErrorCode.FORBIDDEN


@pytest.mark.parametrize(
    "corruption",
    ["creation", "terminal_actor", "terminal_time", "dto", "hash", "review_basis", "decision_hash"],
)
def test_corrupt_saved_history_fails_closed(approval_env, corruption):
    from sqlalchemy import text

    owner, actor, cmd, _ = issued(approval_env)
    owner.record_internal_scientific_release(actor, cmd)
    engine = approval_env[-1][-1][8]
    table = (
        "approval_grant_events"
        if corruption in {"creation", "terminal_actor", "terminal_time"}
        else "approval_request_reviews"
        if corruption == "review_basis"
        else "approval_decisions"
        if corruption == "decision_hash"
        else "approval_grant_consumptions"
    )
    # Privileged corruption injection only; normal-role immutable guards are tested separately.
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE " + table + " DISABLE TRIGGER ALL"))
        if corruption == "creation":
            conn.execute(text("DELETE FROM approval_grant_events WHERE prior_status IS NULL"))
        elif corruption == "terminal_actor":
            conn.execute(
                text(
                    "UPDATE approval_grant_events SET actor_id=:actor WHERE prior_status='ACTIVE'"
                ),
                {"actor": approval_env[2].actor_id},
            )
        elif corruption == "terminal_time":
            conn.execute(
                text(
                    "UPDATE approval_grant_events SET occurred_at=occurred_at-interval '1 second' "
                    "WHERE prior_status='ACTIVE'"
                )
            )
        elif corruption == "dto":
            conn.execute(text("UPDATE approval_grant_consumptions SET result_dto='{}'"))
        elif corruption == "hash":
            conn.execute(
                text("UPDATE approval_grant_consumptions SET request_hash=:hash"),
                {"hash": "0" * 64},
            )
        elif corruption == "decision_hash":
            conn.execute(
                text("UPDATE approval_decisions SET content_hash=:hash"), {"hash": "0" * 64}
            )
        else:
            conn.execute(text("DELETE FROM approval_request_reviews"))
        conn.execute(text("ALTER TABLE " + table + " ENABLE TRIGGER ALL"))
    with pytest.raises(ResearchBaseError) as error:
        owner.record_internal_scientific_release(actor, cmd)
    assert error.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION


def test_completed_replay_after_later_blocker(approval_env):
    from researchbase.application.internal_review import ReviewIssueRequest
    from tests.integration.phase2.test_pr2_15_decision import _review

    owner, actor, cmd, _ = issued(approval_env)
    saved = owner.record_internal_scientific_release(actor, cmd)
    _review(
        approval_env[-1], "REJECT", (ReviewIssueRequest("BLOCKING", "OVERCLAIM", "Later blocker"),)
    )
    assert owner.record_internal_scientific_release(actor, cmd) == saved


def test_write_role_loss_preserves_reader_replay(approval_env):
    from sqlalchemy import text

    from researchbase.application.phase2_identity import AssignProjectRole, CloseProjectRole
    from tests.integration.phase2.test_pr2_00_challenges import _service as identity_service

    owner, actor, cmd, _ = issued(approval_env)
    saved = owner.record_internal_scientific_release(actor, cmd)
    base = approval_env[-1][-1]
    identity, _, _ = identity_service(str(base[8].url))
    identity.assign_project_role(
        AssignProjectRole(
            approval_env[-1][2],
            cmd.project_id,
            actor.actor_id,
            "VIEWER",
            "Historical reader",
            uuid4(),
        )
    )
    with base[8].connect() as conn:
        role = conn.execute(
            text("SELECT id FROM project_role_assignments WHERE actor_id=:actor AND role='OWNER'"),
            {"actor": actor.actor_id},
        ).scalar_one()
    identity.close_project_role(
        CloseProjectRole(
            approval_env[-1][2], cmd.project_id, role, "Remove write authority", uuid4()
        )
    )
    assert owner.record_internal_scientific_release(actor, cmd) == saved
    with pytest.raises(ResearchBaseError) as error:
        approval_env[0].evaluate_approval_grant(
            actor, EvaluateApprovalGrantCommand(cmd.project_id, cmd.grant_id)
        )
    assert error.value.code == ErrorCode.FORBIDDEN


def test_uncertain_commit_recovers_original_key_without_second_effect(approval_env, monkeypatch):
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork

    owner, actor, cmd, _ = issued(approval_env)
    original = SqlAlchemyUnitOfWork.commit

    def uncertain(self):
        original(self)
        raise RuntimeError("uncertain commit connection loss")

    with monkeypatch.context() as patch:
        patch.setattr(SqlAlchemyUnitOfWork, "commit", uncertain)
        with pytest.raises(RuntimeError):
            owner.record_internal_scientific_release(actor, cmd)
    assert owner.record_internal_scientific_release(actor, cmd).grant_id == cmd.grant_id
    assert counts(approval_env) == (1, 2, 1)
