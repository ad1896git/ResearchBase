"""Exact, scoped reads of derived memory; no saving, repair or scientific authority."""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from typing import Any

from researchbase.agent_runtime.application.canonical_context import CanonicalContextService
from researchbase.agent_runtime.application.context_contracts import (
    ArtifactContext,
    CanonicalSource,
    ContextRequest,
    TaskMemoryManifest,
    TaskMemoryRead,
    TaskMemoryRequest,
    UnusableMemory,
    ValidityObservation,
    parse_memory_manifest,
)
from researchbase.agent_runtime.application.contracts import InputType
from researchbase.agent_runtime.application.research_task import TaskContextAdmission
from researchbase.agent_runtime.domain.task_memory import MAX_MANIFEST_BYTES, memory_error
from researchbase.agent_runtime.ports.context_repository import ContextUnitOfWork, ContextUowFactory
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


class TaskMemoryService:
    def __init__(self, factory: ContextUowFactory, credentials: Any):
        self._factory = factory
        self._canonical = CanonicalContextService(factory, credentials)
        self._tasks = TaskContextAdmission(credentials)

    def get_task_working_memory(
        self, principal: VerifiedPrincipal, request: TaskMemoryRequest
    ) -> TaskMemoryRead:
        result = self._read(principal, request, optional=False)
        assert isinstance(result, TaskMemoryRead)
        return result

    def get_optional_task_working_memory(
        self, principal: VerifiedPrincipal, request: TaskMemoryRequest
    ) -> TaskMemoryRead | UnusableMemory:
        """Only local memory loss is optional; denied/required sources always fail closed."""
        return self._read(principal, request, optional=True)

    def _read(
        self, principal: VerifiedPrincipal, request: TaskMemoryRequest, *, optional: bool
    ) -> TaskMemoryRead | UnusableMemory:
        try:
            if type(request) is not TaskMemoryRequest:
                memory_error()
            request.__post_init__()
        except (ValueError, TypeError, AttributeError, UnicodeError):
            memory_error()
        scope = ContextRequest(
            project_id=request.project_id, task_id=request.task_id, step_id=request.step_id
        )
        with self._factory() as uow:
            uow.begin_formal_read()
            at = uow.task_safety.snapshot_at()
            # Required context failures must never be converted into optional memory loss.
            self._canonical.context_in_uow(uow, principal, scope, at)
            try:
                artifact, manifest = self._manifest_in_uow(uow, request)
            except ResearchBaseError as error:
                if not optional or error.code not in {
                    ErrorCode.NOT_FOUND,
                    ErrorCode.VALIDATION_ERROR,
                }:
                    raise
                return UnusableMemory(
                    code=ErrorCode.NOT_FOUND
                    if error.code == ErrorCode.NOT_FOUND
                    else ErrorCode.VALIDATION_ERROR,
                    reason="MISSING_VERSION"
                    if error.code == ErrorCode.NOT_FOUND
                    else "UNUSABLE_CONTENT",
                )
            # Do not catch source failures here: optional memory grants no disclosure exception.
            return self._resolve_in_uow(uow, scope, at, artifact, manifest)

    @staticmethod
    def _manifest_in_uow(
        uow: ContextUnitOfWork, request: TaskMemoryRequest
    ) -> tuple[ArtifactContext, TaskMemoryManifest]:
        row = uow.research_tasks.input_version(
            InputType.ARTIFACT_VERSION, request.artifact_version_id, request.project_id
        )
        if row is None:
            raise ResearchBaseError(ErrorCode.NOT_FOUND, "exact memory version unavailable")
        # Check scope before size, lifecycle, hash or any content-addressed store access.
        if not row["scoped"]:
            raise ResearchBaseError(ErrorCode.FORBIDDEN, "memory scope unavailable")
        if row["status"] not in {"FROZEN", "SUPERSEDED"} or row["frozen_at"] is None:
            raise ResearchBaseError(ErrorCode.VERSION_NOT_FROZEN, "frozen memory required")
        size = row["byte_size"]
        if type(size) is not int or not 0 <= size <= MAX_MANIFEST_BYTES:
            memory_error()
        try:
            artifact = uow.context_reads.artifact(request.project_id, request.artifact_version_id)
        except ResearchBaseError as error:
            if error.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION:
                memory_error()
            raise
        except (OSError, ValueError, TypeError, UnicodeError):
            memory_error()
        if artifact is None:
            raise ResearchBaseError(ErrorCode.NOT_FOUND, "exact memory version unavailable")
        raw = artifact.verified_bytes
        if (
            artifact.reference.id != request.artifact_version_id
            or artifact.byte_size != size
            or len(raw) != size
            or len(raw) > MAX_MANIFEST_BYTES
            or sha256(raw).hexdigest() != row["content_hash"]
            or artifact.reference.content_hash != row["content_hash"]
        ):
            memory_error()
        manifest = parse_memory_manifest(raw)
        if (
            manifest.project_scope != request.project_id
            or manifest.task_id != request.task_id
            or manifest.step_id != request.step_id
        ):
            raise ResearchBaseError(ErrorCode.FORBIDDEN, "memory scope unavailable")
        return artifact, manifest

    def _resolve_in_uow(
        self,
        uow: ContextUnitOfWork,
        scope: ContextRequest,
        at: datetime,
        artifact: ArtifactContext,
        manifest: TaskMemoryManifest,
    ) -> TaskMemoryRead:
        sources: tuple[CanonicalSource, ...] = tuple(
            self._tasks.resolve_context_binding(uow, scope.project_id, ref.task_input, ref)
            for ref in manifest.source_refs
        )
        observations = (artifact.validity, *(source.validity for source in sources))
        precedence = {"VALID": 0, "UNASSESSED": 1, "UNKNOWN": 2, "STALE": 3, "INVALID": 4}
        # Saved trust/validity never participate in this current-snapshot projection.
        current = max(observations, key=lambda view: precedence[view.status])
        warnings = tuple(dict.fromkeys(w for view in observations for w in view.warnings))
        validity = ValidityObservation(
            status=current.status,
            assessment_ids=tuple(
                sorted({key for view in observations for key in view.assessment_ids}, key=str)
            ),
            warnings=warnings,
        )
        return TaskMemoryRead(
            snapshot_at=at,
            scope=scope,
            artifact_version_id=artifact.reference.id,
            content_hash=artifact.reference.content_hash,
            byte_size=artifact.byte_size,
            verified_bytes=artifact.verified_bytes,
            manifest=manifest,
            current_sources=sources,
            derived_trust_level="SOURCE_VERIFIED",
            current_validity=validity,
            warnings=warnings,
        )
