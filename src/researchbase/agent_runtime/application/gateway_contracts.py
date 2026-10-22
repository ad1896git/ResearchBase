"""Immutable gateway vocabulary and closed parsers; no command execution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar
from uuid import UUID

from researchbase.agent_runtime.domain.agent_version import digest_value
from researchbase.agent_runtime.domain.capability_invocation import (
    FAMILIES,
    TERMINAL,
    ClosedValue,
    FakeParameters,
    GatewayRef,
    bounded_text,
    material,
    pin,
    refs,
    require_transition,
    typed,
)
from researchbase.agent_runtime.domain.research_task import exact_uuid, invalid
from researchbase.agent_runtime.domain.task_safety import ResourceVector, integer
from researchbase.agent_runtime.domain.tool_policy import (
    PermissionKey,
    PermissionSpec,
    ToolPolicySpec,
)
from researchbase.agent_runtime.ports.task_safety_repository import FakeConsumerCapability
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import sha256_canonical_json


@dataclass(frozen=True, slots=True)
class RegisterToolPolicyArguments(ClosedValue):
    policy_id: UUID
    policy: ToolPolicySpec
    reason: str

    def __post_init__(self):
        ClosedValue.__post_init__(self)
        exact_uuid(self.policy_id, stable=True)
        bounded_text(self.reason)


@dataclass(frozen=True, slots=True)
class RequestInvocationArguments(ClosedValue):
    invocation_id: UUID
    step_id: UUID | None
    agent_version_id: UUID
    policy_id: UUID
    policy_content_hash: str
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
    parameters: FakeParameters
    input_refs: tuple[GatewayRef, ...]
    retry_parent_id: UUID | None
    deadline_seconds: int
    reason: str

    def __post_init__(self):
        ClosedValue.__post_init__(self)
        exact_uuid(self.invocation_id, stable=True)
        self.permission_key()
        for name in ("skill_id", "skill_version", "strategy_id", "strategy_version"):
            object.__setattr__(
                self, name, pin(getattr(self, name), 128 if name.endswith("_id") else 512)
            )
        for name in (
            "policy_content_hash",
            "harness_content_hash",
            "parameters_content_hash",
            "requested_parameters_hash",
        ):
            digest_value(getattr(self, name))
        integer(self.parameters_byte_size, minimum=1, maximum=65536)
        integer(self.deadline_seconds, minimum=1, maximum=60)
        if (
            self.parameters_byte_size != len(self.parameters.canonical_bytes())
            or self.requested_parameters_hash != self.parameters.digest()
        ):
            invalid("parameter canonical bytes and digest disagree")
        if self.retry_parent_id == self.invocation_id:
            invalid("invocation cannot retry itself")
        object.__setattr__(self, "input_refs", refs(self.input_refs))
        bounded_text(self.reason)

    def verify_retained_parameters(self, supplied: bytes, owning_hash: str, owning_size: int):
        digest_value(owning_hash)
        integer(owning_size, minimum=1, maximum=65536)
        if (
            type(supplied) is not bytes
            or supplied != self.parameters.canonical_bytes()
            or len(supplied) != owning_size
            or owning_size != self.parameters_byte_size
            or owning_hash != self.parameters_content_hash
        ):
            invalid("retained owning pins and parameter bytes disagree")

    def permission_key(self):
        return PermissionKey(
            self.capability_id,
            self.capability_version,
            self.operation,
            self.adapter_id,
            self.adapter_version,
            self.parameter_schema_hash,
        )


@dataclass(frozen=True, slots=True)
class StartInvocationArguments(ClosedValue):
    invocation_id: UUID
    expected_invocation_revision: int
    reason: str

    def __post_init__(self):
        ClosedValue.__post_init__(self)
        integer(self.expected_invocation_revision, minimum=1)
        bounded_text(self.reason)


@dataclass(frozen=True, slots=True)
class FinishInvocationArguments(ClosedValue):
    invocation_id: UUID
    expected_invocation_revision: int
    kind: str
    outcome: str
    measured: ResourceVector
    output_refs: tuple[GatewayRef, ...]
    trace_artifact_version_id: UUID | None
    trace_content_hash: str | None
    result_summary: str | None
    error_code: str | None
    reason: str

    def __post_init__(self):
        ClosedValue.__post_init__(self)
        integer(self.expected_invocation_revision, minimum=1)
        bounded_text(self.reason)
        object.__setattr__(self, "output_refs", refs(self.output_refs, output=True))
        if self.outcome not in TERMINAL or self.kind not in ("FINISH", "RECONCILE"):
            invalid("closed finish observation required")
        if (self.trace_artifact_version_id is None) != (self.trace_content_hash is None):
            invalid("trace pin must be complete")
        if self.trace_content_hash is not None:
            digest_value(self.trace_content_hash)
        if self.result_summary is not None:
            bounded_text(self.result_summary, byte_limit=True, blank=True)
        if self.kind == "RECONCILE":
            if self.outcome == "UNKNOWN_OUTCOME" or any(
                v is not None
                for v in (
                    self.trace_artifact_version_id,
                    self.trace_content_hash,
                    self.result_summary,
                    self.error_code,
                )
            ):
                invalid("reconciliation preserves the original observation")
        else:
            expected = {
                "FAILED": "ADAPTER_UNAVAILABLE",
                "UNKNOWN_OUTCOME": "INVALID_STATE_TRANSITION",
            }.get(self.outcome)
            if self.error_code != expected:
                invalid("outcome error code disagrees")
        if self.outcome != "SUCCEEDED" and self.output_refs:
            invalid("only success may supply outputs")


_ARGUMENTS = {
    "register_agent_tool_policy": RegisterToolPolicyArguments,
    "request_capability_invocation": RequestInvocationArguments,
    "start_capability_invocation": StartInvocationArguments,
    "finish_capability_invocation": FinishInvocationArguments,
}


@dataclass(frozen=True, slots=True)
class GatewayCommand(ClosedValue):
    project_id: UUID
    task_id: UUID
    command_id: UUID
    expected_row_version: int
    command_name: str
    arguments: (
        RegisterToolPolicyArguments
        | RequestInvocationArguments
        | StartInvocationArguments
        | FinishInvocationArguments
    )

    def __post_init__(self):
        ClosedValue.__post_init__(self)
        exact_uuid(self.task_id, stable=True)
        integer(self.expected_row_version, minimum=1)
        if type(self.arguments) is not _ARGUMENTS.get(self.command_name):
            invalid("closed command variant required")

    def material(self, actor_id: UUID):
        exact_uuid(actor_id)
        return {
            "type": "GatewayCommand",
            "material_version": 1,
            **material(self),
            "actor_id": str(actor_id),
        }

    def request_hash(self, actor_id: UUID):
        return str(sha256_canonical_json(self.material(actor_id)))


def parse_gateway_command(name: str, data: dict, *, observation=None) -> GatewayCommand:
    """Public parsing never establishes trust in a submitted finish observation."""
    try:
        if type(data) is not dict or set(data) != {
            "project_id",
            "task_id",
            "command_id",
            "expected_row_version",
            "arguments",
        }:
            invalid("unknown or missing command fields")
        kind = _ARGUMENTS[name]
        args = typed(kind, data["arguments"], decode=True)
        if kind is FinishInvocationArguments:
            if type(observation) is not FinishInvocationArguments or observation != args:
                raise ResearchBaseError(ErrorCode.FORBIDDEN, "trusted observation required")
            args = observation
        raw: dict[str, Any] = dict(data, command_name=name, arguments=args)
        for key in ("project_id", "task_id", "command_id"):
            raw[key] = typed(UUID, raw[key], decode=True)
        return GatewayCommand(**raw)
    except (ValueError, TypeError, KeyError, AttributeError):
        invalid("invalid closed gateway command")


@dataclass(frozen=True, slots=True)
class CapabilityRequest(ClosedValue):
    request_command_id: UUID
    start_command_id: UUID
    finish_command_id: UUID
    expected_row_version: int
    arguments: RequestInvocationArguments

    def __post_init__(self):
        ClosedValue.__post_init__(self)
        integer(self.expected_row_version, minimum=1)
        if len({self.request_command_id, self.start_command_id, self.finish_command_id}) != 3:
            invalid("three distinct stable command IDs required")


@dataclass(frozen=True, slots=True)
class AgentExecutionContext:
    __trusted_context__: ClassVar[bool] = True

    principal: VerifiedPrincipal
    project_id: UUID
    task_id: UUID
    step_id: UUID | None
    agent_version_id: UUID
    harness_artifact_version_id: UUID
    harness_content_hash: str
    consumer_capability: FakeConsumerCapability

    def __post_init__(self):
        for name in ("project_id", "task_id", "agent_version_id", "harness_artifact_version_id"):
            exact_uuid(getattr(self, name))
        if self.step_id is not None:
            exact_uuid(self.step_id)
        digest_value(self.harness_content_hash)
        if (
            type(self.principal) is not VerifiedPrincipal
            or type(self.consumer_capability) is not FakeConsumerCapability
        ):
            invalid("injected trusted context required")

    def __getstate__(self):
        raise TypeError("trusted context is not serializable")


@dataclass(frozen=True, slots=True)
class GatewayCommandResult(ClosedValue):
    receipt_id: UUID
    project_id: UUID
    task_id: UUID
    actor_id: UUID
    command_id: UUID
    command_name: str
    policy_id: UUID
    invocation_id: UUID | None
    invocation_event_id: UUID | None
    reservation_id: UUID | None
    usage_record_id: UUID | None
    resulting_row_version: int
    resulting_invocation_revision: int | None
    completed_at: datetime
    replayed: bool

    def __post_init__(self):
        ClosedValue.__post_init__(self)
        if self.command_name not in _ARGUMENTS:
            invalid("unknown gateway command result")
        integer(self.resulting_row_version, minimum=1)
        if self.resulting_invocation_revision is not None:
            integer(self.resulting_invocation_revision, minimum=1, maximum=3)


@dataclass(frozen=True, slots=True)
class CapabilityResult(ClosedValue):
    invocation_id: UUID
    outcome: str
    output_refs: tuple[GatewayRef, ...]
    trace_artifact_version_id: UUID | None
    resource_usage: ResourceVector
    error_code: str | None
    result_summary: str | None

    def __post_init__(self):
        ClosedValue.__post_init__(self)
        if self.outcome not in TERMINAL:
            invalid("terminal outcome required")
        object.__setattr__(self, "output_refs", refs(self.output_refs, output=True))
        if self.result_summary is not None:
            bounded_text(self.result_summary, byte_limit=True, blank=True)
        expected = {
            "FAILED": "ADAPTER_UNAVAILABLE",
            "UNKNOWN_OUTCOME": "INVALID_STATE_TRANSITION",
        }.get(self.outcome)
        if self.error_code != expected or (self.outcome != "SUCCEEDED" and self.output_refs):
            invalid("result outcome disagrees")


@dataclass(frozen=True, slots=True)
class AgentToolPolicyRead(ClosedValue):
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
    permissions: tuple[PermissionSpec, ...]

    def __post_init__(self):
        ClosedValue.__post_init__(self)
        value = ToolPolicySpec(
            self.version,
            self.permissions,
            self.registry_artifact_version_id,
            self.registry_content_hash,
            self.capability_set_hash,
            self.max_tool_calls,
            self.max_parallel_invocations,
            self.filesystem_scope,
            self.network_scope,
            self.compute_scope,
            self.external_effect_scope,
        )
        object.__setattr__(self, "permissions", value.permissions)
        if self.hash_scheme != "sha256-cjson-v1" or self.content_hash != value.digest(
            self.project_id
        ):
            invalid("stored policy hash material disagrees")


@dataclass(frozen=True, slots=True)
class GatewayRefRead(ClosedValue):
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
    validity_warnings: tuple[str, ...]

    def __post_init__(self):
        ClosedValue.__post_init__(self)
        columns = (
            "research_question_version_id",
            "hypothesis_version_id",
            "claim_version_id",
            "source_version_id",
            "artifact_version_id",
            "manuscript_version_id",
        )
        targets = [
            (family, getattr(self, col))
            for family, col in zip(FAMILIES, columns, strict=True)
            if getattr(self, col) is not None
        ]
        if len(targets) != 1 or self.direction not in ("INPUT", "OUTPUT"):
            invalid("one concrete reference target and direction required")
        value = GatewayRef(targets[0][0], targets[0][1], self.content_hash, self.hash_scheme)
        refs((value,), output=self.direction == "OUTPUT")
        for warning in self.validity_warnings:
            bounded_text(warning)


@dataclass(frozen=True, slots=True)
class CapabilityEventRead(ClosedValue):
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

    def __post_init__(self):
        ClosedValue.__post_init__(self)
        bounded_text(self.reason)
        integer(self.sequence, minimum=1, maximum=4)
        integer(self.invocation_row_version, minimum=1, maximum=3)
        if self.event_type == "REQUESTED":
            if (
                self.sequence,
                self.invocation_row_version,
                self.prior_status,
                self.new_status,
                self.usage_record_id,
                self.reconciled_outcome,
            ) != (1, 1, None, "REQUESTED", None, None):
                invalid("invalid requested event")
            return
        action = {"STARTED": "START", "FINISHED": "FINISH", "RECONCILED": "RECONCILE"}.get(
            self.event_type
        )
        outcome = (
            self.reconciled_outcome
            if action == "RECONCILE"
            else (None if action == "START" else self.new_status)
        )
        target = require_transition(self.prior_status, action, outcome, no_dispatch=True)
        expected_revision = 2 if self.prior_status == "REQUESTED" else 3
        expected_sequence = 4 if action == "RECONCILE" else expected_revision
        if (
            target != self.new_status
            or self.invocation_row_version != expected_revision
            or self.sequence != expected_sequence
            or (self.usage_record_id is None) != (action == "START")
            or (self.reconciled_outcome is not None) != (action == "RECONCILE")
        ):
            invalid("event lifecycle fields disagree")


@dataclass(frozen=True, slots=True)
class CapabilityInvocationRead(ClosedValue):
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
    refs: tuple[GatewayRefRead, ...]
    events: tuple[CapabilityEventRead, ...]
    effective_outcome: str | None
    effective_usage_record_id: UUID | None
    current_availability: str
    execution_enabled: bool = False

    def __post_init__(self):
        ClosedValue.__post_init__(self)
        if self.execution_enabled is not False or self.mode != "CONTRACT_FAKE":
            invalid("execution remains disabled outside CONTRACT_FAKE")
        if self.status not in ("REQUESTED", "RUNNING", *TERMINAL):
            invalid("closed invocation status required")
        if self.effective_outcome is not None and self.effective_outcome not in TERMINAL:
            invalid("closed snapshot outcome required")
        if self.current_availability not in ("ACTIVE", "DISABLED", "RETIRED"):
            invalid("closed snapshot availability required")
        integer(self.row_version, minimum=1, maximum=3)
        integer(self.parameters_byte_size, minimum=1, maximum=65536)
        PermissionKey(
            self.capability_id,
            self.capability_version,
            self.operation,
            self.adapter_id,
            self.adapter_version,
            self.parameter_schema_hash,
        )
        for name in (
            "policy_content_hash",
            "harness_content_hash",
            "parameters_content_hash",
            "requested_parameters_hash",
        ):
            digest_value(getattr(self, name))
        for name in ("skill_id", "skill_version", "strategy_id", "strategy_version"):
            pin(getattr(self, name), 128 if name.endswith("_id") else 512)
        if (self.trace_artifact_version_id is None) != (self.trace_content_hash is None):
            invalid("complete trace pin required")
        if self.trace_content_hash is not None:
            digest_value(self.trace_content_hash)
        if self.result_summary is not None:
            bounded_text(self.result_summary, byte_limit=True, blank=True)
        expected_error = {
            "FAILED": "ADAPTER_UNAVAILABLE",
            "UNKNOWN_OUTCOME": "INVALID_STATE_TRANSITION",
        }.get(self.status)
        if self.error_code != expected_error:
            invalid("stored outcome error disagrees")
        keys = [
            (
                r.direction,
                r.research_question_version_id,
                r.hypothesis_version_id,
                r.claim_version_id,
                r.source_version_id,
                r.artifact_version_id,
                r.manuscript_version_id,
            )
            for r in self.refs
        ]
        if len(keys) > 256 or len(keys) != len(set(keys)):
            invalid("duplicate or excessive persisted refs")
        if len({e.sequence for e in self.events}) != len(self.events):
            invalid("duplicate invocation event sequence")


@dataclass(frozen=True, slots=True)
class InvocationListCursor(ClosedValue):
    created_at: datetime
    id: UUID


@dataclass(frozen=True, slots=True)
class TaskCapabilityInvocationsRead(ClosedValue):
    task_id: UUID
    invocations: tuple[CapabilityInvocationRead, ...]
    next_cursor: InvocationListCursor | None


def parse_gateway_value(kind, raw):
    """Closed decoder for the §8 DTO vocabulary; no trusted context decoder exists."""
    allowed = (
        PermissionSpec,
        ToolPolicySpec,
        RegisterToolPolicyArguments,
        GatewayRef,
        FakeParameters,
        RequestInvocationArguments,
        StartInvocationArguments,
        GatewayCommandResult,
        CapabilityRequest,
        CapabilityResult,
        AgentToolPolicyRead,
        CapabilityInvocationRead,
        GatewayRefRead,
        CapabilityEventRead,
        InvocationListCursor,
        TaskCapabilityInvocationsRead,
    )
    if kind not in allowed:
        invalid("public gateway value type required")
    return typed(kind, raw, decode=True)
