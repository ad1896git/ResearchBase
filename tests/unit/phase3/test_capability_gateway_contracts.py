"""Literal frozen vectors, strict recursive input parsing and lifecycle evidence."""

import json
import pickle
from dataclasses import fields, replace
from decimal import Decimal
from typing import get_type_hints
from uuid import UUID

import pytest
from tests.unit.phase3.test_agent_tool_policy import PROJECT, permission, policy

from researchbase.agent_runtime.application import gateway_contracts as c
from researchbase.agent_runtime.domain.capability_invocation import (
    SCHEMA,
    FakeParameters,
    GatewayRef,
    material,
    refs,
    require_transition,
    retry_eligible,
    typed,
    validate_combined_refs,
)
from researchbase.agent_runtime.domain.task_safety import ResourceVector
from researchbase.agent_runtime.domain.tool_policy import (
    FAKE_KEY,
    capability_set_material,
)
from researchbase.agent_runtime.ports import gateway_repository as stored
from researchbase.foundation.canonical_json import canonical_json_bytes
from researchbase.foundation.errors import ResearchBaseError
from researchbase.foundation.hashing import sha256_canonical_json

ID = UUID("01900000-0000-7000-8000-000000000003")


def request():
    params = FakeParameters("Cafe\u0301", "SUCCEEDED")
    return c.RequestInvocationArguments(
        ID,
        None,
        ID,
        ID,
        "a" * 64,
        **material(FAKE_KEY),
        skill_id="echo-skill",
        skill_version="1.0.0",
        strategy_id="echo-strategy",
        strategy_version="1.0.0",
        harness_artifact_version_id=ID,
        harness_content_hash="b" * 64,
        parameters_artifact_version_id=ID,
        parameters_content_hash="c" * 64,
        requested_parameters_hash=params.digest(),
        parameters_byte_size=len(params.canonical_bytes()),
        parameters=params,
        input_refs=(),
        retry_parent_id=None,
        deadline_seconds=60,
        reason="test",
    )


def finish():
    return c.FinishInvocationArguments(
        ID, 2, "FINISH", "SUCCEEDED", ResourceVector.zero(), (), None, None, "Café", None, "test"
    )


def vectors():
    return [
        SCHEMA,
        capability_set_material(()),
        capability_set_material((permission(),)),
        policy().material(PROJECT),
        policy((permission("DENY"), permission())).material(PROJECT),
        material(FakeParameters("Cafe\u0301", "SUCCEEDED")),
    ]


