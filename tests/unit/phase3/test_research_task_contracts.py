# ruff: noqa: E501
"""Closed normalization and the three literal frozen request-hash vectors."""

import json
from dataclasses import FrozenInstanceError
from typing import Any
from uuid import UUID, uuid4

import pytest

from researchbase.agent_runtime.application.contracts import parse_command
from researchbase.agent_runtime.domain.research_task import AutonomyLevel, TaskType
from researchbase.foundation.canonical_json import canonical_json_bytes
from researchbase.foundation.errors import ResearchBaseError

VECTORS = [
    (
        '{"actor_id":"01900000-0000-7000-8000-000000000002","arguments":{"autonomy_level":"A0","inputs":[],"objective":"Café replication","strategy_id":"human_guided_research","strategy_version":"1.0.0","task_type":"LITERATURE_RESEARCH"},"command_id":"01900000-0000-7000-8000-000000000004","command_name":"create_research_task","expected_row_version":null,"material_version":1,"project_id":"01900000-0000-7000-8000-000000000001","task_id":"01900000-0000-7000-8000-000000000003","type":"ResearchTaskCommand"}',
        "643ae964496ab90b75b5e20140a3ddafa962a542f80d31598fcd10db313615b8",
    ),
    (
        '{"actor_id":"01900000-0000-7000-8000-000000000002","arguments":{"edges":[{"dependent_id":"01900000-0000-7000-8000-000000000011","predecessor_id":"01900000-0000-7000-8000-000000000010"}],"nodes":[{"agent_role":null,"capability_id":null,"inputs":[],"ordinal":2,"parent_step_id":null,"step_id":"01900000-0000-7000-8000-000000000010","step_type":"PLAN"},{"agent_role":"research","capability_id":null,"inputs":[{"id":"01900000-0000-7000-8000-000000000020","type":"ARTIFACT_VERSION"},{"id":"01900000-0000-7000-8000-000000000021","type":"SOURCE_VERSION"}],"ordinal":1,"parent_step_id":"01900000-0000-7000-8000-000000000010","step_id":"01900000-0000-7000-8000-000000000011","step_type":"RESEARCH"}]},"command_id":"01900000-0000-7000-8000-000000000005","command_name":"create_task_plan","expected_row_version":1,"material_version":1,"project_id":"01900000-0000-7000-8000-000000000001","task_id":"01900000-0000-7000-8000-000000000003","type":"ResearchTaskCommand"}',
        "9213a547322e6ea8d35c04f3046af0b034afc8fe3c8c83c05bbeb0d2148d6eed",
    ),
    (
        '{"actor_id":"01900000-0000-7000-8000-000000000002","arguments":{"reason":"Planning withdrawn."},"command_id":"01900000-0000-7000-8000-000000000006","command_name":"cancel_research_task","expected_row_version":2,"material_version":1,"project_id":"01900000-0000-7000-8000-000000000001","task_id":"01900000-0000-7000-8000-000000000003","type":"ResearchTaskCommand"}',
        "743c2a1084f9a7c8c1cdcf74a470b48fe191f166708ec2f0fca3aafcfc4a5067",
    ),
]


def decode(material) -> Any:
    return parse_command(
        material["command_name"],
        {
            k: material[k]
            for k in ("project_id", "command_id", "task_id", "expected_row_version", "arguments")
        },
    )


@pytest.mark.parametrize("canonical,digest", VECTORS)
def test_fixed_vectors(canonical, digest):
    material = json.loads(canonical)
    command = decode(material)
    actor = UUID(material["actor_id"])
    assert canonical_json_bytes(command.material(actor)) == canonical.encode()
    assert command.request_hash(actor) == digest
    with pytest.raises(FrozenInstanceError):
        command.task_id = uuid4()


def test_order_independence_and_nfc():
    material = json.loads(VECTORS[1][0])
    args = material["arguments"]
    args["nodes"].reverse()
    args["nodes"][0]["inputs"].reverse()
    assert decode(material).request_hash(UUID(material["actor_id"])) == VECTORS[1][1]
    material = json.loads(VECTORS[0][0])
    material["arguments"]["objective"] = "Cafe\u0301 replication"
    assert decode(material).request_hash(UUID(material["actor_id"])) == VECTORS[0][1]


@pytest.mark.parametrize(
    "field,value",
    [
        ("actor_id", "forged"),
        ("status", "RUNNING"),
        ("row_version", 1),
        ("policy_id", str(uuid4())),
        ("outputs", []),
        ("content_hash", "a" * 64),
        ("readiness", True),
    ],
)
def test_unknown_top_level_fields(field, value):
    material = json.loads(VECTORS[0][0])
    data = {
        k: material[k]
        for k in ("project_id", "command_id", "task_id", "expected_row_version", "arguments")
    }
    data[field] = value
    with pytest.raises(ResearchBaseError):
        parse_command("create_research_task", data)


@pytest.mark.parametrize(
    "field,value",
    [
        ("objective", " "),
        ("objective", "x" * 8193),
        ("task_type", "unknown"),
        ("autonomy_level", "A4"),
        ("strategy_id", " Latest "),
        ("strategy_version", "MAIN"),
        ("status", "CREATED"),
        ("inputs", [{"type": "ARTIFACT_VERSION", "id": "latest"}]),
        (
            "inputs",
            [
                {
                    "type": "ARTIFACT_VERSION",
                    "id": "01900000-0000-7000-8000-000000000020",
                    "content_hash": "a" * 64,
                }
            ],
        ),
    ],
)
def test_bad_arguments(field, value):
    material = json.loads(VECTORS[0][0])
    material["arguments"][field] = value
    with pytest.raises(ResearchBaseError):
        decode(material)


@pytest.mark.parametrize("kind", tuple(TaskType))
@pytest.mark.parametrize("autonomy", tuple(AutonomyLevel))
def test_declared_intent_types_and_requested_autonomy(kind, autonomy):
    material = json.loads(VECTORS[0][0])
    material["arguments"].update(task_type=kind, autonomy_level=autonomy)
    assert decode(material).arguments.autonomy_level == autonomy


@pytest.mark.parametrize("case", ("node", "edge", "input", "ordinal", "predecessor", "uuid"))
def test_duplicate_rejection_and_uuid(case):
    material = json.loads(VECTORS[1][0])
    args = material["arguments"]
    if case == "node":
        args["nodes"].append(args["nodes"][0])
    elif case == "edge":
        args["edges"] *= 2
    elif case == "input":
        args["nodes"][1]["inputs"] *= 2
    elif case == "ordinal":
        args["nodes"][1]["ordinal"] = args["nodes"][0]["ordinal"]
    elif case == "predecessor":
        material["command_name"] = "add_task_step"
        material["arguments"] = {
            "node": args["nodes"][0],
            "predecessor_ids": [args["nodes"][1]["step_id"]] * 2,
        }
    elif case == "uuid":
        args["nodes"][0]["step_id"] = str(uuid4())
    with pytest.raises(ResearchBaseError):
        decode(material)


@pytest.mark.parametrize("field", ("inputs", "edges", "nodes", "predecessor_ids"))
def test_array_shapes_cannot_be_replaced_with_objects(field):
    material = json.loads(VECTORS[0 if field == "inputs" else 1][0])
    if field == "predecessor_ids":
        material["command_name"] = "add_task_step"
        material["arguments"] = {"node": material["arguments"]["nodes"][0], "predecessor_ids": {}}
    else:
        material["arguments"][field] = {}
    with pytest.raises(ResearchBaseError):
        decode(material)
