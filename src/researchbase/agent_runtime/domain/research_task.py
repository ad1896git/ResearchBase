"""Planning-only task intent and lifecycle; autonomy conveys no authority."""

from enum import StrEnum
from typing import NoReturn
from unicodedata import normalize
from uuid import UUID

from researchbase.foundation.errors import ErrorCode, ResearchBaseError


class TaskType(StrEnum):
    LITERATURE_RESEARCH = "LITERATURE_RESEARCH"
    HYPOTHESIS_GENERATION = "HYPOTHESIS_GENERATION"
    EXPERIMENT_DESIGN = "EXPERIMENT_DESIGN"
    EXPERIMENT_EXECUTION = "EXPERIMENT_EXECUTION"
    ANALYSIS = "ANALYSIS"
    CLAIM_REVISION = "CLAIM_REVISION"
    MANUSCRIPT_DRAFTING = "MANUSCRIPT_DRAFTING"
    INTERNAL_REVIEW = "INTERNAL_REVIEW"
    END_TO_END_RESEARCH = "END_TO_END_RESEARCH"
    REPLICATION = "REPLICATION"
    OTHER = "OTHER"


class TaskStatus(StrEnum):
    CREATED = "CREATED"
    PLANNING = "PLANNING"
    CANCELLED = "CANCELLED"


class AutonomyLevel(StrEnum):
    A0 = "A0"
    A1 = "A1"
    A2 = "A2"
    A3 = "A3"


UNMET_PREREQUISITES = (
    "EXECUTION_BINDINGS_NOT_CONFIGURED",
    "AGENT_EXECUTION_NOT_ENABLED",
    "CAPABILITY_GATEWAY_NOT_ENABLED",
    "RECOVERY_NOT_ENABLED",
)
EXECUTION_COMMANDS = frozenset(
    {
        "start_research_task",
        "pause_research_task",
        "resume_research_task",
        "start_task_step",
        "finish_task_step",
        "fail_task_step",
    }
)
COMMAND_EVENTS = {
    "create_research_task": "CREATED",
    "create_task_plan": "PLAN_CREATED",
    "add_task_step": "STEP_ADDED",
    "add_task_step_dependency": "DEPENDENCY_ADDED",
    "seal_task_plan": "PLAN_SEALED",
    "cancel_research_task": "CANCELLED",
}


def invalid(message: str, reason: str | None = None) -> NoReturn:
    raise ResearchBaseError(
        ErrorCode.VALIDATION_ERROR, message, {"reason": reason} if reason else {}
    )


def text_value(value: str, limit: int | None = None, *, strategy: bool = False) -> str:
    if not isinstance(value, str):
        invalid("text required")
    value = normalize("NFC", value)
    if not value.strip() or (limit is not None and len(value) > limit):
        invalid("text is blank or exceeds admission limit")
    if strategy and value.strip().lower() in {"latest", "main", "master"}:
        invalid("immutable strategy identifier/version required")
    return value


def exact_uuid(value: UUID, *, stable: bool = False) -> None:
    if type(value) is not UUID or (stable and value.version != 7):
        invalid("UUIDv7 required" if stable else "exact UUID required")


def require_transition(command: str, status: str, sealed: bool) -> None:
    if command in EXECUTION_COMMANDS:
        raise ResearchBaseError(
            ErrorCode.INVALID_STATE_TRANSITION,
            "execution is disabled",
            {"reason": "EXECUTION_PREREQUISITES_UNMET"},
        )
    if (command == "cancel_research_task" and status == "CANCELLED") or (
        command == "seal_task_plan" and sealed
    ):
        raise ResearchBaseError(
            ErrorCode.INVALID_STATE_TRANSITION, "lifecycle action already completed"
        )
    if status == "CANCELLED" or (sealed and command != "cancel_research_task"):
        raise ResearchBaseError(ErrorCode.IMMUTABLE_RECORD, "task material is immutable")
    allowed = {
        "create_task_plan": {"CREATED"},
        "add_task_step": {"PLANNING"},
        "add_task_step_dependency": {"PLANNING"},
        "seal_task_plan": {"PLANNING"},
        "cancel_research_task": {"CREATED", "PLANNING"},
    }
    if status not in allowed.get(command, set()):
        raise ResearchBaseError(ErrorCode.INVALID_STATE_TRANSITION, "planning state required")