# Literal §7.2 bytes and digests, transcribed at authoring time; never recomputed.
FIXED = [
    (
        (
            b'{"additionalProperties":false,"properties":{"message":{"maxLength":1024,'
            b'"type":"string"},"outcome":{"enum":["SUCCEEDED","FAILED","UNKNOWN_OUTCOME",'
            b'"CANCELLED"]}},"required":["message","outcome"],"type":"object"}'
        ),
        "79fd29b8c5f855b2d2728a13ba245b96d2287fa52fd364646f4a155e40ff4d8f",
    ),
    (
        (b'{"entries":[],"material_version":1,"type":"CapabilitySet"}'),
        "2be8fb87e16870441bee24424875c19e4bef7500ec600750924b2c00c8d778f1",
    ),
    (
        (
            b'{"entries":[{"adapter_id":"fake_in_process","adapter_version":"1.0.0",'
            b'"capability_id":"fake_capability","capability_version":"1.0.0",'
            b'"operation":"echo",'
            b'"parameter_schema_hash":"79fd29b8c5f855b2d2728a13ba245b96d2287fa52fd364646f4a1'
            b'55e40ff4d8f"}],"material_version":1,"type":"CapabilitySet"}'
        ),
        "2087127ad6ee04e51ebb37b6fb2f89af70209d3dd99a83645a8f803e7e6125f9",
    ),
    (
        (
            b'{"content":{"capability_set_hash":"2be8fb87e16870441bee24424875c19e4bef7500ec6'
            b'00750924b2c00c8d778f1","compute_scope":"DENY","external_effect_scope":"DENY",'
            b'"filesystem_scope":"DENY","max_parallel_invocations":1,"max_tool_calls":50,'
            b'"network_scope":"DENY","permissions":[],'
            b'"project_id":"01900000-0000-7000-8000-000000000001",'
            b'"registry_artifact_version_id":"01900000-0000-7000-8000-000000000020",'
            b'"registry_content_hash":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
            b'aaaaaaaaaaa","version":"fake-policy-v1"},"material_version":1,'
            b'"type":"AgentToolPolicy"}'
        ),
        "dcbc9330ce3ba36e9bc0988395950922f278aba37cef35d37239d8f8b099cf7c",
    ),
    (
        (
            b'{"content":{"capability_set_hash":"2087127ad6ee04e51ebb37b6fb2f89af70209d3dd99'
            b'a83645a8f803e7e6125f9","compute_scope":"DENY","external_effect_scope":"DENY",'
            b'"filesystem_scope":"DENY","max_parallel_invocations":1,"max_tool_calls":50,'
            b'"network_scope":"DENY","permissions":[{"adapter_id":"fake_in_process",'
            b'"adapter_version":"1.0.0","capability_id":"fake_capability",'
            b'"capability_version":"1.0.0","effect":"ALLOW","operation":"echo",'
            b'"parameter_schema_hash":"79fd29b8c5f855b2d2728a13ba245b96d2287fa52fd364646f4a1'
            b'55e40ff4d8f"},{"adapter_id":"fake_in_process","adapter_version":"1.0.0",'
            b'"capability_id":"fake_capability","capability_version":"1.0.0",'
            b'"effect":"DENY","operation":"echo",'
            b'"parameter_schema_hash":"79fd29b8c5f855b2d2728a13ba245b96d2287fa52fd364646f4a1'
            b'55e40ff4d8f"}],"project_id":"01900000-0000-7000-8000-000000000001",'
            b'"registry_artifact_version_id":"01900000-0000-7000-8000-000000000020",'
            b'"registry_content_hash":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
            b'aaaaaaaaaaa","version":"fake-policy-v1"},"material_version":1,'
            b'"type":"AgentToolPolicy"}'
        ),
        "725ad2c4ac6b22c5f53ee1138b5d65d88b344e033d52df268db46afd7d3f293b",
    ),
    (
        ('{"message":"Café","outcome":"SUCCEEDED"}').encode(),
        "a6d9214ed01cfe46686c39829bde5d0a733d16c31d8b5297e48d245b70ce13b3",
    ),
]


@pytest.mark.parametrize(
    "index",
    range(6),
    ids=["schema", "empty-set", "fake-set", "empty-policy", "allow-deny-policy", "cafe-parameters"],
)
def test_frozen_literal_vectors(index):
    value = vectors()[index]
    expected_bytes, expected_digest = FIXED[index]
    assert canonical_json_bytes(value) == expected_bytes
    assert str(sha256_canonical_json(value)) == expected_digest


@pytest.mark.parametrize(
    "name,args",
    [
        ("register_agent_tool_policy", c.RegisterToolPolicyArguments(ID, policy(), "test")),
        ("request_capability_invocation", request()),
        ("start_capability_invocation", c.StartInvocationArguments(ID, 1, "test")),
        ("finish_capability_invocation", finish()),
    ],
)
def test_four_command_roundtrips_and_actor_material(name, args):
    command = c.GatewayCommand(PROJECT, ID, ID, 1, name, args)
    raw = material(command)
    del raw["command_name"]
    raw = json.loads(json.dumps(raw))
    if name.startswith("finish"):
        with pytest.raises(ResearchBaseError, match="trusted observation required"):
            c.parse_gateway_command(name, raw)
    else:
        assert c.parse_gateway_command(name, raw) == command
    assert command.material(ID)["type"] == "GatewayCommand"
    assert command.request_hash(ID) != command.request_hash(PROJECT)
    raw["arguments"]["untrusted"] = True
    with pytest.raises(ResearchBaseError):
        c.parse_gateway_command(name, raw)


