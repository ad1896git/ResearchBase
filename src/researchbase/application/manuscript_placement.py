"""Authenticated draft citation placements and citation-only trace readback."""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from researchbase.application.manuscript_freeze import ManuscriptFreezeService
from researchbase.application.ports import UnitOfWork
from researchbase.application.publication import _READERS, _WRITERS, PublicationService
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.errors import ErrorCode, ResearchBaseError

_PURPOSES = frozenset(
    {"BACKGROUND", "METHOD", "COMPARISON", "EVIDENCE", "PRIOR_ART", "DATASET", "OTHER"}
)
_KINDS = frozenset({"PARAGRAPH", "SPAN", "CAPTION", "ANCHOR"})
_MAX_PLACEMENT_TEXT = 2000


@dataclass(frozen=True, slots=True)
class CitationTrace:
    id: UUID
    manuscript_version_id: UUID
    source_version_id: UUID
    section_id: str
    locator: dict[str, str]
    citation_purpose: str
    ordinal: int
    source_content_hash: str
    path_kind: str = "CITATION_ONLY"


def _text(value: object) -> str:
    if not isinstance(value, str):
        raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, "nonblank text required")
    try:
        normalized = unicodedata.normalize("NFC", value)
        normalized.encode("utf-8", "strict")
    except UnicodeError as exc:
        raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, "invalid Unicode") from exc
    if not normalized.strip() or len(normalized) > _MAX_PLACEMENT_TEXT:
        raise ResearchBaseError(
            ErrorCode.VALIDATION_ERROR,
            "placement text must be nonblank and at most 2000 characters",
        )
    return normalized


class CitationPlacementService:
    def __init__(
        self, factory: Callable[[], UnitOfWork], credentials: Any, store: Any = None
    ) -> None:
        self._factory = factory
        self._auth = PublicationService(factory, credentials, None)
        self._freeze = ManuscriptFreezeService(factory, credentials, store)

    @staticmethod
    def _source(repo: Any, source: UUID, project: UUID) -> str:
        row = repo.citation_source(source, project)
        if (
            row is None
            or row["status"] not in ("FROZEN", "SUPERSEDED")
            or row["frozen_at"] is None
            or not isinstance(row["content_hash"], str)
            or re.fullmatch(r"[0-9a-f]{64}", row["content_hash"]) is None
        ):
            raise ResearchBaseError(
                ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "exact frozen project source required"
            )
        return row["content_hash"]

    @staticmethod
    def _result(row: dict[str, Any], source_hash: str) -> CitationTrace:
        return CitationTrace(
            row["id"],
            row["manuscript_version_id"],
            row["source_version_id"],
            row["section_id"],
            dict(row["locator"]),
            row["citation_purpose"],
            row["ordinal"],
            source_hash,
        )

    def add(
        self,
        principal: VerifiedPrincipal,
        project: UUID,
        publication: UUID,
        manuscript: UUID,
        source: UUID,
        section: str,
        locator: dict[str, str],
        purpose: str,
        ordinal: int,
        request_id: UUID,
    ) -> CitationTrace:
        """Add a citation; section and locator value are each limited to 2000 characters."""
        if (
            type(publication) is not UUID
            or type(manuscript) is not UUID
            or type(source) is not UUID
            or type(request_id) is not UUID
            or type(ordinal) is not int
            or ordinal < 0
            or purpose not in _PURPOSES
            or not isinstance(locator, dict)
            or set(locator) != {"kind", "value"}
            or locator.get("kind") not in _KINDS
        ):
            raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, "typed citation required")
        section = _text(section)
        location = {"kind": locator["kind"], "value": _text(locator["value"])}
        with self._factory() as uow:
            at = self._auth._authorize(uow, principal, project, _WRITERS)
            repo = uow.publication
            parent = repo.publication(publication, project, lock=True)
            version = repo.version(manuscript, publication) if parent else None
            if (
                parent is None
                or version is None
                or version["status"] != "DRAFT"
                or version["frozen_at"] is not None
            ):
                raise ResearchBaseError(
                    ErrorCode.INVALID_STATE_TRANSITION, "draft manuscript unavailable"
                )
            source_hash = self._source(repo, source, project)
            identity = uuid5(
                NAMESPACE_URL,
                f"pr213:citation:{principal.deployment_id}:"
                f"{project}:{principal.actor_id}:{manuscript}:{request_id}",
            )
            repo.lock_request(f"pr213:citation:{identity}")
            prior = repo.citation(identity, manuscript)
            if prior is None:
                row: dict[str, Any] = {
                    "id": identity,
                    "manuscript_version_id": manuscript,
                    "source_version_id": source,
                    "section_id": section,
                    "locator": location,
                    "citation_purpose": purpose,
                    "ordinal": ordinal,
                    "created_by": principal.actor_id,
                    "created_at": at,
                    "row_version": 1,
                }
                repo.insert_citation({**row, "locator": json.dumps(location, sort_keys=True)})
            else:
                row = prior
                if (
                    prior["source_version_id"] != source
                    or prior["section_id"] != section
                    or prior["locator"] != location
                    or prior["citation_purpose"] != purpose
                    or prior["ordinal"] != ordinal
                ):
                    raise ResearchBaseError(
                        ErrorCode.IDEMPOTENCY_CONFLICT, "citation request replay differs"
                    )
            uow.commit()
        return self._result(row, source_hash)

    def trace(
        self,
        principal: VerifiedPrincipal,
        project: UUID,
        publication: UUID,
        manuscript: UUID,
    ) -> tuple[CitationTrace, ...]:
        self._freeze._principal(principal)
        with self._factory() as uow:
            uow.enable_manuscript_freeze_error_normalization()
            uow.manuscript_freeze.prepare_read()
            uow.enable_revision_action_snapshot_reads()
            self._freeze.authorize(uow, principal, project, _READERS)
            repo = uow.publication
            parent = repo.publication(publication, project)
            version = repo.version(manuscript, publication) if parent else None
            if version is None:
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "manuscript version not found")
            if version["status"] == "FROZEN":
                self._freeze.verify_in_uow(uow, project, parent, version)
            elif version["status"] != "DRAFT" or version["frozen_at"] is not None:
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "draft manuscript not found")
            rows = repo.citations(manuscript)
            result = tuple(
                self._result(row, self._source(repo, row["source_version_id"], project))
                for row in rows
            )
            self._freeze.authorize(uow, principal, project, _READERS)
            return result


