"""Deterministic native research strategy; outputs remain unverified candidates."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from researchbase.application.scientific_rag_provider import (
    RetrievalConstraints,
    ScientificRAGCallContext,
    ScientificRAGCapability,
    ScientificRAGRequest,
    SourceLocator,
    validate_scientific_rag_response,
)


class StrategyCancelled(Exception):
    """Local cancellation; no partial candidate is returned."""


@dataclass(frozen=True, slots=True)
class ResearchStrategyRequest:
    topic: str
    source_version_ids: tuple[UUID, ...]
    max_evidence_candidates: int = 20

    def __post_init__(self) -> None:
        if not isinstance(self.topic, str) or not self.topic.strip() or len(self.topic) > 255:
            raise ValueError("topic must be nonblank and at most 255 characters")
        ScientificRAGRequest(
            self.topic,
            self.source_version_ids,
            RetrievalConstraints(self.max_evidence_candidates),
        )


@dataclass(frozen=True, slots=True)
class ResearchStrategyContext:
    authorized_request: ResearchStrategyRequest
    cancellation_requested: Callable[[], bool]


@dataclass(frozen=True, slots=True)
class PerspectivePlan:
    name: str
    query: str


@dataclass(frozen=True, slots=True)
class ResearchStrategyPlan:
    topic: str
    source_version_ids: tuple[UUID, ...]
    max_evidence_candidates: int
    perspectives: tuple[PerspectivePlan, ...]


@dataclass(frozen=True, slots=True)
class StrategyEvidenceCandidate:
    source_version_id: UUID
    locator: SourceLocator
    excerpt: str
    perspective: str
    query: str
    rag_adapter_id: str
    rag_adapter_version: str
    provider_id: str
    retrieved_at: datetime


@dataclass(frozen=True, slots=True)
class BriefSectionCandidate:
    perspective: str
    query: str
    answer_candidate: str | None
    evidence_candidates: tuple[StrategyEvidenceCandidate, ...]
    contradictions: tuple[str, ...] = ()
    missing_evidence: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ResearchBriefCandidate:
    artifact_type: str
    topic: str
    sections: tuple[BriefSectionCandidate, ...]
    coverage_limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class StrategyExecutionMetadata:
    strategy_id: str
    strategy_version: str
    rag_adapter_id: str
    rag_adapter_version: str
    query_count: int
    source_count: int
    provider_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ResearchStrategyResult:
    search_plan_candidate: ResearchStrategyPlan
    source_candidates: tuple[()]
    literature_evidence_candidates: tuple[StrategyEvidenceCandidate, ...]
    research_brief_candidate: ResearchBriefCandidate
    open_question_candidates: tuple[str, ...]
    hypothesis_candidates: tuple[()]
    warnings: tuple[str, ...]
    execution_metadata: StrategyExecutionMetadata


class ResearchStrategy(Protocol):
    strategy_id: str
    strategy_version: str

    def prepare_plan(
        self, request: ResearchStrategyRequest, context: ResearchStrategyContext
    ) -> ResearchStrategyPlan: ...

    def execute(
        self,
        plan: ResearchStrategyPlan,
        capabilities: ScientificRAGCapability,
        context: ResearchStrategyContext,
    ) -> ResearchStrategyResult: ...


class NativeResearchStrategy:
    strategy_id = "native-storm-like"
    strategy_version = "candidate-v1"
    _perspectives = ("methods", "findings", "limitations")

    @staticmethod
    def _check_cancel(context: ResearchStrategyContext) -> None:
        if context.cancellation_requested():
            raise StrategyCancelled("strategy cancelled")

    def prepare_plan(
        self, request: ResearchStrategyRequest, context: ResearchStrategyContext
    ) -> ResearchStrategyPlan:
        self._check_cancel(context)
        if request != context.authorized_request:
            raise ValueError("strategy request differs from trusted context")
        topic = request.topic.strip()
        return ResearchStrategyPlan(
            topic,
            request.source_version_ids,
            request.max_evidence_candidates,
            tuple(
                PerspectivePlan(name, f"What {name} are reported for {topic}?")
                for name in self._perspectives
            ),
        )

    def execute(
        self,
        plan: ResearchStrategyPlan,
        capabilities: ScientificRAGCapability,
        context: ResearchStrategyContext,
    ) -> ResearchStrategyResult:
        self._check_cancel(context)
        if plan != self.prepare_plan(context.authorized_request, context):
            raise ValueError("strategy plan differs from deterministic preparation")
        sections: list[BriefSectionCandidate] = []
        evidence: list[StrategyEvidenceCandidate] = []
        open_questions: list[str] = []
        warnings = ["UNVERIFIED_CANDIDATE", "COVERAGE_LIMITED"]
        provider_ids: list[str] = []
        for perspective in plan.perspectives:
            self._check_cancel(context)
            rag_request = ScientificRAGRequest(
                perspective.query,
                plan.source_version_ids,
                RetrievalConstraints(plan.max_evidence_candidates),
            )
            try:
                response = capabilities.answer(
                    rag_request, ScientificRAGCallContext(context.cancellation_requested)
                )
            except StrategyCancelled:
                raise
            except Exception:
                # Provider error text may contain secrets; only a fixed warning escapes.
                warnings.append("RAG_UNAVAILABLE")
                open_questions.append(perspective.query)
                sections.append(
                    BriefSectionCandidate(perspective.name, perspective.query, None, ())
                )
                continue
            self._check_cancel(context)
            validate_scientific_rag_response(rag_request, response)
            if (
                response.adapter_id != capabilities.adapter_id
                or response.adapter_version != capabilities.adapter_version
            ):
                raise ValueError("RAG adapter provenance mismatch")
            provider_ids.append(response.provider_id)
            candidates = tuple(
                StrategyEvidenceCandidate(
                    item.source_version_id,
                    item.locator,
                    item.excerpt,
                    perspective.name,
                    perspective.query,
                    response.adapter_id,
                    response.adapter_version,
                    response.provider_id,
                    response.retrieved_at,
                )
                for item in response.evidence_candidates
            )
            evidence.extend(candidates)
            qualified = bool(response.contradictions or response.missing_evidence)
            answer = response.answer_candidate if candidates and not qualified else None
            if response.contradictions:
                warnings.append("CONTRADICTION_CANDIDATE")
            if response.missing_evidence:
                warnings.append("MISSING_EVIDENCE")
            if answer is None:
                warnings.append("MISSING_EVIDENCE")
                open_questions.append(perspective.query)
            sections.append(
                BriefSectionCandidate(
                    perspective.name,
                    perspective.query,
                    answer,
                    candidates,
                    response.contradictions,
                    response.missing_evidence,
                )
            )
        self._check_cancel(context)
        return ResearchStrategyResult(
            plan,
            (),
            tuple(evidence),
            ResearchBriefCandidate(
                "research_brief",
                plan.topic,
                tuple(sections),
                ("SOURCE_SET_ONLY", "NOT_COMPREHENSIVE"),
            ),
            tuple(open_questions),
            (),
            tuple(dict.fromkeys(warnings)),
            StrategyExecutionMetadata(
                self.strategy_id,
                self.strategy_version,
                capabilities.adapter_id,
                capabilities.adapter_version,
                len(plan.perspectives),
                len(plan.source_version_ids),
                tuple(dict.fromkeys(provider_ids)),
            ),
        )
