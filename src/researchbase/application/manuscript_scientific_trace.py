"""Authorized, read-only exact-version ManuscriptVersion scientific trace."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, NoReturn
from uuid import UUID

from researchbase.application.manuscript_freeze import ManuscriptFreezeService
from researchbase.application.ports import UnitOfWork
from researchbase.application.provenance_queries import ProvenanceQueryService
from researchbase.application.publication import _READERS, PublicationService
from researchbase.application.saved_provenance import MESSAGE, saved_dependency
from researchbase.domain.claim import ClaimVersionId
from researchbase.domain.literature_evidence import digest, snapshot_material, support_material
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.domain.scientific_conclusion import (
    ClaimConclusionInput,
    LiteratureConclusionInput,
    conclusion_content_material,
    conclusion_support_material,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import sha256_canonical_json

_FROZEN = frozenset({"FROZEN", "SUPERSEDED"})
_HASH = re.compile(r"[0-9a-f]{64}\Z")


def _unresolved() -> NoReturn:
    raise ResearchBaseError(
        ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
        MESSAGE,
    )


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
    conclusion_version_id: UUID
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

    def __init__(
        self, factory: Callable[[], UnitOfWork], credentials: Any, store: Any = None
    ) -> None:
        self._factory = factory
        self._auth = PublicationService(factory, credentials, None)
        self._freeze = ManuscriptFreezeService(factory, credentials, store)

    @staticmethod
    def _placements(rows: list[dict[str, Any]]) -> tuple[PlacementTraceItem, ...]:
        result: list[PlacementTraceItem] = []
        for row in rows:
            if (
                not isinstance(row["target_id"], UUID)
                or row["project_match"] is not True
                or row["target_status"] not in _FROZEN
                or row["target_frozen_at"] is None
                or not _valid_hash(row["target_hash"])
                or (row["placement_kind"] == "CONCLUSION" and not _valid_hash(row["support_hash"]))
            ):
                _unresolved()
            result.append(
                PlacementTraceItem(
                    row["placement_kind"],
                    row["placement_id"],
                    row["target_id"],
                    row["target_hash"],
                    row["section_id"],
                    dict(row["locator"]),
                    row["ordinal"],
                    row["annotation"],
                    "CITATION_ONLY" if row["placement_kind"] == "CITATION" else "PLACEMENT_ONLY",
                    row["support_hash"],
                )
            )
        return tuple(result)

    @staticmethod
    def _conclusion_claims(
        rows: list[dict[str, Any]],
        project: UUID,
    ) -> tuple[ConclusionClaimInputTrace, ...]:
        result: list[ConclusionClaimInputTrace] = []
        for row in rows:
            if (
                (
                    row["literature_support_snapshot_id"] is not None
                    and (
                        row["resolved_snapshot_id"] != row["literature_support_snapshot_id"]
                        or row["snapshot_project_id"] != project
                        or row["snapshot_claim_id"] != row["claim_version_id"]
                        or not _valid_hash(row["snapshot_content_hash"])
                    )
                )
                or row["claim_project_id"] != project
                or row["claim_status"] not in _FROZEN
                or row["claim_frozen_at"] is None
                or not _valid_hash(row["claim_content_hash"])
            ):
                _unresolved()
            result.append(
                ConclusionClaimInputTrace(
                    row["conclusion_version_id"],
                    row["claim_version_id"],
                    row["relation_type"],
                    row["ordinal"],
                    row["literature_support_snapshot_id"],
                    row["claim_content_hash"],
                )
            )
        return tuple(result)

    @staticmethod
    def _experiment_paths(
        rows: list[dict[str, Any]],
        project: UUID,
    ) -> tuple[ClaimExperimentEvidenceTrace, ...]:
        result: list[ClaimExperimentEvidenceTrace] = []
        for row in rows:
            measurement = row["measurement_id"]
            run = row["run_id"]
            if (
                (
                    row["direct_measurement_id"] is not None
                    and row["resolved_direct_measurement_id"] != row["direct_measurement_id"]
                )
                or (
                    row["statistical_result_id"] is not None
                    and (
                        row["resolved_statistical_result_id"] != row["statistical_result_id"]
                        or row["result_project_id"] != project
                        or row["selected_input_measurement_id"] is None
                        or row["resolved_input_measurement_id"]
                        != row["selected_input_measurement_id"]
                    )
                )
                or not isinstance(measurement, UUID)
                or not isinstance(run, UUID)
                or row["run_project_id"] != project
            ):
                _unresolved()
            result.append(
                ClaimExperimentEvidenceTrace(
                    row["claim_version_id"],
                    row["evidence_relation_id"],
                    row["relation_type"],
                    measurement,
                    row["statistical_result_id"],
                    run,
                    row["input_role"],
                    row["input_ordinal"],
                )
            )
        return tuple(result)

    @staticmethod
    def _literature_paths(
        rows: list[dict[str, Any]],
        project: UUID,
    ) -> tuple[LiteratureEvidenceTrace, ...]:
        result: list[LiteratureEvidenceTrace] = []
        for row in rows:
            if (
                row["link_kind"] == "CLAIM_SNAPSHOT"
                and row["relation_id"] is None
                and row["snapshot_project_id"] == project
            ):
                continue  # Selected existing snapshot may have an empty relation set.
            if (
                row["evidence_project_id"] != project
                or (row["link_kind"] == "CLAIM_SNAPSHOT" and row["snapshot_project_id"] != project)
                or row["source_project_match"] is not True
                or row["source_status"] not in _FROZEN
                or row["source_frozen_at"] is None
                or not _valid_hash(row["evidence_content_hash"])
                or not _valid_hash(row["source_content_hash"])
            ):
                _unresolved()
            reviewed = row["review_status"] != "UNREVIEWED"
            if reviewed != (row["review_event_id"] is not None):
                _unresolved()
            if reviewed and row["review_event_status"] != row["review_status"]:
                _unresolved()
            result.append(
                LiteratureEvidenceTrace(
                    row["link_kind"],
                    row["conclusion_version_id"],
                    row["owner_version_id"],
                    row["snapshot_id"],
                    row["relation_id"],
                    row["evidence_id"],
                    row["relation_type"],
                    row["ordinal"],
                    row["source_version_id"],
                    row["evidence_content_hash"],
                    row["source_content_hash"],
                    row["review_status"],
                    row["review_event_id"],
                )
            )
        return tuple(result)

    def trace(
        self,
        principal: VerifiedPrincipal,
        project: UUID,
        publication: UUID,
        manuscript: UUID,
    ) -> ManuscriptScientificTrace:
        if any(type(value) is not UUID for value in (project, publication, manuscript)):
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR, "exact publication and manuscript version required"
            )
        self._freeze._principal(principal)
        with self._factory() as uow:
            uow.enable_manuscript_freeze_error_normalization()
            uow.manuscript_freeze.prepare_read()
            uow.enable_revision_action_snapshot_reads()
            repo = uow.publication
            self._freeze.authorize(uow, principal, project, _READERS)
            parent = repo.publication(publication, project)
            version = repo.version(manuscript, publication) if parent else None
            if version is None:
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "manuscript version not found")
            with saved_dependency():
                if version["status"] in _FROZEN and (
                    version["frozen_at"] is None or not _valid_hash(version["content_hash"])
                ):
                    _unresolved()
                if version["status"] == "FROZEN":
                    self._freeze.verify_in_uow(uow, project, parent, version, require_current=False)
                result = self.build_in_uow(uow, project, publication, manuscript, version)
            self._freeze.authorize(uow, principal, project, _READERS)
            return result

    def _verify_snapshots(self, rows: list[dict], project: UUID) -> set[UUID]:
        snapshots: dict[UUID, dict] = {}
        inputs: dict[UUID, list[dict]] = {}
        claims: set[UUID] = set()
        for row in rows:
            identity = row["selected_id"]
            if (
                row["id"] != identity
                or row["project_id"] != project
                or row["target_project"] != project
                or row["target_status"] not in _FROZEN
                or row["target_frozen_at"] is None
                or not _valid_hash(row["target_hash"])
                or row["hash_scheme"] != "sha256-cjson-v1"
            ):
                _unresolved()
            snapshots[identity] = row
            claims.add(row["claim_version_id"])
            inputs.setdefault(identity, [])
            if row["relation_id"] is None:
                continue
            if (
                row["evidence_project"] != project
                or not _valid_hash(row["evidence_hash"])
                or row["source_id"] is None
                or row["source_owner_id"] is None
                or row["source_artifact_id"] is None
                or row["source_artifact_project"] != project
                or (
                    row["selected_predecessor_id"] is not None
                    and row["resolved_predecessor_id"] != row["selected_predecessor_id"]
                )
                or (
                    row["selected_correction_artifact_id"] is not None
                    and (
                        row["resolved_correction_artifact_id"]
                        != row["selected_correction_artifact_id"]
                        or row["correction_artifact_owner_id"] is None
                    )
                )
            ):
                _unresolved()
            inputs[identity].append(
                {
                    "literature_evidence": {
                        "type": "LiteratureEvidence",
                        "id": str(row["literature_evidence_id"]),
                        "content_hash": row["evidence_hash"],
                    },
                    "relation_type": row["relation_type"],
                    "ordinal": row["ordinal"],
                    "qualification": row["qualification"],
                }
            )
        for identity, row in snapshots.items():
            previous = snapshots.get(row["previous_snapshot_id"])
            if row["previous_snapshot_id"] is not None and (
                previous is None
                or previous["claim_version_id"] != row["claim_version_id"]
                or previous["snapshot_number"] + 1 != row["snapshot_number"]
            ):
                _unresolved()
            if (
                digest(support_material(inputs[identity])) != row["literature_support_set_hash"]
                or digest(
                    snapshot_material(
                        row,
                        {
                            "type": "ClaimVersion",
                            "id": str(row["claim_version_id"]),
                            "content_hash": row["target_hash"],
                        },
                        previous,
                    )
                )
                != row["content_hash"]
            ):
                _unresolved()
        return claims

    @staticmethod
    def _verify_conclusion_hashes(
        versions: list[dict], claims: list[dict], literature: list[dict]
    ) -> None:
        for version in versions:
            identity = version["id"]
            # Placement occurrences may repeat; a conclusion's saved basis is hashed once.
            claim_rows = {
                row["ordinal"]: row for row in claims if row["conclusion_version_id"] == identity
            }
            literature_rows = {
                row["ordinal"]: row
                for row in literature
                if row["link_kind"] == "CONCLUSION_INPUT"
                and row["conclusion_version_id"] == identity
            }
            try:
                claim_inputs = tuple(
                    ClaimConclusionInput(
                        row["claim_version_id"],
                        row["claim_content_hash"],
                        row["relation_type"],
                        row["ordinal"],
                        row["literature_support_snapshot_id"],
                        row["snapshot_content_hash"],
                    )
                    for _, row in sorted(claim_rows.items())
                )
                literature_inputs = tuple(
                    LiteratureConclusionInput(
                        row["evidence_id"],
                        row["evidence_content_hash"],
                        row["relation_type"],
                        row["ordinal"],
                    )
                    for _, row in sorted(literature_rows.items())
                )
                support_hash = str(
                    sha256_canonical_json(
                        conclusion_support_material(claim_inputs, literature_inputs)
                    )
                )
                content_hash = str(
                    sha256_canonical_json(
                        conclusion_content_material(
                            version["scientific_conclusion_id"],
                            version["statement"],
                            version["scope"],
                            version["confidence"],
                            version["limitation_summary"],
                            support_hash,
                        )
                    )
                )
            except (ValueError, TypeError):
                _unresolved()
            if (
                support_hash != version["support_set_hash"]
                or content_hash != version["content_hash"]
            ):
                _unresolved()

    def build_in_uow(
        self, uow: UnitOfWork, project: UUID, publication: UUID, manuscript: UUID, version: dict
    ) -> ManuscriptScientificTrace:
        """Build the existing trace from exact rows in the caller's snapshot."""
        repo = uow.publication
        placement_rows = repo.scientific_trace_placements(manuscript, project)
        with saved_dependency():
            claim_ids = self._verify_snapshots(
                repo.scientific_trace_snapshot_closure(manuscript), project
            )
            claim_ids.update(
                row["target_id"] for row in placement_rows if row["placement_kind"] == "CLAIM"
            )
            claim_ids.update(
                row["claim_version_id"]
                for row in repo.scientific_trace_conclusion_claim_inputs(manuscript)
            )
            relations = [
                edge
                for identity in sorted(claim_ids, key=str)
                for edge in uow.claims.list_evidence(ClaimVersionId(identity))
            ]
            context = ProvenanceQueryService(self._factory)._load_claim_context(uow, relations)
            validator = self._freeze._literature._validator
            for identity in sorted(claim_ids, key=str):
                if not validator.validate_claim_version_in_uow(
                    uow, ClaimVersionId(identity), context
                ).complete:
                    _unresolved()
        placements = self._placements(placement_rows)
        claim_rows = repo.scientific_trace_conclusion_claim_inputs(manuscript)
        claims = self._conclusion_claims(claim_rows, project)
        experiments = self._experiment_paths(
            repo.scientific_trace_claim_experiment_evidence(manuscript),
            project,
        )
        literature_rows = repo.scientific_trace_literature_evidence(manuscript, project)
        literature = self._literature_paths(literature_rows, project)
        self._verify_conclusion_hashes(
            repo.scientific_trace_conclusions(manuscript), claim_rows, literature_rows
        )
        return ManuscriptScientificTrace(
            project,
            publication,
            manuscript,
            version["status"],
            version["content_hash"],
            placements,
            claims,
            experiments,
            literature,
        )
