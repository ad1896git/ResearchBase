"""Explicit one-grant OWNER maintenance and terminal precedence."""

import time
from datetime import timedelta

import pytest
from sqlalchemy import text

from researchbase.application.approval import (
    EvaluateApprovalGrantCommand,
    RevokeApprovalGrantCommand,
)
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
pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)


def test_revoke_and_terminal_repeats(approval_env):
    _, actor, cmd, _ = issued(approval_env)
    service = approval_env[0]
    evaluate = EvaluateApprovalGrantCommand(cmd.project_id, cmd.grant_id)
    assert service.evaluate_approval_grant(actor, evaluate).evaluation.usable
    result = service.revoke_approval_grant(
        actor, RevokeApprovalGrantCommand(cmd.project_id, cmd.grant_id, "Owner revocation")
    )
    assert result.grant.status == "REVOKED"
    assert service.evaluate_approval_grant(actor, evaluate) == result
    assert (
        service.revoke_approval_grant(
            actor, RevokeApprovalGrantCommand(cmd.project_id, cmd.grant_id, "Another reason")
        )
        == result
    )
    assert counts(approval_env) == (0, 2, 1)


def test_expiry_effective_without_write_and_observed_expiry_event(approval_env):
    engine = approval_env[-1][-1][8]
    with engine.connect() as conn:
        until = conn.execute(text("SELECT clock_timestamp()")).scalar_one() + timedelta(seconds=1)
    owner, actor, cmd, _ = issued(approval_env, expiry=until)
    remaining = (
        until - __import__("datetime").datetime.now(__import__("datetime").UTC)
    ).total_seconds()
    if remaining > 0:
        time.sleep(remaining + 0.02)
    with pytest.raises(ResearchBaseError) as error:
        owner.record_internal_scientific_release(actor, cmd)
    assert error.value.code == ErrorCode.GRANT_INVALID
    assert counts(approval_env) == (0, 1, 1)
    result = approval_env[0].revoke_approval_grant(
        actor, RevokeApprovalGrantCommand(cmd.project_id, cmd.grant_id, "Revoke expired")
    )
    assert result.grant.status == "EXPIRED"
    with engine.connect() as conn:
        observed = conn.execute(
            text("SELECT occurred_at FROM approval_grant_events WHERE new_status='EXPIRED'")
        ).scalar_one()
    assert observed >= until
    assert (
        approval_env[0]
        .evaluate_approval_grant(actor, EvaluateApprovalGrantCommand(cmd.project_id, cmd.grant_id))
        .grant.status
        == "EXPIRED"
    )
    assert counts(approval_env) == (0, 2, 1)


def test_explicit_staleness_and_repeat(approval_env):
    from tests.integration.phase2.test_pr2_15_decision import _stale

    _, actor, cmd, _ = issued(approval_env)
    _stale(approval_env[-1])
    result = approval_env[0].evaluate_approval_grant(
        actor, EvaluateApprovalGrantCommand(cmd.project_id, cmd.grant_id)
    )
    assert result.grant.status == "STALE"
    assert counts(approval_env) == (0, 2, 1)
    assert (
        approval_env[0]
        .evaluate_approval_grant(actor, EvaluateApprovalGrantCommand(cmd.project_id, cmd.grant_id))
        .event_ids
        == result.event_ids
    )
