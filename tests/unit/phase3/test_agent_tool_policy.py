"""Fixed policy vectors and exact, task-wide permission/cap evaluation."""

from dataclasses import replace
from uuid import UUID

import pytest

from researchbase.agent_runtime.domain.capability_invocation import material
from researchbase.agent_runtime.domain.tool_policy import (
    FAKE_KEY,
    PermissionKey,
    PermissionSpec,
    ToolPolicySpec,
    capability_set_hash,
)
from researchbase.foundation.errors import ResearchBaseError

PROJECT = UUID("01900000-0000-7000-8000-000000000001")
REGISTRY = UUID("01900000-0000-7000-8000-000000000020")


def permission(effect="ALLOW"):
    return PermissionSpec(**material(FAKE_KEY), effect=effect)


def policy(permissions=()):
    return ToolPolicySpec(
        "fake-policy-v1", permissions, REGISTRY, "a" * 64, capability_set_hash(permissions)
    )


@pytest.mark.parametrize(
    "effects,allowed",
    [
        ([], False),
        (["ALLOW"], True),
        (["DENY"], False),
        (["ALLOW", "DENY"], False),
        (["DENY", "ALLOW"], False),
    ],
)
def test_exact_effects(effects, allowed):
    value = policy(tuple(permission(v) for v in effects))
    assert value.allows(FAKE_KEY) is allowed
    assert not value.allows(replace(FAKE_KEY, operation="Echo"))
    assert (value.max_tool_calls, value.max_parallel_invocations) == (50, 1)


@pytest.mark.parametrize(
    "calls,parallel,allowed",
    [(0, 0, True), (49, 0, True), (50, 0, False), (51, 0, False), (0, 1, False), (0, 2, False)],
)
def test_task_wide_counts_survive_policy_changes(calls, parallel, allowed):
    old = policy((permission(),))
    new = replace(old, version="next-policy-v2")
    assert new.within_caps(task_total_calls=calls, task_parallel_invocations=parallel) is allowed


@pytest.mark.parametrize(
    "updates",
    [
        {"max_tool_calls": True},
        {"max_parallel_invocations": False},
        {"max_tool_calls": 0},
        {"max_parallel_invocations": 51},
        {"network_scope": "ALLOW"},
        {"capability_set_hash": "f" * 64},
        {"permissions": (permission(), permission())},
        {"permissions": (permission(),) * 257},
    ],
)
def test_invalid_policy(updates):
    with pytest.raises(ResearchBaseError):
        replace(policy(), **updates)


@pytest.mark.parametrize(
    "pin",
    [
        "latest",
        "CURRENT",
        "main",
        "master",
        "x/latest",
        "echo*",
        "echo?",
        "^echo$",
        "echo.*",
        "(echo)",
        "echo[0]",
        " echo",
        "echo ",
        "",
    ],
)
def test_aliases_patterns_and_whitespace_deny(pin):
    with pytest.raises(ResearchBaseError):
        replace(FAKE_KEY, operation=pin)


def test_permission_normalization_and_projection():
    key = PermissionKey("cafe\u0301", "1", "echo", "fake", "1", "a" * 64)
    assert key.capability_id == "café"
    assert capability_set_hash((permission("ALLOW"), permission("DENY"))) == capability_set_hash(
        (permission(),)
    )
