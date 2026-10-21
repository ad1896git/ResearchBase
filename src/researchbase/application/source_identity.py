"""Application commands and scoped reads for PR2-01 public source identity."""

from __future__ import annotations

import json
import time
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID, uuid4

from researchbase.application.ports import SourceIdentityRepository, UnitOfWork
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.domain.source_identity import (
    NORMALIZATION_VERSION,
    IdentifierType,
    NormalizedIdentifier,
    SourceKind,
    normalize_reason,
    normalize_source_identifier,
    normalize_source_title,
)
from researchbase.foundation.canonical_json import canonical_json_text
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import sha256_canonical_json


class SourceCredentialVerifier(Protocol):
    def is_valid(self, principal: VerifiedPrincipal, at: datetime) -> bool: ...


@dataclass(frozen=True, slots=True)
class RegisterLiteratureSource:
    principal: VerifiedPrincipal
    project_id: UUID
    kind: SourceKind
    title: str
    request_id: UUID
    initial_identifier_type: IdentifierType | None = None
    initial_identifier_value: str | None = None


@dataclass(frozen=True, slots=True)
class AddSourceIdentifier:
    principal: VerifiedPrincipal
    project_id: UUID
    source_id: UUID
    identifier_type: IdentifierType
    identifier_value: str
    is_primary: bool
    request_id: UUID
    binding_basis_artifact_version_id: UUID | None = None
    supersedes_rejected_identifier_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class VerifySourceIdentifier:
    principal: VerifiedPrincipal
    project_id: UUID
    identifier_id: UUID
    basis_artifact_version_id: UUID
    reason: str
    request_id: UUID


@dataclass(frozen=True, slots=True)
class RejectSourceIdentifier(VerifySourceIdentifier):
    pass


