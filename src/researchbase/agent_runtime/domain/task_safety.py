"""Pure, exact safety limits and accounting for the bounded in-process consumer."""

from __future__ import annotations

from dataclasses import dataclass, fields
from decimal import ROUND_CEILING, Decimal, InvalidOperation
from enum import StrEnum

from researchbase.agent_runtime.domain.research_task import invalid

SCALE = Decimal("0.000001")
COUNTERS = (
    "agent_steps",
    "llm_calls",
    "search_calls",
    "code_iterations",
    "experiment_runs",
    "tree_nodes",
)
ADDITIVE = (*COUNTERS, "gpu_hours", "token_cost")
CHECKPOINT_TYPES = (
    "plan_review",
    "hypothesis_selection",
    "experiment_approval",
    "budget_extension",
    "code_risk",
    "claim_freeze",
    "manuscript_release",
    "exception",
)


class StopCause(StrEnum):
    HUMAN_STOP = "HUMAN_STOP"
    POLICY_VIOLATION = "POLICY_VIOLATION"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    REPEATED_FAILURE = "REPEATED_FAILURE"
    NO_IMPROVEMENT = "NO_IMPROVEMENT"
    SUCCESS = "SUCCESS"


def integer(value, *, minimum=0, maximum=9223372036854775807):
    if type(value) is not int or not minimum <= value <= maximum:
        invalid("bounded integer required")
    return value


def decimal_value(value, *, signed=False):
    if isinstance(value, bool | float) or not isinstance(value, str | int | Decimal):
        invalid("exact decimal required")
    try:
        number = Decimal(value)
        if (
            not number.is_finite()
            or int(number.as_tuple().exponent) < -6
            or abs(number) >= Decimal("100000000000000")
            or (not signed and number < 0)
        ):
            invalid("finite six-place decimal required")
        return Decimal("0.000000") if number == 0 else number.quantize(SCALE)
    except (InvalidOperation, ValueError, TypeError):
        invalid("finite six-place decimal required")
        raise AssertionError("unreachable") from None


def round_up_adapter(value: Decimal) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        invalid("finite nonnegative adapter amount required")
    return decimal_value(value.quantize(SCALE, rounding=ROUND_CEILING))


@dataclass(frozen=True, slots=True)
class ResourceVector:
    wall_time_seconds: int
    agent_steps: int
    llm_calls: int
    search_calls: int
    code_iterations: int
    experiment_runs: int
    tree_nodes: int
    gpu_hours: Decimal
    token_cost: Decimal

    def __post_init__(self):
        for f in fields(self):
            value = getattr(self, f.name)
            object.__setattr__(
                self,
                f.name,
                decimal_value(value)
                if f.name in ("gpu_hours", "token_cost")
                else integer(
                    value,
                    maximum=2147483647 if f.name == "wall_time_seconds" else 9223372036854775807,
                ),
            )

    @classmethod
    def zero(cls):
        return cls(0, 0, 0, 0, 0, 0, 0, Decimal(0), Decimal(0))


def within_budget(budget, charged, proposed):
    return all(charged[k] + getattr(proposed, k) <= getattr(budget, "max_" + k) for k in ADDITIVE)


def exhausted(budget, charged):
    return any(
        charged[k] >= getattr(budget, "max_" + k)
        for k in ADDITIVE
        if getattr(budget, "max_" + k) > 0
    )


def settlement(reserved: ResourceVector, measured: ResourceVector, outcome: str):
    if outcome not in ("SUCCEEDED", "FAILED", "CANCELLED", "PRUNED", "UNKNOWN"):
        invalid("unknown outcome")
    if any(getattr(measured, f.name) > getattr(reserved, f.name) for f in fields(reserved)):
        invalid("measurement exceeds reservation")
    if outcome == "UNKNOWN" and measured != reserved:
        invalid("unknown outcome retains worst case")
    if any(getattr(measured, k) != getattr(reserved, k) for k in COUNTERS):
        invalid("admission counters cannot be refunded")


def streaks(history, outcome, score, direction):
    failure = 0
    progress = 0
    best = None
    for result, value in (*history, (outcome, score)):
        if result == "FAILED":
            failure += 1
        elif result == "SUCCEEDED":
            failure = 0
            if value is not None:
                if best is None or (value > best if direction == "MAXIMIZE" else value < best):
                    best, progress = value, 0
                else:
                    progress += 1
    return failure, progress
