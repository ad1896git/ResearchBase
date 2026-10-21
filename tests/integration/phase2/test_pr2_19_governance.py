"""F5/F5b deterministic approval gates preserve committed predecessor facts."""

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
from tests.integration.phase2.test_approval import approval_env as _approval_env
from tests.integration.phase2.test_b14_publication_ready import b04_env, b05_env, revision_env

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


@pytest.mark.parametrize("stage", ["request", "decision"])
@pytest.mark.parametrize("fact", ["blocking", "stale"])
def test_approval_current_fact_denial_retains_committed_request(approval_env, stage, fact):
    from researchbase.application.approval import ApprovalService
    from researchbase.application.internal_review import ReviewIssueRequest
    from researchbase.persistence.approval_repository import B09_DECIDE_SHARE_SQL, B09_SHARE_SQL
    from tests.integration.phase2.b30_observations import (
        assert_first_share,
        assert_snapshot_read,
        sql_protocol,
    )
    from tests.integration.phase2.test_approval import _decide

    service, requester, approver, command, env = approval_env
    base = env[-1]
    prior = service.request_approval(requester, command) if stage == "decision" else None
    if fact == "blocking":
        cases._review(
            env, "REJECT", (ReviewIssueRequest("BLOCKING", "OVERCLAIM", "B30 current concern"),)
        )
    else:
        cases._stale(env)
    before = counts(base[8])
    with sql_protocol(base[8]) as statements:
        with pytest.raises(ResearchBaseError) as denied:
            if stage == "request":
                service.request_approval(requester, command)
            else:
                service.decide_approval(approver, _decide(command))
    assert_first_share(statements, B09_SHARE_SQL if stage == "request" else B09_DECIDE_SHARE_SQL)
    if stage == "decision":
        assert (
            "LOCK TABLE publications IN SHARE ROW EXCLUSIVE MODE",
            "READ_COMMITTED",
            False,
        ) in statements
    assert denied.value.code is (
        ErrorCode.APPROVAL_GATE_FAILED if fact == "blocking" else ErrorCode.APPROVAL_TARGET_STALE
    )
    assert counts(base[8]) == before
    fresh = ApprovalService(base[1], base[9], base[2])
    if prior:
        with sql_protocol(base[8]) as statements:
            assert fresh.get_request(requester, command.project_id, command.id).status == "PENDING"
        assert_snapshot_read(statements)
    else:
        with pytest.raises(ResearchBaseError) as absent:
            fresh.get_request(requester, command.project_id, command.id)
        assert absent.value.code is ErrorCode.NOT_FOUND
    assert counts(base[8]) == before


@pytest.mark.parametrize(
    "case,code",
    [
        ("owner_only", ErrorCode.FORBIDDEN),
        ("requester", ErrorCode.CONFLICT_OF_INTEREST),
        ("reviewer", ErrorCode.CONFLICT_OF_INTEREST),
        ("author", ErrorCode.CONFLICT_OF_INTEREST),
        ("credential", ErrorCode.FORBIDDEN),
        ("wrong_project", ErrorCode.FORBIDDEN),
    ],
)
def test_approval_independence_and_authority_matrix(approval_env, case, code):
    from uuid import uuid4

    from researchbase.application.phase2_identity import AssignProjectRole
    from tests.integration.phase2.test_approval import _actor, _decide
    from tests.integration.phase2.test_pr2_00_challenges import _service

    service, requester, approver, request, env = approval_env
    base = env[-1]
    prior = service.request_approval(requester, request)
    actor = approver
    if case in {"owner_only", "requester", "reviewer", "author"}:
        actor = {"requester": requester, "reviewer": env[2], "author": base[3]}.get(case)
        if actor is None:
            actor = _actor(env)
        if case != "owner_only":
            identity, _, _ = _service(base[8].url.render_as_string(hide_password=False))
            identity.assign_project_role(
                AssignProjectRole(
                    actor if case == "author" else env[2],
                    request.project_id,
                    actor.actor_id,
                    "APPROVER",
                    "Test independence even with role",
                    uuid4(),
                )
            )
    command = _decide(request)
    if case == "credential":
        del base[9].principals[actor.actor_id]
    elif case == "wrong_project":
        command = replace(command, project_id=uuid4())
    before = counts(base[8])
    with pytest.raises(ResearchBaseError) as denied:
        service.decide_approval(actor, command)
    assert denied.value.code is code
    assert counts(base[8]) == before
    assert service.get_request(requester, request.project_id, prior.id).status == "PENDING"


