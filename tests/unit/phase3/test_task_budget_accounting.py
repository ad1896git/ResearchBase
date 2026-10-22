"""Worst-case retention and per-step comparable accounting rules."""

from dataclasses import asdict, replace
from decimal import Decimal

import pytest

from researchbase.agent_runtime.application.task_safety import balances
from researchbase.agent_runtime.domain.task_safety import ResourceVector, settlement, streaks
from researchbase.foundation.errors import ResearchBaseError


def vector():
    return ResourceVector(60, 1, 1, 1, 1, 1, 1, Decimal("1.000000"), Decimal("2.000000"))


@pytest.mark.parametrize("outcome", ("SUCCEEDED", "FAILED", "CANCELLED", "PRUNED", "UNKNOWN"))
def test_charge_retention(outcome):
    v = vector()
    settlement(v, v, outcome)
    with pytest.raises(ResearchBaseError):
        settlement(v, replace(v, llm_calls=0), outcome)
    if outcome == "UNKNOWN":
        with pytest.raises(ResearchBaseError):
            settlement(v, replace(v, token_cost=Decimal(0)), outcome)
    else:
        settlement(
            v, replace(v, gpu_hours=Decimal(0), token_cost=Decimal(0), wall_time_seconds=0), outcome
        )


def test_multiple_unknown_observations_do_not_double_charge():
    reservation = {"id": 1, **asdict(vector())}
    unknown = {"reservation_id": 1, "is_final": False, **asdict(vector())}
    consumed, reserved = balances([reservation], [unknown, unknown])
    assert consumed["token_cost"] == 0 and reserved["token_cost"] == 2
    final = {
        "reservation_id": 1,
        "is_final": True,
        **asdict(replace(vector(), token_cost=Decimal("0.100000"))),
    }
    consumed, reserved = balances([reservation], [unknown, unknown, final])
    assert consumed["token_cost"] == Decimal("0.100000") and reserved["token_cost"] == 0


@pytest.mark.parametrize("field", ("wall_time_seconds", "llm_calls", "gpu_hours", "token_cost"))
def test_measured_over_bound_denied(field):
    v = vector()
    with pytest.raises(ResearchBaseError):
        settlement(v, replace(v, **{field: getattr(v, field) + 1}), "SUCCEEDED")


@pytest.mark.parametrize(
    "direction,scores", (("MAXIMIZE", (1, 1, 0, 2)), ("MINIMIZE", (2, 2, 3, 1)))
)
def test_progress_first_tie_worse_and_reset(direction, scores):
    history = []
    for score, expected in zip(scores, (0, 1, 2, 0), strict=True):
        assert streaks(history, "SUCCEEDED", score, direction) == (0, expected)
        history.append(("SUCCEEDED", score))


def test_failure_streak_preserved_until_success():
    history = [("FAILED", None), ("CANCELLED", None), ("PRUNED", None), ("UNKNOWN", None)]
    assert streaks(history, "FAILED", None, None) == (2, 0)
    assert streaks(history, "SUCCEEDED", None, None) == (0, 0)
