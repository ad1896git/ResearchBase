"""Authenticated publication drafts and bounded internal lifecycle transitions."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, Literal, NoReturn, cast
from uuid import NAMESPACE_URL, UUID, uuid5

from researchbase.application.ports import UnitOfWork
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.errors import ErrorCode, ResearchBaseError

if TYPE_CHECKING:
    from researchbase.application.approval import ConsumptionReadback

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
    if not result.strip() or len(result) > 2000 or "\x00" in result:
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


def _entry_ids(value: Any, names: tuple[str, ...]) -> None:
    if any(type(getattr(value, name)) is not UUID for name in names):
        _fail(ErrorCode.VALIDATION_ERROR, "exact entry UUIDs required")


def _entry_hash(value: str) -> None:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        _fail(ErrorCode.VALIDATION_ERROR, "exact lowercase content hash required")


@dataclass(frozen=True, slots=True)
class TransitionPublicationInternalReviewCommand:
    id: UUID
    project_id: UUID
    publication_id: UUID
    manuscript_version_id: UUID
    expected_content_hash: str

    def __post_init__(self) -> None:
        _entry_ids(self, ("id", "project_id", "publication_id", "manuscript_version_id"))
        _entry_hash(self.expected_content_hash)


@dataclass(frozen=True, slots=True)
class GetPublicationInternalReviewEntryQuery:
    project_id: UUID
    id: UUID

    def __post_init__(self) -> None:
        _entry_ids(self, ("id", "project_id"))


@dataclass(frozen=True, slots=True)
class PublicationInternalReviewEntryReadback:
    id: UUID
    project_id: UUID
    publication_id: UUID
    manuscript_version_id: UUID
    manuscript_content_hash: str
    hash_scheme: Literal["sha256-cjson-v1"]
    prior_status: Literal["DRAFTING"]
    new_status: Literal["INTERNAL_REVIEW"]
    actor_id: UUID
    occurred_at: datetime

    def __post_init__(self) -> None:
        _entry_ids(
            self, ("id", "project_id", "publication_id", "manuscript_version_id", "actor_id")
        )
        _entry_hash(self.manuscript_content_hash)
        if (
            type(self.hash_scheme) is not str
            or self.hash_scheme != "sha256-cjson-v1"
            or type(self.prior_status) is not str
            or self.prior_status != "DRAFTING"
            or type(self.new_status) is not str
            or self.new_status != "INTERNAL_REVIEW"
            or type(self.occurred_at) is not datetime
            or self.occurred_at.tzinfo is None
            or self.occurred_at.utcoffset() != timedelta(0)
        ):
            _fail(ErrorCode.VALIDATION_ERROR, "literal entry facts and finite UTC time required")


@dataclass(frozen=True, slots=True)
class TransitionPublicationReadyCommand:
    command_key: UUID
    project_id: UUID
    grant_id: UUID
    result_id: UUID
    checked_review_ids: tuple[UUID, ...]

    def __post_init__(self) -> None:
        _entry_ids(self, ("command_key", "project_id", "grant_id", "result_id"))
        if (
            type(self.checked_review_ids) is not tuple
            or not 1 <= len(self.checked_review_ids) <= 100
            or any(type(x) is not UUID for x in self.checked_review_ids)
            or len(set(self.checked_review_ids)) != len(self.checked_review_ids)
        ):
            _fail(ErrorCode.VALIDATION_ERROR, "complete bounded readiness review set required")
        object.__setattr__(
            self, "checked_review_ids", tuple(sorted(self.checked_review_ids, key=str))
        )


@dataclass(frozen=True, slots=True)
class GetPublicationReadyTransitionQuery:
    project_id: UUID
    consumption_id: UUID

    def __post_init__(self) -> None:
        _entry_ids(self, ("project_id", "consumption_id"))


@dataclass(frozen=True, slots=True)
class ReadyTransitionDiagnostics:
    publication_status: str
    target_validity: Literal["VALID", "STALE", "INVALID"]
    blocking_issue_ids: tuple[UUID, ...]
    evaluated_at: datetime

    def __post_init__(self) -> None:
        if (
            type(self.publication_status) is not str
            or self.publication_status not in {"DRAFTING", "INTERNAL_REVIEW", "READY"}
            or type(self.target_validity) is not str
            or self.target_validity not in {"VALID", "STALE", "INVALID"}
            or type(self.blocking_issue_ids) is not tuple
            or any(type(i) is not UUID for i in self.blocking_issue_ids)
            or self.blocking_issue_ids != tuple(sorted(set(self.blocking_issue_ids), key=str))
            or type(self.evaluated_at) is not datetime
            or self.evaluated_at.tzinfo is None
            or self.evaluated_at.utcoffset() != timedelta(0)
        ):
            _fail(ErrorCode.VALIDATION_ERROR, "closed current readiness diagnostics required")


@dataclass(frozen=True, slots=True)
class ReadyTransitionReadback:
    consumption: ConsumptionReadback
    event_id: UUID
    publication_id: UUID
    basis_decision_id: UUID
    manuscript_version_id: UUID
    actor_id: UUID
    occurred_at: datetime
    prior_status: Literal["INTERNAL_REVIEW"]
    new_status: Literal["READY"]
    current: ReadyTransitionDiagnostics

    def __post_init__(self) -> None:
        from researchbase.application.approval import ConsumptionReadback

        _entry_ids(
            self,
            (
                "event_id",
                "publication_id",
                "basis_decision_id",
                "manuscript_version_id",
                "actor_id",
            ),
        )
        if (
            type(self.consumption) is not ConsumptionReadback
            or self.consumption.command != "TRANSITION_PUBLICATION_READY"
            or self.consumption.result_publication_id != self.publication_id
            or self.consumption.actor_id != self.actor_id
            or self.consumption.consumed_at != self.occurred_at
            or type(self.prior_status) is not str
            or self.prior_status != "INTERNAL_REVIEW"
            or type(self.new_status) is not str
            or self.new_status != "READY"
            or type(self.occurred_at) is not datetime
            or self.occurred_at.tzinfo is None
            or self.occurred_at.utcoffset() != timedelta(0)
            or type(self.current) is not ReadyTransitionDiagnostics
        ):
            _fail(ErrorCode.VALIDATION_ERROR, "closed saved readiness facts required")


class PublicationService:
    def __init__(self, factory: Callable[[], UnitOfWork], credentials: Any, store: Any) -> None:
        self._factory = factory
        self._credentials = credentials
        self._store = store

    def _authorize(
        self,
        uow: UnitOfWork,
        principal: VerifiedPrincipal,
        project: UUID,
        roles: frozenset[str],
    ):
        if not isinstance(principal, VerifiedPrincipal) or type(project) is not UUID:
            _fail(ErrorCode.AUTHENTICATION_REQUIRED, "verified project principal required")
        rows = uow.manuscript_freeze.authority(principal, project)
        at = uow.source_version.at()
        try:
            live = principal.verified_at <= at and self._credentials.is_valid(principal, at)
        except Exception:
            live = False
        if live and (roles == _READERS or uow.literature_search_plan.project_active(project)):
            for row in rows:
                if (
                    row["actor_type"] == "HUMAN"
                    and row["retired_at"] is None
                    and row["membership_status"] == "ACTIVE"
                    and row["binding_status"] == "ACTIVE"
                    and row["role"] in roles
                    and row["effective_from"] <= at
                    and (row["effective_until"] is None or at < row["effective_until"])
                    and row["bound_at"] <= at
                    and (row["revoked_at"] is None or at < row["revoked_at"])
                ):
                    return at
        _fail(ErrorCode.FORBIDDEN, "current publication authority unavailable")

    @staticmethod
    def _identity(
        principal: VerifiedPrincipal,
        project: UUID,
        request: UUID,
        command: str,
        parent: UUID | None = None,
    ) -> UUID:
        if not isinstance(principal, VerifiedPrincipal):
            _fail(ErrorCode.AUTHENTICATION_REQUIRED, "verified principal required")
        if type(project) is not UUID:
            _fail(ErrorCode.VALIDATION_ERROR, "exact project UUID required")
        if type(request) is not UUID:
            _fail(ErrorCode.VALIDATION_ERROR, "request UUID required")
        return uuid5(
            NAMESPACE_URL,
            f"pr212:{command}:{principal.deployment_id}:"
            f"{project}:{principal.actor_id}:{parent}:{request}",
        )

    def _document(self, repo: Any, identity: UUID, project: UUID) -> None:
        row = repo.document(identity, project)
        if (
            row is None
            or row["status"] != "FROZEN"
            or row["frozen_at"] is None
            or row["artifact_type"] != "manuscript"
            or row["byte_size"] is None
        ):
            _fail(
                ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                "same-project frozen manuscript document required",
            )
        digest = str(row["content_hash"])
        try:
            good = self._store.verify(digest)
            payload = self._store.open(digest) if good else None
        except (OSError, ValueError):
            good, payload = False, None
        if not good or payload is None or len(payload) != row["byte_size"]:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "manuscript document bytes unavailable")

    def create_publication(
        self,
        principal: VerifiedPrincipal,
        project: UUID,
        kind: str,
        title: str,
        request_id: UUID,
    ) -> PublicationReadback:
        if kind not in _TYPES:
            _fail(ErrorCode.VALIDATION_ERROR, "publication type invalid")
        title = _title(title)
        identity = self._identity(principal, project, request_id, "publication")
        with self._factory() as uow:
            uow.literature_search_plan.lock_project(project)
            at = self._authorize(uow, principal, project, _WRITERS)
            repo = uow.publication
            repo.lock_request(f"pr212:publication:{identity}")
            prior = repo.publication(identity, project)
            if prior is None:
                repo.insert_publication(
                    {
                        "id": identity,
                        "project_id": project,
                        "publication_type": kind,
                        "title": title,
                        "lifecycle_status": "DRAFTING",
                        "current_manuscript_version_id": None,
                        "created_by": principal.actor_id,
                        "created_at": at,
                        "row_version": 1,
                    }
                )
                repo.insert_initial_event(
                    {
                        "id": uuid5(NAMESPACE_URL, f"pr212:initial-event:{identity}"),
                        "publication_id": identity,
                        "actor_id": principal.actor_id,
                        "occurred_at": at,
                    }
                )
            elif prior["publication_type"] != kind or prior["title"] != title:
                _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "publication request replay differs")
            uow.commit()
        return PublicationReadback(identity, project, kind, title, "DRAFTING", None)

    def create_draft(
        self,
        principal: VerifiedPrincipal,
        project: UUID,
        publication_id: UUID,
        document_id: UUID,
        title: str,
        abstract: str | None,
        change_class: str,
        request_id: UUID,
    ) -> DraftReadback:
        if (
            type(publication_id) is not UUID
            or type(document_id) is not UUID
            or type(change_class) is not str
            or change_class not in _CHANGES
            or (abstract is not None and (not isinstance(abstract, str) or not abstract.strip()))
        ):
            _fail(ErrorCode.VALIDATION_ERROR, "typed draft material required")
        title = _title(title)
        if abstract is not None:
            abstract = unicodedata.normalize("NFC", abstract)
            try:
                abstract.encode("utf-8", "strict")
            except UnicodeError:
                _fail(ErrorCode.VALIDATION_ERROR, "invalid manuscript abstract Unicode")
            if len(abstract) > 100000 or "\x00" in abstract:
                _fail(ErrorCode.VALIDATION_ERROR, "bounded manuscript abstract required")
        identity = self._identity(principal, project, request_id, "draft", publication_id)
        with self._factory() as uow:
            uow.configure_revision_transaction(readonly=True)
            uow.enable_revision_action_snapshot_reads()
            self._authorize(uow, principal, project, _READERS)
            parent = uow.publication.publication(publication_id, project)
            saved = uow.publication.version(identity, publication_id) if parent else None
            if saved is not None:
                if any(
                    saved[k] != v
                    for k, v in {
                        "document_artifact_version_id": document_id,
                        "title": title,
                        "abstract": abstract,
                        "semantic_change_class": change_class,
                        "created_by": principal.actor_id,
                    }.items()
                ):
                    _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "draft request replay differs")
                if saved["status"] == "FROZEN":
                    self._entry_policy()._manuscripts.verify_saved_seal_in_uow(
                        uow, project, parent, saved
                    )
                else:
                    if saved["status"] != "DRAFT" or any(
                        saved[k] is not None
                        for k in ("frozen_at", "placement_set_hash", "content_hash")
                    ):
                        _fail(
                            ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "draft replay material invalid"
                        )
                    self._document(uow.publication, document_id, project)
                self._authorize(uow, principal, project, _READERS)
                return DraftReadback(
                    identity,
                    publication_id,
                    saved["version_number"],
                    saved["status"],
                    document_id,
                    title,
                    abstract,
                    change_class,
                    saved["placement_set_hash"],
                    saved["content_hash"],
                )
        with self._factory() as uow:
            uow.enable_manuscript_freeze_error_normalization()
            uow.configure_revision_transaction()
            # INITIAL remains the PR2-12 command, including at revision 0035.
            # Only successor creation needs the M1 editing inventory (§12.2).
            if change_class != "INITIAL":
                uow.manuscript_freeze.prepare_revision_write()
            else:
                uow.literature_search_plan.lock_project(project)
            repo = uow.publication
            repo.lock_request(f"pr212:draft:{identity}")
            repo.lock_project(project)
            parent = repo.publication(publication_id, project, lock=True)
            self._authorize(uow, principal, project, _READERS)
            if parent is None:
                _fail(ErrorCode.NOT_FOUND, "draft parent unavailable")
            prior = repo.version(identity, publication_id)
            if prior is not None:
                if any(
                    prior[k] != v
                    for k, v in {
                        "document_artifact_version_id": document_id,
                        "title": title,
                        "abstract": abstract,
                        "semantic_change_class": change_class,
                        "created_by": principal.actor_id,
                    }.items()
                ):
                    _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "draft request replay differs")
                if prior["status"] == "FROZEN":
                    self._entry_policy()._manuscripts.verify_saved_seal_in_uow(
                        uow, project, parent, prior
                    )
                else:
                    self._document(repo, document_id, project)
                result = DraftReadback(
                    identity,
                    publication_id,
                    prior["version_number"],
                    prior["status"],
                    document_id,
                    title,
                    abstract,
                    change_class,
                    prior["placement_set_hash"],
                    prior["content_hash"],
                )
            else:
                if parent["lifecycle_status"] not in {"DRAFTING", "INTERNAL_REVIEW"}:
                    _fail(ErrorCode.INVALID_STATE_TRANSITION, "publication stage ineligible")
                predecessor = parent["current_manuscript_version_id"]
                old = repo.version(predecessor, publication_id, share=True) if predecessor else None
                number = repo.next_version(publication_id)
                if repo.has_draft(publication_id):
                    _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "publication already has a draft")
                if number > 2147483647 or (number == 1) != (change_class == "INITIAL"):
                    _fail(
                        ErrorCode.INVALID_STATE_TRANSITION,
                        "manuscript version/change class mismatch",
                    )
                if number > 1 and (
                    old is None or old["status"] != "FROZEN" or old["version_number"] != number - 1
                ):
                    _fail(
                        ErrorCode.INVALID_STATE_TRANSITION, "contiguous frozen predecessor required"
                    )
                self._document(repo, document_id, project)
                at = self._authorize(uow, principal, project, _WRITERS)
                repo.insert_version(
                    dict(
                        id=identity,
                        publication_id=publication_id,
                        version_number=number,
                        status="DRAFT",
                        document_artifact_version_id=document_id,
                        title=title,
                        abstract=abstract,
                        semantic_change_class=change_class,
                        placement_set_hash=None,
                        content_hash=None,
                        hash_scheme="sha256-cjson-v1",
                        created_by=principal.actor_id,
                        created_at=at,
                        frozen_at=None,
                        row_version=1,
                    )
                )
                uow.manuscript_freeze.force_constraints()
                result = DraftReadback(
                    identity,
                    publication_id,
                    number,
                    "DRAFT",
                    document_id,
                    title,
                    abstract,
                    change_class,
                    None,
                    None,
                )
            self._authorize(uow, principal, project, _READERS)
            uow.commit()
        return result

    def read_draft(
        self,
        principal: VerifiedPrincipal,
        project: UUID,
        publication_id: UUID,
        version_id: UUID,
    ) -> DraftReadback:
        with self._factory() as uow:
            uow.configure_revision_transaction(readonly=True)
            uow.enable_revision_action_snapshot_reads()
            self._authorize(uow, principal, project, _READERS)
            repo = uow.publication
            parent = repo.publication(publication_id, project)
            row = repo.version(version_id, publication_id) if parent else None
            if row is None:
                _fail(ErrorCode.NOT_FOUND, "manuscript draft not found")
            self._document(repo, row["document_artifact_version_id"], project)
            if (
                row["status"] != "DRAFT"
                or row["placement_set_hash"] is not None
                or row["content_hash"] is not None
                or row["frozen_at"] is not None
            ):
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "draft cannot claim frozen material")
            return DraftReadback(
                row["id"],
                publication_id,
                row["version_number"],
                row["status"],
                row["document_artifact_version_id"],
                row["title"],
                row["abstract"],
                row["semantic_change_class"],
                row["placement_set_hash"],
                row["content_hash"],
            )

    def _entry_policy(self):
        from researchbase.application.decision import DecisionService
        from researchbase.application.literature_evidence import LiteratureEvidenceService

        return DecisionService(
            self._factory,
            self._credentials,
            LiteratureEvidenceService(self._factory, self._credentials, self._store),
            self._store,
        )

    @staticmethod
    def _entry_principal(principal) -> None:
        if not isinstance(principal, VerifiedPrincipal):
            _fail(ErrorCode.AUTHENTICATION_REQUIRED, "trusted verified principal required")

    def _entry_readback(self, uow, policy, row):
        from researchbase.application.saved_provenance import saved_seal

        with saved_seal():
            parent = uow.publication.publication(row["publication_id"], row["project_id"])
            target = uow.publication.version(row["manuscript_version_id"], row["publication_id"])
            initial = uow.publication.initial_events(row["publication_id"])
            entries = uow.publication.entry_events(row["publication_id"])
            if (
                parent is None
                or parent["lifecycle_status"] not in {"INTERNAL_REVIEW", "READY"}
                or parent["row_version"] < 3
                or not uow.publication.entry_creation_authorized(row)
                or target is None
                or len(initial) != 1
                or len(entries) != 1
                or entries[0]["id"] != row["id"]
                or target["status"] != "FROZEN"
                or target["frozen_at"] is None
                or row["prior_status"] != "DRAFTING"
                or row["new_status"] != "INTERNAL_REVIEW"
                or row["basis_decision_id"] is not None
                or row["basis_grant_consumption_id"] is not None
            ):
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved entry graph invalid")
            root = initial[0]
            if (
                root["new_status"] != "DRAFTING"
                or root["actor_id"] != parent["created_by"]
                or root["occurred_at"] != parent["created_at"]
                or root["manuscript_version_id"] is not None
                or root["basis_decision_id"] is not None
                or root["basis_grant_consumption_id"] is not None
                or row["occurred_at"] < root["occurred_at"]
                or row["occurred_at"] < target["frozen_at"]
                or row["occurred_at"] > uow.manuscript_freeze.at()
            ):
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved entry chronology invalid")
            policy._manuscripts.verify_saved_seal_in_uow(uow, row["project_id"], parent, target)
            try:
                return PublicationInternalReviewEntryReadback(
                    row["id"],
                    row["project_id"],
                    row["publication_id"],
                    target["id"],
                    target["content_hash"],
                    target["hash_scheme"],
                    row["prior_status"],
                    row["new_status"],
                    row["actor_id"],
                    row["occurred_at"].astimezone(UTC),
                )
            except ResearchBaseError:
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved entry facts invalid")

    def _read_entry(self, principal, query, command=None):
        policy = self._entry_policy()
        with self._factory() as uow:
            uow.enable_publication_entry_error_normalization()
            uow.configure_revision_transaction(readonly=True)
            uow.enable_revision_action_snapshot_reads()
            policy._readiness_authorize(uow, principal, query.project_id, _READERS)
            row = uow.publication.entry_event(query.id)
            if row is None:
                policy._readiness_authorize(uow, principal, query.project_id, _READERS)
                return None
            if row["project_id"] != query.project_id or (
                command is not None and row["actor_id"] != principal.actor_id
            ):
                _fail(ErrorCode.FORBIDDEN, "entry unavailable in caller scope")
            result = self._entry_readback(uow, policy, row)
            if command is not None and (
                result.publication_id != command.publication_id
                or result.manuscript_version_id != command.manuscript_version_id
                or result.manuscript_content_hash != command.expected_content_hash
            ):
                _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "entry command material differs")
            policy._readiness_authorize(uow, principal, query.project_id, _READERS)
            return result

    def get_publication_internal_review_entry(
        self, principal, query: GetPublicationInternalReviewEntryQuery
    ) -> PublicationInternalReviewEntryReadback:
        if type(query) is not GetPublicationInternalReviewEntryQuery:
            _fail(ErrorCode.VALIDATION_ERROR, "closed entry query required")
        query.__post_init__()
        self._entry_principal(principal)
        result = self._read_entry(principal, query)
        if result is None:
            _fail(ErrorCode.NOT_FOUND, "exact entry event not found")
        return result

    def transition_publication_internal_review(
        self, principal, command: TransitionPublicationInternalReviewCommand
    ) -> PublicationInternalReviewEntryReadback:
        if type(command) is not TransitionPublicationInternalReviewCommand:
            _fail(ErrorCode.VALIDATION_ERROR, "closed entry command required")
        command.__post_init__()
        self._entry_principal(principal)
        query = GetPublicationInternalReviewEntryQuery(command.project_id, command.id)
        prior = self._read_entry(principal, query, command)
        if prior is not None:
            return prior
        for attempt in range(3):
            try:
                result = self._enter_review_once(principal, command)
                if result is not None:
                    return result
                break
            except ResearchBaseError as exc:
                if (exc.details or {}).get("b14a_pk_collision"):
                    break
                if not (exc.details or {}).get("retryable_b14a") or attempt == 2:
                    raise
        result = self._read_entry(principal, query, command)
        if result is None:
            _fail(ErrorCode.CONCURRENT_MODIFICATION, "entry outcome unresolved; replay same id")
        return result

    def _enter_review_once(self, principal, command):
        policy = self._entry_policy()
        with self._factory() as uow:
            uow.enable_publication_entry_error_normalization()
            uow.configure_revision_transaction()
            repo = uow.publication
            repo.prepare_entry_write()
            repo.lock_request(f"b14a:entry:{command.id}")
            repo.lock_entry_target(command.manuscript_version_id)
            parent = repo.publication(command.publication_id, command.project_id, lock=True)
            uow.enable_revision_action_snapshot_reads()
            policy._readiness_authorize(uow, principal, command.project_id, _READERS)
            if repo.entry_event(command.id) is not None:
                # Exit/rollback the writer; comparison belongs to a fresh lock-free read.
                return None
            policy._readiness_authorize(uow, principal, command.project_id, _WRITERS)
            if parent is None:
                _fail(
                    ErrorCode.FORBIDDEN
                    if repo.publication_exists(command.publication_id)
                    else ErrorCode.NOT_FOUND,
                    "exact publication unavailable",
                )
            target = repo.version(command.manuscript_version_id, parent["id"])
            if target is None:
                _fail(
                    ErrorCode.FORBIDDEN
                    if uow.decision.manuscript_exists(command.manuscript_version_id)
                    else ErrorCode.NOT_FOUND,
                    "exact same-parent manuscript unavailable",
                )
            if parent["lifecycle_status"] != "DRAFTING":
                _fail(ErrorCode.INVALID_STATE_TRANSITION, "publication already entered review")
            if (
                target["status"] != "FROZEN"
                or any(
                    target[k] is None for k in ("content_hash", "placement_set_hash", "frozen_at")
                )
                or target["hash_scheme"] != "sha256-cjson-v1"
            ):
                _fail(ErrorCode.FROZEN_REFERENCE_REQUIRED, "exact frozen manuscript required")
            if target["content_hash"] != command.expected_content_hash:
                _fail(ErrorCode.CONCURRENT_MODIFICATION, "expected manuscript hash differs")
            policy._manuscripts.verify_in_uow(
                uow, command.project_id, parent, target, admission=True
            )
            for review in uow.decision.applicable_manuscript_reviews(
                target["id"], command.project_id
            ):
                policy._reviews.verify_entry_review_in_uow(uow, review)
                if not uow.decision.review_creation_authorized(review):
                    _fail(
                        ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                        "invalid historical review attribution",
                    )
            if policy._readiness_blockers(uow, command.project_id, target["id"]):
                _fail(ErrorCode.APPROVAL_GATE_FAILED, "applicable open blocking Issue")
            at = policy._readiness_authorize(uow, principal, command.project_id, _WRITERS)
            if parent["row_version"] >= 2147483647:
                _fail(ErrorCode.CONCURRENT_MODIFICATION, "publication version exhausted")
            if not repo.transition_entry(
                parent,
                dict(
                    id=command.id,
                    publication_id=parent["id"],
                    manuscript_version_id=target["id"],
                    actor_id=principal.actor_id,
                    occurred_at=at,
                ),
            ):
                _fail(ErrorCode.CONCURRENT_MODIFICATION, "publication update lost")
            repo.force_entry_constraints()
            result = self._entry_readback(uow, policy, repo.entry_event(command.id))
            policy._readiness_authorize(uow, principal, command.project_id, _WRITERS)
            uow.commit()
            return result

    def _ready_approval(self):
        from researchbase.application.approval import ApprovalService
        from researchbase.application.literature_evidence import LiteratureEvidenceService

        return ApprovalService(
            self._factory,
            self._credentials,
            LiteratureEvidenceService(self._factory, self._credentials, self._store),
        )

    def _ready_readback(self, uow, app, receipt):
        event = uow.publication.ready_event(receipt.id)
        grant, decision, request = app._grant_chain(uow, receipt.project_id, receipt.grant_id)
        parent = uow.publication.publication(receipt.result_publication_id, receipt.project_id)
        if (
            event is None
            or parent is None
            or receipt.command != "TRANSITION_PUBLICATION_READY"
            or event["publication_id"] != receipt.result_publication_id
            or event["basis_decision_id"] != request["basis_decision_id"]
            or event["actor_id"] != receipt.actor_id
            or event["occurred_at"] != receipt.consumed_at
            or event["prior_status"] != "INTERNAL_REVIEW"
            or event["new_status"] != "READY"
        ):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "complete READY history required")
        target = uow.publication.version(request["manuscript_version_id"], parent["id"])
        checked = app._decisions._manuscripts.verify_saved_seal_in_uow(
            uow, receipt.project_id, parent, target
        )
        blockers = app._decisions._readiness_blockers(uow, receipt.project_id, target["id"])
        return ReadyTransitionReadback(
            receipt,
            event["id"],
            parent["id"],
            request["basis_decision_id"],
            target["id"],
            receipt.actor_id,
            receipt.consumed_at.astimezone(UTC),
            "INTERNAL_REVIEW",
            "READY",
            ReadyTransitionDiagnostics(
                parent["lifecycle_status"],
                checked.current_validity,
                tuple(sorted(blockers, key=str)),
                uow.source_version.at().astimezone(UTC),
            ),
        )

    def _read_ready(self, principal, project, *, key=None, identity=None, command=None):
        app = self._ready_approval()
        with self._factory() as uow:
            app._prepare_read(uow, principal, project, strict=True)
            row = (
                uow.approval.consumption(key)
                if key is not None
                else uow.approval.consumption_by_id(cast(UUID, identity))
            )
            if row is None:
                app._authorize(uow, principal, project, _READERS)
                return None
            if row["project_id"] != project or (
                command is not None and row["actor_id"] != principal.actor_id
            ):
                _fail(ErrorCode.FORBIDDEN, "receipt unavailable in caller scope")
            receipt = app._receipt_view(uow, row)
            if command is not None and (
                receipt.grant_id != command.grant_id
                or receipt.result_publication_id != command.result_id
                or receipt.checked_review_ids != command.checked_review_ids
                or receipt.command != "TRANSITION_PUBLICATION_READY"
            ):
                _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "saved readiness material differs")
            if receipt.command != "TRANSITION_PUBLICATION_READY":
                _fail(ErrorCode.NOT_FOUND, "exact READY receipt absent")
            result = self._ready_readback(uow, app, receipt)
            app._authorize(uow, principal, project, _READERS)
            return result

    def get_publication_ready_transition(
        self, principal, query: GetPublicationReadyTransitionQuery
    ) -> ReadyTransitionReadback:
        if type(query) is not GetPublicationReadyTransitionQuery:
            _fail(ErrorCode.VALIDATION_ERROR, "closed readiness query required")
        query.__post_init__()
        self._entry_principal(principal)
        result = self._read_ready(principal, query.project_id, identity=query.consumption_id)
        if result is None:
            _fail(ErrorCode.NOT_FOUND, "exact READY receipt absent")
        return result

    def transition_publication_ready(
        self, principal, command: TransitionPublicationReadyCommand
    ) -> ConsumptionReadback:
        if type(command) is not TransitionPublicationReadyCommand:
            _fail(ErrorCode.VALIDATION_ERROR, "closed readiness command required")
        command.__post_init__()
        self._entry_principal(principal)
        app = self._ready_approval()
        for attempt in range(3):
            prior = self._read_ready(
                principal, command.project_id, key=command.command_key, command=command
            )
            if prior is not None:
                return prior.consumption
            try:
                with self._factory() as uow:
                    uow.enable_approval_error_normalization(strict=True)
                    uow.configure_grant_transaction(consuming=True)
                    uow.approval.prepare_write()
                    uow.approval.lock_lifecycle(command.command_key, consuming=True)
                    if uow.approval.consumption(command.command_key) is not None:
                        continue  # close writer before entitled historical readback
                    result = app._consume_ready_in_uow(uow, principal, command)
                    uow.commit()
                    return result
            except ResearchBaseError as exc:
                if (exc.details or {}).get("b13_key_race"):
                    break
                if not (exc.details or {}).get("retryable_b13") or attempt == 2:
                    raise
        prior = self._read_ready(
            principal, command.project_id, key=command.command_key, command=command
        )
        if prior is None:
            _fail(
                ErrorCode.CONCURRENT_MODIFICATION, "readiness outcome unresolved; replay same key"
            )
        return prior.consumption
