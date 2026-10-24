"""Read-only candidate context validation; every action still requires fresh admission."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from researchbase.agent_runtime.application.canonical_context import CanonicalContextService
from researchbase.agent_runtime.application.context_contracts import (
    ContextRequest,
    PromotionContextRequest,
    PromotionContextValidation,
    PromotionFailure,
)
from researchbase.agent_runtime.application.task_safety import gates
from researchbase.agent_runtime.ports.context_repository import ContextUowFactory
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


class PromotionContextService:
    def __init__(self, factory: ContextUowFactory, credentials: Any):
        self._factory = factory
        self._canonical = CanonicalContextService(factory, credentials)

    def validate_promotion_context(
        self, principal: VerifiedPrincipal, request: PromotionContextRequest
    ) -> PromotionContextValidation:
        try:
            if type(request) is not PromotionContextRequest:
                raise ValueError("closed request required")
            request.__post_init__()
        except (ValueError, TypeError, AttributeError, UnicodeError):
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR, "closed promotion context request required"
            ) from None
        scope = ContextRequest(
            project_id=request.project_id, task_id=request.task_id, step_id=request.step_id
        )
        with self._factory() as uow:
            uow.begin_formal_read()
            at = uow.task_safety.snapshot_at()
            context = self._canonical.context_in_uow(uow, principal, scope, at)
            candidate = uow.context_reads.artifact(
                scope.project_id, request.candidate_artifact_version_id
            )
            if candidate is None:
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "exact candidate version unavailable")
            failures = []
            if context.task.row_version != request.expected_task_row_version:
                failures.append(
                    PromotionFailure(
                        code=ErrorCode.CONCURRENT_MODIFICATION, reason="REVISION_MISMATCH"
                    )
                )
            if (
                candidate.reference.id != request.candidate_artifact_version_id
                or candidate.reference.content_hash != request.candidate_content_hash
            ):
                failures.append(
                    PromotionFailure(code=ErrorCode.VALIDATION_ERROR, reason="CANDIDATE_MISMATCH")
                )
            # Resolve even mismatched requested basis identities before returning any result.
            # A foreign required source denies the entire query, never a partial failure row.
            expected = tuple(source.reference for source in context.sources)
            validated = []
            for reference in request.canonical_basis:
                source = uow.context_reads.source(scope.project_id, reference.task_input)
                if source is not None and source.reference == reference and reference in expected:
                    validated.append(reference)
            if tuple(validated) != request.canonical_basis or request.canonical_basis != expected:
                failures.append(
                    PromotionFailure(
                        code=ErrorCode.PROVENANCE_CLOSURE_VIOLATION, reason="BASIS_MISMATCH"
                    )
                )
            safety = context.safety
            selected_gates = ()
            if scope.step_id is not None and safety.checkpoint_policy is not None:
                selected_gates = gates(
                    {"required_types": safety.checkpoint_policy.required_types},
                    [asdict(checkpoint) for checkpoint in context.checkpoint_history.checkpoints],
                    at,
                    step=scope.step_id,
                )
            if (
                context.task.status == "CANCELLED"
                or safety.stop_causes
                or safety.budget_policy_id is None
                or safety.termination_policy_id is None
                or safety.checkpoint_policy_id is None
                or any(not gate.satisfied for gate in safety.required_gates)
                or any(not gate.satisfied for gate in selected_gates)
            ):
                failures.append(
                    PromotionFailure(code=ErrorCode.INVALID_STATE_TRANSITION, reason="GATE_UNMET")
                )
            admissible = not failures
            failures.append(
                PromotionFailure(
                    code=ErrorCode.INVALID_STATE_TRANSITION,
                    reason="S2_PRODUCER_PROVENANCE_UNVERIFIED",
                )
            )
            return PromotionContextValidation(
                snapshot_at=at,
                scope=scope,
                candidate=candidate,
                target_type=request.target_type,
                requested_task_row_version=request.expected_task_row_version,
                context=context,
                validated_basis=tuple(validated),
                context_admissible=admissible,
                failures=tuple(failures),
            )
