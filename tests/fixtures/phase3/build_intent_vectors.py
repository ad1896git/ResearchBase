"""Independent standard-library intent vector source; run from repository root."""

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def build():
    ids = [f"01900000-0000-7000-8000-{i:012x}" for i in range(1, 9)]
    arguments: dict[str, Any] = dict(
        zip(
            ("execution_id", "agent_version_id", "research_task_id", "harness_artifact_version_id"),
            ids[3:7],
            strict=True,
        )
    )
    arguments.update(research_task_step_id=None, expected_task_revision=1)
    envelope = dict(
        type="AgentCommandMaterial",
        material_version=1,
        operation="create_agent_execution",
        project_id=ids[0],
        caller_actor_id=ids[1],
        command_id=ids[2],
        expected_revision=None,
        arguments=arguments,
    )
    items = [
        dict(
            owner_kind=owner,
            owner_id=identity,
            target_kind="ARTIFACT_VERSION",
            target_id=ids[7],
            content_hash=None,
            hash_scheme=None,
        )
        for owner, identity in (("TASK", ids[5]), ("STEP", ids[6]))
    ]
    inputs = dict(
        type="AgentExecutionInputs",
        material_version=1,
        project_id=ids[0],
        research_task_id=ids[5],
        research_task_step_id=ids[6],
        inputs=sorted(
            items,
            key=lambda x: tuple(
                x[k] for k in ("owner_kind", "owner_id", "target_kind", "target_id")
            ),
        ),
    )
    empty = {**inputs, "research_task_step_id": None, "inputs": []}
    records = {}
    for key, value in {
        "V01": envelope,
        "V08_V09": inputs,
        "V09_empty": empty,
        "V13_unicode": {"étude": "研究", "null": None, "bool": True, "integer": 1},
    }.items():
        payload = canonical(value)
        records[key] = {
            "value": value,
            "utf8": payload.decode(),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
    # Literal HarnessManifest v1 values; no ResearchBase imports or stored outputs.
    harness = {
        "schema_version": 1,
        "researchbase_revision": "rev1",
        "agent_runtime_revision": "runtime1",
        "model_profile_id": "model1",
        "prompt_template_version": "prompt1",
        "agents_md_sha256": "a" * 64,
        "config_sha256": "b" * 64,
        "strategy_id": "strategy1",
        "strategy_revision": "strategyrev1",
        "skills": [],
        "plugins": [],
        "adapters": [],
        "hooks": [],
        "mcp_capabilities": [],
        "reference_libraries": [],
    }
    for name, value, indent in (
        ("V13_harness_compact", harness, None),
        ("V13_harness_spaced", harness, 2),
        ("V14_changed_pin", {**harness, "model_profile_id": "model2"}, None),
    ):
        normalized = canonical(value)
        retained = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=indent,
            separators=(",", ":") if indent is None else None,
        ).encode()
        records[name] = {
            "value": value,
            "utf8": normalized.decode(),
            "sha256": hashlib.sha256(normalized).hexdigest(),
            "retained_utf8": retained.decode(),
            "retained_sha256": hashlib.sha256(retained).hexdigest(),
        }
    records["source_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (ROOT / "intent_vectors.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n"
    )


if __name__ == "__main__":
    build()
