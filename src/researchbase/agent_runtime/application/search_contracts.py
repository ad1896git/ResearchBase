"""Closed create/append search command material, independent of transports."""

from dataclasses import dataclass, fields
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from researchbase.agent_runtime.application.contracts import CommandResult, enum_value, json_value
from researchbase.agent_runtime.application.safety_contracts import TaskSafetyRead
from researchbase.agent_runtime.domain.experiment_search import BranchKind
from researchbase.agent_runtime.domain.research_task import exact_uuid, invalid, text_value
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import sha256_canonical_json


@dataclass(frozen=True, slots=True)
class CreateSearchArguments:
    session_id: UUID
    root_hypothesis_version_id: UUID | None = None
    root_experiment_spec_version_id: UUID | None = None

    def __post_init__(self) -> None:
        exact_uuid(self.session_id, stable=True)
        for value in (self.root_hypothesis_version_id, self.root_experiment_spec_version_id):
            if value is not None:
                exact_uuid(value)


@dataclass(frozen=True, slots=True)
class AppendSearchArguments:
    session_id: UUID
    node_id: UUID
    branch_kind: BranchKind
    mutation_reason: str
    reservation_id: UUID
    parent_node_id: UUID | None = None
    hypothesis_version_id: UUID | None = None
    experiment_spec_version_id: UUID | None = None

    def __post_init__(self) -> None:
        exact_uuid(self.session_id, stable=True)
        exact_uuid(self.node_id, stable=True)
        exact_uuid(self.reservation_id)
        if self.parent_node_id is not None:
            exact_uuid(self.parent_node_id, stable=True)
            if self.parent_node_id == self.node_id:
                invalid("node cannot parent itself")
        for value in (self.hypothesis_version_id, self.experiment_spec_version_id):
            if value is not None:
                exact_uuid(value)
        object.__setattr__(self, "branch_kind", enum_value(BranchKind, self.branch_kind))
        reason = text_value(self.mutation_reason, 8192)
        if any(ord(c) == 0 or 0xD800 <= ord(c) <= 0xDFFF for c in reason):
            invalid("invalid reason character")
        object.__setattr__(self, "mutation_reason", reason)


_ARGUMENTS = {
    "create_search_session": CreateSearchArguments,
    "append_search_node": AppendSearchArguments,
}