approval_env = _approval_env


def test_snapshot_observer_uses_server_settings_across_pooled_reuse(approval_env):
    from tests.integration.phase2.b30_observations import assert_snapshot_read, sql_protocol

    engine = approval_env[-1][-1][8]
    with engine.connect() as conn:
        with sql_protocol(engine) as observed:
            conn.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
            conn.execute(text("SELECT 1"))
            conn.rollback()
            conn.execute(text("SELECT 2"))
            conn.rollback()
    assert len(observed.transactions) == 2
    first, second = observed.transactions
    assert first.backend_pid == second.backend_pid
    assert_snapshot_read(first.statements)
    assert all(mode == "READ_COMMITTED" and not readonly for _, mode, readonly in second.statements)
    with pytest.raises(AssertionError):
        assert_snapshot_read(observed)


@pytest.mark.parametrize("field", ["on_behalf_of_actor_id", "approved", "skip_review"])
def test_closed_approval_command_rejects_bypass_fields(approval_env, field):
    from dataclasses import asdict
    from uuid import uuid4

    from researchbase.application.approval import RequestApprovalCommand

    service, requester, _, command, env = approval_env
    before = counts(env[-1][8])
    with pytest.raises(TypeError):
        RequestApprovalCommand(**{**asdict(command), field: uuid4()})
    assert counts(env[-1][8]) == before
    with pytest.raises(ResearchBaseError) as missing:
        service.get_request(requester, command.project_id, command.id)
    assert missing.value.code is ErrorCode.NOT_FOUND


def test_wrong_purpose_target_tuple_never_creates_approval(approval_env):
    _, _, _, command, env = approval_env
    before = counts(env[-1][8])
    with pytest.raises(ResearchBaseError) as denied:
        replace(command, approval_purpose="READY_FOR_SUBMISSION")
    assert denied.value.code is ErrorCode.APPROVAL_PURPOSE_TARGET_COMMAND_INVALID
    assert counts(env[-1][8]) == before


@pytest.mark.parametrize("delta", [-1, 0, 31])
def test_approval_expiry_denial_retains_committed_request(approval_env, delta):
    from datetime import timedelta

    from researchbase.application.approval import ApprovalService
    from tests.integration.phase2.test_approval import _decide

    service, requester, approver, request, env = approval_env
    prior = service.request_approval(requester, request)
    with env[-1][8].connect() as conn:
        expiry = conn.execute(text("SELECT clock_timestamp()")).scalar_one() + timedelta(days=delta)
    before = counts(env[-1][8])
    with pytest.raises(ResearchBaseError) as denied:
        service.decide_approval(
            approver, _decide(request, "APPROVE_WITH_CONDITIONS", valid_until=expiry)
        )
    assert denied.value.code is ErrorCode.VALIDATION_ERROR
    assert counts(env[-1][8]) == before
    reader = ApprovalService(env[-1][1], env[-1][9], env[-1][2])
    assert reader.get_request(requester, request.project_id, prior.id).status == "PENDING"


def test_complete_adverse_review_basis_cannot_be_substituted(approval_env):
    from tests.integration.phase2.test_approval import _decide

    service, requester, approver, command, env = approval_env
    adverse = cases._review(env, "REJECT")
    before = counts(env[-1][8])
    with pytest.raises(ResearchBaseError) as denied:
        service.request_approval(
            requester,
            replace(command, review_ids=tuple(sorted(command.review_ids + (adverse.id,)))),
        )
    assert denied.value.code is ErrorCode.DECISION_BASIS_INVALID
    assert counts(env[-1][8]) == before
    # Later adverse review is historical evidence; the saved Decision's exact
    # basis remains the only admissible request basis (no implicit replacement).
    saved = service.request_approval(requester, command)
    result = service.decide_approval(approver, _decide(command))
    assert result.grant is not None
    assert tuple(ref.id for ref in saved.reviews) == command.review_ids


