"""Closed, caller-neutral CREATED intent command and historical read values."""

from dataclasses import asdict, dataclass, fields
from datetime import datetime
from uuid import UUID

from researchbase.agent_runtime.domain.agent_execution import intent_json, uuid7
from researchbase.agent_runtime.domain.research_task import exact_uuid, invalid
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.hashing import sha256_canonical_json


@dataclass(frozen=True, slots=True)
class CreateAgentExecution:
    execution_id: UUID
    agent_version_id: UUID
    research_task_id: UUID
    research_task_step_id: UUID | None
    expected_task_revision: int
    harness_artifact_version_id: UUID

    def __post_init__(self):
        uuid7(self.execution_id)
        for name in ("agent_version_id", "research_task_id", "harness_artifact_version_id"):
            exact_uuid(getattr(self, name))
        if self.research_task_step_id is not None:
            exact_uuid(self.research_task_step_id)
        if (
            type(self.expected_task_revision) is not int
            or not 1 <= self.expected_task_revision <= 2147483647
        ):
            invalid("strict task revision required")


@dataclass(frozen=True, slots=True)
class ExecutionCommand:
    project_id: UUID
    caller: VerifiedPrincipal
    command_id: UUID
    operation: str
    expected_revision: None
    arguments: CreateAgentExecution

    def __post_init__(self):
        exact_uuid(self.project_id)
        uuid7(self.command_id)
        if type(self.caller) is not VerifiedPrincipal:
            from researchbase.foundation.errors import ErrorCode, ResearchBaseError

            raise ResearchBaseError(ErrorCode.AUTHENTICATION_REQUIRED, "trusted principal required")
        if (
            self.operation != "create_agent_execution"
            or type(self.arguments) is not CreateAgentExecution
            or self.expected_revision is not None
        ):
            invalid("closed intent command required")

    def material(self):
        return {
            "type": "AgentCommandMaterial",
            "material_version": 1,
            "operation": self.operation,
            "project_id": str(self.project_id),
            "caller_actor_id": str(self.caller.actor_id),
            "command_id": str(self.command_id),
            "expected_revision": None,
            "arguments": {
                k: str(v) if isinstance(v, UUID) else v for k, v in asdict(self.arguments).items()
            },
        }

    def request_hash(self):
        return str(sha256_canonical_json(self.material()))


def parse_execution_command(name, payload, caller):
    data = intent_json(payload) if isinstance(payload, str | bytes) else payload
    try:
        if type(data) is not dict or type(data.get("arguments")) is not dict:
            invalid("intent envelope and arguments must be JSON objects")
        if set(data) != {"project_id", "command_id", "expected_revision", "arguments"}:
            invalid("unknown or missing intent envelope fields")
        args = dict(data["arguments"])
        if set(args) != {f.name for f in fields(CreateAgentExecution)}:
            invalid("unknown or missing intent argument fields")

        def identity(value):
            if type(value) is not str or str(UUID(value)) != value:
                invalid("canonical lowercase UUID required")
            return UUID(value)

        for key in (
            "execution_id",
            "agent_version_id",
            "research_task_id",
            "research_task_step_id",
            "harness_artifact_version_id",
        ):
            if args[key] is not None:
                args[key] = identity(args[key])
        return ExecutionCommand(
            identity(data["project_id"]),
            caller,
            identity(data["command_id"]),
            name,
            data["expected_revision"],
            CreateAgentExecution(**args),
        )
    except (ValueError, TypeError, KeyError, AttributeError):
        invalid("invalid closed intent command")


@dataclass(frozen=True, slots=True)
class GetAgentExecution:
    project_id: UUID
    execution_id: UUID
    caller: VerifiedPrincipal

    def __post_init__(self):
        exact_uuid(self.project_id)
        exact_uuid(self.execution_id)


@dataclass(frozen=True, slots=True)
class ListTaskExecutions:
    project_id: UUID
    research_task_id: UUID
    caller: VerifiedPrincipal
    limit: int = 50
    after_id: UUID | None = None

    def __post_init__(self):
        exact_uuid(self.project_id)
        exact_uuid(self.research_task_id)
        if type(self.limit) is not int or not 1 <= self.limit <= 100:
            invalid("page limit must be 1..100")
        if self.after_id is not None:
            exact_uuid(self.after_id)


@dataclass(frozen=True, slots=True)
class AgentExecutionEventDTO:
    id: UUID
    execution_id: UUID
    sequence: int
    prior_status: str | None
    new_status: str
    actor_id: UUID
    occurred_at: datetime
    reason: str
    receipt_id: UUID


@dataclass(frozen=True, slots=True)
class AgentExecutionDTO:
    id: UUID
    project_id: UUID
    research_task_id: UUID
    research_task_step_id: UUID | None
    task_revision_at_creation: int
    agent_version_id: UUID
    actor_id: UUID
    status: str
    revision: int
    created_at: datetime
    input_ref_hash: str
    input_ref_hash_scheme: str
    harness_artifact_version_id: UUID
    harness_content_hash: str
    harness_hash_scheme: str
    events: tuple[AgentExecutionEventDTO, ...]
