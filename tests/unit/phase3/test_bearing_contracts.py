import json
from dataclasses import FrozenInstanceError, fields, replace
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

from researchbase.agent_runtime.application.bearing_contracts import (
    AdmitBearingArguments,
    BearingBinding,
    BearingEvaluationCommand,
    BearingEvaluationResult,
    SettleBearingArguments,
)
from researchbase.agent_runtime.domain.task_safety import ResourceVector
from researchbase.foundation.canonical_json import canonical_json_bytes
from researchbase.foundation.errors import ResearchBaseError

DOCUMENT = (
    Path(__file__).resolve().parents[3] / "docs/phase3/design/PR3-16-bearing-v2-material-vectors.md"
)
VECTORS = json.loads(DOCUMENT.read_text().split("```json\n", 1)[1].split("\n```", 1)[0])


def command_from_vector(vector):
    material = json.loads(vector["material_utf8"])
    args = material["arguments"].copy()
    binding = {}
    for field in fields(BearingBinding):
        value = args.pop(field.name)
        binding[field.name] = UUID(value) if not field.name.endswith("_hash") else value
    for key, value in list(args.items()):
        if key.endswith("_id") and value is not None:
            args[key] = UUID(value)
    resource = "resources" if "resources" in args else "measured"
    args[resource] = ResourceVector(**args[resource])
    kind = AdmitBearingArguments if resource == "resources" else SettleBearingArguments
    arguments = kind(binding=BearingBinding(**binding), **args)
    command = BearingEvaluationCommand(
        UUID(material["project_id"]),
        UUID(material["command_id"]),
        UUID(material["task_id"]),
        material["expected_row_version"],
        material["command_name"],
        arguments,
    )
    return command, UUID(material["actor_id"])


@pytest.mark.parametrize("vector", VECTORS, ids=lambda v: v["name"])
def test_literal_vectors(vector):
    command, actor = command_from_vector(vector)
    assert canonical_json_bytes(command.material(actor)) == vector["material_utf8"].encode()
    assert command.request_hash(actor) == vector["sha256"]
    result = vector["expected_result"]
    if "error" not in result:
        converted: dict[str, Any] = {
            k: UUID(v) if k.endswith("_id") and v is not None else v for k, v in result.items()
        }
        assert BearingEvaluationResult(**converted).replayed is False


def test_immutable_closed_and_material_copy():
    command, actor = command_from_vector(VECTORS[0])
    with pytest.raises(FrozenInstanceError):
        command.arguments.binding.labels_content_hash = "x"  # type: ignore[misc]
    with pytest.raises(TypeError):
        BearingBinding(
            **{
                **{
                    f.name: getattr(command.arguments.binding, f.name)
                    for f in fields(BearingBinding)
                },
                "extra": 1,
            }
        )
    material = command.material(actor)
    material["arguments"]["resources"]["tree_nodes"] = 99
    assert command.material(actor)["arguments"]["resources"]["tree_nodes"] == 1
    with pytest.raises(ResearchBaseError):
        replace(command, arguments={})
    with pytest.raises(ResearchBaseError):
        replace(command, command_name="other")


@pytest.mark.parametrize(
    "field,value",
    [
        ("labels_content_hash", "A" * 64),
        ("metric_content_hash", "0" * 63),
        ("consumer_generation", "current"),
    ],
)
def test_invalid_binding(field, value):
    command, _ = command_from_vector(VECTORS[0])
    with pytest.raises(ResearchBaseError):
        replace(command.arguments.binding, **{field: value})


@pytest.mark.parametrize(
    "field,value",
    [
        ("observed_depth", True),
        ("observed_depth", 4),
        ("observed_parallel_branches", 2),
        ("deadline_seconds", 11),
        ("operation_id", UUID(int=1)),
        ("reason", " "),
        ("resources", {}),
    ],
)
def test_invalid_admission(field, value):
    command, _ = command_from_vector(VECTORS[0])
    with pytest.raises(ResearchBaseError):
        replace(command.arguments, **{field: value})


@pytest.mark.parametrize(
    "changes",
    [
        {"score": None},
        {"score": 1.1},
        {"score": "1.000001"},
        {"score": True},
        {"evaluator_version": "latest"},
        {"outcome": "FAILED"},
        {"outcome": []},
    ],
)
def test_invalid_settlement(changes):
    command, _ = command_from_vector(VECTORS[3])
    with pytest.raises(ResearchBaseError):
        replace(command.arguments, **changes)


def test_normalization_and_result_shape():
    command, actor = command_from_vector(VECTORS[0])
    args = replace(command.arguments, mutation_reason="Synthetic cafe\u0301")
    assert replace(command, arguments=args).request_hash(actor) == command.request_hash(actor)
    settled, _ = command_from_vector(VECTORS[3])
    assert isinstance(settled.arguments, SettleBearingArguments)
    assert replace(settled.arguments, score="-0").score == 0
    result = VECTORS[0]["expected_result"]
    converted = {
        k: UUID(v) if k.endswith("_id") and v is not None else v for k, v in result.items()
    }
    with pytest.raises(ResearchBaseError):
        BearingEvaluationResult(**{**converted, "usage_record_id": UUID(int=1)})
    with pytest.raises(ResearchBaseError):
        BearingEvaluationResult(**{**converted, "replayed": 1})