def test_agent_with_existing_role_and_verified_binding_cannot_approve(approval_env):
    from uuid import uuid4

    from researchbase.application.phase2_identity import AssignProjectRole
    from tests.integration.phase2.test_approval import _actor, _decide
    from tests.integration.phase2.test_pr2_00_challenges import _service

    service, requester, _, request, env = approval_env
    actor = _actor(env)
    identity, _, _ = _service(env[-1][8].url.render_as_string(hide_password=False))
    identity.assign_project_role(
        AssignProjectRole(
            env[2], request.project_id, actor.actor_id, "APPROVER", "Test HUMAN-only gate", uuid4()
        )
    )
    # Existing discussion fixture pattern: isolated test actor classification,
    # with valid binding/membership/role retained. No scientific/grant fabrication.
    with env[-1][8].begin() as conn:
        conn.execute(
            text("UPDATE actors SET actor_type='AGENT' WHERE id=:id"), {"id": actor.actor_id}
        )
    prior = service.request_approval(requester, request)
    before = counts(env[-1][8])
    with pytest.raises(ResearchBaseError) as denied:
        service.decide_approval(actor, _decide(request))
    assert denied.value.code is ErrorCode.FORBIDDEN
    assert counts(env[-1][8]) == before
    assert service.get_request(requester, request.project_id, prior.id).status == "PENDING"


@pytest.mark.parametrize("blocked", [False, True])
@pytest.mark.parametrize("wait", [False, True])
def test_f5_ready_consumption_uses_current_issue_not_recommendation(b05_env, blocked, wait):
    from types import SimpleNamespace

    from researchbase.application.internal_review import ReviewIssueRequest
    from researchbase.persistence.approval_repository import B13_SHARE_SQL
    from tests.integration.phase2.b30_observations import assert_first_share, sql_protocol
    from tests.integration.phase2.test_b05_manuscript_review import create
    from tests.integration.phase2.test_b14_publication_ready import issued
    from tests.integration.phase2.test_b17_freeze_concurrency import observed_order

    env = b05_env
    app, command, approval, _ = issued(env)
    before = counts(env[5])

    def review():
        return create(
            env,
            recommendation="REJECT",
            issues=(ReviewIssueRequest("BLOCKING", "OTHER", "S2 current concern"),)
            if blocked
            else (),
        )

    def consume():
        return app.transition_publication_ready(env[2], command)

    if wait:
        _, result = observed_order(
            SimpleNamespace(engine=env[5]),
            review,
            consume,
            "INSERT INTO INTERNAL_REVIEW_RECORDS",
        )
    else:
        review()
        with sql_protocol(env[5]) as observed:
            try:
                result = consume()
            except ResearchBaseError as exc:
                result = exc.code
        assert_first_share(observed, B13_SHARE_SQL, "SERIALIZABLE")
    after = counts(env[5])
    if blocked:
        assert result == ErrorCode.APPROVAL_GATE_FAILED
        for table in (
            "approval_grant_consumptions",
            "approval_grant_events",
            "publication_lifecycle_events",
        ):
            assert after[table] == before[table]
    else:
        assert not isinstance(result, ErrorCode)
        assert result.result_publication_id == command.result_id
        assert after["approval_grant_consumptions"] == before["approval_grant_consumptions"] + 1
    from researchbase.application.approval import ApprovalService

    fresh = ApprovalService(env[4], env[9], env[10][2])
    grant = fresh.get_grant(env[2], command.project_id, command.grant_id)
    assert grant.status == ("ACTIVE" if blocked else "CONSUMED")
    assert fresh.get_decision(env[2], command.project_id, grant.approval_decision_id)
    with env[5].connect() as conn:
        assert conn.execute(
            text("SELECT lifecycle_status FROM publications WHERE id=:id"),
            {"id": command.result_id},
        ).scalar_one() == ("INTERNAL_REVIEW" if blocked else "READY")


_FIXTURES = (b04_env, b05_env, revision_env)
