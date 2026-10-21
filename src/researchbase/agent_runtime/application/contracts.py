"""Immutable closed planning commands and read projections, independent of transports."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from researchbase.agent_runtime.domain.research_task import (
    EXECUTION_COMMANDS,
    UNMET_PREREQUISITES,
    AutonomyLevel,
    TaskType,
    exact_uuid,
    invalid,
    text_value,
)
from researchbase.agent_runtime.domain.task_graph import unique
from researchbase.agent_runtime.domain.task_step import StepType
from researchbase.foundation.hashing import sha256_canonical_json


class InputType(StrEnum):
    RESEARCH_QUESTION_VERSION = "RESEARCH_QUESTION_VERSION"
    HYPOTHESIS_VERSION = "HYPOTHESIS_VERSION"
    CLAIM_VERSION = "CLAIM_VERSION"
    SOURCE_VERSION = "SOURCE_VERSION"
    ARTIFACT_VERSION = "ARTIFACT_VERSION"
    MANUSCRIPT_VERSION = "MANUSCRIPT_VERSION"


def enum_value(kind, value):
    try:
        return kind(value)
    except (ValueError, TypeError):
        invalid("unknown enum value")


def positive(value: int) -> None:
    if type(value) is not int or value < 1:
        invalid("positive integer required")


@dataclass(frozen=True, slots=True)
class TaskInput:
    type: InputType
    id: UUID

    def __post_init__(self):
        object.__setattr__(self, "type", enum_value(InputType, self.type))
        exact_uuid(self.id)


def normalized_inputs(values: tuple[TaskInput, ...]) -> tuple[TaskInput, ...]:
    if not isinstance(values, tuple) or any(not isinstance(v, TaskInput) for v in values):
        invalid("typed input tuple required")
    unique([(v.type, v.id) for v in values], "duplicate typed input")
    return tuple(sorted(values, key=lambda v: (v.type, str(v.id))))


@dataclass(frozen=True, slots=True)
class PlanNode:
    step_id: UUID
    step_type: StepType
    ordinal: int
    parent_step_id: UUID | None = None
    agent_role: str | None = None
    capability_id: str | None = None
    inputs: tuple[TaskInput, ...] = ()

    def __post_init__(self):
        exact_uuid(self.step_id, stable=True)
        if self.parent_step_id is not None:
            exact_uuid(self.parent_step_id, stable=True)
        positive(self.ordinal)
        object.__setattr__(self, "step_type", enum_value(StepType, self.step_type))
        for field in ("agent_role", "capability_id"):
            if getattr(self, field) is not None:
                object.__setattr__(self, field, text_value(getattr(self, field), 128))
        object.__setattr__(self, "inputs", normalized_inputs(self.inputs))


@dataclass(frozen=True, slots=True)
class PlanEdge:
    predecessor_id: UUID
    dependent_id: UUID

    def __post_init__(self):
        exact_uuid(self.predecessor_id, stable=True)
        exact_uuid(self.dependent_id, stable=True)


@dataclass(frozen=True, slots=True)
class CreateTaskArguments:
    task_type: TaskType
    objective: str
    strategy_id: str
    strategy_version: str
    autonomy_level: AutonomyLevel = AutonomyLevel.A0
    inputs: tuple[TaskInput, ...] = ()

    def __post_init__(self):
        object.__setattr__(self, "task_type", enum_value(TaskType, self.task_type))
        object.__setattr__(self, "autonomy_level", enum_value(AutonomyLevel, self.autonomy_level))
        object.__setattr__(self, "objective", text_value(self.objective, 8192))
        for name in ("strategy_id", "strategy_version"):
            object.__setattr__(self, name, text_value(getattr(self, name), strategy=True))
        object.__setattr__(self, "inputs", normalized_inputs(self.inputs))
        if len(self.inputs) > 256:
            invalid("input admission limit exceeded")


@dataclass(frozen=True, slots=True)
class CreatePlanArguments:
    nodes: tuple[PlanNode, ...]
    edges: tuple[PlanEdge, ...] = ()

    def __post_init__(self):
        if not self.nodes:
            invalid("initial plan must be nonempty")
        unique([n.step_id for n in self.nodes], "duplicate step")
        unique([n.ordinal for n in self.nodes], "duplicate ordinal")
        unique([(e.predecessor_id, e.dependent_id) for e in self.edges], "duplicate edge")
        object.__setattr__(self, "nodes", tuple(sorted(self.nodes, key=lambda n: str(n.step_id))))
        object.__setattr__(
            self,
            "edges",
            tuple(sorted(self.edges, key=lambda e: (str(e.predecessor_id), str(e.dependent_id)))),
        )


@dataclass(frozen=True, slots=True)
class AddStepArguments:
    node: PlanNode
    predecessor_ids: tuple[UUID, ...] = ()

    def __post_init__(self):
        for identity in self.predecessor_ids:
            exact_uuid(identity, stable=True)
        unique(self.predecessor_ids, "duplicate predecessor")
        object.__setattr__(self, "predecessor_ids", tuple(sorted(self.predecessor_ids, key=str)))


@dataclass(frozen=True, slots=True)
class CancelArguments:
    reason: str

    def __post_init__(self):
        object.__setattr__(self, "reason", text_value(self.reason))


@dataclass(frozen=True, slots=True)
class EmptyArguments:
    pass


@dataclass(frozen=True, slots=True)
class StepExecutionArguments:
    step_id: UUID

    def __post_init__(self):
        exact_uuid(self.step_id, stable=True)


_ARGUMENTS = {
    "create_research_task": CreateTaskArguments,
    "create_task_plan": CreatePlanArguments,
    "add_task_step": AddStepArguments,
    "add_task_step_dependency": PlanEdge,
    "seal_task_plan": EmptyArguments,
    "cancel_research_task": CancelArguments,
    **{
        name: StepExecutionArguments if "task_step" in name else EmptyArguments
        for name in EXECUTION_COMMANDS
    },
}
Arguments = (
    CreateTaskArguments
    | CreatePlanArguments
    | AddStepArguments
    | PlanEdge
    | CancelArguments
    | EmptyArguments
    | StepExecutionArguments
)


@dataclass(frozen=True, slots=True)
class TaskCommand:
    project_id: UUID
    command_id: UUID
    task_id: UUID
    expected_row_version: int | None
    command_name: str
    arguments: Arguments

    def __post_init__(self):
        exact_uuid(self.project_id)
        exact_uuid(self.command_id)
        exact_uuid(self.task_id, stable=True)
        if (
            self.command_name not in _ARGUMENTS
            or type(self.arguments) is not _ARGUMENTS[self.command_name]
        ):
            invalid("closed command arguments required")
        if self.command_name == "create_research_task":
            if self.expected_row_version is not None:
                invalid("create expected revision must be null")
        else:
            positive(self.expected_row_version)  # type: ignore[arg-type]

    def material(self, actor_id: UUID) -> dict[str, Any]:
        exact_uuid(actor_id)
        return {
            "type": "ResearchTaskCommand",
            "material_version": 1,
            "command_name": self.command_name,
            "project_id": str(self.project_id),
            "actor_id": str(actor_id),
            "command_id": str(self.command_id),
            "task_id": str(self.task_id),
            "expected_row_version": self.expected_row_version,
            "arguments": json_value(self.arguments),
        }

    def request_hash(self, actor_id: UUID) -> str:
        return str(sha256_canonical_json(self.material(actor_id)))


def json_value(value):
    if hasattr(value, "__dataclass_fields__"):
        return {k: json_value(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {k: json_value(v) for k, v in value.items()}
    if isinstance(value, tuple | list):
        return [json_value(v) for v in value]
    if isinstance(value, UUID):
        return str(value)
    return value


def parse_command(name: str, data: dict) -> TaskCommand:
    """Shared closed HTTP/CLI decoder; only submitted-field errors escape validation."""
    try:
        allowed = {"project_id", "command_id", "task_id", "expected_row_version", "arguments"}
        if set(data) - allowed or not {"project_id", "command_id", "task_id", "arguments"} <= set(
            data
        ):
            invalid("unknown or missing command fields")

        def closed(kind, raw, transforms=None):
            if not isinstance(raw, dict) or set(raw) - {f.name for f in fields(kind)}:
                invalid("unknown argument fields")
            raw = dict(raw)
            for key, fn in (transforms or {}).items():
                if key in raw:
                    raw[key] = fn(raw[key])
            return kind(**raw)

        def uuid(raw):
            if isinstance(raw, UUID):
                return raw
            return UUID(raw)

        def sequence(raw):
            if not isinstance(raw, tuple | list):
                invalid("array required")
            return raw

        def inputs(raw):
            return tuple(closed(TaskInput, v, {"id": uuid}) for v in sequence(raw))

        def node(raw):
            return closed(
                PlanNode,
                raw,
                {
                    "step_id": uuid,
                    "parent_step_id": lambda v: uuid(v) if v is not None else None,
                    "inputs": inputs,
                },
            )

        def edge(raw):
            return closed(PlanEdge, raw, {"predecessor_id": uuid, "dependent_id": uuid})

        kind = _ARGUMENTS[name]
        transforms = (
            {"inputs": inputs}
            if kind is CreateTaskArguments
            else {
                "nodes": lambda v: tuple(node(n) for n in sequence(v)),
                "edges": lambda v: tuple(edge(e) for e in sequence(v)),
            }
            if kind is CreatePlanArguments
            else {"node": node, "predecessor_ids": lambda v: tuple(uuid(i) for i in sequence(v))}
            if kind is AddStepArguments
            else {"predecessor_id": uuid, "dependent_id": uuid}
            if kind is PlanEdge
            else {"step_id": uuid}
            if kind is StepExecutionArguments
            else {}
        )
        return TaskCommand(
            uuid(data["project_id"]),
            uuid(data["command_id"]),
            uuid(data["task_id"]),
            data.get("expected_row_version"),
            name,
            closed(kind, data["arguments"], transforms),
        )
    except (ValueError, TypeError, KeyError, AttributeError):
        invalid("invalid closed task command")
        raise AssertionError("unreachable") from None


@dataclass(frozen=True, slots=True)
class InputRead:
    type: str
    id: UUID
    content_hash: str
    hash_scheme: str | None
    validity_warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TaskRead:
    id: UUID
    project_id: UUID
    requested_by: UUID
    task_type: str
    objective: str
    strategy_id: str
    strategy_version: str
    autonomy_level: str
    status: str
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    plan_sealed_at: datetime | None
    current_step_id: UUID | None
    row_version: int
    inputs: tuple[InputRead, ...]
    execution_enabled: bool = False
    unmet_prerequisites: tuple[str, ...] = UNMET_PREREQUISITES


@dataclass(frozen=True, slots=True)
class StepRead:
    id: UUID
    research_task_id: UUID
    step_type: str
    ordinal: int
    parent_step_id: UUID | None
    status: str
    agent_role: str | None
    capability_id: str | None
    started_at: datetime | None
    finished_at: datetime | None
    retry_count: int
    failure_code: str | None
    row_version: int
    inputs: tuple[InputRead, ...]
    outputs: tuple = ()


@dataclass(frozen=True, slots=True)
class TaskEventRead:
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


@dataclass(frozen=True, slots=True)
class StepEventRead:
    id: UUID
    research_task_id: UUID
    step_id: UUID
    actor_id: UUID
    command_id: UUID
    event_type: str
    sequence: int
    step_row_version: int
    task_row_version: int
    prior_status: str | None
    new_status: str
    reason: str | None
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class TaskGraphRead:
    task: TaskRead
    nodes: tuple[StepRead, ...]
    edges: tuple[PlanEdge, ...]
    task_events: tuple[TaskEventRead, ...]
    step_events: tuple[StepEventRead, ...]


@dataclass(frozen=True, slots=True)
class ProgressCounts:
    PENDING: int = 0
    READY: int = 0
    RUNNING: int = 0
    WAITING: int = 0
    SUCCEEDED: int = 0
    FAILED: int = 0
    SKIPPED: int = 0
    CANCELLED: int = 0


@dataclass(frozen=True, slots=True)
class TaskProgressRead:
    task_id: UUID
    task_row_version: int
    task_status: str
    total_steps: int
    counts: ProgressCounts
    completed_steps: int = 0
    completion_percent: float = 0
    execution_enabled: bool = False
    unmet_prerequisites: tuple[str, ...] = UNMET_PREREQUISITES


@dataclass(frozen=True, slots=True)
class CommandResult:
    task_id: UUID
    resulting_row_version: int
    task_event_ids: tuple[UUID, ...]
    step_event_ids: tuple[UUID, ...]
    replayed: bool
