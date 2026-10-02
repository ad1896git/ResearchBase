"""Claim identity, version, and exact evidence-relation domain objects for PR-12."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from typing import NewType, Self
from uuid import UUID

from researchbase.domain.measurement import MeasurementId
from researchbase.domain.organization import ProjectId
from researchbase.domain.statistical_result import StatisticalResultId
from researchbase.foundation.canonical_json import canonical_json_bytes
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.frozen_json import freeze_json, thaw_json
from researchbase.foundation.hashing import ContentHash, sha256_canonical_json
from researchbase.foundation.ids import ActorId
from researchbase.foundation.time import Clock, to_utc
from researchbase.foundation.versioning import (
    VersionStatus,
    freeze_material,
    require_transition,
    validate_version_hash,
)

ClaimId = NewType("ClaimId", UUID)
ClaimVersionId = NewType("ClaimVersionId", UUID)
EvidenceRelationId = NewType("EvidenceRelationId", UUID)


class EvidenceRelationType(StrEnum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    QUALIFIES = "qualifies"
    CONTEXT = "context"


@dataclass(frozen=True, slots=True)
class Claim:
    id: ClaimId
    project_id: ProjectId
    created_by: ActorId
    created_at: datetime
    current_version_id: ClaimVersionId | None = None
    row_version: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID) or not isinstance(self.project_id, UUID):
            raise TypeError("claim IDs must be UUID-compatible")
        if not isinstance(self.created_by, UUID):
            raise TypeError("created_by must be UUID-compatible")
        if self.current_version_id is not None and not isinstance(self.current_version_id, UUID):
            raise TypeError("current version id must be UUID-compatible")
        object.__setattr__(self, "id", ClaimId(self.id))
        object.__setattr__(self, "project_id", ProjectId(self.project_id))
        object.__setattr__(self, "created_by", ActorId(self.created_by))
        if self.current_version_id is not None:
            object.__setattr__(self, "current_version_id", ClaimVersionId(self.current_version_id))
        object.__setattr__(self, "created_at", to_utc(self.created_at))
        _validate_positive(self.row_version, "row_version")


@dataclass(frozen=True, slots=True)
class ClaimVersion:
    id: ClaimVersionId
    claim_id: ClaimId
    version_number: int
    status: VersionStatus
    statement: str
    scope: object | None
    qualification: str | None
    created_by: ActorId
    created_at: datetime
    support_set_hash: ContentHash | None = None
    content_hash: ContentHash | None = None
    hash_scheme: str | None = None
    frozen_at: datetime | None = None
    row_version: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID) or not isinstance(self.claim_id, UUID):
            raise TypeError("claim version IDs must be UUID-compatible")
        if not isinstance(self.created_by, UUID):
            raise TypeError("created_by must be UUID-compatible")
        object.__setattr__(self, "id", ClaimVersionId(self.id))
        object.__setattr__(self, "claim_id", ClaimId(self.claim_id))
        object.__setattr__(self, "created_by", ActorId(self.created_by))
        object.__setattr__(self, "status", VersionStatus(self.status))
        _validate_positive(self.version_number, "version_number")
        if not isinstance(self.statement, str) or not self.statement.strip():
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR,
                "statement must not be blank",
                {"field": "statement"},
            )
        if self.qualification is not None and not isinstance(self.qualification, str):
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR,
                "qualification must be text or null",
                {"field": "qualification"},
            )
        if self.scope is not None:
            object.__setattr__(self, "scope", freeze_json(self.scope))
        object.__setattr__(self, "created_at", to_utc(self.created_at))
        if self.frozen_at is not None:
            object.__setattr__(self, "frozen_at", to_utc(self.frozen_at))
        if self.support_set_hash is not None and not isinstance(self.support_set_hash, ContentHash):
            object.__setattr__(self, "support_set_hash", ContentHash(self.support_set_hash))
        if self.status in {VersionStatus.FROZEN, VersionStatus.SUPERSEDED} and (
            self.support_set_hash is None
        ):
            raise ValueError("frozen claim versions require support_set_hash")
        if self.status in {VersionStatus.DRAFT, VersionStatus.ABANDONED} and self.support_set_hash:
            raise ValueError("draft-origin claim versions must not have support_set_hash")
        object.__setattr__(
            self,
            "content_hash",
            validate_version_hash(
                self.status,
                self.material_payload(),
                self.content_hash,
                self.hash_scheme,
                self.frozen_at,
            ),
        )
        _validate_positive(self.row_version, "row_version")
        self.validate_material()

    def material_payload(self) -> dict[str, object | None]:
        return {
            "statement": self.statement,
            "scope": thaw_json(self.scope) if self.scope is not None else None,
            "qualification": self.qualification,
            "support_set_hash": (
                str(self.support_set_hash) if self.support_set_hash is not None else None
            ),
        }

    def validate_material(self) -> None:
        try:
            canonical_json_bytes(self.material_payload())
        except (TypeError, ValueError) as exc:
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR,
                "claim material is not valid canonical JSON",
                {"field": "material"},
            ) from exc

    def edit_material(
        self, *, statement: str, scope: object | None, qualification: str | None
    ) -> Self:
        if self.status is not VersionStatus.DRAFT:
            raise ResearchBaseError(ErrorCode.IMMUTABLE_RECORD, "version material is immutable")
        candidate = replace(
            self,
            statement=statement,
            scope=scope,
            qualification=qualification,
            support_set_hash=None,
            content_hash=None,
            hash_scheme=None,
            frozen_at=None,
        )
        candidate.validate_material()
        return candidate

    def freeze(self, *, support_set_hash: ContentHash, clock: Clock) -> ClaimVersion:
        self.validate_material()
        normalized_support_hash = ContentHash(support_set_hash)
        material = self.material_payload()
        material["support_set_hash"] = str(normalized_support_hash)
        result = freeze_material(
            self.status,
            material,
            clock,
        )
        return replace(
            self,
            status=result.status,
            support_set_hash=normalized_support_hash,
            content_hash=result.content_hash,
            hash_scheme=result.hash_scheme,
            frozen_at=result.frozen_at,
        )

    def transition_to(self, target: VersionStatus) -> ClaimVersion:
        require_transition(self.status, target)
        return replace(self, status=target)


@dataclass(frozen=True, slots=True)
class EvidenceRelation:
    id: EvidenceRelationId
    claim_version_id: ClaimVersionId
    measurement_id: MeasurementId | None
    statistical_result_id: StatisticalResultId | None
    relation_type: EvidenceRelationType
    qualification: str | None
    created_by: ActorId
    created_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID) or not isinstance(self.claim_version_id, UUID):
            raise TypeError("evidence relation IDs must be UUID-compatible")
        if not isinstance(self.created_by, UUID):
            raise TypeError("created_by must be UUID-compatible")
        if (self.measurement_id is None) == (self.statistical_result_id is None):
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR,
                "exactly one evidence source is required",
                {"field": "evidence_source"},
            )
        for value, field in (
            (self.measurement_id, "measurement_id"),
            (self.statistical_result_id, "statistical_result_id"),
        ):
            if value is not None and not isinstance(value, UUID):
                raise TypeError(f"{field} must be UUID-compatible")
        object.__setattr__(self, "id", EvidenceRelationId(self.id))
        object.__setattr__(self, "claim_version_id", ClaimVersionId(self.claim_version_id))
        object.__setattr__(self, "relation_type", EvidenceRelationType(self.relation_type))
        object.__setattr__(self, "created_by", ActorId(self.created_by))
        object.__setattr__(self, "created_at", to_utc(self.created_at))

    @property
    def source_type(self) -> str:
        return "measurement" if self.measurement_id is not None else "statistical_result"

    @property
    def source_id(self) -> UUID:
        source_id = self.measurement_id or self.statistical_result_id
        if not isinstance(source_id, UUID):
            raise RuntimeError("evidence relation source invariant was violated")
        return source_id

    def semantic_row(self) -> dict[str, str | None]:
        return {
            "source_type": self.source_type,
            "source_id": str(self.source_id),
            "relation_type": self.relation_type.value,
            "qualification": self.qualification,
        }


def calculate_support_set_hash(relations: list[EvidenceRelation]) -> ContentHash:
    """Hash persisted evidence semantics, excluding relation identity metadata."""
    rows = [relation.semantic_row() for relation in relations]
    rows.sort(
        key=lambda row: (
            row["source_type"],
            row["source_id"],
            row["relation_type"],
            row["qualification"] is not None,
            row["qualification"] or "",
        )
    )
    return sha256_canonical_json(rows)


def _validate_positive(value: int, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field} must be positive")
