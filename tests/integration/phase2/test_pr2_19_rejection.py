"""F5c rejection fences survive new identifiers; release-only reconsideration."""

from dataclasses import replace
from uuid import uuid4

import pytest

from researchbase.application.approval import ApprovalService
from researchbase.application.decision import DecisionService
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.b30_observations import assert_snapshot_read, sql_protocol
from tests.integration.phase2.pr2_19_support import counts
from tests.integration.phase2.test_approval import (
    _decide,
    approval_env,
    conclusion_env,
    decision_env,
    phase2_database_url,
)
from tests.integration.phase2.test_b10_reconsideration import approver_actor, reconsideration_env

_FIXTURES = (approval_env, conclusion_env, decision_env, phase2_database_url, reconsideration_env)
pytestmark = pytest.mark.integration


def test_rejection_fences_new_and_precreated_requests(approval_env):
    service, requester, approver, request, env = approval_env
    from researchbase.application.approval import RequestApprovalCommand
    from researchbase.application.scientific_conclusion import ClaimInputRequest
    from tests.integration.phase2.test_pr2_11_r2_persistence import SCOPE
    from tests.integration.phase2.test_pr2_15_decision import _command, _review

    base = env[-1]
    target = base[0].create(
        base[3],
        base[5],
        "B30 second target",
        SCOPE,
        "MODERATE",
        None,
        (ClaimInputRequest(base[6], "SUPPORTS"),),
        (),
        uuid4(),
    )
    base[0].freeze(base[3], base[5], target.conclusion_id, target.version_id, uuid4())
    other_env = (env[0], env[1], env[2], target, base)
    review = _review(other_env)
    basis = env[0].record_decision(env[2], _command(other_env))
    precreated = RequestApprovalCommand(
        uuid4(), request.project_id, target.version_id, basis.id, (review.id,)
    )
    first = service.request_approval(requester, request)
    service.request_approval(requester, precreated)
    rejected = service.decide_approval(approver, _decide(precreated, "REJECT"))
    assert rejected.grant is None
    independent_approver = approver_actor(env)
    before = counts(env[-1][8])
    for actor, candidate in (
        (requester, replace(request, id=uuid4())),
        (requester, replace(precreated, id=uuid4())),
    ):
        with pytest.raises(ResearchBaseError) as denied:
            service.request_approval(actor, candidate)
        assert denied.value.code is ErrorCode.REJECTION_RECONSIDERATION_REQUIRED
    with pytest.raises(ResearchBaseError) as denied:
        service.decide_approval(independent_approver, _decide(request))
    assert denied.value.code is ErrorCode.REJECTION_RECONSIDERATION_REQUIRED
    fresh = ApprovalService(env[-1][1], env[-1][9], env[-1][2])
    assert fresh.get_request(requester, request.project_id, first.id).status == "PENDING"
    assert fresh.get_request(requester, request.project_id, precreated.id).status == "DECIDED"
    assert counts(env[-1][8]) == before


def test_reconsideration_exact_successor_retains_rejected_history(reconsideration_env):
    decisions, cmd, actor, approval = reconsideration_env
    service, requester, _, old, env = approval
    base = env[-1]
    saved = decisions.record_rejection_reconsideration(cmd, actor)
    successor = replace(
        old, id=uuid4(), prior_rejected_request_id=old.id, reconsideration_decision_id=saved.id
    )
    requested = service.request_approval(requester, successor)
    approved = service.decide_approval(approver_actor(env), _decide(successor))
    assert approved.grant is not None and approved.grant.usable
    assert requested.prior_rejected_request_id == old.id
    fresh = DecisionService(base[1], base[9], base[2])
    with sql_protocol(base[8]) as statements:
        historical = fresh.get_rejection_reconsideration(cmd.project_id, saved.id, actor)
    assert_snapshot_read(statements)
    assert (
        historical.successor_request_id == successor.id
        and historical.content_hash == saved.content_hash
    )
    before = counts(base[8])
    with pytest.raises(ResearchBaseError) as denied:
        fresh.record_rejection_reconsideration(replace(cmd, rationale="Changed replay"), actor)
    assert denied.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    assert counts(base[8]) == before
    del base[9].principals[actor.actor_id]
    with pytest.raises(ResearchBaseError) as denied:
        fresh.get_rejection_reconsideration(cmd.project_id, saved.id, actor)
    assert denied.value.code is ErrorCode.FORBIDDEN
    assert counts(base[8]) == before
    assert service.get_request(requester, old.project_id, old.id).status == "DECIDED"


def test_later_rejection_requires_complete_new_coverage_but_retains_saved_history(
    reconsideration_env,
):
    decisions, cmd, actor, approval = reconsideration_env
    service, requester, _, old, env = approval
    base = env[-1]
    coverage = decisions.record_rejection_reconsideration(cmd, actor)
    unused = decisions.record_rejection_reconsideration(replace(cmd, id=uuid4()), actor)
    successor = replace(
        old, id=uuid4(), prior_rejected_request_id=old.id, reconsideration_decision_id=coverage.id
    )
    service.request_approval(requester, successor)
    service.decide_approval(approver_actor(env), _decide(successor, "REJECT"))
    before = counts(base[8])
    fresh = DecisionService(base[1], base[9], base[2])
    history = fresh.get_rejection_reconsideration(cmd.project_id, unused.id, actor)
    assert history.content_hash == unused.content_hash and not history.current_coverage_complete
    with pytest.raises(ResearchBaseError) as denied:
        service.request_approval(
            requester, replace(successor, id=uuid4(), reconsideration_decision_id=unused.id)
        )
    assert denied.value.code is ErrorCode.REJECTION_RECONSIDERATION_REQUIRED
    assert counts(base[8]) == before
    assert service.get_request(requester, old.project_id, old.id).status == "DECIDED"
    assert service.get_request(requester, old.project_id, successor.id).status == "DECIDED"
