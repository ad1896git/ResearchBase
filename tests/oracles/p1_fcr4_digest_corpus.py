"""Deterministic P1-FCR4 digest corpus executable against PRE or POST source trees."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from researchbase.foundation.canonical_json import canonical_json_bytes
from researchbase.foundation.hashing import sha256_bytes, sha256_canonical_json

PROJECT_ID = "00000000-0000-4000-8000-000000000001"
RUN_ID = "00000000-0000-4000-8000-000000000002"
METRIC_ID = "00000000-0000-4000-8000-000000000003"
MEASUREMENT_ID = "00000000-0000-4000-8000-000000000004"
FINDING_ID = "00000000-0000-4000-8000-000000000005"
TARGET_ID = "00000000-0000-4000-8000-000000000006"
ARTIFACT_BYTES = b"ResearchBase\nraw bytes\x00\xff"
MANIFEST_HASH = hashlib.sha256(b"manifest-v1").hexdigest()

NESTED = {
    "z": None,
    "outer": {
        "items": [1, {"inner": [True, False, 1.25, "研究-é"]}],
    },
}


def independent_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def independent_digest(value: object) -> str:
    return hashlib.sha256(independent_bytes(value)).hexdigest()


def support_rows() -> list[dict[str, str | None]]:
    rows = [
        {
            "source_type": "statistical_result",
            "source_id": "00000000-0000-4000-8000-000000000011",
            "relation_type": "supports",
            "qualification": None,
        },
        {
            "source_type": "measurement",
            "source_id": MEASUREMENT_ID,
            "relation_type": "supports",
            "qualification": "primary-évidence",
        },
    ]
    rows.sort(
        key=lambda row: (
            row["source_type"],
            row["source_id"],
            row["relation_type"],
            row["qualification"] is not None,
            row["qualification"] or "",
        )
    )
    return rows


def structured_materials() -> dict[str, object]:
    support_hash = independent_digest(support_rows())
    raw_hash = hashlib.sha256(ARTIFACT_BYTES).hexdigest()
    measurement_material = {
        "run_id": RUN_ID,
        "metric_definition_version_id": METRIC_ID,
        "numeric_value": None,
        "structured_value": NESTED,
        "unit": "ms",
        "evaluation_scope": {"cohort": ["α", "β"], "complete": True},
    }
    measurement_hash = independent_digest(measurement_material)
    impact_targets = [
        {
            "target_type": "artifact_version",
            "target_id": "00000000-0000-4000-8000-000000000020",
            "target_content_hash": raw_hash,
            "impact_kind": "downstream",
        },
        {
            "target_type": "measurement",
            "target_id": MEASUREMENT_ID,
            "target_content_hash": measurement_hash,
            "impact_kind": "direct",
        },
        {
            "target_type": "run",
            "target_id": RUN_ID,
            "target_content_hash": None,
            "impact_kind": "downstream",
        },
    ]
    impact_targets.sort(
        key=lambda row: (
            row["target_type"],
            row["target_id"],
            row["target_content_hash"] is not None,
            row["target_content_hash"] or "",
            row["impact_kind"],
        )
    )
    return {
        "ResearchQuestionVersion": {
            "question_text": "Does Δ improve latency?",
            "scope": NESTED,
            "rationale": None,
        },
        "HypothesisVersion": {
            "statement": "Δ reduces latency",
            "expected_direction": "decrease",
            "success_criteria": NESTED,
            "rationale": "Pré-registered",
        },
        "ExperimentSpecVersion": {
            "title": "Protocol Ω",
            "objective": "Measure finite effects",
            "protocol": NESTED,
            "planned_metrics": [{"name": "latency", "ordinal": 1}],
            "seed_policy": {"seed": 42, "deterministic": True},
            "analysis_plan": {"method": "bootstrap", "alpha": 0.05},
        },
        "DatasetSnapshot": {
            "manifest_hash": MANIFEST_HASH,
            "selection_definition": NESTED,
        },
        "MetricDefinitionVersion": {
            "definition": NESTED,
            "unit": "ms",
            "aggregation": "median",
        },
        "Measurement": measurement_material,
        "StatisticalResult": {
            "analysis_type": "bootstrap",
            "result_payload": NESTED,
            "analysis_definition": {"iterations": 1000, "confidence": 0.95},
        },
        "ClaimVersion": {
            "statement": "Observed effect is robust",
            "scope": NESTED,
            "qualification": "within cohort",
            "support_set_hash": support_hash,
        },
        "ImpactAssessment": {
            "project_id": PROJECT_ID,
            "audit_finding_id": FINDING_ID,
            "assessment_payload": NESTED,
            "conclusion": "requires_review",
            "impact_targets": impact_targets,
        },
        "CorrectionRecord": {
            "project_id": PROJECT_ID,
            "target_type": "measurement",
            "target_id": MEASUREMENT_ID,
            "target_content_hash": measurement_hash,
            "correction_type": "computational",
            "corrected_assertion": NESTED,
            "reason": "Correct deterministic fixture",
        },
    }


GENERIC_VECTORS: dict[str, object] = {
    "key-order-a": {"z": 1, "a": {"b": 2, "a": 1}},
    "key-order-b": {"a": {"a": 1, "b": 2}, "z": 1},
    "nested-object": {"a": {"b": {"c": "value"}}},
    "ordered-array": [1, 2, 3],
    "reversed-array": [3, 2, 1],
    "mixed": {"items": [None, True, False, 7, 1.5, {"é": "研究"}]},
    "unicode-composed": {"text": "é"},
    "unicode-decomposed": {"text": "e\u0301"},
    "finite-floats": {"positive": 1.25, "negative_zero": -0.0},
    "deep": NESTED,
}


def vector(value: object) -> dict[str, Any]:
    production_bytes = canonical_json_bytes(value)
    oracle_bytes = independent_bytes(value)
    return {
        "material": value,
        "canonical_hex": production_bytes.hex(),
        "digest": str(sha256_canonical_json(value)),
        "oracle_canonical_hex": oracle_bytes.hex(),
        "oracle_digest": hashlib.sha256(oracle_bytes).hexdigest(),
    }


def build_report() -> dict[str, Any]:
    materials = structured_materials()
    raw_digest = str(sha256_bytes(ARTIFACT_BYTES))
    support = support_rows()
    structured = {name: vector(value) for name, value in materials.items()}
    measurement_hash = structured["Measurement"]["digest"]
    return {
        "schemes": {"canonical": "canonical-json-v1", "hash": "sha256-cjson-v1"},
        "structured": structured,
        "generic": {name: vector(value) for name, value in GENERIC_VECTORS.items()},
        "artifact": {
            "bytes_hex": ARTIFACT_BYTES.hex(),
            "production_digest": raw_digest,
            "oracle_digest": hashlib.sha256(ARTIFACT_BYTES).hexdigest(),
            "metadata_a_digest": raw_digest,
            "metadata_b_digest": raw_digest,
        },
        "support_set": {
            "rows": support,
            "production_digest": str(sha256_canonical_json(support)),
            "oracle_digest": independent_digest(support),
        },
        "bindings": {
            "structured_measurement": measurement_hash,
            "raw_artifact": raw_digest,
            "hashless_run": None,
        },
        "manifest": {
            "external_identity": MANIFEST_HASH,
            "snapshot_digest": structured["DatasetSnapshot"]["digest"],
        },
    }


if __name__ == "__main__":
    print(json.dumps(build_report(), ensure_ascii=False, sort_keys=True, separators=(",", ":")))