class SourceIdentityService:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        credential_verifier: SourceCredentialVerifier | None,
        *,
        registered_other_namespaces: frozenset[str] = frozenset(),
    ) -> None:
        self._uow_factory = uow_factory
        self._credential_verifier = credential_verifier
        self._namespaces = registered_other_namespaces

    def register_literature_source(self, command: RegisterLiteratureSource) -> dict[str, object]:
        return self._retry(lambda: self._register_literature_source_once(command))

    def _register_literature_source_once(
        self, command: RegisterLiteratureSource
    ) -> dict[str, object]:
        title = _validated(lambda: normalize_source_title(command.title))
        initial: NormalizedIdentifier | None = None
        raw_value: str | None = None
        initial_type = command.initial_identifier_type
        if (initial_type is None) != (command.initial_identifier_value is None):
            raise _error(
                ErrorCode.VALIDATION_ERROR,
                "initial identifier type and value must be supplied together",
            )
        if initial_type is not None and command.initial_identifier_value is not None:
            initial = self._normalize(initial_type, command.initial_identifier_value)
            raw_value = unicodedata.normalize("NFC", command.initial_identifier_value).strip()
        initial_payload: dict[str, str] | None = None
        if initial is not None:
            assert initial_type is not None
            initial_payload = {
                "identifier_type": initial_type.value,
                "normalized_value": initial.normalized_value,
                "normalization_version": initial.normalization_version,
            }
        payload = {
            "type": "REGISTER_LITERATURE_SOURCE",
            "material_version": 1,
            "kind": command.kind.value,
            "title": title,
            "initial_identifier": initial_payload,
        }
        input_hash = str(sha256_canonical_json(payload))
        with self._uow_factory() as uow:
            uow.begin_serializable()
            repo = uow.source_identity
            repo.lock_command(
                command.principal,
                command.project_id,
                "REGISTER_LITERATURE_SOURCE",
                command.request_id,
            )
            existing = None
            if initial is not None:
                assert initial_type is not None
                repo.lock_identifier(initial_type.value, initial.normalized_value)
                existing = repo.source_by_identifier(
                    initial_type.value, initial.normalized_value, lock=True
                )
                if existing is not None:
                    repo.lock_source(_uuid(existing["literature_source_id"]))
            at, role, actor_type = self._authorize(repo, command.principal, command.project_id)
            _require_writer(role)
            receipt = repo.receipt(
                command.principal,
                command.project_id,
                "REGISTER_LITERATURE_SOURCE",
                command.request_id,
            )
            if receipt is not None:
                uow.commit()
                return _replay(receipt, input_hash)
            if existing is not None:
                if existing["verification_status"] != "VERIFIED":
                    raise _error(
                        ErrorCode.SOURCE_IDENTITY_CONFLICT,
                        "identifier is already bound but not verified",
                    )
                if (
                    existing["source_kind"] != command.kind.value
                    or existing["canonical_title"] != title
                ):
                    raise _error(
                        ErrorCode.SOURCE_IDENTITY_CONFLICT,
                        "verified identifier refers to incompatible source metadata",
                    )
                source_id = _uuid(existing["literature_source_id"])
                identifier_id = _uuid(existing["id"])
            else:
                source_id = uuid4()
                identifier_id = uuid4() if initial is not None else None
                repo.insert_source(
                    {
                        "id": source_id,
                        "kind": command.kind.value,
                        "title": title,
                        "actor": command.principal.actor_id,
                        "at": at,
                    }
                )
                if initial is not None and identifier_id is not None:
                    assert initial_type is not None
                    repo.insert_identifier(
                        {
                            "id": identifier_id,
                            "source": source_id,
                            "type": initial_type.value,
                            "value": raw_value,
                            "normalized": initial.normalized_value,
                            "normalization_version": NORMALIZATION_VERSION,
                            "basis": None,
                            "supersedes": None,
                            "is_primary": True,
                            "actor": command.principal.actor_id,
                            "at": at,
                        }
                    )
            repo.insert_link(
                {
                    "id": uuid4(),
                    "source": source_id,
                    "project": command.project_id,
                    "actor": command.principal.actor_id,
                    "at": at,
                }
            )
            dto: dict[str, object] = {
                "source_id": str(source_id),
                "identifier_id": str(identifier_id) if identifier_id else None,
            }
            self._receipt(
                repo,
                command.principal,
                command.project_id,
                "REGISTER_LITERATURE_SOURCE",
                command.request_id,
                input_hash,
                source_id,
                identifier_id,
                None,
                dto,
                at,
            )
            uow.commit()
            return dto

    def add_source_identifier(self, command: AddSourceIdentifier) -> dict[str, object]:
        return self._retry(lambda: self._add_source_identifier_once(command))

    def _add_source_identifier_once(self, command: AddSourceIdentifier) -> dict[str, object]:
        normalized = self._normalize(command.identifier_type, command.identifier_value)
        raw_value = unicodedata.normalize("NFC", command.identifier_value).strip()
        if (
            command.supersedes_rejected_identifier_id is not None
            and command.binding_basis_artifact_version_id is None
        ):
            raise _error(ErrorCode.VALIDATION_ERROR, "corrected binding requires a frozen basis")
        payload = {
            "type": "ADD_SOURCE_IDENTIFIER",
            "material_version": 1,
            "source_id": str(command.source_id),
            "identifier_type": command.identifier_type.value,
            "normalized_value": normalized.normalized_value,
            "normalization_version": normalized.normalization_version,
            "is_primary": command.is_primary,
            "binding_basis_artifact_version_id": _str_or_none(
                command.binding_basis_artifact_version_id
            ),
            "supersedes_rejected_identifier_id": _str_or_none(
                command.supersedes_rejected_identifier_id
            ),
        }
        input_hash = str(sha256_canonical_json(payload))
        with self._uow_factory() as uow:
            uow.begin_serializable()
            repo = uow.source_identity
            repo.lock_command(
                command.principal, command.project_id, "ADD_SOURCE_IDENTIFIER", command.request_id
            )
            repo.lock_identifier(command.identifier_type.value, normalized.normalized_value)
            repo.lock_source(command.source_id)
            has_rejected = repo.has_rejected_identifier(
                command.identifier_type.value, normalized.normalized_value
            )
            if command.binding_basis_artifact_version_id is not None:
                if not repo.basis_is_frozen(command.binding_basis_artifact_version_id):
                    raise _error(
                        ErrorCode.IDENTIFIER_BASIS_NOT_FROZEN,
                        "identifier binding basis must be frozen",
                    )
            predecessor = None
            if command.supersedes_rejected_identifier_id is not None:
                predecessor = repo.identifier(
                    command.supersedes_rejected_identifier_id, command.project_id, lock=True
                )
            conflict = repo.source_by_identifier(
                command.identifier_type.value, normalized.normalized_value, lock=True
            )
            at, role, _ = self._authorize(repo, command.principal, command.project_id)
            _require_writer(role)
            receipt = repo.receipt(
                command.principal, command.project_id, "ADD_SOURCE_IDENTIFIER", command.request_id
            )
            if receipt is not None:
                uow.commit()
                return _replay(receipt, input_hash)
            if repo.source(command.source_id, command.project_id) is None:
                raise _error(ErrorCode.SOURCE_NOT_FOUND, "source not found")
            if conflict is not None:
                raise _error(ErrorCode.IDENTIFIER_ALREADY_BOUND, "identifier is already bound")
            if has_rejected and command.supersedes_rejected_identifier_id is None:
                raise _error(
                    ErrorCode.SOURCE_IDENTITY_CONFLICT,
                    "rejected identifier requires an explicit corrected-binding predecessor",
                )
            if command.binding_basis_artifact_version_id is not None:
                predecessor_id = command.supersedes_rejected_identifier_id
                assert predecessor_id is not None
                if (
                    predecessor is None
                    or predecessor["verification_status"] != "REJECTED"
                    or predecessor["identifier_type"] != command.identifier_type.value
                    or predecessor["normalized_value"] != normalized.normalized_value
                ):
                    raise _error(
                        ErrorCode.SOURCE_IDENTITY_CONFLICT,
                        "corrected binding predecessor does not match rejected identity",
                    )
                if _uuid(predecessor["literature_source_id"]) != command.source_id:
                    raise _error(
                        ErrorCode.SOURCE_IDENTITY_CONFLICT,
                        "cross-source identifier correction is not authorized in PR2-01",
                    )
            identifier_id = uuid4()
            repo.insert_identifier(
                {
                    "id": identifier_id,
                    "source": command.source_id,
                    "type": command.identifier_type.value,
                    "value": raw_value,
                    "normalized": normalized.normalized_value,
                    "normalization_version": normalized.normalization_version,
                    "basis": command.binding_basis_artifact_version_id,
                    "supersedes": command.supersedes_rejected_identifier_id,
                    "is_primary": command.is_primary,
                    "actor": command.principal.actor_id,
                    "at": at,
                }
            )
            dto: dict[str, object] = {
                "source_id": str(command.source_id),
                "identifier_id": str(identifier_id),
            }
            self._receipt(
                repo,
                command.principal,
                command.project_id,
                "ADD_SOURCE_IDENTIFIER",
                command.request_id,
                input_hash,
                command.source_id,
                identifier_id,
                None,
                dto,
                at,
            )
            uow.commit()
            return dto

    def verify_source_identifier(self, command: VerifySourceIdentifier) -> dict[str, object]:
        return self._change_status(command, "VERIFY_SOURCE_IDENTIFIER", "VERIFIED")

    def reject_source_identifier(self, command: RejectSourceIdentifier) -> dict[str, object]:
        return self._change_status(command, "REJECT_SOURCE_IDENTIFIER", "REJECTED")

    def _change_status(
        self, command: VerifySourceIdentifier, command_name: str, new_status: str
    ) -> dict[str, object]:
        return self._retry(lambda: self._change_status_once(command, command_name, new_status))

    def _change_status_once(
        self, command: VerifySourceIdentifier, command_name: str, new_status: str
    ) -> dict[str, object]:
        reason = _validated(lambda: normalize_reason(command.reason))
        payload = {
            "type": command_name,
            "material_version": 1,
            "identifier_id": str(command.identifier_id),
            "basis_artifact_version_id": str(command.basis_artifact_version_id),
            "reason": reason,
        }
        input_hash = str(sha256_canonical_json(payload))
        with self._uow_factory() as uow:
            uow.begin_serializable()
            repo = uow.source_identity
            repo.lock_command(
                command.principal, command.project_id, command_name, command.request_id
            )
            preliminary = repo.identifier(command.identifier_id, command.project_id)
            if preliminary is None:
                raise _error(ErrorCode.SOURCE_NOT_FOUND, "source not found")
            repo.lock_identifier(
                str(preliminary["identifier_type"]), str(preliminary["normalized_value"])
            )
            repo.lock_source(_uuid(preliminary["literature_source_id"]))
            identifier = repo.identifier(command.identifier_id, command.project_id, lock=True)
            if identifier is None:
                raise _error(ErrorCode.SOURCE_NOT_FOUND, "source not found")
            basis_is_frozen = repo.basis_is_frozen(command.basis_artifact_version_id)
            at, role, actor_type = self._authorize(repo, command.principal, command.project_id)
            if command_name == "REJECT_SOURCE_IDENTIFIER":
                if (
                    role != "OWNER"
                    or actor_type != "HUMAN"
                    or repo.link_count(_uuid(identifier["literature_source_id"])) != 1
                ):
                    if role == "OWNER" and actor_type == "HUMAN":
                        raise _error(
                            ErrorCode.SHARED_SOURCE_REJECTION_REQUIRES_REVIEW,
                            "shared source rejection requires review",
                        )
                    raise _error(ErrorCode.FORBIDDEN, "rejection requires a HUMAN OWNER")
            elif role not in {"OWNER", "RESEARCHER"}:
                raise _error(ErrorCode.FORBIDDEN, "verification requires OWNER or RESEARCHER")
            receipt = repo.receipt(
                command.principal, command.project_id, command_name, command.request_id
            )
            if receipt is not None:
                uow.commit()
                return _replay(receipt, input_hash)
            if identifier["verification_status"] not in {"UNVERIFIED", "VERIFIED"} or (
                new_status == "VERIFIED" and identifier["verification_status"] != "UNVERIFIED"
            ):
                raise _error(
                    ErrorCode.INVALID_STATE_TRANSITION,
                    "identifier status does not permit this transition",
                )
            if not basis_is_frozen:
                raise _error(
                    ErrorCode.IDENTIFIER_BASIS_NOT_FROZEN,
                    "identifier verification basis must be frozen",
                )
            event_id = uuid4()
            prior_status = str(identifier["verification_status"])
            verified_at = at if new_status == "VERIFIED" else None
            verified_by = command.principal.actor_id if new_status == "VERIFIED" else None
            basis_id = command.basis_artifact_version_id if new_status == "VERIFIED" else None
            repo.transition_identifier(
                {
                    "id": command.identifier_id,
                    "status": new_status,
                    "verified_at": verified_at,
                    "verified_by": verified_by,
                    "basis": basis_id,
                }
            )
            repo.insert_verification_event(
                {
                    "id": event_id,
                    "identifier": command.identifier_id,
                    "prior": prior_status,
                    "new": new_status,
                    "basis": command.basis_artifact_version_id,
                    "actor": command.principal.actor_id,
                    "at": at,
                    "reason": reason,
                    "request_id": command.request_id,
                }
            )
            source_id = _uuid(identifier["literature_source_id"])
            dto: dict[str, object] = {
                "source_id": str(source_id),
                "identifier_id": str(command.identifier_id),
                "event_id": str(event_id),
            }
            self._receipt(
                repo,
                command.principal,
                command.project_id,
                command_name,
                command.request_id,
                input_hash,
                source_id,
                command.identifier_id,
                event_id,
                dto,
                at,
            )
            uow.commit()
            return dto

    @staticmethod
    def _retry(call: Callable[[], dict[str, object]]) -> dict[str, object]:
        for attempt in range(3):
            try:
                return call()
            except ResearchBaseError as exc:
                if exc.code is not ErrorCode.CONCURRENT_MODIFICATION or attempt == 2:
                    raise
                time.sleep(0.01 * (attempt + 1))
        raise AssertionError("retry loop must return or raise")

    def get_literature_source(
        self, principal: VerifiedPrincipal, project_id: UUID, source_id: UUID
    ) -> dict[str, object]:
        with self._uow_factory() as uow:
            uow.begin_serializable()
            repo = uow.source_identity
            repo.lock_command(principal, project_id, "READ_SOURCE", source_id)
            at, _, _ = self._authorize(repo, principal, project_id)
            source = repo.source(source_id, project_id)
            if source is None:
                raise _error(ErrorCode.SOURCE_NOT_FOUND, "source not found")
            result = _source_dto(source)
            uow.commit()
            return result

    def find_source_by_identifier(
        self,
        principal: VerifiedPrincipal,
        project_id: UUID,
        identifier_type: IdentifierType,
        value: str,
    ) -> dict[str, object]:
        normalized = self._normalize(identifier_type, value)
        with self._uow_factory() as uow:
            uow.begin_serializable()
            repo = uow.source_identity
            repo.lock_command(principal, project_id, "READ_SOURCE", uuid4())
            self._authorize(repo, principal, project_id)
            source = repo.find_source(
                project_id, identifier_type.value, normalized.normalized_value
            )
            if source is None:
                raise _error(ErrorCode.SOURCE_NOT_FOUND, "source not found")
            result = _source_dto(source)
            uow.commit()
            return result

    def list_source_identifiers(
        self, principal: VerifiedPrincipal, project_id: UUID, source_id: UUID
    ) -> list[dict[str, object]]:
        with self._uow_factory() as uow:
            uow.begin_serializable()
            repo = uow.source_identity
            repo.lock_command(principal, project_id, "READ_SOURCE", source_id)
            self._authorize(repo, principal, project_id)
            source = repo.source(source_id, project_id)
            if source is None:
                raise _error(ErrorCode.SOURCE_NOT_FOUND, "source not found")
            results = [_identifier_dto(row) for row in repo.list_identifiers(source_id, project_id)]
            uow.commit()
            return results

    def _authorize(
        self, repo: SourceIdentityRepository, principal: VerifiedPrincipal, project_id: UUID
    ) -> tuple[datetime, str, str]:
        at = repo.database_time()
        facts = repo.authorize(principal, project_id, at)
        if facts is None or principal.verified_at > at or self._credential_verifier is None:
            raise _error(
                ErrorCode.AUTHENTICATION_REQUIRED, "a current verified principal is required"
            )
        try:
            credential_valid = self._credential_verifier.is_valid(principal, at)
        except Exception:
            credential_valid = False
        if not credential_valid:
            raise _error(
                ErrorCode.AUTHENTICATION_REQUIRED, "a current verified principal is required"
            )
        return at, facts[1], facts[0]

    def _normalize(self, identifier_type: IdentifierType, value: str) -> NormalizedIdentifier:
        return _validated(
            lambda: normalize_source_identifier(identifier_type, value, namespaces=self._namespaces)
        )

    def _receipt(
        self,
        repo: SourceIdentityRepository,
        principal: VerifiedPrincipal,
        project_id: UUID,
        command_name: str,
        request_id: UUID,
        input_hash: str,
        source_id: UUID,
        identifier_id: UUID | None,
        event_id: UUID | None,
        dto: dict[str, object],
        at: datetime,
    ) -> None:
        repo.insert_receipt(
            {
                "id": uuid4(),
                "deployment": principal.deployment_id,
                "project": project_id,
                "actor": principal.actor_id,
                "command": command_name,
                "request_id": request_id,
                "hash": input_hash,
                "source": source_id,
                "identifier": identifier_id,
                "event": event_id,
                "dto": canonical_json_text(dto),
                "at": at,
            }
        )


