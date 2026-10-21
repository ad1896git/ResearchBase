# ruff: noqa: E501
"""Fixed independent canonical safety vectors, closed parsing and old hashes."""

import json
from dataclasses import replace
from uuid import UUID

import pytest

from researchbase.agent_runtime.application.safety_contracts import parse_safety_command
from researchbase.foundation.canonical_json import canonical_json_bytes
from researchbase.foundation.errors import ResearchBaseError

VECTORS = (
    (
        '{"actor_id":"01900000-0000-7000-8000-000000000002","arguments":{"budget":{"currency":"USD","hard_stop":true,"max_agent_steps":50,"max_code_iterations":3,"max_experiment_runs":5,"max_gpu_hours":"0.000000","max_llm_calls":50,"max_parallel_branches":1,"max_search_calls":20,"max_token_cost":"5.000000","max_tree_depth":3,"max_tree_nodes":10,"max_wall_time_seconds":1800,"pricing_basis":"fake-usd-v1"},"budget_id":"01900000-0000-7000-8000-000000000010","checkpoint":{"a3_authorized":false,"allowed_code_paths":[],"allowed_dataset_snapshot_ids":[],"allowed_metric_version_ids":[],"allowed_network_hosts":[],"maximum_autonomy":"A2","network_mode":"DENY","required_types":["plan_review"],"timeout_seconds":86400},"checkpoint_policy_id":"01900000-0000-7000-8000-000000000012","reason":"Café pilot limits.","termination":{"budget_stop":true,"confidence_stop_enabled":false,"confidence_stop_threshold":null,"duplicate_hypothesis_enabled":false,"duplicate_hypothesis_threshold":null,"evaluator_version":null,"human_stop":true,"max_no_improvement_iterations":2,"min_progress_enabled":false,"min_progress_score":null,"policy_stop":true,"repeated_failure_threshold":2,"score_direction":null,"score_metric_version_id":null,"success_condition":null,"success_condition_enabled":false},"termination_policy_id":"01900000-0000-7000-8000-000000000011"},"command_id":"01900000-0000-7000-8000-000000000004","command_name":"bind_task_policies","expected_row_version":1,"material_version":1,"project_id":"01900000-0000-7000-8000-000000000001","task_id":"01900000-0000-7000-8000-000000000003","type":"SafetyCommand"}\n',
        "89dd196e873985a5caffb868135bf79efc841f387d1b8836fa5b7e27fc19313e",
    ),
    (
        '{"actor_id":"01900000-0000-7000-8000-000000000002","arguments":{"deadline_seconds":60,"observed_depth":0,"observed_parallel_branches":1,"operation_id":"01900000-0000-7000-8000-000000000020","reason":"Bounded fake call.","resources":{"agent_steps":1,"code_iterations":0,"experiment_runs":0,"gpu_hours":"0.000000","llm_calls":1,"search_calls":0,"token_cost":"0.125000","tree_nodes":0,"wall_time_seconds":60},"step_id":"01900000-0000-7000-8000-000000000021"},"command_id":"01900000-0000-7000-8000-000000000005","command_name":"reserve_task_budget","expected_row_version":4,"material_version":1,"project_id":"01900000-0000-7000-8000-000000000001","task_id":"01900000-0000-7000-8000-000000000003","type":"SafetyCommand"}\n',
        "10710e357af6f0e4ec592ba079aae570a60e78b2b26e85b82259a74ba935c0ab",
    ),
    (
        '{"actor_id":"01900000-0000-7000-8000-000000000002","arguments":{"checkpoint_id":"01900000-0000-7000-8000-000000000030","expected_checkpoint_row_version":1,"reason":"Extension intent only; new task required.","response":"APPROVED"},"command_id":"01900000-0000-7000-8000-000000000006","command_name":"respond_human_checkpoint","expected_row_version":7,"material_version":1,"project_id":"01900000-0000-7000-8000-000000000001","task_id":"01900000-0000-7000-8000-000000000003","type":"SafetyCommand"}\n',
        "a364746081f6cfe74e4102f9efd1f2da2751311a05228f748d06dd4853df687e",
    ),
)


