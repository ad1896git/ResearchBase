"""Disconnected strategy candidates; no retained science or human review."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from researchbase.application.native_research_strategy import (
    NativeResearchStrategy,
    ResearchStrategyContext,
    ResearchStrategyRequest,
    StrategyCancelled,
)
from researchbase.application.scientific_rag_provider import (
    EvidenceCandidate,
    ScientificRAGResponse,
    SourceLocator,
)


def _request(source_id):
    return ResearchStrategyRequest("CRISPR repair", (source_id,))


def _response(question, source_id, *, with_evidence=True):
    evidence = (
        (
            EvidenceCandidate(
                source_id, SourceLocator(paragraph="1", quote_span="char:0:8"), "excerpt"
            ),
        )
        if with_evidence
        else ()
    )
    return ScientificRAGResponse(
        answer_candidate="Unverified candidate" if with_evidence else None,
        evidence_candidates=evidence,
        contradictions=(),
        missing_evidence=(),
        adapter_id="scripted-rag",
        adapter_version="1",
        model_id=None,
        provider_id="test-only",
        retrieval_query=question,
        retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


class ScriptedRAG:
    adapter_id = "scripted-rag"
    adapter_version = "1"

    def __init__(self, source_id, *, missing=(), failure=()):
        self.source_id = source_id
        self.missing = set(missing)
        self.failure = set(failure)
        self.calls = []

    def answer(self, request, context):
        self.calls.append(request)
        if request.question in self.failure:
            raise RuntimeError("synthetic-secret")
        return _response(
            request.question,
            self.source_id,
            with_evidence=request.question not in self.missing,
        )


def _context(cancelled=lambda: False):
    return ResearchStrategyContext(cancelled)


def test_plan_has_deterministic_multiple_perspectives_and_queries():
    source_id = uuid4()
    strategy = NativeResearchStrategy()
    plan = strategy.prepare_plan(_request(source_id), _context())
    assert [item.name for item in plan.perspectives] == ["methods", "findings", "limitations"]
    assert [item.query for item in plan.perspectives] == [
        "What methods are reported for CRISPR repair?",
        "What findings are reported for CRISPR repair?",
        "What limitations are reported for CRISPR repair?",
    ]
    assert plan.source_version_ids == (source_id,)
    assert plan == strategy.prepare_plan(_request(source_id), _context())


def test_execute_preserves_exact_source_spans_and_candidate_provenance():
    source_id = uuid4()
    strategy = NativeResearchStrategy()
    plan = strategy.prepare_plan(_request(source_id), _context())
    rag = ScriptedRAG(source_id)
    result = strategy.execute(plan, rag, _context())
    assert [call.source_version_ids for call in rag.calls] == [(source_id,)] * 3
    assert [section.perspective for section in result.research_brief_candidate.sections] == [
        "methods", "findings", "limitations"
    ]
    assert all(
        section.answer_candidate == "Unverified candidate"
        for section in result.research_brief_candidate.sections
    )
    assert all(
        item.source_version_id == source_id for item in result.literature_evidence_candidates
    )
    assert all(
        item.locator == SourceLocator(paragraph="1", quote_span="char:0:8")
        for item in result.literature_evidence_candidates
    )
    assert result.execution_metadata.query_count == 3
    assert result.execution_metadata.rag_adapter_id == "scripted-rag"
    assert result.research_brief_candidate.artifact_type == "research_brief"
    assert result.hypothesis_candidates == ()
    assert "UNVERIFIED_CANDIDATE" in result.warnings
    assert "COVERAGE_LIMITED" in result.warnings


def test_missing_evidence_makes_open_question_without_fabricated_answer():
    source_id = uuid4()
    strategy = NativeResearchStrategy()
    plan = strategy.prepare_plan(_request(source_id), _context())
    query = plan.perspectives[1].query
    result = strategy.execute(plan, ScriptedRAG(source_id, missing=(query,)), _context())
    assert result.research_brief_candidate.sections[1].answer_candidate is None
    assert query in result.open_question_candidates
    assert "MISSING_EVIDENCE" in result.warnings


def test_provider_failure_is_isolated_and_raw_error_is_not_returned():
    source_id = uuid4()
    strategy = NativeResearchStrategy()
    plan = strategy.prepare_plan(_request(source_id), _context())
    query = plan.perspectives[0].query
    result = strategy.execute(plan, ScriptedRAG(source_id, failure=(query,)), _context())
    assert result.research_brief_candidate.sections[0].answer_candidate is None
    assert query in result.open_question_candidates
    assert "RAG_UNAVAILABLE" in result.warnings
    assert "synthetic-secret" not in repr(result)


def test_foreign_source_candidate_fails_closed():
    source_id = uuid4()
    strategy = NativeResearchStrategy()
    plan = strategy.prepare_plan(_request(source_id), _context())
    with pytest.raises(ValueError, match="source"):
        strategy.execute(plan, ScriptedRAG(uuid4()), _context())


def test_cancellation_between_perspectives_aborts_without_partial_result():
    source_id = uuid4()
    strategy = NativeResearchStrategy()
    plan = strategy.prepare_plan(_request(source_id), _context())
    rag = ScriptedRAG(source_id)
    with pytest.raises(StrategyCancelled):
        strategy.execute(plan, rag, _context(lambda: len(rag.calls) >= 1))
    assert len(rag.calls) == 1


def test_provider_cancellation_propagates_instead_of_becoming_availability_warning():
    source_id = uuid4()
    strategy = NativeResearchStrategy()
    plan = strategy.prepare_plan(_request(source_id), _context())

    class CancellingRAG(ScriptedRAG):
        def answer(self, request, context):
            raise StrategyCancelled("cancelled")

    with pytest.raises(StrategyCancelled):
        strategy.execute(plan, CancellingRAG(source_id), _context())


def test_tampered_plan_cannot_dispatch_a_different_query():
    from dataclasses import replace

    source_id = uuid4()
    strategy = NativeResearchStrategy()
    plan = strategy.prepare_plan(_request(source_id), _context())
    changed = replace(plan, perspectives=(replace(plan.perspectives[0], query="hidden query"),))
    rag = ScriptedRAG(source_id)
    with pytest.raises(ValueError, match="plan"):
        strategy.execute(changed, rag, _context())
    assert rag.calls == []
