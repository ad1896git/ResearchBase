"""Closed stored gateway rows and read/lock boundary; no command admission or dispatch."""

from collections.abc import Callable
from datetime import datetime
from typing import Any, Protocol, TypedDict
from uuid import UUID

from researchbase.agent_runtime.ports.task_safety_repository import TaskSafetyRepository


class StoredToolPolicy(TypedDict):
    id: UUID
    project_id: UUID
    registration_task_id: UUID
    receipt_id: UUID
    version: str
    capability_set_hash: str
    max_tool_calls: int
    max_parallel_invocations: int
    filesystem_scope: str
    network_scope: str
    compute_scope: str
    external_effect_scope: str
    registry_artifact_version_id: UUID
    registry_content_hash: str
    content_hash: str
    hash_scheme: str
    created_by: UUID
    created_at: datetime


class StoredPermission(TypedDict):
    id: UUID
    policy_id: UUID
    project_id: UUID
    capability_id: str
    capability_version: str
    operation: str
    adapter_id: str
    adapter_version: str
    parameter_schema_hash: str
    effect: str


class StoredInvocation(TypedDict):
    id: UUID
    project_id: UUID
    research_task_id: UUID
    step_id: UUID | None
    agent_version_id: UUID
    agent_actor_id: UUID
    requested_by: UUID
    policy_id: UUID
    policy_content_hash: str
    mode: str
    capability_id: str
    capability_version: str
    operation: str
    adapter_id: str
    adapter_version: str
    parameter_schema_hash: str
    skill_id: str
    skill_version: str
    strategy_id: str
    strategy_version: str
    harness_artifact_version_id: UUID
    harness_content_hash: str
    parameters_artifact_version_id: UUID
    parameters_content_hash: str
    requested_parameters_hash: str
    parameters_byte_size: int
    reservation_id: UUID
    usage_record_id: UUID | None
    trace_artifact_version_id: UUID | None
    trace_content_hash: str | None
    retry_parent_id: UUID | None
    status: str
    row_version: int
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    request_receipt_id: UUID
    start_receipt_id: UUID | None
    finish_receipt_id: UUID | None
    result_summary: str | None
    error_code: str | None


class StoredInvocationRef(TypedDict):
    id: UUID
    project_id: UUID
    research_task_id: UUID
    invocation_id: UUID
    receipt_id: UUID
    direction: str
    research_question_version_id: UUID | None
    hypothesis_version_id: UUID | None
    claim_version_id: UUID | None
    source_version_id: UUID | None
    artifact_version_id: UUID | None
    manuscript_version_id: UUID | None
    content_hash: str
    hash_scheme: str | None


class StoredInvocationEvent(TypedDict):
    id: UUID
    project_id: UUID
    research_task_id: UUID
    invocation_id: UUID
    reservation_id: UUID
    receipt_id: UUID
    sequence: int
    invocation_row_version: int
    event_type: str
    prior_status: str | None
    new_status: str
    reconciled_outcome: str | None
    usage_record_id: UUID | None
    actor_id: UUID
    occurred_at: datetime
    reason: str


class StoredGatewayReceipt(TypedDict):
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


class StoredTaskEvent(TypedDict):
    id: UUID
    research_task_id: UUID
    actor_id: UUID
    command_id: UUID
    event_type: str
    sequence: int
    task_row_version: int
    prior_status: str | None
    new_status: str
    reason: str | None
    occurred_at: datetime
    stop_human: bool
    stop_policy: bool
    stop_budget: bool
    stop_repeated_failure: bool
    stop_no_improvement: bool
    stop_success: bool
    result_tool_policy_id: UUID | None
    result_capability_invocation_id: UUID | None
    result_capability_event_id: UUID | None


class GatewayRepository(TaskSafetyRepository, Protocol):
    def lock_gateway(
        self,
        project: UUID,
        actor: UUID,
        command: UUID,
        task: UUID,
        *,
        agent_version: UUID | None = None,
        after_wait: Callable[[], object] | None = None,
    ) -> None: ...
    def policy(self, project: UUID, identity: UUID) -> StoredToolPolicy | None: ...
    def permissions(self, project: UUID, policy: UUID) -> list[StoredPermission]: ...
    def invocation(self, project: UUID, task: UUID, identity: UUID) -> StoredInvocation | None: ...
    def invocation_refs(
        self, project: UUID, task: UUID, invocation: UUID
    ) -> list[StoredInvocationRef]: ...
    def invocation_events(
        self, project: UUID, task: UUID, invocation: UUID
    ) -> list[StoredInvocationEvent]: ...
    def gateway_receipt(
        self, project: UUID, actor: UUID, command: UUID
    ) -> StoredGatewayReceipt | None: ...
    def gateway_task_events(self, task: UUID) -> list[StoredTaskEvent]: ...

    def committed_receipt(
        self, project: UUID, actor: UUID, command: UUID
    ) -> dict[str, Any] | None: ...
    def gateway_result(self, receipt: dict[str, Any], *, replayed: bool) -> Any: ...
    def policy_version_occupied(self, project: UUID, version: str) -> bool: ...
    def gateway_identity_occupied(self, table: str, identity: UUID) -> bool: ...
    def task_invocations(self, project: UUID, task: UUID) -> list[dict[str, Any]]: ...
    def agent_version(self, identity: UUID) -> dict[str, Any] | None: ...
    def agent_availability(self, identity: UUID) -> dict[str, Any] | None: ...
    def live_agent(self, actor: UUID, project: UUID) -> bool: ...
    def artifact_pin(self, project: UUID, identity: UUID) -> dict[str, Any] | None: ...
