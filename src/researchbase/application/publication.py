"""Authenticated, draft-only PR2-12 Publication and ManuscriptVersion commands."""

from __future__ import annotations

import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, NoReturn
from uuid import NAMESPACE_URL, UUID, uuid5

from researchbase.application.ports import UnitOfWork
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.errors import ErrorCode, ResearchBaseError

_TYPES = frozenset({"PAPER", "PREPRINT", "REPORT", "THESIS", "TECHNICAL_REPORT", "OTHER"})
_CHANGES = frozenset({"INITIAL", "EDITORIAL", "SCIENTIFIC_MINOR", "SCIENTIFIC_MATERIAL"})
_WRITERS = frozenset({"OWNER", "RESEARCHER"})
_READERS = frozenset({"OWNER", "RESEARCHER", "REVIEWER", "VIEWER", "APPROVER"})


def _fail(code: ErrorCode, message: str) -> NoReturn:
    raise ResearchBaseError(code, message)


def _title(value: str) -> str:
    if not isinstance(value, str):
        _fail(ErrorCode.VALIDATION_ERROR, "publication title must be text")
    result = unicodedata.normalize("NFC", value)
    try:
        result.encode("utf-8", "strict")
    except UnicodeError:
        _fail(ErrorCode.VALIDATION_ERROR, "publication title contains invalid Unicode")
    if not result.strip() or len(result) > 2000:
        _fail(ErrorCode.VALIDATION_ERROR, "publication title must be nonblank and bounded")
    return result


@dataclass(frozen=True, slots=True)
class PublicationReadback:
    id: UUID
    project_id: UUID
    publication_type: str
    title: str
    lifecycle_status: str
    current_manuscript_version_id: UUID | None


@dataclass(frozen=True, slots=True)
class DraftReadback:
    id: UUID
    publication_id: UUID
    version_number: int
    status: str
    document_artifact_version_id: UUID
    title: str
    abstract: str | None
    semantic_change_class: str
    placement_set_hash: str | None
    content_hash: str | None