@dataclass(frozen=True, slots=True)
class SearchCommand:
    project_id: UUID
    command_id: UUID
    task_id: UUID
    expected_row_version: int
    command_name: str
    arguments: CreateSearchArguments | AppendSearchArguments

    def __post_init__(self) -> None:
        exact_uuid(self.project_id)
        exact_uuid(self.command_id)
        exact_uuid(self.task_id, stable=True)
        if (
            type(self.expected_row_version) is not int
            or not 1 <= self.expected_row_version <= 2147483646
        ):
            invalid("invalid expected revision")
        if (
            self.command_name not in _ARGUMENTS
            or type(self.arguments) is not _ARGUMENTS[self.command_name]
        ):
            invalid("closed command arguments required")

    def material(self, actor_id: UUID) -> dict[str, Any]:
        exact_uuid(actor_id)
        return {
            "type": "ExperimentSearchCommand",
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


def parse_search_command(name: str, data: dict) -> SearchCommand:
    """Decode exact UUID text and closed request fields."""

    def uuid(value):
        if type(value) is UUID:
            return value
        if not isinstance(value, str) or len(value) != 36:
            invalid("canonical UUID required")
        try:
            result = UUID(value)
        except ValueError:
            invalid("canonical UUID required")
        if str(result) != value.lower():
            invalid("canonical UUID required")
        return result

    try:
        if (
            name not in _ARGUMENTS
            or not isinstance(data, dict)
            or set(data)
            != {"project_id", "command_id", "task_id", "expected_row_version", "arguments"}
        ):
            invalid("unknown or missing command fields")
        raw = data["arguments"]
        kind = _ARGUMENTS[name]
        if not isinstance(raw, dict) or set(raw) - {f.name for f in fields(kind)}:
            invalid("unknown argument fields")
        # Validate all ordinary syntax before reporting scientific selectors. The
        # optional reference placeholders never escape this decoder.
        project_id = uuid(data["project_id"])
        command_id = uuid(data["command_id"])
        task_id = uuid(data["task_id"])
        args = dict(raw)
        selectors = []
        scientific_fields = {
            "root_hypothesis_version_id",
            "root_experiment_spec_version_id",
            "hypothesis_version_id",
            "experiment_spec_version_id",
        }
        for field in fields(kind):
            key = field.name
            if key in args and key.endswith("_id") and args[key] is not None:
                if key in scientific_fields and args[key] in ("current", "latest"):
                    selectors.append(key)
                    args[key] = None
                else:
                    args[key] = uuid(args[key])
        command = SearchCommand(
            project_id,
            command_id,
            task_id,
            data["expected_row_version"],
            name,
            kind(**args),
        )
        if selectors:
            raise ResearchBaseError(
                ErrorCode.FROZEN_REFERENCE_REQUIRED, "exact frozen reference required"
            )
        return command
    except (TypeError, KeyError):
        invalid("invalid command fields")


@dataclass(frozen=True, slots=True)
class SearchCommandResult:
    command_result: CommandResult
    session_id: UUID
    node_id: UUID | None
    search_event_id: UUID

    def __post_init__(self) -> None:
        if type(self.command_result) is not CommandResult:
            invalid("command result required")
        exact_uuid(self.command_result.task_id, stable=True)
        if (
            type(self.command_result.resulting_row_version) is not int
            or self.command_result.resulting_row_version < 1
            or type(self.command_result.replayed) is not bool
            or type(self.command_result.task_event_ids) is not tuple
            or len(self.command_result.task_event_ids) != 1
            or self.command_result.step_event_ids != ()
        ):
            invalid("invalid search command result")
        exact_uuid(self.command_result.task_event_ids[0], stable=True)
        exact_uuid(self.session_id, stable=True)
        exact_uuid(self.search_event_id, stable=True)
        if self.node_id is not None:
            exact_uuid(self.node_id, stable=True)


@dataclass(frozen=True, slots=True)
class SearchReadRequest:
    project_id: UUID
    task_id: UUID
    session_id: UUID

    def __post_init__(self) -> None:
        exact_uuid(self.project_id)
        exact_uuid(self.task_id, stable=True)
        exact_uuid(self.session_id, stable=True)


@dataclass(frozen=True, slots=True)
class BranchLineageRequest(SearchReadRequest):
    node_id: UUID

    def __post_init__(self) -> None:
        SearchReadRequest.__post_init__(self)
        exact_uuid(self.node_id, stable=True)


def parse_search_read(name: str, data: dict) -> SearchReadRequest:
    kind = {
        "get_experiment_search_tree": SearchReadRequest,
        "get_branch_lineage": BranchLineageRequest,
        "get_search_budget": SearchReadRequest,
    }.get(name)
    if kind is None or type(data) is not dict or set(data) != {f.name for f in fields(kind)}:
        invalid("unknown or missing read fields")
    values = {}
    for key, value in data.items():
        if type(value) is UUID:
            values[key] = value
            continue
        if type(value) is not str or len(value) != 36:
            invalid("canonical UUID required")
        try:
            identity = UUID(value)
        except ValueError:
            invalid("canonical UUID required")
        if str(identity) != value.lower():
            invalid("canonical UUID required")
        values[key] = identity
    return kind(**values)


@dataclass(frozen=True, slots=True)
class SearchObjectiveRead:
    source: Literal["RESEARCH_TASK"]
    research_task_id: UUID
    text: str


@dataclass(frozen=True, slots=True)
class SearchSessionRead:
    id: UUID
    project_id: UUID
    task_id: UUID
    budget_id: UUID
    root_hypothesis_version_id: UUID | None
    root_hypothesis_content_hash: str | None
    root_experiment_spec_version_id: UUID | None
    root_experiment_spec_content_hash: str | None
    created_by: UUID
    created_at: datetime
    status: Literal["ACTIVE"]
    objective_definition: SearchObjectiveRead


@dataclass(frozen=True, slots=True)
class SearchNodeRead:
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
    status: Literal["PROPOSED"]


@dataclass(frozen=True, slots=True)
class SearchEventRead:
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


@dataclass(frozen=True, slots=True)
class ExperimentSearchTreeRead:
    session: SearchSessionRead
    nodes: tuple[SearchNodeRead, ...]
    run_links: tuple[()]
    events: tuple[SearchEventRead, ...]
    task_safety: TaskSafetyRead


@dataclass(frozen=True, slots=True)
class BranchLineageRead:
    session: SearchSessionRead
    path: tuple[SearchNodeRead, ...]
    run_links: tuple[()]
    events: tuple[SearchEventRead, ...]
    task_safety: TaskSafetyRead


@dataclass(frozen=True, slots=True)
class SearchBudgetRead:
    session_id: UUID
    task_id: UUID
    budget_id: UUID
    task_safety: TaskSafetyRead