_STRENGTHS = frozenset({"DESCRIPTIVE", "SUGGESTIVE", "SUPPORTED", "STRONG"})


@dataclass(frozen=True, slots=True)
class ClaimPlacementTrace:
    id: UUID
    manuscript_version_id: UUID
    claim_version_id: UUID | None
    scientific_conclusion_version_id: UUID | None
    section_id: str
    locator: dict[str, str]
    rhetorical_strength: str
    ordinal: int
    target_kind: str
    target_content_hash: str
    path_kind: str = "PLACEMENT_ONLY"


class ClaimPlacementService:
    """Draft presentation links; no support, review or promotion is created."""

    def __init__(
        self, factory: Callable[[], UnitOfWork], credentials: Any, store: Any = None
    ) -> None:
        self._factory = factory
        self._auth = PublicationService(factory, credentials, None)
        self._freeze = ManuscriptFreezeService(factory, credentials, store)

    @staticmethod
    def _target(repo: Any, target: UUID, project: UUID, *, conclusion: bool) -> str:
        row = repo.claim_placement_target(target, project, conclusion=conclusion)
        if (
            row is None
            or row["status"] not in ("FROZEN", "SUPERSEDED")
            or row["frozen_at"] is None
            or not isinstance(row["content_hash"], str)
            or re.fullmatch(r"[0-9a-f]{64}", row["content_hash"]) is None
            or (
                conclusion
                and (
                    not isinstance(row["support_set_hash"], str)
                    or re.fullmatch(r"[0-9a-f]{64}", row["support_set_hash"]) is None
                )
            )
        ):
            raise ResearchBaseError(
                ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                "exact frozen project claim or conclusion required",
            )
        return row["content_hash"]

    @staticmethod
    def _result(row: dict[str, Any], target_hash: str) -> ClaimPlacementTrace:
        conclusion = row["scientific_conclusion_version_id"] is not None
        return ClaimPlacementTrace(
            row["id"],
            row["manuscript_version_id"],
            row["claim_version_id"],
            row["scientific_conclusion_version_id"],
            row["section_id"],
            dict(row["locator"]),
            row["rhetorical_strength"],
            row["ordinal"],
            "SCIENTIFIC_CONCLUSION_VERSION" if conclusion else "CLAIM_VERSION",
            target_hash,
        )

    def add(
        self,
        principal: VerifiedPrincipal,
        project: UUID,
        publication: UUID,
        manuscript: UUID,
        claim: UUID | None,
        conclusion: UUID | None,
        section: str,
        locator: dict[str, str],
        strength: str,
        ordinal: int,
        request_id: UUID,
    ) -> ClaimPlacementTrace:
        """Add one exact frozen target to a draft; text values max 2000 characters."""
        if (
            type(publication) is not UUID
            or type(manuscript) is not UUID
            or (type(claim) is UUID) == (type(conclusion) is UUID)
            or (claim is not None and type(claim) is not UUID)
            or (conclusion is not None and type(conclusion) is not UUID)
            or type(request_id) is not UUID
            or type(ordinal) is not int
            or ordinal < 0
            or strength not in _STRENGTHS
            or not isinstance(locator, dict)
            or set(locator) != {"kind", "value"}
            or locator.get("kind") not in _KINDS
        ):
            raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, "typed exact placement required")
        section = _text(section)
        location = {"kind": locator["kind"], "value": _text(locator["value"])}
        target = conclusion if conclusion is not None else claim
        assert target is not None
        with self._factory() as uow:
            at = self._auth._authorize(uow, principal, project, _WRITERS)
            repo = uow.publication
            parent = repo.publication(publication, project, lock=True)
            version = repo.version(manuscript, publication) if parent else None
            if (
                parent is None
                or version is None
                or version["status"] != "DRAFT"
                or version["frozen_at"] is not None
            ):
                raise ResearchBaseError(
                    ErrorCode.INVALID_STATE_TRANSITION, "draft manuscript unavailable"
                )
            target_hash = self._target(repo, target, project, conclusion=conclusion is not None)
            identity = uuid5(
                NAMESPACE_URL,
                f"pr213:claim-placement:{principal.deployment_id}:"
                f"{project}:{principal.actor_id}:{manuscript}:{request_id}",
            )
            repo.lock_request(f"pr213:claim-placement:{identity}")
            prior = repo.claim_placement(identity, manuscript)
            if prior is None:
                row: dict[str, Any] = {
                    "id": identity,
                    "manuscript_version_id": manuscript,
                    "claim_version_id": claim,
                    "scientific_conclusion_version_id": conclusion,
                    "section_id": section,
                    "locator": location,
                    "rhetorical_strength": strength,
                    "ordinal": ordinal,
                    "created_by": principal.actor_id,
                    "created_at": at,
                    "row_version": 1,
                }
                repo.insert_claim_placement(
                    {
                        **row,
                        "locator": json.dumps(location, sort_keys=True),
                    }
                )
            else:
                row = prior
                if (
                    prior["claim_version_id"] != claim
                    or prior["scientific_conclusion_version_id"] != conclusion
                    or prior["section_id"] != section
                    or prior["locator"] != location
                    or prior["rhetorical_strength"] != strength
                    or prior["ordinal"] != ordinal
                ):
                    raise ResearchBaseError(
                        ErrorCode.IDEMPOTENCY_CONFLICT, "claim placement request replay differs"
                    )
            uow.commit()
        return self._result(row, target_hash)

    def trace(
        self,
        principal: VerifiedPrincipal,
        project: UUID,
        publication: UUID,
        manuscript: UUID,
    ) -> tuple[ClaimPlacementTrace, ...]:
        self._freeze._principal(principal)
        with self._factory() as uow:
            uow.enable_manuscript_freeze_error_normalization()
            uow.manuscript_freeze.prepare_read()
            uow.enable_revision_action_snapshot_reads()
            self._freeze.authorize(uow, principal, project, _READERS)
            repo = uow.publication
            parent = repo.publication(publication, project)
            version = repo.version(manuscript, publication) if parent else None
            if version is None:
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "manuscript version not found")
            if version["status"] == "FROZEN":
                self._freeze.verify_in_uow(uow, project, parent, version)
            elif version["status"] != "DRAFT" or version["frozen_at"] is not None:
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "draft manuscript not found")
            rows = repo.claim_placements(manuscript)
            result = tuple(
                self._result(
                    row,
                    self._target(
                        repo,
                        row["scientific_conclusion_version_id"] or row["claim_version_id"],
                        project,
                        conclusion=row["scientific_conclusion_version_id"] is not None,
                    ),
                )
                for row in rows
            )
            self._freeze.authorize(uow, principal, project, _READERS)
            return result