@pytest.mark.parametrize(
    "field,value",
    [
        ("deadline_seconds", True),
        ("parameters_byte_size", True),
        ("deadline_seconds", 61),
        ("parameters_byte_size", 65537),
        ("requested_parameters_hash", "a" * 64),
        ("step_id", "latest"),
        ("invocation_id", UUID(int=1)),
    ],
)
def test_invalid_request_fields(field, value):
    with pytest.raises(ResearchBaseError):
        replace(request(), **{field: value})


@pytest.mark.parametrize(
    "mutation",
    [
        lambda raw: raw["parameters"].update(extra="ignored?"),
        lambda raw: raw.update(parameters={"message": "ok"}),
        lambda raw: raw.update(parameters={"message": False, "outcome": "SUCCEEDED"}),
        lambda raw: raw.update(
            input_refs=[
                {
                    "family": "ARTIFACT_VERSION",
                    "version_id": str(ID),
                    "content_hash": "a" * 64,
                    "hash_scheme": None,
                    "extra": None,
                }
            ]
        ),
    ],
)
def test_nested_extras_and_missing_fields(mutation):
    raw = material(request())
    mutation(raw)
    with pytest.raises(ResearchBaseError):
        typed(c.RequestInvocationArguments, raw, decode=True)


@pytest.mark.parametrize("amount", ["0.0000001", "NaN", "Infinity", "-Infinity", 0.5, True])
def test_exact_six_place_resources(amount):
    raw = material(finish())
    raw["measured"]["gpu_hours"] = amount
    with pytest.raises(ResearchBaseError):
        typed(c.FinishInvocationArguments, raw, decode=True)


def test_resources_material_is_fixed_six_place_and_nulls_expand():
    value = replace(finish(), measured=replace(ResourceVector.zero(), gpu_hours=Decimal("1.2")))
    assert material(value)["measured"]["gpu_hours"] == "1.200000"
    assert material(value)["trace_content_hash"] is None


def test_public_finish_and_trusted_context_cannot_be_deserialized():
    raw = material(c.GatewayCommand(PROJECT, ID, ID, 1, "finish_capability_invocation", finish()))
    del raw["command_name"]
    with pytest.raises(ResearchBaseError):
        c.parse_gateway_command("finish_capability_invocation", raw)
    with pytest.raises(ResearchBaseError):
        typed(c.AgentExecutionContext, {"trusted": True}, decode=True)
    # __getstate__ explicitly blocks pickle even for a context allocated without construction.
    with pytest.raises(TypeError, match="not serializable"):
        pickle.dumps(object.__new__(c.AgentExecutionContext))


def test_retained_parameters_have_separate_owning_hash():
    value = request()
    assert value.parameters_content_hash != value.requested_parameters_hash
    value.verify_retained_parameters(
        value.parameters.canonical_bytes(), "c" * 64, value.parameters_byte_size
    )
    for data, digest, size in [
        (b"{}", "c" * 64, 2),
        (value.parameters.canonical_bytes(), "d" * 64, value.parameters_byte_size),
    ]:
        with pytest.raises(ResearchBaseError):
            value.verify_retained_parameters(data, digest, size)


def test_refs_sort_duplicate_and_combined_bound():
    values = tuple(GatewayRef("ARTIFACT_VERSION", UUID(int=i), "a" * 64, None) for i in range(256))
    assert refs(tuple(reversed(values))) == values
    validate_combined_refs(values, ())
    with pytest.raises(ResearchBaseError):
        refs((values[0], values[0]))
    with pytest.raises(ResearchBaseError):
        validate_combined_refs(values, (values[0],))
    with pytest.raises(ResearchBaseError):
        GatewayRef("SOURCE_VERSION", ID, "a" * 64, None)


