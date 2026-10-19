"""Literal first-slice novelty material and closed scientific values."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Literal
from uuid import UUID


class PriorArtKind(StrEnum):
    IDENTICAL = "IDENTICAL"
    HIGHLY_SIMILAR = "HIGHLY_SIMILAR"
    PARTIAL_OVERLAP = "PARTIAL_OVERLAP"
    RELATED = "RELATED"
    CONTRASTING = "CONTRASTING"
    UNCLEAR = "UNCLEAR"


class PriorArtSelectionState(StrEnum):
    EMPTY = "EMPTY"
    UNIQUE = "UNIQUE"
    AMBIGUOUS = "AMBIGUOUS"


class NoveltyOutcome(StrEnum):
    INCONCLUSIVE = "INCONCLUSIVE"
    CLOSE_PRIOR_ART_FOUND = "CLOSE_PRIOR_ART_FOUND"
    NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE = "NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE"


class QualityWarning(StrEnum):
    NO_INVOKED_QUERIES = "NO_INVOKED_QUERIES"
    FAILED_ATTEMPT = "FAILED_ATTEMPT"
    CANCELLED_ATTEMPT = "CANCELLED_ATTEMPT"
    UNKNOWN_ATTEMPT = "UNKNOWN_ATTEMPT"
    UNINVOKED_PROVIDER = "UNINVOKED_PROVIDER"
    PARTIAL_RESULTS = "PARTIAL_RESULTS"
    UNRESOLVED_RESULTS = "UNRESOLVED_RESULTS"
    FILTER_COMPLIANCE_UNPROVEN = "FILTER_COMPLIANCE_UNPROVEN"
    SCREENING_NOT_CAPTURED = "SCREENING_NOT_CAPTURED"
    INPUT_CURRENTLY_UNUSABLE = "INPUT_CURRENTLY_UNUSABLE"


def narrative(value: str, limit: int = 16384) -> str:
    if type(value) is not str:
        raise ValueError("text required")
    value = unicodedata.normalize("NFC", value)
    if not value.strip() or len(value) > limit or "\x00" in value:
        raise ValueError("nonblank bounded text required")
    try:
        value.encode("utf8", "strict")
    except UnicodeError:
        raise ValueError("valid Unicode required") from None
    return value


def uuid_set(value: tuple[UUID, ...]) -> tuple[UUID, ...]:
    if type(value) is not tuple or not 1 <= len(value) <= 100:
        raise ValueError("one to 100 exact UUIDs required")
    if any(type(x) is not UUID for x in value) or len(set(value)) != len(value):
        raise ValueError("distinct exact UUIDs required")
    return tuple(sorted(value))


@dataclass(frozen=True, slots=True)
class TimeScope:
    from_date: date | None
    through_date: date | None

    def __post_init__(self) -> None:
        if all(x is None for x in (self.from_date, self.through_date)) or any(
            x is not None and type(x) is not date for x in (self.from_date, self.through_date)
        ):
            raise ValueError("at least one exact date required")
        if self.from_date and self.through_date and self.from_date > self.through_date:
            raise ValueError("date bounds reversed")

    def material(self) -> dict[str, str | None]:
        return {
            "from": self.from_date.isoformat() if self.from_date else None,
            "through": self.through_date.isoformat() if self.through_date else None,
        }


@dataclass(frozen=True, slots=True)
class HashRef:
    type: Literal[
        "LiteratureSearchPlanVersion",
        "ClaimVersion",
        "SourceVersion",
        "LiteratureEvidence",
        "SearchCoverage",
        "NoveltyAssessment",
        "PriorArtRelation",
    ]
    id: UUID
    content_hash: str

    def __post_init__(self) -> None:
        if self.type not in {
            "LiteratureSearchPlanVersion",
            "ClaimVersion",
            "SourceVersion",
            "LiteratureEvidence",
            "SearchCoverage",
            "NoveltyAssessment",
            "PriorArtRelation",
        }:
            raise ValueError("unsupported reference")
        if (
            type(self.id) is not UUID
            or not isinstance(self.content_hash, str)
            or not re.fullmatch("[0-9a-f]{64}", self.content_hash)
        ):
            raise ValueError("exact hashed reference required")

    def material(self) -> dict[str, str]:
        return {"type": self.type, "id": str(self.id), "content_hash": self.content_hash}


def coverage_material(
    plan: HashRef,
    executions: tuple[UUID, ...],
    providers: tuple[str, ...],
    query_count: int,
    result_count: int,
    resolved_source_count: int,
    time_scope: TimeScope | None,
    limitations: str,
) -> dict[str, object]:
    if plan.type != "LiteratureSearchPlanVersion":
        raise ValueError("exact plan required")
    values = tuple(narrative(x, 128) for x in providers)
    if len(set(values)) != len(values):
        raise ValueError("duplicate providers")
    if (
        any(
            type(x) is not int or not 0 <= x <= 2147483647
            for x in (query_count, result_count, resolved_source_count)
        )
        or resolved_source_count > result_count
    ):
        raise ValueError("invalid captured counts")
    return {
        "type": "SearchCoverage",
        "material_version": 1,
        "search_plan_version": plan.material(),
        "search_execution": [
            {"type": "LiteratureSearchExecution", "id": str(x)} for x in uuid_set(executions)
        ],
        "providers": sorted(values),
        "query_count": query_count,
        "result_count": result_count,
        "resolved_source_count": resolved_source_count,
        "time_scope": time_scope.material() if time_scope else None,
        "coverage_limitations": narrative(limitations),
    }


def prior_art_material(
    claim: HashRef,
    source: HashRef,
    relation: PriorArtKind,
    rationale: str,
    evidence: tuple[HashRef, ...],
    actor: UUID,
    predecessor: HashRef | None = None,
    *,
    material_version: int = 1,
) -> dict[str, object]:
    if type(material_version) is not int or material_version not in (1, 2):
        raise ValueError("unknown prior-art material version")
    if (material_version == 1) != (predecessor is None) or (
        predecessor is not None and predecessor.type != "PriorArtRelation"
    ):
        raise ValueError("typed correction predecessor required")
    if (
        claim.type != "ClaimVersion"
        or source.type != "SourceVersion"
        or type(relation) is not PriorArtKind
        or type(actor) is not UUID
    ):
        raise ValueError("typed comparison required")
    uuid_set(tuple(x.id for x in evidence))
    if any(x.type != "LiteratureEvidence" for x in evidence):
        raise ValueError("typed evidence required")
    material: dict[str, object] = {
        "type": "PriorArtRelation",
        "material_version": material_version,
        "claim_version": claim.material(),
        "source_version": source.material(),
        "relation": relation.value,
        "rationale": narrative(rationale),
        "literature_evidence": [x.material() for x in sorted(evidence, key=lambda x: x.id)],
        "assessed_by": {"type": "ActorIdentity", "id": str(actor)},
    }

    if predecessor is not None:
        material["supersedes_prior_art_relation"] = predecessor.material()
    return material


def novelty_material(
    claim: HashRef,
    coverage: HashRef,
    assessment: NoveltyOutcome,
    limitations: str,
    predecessor: HashRef | None,
    actor: UUID,
) -> dict[str, object]:
    if (
        claim.type != "ClaimVersion"
        or coverage.type != "SearchCoverage"
        or type(assessment) is not NoveltyOutcome
        or type(actor) is not UUID
        or (predecessor is not None and predecessor.type != "NoveltyAssessment")
    ):
        raise ValueError("typed assessment required")
    return {
        "type": "NoveltyAssessment",
        "material_version": 1,
        "claim_version": claim.material(),
        "search_coverage": coverage.material(),
        "assessment": assessment.value,
        "limitations": narrative(limitations),
        "supersedes_assessment": predecessor.material() if predecessor else None,
        "assessed_by": {"type": "ActorIdentity", "id": str(actor)},
    }


def prior_art_chains(
    rows: tuple[tuple[UUID, UUID, UUID, UUID | None], ...],
) -> tuple[tuple[UUID, UUID], ...]:
    """Validate an entire exact-pair graph and return UUID-sorted root/terminal pairs."""
    if len(rows) > 10000:
        raise ValueError("prior-art selection limit exceeded")
    nodes = {r[0]: r for r in rows}
    if len(nodes) != len(rows) or len({(r[1], r[2]) for r in rows}) > 1:
        raise ValueError("invalid exact-pair graph")
    successors = {}
    for identity, _, _, previous in rows:
        if previous is not None:
            if previous not in nodes or previous in successors:
                raise ValueError("unresolved or forked correction")
            successors[previous] = identity
    visited = set()
    result = []
    for root in sorted(r[0] for r in rows if r[3] is None):
        current = root
        while True:
            if current in visited:
                raise ValueError("cyclic correction")
            visited.add(current)
            if current not in successors:
                break
            current = successors[current]
        result.append((root, current))
    if len(visited) != len(nodes):
        raise ValueError("cyclic correction")
    return tuple(result)
