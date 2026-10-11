"""Offline candidate boundary; every actor and source here is test-only."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from researchbase.application.scientific_rag_provider import (
    EvidenceCandidate,
    FakeScientificRAGCapability,
    RetrievalConstraints,
    ScientificRAGCallContext,
    ScientificRAGRequest,
    ScientificRAGResponse,
)


def request(source_ids):
    return ScientificRAGRequest(
        "What does the source report?",
        tuple(source_ids),
        RetrievalConstraints(max_evidence_candidates=2),
    )


def response(source_id, *, locator="page 2, paragraph 3", excerpt="Measured result"):
    return ScientificRAGResponse(
        answer_candidate="Candidate answer",
        evidence_candidates=(EvidenceCandidate(source_id, locator, excerpt),),
        contradictions=(),
        missing_evidence=(),
        adapter_id="fake-scientific-rag",
        adapter_version="1",
        model_id=None,
        provider_id="test-only",
        retrieval_query="What does the source report?",
        retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def context(cancelled=False):
    return ScientificRAGCallContext(lambda: cancelled)


def test_offline_candidate_preserves_source_locator_and_provenance():
    source_id = uuid4()
    fake = FakeScientificRAGCapability(response(source_id))
    result = fake.answer(request((source_id,)), context())
    assert result.evidence_candidates[0].source_version_id == source_id
    assert result.evidence_candidates[0].locator == "page 2, paragraph 3"
    assert (result.adapter_id, result.adapter_version, result.provider_id) == (
        "fake-scientific-rag", "1", "test-only"
    )
    assert result.retrieval_query == "What does the source report?"
    assert fake.calls == [request((source_id,))]


@pytest.mark.parametrize("source_ids", [(), (uuid4(), uuid4())])
def test_request_requires_a_nonempty_unique_source_set(source_ids):
    if len(source_ids) == 2:
        source_ids = (source_ids[0], source_ids[0])
    with pytest.raises(ValueError):
        request(source_ids)


def test_foreign_source_version_is_rejected_without_partial_candidate():
    approved, foreign = uuid4(), uuid4()
    fake = FakeScientificRAGCapability(response(foreign))
    with pytest.raises(ValueError, match="source"):
        fake.answer(request((approved,)), context())
    assert len(fake.calls) == 1


@pytest.mark.parametrize("locator", ["", " ", "x" * 257])
def test_unverifiable_or_unbounded_locator_is_rejected(locator):
    source_id = uuid4()
    with pytest.raises(ValueError):
        EvidenceCandidate(source_id, locator, "excerpt")


def test_duplicate_source_locator_and_candidate_budget_are_rejected():
    source_id = uuid4()
    candidate = EvidenceCandidate(source_id, "page 2", "excerpt")
    result = response(source_id)
    from dataclasses import replace

    result = replace(result, evidence_candidates=(candidate, candidate))
    fake = FakeScientificRAGCapability(result)
    with pytest.raises(ValueError, match="duplicate"):
        fake.answer(request((source_id,)), context())
    result = replace(result, evidence_candidates=(candidate,) * 3)
    with pytest.raises(ValueError, match="limit"):
        FakeScientificRAGCapability(result).answer(request((source_id,)), context())


def test_answer_and_excerpt_are_bounded_and_answer_requires_evidence():
    source_id = uuid4()
    with pytest.raises(ValueError):
        EvidenceCandidate(source_id, "page 2", "x" * 4001)
    result = response(source_id)
    from dataclasses import replace

    with pytest.raises(ValueError, match="evidence"):
        FakeScientificRAGCapability(replace(result, evidence_candidates=())).answer(
            request((source_id,)), context()
        )
    with pytest.raises(ValueError):
        replace(result, answer_candidate="x" * 16001)


def test_cancellation_prevents_fake_answer_without_claiming_provider_result():
    source_id = uuid4()
    fake = FakeScientificRAGCapability(response(source_id))
    with pytest.raises(ValueError, match="cancel"):
        fake.answer(request((source_id,)), context(True))
    assert fake.calls == []


def test_query_and_adapter_provenance_cannot_be_substituted():
    from dataclasses import replace

    source_id = uuid4()
    original = response(source_id)
    with pytest.raises(ValueError, match="query"):
        FakeScientificRAGCapability(
            replace(original, retrieval_query="unrelated query")
        ).answer(request((source_id,)), context())
    with pytest.raises(ValueError, match="provenance"):
        FakeScientificRAGCapability(replace(original, provider_id="unapproved")).answer(
            request((source_id,)), context()
        )
