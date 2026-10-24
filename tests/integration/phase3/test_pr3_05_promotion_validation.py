"""Validation returns context observations, never promotion or execution authority."""

from dataclasses import replace
from hashlib import sha256

import pytest
from sqlalchemy.orm import sessionmaker
from tests.integration.phase3.conftest import Credentials
from tests.integration.phase3.test_pr3_04_application import approve, bind
from tests.integration.phase3.test_pr3_05_context_reads import create_task, reader, scope
from tests.integration.phase3.test_pr3_05_memory_reads import saved_memory

from researchbase.agent_runtime.application.context_contracts import PromotionContextRequest
from researchbase.agent_runtime.application.promotion_context import PromotionContextService
from researchbase.persistence.uow import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("target", ["RESEARCH_QUESTION_VERSION", "HYPOTHESIS_VERSION"])
def test_candidate_basis_revision_gates_and_missing_s2(
    planning, normal_engine, scientific_inputs, target
):
    task = create_task(planning, {target: scientific_inputs[target]})
    bind(planning, task)
    approve(planning, task, 2)
    memory, raw = saved_memory(planning, task=task)
    context = reader(planning).load_for_task(planning.principal, scope(planning, task))
    request = PromotionContextRequest(
        project_id=planning.project,
        task_id=task,
        candidate_artifact_version_id=memory.artifact_version_id,
        candidate_content_hash=sha256(raw).hexdigest(),
        expected_task_row_version=4,
        target_type=target,
        canonical_basis=tuple(s.reference for s in context.sources),
    )

    def factory():
        return SqlAlchemyUnitOfWork(
            sessionmaker(normal_engine), context_artifact_store=planning.store
        )

    service = PromotionContextService(factory, Credentials())
    for changes, expected in (
        ({}, None),
        ({"expected_task_row_version": 1}, "REVISION_MISMATCH"),
        ({"candidate_content_hash": "0" * 64}, "CANDIDATE_MISMATCH"),
        ({"canonical_basis": ()}, "BASIS_MISMATCH"),
    ):
        result = service.validate_promotion_context(planning.principal, replace(request, **changes))
        reasons = {f.reason for f in result.failures}
        assert "S2_PRODUCER_PROVENANCE_UNVERIFIED" in reasons
        if not changes:
            assert result.context_admissible
        if expected:
            assert expected in reasons and not result.context_admissible
        assert not result.promotion_enabled and not result.execution_enabled
        assert not result.provider_disclosure_granted and not result.producer_provenance_verified
        assert result.context.sources == context.sources

    planning.service.execute(
        planning.principal,
        planning.command("cancel_research_task", task, 4, {"reason": "Stop remains authoritative"}),
    )
    stopped = service.validate_promotion_context(
        planning.principal, replace(request, expected_task_row_version=5)
    )
    assert not stopped.context_admissible
    assert "GATE_UNMET" in {failure.reason for failure in stopped.failures}
    assert not stopped.execution_enabled and not stopped.promotion_enabled