def _validated[ValueT](call: Callable[[], ValueT]) -> ValueT:
    try:
        return call()
    except ResearchBaseError:
        raise
    except (TypeError, ValueError) as exc:
        raise _error(ErrorCode.VALIDATION_ERROR, "invalid source identity input") from exc


def _require_writer(role: str) -> None:
    if role not in {"OWNER", "RESEARCHER"}:
        raise _error(ErrorCode.FORBIDDEN, "source write requires OWNER or RESEARCHER")


def _replay(receipt: dict[str, object], input_hash: str) -> dict[str, object]:
    if receipt["input_hash"] != input_hash:
        raise _error(
            ErrorCode.IDEMPOTENCY_CONFLICT, "request ID was already used with different input"
        )
    value = receipt["result_dto"]
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, dict):
        raise RuntimeError("literature command receipt DTO is not an object")
    return value


def _source_dto(row: dict[str, object]) -> dict[str, object]:
    result: dict[str, object] = {
        "source_id": str(row["id"]),
        "kind": str(row["source_kind"]),
        "title": str(row["canonical_title"]),
        "status": str(row["lifecycle_status"]),
        "created_by": str(row["created_by"]),
        "created_at": _timestamp(row["created_at"]),
        "row_version": _integer(row["row_version"]),
    }
    return result


