"""Only the existing minimal Decision command; no approval activation."""

from dataclasses import replace

import pytest
from sqlalchemy import text

from researchbase.application.decision import RecordDecisionCommand
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2 import test_pr2_15_decision as cases
from tests.integration.phase2.pr2_19_support import conclusion_env as _conclusion_env
from tests.integration.phase2.pr2_19_support import counts
from tests.integration.phase2.pr2_19_support import decision_env as _decision_env
from tests.integration.phase2.pr2_19_support import m3 as _m3
from tests.integration.phase2.pr2_19_support import phase2_database_url as _phase2_database_url
from tests.integration.phase2.pr2_19_support import pr219_decision_env as _pr219_decision_env

pytestmark = pytest.mark.integration


def test_complete_unfavorable_basis_does_not_change_target_or_effects(pr219_decision_env):
    env = pr219_decision_env
    engine = env[-1][8]
    with engine.connect() as conn:
        before = conn.execute(
            text("SELECT * FROM scientific_conclusion_versions ORDER BY id")
        ).all()
    cases.test_complete_basis_every_type_unfavorable_review_r2_and_restart(env)
    with engine.connect() as conn:
        assert (
            conn.execute(text("SELECT * FROM scientific_conclusion_versions ORDER BY id")).all()
            == before
        )
    assert counts(engine, ("approval_requests", "approval_decisions", "approval_grants")) == {
        "approval_requests": 0,
        "approval_decisions": 0,
        "approval_grants": 0,
    }


@pytest.mark.parametrize(
    "severity,allowed", [("BLOCKING", False), ("MAJOR", True), ("MINOR", True), ("INFO", True)]
)
def test_exact_open_blocking_predicate(pr219_decision_env, severity, allowed):
    cases.test_exact_open_blocking_predicate(pr219_decision_env, severity, allowed)


def test_unrelated_issue_control(pr219_decision_env):
    cases.test_shared_claim_other_conclusion_blocker_does_not_apply(pr219_decision_env)


@pytest.mark.parametrize(
    "case", ["author", "no_principal", "cross_project", "expired_credential", "unknown_field"]
)
def test_authority_and_closed_boundary_zero_delta(pr219_decision_env, case):
    env = pr219_decision_env
    service, _, actor, _, base = env
    cases._review(env)
    command = cases._command(env)
    before = counts(base[8])
    if case == "unknown_field":
        with pytest.raises(TypeError):
            RecordDecisionCommand(
                **{
                    **{name: getattr(command, name) for name in command.__dataclass_fields__},
                    "approved": True,
                }
            )
    else:
        principal = base[3] if case == "author" else None if case == "no_principal" else actor
        if case == "cross_project":
            from uuid import uuid4

            command = replace(command, project_id=uuid4())
        if case == "expired_credential":
            base[9].enabled = False
        with pytest.raises(ResearchBaseError) as denied:
            service.record_decision(principal, command)
        assert (
            denied.value.code
            is {
                "author": ErrorCode.CONFLICT_OF_INTEREST,
                "no_principal": ErrorCode.AUTHENTICATION_REQUIRED,
                "cross_project": ErrorCode.FORBIDDEN,
                "expired_credential": ErrorCode.FORBIDDEN,
            }[case]
        )
    assert counts(base[8]) == before


# Register imported fixtures explicitly, matching the existing Phase 2 layout.
conclusion_env = _conclusion_env
decision_env = _decision_env
m3 = _m3
phase2_database_url = _phase2_database_url
pr219_decision_env = _pr219_decision_env
