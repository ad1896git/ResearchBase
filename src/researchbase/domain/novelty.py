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


class ProbeDisposition(StrEnum):
    NO_HITS = "NO_HITS"
    SCREENED = "SCREENED"
    INCOMPLETE = "INCOMPLETE"


class ScreeningDisposition(StrEnum):
    NOT_CLOSE = "NOT_CLOSE"
    CLOSE = "CLOSE"
    UNCLEAR = "UNCLEAR"
    EXCLUDED = "EXCLUDED"
    UNRESOLVED = "UNRESOLVED"


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
        "SearchResultResolution",
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
            "SearchResultResolution",
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


@dataclass(frozen=True, slots=True)
class CapturedResolution:
    id: UUID
    content_hash: str
    source_id: UUID
    source_version_id: UUID | None

    def __post_init__(self) -> None:
        if (
            type(self.id) is not UUID
            or type(self.source_id) is not UUID
            or (self.source_version_id is not None and type(self.source_version_id) is not UUID)
            or type(self.content_hash) is not str
            or not re.fullmatch("[0-9a-f]{64}", self.content_hash)
        ):
            raise ValueError("exact captured resolution required")

    def material(self) -> dict[str, str]:
        return {
            "type": "SearchResultResolution",
            "id": str(self.id),
            "content_hash": self.content_hash,
        }


@dataclass(frozen=True, slots=True)
class CapturedResult:
    search_result_record_id: UUID
    resolutions: tuple[CapturedResolution, ...]

    def __post_init__(self) -> None:
        if (
            type(self.search_result_record_id) is not UUID
            or type(self.resolutions) is not tuple
            or any(type(x) is not CapturedResolution for x in self.resolutions)
            or len({x.id for x in self.resolutions}) != len(self.resolutions)
        ):
            raise ValueError("distinct typed captured resolutions required")

    @property
    def resolved_source(self) -> UUID | None:
        pairs = {(x.source_id, x.source_version_id) for x in self.resolutions}
        if len(pairs) == 1 and all(x.source_version_id is not None for x in self.resolutions):
            return self.resolutions[0].source_id
        return None

    def material(self) -> dict[str, object]:
        return {
            "search_result_record": {
                "type": "SearchResultRecord",
                "id": str(self.search_result_record_id),
            },
            "resolutions": [x.material() for x in sorted(self.resolutions, key=lambda x: x.id)],
        }


def coverage_material_v2(
    plan: HashRef,
    executions: tuple[UUID, ...],
    providers: tuple[str, ...],
    query_count: int,
    result_count: int,
    resolved_source_count: int,
    time_scope: TimeScope | None,
    limitations: str,
    captured_unresolved_result_count: int,
    captured_results: tuple[CapturedResult, ...],
) -> dict[str, object]:
    material = coverage_material(
        plan,
        executions,
        providers,
        query_count,
        result_count,
        resolved_source_count,
        time_scope,
        limitations,
    )
    if (
        type(captured_results) is not tuple
        or any(type(x) is not CapturedResult for x in captured_results)
        or len({x.search_result_record_id for x in captured_results}) != len(captured_results)
        or len(captured_results) != result_count
        or type(captured_unresolved_result_count) is not int
        or not 0 <= captured_unresolved_result_count <= result_count
        or captured_unresolved_result_count
        != sum(x.resolved_source is None for x in captured_results)
        or resolved_source_count
        != len({x.resolved_source for x in captured_results if x.resolved_source is not None})
    ):
        raise ValueError("invalid captured membership accounting")
    refs = [r.id for x in captured_results for r in x.resolutions]
    if len(set(refs)) != len(refs):
        raise ValueError("duplicate captured resolution")
    material.update(
        material_version=2,
        captured_unresolved_result_count=captured_unresolved_result_count,
        captured_results=[
            x.material() for x in sorted(captured_results, key=lambda x: x.search_result_record_id)
        ],
    )
    return material


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


@dataclass(frozen=True, slots=True)
class PriorArtBasisInput:
    prior_art_relation_id: UUID
    search_result_resolution_id: UUID

    def __post_init__(self):
        if any(
            type(x) is not UUID
            for x in (self.prior_art_relation_id, self.search_result_resolution_id)
        ):
            raise ValueError("exact basis UUIDs required")


@dataclass(frozen=True, slots=True)
class ClosenessCriteria:
    statements: tuple[str, ...]

    def __post_init__(self):
        if type(self.statements) is not tuple or not 1 <= len(self.statements) <= 100:
            raise ValueError("one to 100 criteria statements required")
        values = tuple(narrative(x) for x in self.statements)
        if sum(map(len, values)) > 16384:
            raise ValueError("criteria total exceeds bound")
        object.__setattr__(self, "statements", values)

    def material(self):
        return {"statements": list(self.statements)}