def _identifier_dto(row: dict[str, object]) -> dict[str, object]:
    result: dict[str, object] = {
        "identifier_id": str(row["id"]),
        "source_id": str(row["literature_source_id"]),
        "identifier_type": str(row["identifier_type"]),
        "value": str(row["identifier_value"]),
        "normalized_value": str(row["normalized_value"]),
        "normalization_version": str(row["normalization_version"]),
        "is_primary": bool(row["is_primary"]),
        "status": str(row["verification_status"]),
        "verified_at": _timestamp(row["verified_at"]) if row["verified_at"] else None,
        "verified_by": _str_or_none(row["verified_by"]),
        "verification_basis_artifact_version_id": _str_or_none(
            row["verification_basis_artifact_version_id"]
        ),
        "binding_basis_artifact_version_id": _str_or_none(
            row.get("binding_basis_artifact_version_id")
        ),
        "supersedes_rejected_identifier_id": _str_or_none(
            row.get("supersedes_rejected_identifier_id")
        ),
    }
    return result


def _timestamp(value: object) -> str:
    if not isinstance(value, datetime):
        raise TypeError("database timestamp is invalid")
    return value.isoformat()


def _uuid(value: object) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def _integer(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value)
    raise TypeError("database integer is invalid")


def _str_or_none(value: object | None) -> str | None:
    return str(value) if value is not None else None


def _error(code: ErrorCode, message: str) -> ResearchBaseError:
    return ResearchBaseError(code, message)
