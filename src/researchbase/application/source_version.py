"""Application commands for the SourceVersion lifecycle."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from researchbase.application.ports import UnitOfWork
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.domain.source_version import (
    FrozenSourceReference,
    SourceVersionKind,
    SourceVersionMaterial,
    SourceVersionStatus,
)
from researchbase.foundation.canonical_json import canonical_json_text
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import sha256_canonical_json


class SourceVersionCredentialVerifier(Protocol):
    def is_valid(self, principal: VerifiedPrincipal, at: datetime) -> bool: ...


@dataclass(frozen=True, slots=True)
class CreateSourceVersion:
    principal: VerifiedPrincipal
    project_id: UUID
    material: SourceVersionMaterial
    request_id: UUID


@dataclass(frozen=True, slots=True)
class UpdateSourceVersionDraft:
    principal: VerifiedPrincipal
    project_id: UUID
    source_version_id: UUID
    material: SourceVersionMaterial
    request_id: UUID


@dataclass(frozen=True, slots=True)
class TransitionSourceVersion:
    principal: VerifiedPrincipal
    project_id: UUID
    source_version_id: UUID
    request_id: UUID


class SourceVersionService:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        credential_verifier: SourceVersionCredentialVerifier | None,
    ) -> None:
        self._uow_factory = uow_factory
        self._credential_verifier = credential_verifier

    def create(self, command: CreateSourceVersion) -> dict[str, object]:
        return self._retry(lambda: self._create_once(command))

    def _create_once(self, command: CreateSourceVersion) -> dict[str, object]:
        material = command.material
        payload = _command_payload("CREATE_SOURCE_VERSION", command.project_id, material)
        digest = str(sha256_canonical_json(payload))
        principal = command.principal
        with self._uow_factory() as uow:
            uow.begin_serializable()
            repo = uow.source_version
            repo.lock_project(command.project_id)
            repo.lock_command(
                principal.deployment_id,
                command.project_id,
                principal.actor_id,
                "CREATE_SOURCE_VERSION",
                command.request_id,
            )
            source = repo.source(material.literature_source_id, command.project_id, lock=True)
            if source is None:
                raise _error(ErrorCode.SOURCE_NOT_FOUND, "source not found")
            facts, at = self._authorize(repo, principal, command.project_id)
            _require_writer(facts)
            prior = repo.receipt(
                principal.deployment_id,
                command.project_id,
                principal.actor_id,
                "CREATE_SOURCE_VERSION",
                command.request_id,
            )
            if prior is not None:
                return _replay(uow, prior, digest)
            if source["lifecycle_status"] != "ACTIVE":
                raise _error(ErrorCode.SOURCE_VERSION_NOT_FREEZABLE, "source is not active")
            _validate_references(repo, material, source["current_version_id"])
            version_id = uuid4()
            number = repo.next_version_number(material.literature_source_id)
            repo.insert_draft(_draft_values(version_id, number, material, principal.actor_id, at))
            dto = _dto(
                version_id, material.literature_source_id, number, SourceVersionStatus.DRAFT, None
            )
            _save_receipt(
                repo,
                principal,
                command.project_id,
                "CREATE_SOURCE_VERSION",
                command.request_id,
                digest,
                version_id,
                dto,
                at,
            )
            uow.commit()
            return dto

    def update(self, command: UpdateSourceVersionDraft) -> dict[str, object]:
        return self._retry(lambda: self._update_once(command))

    def _update_once(self, command: UpdateSourceVersionDraft) -> dict[str, object]:
        principal = command.principal
        material = command.material
        payload = _command_payload(
            "UPDATE_SOURCE_VERSION_DRAFT",
            command.project_id,
            material,
            source_version_id=command.source_version_id,
        )
        digest = str(sha256_canonical_json(payload))
        with self._uow_factory() as uow:
            uow.begin_serializable()
            repo = uow.source_version
            preliminary = repo.version(command.source_version_id)
            if preliminary is None:
                raise _error(ErrorCode.SOURCE_VERSION_NOT_FOUND, "source version not found")
            source_id = preliminary["literature_source_id"]
            repo.lock_project(command.project_id)
            repo.lock_command(
                principal.deployment_id,
                command.project_id,
                principal.actor_id,
                "UPDATE_SOURCE_VERSION_DRAFT",
                command.request_id,
            )
            source = repo.source(source_id, command.project_id, lock=True)
            version = repo.version(command.source_version_id, lock=True)
            if source is None or version is None:
                raise _error(ErrorCode.SOURCE_VERSION_NOT_FOUND, "source version not found")
            facts, at = self._authorize(repo, principal, command.project_id)
            _require_writer(facts)
            prior = repo.receipt(
                principal.deployment_id,
                command.project_id,
                principal.actor_id,
                "UPDATE_SOURCE_VERSION_DRAFT",
                command.request_id,
            )
            if prior is not None:
                return _replay(uow, prior, digest)
            if version["status"] != "DRAFT" or material.literature_source_id != source_id:
                raise _error(
                    ErrorCode.SOURCE_VERSION_IMMUTABLE, "only the owning draft may be edited"
                )
            _validate_references(repo, material, source["current_version_id"])
            repo.update_draft(command.source_version_id, _material_values(material))
            dto = _dto(
                command.source_version_id,
                source_id,
                version["version_number"],
                SourceVersionStatus.DRAFT,
                None,
            )
            _save_receipt(
                repo,
                principal,
                command.project_id,
                "UPDATE_SOURCE_VERSION_DRAFT",
                command.request_id,
                digest,
                command.source_version_id,
                dto,
                at,
            )
            uow.commit()
            return dto

    def freeze(self, command: TransitionSourceVersion) -> dict[str, object]:
        return self._transition(command, "FREEZE_SOURCE_VERSION")

    def abandon(self, command: TransitionSourceVersion) -> dict[str, object]:
        return self._transition(command, "ABANDON_SOURCE_VERSION")

    def get(
        self, principal: VerifiedPrincipal, project_id: UUID, source_version_id: UUID
    ) -> dict[str, object]:
        with self._uow_factory() as uow:
            uow.begin_serializable()
            repo = uow.source_version
            row = repo.version(source_version_id)
            if row is None or repo.source(row["literature_source_id"], project_id) is None:
                raise _error(ErrorCode.SOURCE_VERSION_NOT_FOUND, "source version not found")
            self._authorize(repo, principal, project_id)
            result = _read_dto(row)
            uow.commit()
            return result

    def list(
        self, principal: VerifiedPrincipal, project_id: UUID, source_id: UUID
    ) -> list[dict[str, object]]:
        with self._uow_factory() as uow:
            uow.begin_serializable()
            repo = uow.source_version
            if repo.source(source_id, project_id) is None:
                raise _error(ErrorCode.SOURCE_NOT_FOUND, "source not found")
            self._authorize(repo, principal, project_id)
            result = [_read_dto(row) for row in repo.versions_for_source(source_id)]
            uow.commit()
            return result

    def _transition(self, command: TransitionSourceVersion, name: str) -> dict[str, object]:
        return self._retry(lambda: self._transition_once(command, name))

    def _transition_once(self, command: TransitionSourceVersion, name: str) -> dict[str, object]:
        principal = command.principal
        payload = {
            "type": name,
            "material_version": 1,
            "project_id": str(command.project_id),
            "source_version_id": str(command.source_version_id),
        }
        digest = str(sha256_canonical_json(payload))
        with self._uow_factory() as uow:
            uow.begin_serializable()
            repo = uow.source_version
            preliminary = repo.version(command.source_version_id)
            if preliminary is None:
                raise _error(ErrorCode.SOURCE_VERSION_NOT_FOUND, "source version not found")
            source_id = preliminary["literature_source_id"]
            repo.lock_project(command.project_id)
            repo.lock_command(
                principal.deployment_id,
                command.project_id,
                principal.actor_id,
                name,
                command.request_id,
            )
            source = repo.source(source_id, command.project_id, lock=True)
            version = repo.version(command.source_version_id, lock=True)
            if source is None or version is None:
                raise _error(ErrorCode.SOURCE_VERSION_NOT_FOUND, "source version not found")
            prior_current = (
                repo.current_version(source_id) if name == "FREEZE_SOURCE_VERSION" else None
            )
            facts, at = self._authorize(repo, principal, command.project_id)
            _require_writer(facts)
            prior = repo.receipt(
                principal.deployment_id,
                command.project_id,
                principal.actor_id,
                name,
                command.request_id,
            )
            if prior is not None:
                return _replay(uow, prior, digest)
            if version["status"] != "DRAFT":
                error = (
                    ErrorCode.SOURCE_VERSION_ALREADY_FROZEN
                    if version["status"] in {"FROZEN", "SUPERSEDED"}
                    else ErrorCode.INVALID_STATE_TRANSITION
                )
                raise _error(error, "source version is not a draft")
            if name == "FREEZE_SOURCE_VERSION":
                if source["lifecycle_status"] != "ACTIVE":
                    raise _error(ErrorCode.SOURCE_VERSION_NOT_FREEZABLE, "source is not active")
                material = _material_from_row(repo, version)
                _validate_references(repo, material, source["current_version_id"])
                content_hash = material.digest()
                repo.freeze(command.source_version_id, content_hash, at)
                repo.set_current(source_id, command.source_version_id)
                if prior_current is not None:
                    repo.supersede(prior_current["id"])
                status = SourceVersionStatus.FROZEN
            else:
                repo.abandon(command.source_version_id)
                content_hash = None
                status = SourceVersionStatus.ABANDONED
            dto = _dto(
                command.source_version_id,
                source_id,
                version["version_number"],
                status,
                content_hash,
            )
            _save_receipt(
                repo,
                principal,
                command.project_id,
                name,
                command.request_id,
                digest,
                command.source_version_id,
                dto,
                at,
            )
            uow.commit()
            return dto

    def _authorize(self, repo, principal: VerifiedPrincipal, project_id: UUID):
        facts = repo.authorize(principal, project_id, None)
        at = repo.at()
        verifier = self._credential_verifier
        if facts is None or verifier is None or principal.verified_at > at:
            raise _error(ErrorCode.FORBIDDEN, "current project authority is unavailable")
        try:
            valid = bool(verifier.is_valid(principal, at))
        except Exception:
            valid = False
        valid = bool(
            valid
            and facts["retired_at"] is None
            and facts["membership_status"] == "ACTIVE"
            and facts["role"] is not None
            and facts["effective_from"] <= at
            and (facts["effective_until"] is None or at < facts["effective_until"])
            and facts["binding_status"] == "ACTIVE"
            and facts["bound_at"] <= at
            and (facts["revoked_at"] is None or at < facts["revoked_at"])
        )
        if not valid:
            raise _error(ErrorCode.FORBIDDEN, "current project authority is unavailable")
        return facts, at

    @staticmethod
    def _retry[ResultT](call: Callable[[], ResultT]) -> ResultT:
        for attempt in range(3):
            try:
                return call()
            except ResearchBaseError as exc:
                if exc.code is not ErrorCode.CONCURRENT_MODIFICATION or attempt == 2:
                    raise
                time.sleep(0.01 * (attempt + 1))
        raise AssertionError("retry loop must return or raise")


def _validate_references(repo, material: SourceVersionMaterial, current_version_id) -> None:
    for ref in (material.fulltext_artifact, material.correction_basis_artifact):
        if ref is not None:
            row = repo.artifact_ref(ref.id)
            if row is None or row["status"] != "FROZEN" or row["content_hash"] != ref.content_hash:
                raise _error(
                    ErrorCode.FROZEN_REFERENCE_REQUIRED,
                    "version references require the exact frozen ArtifactVersion",
                )
    predecessor = material.predecessor_source_version
    if predecessor is not None:
        row = repo.version(predecessor.id)
        if (
            row is None
            or row["literature_source_id"] != material.literature_source_id
            or row["status"] not in {"FROZEN", "SUPERSEDED"}
            or row["content_hash"] != predecessor.content_hash
        ):
            raise _error(
                ErrorCode.INVALID_SOURCE_VERSION_LINEAGE,
                "predecessor must be a prior same-source frozen version",
            )
    if material.version_kind in {SourceVersionKind.CORRECTED, SourceVersionKind.RETRACTED}:
        if predecessor is None or predecessor.id != current_version_id:
            raise _error(
                ErrorCode.INVALID_SOURCE_VERSION_LINEAGE,
                "correction predecessor must be the current source version",
            )


def _material_values(material: SourceVersionMaterial) -> dict[str, object]:
    return {
        "kind": material.version_kind.value,
        "predecessor": material.predecessor_source_version.id
        if material.predecessor_source_version
        else None,
        "correction_basis": material.correction_basis_artifact.id
        if material.correction_basis_artifact
        else None,
        "title": material.title,
        "abstract": material.abstract,
        "authors": canonical_json_text(material.payload()["authors"]),
        "publication_date": material.publication_date,
        "venue": material.venue,
        "external_label": material.external_version_label,
        "fulltext": material.fulltext_artifact.id if material.fulltext_artifact else None,
        "metadata": canonical_json_text(material.payload()["metadata"])
        if material.metadata is not None
        else None,
    }


def _draft_values(
    version_id: UUID, number: int, material: SourceVersionMaterial, actor: UUID, at: datetime
) -> dict[str, object]:
    return {
        "id": version_id,
        "source": material.literature_source_id,
        "number": number,
        "actor": actor,
        "at": at,
        **_material_values(material),
    }


def _material_from_row(repo, row: dict[str, Any]) -> SourceVersionMaterial:
    def artifact(field: str) -> FrozenSourceReference | None:
        reference_id = row[field]
        if reference_id is None:
            return None
        record = repo.artifact_ref(reference_id)
        if record is None:
            raise _error(ErrorCode.FROZEN_REFERENCE_REQUIRED, "referenced artifact is unavailable")
        return FrozenSourceReference(record["id"], record["content_hash"])

    predecessor = row["predecessor_source_version_id"]
    predecessor_ref = None
    if predecessor is not None:
        record = repo.version(predecessor)
        if record is None:
            raise _error(ErrorCode.INVALID_SOURCE_VERSION_LINEAGE, "predecessor is unavailable")
        predecessor_ref = FrozenSourceReference(record["id"], record["content_hash"])
    authors = row["authors"]
    metadata = row["metadata"]
    if isinstance(authors, str):
        authors = json.loads(authors)
    if isinstance(metadata, str):
        metadata = json.loads(metadata)
    return SourceVersionMaterial(
        literature_source_id=row["literature_source_id"],
        version_kind=SourceVersionKind(row["version_kind"]),
        predecessor_source_version=predecessor_ref,
        correction_basis_artifact=artifact("correction_basis_artifact_version_id"),
        title=row["title"],
        abstract=row["abstract"],
        authors=tuple(authors),
        publication_date=row["publication_date"],
        venue=row["venue"],
        external_version_label=row["external_version_label"],
        fulltext_artifact=artifact("fulltext_artifact_version_id"),
        metadata=metadata,
    )


def _command_payload(
    name: str,
    project_id: UUID,
    material: SourceVersionMaterial,
    *,
    source_version_id: UUID | None = None,
) -> dict[str, Any]:
    material_payload = material.payload()
    result: dict[str, Any] = {"type": name, "material_version": 1, "project_id": str(project_id)}
    if name == "CREATE_SOURCE_VERSION":
        result["source_id"] = str(material.literature_source_id)
    else:
        result["source_version_id"] = str(source_version_id)
    result.update(
        {
            "version_kind": material.version_kind.value,
            "predecessor_source_version_id": str(material.predecessor_source_version.id)
            if material.predecessor_source_version
            else None,
            "correction_basis_artifact_version_id": str(material.correction_basis_artifact.id)
            if material.correction_basis_artifact
            else None,
            "title": material.title,
            "abstract": material.abstract,
            "authors": material_payload["authors"],
            "publication_date": material.publication_date.isoformat()
            if material.publication_date
            else None,
            "venue": material.venue,
            "external_version_label": material.external_version_label,
            "fulltext_artifact_version_id": str(material.fulltext_artifact.id)
            if material.fulltext_artifact
            else None,
            "metadata": material_payload["metadata"],
        }
    )
    return result


def _dto(
    version_id: UUID,
    source_id: UUID,
    number: int,
    status: SourceVersionStatus,
    content_hash: str | None,
) -> dict[str, object]:
    return {
        "source_version_id": str(version_id),
        "literature_source_id": str(source_id),
        "version_number": number,
        "status": status.value,
        "content_hash": content_hash,
    }


def _read_dto(row: dict[str, Any]) -> dict[str, object]:
    result: dict[str, object] = {
        "source_version_id": str(row["id"]),
        "literature_source_id": str(row["literature_source_id"]),
        "version_number": int(row["version_number"]),
        "version_kind": str(row["version_kind"]),
        "predecessor_source_version_id": (
            str(row["predecessor_source_version_id"])
            if row["predecessor_source_version_id"]
            else None
        ),
        "correction_basis_artifact_version_id": (
            str(row["correction_basis_artifact_version_id"])
            if row["correction_basis_artifact_version_id"]
            else None
        ),
        "title": row["title"],
        "abstract": row["abstract"],
        "authors": row["authors"],
        "publication_date": row["publication_date"].isoformat()
        if row["publication_date"]
        else None,
        "venue": row["venue"],
        "external_version_label": row["external_version_label"],
        "fulltext_artifact_version_id": (
            str(row["fulltext_artifact_version_id"])
            if row["fulltext_artifact_version_id"]
            else None
        ),
        "metadata": row["metadata"],
        "status": str(row["status"]),
        "content_hash": row["content_hash"],
        "hash_scheme": str(row["hash_scheme"]),
        "frozen_at": row["frozen_at"].isoformat() if row["frozen_at"] else None,
    }
    return result


def _save_receipt(repo, principal, project_id, name, request_id, digest, version_id, dto, at):
    repo.insert_receipt(
        {
            "id": uuid4(),
            "deployment": principal.deployment_id,
            "project": project_id,
            "actor": principal.actor_id,
            "command": name,
            "request": request_id,
            "hash": digest,
            "result_id": version_id,
            "dto": canonical_json_text(dto),
            "at": at,
        }
    )


def _replay(uow, prior, digest):
    if prior["request_hash"] != digest:
        raise _error(ErrorCode.IDEMPOTENCY_CONFLICT, "request ID was reused with different input")
    uow.commit()
    value = prior["result_dto"]
    return json.loads(value) if isinstance(value, str) else dict(value)


def _require_writer(facts) -> None:
    if facts["role"] not in {"OWNER", "RESEARCHER"}:
        raise _error(ErrorCode.FORBIDDEN, "source version write requires OWNER or RESEARCHER")


def _error(code: ErrorCode, message: str) -> ResearchBaseError:
    return ResearchBaseError(code, message)