def decoded(text):
    raw = json.loads(text)
    return raw, parse_safety_command(
        raw["command_name"],
        {
            k: v
            for k, v in raw.items()
            if k not in ("type", "material_version", "actor_id", "command_name")
        },
    )


@pytest.mark.parametrize("canonical,digest", VECTORS)
def test_fixed_hash_vectors(canonical, digest):
    raw, command = decoded(canonical)
    assert (
        canonical_json_bytes(command.material(UUID(raw["actor_id"]))).decode() == canonical.strip()
    )
    assert command.request_hash(UUID(raw["actor_id"])) == digest


def test_nfc_and_set_order():
    raw, c = decoded(VECTORS[0][0])
    changed = replace(c, arguments=replace(c.arguments, reason="Cafe\u0301 pilot limits."))
    assert c.request_hash(UUID(raw["actor_id"])) == changed.request_hash(UUID(raw["actor_id"]))


@pytest.mark.parametrize(
    "member", ("trusted", "actor_id", "created_at", "status", "failure_streak", "request_hash")
)
def test_unknown_fields_reject(member):
    raw = json.loads(VECTORS[0][0])
    envelope = {
        k: v
        for k, v in raw.items()
        if k not in ("type", "material_version", "actor_id", "command_name")
    }
    envelope[member] = True
    with pytest.raises(ResearchBaseError):
        parse_safety_command(raw["command_name"], envelope)
    envelope.pop(member)
    envelope["arguments"]["budget"][member] = True
    with pytest.raises(ResearchBaseError):
        parse_safety_command(raw["command_name"], envelope)


def test_negative_zero_has_one_canonical_representation():
    from researchbase.agent_runtime.application.safety_contracts import material_value
    from researchbase.agent_runtime.domain.task_safety import decimal_value

    assert material_value(decimal_value("-0.000000")) == "0.000000"


def test_complete_extension_request_material():
    from researchbase.agent_runtime.application.safety_contracts import (
        BudgetSpec,
        RequestCheckpointArguments,
        SafetyCommand,
    )
    from researchbase.foundation.ids import new_uuid7

    actor = new_uuid7()
    proposed = BudgetSpec("fake-usd-v1", max_agent_steps=100)
    c = SafetyCommand(
        new_uuid7(),
        new_uuid7(),
        new_uuid7(),
        2,
        "request_human_checkpoint",
        RequestCheckpointArguments(
            new_uuid7(), None, "budget_extension", "Continuation intent.", new_uuid7(), proposed
        ),
    )
    value = c.material(actor)
    assert value["arguments"]["proposed_budget"]["max_agent_steps"] == 100
    assert value["arguments"]["step_id"] is None
    changed = replace(
        c, arguments=replace(c.arguments, proposed_budget=replace(proposed, max_agent_steps=101))
    )
    assert c.request_hash(actor) != changed.request_hash(actor)


def test_policy_sets_reorder_and_duplicates_reject():
    from researchbase.agent_runtime.application.safety_contracts import (
        CheckpointPolicySpec,
        material_value,
    )

    first = CheckpointPolicySpec(required_types=("plan_review", "exception"))
    second = CheckpointPolicySpec(required_types=("exception", "plan_review"))
    assert material_value(first) == material_value(second)
    with pytest.raises(ResearchBaseError):
        CheckpointPolicySpec(required_types=("exception", "exception"))


@pytest.mark.parametrize("reference", ("latest", "current", "live"))
def test_live_policy_scope_reference_is_not_frozen(reference):
    from researchbase.agent_runtime.application.safety_contracts import CheckpointPolicySpec
    from researchbase.foundation.errors import ErrorCode

    with pytest.raises(ResearchBaseError) as exc:
        CheckpointPolicySpec(allowed_dataset_snapshot_ids=(reference,))
    assert exc.value.code == ErrorCode.FROZEN_REFERENCE_REQUIRED
