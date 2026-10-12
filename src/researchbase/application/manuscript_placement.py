"""Authenticated draft citation placements and citation-only trace readback."""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from researchbase.application.ports import UnitOfWork
from researchbase.application.publication import _READERS, _WRITERS, PublicationService
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.errors import ErrorCode, ResearchBaseError

_PURPOSES = frozenset({"BACKGROUND", "METHOD", "COMPARISON", "EVIDENCE",
                       "PRIOR_ART", "DATASET", "OTHER"})
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
        raise ResearchBaseError(ErrorCode.VALIDATION_ERROR,
                                "placement text must be nonblank and at most 2000 characters")
    return normalized


class CitationPlacementService:
    def __init__(self, factory: Callable[[], UnitOfWork], credentials: Any) -> None:
        self._factory = factory
        self._auth = PublicationService(factory, credentials, None)

    @staticmethod
    def _source(repo: Any, source: UUID, project: UUID) -> str:
        row = repo.citation_source(source, project)
        if (row is None or row["status"] not in ("FROZEN", "SUPERSEDED")
            or row["frozen_at"] is None or not isinstance(row["content_hash"], str)
            or re.fullmatch(r"[0-9a-f]{64}", row["content_hash"]) is None):
            raise ResearchBaseError(ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                                    "exact frozen project source required")
        return row["content_hash"]

    @staticmethod
    def _result(row: dict[str, Any], source_hash: str) -> CitationTrace:
        return CitationTrace(row["id"], row["manuscript_version_id"],
                             row["source_version_id"], row["section_id"],
                             dict(row["locator"]), row["citation_purpose"], row["ordinal"],
                             source_hash)

    def add(
        self, principal: VerifiedPrincipal, project: UUID, publication: UUID,
        manuscript: UUID, source: UUID, section: str, locator: dict[str, str],
        purpose: str, ordinal: int, request_id: UUID,
    ) -> CitationTrace:
        """Add a citation; section and locator value are each limited to 2000 characters."""
        if (type(publication) is not UUID or type(manuscript) is not UUID
            or type(source) is not UUID or type(request_id) is not UUID
            or type(ordinal) is not int or ordinal < 0 or purpose not in _PURPOSES
            or not isinstance(locator, dict) or set(locator) != {"kind", "value"}
            or locator.get("kind") not in _KINDS):
            raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, "typed citation required")
        section = _text(section)
        location = {"kind": locator["kind"], "value": _text(locator["value"])}
        with self._factory() as uow:
            at = self._auth._authorize(uow, principal, project, _WRITERS)
            repo = uow.publication
            parent = repo.publication(publication, project, lock=True)
            version = repo.version(manuscript, publication) if parent else None
            if (parent is None or version is None or version["status"] != "DRAFT"
                or version["frozen_at"] is not None):
                raise ResearchBaseError(ErrorCode.INVALID_STATE_TRANSITION,
                                        "draft manuscript unavailable")
            source_hash = self._source(repo, source, project)
            identity = uuid5(NAMESPACE_URL, f"pr213:citation:{principal.deployment_id}:"
                             f"{project}:{principal.actor_id}:{manuscript}:{request_id}")
            repo.lock_request(f"pr213:citation:{identity}")
            prior = repo.citation(identity, manuscript)
            if prior is None:
                row: dict[str, Any] = {
                    "id": identity, "manuscript_version_id": manuscript,
                    "source_version_id": source, "section_id": section,
                    "locator": location, "citation_purpose": purpose,
                    "ordinal": ordinal, "created_by": principal.actor_id,
                    "created_at": at, "row_version": 1,
                }
                repo.insert_citation({**row, "locator": json.dumps(location, sort_keys=True)})
            else:
                row = prior
                if (prior["source_version_id"] != source or prior["section_id"] != section
                    or prior["locator"] != location or prior["citation_purpose"] != purpose
                    or prior["ordinal"] != ordinal):
                    raise ResearchBaseError(ErrorCode.IDEMPOTENCY_CONFLICT,
                                            "citation request replay differs")
            uow.commit()
        return self._result(row, source_hash)

    def trace(
        self, principal: VerifiedPrincipal, project: UUID, publication: UUID,
        manuscript: UUID,
    ) -> tuple[CitationTrace, ...]:
        with self._factory() as uow:
            self._auth._authorize(uow, principal, project, _READERS)
            repo = uow.publication
            parent = repo.publication(publication, project)
            version = repo.version(manuscript, publication) if parent else None
            if (version is None or version["status"] != "DRAFT"
                or version["frozen_at"] is not None):
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "draft manuscript not found")
            rows = repo.citations(manuscript)
            return tuple(self._result(row, self._source(repo, row["source_version_id"],
                                                       project)) for row in rows)
