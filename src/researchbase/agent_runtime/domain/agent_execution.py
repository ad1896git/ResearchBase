"""Immutable intent material. An intended Agent is not a producer."""

import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from researchbase.agent_runtime.domain.agent_version import digest_value
from researchbase.agent_runtime.domain.research_task import exact_uuid, invalid
from researchbase.foundation.canonical_json import canonical_json_bytes


def intent_value(value) -> Any:
    if value is None or type(value) in (bool, str, int):
        return value
    if type(value) in (list, tuple):
        return [intent_value(v) for v in value]
    if type(value) is dict and all(type(k) is str for k in value):
        return {k: intent_value(v) for k, v in value.items()}
    invalid("unsupported intent canonical value", "pr302s2_value_type")


def intent_bytes(value):
    return canonical_json_bytes(intent_value(value))


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            invalid("duplicate JSON key")
        result[key] = value
    return result


def intent_json(payload) -> Any:
    try:
        return intent_value(json.loads(payload, object_pairs_hook=unique_object))
    except (ValueError, TypeError, UnicodeError):
        invalid("invalid intent JSON")


def uuid7(value):
    if type(value) is not UUID or value.version != 7:
        invalid("UUIDv7 required")


@dataclass(frozen=True, slots=True)
class ExecutionInput:
    owner_kind: str
    owner_id: UUID
    target_kind: str
    target_id: UUID
    content_hash: str | None
    hash_scheme: str | None

    def __post_init__(self):
        if type(self.owner_kind) is not str or type(self.target_kind) is not str:
            invalid("strict execution input kinds required")
        if self.owner_kind not in {"TASK", "STEP"} or self.target_kind not in {
            "RESEARCH_QUESTION_VERSION",
            "HYPOTHESIS_VERSION",
            "CLAIM_VERSION",
            "SOURCE_VERSION",
            "ARTIFACT_VERSION",
            "MANUSCRIPT_VERSION",
        }:
            invalid("closed execution input kinds required")
        exact_uuid(self.owner_id)
        exact_uuid(self.target_id)
        if self.content_hash is not None:
            digest_value(self.content_hash)
        if self.hash_scheme is not None and self.hash_scheme != "sha256-cjson-v1":
            invalid("saved input hash scheme unsupported")

    def material(self):
        return {
            "owner_kind": self.owner_kind,
            "owner_id": str(self.owner_id),
            "target_kind": self.target_kind,
            "target_id": str(self.target_id),
            "content_hash": self.content_hash,
            "hash_scheme": self.hash_scheme,
        }


def input_material(project, task, step, inputs):
    exact_uuid(project)
    exact_uuid(task)
    if step is not None:
        exact_uuid(step)
    values = [item.material() for item in inputs]
    keys = [
        tuple(v[k] for k in ("owner_kind", "owner_id", "target_kind", "target_id")) for v in values
    ]
    if len(set(keys)) != len(keys):
        invalid("duplicate input owner/target")
    values = [v for _, v in sorted(zip(keys, values, strict=True), key=lambda pair: pair[0])]
    return {
        "type": "AgentExecutionInputs",
        "material_version": 1,
        "project_id": str(project),
        "research_task_id": str(task),
        "research_task_step_id": str(step) if step is not None else None,
        "inputs": values,
    }