@pytest.mark.parametrize("summary,allowed", [("é" * 4096, True), ("é" * 4097, False)])
def test_summary_utf8_byte_bound(summary, allowed):
    if allowed:
        assert replace(finish(), result_summary=summary).result_summary == summary
    else:
        with pytest.raises(ResearchBaseError):
            replace(finish(), result_summary=summary)


@pytest.mark.parametrize(
    "prior,action,outcome,kwargs,expected",
    [
        ("REQUESTED", "START", None, {}, "RUNNING"),
        ("REQUESTED", "FINISH", "CANCELLED", {"no_dispatch": True}, "CANCELLED"),
        *[
            ("RUNNING", "FINISH", v, {}, v)
            for v in ("SUCCEEDED", "FAILED", "UNKNOWN_OUTCOME", "CANCELLED")
        ],
        ("UNKNOWN_OUTCOME", "RECONCILE", "SUCCEEDED", {}, "UNKNOWN_OUTCOME"),
    ],
)
def test_lifecycle_edges(prior, action, outcome, kwargs, expected):
    assert require_transition(prior, action, outcome, **kwargs) == expected


@pytest.mark.parametrize(
    "prior,action,outcome",
    [
        ("REQUESTED", "FINISH", "SUCCEEDED"),
        ("REQUESTED", "FINISH", "CANCELLED"),
        ("SUCCEEDED", "FINISH", "SUCCEEDED"),
        ("UNKNOWN_OUTCOME", "RECONCILE", "UNKNOWN_OUTCOME"),
        ("FAILED", "START", None),
    ],
)
def test_invalid_lifecycle(prior, action, outcome):
    with pytest.raises(ResearchBaseError):
        require_transition(prior, action, outcome)


def test_reconciliation_and_retry():
    assert retry_eligible("FAILED")
    assert not retry_eligible("UNKNOWN_OUTCOME")
    assert retry_eligible("UNKNOWN_OUTCOME", "SUCCEEDED")
    with pytest.raises(ResearchBaseError):
        require_transition("UNKNOWN_OUTCOME", "RECONCILE", "FAILED", reconciled=True)
    with pytest.raises(ResearchBaseError):
        replace(finish(), kind="RECONCILE", result_summary="rewritten")


def test_complete_stored_read_vocabulary():
    for read, row, extras in [
        (c.AgentToolPolicyRead, stored.StoredToolPolicy, {"permissions"}),
        (
            c.CapabilityInvocationRead,
            stored.StoredInvocation,
            {
                "refs",
                "events",
                "effective_outcome",
                "effective_usage_record_id",
                "current_availability",
                "execution_enabled",
            },
        ),
        (c.CapabilityEventRead, stored.StoredInvocationEvent, set()),
        (c.GatewayRefRead, stored.StoredInvocationRef, {"validity_warnings"}),
    ]:
        assert {f.name for f in fields(read)} == set(get_type_hints(row)) | extras


def test_capability_request_command_ids_must_be_distinct():
    with pytest.raises(ResearchBaseError):
        c.CapabilityRequest(ID, ID, PROJECT, 1, request())


