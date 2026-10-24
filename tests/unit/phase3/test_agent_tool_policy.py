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


@pytest.mark.parametrize("field", tuple(material(FAKE_KEY)))
def test_each_permission_pin_is_required_without_fallback(field):
    changed = replace(
        FAKE_KEY, **{field: "b" * 64 if field == "parameter_schema_hash" else "other-v1"}
    )
    assert not policy((permission(),)).allows(changed)
    assert not policy((PermissionSpec(**material(changed), effect="ALLOW"),)).allows(FAKE_KEY)


@pytest.mark.parametrize("limits", [(50, 1), (3, 2), (1, 1)], ids=["default", "reduced", "last"])
@pytest.mark.parametrize(
    "call_delta", [-1, 0, 1], ids=["calls-below", "calls-equal", "calls-above"]
)
@pytest.mark.parametrize(
    "slot_delta", [-1, 0, 1], ids=["slots-below", "slots-equal", "slots-above"]
)
def test_caps_cross_product_across_policy_switch(limits, call_delta, slot_delta):
    calls, slots = limits
    original = policy((permission(),))
    switched = replace(
        original, version="reviewed-v2", max_tool_calls=calls, max_parallel_invocations=slots
    )
    counts = dict(task_total_calls=calls + call_delta, task_parallel_invocations=slots + slot_delta)
    expected = call_delta < 0 and slot_delta < 0
    assert switched.within_caps(**counts) is expected
    # The same accumulated counts apply when switching back; no per-policy reset.
    assert original.within_caps(**counts) is (
        counts["task_total_calls"] < 50 and counts["task_parallel_invocations"] < 1
    )


def test_policy_set_order_defaults_and_duplicates():
    allow, deny = permission(), permission("DENY")
    a, b = policy((allow, deny)), policy((deny, allow))
    assert a == b and a.digest(PROJECT) == b.digest(PROJECT)
    assert a.material(PROJECT)["content"]["network_scope"] == "DENY"
    assert a.material(PROJECT)["content"]["max_tool_calls"] == 50
    with pytest.raises(ResearchBaseError):
        policy((allow, deny, allow))
