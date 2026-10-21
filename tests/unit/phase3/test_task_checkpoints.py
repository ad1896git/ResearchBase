"""Conjunctive gates use the latest exact-scope request and effective expiry."""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from researchbase.agent_runtime.application.task_safety import gates
from researchbase.agent_runtime.domain.task_safety import CHECKPOINT_TYPES

NOW = datetime(2026, 10, 21, tzinfo=UTC)


def checkpoint(
    identity=1, *, status="APPROVED", step=None, kind="plan_review", created=None
) -> dict[str, Any]:
    return dict(
        id=identity,
        created_at=created or NOW,
        step_id=step,
        checkpoint_type=kind,
        status=status,
        expires_at=NOW + timedelta(days=1),
    )


@pytest.mark.parametrize("kind", CHECKPOINT_TYPES)
def test_each_policy_gate_is_conjunctive(kind):
    policy = {"required_types": [kind]}
    rows = [checkpoint(kind=t) for t in {kind, "plan_review"}]
    assert all(g.satisfied for g in gates(policy, rows, NOW))
    assert not all(g.satisfied for g in gates(policy, [], NOW))


@pytest.mark.parametrize("status", ("PENDING", "REJECTED", "MODIFIED", "EXPIRED"))
def test_new_request_defeats_old_approval(status):
    rows = [checkpoint(), checkpoint(2, status=status, created=NOW + timedelta(seconds=1))]
    assert not gates({"required_types": []}, rows, NOW)[0].satisfied


@pytest.mark.parametrize("offset,expected", ((-1, "PENDING"), (0, "EXPIRED"), (1, "EXPIRED")))
def test_expiry_boundary(offset, expected):
    row = checkpoint(status="PENDING")
    at = row["expires_at"] + timedelta(microseconds=offset)
    gate = gates({"required_types": []}, [row], at)[0]
    assert gate.effective_status == expected and not gate.satisfied


def test_exact_step_scope_and_extension_do_not_authorize_other_work():
    assert not gates({"required_types": []}, [checkpoint(step=2)], NOW, step=1)[0].satisfied
    assert not gates({"required_types": []}, [checkpoint(kind="budget_extension")], NOW)[
        0
    ].satisfied
