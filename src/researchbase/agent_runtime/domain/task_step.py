"""Declared planning step types; readiness is never inferred from display order."""

from enum import StrEnum


class StepType(StrEnum):
    PLAN = "PLAN"
    RESEARCH = "RESEARCH"
    RETRIEVE = "RETRIEVE"
    HYPOTHESIZE = "HYPOTHESIZE"
    DESIGN_EXPERIMENT = "DESIGN_EXPERIMENT"
    CODE = "CODE"
    DEBUG = "DEBUG"
    EXECUTE = "EXECUTE"
    ANALYZE = "ANALYZE"
    CRITIQUE = "CRITIQUE"
    WRITE = "WRITE"
    REVIEW = "REVIEW"
    HUMAN_CHECKPOINT = "HUMAN_CHECKPOINT"
    PROMOTE = "PROMOTE"
    OTHER = "OTHER"


class StepStatus(StrEnum):
    PENDING = "PENDING"
    CANCELLED = "CANCELLED"


PROGRESS_STATUSES = (
    "PENDING",
    "READY",
    "RUNNING",
    "WAITING",
    "SUCCEEDED",
    "FAILED",
    "SKIPPED",
    "CANCELLED",
)


def predecessors_succeeded(statuses: tuple[str, ...]) -> bool:
    return all(status == "SUCCEEDED" for status in statuses)
