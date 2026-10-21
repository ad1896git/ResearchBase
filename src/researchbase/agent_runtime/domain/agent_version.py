"""Immutable Agent behavior and separate operational availability values."""

from __future__ import annotations

import re
from enum import StrEnum

from researchbase.agent_runtime.domain.research_task import invalid, text_value
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


class AgentRole(StrEnum):
    PLANNER = "planner"
    RESEARCH = "research"
    HYPOTHESIS = "hypothesis"
    EXPERIMENT_DESIGNER = "experiment_designer"
    CODER = "coder"
    DEBUGGER = "debugger"
    EXECUTOR = "executor"
    ANALYST = "analyst"
    CRITIC = "critic"
    WRITER = "writer"
    REVIEWER = "reviewer"
    ORCHESTRATOR = "orchestrator"
    GENERAL = "general"


class RuntimeType(StrEnum):
    NATIVE = "native"
    LANGGRAPH = "langgraph"
    DEEPAGENTS = "deepagents"
    OPENHANDS = "openhands"
    EXTERNAL_SERVICE = "external_service"
    OTHER = "other"


class AgentStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    RETIRED = "RETIRED"


def digest_value(value):
    if not isinstance(value, str) or not re.fullmatch("[0-9a-f]{64}", value):
        invalid("lowercase SHA-256 digest required")
    return value


def pinned(value):
    value = text_value(value, 512)
    if any(
        part.lower() in {"latest", "current", "main", "master", "head"}
        for part in re.split(r"[/@:#?=&\s]+", value)
    ):
        raise ResearchBaseError(
            ErrorCode.FROZEN_REFERENCE_REQUIRED, "immutable pinned reference required"
        )
    return value


def transition(prior, next_status):
    if prior == "RETIRED" or prior == next_status:
        raise ResearchBaseError(
            ErrorCode.INVALID_STATE_TRANSITION, "invalid availability transition"
        )
