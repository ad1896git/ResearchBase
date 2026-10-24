"""Read capabilities only. Every port belongs to the same formal-read session.

Rows below are private adapter/composition values, never public result payloads.
No protocol inherits a writer, Session, commit, lock or ArtifactStore write method.
Owning-domain verification must use this UoW's session, never a public query wrapper.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime
from types import TracebackType
from typing import Protocol, Self
from uuid import UUID

from researchbase.agent_runtime.application.context_contracts import (
    ArtifactContext,
    CanonicalContext,
    CanonicalSource,
    ContextRequest,
    InputBinding,
    PromotionContextRequest,
    PromotionContextValidation,
    SourceReference,
    TaskContext,
    TaskMemoryRead,
    TaskMemoryRequest,
    ValidityObservation,
)
from researchbase.agent_runtime.application.contracts import TaskInput
from researchbase.domain.phase2_identity import VerifiedPrincipal

type ReadRow = Mapping[str, object]


class TaskContextReadRepository(Protocol):
    """Read subset for delivered same-UoW task admission and input resolution."""

    def authority(self, principal: VerifiedPrincipal, project: UUID) -> tuple[ReadRow, ...]: ...
    def project_active(self, project: UUID) -> bool: ...
    def task(self, identity: UUID) -> ReadRow | None: ...
    def steps(self, task: UUID) -> tuple[ReadRow, ...]: ...
    def inputs(self, task: UUID, *, step: bool = False) -> tuple[ReadRow, ...]: ...
    def input_version(self, kind: str, identity: UUID, project: UUID) -> ReadRow | None: ...


class SafetyContextReadRepository(Protocol):
    """Reads required by safety_projection/verify_saved_policies, with no lock option."""

    def snapshot_at(self) -> datetime: ...
    def rows(self, table: str, task: UUID) -> tuple[ReadRow, ...]: ...
    def scope_reference(self, kind: str, identity: UUID, project: UUID) -> ReadRow | None: ...
    def events(self, task: UUID, *, step: bool = False) -> tuple[ReadRow, ...]: ...


class ContextRepository(Protocol):
    """Narrow scoped projections, not a second source of scientific truth.

    Application must admit the principal/project before invoking these methods.
    Implementations scope each node *before* any expansion or protected diagnostic.
    Missing entitled identities return None; foreign/global dependencies raise a
    sanitized FORBIDDEN rather than returning partial rows or a partial graph.
    """

    def task_context(self, scope: ContextRequest) -> TaskContext | None: ...
    def bindings(self, scope: ContextRequest) -> tuple[InputBinding, ...]: ...
    def source(self, project: UUID, reference: TaskInput) -> CanonicalSource | None: ...
    def validity(self, project: UUID, reference: TaskInput) -> ValidityObservation: ...
    def artifact(self, project: UUID, version: UUID) -> ArtifactContext | None: ...
    def verify_source(self, project: UUID, reference: SourceReference) -> None: ...


class ContextUnitOfWork(Protocol):
    """One query, one snapshot; begin_formal_read precedes all Application SQL.

    REPEATABLE READ READ ONLY, autoflush disabled; capture task_safety.snapshot_at
    exactly once. Exit rolls back/closes the read. No nested transaction/session,
    flush, commit, explicit exclusion lock, repair or provider I/O is permitted.
    """

    @property
    def research_tasks(self) -> TaskContextReadRepository: ...
    @property
    def task_safety(self) -> SafetyContextReadRepository: ...
    @property
    def context_reads(self) -> ContextRepository: ...
    def begin_formal_read(self) -> None: ...
    def __enter__(self) -> Self: ...
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...


type ContextUowFactory = Callable[[], ContextUnitOfWork]


class CanonicalContextLoader(Protocol):
    def load_for_task(
        self, principal: VerifiedPrincipal, request: ContextRequest
    ) -> CanonicalContext: ...


class ContextReadQueries(Protocol):
    """Common Human/Agent Application boundary; principal is never a request field."""

    def get_canonical_context_for_task(
        self, principal: VerifiedPrincipal, request: ContextRequest
    ) -> CanonicalContext: ...
    def get_task_working_memory(
        self, principal: VerifiedPrincipal, request: TaskMemoryRequest
    ) -> TaskMemoryRead: ...
    def validate_promotion_context(
        self, principal: VerifiedPrincipal, request: PromotionContextRequest
    ) -> PromotionContextValidation: ...
