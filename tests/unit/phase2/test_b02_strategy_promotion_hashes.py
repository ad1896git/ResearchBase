"""Independent exhaustive literal material vectors; no builder supplies an oracle."""

import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest

from researchbase.domain.strategy_candidate_promotion import relation_hash, relation_material


def digest(value):
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


@pytest.mark.parametrize("kind", ["capture", "question", "hypothesis"])
def test_literal_relation_vectors(kind):
    # Literal expected material is exhaustive and independent of production field inventories.
    common: dict[str, Any] = dict(
        type="StrategyQuestionAdmission",
        material_version=1,
        id=str(UUID(int=1)),
        project_id=str(UUID(int=2)),
        capture_id=str(UUID(int=3)),
        capture_content_hash="a" * 64,
        candidate_index=2,
        candidate_text="Original é",
        question_text="Original é",
        rationale="Rationale",
        research_question_id=str(UUID(int=4)),
        research_question_version_id=str(UUID(int=5)),
        admitted_by=str(UUID(int=6)),
        admitted_at="2026-10-19T12:00:00Z",
    )
    if kind == "capture":
        literal = dict(
            type="StrategyCandidateCapture",
            material_version=1,
            id=str(UUID(int=1)),
            project_id=str(UUID(int=2)),
            artifact_version_id=str(UUID(int=3)),
            artifact_content_hash="b" * 64,
            topic="Topic é",
            source_version_ids=[str(UUID(int=4)), str(UUID(int=5))],
            max_evidence_candidates=20,
            strategy_id="native-storm-like",
            strategy_version="candidate-v1",
            captured_by=str(UUID(int=6)),
            captured_at="2026-10-19T12:00:00Z",
        )
    elif kind == "hypothesis":
        literal = {
            k: v
            for k, v in common.items()
            if k not in {"question_text", "research_question_version_id"}
        }
        literal.update(
            type="StrategyHypothesisAdmission",
            statement="Adaptation é",
            research_question_id=None,
            hypothesis_id=str(UUID(int=7)),
            hypothesis_version_id=str(UUID(int=8)),
        )
    else:
        literal = common
    row: dict[str, Any] = {
        k: v for k, v in literal.items() if k not in {"type", "material_version"}
    }
    for key, value in list(row.items()):
        if key.endswith("_at"):
            row[key] = datetime(2026, 10, 19, 12, tzinfo=UTC)
        elif (
            key
            in {
                "id",
                "project_id",
                "capture_id",
                "artifact_version_id",
                "research_question_id",
                "research_question_version_id",
                "hypothesis_id",
                "hypothesis_version_id",
                "admitted_by",
                "captured_by",
            }
            and value is not None
        ):
            row[key] = UUID(value)
        elif key == "source_version_ids":
            row[key] = tuple(UUID(v) for v in reversed(list(value or [])))
    assert relation_material(kind, row) == literal
    assert relation_hash(kind, row) == digest(literal)
    changed = (
        dict(row, topic="different") if kind == "capture" else dict(row, rationale="different")
    )
    assert relation_hash(kind, changed) != digest(literal)


def test_exact_byte_envelope_vector():
    from researchbase.application.native_research_strategy import (
        NativeResearchStrategy,
        ResearchStrategyContext,
        ResearchStrategyRequest,
    )
    from researchbase.application.strategy_candidate_promotion import (
        CaptureNativeStrategyCommand,
        capture_envelope,
    )
    from tests.unit.phase2.test_pr2_08_native_strategy import ScriptedRAG

    source = UUID(int=7)
    c = CaptureNativeStrategyCommand(UUID(int=1), UUID(int=2), "é", (source,))
    req = ResearchStrategyRequest("é", (source,))
    ctx = ResearchStrategyContext(req, lambda: False)
    native = NativeResearchStrategy()
    rag = ScriptedRAG(
        source,
        failure={f"What {p} are reported for é?" for p in ("methods", "findings", "limitations")},
    )
    result = native.execute(native.prepare_plan(req, ctx), rag, ctx)
    perspectives = [
        {"name": p, "query": f"What {p} are reported for é?"}
        for p in ("methods", "findings", "limitations")
    ]
    literal = {
        "schema": "b02-native-capture-v1",
        "project_id": str(UUID(int=2)),
        "request": {
            "topic": "é",
            "source_version_ids": [str(source)],
            "max_evidence_candidates": 20,
        },
        "result": {
            "search_plan_candidate": {
                "topic": "é",
                "source_version_ids": [str(source)],
                "max_evidence_candidates": 20,
                "perspectives": perspectives,
            },
            "source_candidates": [],
            "literature_evidence_candidates": [],
            "research_brief_candidate": {
                "artifact_type": "research_brief",
                "topic": "é",
                "sections": [
                    {
                        "perspective": p["name"],
                        "query": p["query"],
                        "answer_candidate": None,
                        "evidence_candidates": [],
                        "contradictions": [],
                        "missing_evidence": [],
                    }
                    for p in perspectives
                ],
                "coverage_limitations": ["SOURCE_SET_ONLY", "NOT_COMPREHENSIVE"],
            },
            "open_question_candidates": [p["query"] for p in perspectives],
            "hypothesis_candidates": [],
            "warnings": ["UNVERIFIED_CANDIDATE", "COVERAGE_LIMITED", "RAG_UNAVAILABLE"],
            "execution_metadata": {
                "strategy_id": "native-storm-like",
                "strategy_version": "candidate-v1",
                "rag_adapter_id": "scripted-rag",
                "rag_adapter_version": "1",
                "query_count": 3,
                "source_count": 1,
                "provider_ids": [],
            },
        },
    }
    data = capture_envelope(c, result)
    assert (
        data
        == json.dumps(literal, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    )
    assert hashlib.sha256(data).hexdigest() == digest(literal)
    assert hashlib.sha256(data + b" ").hexdigest() != digest(literal)
