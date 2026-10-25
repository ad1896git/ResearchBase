import json
from dataclasses import fields
from pathlib import Path
from uuid import UUID

import pytest

from researchbase.agent_runtime.application.execution_contracts import (
    AgentExecutionDTO,
    CreateAgentExecution,
    ListTaskExecutions,
)
from researchbase.agent_runtime.domain.agent_execution import (
    ExecutionInput,
    input_material,
    intent_bytes,
    intent_json,
)
from researchbase.agent_runtime.domain.harness_manifest import HarnessManifest, ManifestEntry
from researchbase.foundation.errors import ResearchBaseError
from researchbase.foundation.hashing import sha256_bytes

VECTORS = json.loads(Path("tests/fixtures/phase3/intent_vectors.json").read_text())


def test_closed_intent_command_and_literal_vectors():
    for key, vector in VECTORS.items():
        if key == "source_sha256":
            continue
        assert intent_bytes(vector["value"]) == vector["utf8"].encode()
        assert str(sha256_bytes(intent_bytes(vector["value"]))) == vector["sha256"]
    for value in (1.0, 1e100, float("nan"), {"nested": [2.0]}):
        with pytest.raises(ResearchBaseError) as exc:
            intent_bytes(value)
        assert exc.value.details == {"reason": "pr302s2_value_type"}
    with pytest.raises(ResearchBaseError):
        intent_json('{"x":1,"x":2}')


@pytest.mark.parametrize("revision", [True, False, 1.0, 0, -1, 2147483648, "1"])
def test_strict_revision(revision):
    args = VECTORS["V01"]["value"]["arguments"].copy()
    for name in (
        "execution_id",
        "agent_version_id",
        "research_task_id",
        "harness_artifact_version_id",
    ):
        args[name] = UUID(args[name])
    args["expected_task_revision"] = revision
    with pytest.raises(ResearchBaseError):
        CreateAgentExecution(**args)


def test_intent_binding_and_harness_pins():
    vector = VECTORS["V08_V09"]["value"]
    items = [
        ExecutionInput(
            v["owner_kind"],
            UUID(v["owner_id"]),
            v["target_kind"],
            UUID(v["target_id"]),
            v["content_hash"],
            v["hash_scheme"],
        )
        for v in vector["inputs"]
    ]
    result = input_material(
        UUID(vector["project_id"]),
        UUID(vector["research_task_id"]),
        UUID(vector["research_task_step_id"]),
        reversed(items),
    )
    assert result == vector
    with pytest.raises(ResearchBaseError):
        input_material(
            UUID(vector["project_id"]), UUID(vector["research_task_id"]), None, [items[0], items[0]]
        )
    # S1 ordinal and immutable pin rules remain authoritative.
    with pytest.raises(ResearchBaseError):
        ManifestEntry("latest", "1", "a" * 64, 1)
    assert all(f.name != "status" for f in fields(HarnessManifest))


def test_intent_query_and_receipt_shapes():
    from typing import cast

    from researchbase.domain.phase2_identity import VerifiedPrincipal

    assert {f.name for f in fields(AgentExecutionDTO)} == {
        "id",
        "project_id",
        "research_task_id",
        "research_task_step_id",
        "task_revision_at_creation",
        "agent_version_id",
        "actor_id",
        "status",
        "revision",
        "created_at",
        "input_ref_hash",
        "input_ref_hash_scheme",
        "harness_artifact_version_id",
        "harness_content_hash",
        "harness_hash_scheme",
        "events",
    }
    with pytest.raises(ResearchBaseError):
        ListTaskExecutions(
            UUID(int=1), UUID(int=2), caller=cast(VerifiedPrincipal, object()), limit=101
        )


def test_create_parser_closed_fields_and_envelope():
    from datetime import UTC, datetime

    from researchbase.agent_runtime.application.execution_contracts import parse_execution_command
    from researchbase.domain.phase2_identity import VerifiedPrincipal

    vector = VECTORS["V01"]["value"]
    principal = VerifiedPrincipal(
        UUID(vector["caller_actor_id"]),
        "test",
        "MTLS_URI",
        "spiffe://test/human",
        "cert",
        datetime.now(UTC),
    )
    payload = {k: vector[k] for k in ("project_id", "command_id", "expected_revision", "arguments")}
    assert (
        parse_execution_command("create_agent_execution", payload, principal).material() == vector
    )
    for arguments in (
        {**payload["arguments"], "unknown": 1},
        {**payload["arguments"], "expected_task_revision": True},
        {**payload["arguments"], "expected_task_revision": 1.0},
    ):
        with pytest.raises(ResearchBaseError):
            parse_execution_command(
                "create_agent_execution", {**payload, "arguments": arguments}, principal
            )
    with pytest.raises(ResearchBaseError):
        parse_execution_command("transition_agent_execution", payload, principal)
    with pytest.raises(ResearchBaseError):
        parse_execution_command(
            "create_agent_execution",
            {**payload, "arguments": list(payload["arguments"].items())},
            principal,
        )


def test_harness_byte_value_hashes_and_ordinal_pins():
    from dataclasses import asdict, replace

    manifest = HarnessManifest(
        1,
        "rev1",
        "runtime1",
        "model1",
        "prompt1",
        "a" * 64,
        "b" * 64,
        "strategy1",
        "strategyrev1",
        (),
        (),
        (),
        (),
        (),
        (),
    )
    assert json.loads(json.dumps(asdict(manifest))) == VECTORS["V13_harness_compact"]["value"]
    compact = VECTORS["V13_harness_compact"]["retained_utf8"].encode()
    spaced = VECTORS["V13_harness_spaced"]["retained_utf8"].encode()
    assert sha256_bytes(compact) == VECTORS["V13_harness_compact"]["retained_sha256"]
    assert sha256_bytes(spaced) == VECTORS["V13_harness_spaced"]["retained_sha256"]
    assert manifest.digest() == VECTORS["V13_harness_compact"]["sha256"]
    assert (
        replace(manifest, model_profile_id="model2").digest()
        == VECTORS["V14_changed_pin"]["sha256"]
    )
    assert sha256_bytes(compact) != sha256_bytes(spaced)
    assert intent_bytes(json.loads(compact)) == intent_bytes(json.loads(spaced))
    assert manifest.digest() != replace(manifest, model_profile_id="model2").digest()
    entries = (ManifestEntry("two", "rev1", "c" * 64, 2), ManifestEntry("one", "rev1", "d" * 64, 1))
    assert replace(manifest, skills=entries).skills == tuple(reversed(entries))
    for bad in ((entries[0],), (entries[0], entries[0])):
        with pytest.raises(ResearchBaseError):
            replace(manifest, skills=bad)


def test_independent_vector_source_identity():
    assert (
        str(sha256_bytes(Path("tests/fixtures/phase3/build_intent_vectors.py").read_bytes()))
        == VECTORS["source_sha256"]
    )
