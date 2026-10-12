"""Authorized, read-only exact-version ManuscriptVersion scientific trace."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from researchbase.application.ports import UnitOfWork
from researchbase.application.publication import _READERS, PublicationService
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.errors import ErrorCode, ResearchBaseError

_FROZEN = frozenset({"FROZEN", "SUPERSEDED"})
_HASH = re.compile(r"[0-9a-f]{64}\Z")


def _unresolved() -> None:
    raise ResearchBaseError(ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                            "manuscript scientific trace has unresolved exact provenance")


def _valid_hash(value: object) -> bool:
    return isinstance(value, str) and _HASH.fullmatch(value) is not None


@dataclass(frozen=True, slots=True)
class PlacementTraceItem:
    placement_kind: str
    placement_id: UUID
    target_id: UUID
    target_content_hash: str
    section_id: str
    locator: dict[str, str]
    ordinal: int
    annotation: str
    semantic: str
    support_set_hash: str | None


@dataclass(frozen=True, slots=True)
class ConclusionClaimInputTrace:
    conclusion_version_id: UUID
    claim_version_id: UUID
    relation_type: str
    ordinal: int
    literature_support_snapshot_id: UUID | None
    claim_content_hash: str


@dataclass(frozen=True, slots=True)
class ClaimExperimentEvidenceTrace:
    claim_version_id: UUID
    evidence_relation_id: UUID
    relation_type: str
    measurement_id: UUID
    statistical_result_id: UUID | None
    run_id: UUID
    input_role: str | None
    input_ordinal: int | None


@dataclass(frozen=True, slots=True)
class LiteratureEvidenceTrace:
    link_kind: str
    owner_version_id: UUID
    snapshot_id: UUID | None
    relation_id: UUID | None
    evidence_id: UUID
    relation_type: str
    ordinal: int
    source_version_id: UUID
    evidence_content_hash: str
    source_content_hash: str
    review_status: str
    review_event_id: UUID | None


@dataclass(frozen=True, slots=True)
class ManuscriptScientificTrace:
    project_id: UUID
    publication_id: UUID
    manuscript_version_id: UUID
    manuscript_status: str
    manuscript_content_hash: str | None
    placements: tuple[PlacementTraceItem, ...]
    conclusion_claim_inputs: tuple[ConclusionClaimInputTrace, ...]
    claim_experiment_evidence: tuple[ClaimExperimentEvidenceTrace, ...]
    literature_evidence: tuple[LiteratureEvidenceTrace, ...]


class ManuscriptScientificTraceService:
    """Query persisted paths only; never infer support or human verification."""

    def __init__(self, factory: Callable[[], UnitOfWork], credentials: Any) -> None:
        self._factory = factory
        self._auth = PublicationService(factory, credentials, None)

    @staticmethod
    def _placements(rows: list[dict[str, Any]]) -> tuple[PlacementTraceItem, ...]:
        result: list[PlacementTraceItem] = []
        for row in rows:
            if (not isinstance(row["target_id"], UUID)
                or row["project_match"] is not True or row["target_status"] not in _FROZEN
                or row["target_frozen_at"] is None or not _valid_hash(row["target_hash"])
                or (row["placement_kind"] == "CONCLUSION"
                    and not _valid_hash(row["support_hash"]))):
                _unresolved()
            result.append(PlacementTraceItem(
                row["placement_kind"], row["placement_id"], row["target_id"],
                row["target_hash"], row["section_id"], dict(row["locator"]),
                row["ordinal"], row["annotation"],
                "CITATION_ONLY" if row["placement_kind"] == "CITATION" else "PLACEMENT_ONLY",
                row["support_hash"],
            ))
        return tuple(result)

    @staticmethod
    def _conclusion_claims(
        rows: list[dict[str, Any]], project: UUID,
    ) -> tuple[ConclusionClaimInputTrace, ...]:
        result: list[ConclusionClaimInputTrace] = []
        for row in rows:
            if (row["claim_project_id"] != project or row["claim_status"] not in _FROZEN
                or row["claim_frozen_at"] is None
                or not _valid_hash(row["claim_content_hash"])):
                _unresolved()
            result.append(ConclusionClaimInputTrace(
                row["conclusion_version_id"], row["claim_version_id"],
                row["relation_type"], row["ordinal"],
                row["literature_support_snapshot_id"], row["claim_content_hash"],
            ))
        return tuple(result)

    @staticmethod
    def _experiment_paths(
        rows: list[dict[str, Any]], project: UUID,
    ) -> tuple[ClaimExperimentEvidenceTrace, ...]:
        result: list[ClaimExperimentEvidenceTrace] = []
        for row in rows:
            measurement = row["measurement_id"]
            run = row["run_id"]
            if (not isinstance(measurement, UUID) or not isinstance(run, UUID)
                or row["run_project_id"] != project):
                _unresolved()
            result.append(ClaimExperimentEvidenceTrace(
                row["claim_version_id"], row["evidence_relation_id"],
                row["relation_type"], measurement,
                row["statistical_result_id"], run,
                row["input_role"], row["input_ordinal"],
            ))
        return tuple(result)

    @staticmethod
    def _literature_paths(
        rows: list[dict[str, Any]], project: UUID,
    ) -> tuple[LiteratureEvidenceTrace, ...]:
        result: list[LiteratureEvidenceTrace] = []
        for row in rows:
            if (row["evidence_project_id"] != project
                or (row["link_kind"] == "CLAIM_SNAPSHOT"
                    and row["snapshot_project_id"] != project)
                or row["source_project_match"] is not True
                or row["source_status"] not in _FROZEN
                or row["source_frozen_at"] is None
                or not _valid_hash(row["evidence_content_hash"])
                or not _valid_hash(row["source_content_hash"])):
                _unresolved()
            reviewed = row["review_status"] != "UNREVIEWED"
            if reviewed != (row["review_event_id"] is not None):
                _unresolved()
            if reviewed and row["review_event_status"] != row["review_status"]:
                _unresolved()
            result.append(LiteratureEvidenceTrace(
                row["link_kind"], row["owner_version_id"], row["snapshot_id"],
                row["relation_id"], row["evidence_id"], row["relation_type"],
                row["ordinal"], row["source_version_id"],
                row["evidence_content_hash"], row["source_content_hash"],
                row["review_status"], row["review_event_id"],
            ))
        return tuple(result)

    def trace(
        self, principal: VerifiedPrincipal, project: UUID, publication: UUID,
        manuscript: UUID,
    ) -> ManuscriptScientificTrace:
        if type(publication) is not UUID or type(manuscript) is not UUID:
            raise ResearchBaseError(ErrorCode.VALIDATION_ERROR,
                                    "exact publication and manuscript version required")
        with self._factory() as uow:
            repo = uow.publication
            repo.begin_scientific_trace_snapshot()
            self._auth._authorize(uow, principal, project, _READERS)
            parent = repo.publication(publication, project)
            version = repo.version(manuscript, publication) if parent else None
            if version is None:
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "manuscript version not found")
            if (version["status"] in _FROZEN
                and (version["frozen_at"] is None
                    or not _valid_hash(version["content_hash"]))):
                _unresolved()
            placements = self._placements(repo.scientific_trace_placements(manuscript, project))
            claims = self._conclusion_claims(
                repo.scientific_trace_conclusion_claim_inputs(manuscript), project,
            )
            experiments = self._experiment_paths(
                repo.scientific_trace_claim_experiment_evidence(manuscript), project,
            )
            literature = self._literature_paths(
                repo.scientific_trace_literature_evidence(manuscript, project), project,
            )
            return ManuscriptScientificTrace(
                project, publication, manuscript, version["status"],
                version["content_hash"], placements, claims, experiments, literature,
            )