_ARTIFACT_ROLES = frozenset({"FIGURE", "TABLE", "OTHER"})


@dataclass(frozen=True, slots=True)
class ArtifactPlacementTrace:
    id: UUID
    manuscript_version_id: UUID
    artifact_version_id: UUID
    section_id: str
    locator: dict[str, str]
    artifact_role: str
    ordinal: int
    artifact_content_hash: str
    path_kind: str = "PLACEMENT_ONLY"


class ArtifactPlacementService:
    """Exact frozen artifact presentation; no scientific promotion."""

    def __init__(
        self, factory: Callable[[], UnitOfWork], credentials: Any, store: Any = None
    ) -> None:
        self._factory = factory
        self._auth = PublicationService(factory, credentials, None)
        self._freeze = ManuscriptFreezeService(factory, credentials, store)

    @staticmethod
    def _target(repo: Any, artifact: UUID, project: UUID) -> str:
        row = repo.artifact_placement_target(artifact, project)
        if (
            row is None
            or row["status"] not in ("FROZEN", "SUPERSEDED")
            or row["frozen_at"] is None
            or not isinstance(row["content_hash"], str)
            or re.fullmatch(r"[0-9a-f]{64}", row["content_hash"]) is None
        ):
            raise ResearchBaseError(
                ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "exact frozen project artifact required"
            )
        return row["content_hash"]

    @staticmethod
    def _result(row: dict[str, Any], artifact_hash: str) -> ArtifactPlacementTrace:
        return ArtifactPlacementTrace(
            row["id"],
            row["manuscript_version_id"],
            row["artifact_version_id"],
            row["section_id"],
            dict(row["locator"]),
            row["artifact_role"],
            row["ordinal"],
            artifact_hash,
        )

    def add(
        self,
        principal: VerifiedPrincipal,
        project: UUID,
        publication: UUID,
        manuscript: UUID,
        artifact: UUID,
        section: str,
        locator: dict[str, str],
        role: str,
        ordinal: int,
        request_id: UUID,
    ) -> ArtifactPlacementTrace:
        if (
            type(publication) is not UUID
            or type(manuscript) is not UUID
            or type(artifact) is not UUID
            or type(request_id) is not UUID
            or type(ordinal) is not int
            or ordinal < 0
            or role not in _ARTIFACT_ROLES
            or not isinstance(locator, dict)
            or set(locator) != {"kind", "value"}
            or locator.get("kind") not in _KINDS
        ):
            raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, "typed artifact placement required")
        section = _text(section)
        location = {"kind": locator["kind"], "value": _text(locator["value"])}
        with self._factory() as uow:
            at = self._auth._authorize(uow, principal, project, _WRITERS)
            repo = uow.publication
            parent = repo.publication(publication, project, lock=True)
            version = repo.version(manuscript, publication) if parent else None
            if (
                parent is None
                or version is None
                or version["status"] != "DRAFT"
                or version["frozen_at"] is not None
            ):
                raise ResearchBaseError(
                    ErrorCode.INVALID_STATE_TRANSITION, "draft manuscript unavailable"
                )
            artifact_hash = self._target(repo, artifact, project)
            identity = uuid5(
                NAMESPACE_URL,
                f"pr213:artifact-placement:{principal.deployment_id}:"
                f"{project}:{principal.actor_id}:{manuscript}:{request_id}",
            )
            repo.lock_request(f"pr213:artifact-placement:{identity}")
            prior = repo.artifact_placement(identity, manuscript)
            if prior is None:
                row: dict[str, Any] = {
                    "id": identity,
                    "manuscript_version_id": manuscript,
                    "artifact_version_id": artifact,
                    "section_id": section,
                    "locator": location,
                    "artifact_role": role,
                    "ordinal": ordinal,
                    "created_by": principal.actor_id,
                    "created_at": at,
                    "row_version": 1,
                }
                repo.insert_artifact_placement(
                    {
                        **row,
                        "locator": json.dumps(location, sort_keys=True),
                    }
                )
            else:
                row = prior
                if (
                    prior["artifact_version_id"] != artifact
                    or prior["section_id"] != section
                    or prior["locator"] != location
                    or prior["artifact_role"] != role
                    or prior["ordinal"] != ordinal
                ):
                    raise ResearchBaseError(
                        ErrorCode.IDEMPOTENCY_CONFLICT, "artifact placement request replay differs"
                    )
            uow.commit()
        return self._result(row, artifact_hash)

    def trace(
        self,
        principal: VerifiedPrincipal,
        project: UUID,
        publication: UUID,
        manuscript: UUID,
    ) -> tuple[ArtifactPlacementTrace, ...]:
        self._freeze._principal(principal)
        with self._factory() as uow:
            uow.enable_manuscript_freeze_error_normalization()
            uow.manuscript_freeze.prepare_read()
            uow.enable_revision_action_snapshot_reads()
            self._freeze.authorize(uow, principal, project, _READERS)
            repo = uow.publication
            parent = repo.publication(publication, project)
            version = repo.version(manuscript, publication) if parent else None
            if version is None:
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "manuscript version not found")
            if version["status"] == "FROZEN":
                self._freeze.verify_in_uow(uow, project, parent, version)
            elif version["status"] != "DRAFT" or version["frozen_at"] is not None:
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "draft manuscript not found")
            rows = repo.artifact_placements(manuscript)
            result = tuple(
                self._result(row, self._target(repo, row["artifact_version_id"], project))
                for row in rows
            )
            self._freeze.authorize(uow, principal, project, _READERS)
            return result