class PublicationService:
    def __init__(self, factory: Callable[[], UnitOfWork], credentials: Any, store: Any) -> None:
        self._factory = factory
        self._credentials = credentials
        self._store = store

    def _authorize(
        self, uow: UnitOfWork, principal: VerifiedPrincipal, project: UUID,
        roles: frozenset[str],
    ):
        if not isinstance(principal, VerifiedPrincipal) or type(project) is not UUID:
            _fail(ErrorCode.AUTHENTICATION_REQUIRED, "verified project principal required")
        uow.literature_search_plan.lock_project(project)
        rows = uow.literature_search_plan.authorize(principal, project)
        at = uow.source_version.at()
        try:
            live = principal.verified_at <= at and self._credentials.is_valid(principal, at)
        except Exception:
            live = False
        if live and (roles == _READERS or uow.literature_search_plan.project_active(project)):
            for row in rows:
                if (row["actor_type"] == "HUMAN" and row["retired_at"] is None
                    and row["membership_status"] == "ACTIVE"
                    and row["binding_status"] == "ACTIVE" and row["role"] in roles
                    and row["effective_from"] <= at
                    and (row["effective_until"] is None or at < row["effective_until"])
                    and row["bound_at"] <= at
                    and (row["revoked_at"] is None or at < row["revoked_at"])):
                    return at
        _fail(ErrorCode.FORBIDDEN, "current publication authority unavailable")

    @staticmethod
    def _identity(principal: VerifiedPrincipal, project: UUID, request: UUID,
                  command: str, parent: UUID | None = None) -> UUID:
        if type(request) is not UUID:
            _fail(ErrorCode.VALIDATION_ERROR, "request UUID required")
        return uuid5(NAMESPACE_URL, f"pr212:{command}:{principal.deployment_id}:"
                     f"{project}:{principal.actor_id}:{parent}:{request}")

    def _document(self, repo: Any, identity: UUID, project: UUID) -> None:
        row = repo.document(identity, project)
        if (row is None or row["status"] != "FROZEN" or row["frozen_at"] is None
            or row["artifact_type"] != "manuscript" or row["byte_size"] is None):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                  "same-project frozen manuscript document required")
        digest = str(row["content_hash"])
        try:
            good = self._store.verify(digest)
            payload = self._store.open(digest) if good else None
        except (OSError, ValueError):
            good, payload = False, None
        if not good or payload is None or len(payload) != row["byte_size"]:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                  "manuscript document bytes unavailable")

    def create_publication(
        self, principal: VerifiedPrincipal, project: UUID, kind: str, title: str,
        request_id: UUID,
    ) -> PublicationReadback:
        if kind not in _TYPES:
            _fail(ErrorCode.VALIDATION_ERROR, "publication type invalid")
        title = _title(title)
        identity = self._identity(principal, project, request_id, "publication")
        with self._factory() as uow:
            uow.begin_serializable()
            at = self._authorize(uow, principal, project, _WRITERS)
            repo = uow.publication
            repo.lock_request(f"pr212:publication:{identity}")
            prior = repo.publication(identity, project)
            if prior is None:
                repo.insert_publication({
                    "id": identity, "project_id": project, "publication_type": kind,
                    "title": title, "lifecycle_status": "DRAFTING",
                    "current_manuscript_version_id": None,
                    "created_by": principal.actor_id, "created_at": at, "row_version": 1,
                })
                repo.insert_initial_event({
                    "id": uuid5(NAMESPACE_URL, f"pr212:initial-event:{identity}"),
                    "publication_id": identity, "actor_id": principal.actor_id,
                    "occurred_at": at,
                })
            elif prior["publication_type"] != kind or prior["title"] != title:
                _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "publication request replay differs")
            uow.commit()
        return PublicationReadback(identity, project, kind, title, "DRAFTING", None)

    def create_draft(
        self, principal: VerifiedPrincipal, project: UUID, publication_id: UUID,
        document_id: UUID, title: str, abstract: str | None,
        change_class: str, request_id: UUID,
    ) -> DraftReadback:
        if (type(publication_id) is not UUID or type(document_id) is not UUID
            or change_class not in _CHANGES or (abstract is not None
            and (not isinstance(abstract, str) or not abstract.strip()))):
            _fail(ErrorCode.VALIDATION_ERROR, "typed draft material required")
        title = _title(title)
        if abstract is not None:
            abstract = unicodedata.normalize("NFC", abstract)
        identity = self._identity(principal, project, request_id, "draft", publication_id)
        with self._factory() as uow:
            uow.begin_serializable()
            at = self._authorize(uow, principal, project, _WRITERS)
            repo = uow.publication
            repo.lock_request(f"pr212:draft:{identity}")
            parent = repo.publication(publication_id, project, lock=True)
            if parent is None or parent["lifecycle_status"] != "DRAFTING":
                _fail(ErrorCode.INVALID_STATE_TRANSITION, "draft parent unavailable")
            prior = repo.version(identity, publication_id)
            if prior is None:
                self._document(repo, document_id, project)
                # This slice permits one initial draft; revision needs a later command.
                if parent["current_manuscript_version_id"] is not None:
                    _fail(ErrorCode.INVALID_STATE_TRANSITION, "published version cannot draft here")
                if repo.initial_version(publication_id) is not None:
                    _fail(ErrorCode.INVALID_STATE_TRANSITION,
                          "initial manuscript draft already exists")
                repo.insert_version({
                    "id": identity, "publication_id": publication_id,
                    "version_number": 1, "status": "DRAFT",
                    "document_artifact_version_id": document_id,
                    "title": title, "abstract": abstract,
                    "semantic_change_class": change_class,
                    "placement_set_hash": None, "content_hash": None,
                    "created_by": principal.actor_id, "created_at": at,
                    "frozen_at": None, "row_version": 1,
                })
            elif (prior["document_artifact_version_id"] != document_id
                  or prior["title"] != title or prior["abstract"] != abstract
                  or prior["semantic_change_class"] != change_class):
                _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "draft request replay differs")
            uow.commit()
        return self.read_draft(principal, project, publication_id, identity)

    def read_draft(
        self, principal: VerifiedPrincipal, project: UUID,
        publication_id: UUID, version_id: UUID,
    ) -> DraftReadback:
        with self._factory() as uow:
            self._authorize(uow, principal, project, _READERS)
            repo = uow.publication
            parent = repo.publication(publication_id, project)
            row = repo.version(version_id, publication_id) if parent else None
            if row is None:
                _fail(ErrorCode.NOT_FOUND, "manuscript draft not found")
            self._document(repo, row["document_artifact_version_id"], project)
            if (row["status"] != "DRAFT" or row["placement_set_hash"] is not None
                or row["content_hash"] is not None or row["frozen_at"] is not None):
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                      "draft cannot claim frozen material")
            return DraftReadback(row["id"], publication_id, row["version_number"],
                                 row["status"], row["document_artifact_version_id"],
                                 row["title"], row["abstract"], row["semantic_change_class"],
                                 row["placement_set_hash"], row["content_hash"])
