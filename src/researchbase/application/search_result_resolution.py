"""Authenticated exact search-result admission; retrieval never becomes evidence."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal, NoReturn
from uuid import UUID

from researchbase.application.literature_search_plan import _validate_question_row
from researchbase.application.ports import SearchResultResolutionUnitOfWork
from researchbase.application.source_identity import SourceCredentialVerifier
from researchbase.application.source_version import _material_from_row
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.domain.search_result_resolution import (
    normalize_basis,
    require_uuid,
    resolution_hash,
    result_doi,
    titles_match,
)
from researchbase.foundation.artifact_store import ArtifactStore
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import sha256_bytes

_READERS = {"OWNER", "RESEARCHER", "REVIEWER", "VIEWER", "APPROVER"}
_WRITERS = {"OWNER", "RESEARCHER"}


def _fail(code: ErrorCode, message: str) -> NoReturn:
    raise ResearchBaseError(code, message)


@dataclass(frozen=True, slots=True)
class RecordSearchResultResolutionCommand:
    id: UUID
    project_id: UUID
    search_result_record_id: UUID
    source_id: UUID
    source_version_id: UUID
    basis: str

    def __post_init__(self) -> None:
        for value in (
            self.id,
            self.project_id,
            self.search_result_record_id,
            self.source_id,
            self.source_version_id,
        ):
            require_uuid(value)
        object.__setattr__(self, "basis", normalize_basis(self.basis))


@dataclass(frozen=True, slots=True)
class ExactResolutionQuery:
    project_id: UUID
    id: UUID

    def __post_init__(self) -> None:
        require_uuid(self.project_id)
        require_uuid(self.id)


@dataclass(frozen=True, slots=True)
class SearchResultResolutionReadback:
    id: UUID
    project_id: UUID
    search_result_record_id: UUID
    source_id: UUID
    source_version_id: UUID | None
    resolved_by: UUID
    resolved_at: datetime
    basis: str
    content_hash: str
    hash_scheme: Literal["sha256-cjson-v1"]

    def __post_init__(self) -> None:
        for value in (
            self.id,
            self.project_id,
            self.search_result_record_id,
            self.source_id,
            self.resolved_by,
        ):
            require_uuid(value)
        if self.source_version_id is not None:
            require_uuid(self.source_version_id)
        if (
            not isinstance(self.resolved_at, datetime)
            or self.resolved_at.tzinfo is None
            or self.resolved_at.utcoffset() != UTC.utcoffset(self.resolved_at)
            or self.hash_scheme != "sha256-cjson-v1"
            or not isinstance(self.content_hash, str)
            or re.fullmatch("[0-9a-f]{64}", self.content_hash) is None
            or not isinstance(self.basis, str)
        ):
            _fail(ErrorCode.VALIDATION_ERROR, "invalid resolution readback")


def _same_material(
    saved: Mapping[str, object] | SearchResultResolutionReadback,
    command: RecordSearchResultResolutionCommand,
) -> bool:
    fields = ("search_result_record_id", "source_id", "source_version_id", "basis")
    return all(
        (saved[field] if isinstance(saved, Mapping) else getattr(saved, field))
        == getattr(command, field)
        for field in fields
    )


class SearchResultResolutionService:
    def __init__(
        self,
        factory: Callable[[], SearchResultResolutionUnitOfWork],
        credentials: SourceCredentialVerifier,
        store: ArtifactStore,
    ) -> None:
        self._factory = factory
        self._credentials = credentials
        self._store = store

    def _authorize(
        self,
        uow: SearchResultResolutionUnitOfWork,
        principal: VerifiedPrincipal | None,
        project: UUID,
        *,
        write: bool = False,
    ) -> datetime:
        if not isinstance(principal, VerifiedPrincipal):
            _fail(ErrorCode.AUTHENTICATION_REQUIRED, "authenticated principal required")
        rows = uow.search_result_resolutions.authority(principal, project)
        at = uow.search_result_resolutions.at()
        try:
            live = principal.verified_at <= at and self._credentials.is_valid(principal, at)
        except Exception:
            live = False
        for row in rows:
            if (
                live
                and row["retired_at"] is None
                and row["membership_status"] == "ACTIVE"
                and row["binding_status"] == "ACTIVE"
                and row["role"] in (_WRITERS if write else _READERS)
                and row["effective_from"] <= at
                and (row["effective_until"] is None or at < row["effective_until"])
                and row["bound_at"] <= at
                and (row["revoked_at"] is None or at < row["revoked_at"])
                and (not write or row["lifecycle_status"] == "ACTIVE")
            ):
                return at
        _fail(ErrorCode.FORBIDDEN, "current project authority unavailable")

    def _result(
        self,
        uow: SearchResultResolutionUnitOfWork,
        identity: UUID,
        project: UUID,
        *,
        admission: bool,
    ) -> dict[str, Any]:
        row = uow.metadata_observations.result(identity, project)
        if row is None:
            _fail(ErrorCode.NOT_FOUND, "search result not found")
        history = uow.literature_search_execution.provenance(row["execution_id"])
        for reference in history["plan"]["material"]["research_question_refs"]:
            question = uow.literature_search_plan.question(UUID(reference["id"]), lock=False)
            if question is None or question["content_hash"] != reference["content_hash"]:
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "question closure invalid")
            try:
                _validate_question_row(question, project)
            except ResearchBaseError:
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "question closure invalid")
        execution = history["execution"]
        if admission:
            if execution.status not in {"SUCCEEDED", "FAILED", "CANCELLED", "UNKNOWN"}:
                _fail(ErrorCode.INVALID_STATE_TRANSITION, "terminal execution required")
            if any(a["status"] == "RESERVED" for a in history["attempts"]):
                _fail(ErrorCode.INVALID_STATE_TRANSITION, "terminal attempt history required")
            if not any(
                e.kind == "FINISHED" and e.new_status == execution.status for e in history["events"]
            ):
                _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "terminal history incomplete")
        return row

    def _artifact(
        self,
        uow: SearchResultResolutionUnitOfWork,
        identity: UUID,
        project: UUID,
    ) -> None:
        row = uow.search_result_resolutions.artifact(identity)
        if row is None or row["project_id"] != project:
            _fail(ErrorCode.FORBIDDEN, "related basis access unavailable")
        if row["status"] not in {"FROZEN", "SUPERSEDED"} or row["frozen_at"] is None:
            _fail(ErrorCode.FROZEN_REFERENCE_REQUIRED, "exact frozen artifact required")
        try:
            if row["locator"] != "sha256:" + row["content_hash"]:
                raise ValueError
            data = self._store.open(row["locator"])
            if str(sha256_bytes(data)) != row["content_hash"] or len(data) != row["byte_size"]:
                raise ValueError
        except (OSError, ValueError):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "related basis unavailable or altered")

    def _version(
        self,
        uow: SearchResultResolutionUnitOfWork,
        identity: UUID,
        source: UUID,
        project: UUID,
        seen: set[UUID] | None = None,
    ) -> dict[str, Any]:
        seen = set() if seen is None else seen
        if identity in seen:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "cyclic source lineage")
        seen.add(identity)
        row = uow.source_version.version(identity)
        if row is None:
            _fail(ErrorCode.SOURCE_VERSION_NOT_FOUND, "source version not found")
        if row["literature_source_id"] != source:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "exact source mismatch")
        if row["status"] not in {"FROZEN", "SUPERSEDED"} or row["frozen_at"] is None:
            _fail(ErrorCode.FROZEN_REFERENCE_REQUIRED, "exact frozen source required")
        for field in ("fulltext_artifact_version_id", "correction_basis_artifact_version_id"):
            if row[field] is not None:
                artifact = uow.search_result_resolutions.artifact(row[field])
                if (
                    artifact is None
                    or artifact["status"] not in {"FROZEN", "SUPERSEDED"}
                    or artifact["frozen_at"] is None
                ):
                    _fail(
                        ErrorCode.FROZEN_REFERENCE_REQUIRED,
                        "exact frozen artifact reference required",
                    )
        if row["predecessor_source_version_id"] is not None:
            self._version(uow, row["predecessor_source_version_id"], source, project, seen)
        try:
            valid_digest = (
                row["hash_scheme"] == "sha256-cjson-v1"
                and _material_from_row(uow.source_version, row).digest() == row["content_hash"]
            )
        except (ValueError, TypeError, KeyError, ResearchBaseError):
            valid_digest = False
        if not valid_digest:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "source version digest mismatch")
        return row

    def _history(
        self,
        uow: SearchResultResolutionUnitOfWork,
        row: dict[str, Any],
        project: UUID,
    ) -> SearchResultResolutionReadback:
        if row["hash_scheme"] != "sha256-cjson-v1" or resolution_hash(row) != row["content_hash"]:
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "resolution digest mismatch")
        self._result(uow, row["search_result_record_id"], project, admission=False)
        if uow.source_version.source(row["source_id"], project) is None:
            _fail(ErrorCode.SOURCE_NOT_FOUND, "source not found")
        if row["source_version_id"] is not None:
            self._version(uow, row["source_version_id"], row["source_id"], project)
        return SearchResultResolutionReadback(
            project_id=project, **dict(row, resolved_at=row["resolved_at"].astimezone(UTC))
        )

    def _admit(
        self,
        uow: SearchResultResolutionUnitOfWork,
        command: RecordSearchResultResolutionCommand,
    ) -> None:
        result = self._result(
            uow, command.search_result_record_id, command.project_id, admission=True
        )
        source = uow.source_version.source(command.source_id, command.project_id)
        if source is None:
            _fail(ErrorCode.SOURCE_NOT_FOUND, "source not found")
        if source["lifecycle_status"] != "ACTIVE":
            _fail(ErrorCode.SOURCE_IDENTITY_CONFLICT, "active source required")
        version = self._version(
            uow, command.source_version_id, command.source_id, command.project_id
        )
        if not titles_match(result["title"], version["title"]):
            _fail(ErrorCode.SOURCE_IDENTITY_CONFLICT, "exact version title mismatch")
        current = (
            self._version(uow, source["current_version_id"], command.source_id, command.project_id)
            if source["current_version_id"]
            else None
        )
        if version["version_kind"] == "RETRACTED" or (
            current
            and (
                current["version_kind"] == "RETRACTED"
                or (current["version_kind"] == "CORRECTED" and current["id"] != version["id"])
            )
        ):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "source version currently unusable")
        identifiers = uow.search_result_resolutions.identifiers(result_doi(result["url"]))
        if len(identifiers) != 1 or identifiers[0]["literature_source_id"] != command.source_id:
            _fail(ErrorCode.SOURCE_IDENTITY_CONFLICT, "verified same-source DOI required")
        identifier = identifiers[0]
        events = uow.search_result_resolutions.verification_events(identifier["id"])
        if not any(
            e["new_status"] == "VERIFIED"
            and e["basis_artifact_version_id"]
            == identifier["verification_basis_artifact_version_id"]
            and e["verified_by"] == identifier["verified_by"]
            and e["occurred_at"] == identifier["verified_at"]
            for e in events
        ):
            _fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "identifier verification history invalid")
        self._artifact(
            uow, identifier["verification_basis_artifact_version_id"], command.project_id
        )

    def record_search_result_resolution(
        self,
        principal: VerifiedPrincipal,
        command: RecordSearchResultResolutionCommand,
    ) -> SearchResultResolutionReadback:
        for attempt in range(3):
            try:
                return self._record(principal, command)
            except ResearchBaseError as exc:
                if exc.details and exc.details.get("reread_b01"):
                    value = self.get_search_result_resolution(
                        principal, ExactResolutionQuery(command.project_id, command.id)
                    )
                    if value.resolved_by != principal.actor_id:
                        _fail(ErrorCode.FORBIDDEN, "resolution actor differs")
                    if not _same_material(value, command):
                        _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "resolution material changed")
                    return value
                retry = exc.details and exc.details.get("retryable_b01")
                if exc.code is not ErrorCode.CONCURRENT_MODIFICATION or not retry or attempt == 2:
                    raise
        raise AssertionError

    def _record(
        self,
        principal: VerifiedPrincipal,
        command: RecordSearchResultResolutionCommand,
    ) -> SearchResultResolutionReadback:
        with self._factory() as uow:
            uow.begin_resolution(read_only=False)
            repo = uow.search_result_resolutions
            repo.prepare_write(command.id)
            self._authorize(uow, principal, command.project_id)
            row = repo.exact(command.id, command.project_id)
            if row is not None:
                if row["resolved_by"] != principal.actor_id:
                    _fail(ErrorCode.FORBIDDEN, "resolution actor differs")
                if not _same_material(row, command):
                    _fail(ErrorCode.IDEMPOTENCY_CONFLICT, "resolution material changed")
                value = self._history(uow, row, command.project_id)
                self._authorize(uow, principal, command.project_id)
                uow.commit()
                return value
            if repo.id_exists(command.id):
                _fail(ErrorCode.NOT_FOUND, "resolution not found")
            self._authorize(uow, principal, command.project_id, write=True)
            self._admit(uow, command)
            if repo.duplicate(
                command.search_result_record_id, command.source_id, command.source_version_id
            ):
                _fail(ErrorCode.DUPLICATE_CONTENT, "resolution tuple already exists")
            at = self._authorize(uow, principal, command.project_id, write=True)
            row = {
                "id": command.id,
                "search_result_record_id": command.search_result_record_id,
                "source_id": command.source_id,
                "source_version_id": command.source_version_id,
                "resolved_by": principal.actor_id,
                "resolved_at": at,
                "basis": command.basis,
                "hash_scheme": "sha256-cjson-v1",
            }
            row["content_hash"] = resolution_hash(row)
            repo.insert(row)
            repo.force_constraints()
            self._authorize(uow, principal, command.project_id, write=True)
            value = SearchResultResolutionReadback(project_id=command.project_id, **row)
            uow.commit()
            return value

    def get_search_result_resolution(
        self,
        principal: VerifiedPrincipal,
        query: ExactResolutionQuery,
    ) -> SearchResultResolutionReadback:
        with self._factory() as uow:
            uow.begin_resolution(read_only=True)
            self._authorize(uow, principal, query.project_id)
            row = uow.search_result_resolutions.exact(query.id, query.project_id)
            if row is None:
                _fail(ErrorCode.NOT_FOUND, "resolution not found")
            value = self._history(uow, row, query.project_id)
            self._authorize(uow, principal, query.project_id)
            uow.commit()
            return value
