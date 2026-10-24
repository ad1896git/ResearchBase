"""Canonical reconstruction only; no memory, promotion or execution authority."""

from __future__ import annotations

from typing import Any, cast

from researchbase.agent_runtime.application.context_contracts import (
    CanonicalContext,
    ContextRequest,
)
from researchbase.agent_runtime.application.research_task import TaskContextAdmission
from researchbase.agent_runtime.application.safety_contracts import (
    CheckpointHistoryRead,
    TaskSafetyRead,
)
from researchbase.agent_runtime.application.task_safety import safety_projection
from researchbase.agent_runtime.ports.context_repository import ContextUowFactory
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


class CanonicalContextService:
    def __init__(self, factory: ContextUowFactory, credentials: Any):
        self._factory = factory
        self._tasks = TaskContextAdmission(credentials)

    def load_for_task(
        self, principal: VerifiedPrincipal, request: ContextRequest
    ) -> CanonicalContext:
        return self.get_canonical_context_for_task(principal, request)

    def get_canonical_context_for_task(
        self, principal: VerifiedPrincipal, request: ContextRequest
    ) -> CanonicalContext:
        if type(request) is not ContextRequest:
            raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, "closed context request required")
        with self._factory() as uow:
            uow.begin_formal_read()
            at = uow.task_safety.snapshot_at()
            return self.context_in_uow(uow, principal, request, at)

    def context_in_uow(self, uow, principal, request, at) -> CanonicalContext:
        """Composition surface for later read services; never opens another transaction."""
        self._tasks.authorize_context_read(uow, principal, request.project_id, at)
        try:
            task = uow.context_reads.task_context(request)
            if task is None:
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "task not found")
            sources = {}
            for binding in task.bindings:
                reference = binding.source
                key = (reference.type, reference.id)
                if key not in sources:
                    sources[key] = self._tasks.resolve_context_binding(
                        uow, request.project_id, reference.task_input, reference
                    )
                elif sources[key].reference != reference:
                    raise ResearchBaseError(
                        ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved exact input contradiction"
                    )
            ordered = tuple(
                sources[key] for key in sorted(sources, key=lambda k: (k[0], str(k[1])))
            )
            raw_task = uow.research_tasks.task(request.task_id)
            safety = safety_projection(uow.task_safety, raw_task, at, history=False)
            history = safety_projection(uow.task_safety, raw_task, at, history=True)
            return CanonicalContext(
                snapshot_at=at,
                task=task,
                sources=ordered,
                safety=cast(TaskSafetyRead, safety),
                checkpoint_history=cast(CheckpointHistoryRead, history),
                warnings=tuple(w for source in ordered for w in source.validity.warnings),
            )
        except (ValueError, TypeError, KeyError, UnicodeError):
            raise ResearchBaseError(
                ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "canonical context contradiction"
            ) from None
