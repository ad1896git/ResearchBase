"""F7 faults after real protected writes, deferred checks and before commit."""

import pytest

from researchbase.application.approval import ApprovalService
from researchbase.application.internal_review import InternalReviewService
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.approval_repository import SqlAlchemyApprovalRepository
from researchbase.persistence.uow import SqlAlchemyUnitOfWork
from tests.integration.phase2.pr2_19_support import counts
from tests.integration.phase2.test_approval import (
    _decide,
    approval_env,
    conclusion_env,
    decision_env,
    phase2_database_url,
)

_FIXTURES = (approval_env, conclusion_env, decision_env, phase2_database_url)
pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    "command,stage",
    [
        ("request", "approval_requests"),  # Parent insert also executes the event trigger.
        ("request", "approval_request_reviews"),
        ("request", "force_constraints"),
        ("request", "commit"),
        ("decision", "approval_decisions"),  # Includes request status/event trigger.
        ("decision", "approval_grants"),  # Includes grant creation event trigger.
        ("decision", "force_constraints"),
        ("decision", "commit"),
    ],
)
def test_protected_command_rolls_back_but_committed_predecessors_survive(
    approval_env, monkeypatch, command, stage
):
    service, requester, approver, request, env = approval_env
    base = env[-1]
    predecessor = service.request_approval(requester, request) if command == "decision" else None
    old_review = env[1].read(requester, request.project_id, request.review_ids[0])
    before = counts(base[8])
    touched = []
    if stage == "commit":

        def fail_commit(self):
            touched.append(stage)
            raise RuntimeError("B30 before commit")

        target, name, fail = SqlAlchemyUnitOfWork, "commit", fail_commit
    elif stage == "force_constraints":
        original = SqlAlchemyApprovalRepository.force_constraints

        def fail_check(self):
            original(self)
            touched.append(stage)
            raise RuntimeError("B30 after deferred checks")

        target, name, fail = SqlAlchemyApprovalRepository, stage, fail_check
    else:
        original = SqlAlchemyApprovalRepository.insert

        def fail_insert(self, table, row):
            original(self, table, row)
            if table == stage:
                touched.append(stage)
                raise RuntimeError("B30 after parent/child and trigger event")

        target, name, fail = SqlAlchemyApprovalRepository, "insert", fail_insert
    with monkeypatch.context() as patch:
        patch.setattr(target, name, fail)
        with pytest.raises(RuntimeError, match="B30"):
            if command == "request":
                service.request_approval(requester, request)
            else:
                service.decide_approval(approver, _decide(request))
    assert touched == [stage] and counts(base[8]) == before
    fresh = ApprovalService(base[1], base[9], base[2])
    assert (
        InternalReviewService(base[1], base[9], base[2]).read(
            requester, request.project_id, old_review.id
        )
        == old_review
    )
    if predecessor:
        assert fresh.get_request(requester, request.project_id, request.id) == predecessor
    else:
        with pytest.raises(ResearchBaseError) as denied:
            fresh.get_request(requester, request.project_id, request.id)
        assert denied.value.code is ErrorCode.NOT_FOUND
    assert counts(base[8]) == before