def basis_inputs(values):
    if (
        type(values) is not tuple
        or len(values) > 100
        or any(type(x) is not PriorArtBasisInput for x in values)
    ):
        raise ValueError("closed bounded basis required")
    if len({x.prior_art_relation_id for x in values}) != len(values):
        raise ValueError("distinct basis relations required")
    return tuple(sorted(values, key=lambda x: x.prior_art_relation_id))


def novelty_material_v2(
    claim,
    coverage,
    assessment,
    limitations,
    predecessor,
    actor,
    scope_statement,
    closeness_criteria,
    prior_art_basis,
):
    if (
        assessment is not NoveltyOutcome.CLOSE_PRIOR_ART_FOUND
        or type(closeness_criteria) is not ClosenessCriteria
    ):
        raise ValueError("typed close finding required")
    if type(prior_art_basis) is not tuple or not 1 <= len(prior_art_basis) <= 100:
        raise ValueError("bounded close basis required")
    seen = set()
    for relation, witness in prior_art_basis:
        if (
            type(relation) is not HashRef
            or type(witness) is not HashRef
            or relation.type != "PriorArtRelation"
            or witness.type != "SearchResultResolution"
            or relation.id in seen
        ):
            raise ValueError("distinct typed basis required")
        seen.add(relation.id)
    material = novelty_material(claim, coverage, assessment, limitations, predecessor, actor)
    material.update(
        material_version=2,
        scope_statement=narrative(scope_statement),
        closeness_criteria=closeness_criteria.material(),
        prior_art_basis=[
            {"prior_art_relation": r.material(), "search_result_resolution": w.material()}
            for r, w in sorted(prior_art_basis, key=lambda pair: pair[0].id)
        ],
    )
    return material


def versioned_novelty_material(
    version,
    *args,
    scope_statement=None,
    closeness_criteria=None,
    prior_art_basis=(),
    screening_basis=None,
):
    if type(version) is not int or version not in (1, 2):
        raise ValueError("unknown novelty material version")
    if version == 1:
        if (
            args[2] is not NoveltyOutcome.INCONCLUSIVE
            or scope_statement is not None
            or closeness_criteria is not None
            or prior_art_basis
            or screening_basis is not None
        ):
            raise ValueError("invalid v1 material")
        return novelty_material(*args)
    if screening_basis is not None:
        if prior_art_basis:
            raise ValueError("screening forbids positive basis")
        return screening_novelty_material(
            args[0],
            args[1],
            args[2],
            args[3],
            args[4],
            args[5],
            scope_statement,
            closeness_criteria,
            screening_basis,
        )
    return novelty_material_v2(
        args[0],
        args[1],
        args[2],
        args[3],
        args[4],
        args[5],
        scope_statement,
        closeness_criteria,
        prior_art_basis,
    )


@dataclass(frozen=True, slots=True)
class ProbeInput:
    search_execution_id: UUID
    query_index: int
    disposition: ProbeDisposition
    rationale: str

    def __post_init__(self):
        if (
            type(self.search_execution_id) is not UUID
            or type(self.query_index) is not int
            or not 0 <= self.query_index <= 31
            or type(self.disposition) is not ProbeDisposition
        ):
            raise ValueError("typed bounded probe required")
        object.__setattr__(self, "rationale", narrative(self.rationale))

    def material(self):
        return {
            "search_execution": {
                "type": "LiteratureSearchExecution",
                "id": str(self.search_execution_id),
            },
            "query_index": self.query_index,
            "disposition": self.disposition.value,
            "rationale": self.rationale,
        }


@dataclass(frozen=True, slots=True)
class ScreeningResultInput:
    search_result_record_id: UUID
    disposition: ScreeningDisposition
    criteria_ordinals: tuple[int, ...]
    rationale: str
    prior_art_relation_id: UUID | None = None
    search_result_resolution_id: UUID | None = None

    def __post_init__(self):
        if (
            type(self.search_result_record_id) is not UUID
            or type(self.disposition) is not ScreeningDisposition
        ):
            raise ValueError("typed result required")
        refs = (self.prior_art_relation_id, self.search_result_resolution_id)
        if (
            any(x is not None and type(x) is not UUID for x in refs)
            or (refs[0] is None) != (refs[1] is None)
            or (
                self.disposition in {ScreeningDisposition.NOT_CLOSE, ScreeningDisposition.CLOSE}
                and refs[0] is None
            )
            or (self.disposition is ScreeningDisposition.UNRESOLVED and refs[0] is not None)
        ):
            raise ValueError("paired exact references required")
        v = self.criteria_ordinals
        if (
            type(v) is not tuple
            or not 1 <= len(v) <= 100
            or any(type(x) is not int or not 0 <= x <= 99 for x in v)
            or len(set(v)) != len(v)
        ):
            raise ValueError("distinct bounded criterion ordinals required")
        object.__setattr__(self, "criteria_ordinals", tuple(sorted(v)))
        object.__setattr__(self, "rationale", narrative(self.rationale))