def read_values():
    from datetime import UTC, datetime

    stamp = datetime(2026, 10, 22, tzinfo=UTC)
    p = policy((permission(),))
    policy_read = c.AgentToolPolicyRead(
        ID,
        PROJECT,
        ID,
        ID,
        p.version,
        p.capability_set_hash,
        50,
        1,
        "DENY",
        "DENY",
        "DENY",
        "DENY",
        p.registry_artifact_version_id,
        p.registry_content_hash,
        p.digest(PROJECT),
        "sha256-cjson-v1",
        ID,
        stamp,
        p.permissions,
    )
    ref = c.GatewayRefRead(
        ID,
        PROJECT,
        ID,
        ID,
        ID,
        "INPUT",
        None,
        None,
        None,
        None,
        ID,
        None,
        "a" * 64,
        None,
        (),
    )
    event = c.CapabilityEventRead(
        ID,
        PROJECT,
        ID,
        ID,
        ID,
        ID,
        1,
        1,
        "REQUESTED",
        None,
        "REQUESTED",
        None,
        None,
        ID,
        stamp,
        "test",
    )
    r = request()
    invocation = c.CapabilityInvocationRead(
        ID,
        PROJECT,
        ID,
        None,
        ID,
        ID,
        ID,
        ID,
        r.policy_content_hash,
        "CONTRACT_FAKE",
        r.capability_id,
        r.capability_version,
        r.operation,
        r.adapter_id,
        r.adapter_version,
        r.parameter_schema_hash,
        r.skill_id,
        r.skill_version,
        r.strategy_id,
        r.strategy_version,
        ID,
        r.harness_content_hash,
        ID,
        r.parameters_content_hash,
        r.requested_parameters_hash,
        r.parameters_byte_size,
        ID,
        None,
        None,
        None,
        None,
        "REQUESTED",
        1,
        stamp,
        None,
        None,
        ID,
        None,
        None,
        None,
        None,
        (ref,),
        (event,),
        None,
        None,
        "ACTIVE",
        False,
    )
    result = c.GatewayCommandResult(
        ID,
        PROJECT,
        ID,
        ID,
        ID,
        "request_capability_invocation",
        ID,
        ID,
        ID,
        ID,
        None,
        2,
        1,
        stamp,
        False,
    )
    capability = c.CapabilityResult(ID, "SUCCEEDED", (), None, ResourceVector.zero(), None, "ok")
    cursor = c.InvocationListCursor(stamp, ID)
    page = c.TaskCapabilityInvocationsRead(ID, (invocation,), cursor)
    return (policy_read, ref, event, invocation, result, capability, cursor, page)


@pytest.mark.parametrize("index", range(8))
def test_closed_read_and_result_roundtrips(index):
    value = read_values()[index]
    assert c.parse_gateway_value(type(value), material(value)) == value
    raw = material(value)
    raw["extra"] = "unknown"
    with pytest.raises(ResearchBaseError):
        c.parse_gateway_value(type(value), raw)


def test_read_nested_extras_and_projection_literals():
    invocation = read_values()[3]
    raw = material(invocation)
    raw["events"][0]["extra"] = True
    with pytest.raises(ResearchBaseError):
        c.parse_gateway_value(c.CapabilityInvocationRead, raw)
    with pytest.raises(ResearchBaseError):
        replace(invocation, execution_enabled=True)
    with pytest.raises(ResearchBaseError):
        replace(invocation, current_availability="UNKNOWN")
    with pytest.raises(ResearchBaseError):
        replace(read_values()[1], hypothesis_version_id=ID)
    with pytest.raises(ResearchBaseError):
        replace(read_values()[2], sequence=2)


def test_trusted_context_has_no_material_or_public_decoder():
    context = object.__new__(c.AgentExecutionContext)
    with pytest.raises(ResearchBaseError):
        material(context)
    with pytest.raises(ResearchBaseError):
        c.parse_gateway_value(c.AgentExecutionContext, {})
    with pytest.raises(ResearchBaseError):
        typed(c.AgentExecutionContext, {}, decode=True)


@pytest.mark.parametrize("stamp", ["2026-10-22T10:00:00", "bad-date", True])
def test_cursor_requires_aware_timestamp(stamp):
    with pytest.raises(ResearchBaseError):
        c.parse_gateway_value(c.InvocationListCursor, {"created_at": stamp, "id": str(ID)})


def test_parameters_message_limits_and_scale():
    assert len(FakeParameters("é" * 1024, "SUCCEEDED").message) == 1024
    with pytest.raises(ResearchBaseError):
        FakeParameters("é" * 1025, "SUCCEEDED")
    with pytest.raises(ResearchBaseError):
        FakeParameters("ok", "PENDING")
