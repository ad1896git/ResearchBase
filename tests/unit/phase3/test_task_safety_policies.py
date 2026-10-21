"""Pure safety bounds, immutable policies, and exact decimal admission."""

from dataclasses import FrozenInstanceError, replace
from decimal import Decimal

import pytest

from researchbase.agent_runtime.application.safety_contracts import (
    BudgetSpec,
    CheckpointPolicySpec,
    TerminationSpec,
)
from researchbase.agent_runtime.domain.task_safety import (
    ADDITIVE,
    ResourceVector,
    decimal_value,
    exhausted,
    round_up_adapter,
    within_budget,
)
from researchbase.foundation.errors import ResearchBaseError


@pytest.mark.parametrize("dimension", ADDITIVE)
@pytest.mark.parametrize("delta", (-1, 0, 1))
def test_exact_additive_boundaries(dimension, delta):
    b = BudgetSpec("fake-usd-v1", max_gpu_hours=Decimal("1.000000"))
    charged = dict.fromkeys(ADDITIVE, 0)
    cap = getattr(b, "max_" + dimension)
    step = Decimal("0.000001") if dimension in ("gpu_hours", "token_cost") else 1
    vector = replace(ResourceVector.zero(), **{dimension: cap + delta * step})
    assert within_budget(b, charged, vector) == (delta <= 0)
    charged[dimension] = cap + delta * step
    assert exhausted(b, charged) == (delta >= 0)


def test_cpu_work_at_zero_gpu_cap():
    b = BudgetSpec("fake-usd-v1")
    totals = dict.fromkeys(ADDITIVE, 0)
    assert not exhausted(b, totals)
    assert within_budget(b, totals, replace(ResourceVector.zero(), agent_steps=1))
    assert not within_budget(
        b, totals, replace(ResourceVector.zero(), gpu_hours=Decimal("0.000001"))
    )


@pytest.mark.parametrize(
    "value",
    ("NaN", "Infinity", "-Infinity", "0.0000001", "-1.000000", True, 0.1, "100000000000000"),
)
def test_reject_inexact_nonfinite_or_out_of_range_decimal(value):
    with pytest.raises(ResearchBaseError):
        decimal_value(value)


def test_round_up_adapter_and_immutability():
    assert round_up_adapter(Decimal("0.00000001")) == Decimal("0.000001")
    assert decimal_value("1") == Decimal("1.000000")
    with pytest.raises(FrozenInstanceError):
        BudgetSpec("fake-usd-v1").currency = "EUR"  # type: ignore[misc]


@pytest.mark.parametrize("value", (True, 0, -1, 2**63))
def test_counter_limits(value):
    with pytest.raises(ResearchBaseError):
        BudgetSpec("fake-usd-v1", max_agent_steps=value)


@pytest.mark.parametrize(
    "kwargs",
    (
        {"maximum_autonomy": "A4"},
        {"maximum_autonomy": "A3"},
        {"a3_authorized": True},
        {"allowed_code_paths": ("code.py",)},
        {"network_mode": "ALLOWLIST"},
    ),
)
def test_autonomy_and_scope_fail_closed(kwargs):
    with pytest.raises(ResearchBaseError):
        CheckpointPolicySpec(**kwargs)


@pytest.mark.parametrize(
    "field",
    (
        "min_progress_enabled",
        "duplicate_hypothesis_enabled",
        "confidence_stop_enabled",
        "success_condition_enabled",
    ),
)
def test_optional_evaluators_disabled(field):
    with pytest.raises(ResearchBaseError):
        TerminationSpec(**{field: True})  # type: ignore[arg-type]


def test_policy_defaults():
    b = BudgetSpec("fake-usd-v1")
    assert (
        b.max_wall_time_seconds,
        b.max_agent_steps,
        b.max_code_iterations,
        b.max_gpu_hours,
        b.max_token_cost,
    ) == (1800, 50, 3, Decimal(0), Decimal(5))
    assert CheckpointPolicySpec().timeout_seconds == 86400
    assert CheckpointPolicySpec().required_types == ("plan_review",)
    assert TerminationSpec().repeated_failure_threshold == 2
