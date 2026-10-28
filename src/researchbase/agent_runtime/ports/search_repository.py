"""Closed stored search rows and storage stages; Application owns all admission policy.

These are persistence values, not S3 domain values or public query envelopes. The
callback may read current entitlement and committed receipts on this same UoW,
then stop by raising. It must not acquire locks, write, or open another UoW.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Protocol, TypedDict
from uuid import UUID

from researchbase.agent_runtime.ports.task_repository import TaskUnitOfWork

SearchCallerKind = Literal["HUMAN", "AGENT"]
# A principal has no actor kind. Application may resolve it from current authority
# in the first post-SHARE callback, without issuing SQL before the lock prefix.
SearchCallerKindSource = SearchCallerKind | Callable[[], SearchCallerKind]


class StoredSearchSession(TypedDict):
    id: UUID
    project_id: UUID
    research_task_id: UUID
    budget_id: UUID
    root_hypothesis_version_id: UUID | None
    root_hypothesis_content_hash: str | None
    root_experiment_spec_version_id: UUID | None
    root_experiment_spec_content_hash: str | None
    created_by: UUID
    created_at: datetime
    receipt_id: UUID


class StoredSearchNode(TypedDict):
    id: UUID
    research_task_id: UUID
    search_session_id: UUID
    parent_node_id: UUID | None
    depth: int
    branch_kind: str
    mutation_reason: str
    hypothesis_version_id: UUID | None
    hypothesis_content_hash: str | None
    experiment_spec_version_id: UUID | None
    experiment_spec_content_hash: str | None
    reservation_id: UUID
    created_by: UUID
    created_at: datetime
    receipt_id: UUID


class StoredSearchNodeRun(TypedDict):
    id: UUID
    project_id: UUID
    research_task_id: UUID
    search_session_id: UUID
    node_id: UUID
    run_id: UUID
    created_by: UUID
    created_at: datetime
    receipt_id: UUID


class StoredSearchEvent(TypedDict):
    id: UUID
    research_task_id: UUID
    search_session_id: UUID
    node_id: UUID | None
    sequence: int
    event_type: str
    reason: str
    actor_id: UUID
    occurred_at: datetime
    receipt_id: UUID


class StoredSearchReceipt(TypedDict):
    id: UUID
    project_id: UUID
    actor_id: UUID
    command_id: UUID
    command_name: str
    research_task_id: UUID
    request_hash: str
    hash_scheme: str
    material_version: int
    resulting_row_version: int
    completed_at: datetime
    result_tool_policy_id: UUID | None
    result_capability_invocation_id: UUID | None
    result_capability_event_id: UUID | None
    resulting_invocation_revision: int | None
    result_search_session_id: UUID | None
    result_search_node_id: UUID | None
    result_search_event_id: UUID | None


class StoredHypothesisReference(TypedDict):
    id: UUID
    hypothesis_id: UUID
    project_id: UUID
    status: str
    frozen_at: datetime | None
    content_hash: str | None


class StoredExperimentSpecReference(TypedDict):
    id: UUID
    experiment_spec_id: UUID
    project_id: UUID
    status: str
    frozen_at: datetime | None
    content_hash: str | None


class StoredSearchRun(TypedDict):
    id: UUID
    project_id: UUID
    experiment_spec_version_id: UUID
    status: str
    inputs_sealed_at: datetime | None
    created_at: datetime
    finished_at: datetime | None


@dataclass(frozen=True, slots=True)
class SearchStorageStage:
    """A completed storage operation, never an authorization or trust assertion."""

    operation: Literal[
        "share",
        "project",
        "command_key",
        "task_key",
        "actor_key",
        "task_row",
        "step_row",
        "read",
        "insert",
        "update",
        "flush",
        "constraints",
        "final",
    ]
    table: str | None = None
    identity: UUID | None = None


FreshSearchValidation = Callable[[SearchStorageStage], None]


@dataclass(frozen=True, slots=True)
class StoredSearchWriteRows:
    """Uninterpreted retained rows, read in the frozen writer order."""

    events: tuple[StoredSearchEvent, ...]
    nodes: tuple[StoredSearchNode, ...]
    sessions: tuple[StoredSearchSession, ...]
    hypotheses: tuple[StoredHypothesisReference, ...]
    experiment_specs: tuple[StoredExperimentSpecReference, ...]


class SearchRepository(Protocol):
    def lock_write(
        self,
        project: UUID,
        actor: UUID,
        command: UUID,
        task: UUID,
        *,
        caller_kind: SearchCallerKindSource,
        after_stage: FreshSearchValidation,
        hypothesis_versions: tuple[UUID, ...] = (),
        experiment_spec_versions: tuple[UUID, ...] = (),
    ) -> StoredSearchWriteRows: ...
    def committed_receipt(
        self, project: UUID, actor: UUID, command: UUID
    ) -> StoredSearchReceipt | None: ...
    def sessions(self, project: UUID, task: UUID) -> list[StoredSearchSession]: ...
    def nodes(self, task: UUID, session: UUID) -> list[StoredSearchNode]: ...
    def search_events(self, task: UUID, session: UUID) -> list[StoredSearchEvent]: ...
    def events(self, task: UUID, *, step: bool = False) -> list[dict[str, Any]]: ...
    def node_runs(self, project: UUID, task: UUID, session: UUID) -> list[StoredSearchNodeRun]: ...
    def run(self, project: UUID, identity: UUID) -> StoredSearchRun | None: ...
    def hypothesis_version(self, identity: UUID) -> StoredHypothesisReference | None: ...
    def experiment_spec_version(self, identity: UUID) -> StoredExperimentSpecReference | None: ...
    # Existing task/safety row contracts are shared, without another Session/snapshot.
    def task(self, identity: UUID) -> dict[str, Any] | None: ...
    def steps(self, task: UUID) -> list[dict[str, Any]]: ...
    def edges(self, task: UUID) -> list[dict[str, Any]]: ...
    def inputs(self, task: UUID, *, step: bool = False) -> list[dict[str, Any]]: ...
    def rows(self, table: str, task: UUID) -> list[dict[str, Any]]: ...
    def scope_reference(
        self, kind: str, identity: UUID, project: UUID
    ) -> dict[str, Any] | None: ...
    def receipt_history(self, task: UUID) -> list[dict[str, Any]]: ...
    def authority(self, principal: Any, project: UUID) -> list[dict[str, Any]]: ...
    def project_active(self, project: UUID) -> bool: ...
    def at(self) -> datetime: ...
    def snapshot_at(self) -> datetime: ...
    def insert(self, table: str, row: dict[str, Any]) -> None: ...
    def update_task(self, identity: UUID, expected_revision: int) -> None: ...
    def flush(self) -> None: ...
    def force_constraints(self) -> None: ...
    def before_commit(self) -> None: ...


class SearchUnitOfWork(TaskUnitOfWork, Protocol):
    @property
    def experiment_search(self) -> SearchRepository: ...

    def begin_experiment_search(self) -> None: ...


SearchUowFactory = Callable[[], SearchUnitOfWork]
