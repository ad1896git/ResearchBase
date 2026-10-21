"""Provider-neutral scientific-RAG candidates; never canonical evidence."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol
from uuid import UUID


def _bounded_text(value: str, name: str, maximum: int) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{name} must be nonblank and at most {maximum} characters")


@dataclass(frozen=True, slots=True)
class RetrievalConstraints:
    max_evidence_candidates: int = 20

    def __post_init__(self) -> None:
        if (
            type(self.max_evidence_candidates) is not int
            or not 1 <= self.max_evidence_candidates <= 100
        ):
            raise ValueError("max_evidence_candidates must be between 1 and 100")


@dataclass(frozen=True, slots=True)
class ScientificRAGRequest:
    question: str
    source_version_ids: tuple[UUID, ...]
    retrieval_constraints: RetrievalConstraints

    def __post_init__(self) -> None:
        _bounded_text(self.question, "question", 16_000)
        if (
            not isinstance(self.source_version_ids, tuple)
            or not self.source_version_ids
            or any(type(value) is not UUID for value in self.source_version_ids)
            or len(set(self.source_version_ids)) != len(self.source_version_ids)
            or not isinstance(self.retrieval_constraints, RetrievalConstraints)
        ):
            raise ValueError("source_version_ids must be a unique nonempty canonical set")


@dataclass(frozen=True, slots=True)
class ScientificRAGCallContext:
    cancellation_requested: Callable[[], bool]


@dataclass(frozen=True, slots=True)
class SourceLocator:
    """A candidate source span shape; exact bytes are verified on promotion."""

    page: int | None = None
    section: str | None = None
    paragraph: str | None = None
    figure: str | None = None
    table: str | None = None
    quote_span: str | None = None

    def __post_init__(self) -> None:
        if self.page is not None and (type(self.page) is not int or self.page < 1):
            raise ValueError("locator page must be positive")
        if self.paragraph is not None and (
            not isinstance(self.paragraph, str)
            or re.fullmatch(r"[1-9][0-9]*", self.paragraph) is None
        ):
            raise ValueError("locator paragraph must be a positive ordinal")
        for name in ("section", "figure", "table"):
            value = getattr(self, name)
            if value is not None:
                _bounded_text(value, f"locator {name}", 128)
                if (
                    value != value.strip()
                    or any(unicodedata.category(character).startswith("C") for character in value)
                    or re.match(r"[A-Za-z][A-Za-z0-9+.-]*:", value) is not None
                    or "://" in value
                ):
                    raise ValueError("locator cannot be an opaque reference")
        if not any(
            value is not None
            for value in (self.page, self.section, self.paragraph, self.figure, self.table)
        ):
            raise ValueError("locator must identify a source span")
        if self.quote_span is not None:
            match = (
                re.fullmatch(r"char:(0|[1-9][0-9]*):([1-9][0-9]*)", self.quote_span)
                if isinstance(self.quote_span, str)
                else None
            )
            if self.paragraph is None or match is None or int(match[2]) <= int(match[1]):
                raise ValueError("locator quote span must be bounded within a paragraph")


@dataclass(frozen=True, slots=True)
class EvidenceCandidate:
    source_version_id: UUID
    locator: SourceLocator
    excerpt: str

    def __post_init__(self) -> None:
        if type(self.source_version_id) is not UUID:
            raise ValueError("candidate source_version_id must be a UUID")
        if not isinstance(self.locator, SourceLocator):
            raise ValueError("candidate locator must be a structured source span")
        _bounded_text(self.excerpt, "excerpt", 4_000)


@dataclass(frozen=True, slots=True)
class ScientificRAGResponse:
    answer_candidate: str | None
    evidence_candidates: tuple[EvidenceCandidate, ...]
    contradictions: tuple[str, ...]
    missing_evidence: tuple[str, ...]
    adapter_id: str
    adapter_version: str
    model_id: str | None
    provider_id: str
    retrieval_query: str
    retrieved_at: datetime

    def __post_init__(self) -> None:
        if self.answer_candidate is not None:
            _bounded_text(self.answer_candidate, "answer_candidate", 16_000)
        for name in ("adapter_id", "adapter_version", "provider_id"):
            _bounded_text(getattr(self, name), name, 128)
        if self.model_id is not None:
            _bounded_text(self.model_id, "model_id", 256)
        _bounded_text(self.retrieval_query, "retrieval_query", 16_000)
        if (
            not isinstance(self.evidence_candidates, tuple)
            or any(not isinstance(item, EvidenceCandidate) for item in self.evidence_candidates)
            or not isinstance(self.contradictions, tuple)
            or not isinstance(self.missing_evidence, tuple)
        ):
            raise ValueError("candidate collections must be typed tuples")
        for item in (*self.contradictions, *self.missing_evidence):
            _bounded_text(item, "candidate note", 1_000)
        if not isinstance(self.retrieved_at, datetime) or self.retrieved_at.utcoffset() is None:
            raise ValueError("retrieved_at must be timezone-aware")


def validate_scientific_rag_response(
    request: ScientificRAGRequest, response: ScientificRAGResponse
) -> None:
    """A provider candidate may cite only the caller's exact source set."""
    if response.retrieval_query != request.question:
        raise ValueError("retrieval query does not match the request")
    if len(response.evidence_candidates) > request.retrieval_constraints.max_evidence_candidates:
        raise ValueError("evidence candidate limit exceeded")
    if response.answer_candidate is not None and not response.evidence_candidates:
        raise ValueError("answer candidate requires source evidence")
    permitted = set(request.source_version_ids)
    seen: set[tuple[UUID, SourceLocator]] = set()
    for candidate in response.evidence_candidates:
        if candidate.source_version_id not in permitted:
            raise ValueError("candidate source is outside requested source set")
        key = (candidate.source_version_id, candidate.locator)
        if key in seen:
            raise ValueError("duplicate source locator candidate")
        seen.add(key)


class ScientificRAGCapability(Protocol):
    adapter_id: str
    adapter_version: str

    def answer(
        self, request: ScientificRAGRequest, context: ScientificRAGCallContext
    ) -> ScientificRAGResponse: ...


@dataclass(slots=True)
class FakeScientificRAGCapability:
    """Disconnected test adapter. Responses are supplied by tests, never generated."""

    response: ScientificRAGResponse
    adapter_id: str = "fake-scientific-rag"
    adapter_version: str = "1"
    calls: list[ScientificRAGRequest] = field(default_factory=list)

    def answer(
        self, request: ScientificRAGRequest, context: ScientificRAGCallContext
    ) -> ScientificRAGResponse:
        if context.cancellation_requested():
            raise ValueError("scientific RAG call cancelled before dispatch")
        self.calls.append(request)
        if (
            self.response.adapter_id != self.adapter_id
            or self.response.adapter_version != self.adapter_version
            or self.response.provider_id != "test-only"
        ):
            raise ValueError("fake adapter provenance mismatch")
        validate_scientific_rag_response(request, self.response)
        return self.response