@dataclass(frozen=True, slots=True)
class ScreeningBasisInput:
    probes: tuple[ProbeInput, ...]
    results: tuple[ScreeningResultInput, ...]

    def __post_init__(self):
        if (
            type(self.probes) is not tuple
            or not 1 <= len(self.probes) <= 3200
            or any(type(x) is not ProbeInput for x in self.probes)
            or type(self.results) is not tuple
            or len(self.results) > 10000
            or any(type(x) is not ScreeningResultInput for x in self.results)
        ):
            raise ValueError("bounded typed screening basis required")
        keys = {(x.search_execution_id, x.query_index) for x in self.probes}
        if (
            len(keys) != len(self.probes)
            or len({x.search_execution_id for x in self.probes}) > 100
            or len({x.search_result_record_id for x in self.results}) != len(self.results)
        ):
            raise ValueError("distinct bounded screening inventory required")
        object.__setattr__(
            self,
            "probes",
            tuple(sorted(self.probes, key=lambda x: (x.search_execution_id, x.query_index))),
        )
        object.__setattr__(
            self, "results", tuple(sorted(self.results, key=lambda x: x.search_result_record_id))
        )


@dataclass(frozen=True, slots=True)
class ScreeningResult:
    search_result_record_id: UUID
    disposition: ScreeningDisposition
    criteria_ordinals: tuple[int, ...]
    rationale: str
    prior_art_relation: HashRef | None
    search_result_resolution: HashRef | None

    def __post_init__(self):
        for reference, kind in (
            (self.prior_art_relation, "PriorArtRelation"),
            (self.search_result_resolution, "SearchResultResolution"),
        ):
            if reference is not None and (type(reference) is not HashRef or reference.type != kind):
                raise ValueError("typed screening references required")
        normalized = ScreeningResultInput(
            self.search_result_record_id,
            self.disposition,
            self.criteria_ordinals,
            self.rationale,
            self.prior_art_relation.id if self.prior_art_relation else None,
            self.search_result_resolution.id if self.search_result_resolution else None,
        )
        object.__setattr__(self, "criteria_ordinals", normalized.criteria_ordinals)
        object.__setattr__(self, "rationale", normalized.rationale)

    def material(self):
        return {
            "search_result_record": {
                "type": "SearchResultRecord",
                "id": str(self.search_result_record_id),
            },
            "disposition": self.disposition.value,
            "criteria_ordinals": list(self.criteria_ordinals),
            "rationale": self.rationale,
            "prior_art_relation": self.prior_art_relation.material()
            if self.prior_art_relation
            else None,
            "search_result_resolution": self.search_result_resolution.material()
            if self.search_result_resolution
            else None,
        }


@dataclass(frozen=True, slots=True)
class ScreeningBasis:
    probes: tuple[ProbeInput, ...]
    results: tuple[ScreeningResult, ...]

    def inputs(self):
        return ScreeningBasisInput(
            self.probes,
            tuple(
                ScreeningResultInput(
                    x.search_result_record_id,
                    x.disposition,
                    x.criteria_ordinals,
                    x.rationale,
                    x.prior_art_relation.id if x.prior_art_relation else None,
                    x.search_result_resolution.id if x.search_result_resolution else None,
                )
                for x in self.results
            ),
        )

    def material(self):
        inputs = self.inputs()
        by_id = {x.search_result_record_id: x for x in self.results}
        return {
            "probes": [x.material() for x in inputs.probes],
            "results": [by_id[x.search_result_record_id].material() for x in inputs.results],
        }


def screening_novelty_material(
    claim,
    coverage,
    assessment,
    limitations,
    predecessor,
    actor,
    scope_statement,
    closeness_criteria,
    screening_basis,
):
    if (
        assessment
        not in {NoveltyOutcome.INCONCLUSIVE, NoveltyOutcome.NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE}
        or type(closeness_criteria) is not ClosenessCriteria
        or type(screening_basis) is not ScreeningBasis
    ):
        raise ValueError("typed screening shape required")
    if any(
        i >= len(closeness_criteria.statements)
        for x in screening_basis.results
        for i in x.criteria_ordinals
    ):
        raise ValueError("criterion outside parent")
    material = novelty_material(claim, coverage, assessment, limitations, predecessor, actor)
    material.update(
        material_version=2,
        scope_statement=narrative(scope_statement),
        closeness_criteria=closeness_criteria.material(),
        prior_art_basis=[],
        screening_basis=screening_basis.material(),
    )
    return material
