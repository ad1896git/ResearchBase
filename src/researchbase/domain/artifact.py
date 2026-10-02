"""Artifact identity and versioned exact-byte content semantics for PR-07."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from typing import NewType, Self
from uuid import UUID

from researchbase.domain.organization import ProjectId
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.frozen_json import freeze_json
from researchbase.foundation.hashing import ContentHash
from researchbase.foundation.ids import ActorId
from researchbase.foundation.time import Clock, to_utc
from researchbase.foundation.versioning import VersionStatus, require_transition

ArtifactId = NewType("ArtifactId", UUID)
ArtifactVersionId = NewType("ArtifactVersionId", UUID)


@dataclass(frozen=True, slots=True)
class Artifact:
    id: ArtifactId
    project_id: ProjectId | None
    artifact_type: str
    name: str
    description: str | None
    created_by: ActorId
    created_at: datetime
    current_version_id: ArtifactVersionId | None = None
    row_version: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID):
            raise TypeError("artifact id must be UUID-compatible")
        if self.project_id is not None and not isinstance(self.project_id, UUID):
            raise TypeError("project id must be UUID-compatible")
        if not isinstance(self.created_by, UUID):
            raise TypeError("created_by must be UUID-compatible")
        if self.current_version_id is not None and not isinstance(self.current_version_id, UUID):
            raise TypeError("current version id must be UUID-compatible")
        _validate_text(self.artifact_type, "artifact_type", 32)
        _validate_text(self.name, "name", 255)
        object.__setattr__(self, "id", ArtifactId(self.id))
        if self.project_id is not None:
            object.__setattr__(self, "project_id", ProjectId(self.project_id))
        object.__setattr__(self, "created_by", ActorId(self.created_by))
        if self.current_version_id is not None:
            object.__setattr__(
                self, "current_version_id", ArtifactVersionId(self.current_version_id)
            )
        object.__setattr__(self, "created_at", to_utc(self.created_at))
        _validate_row_version(self.row_version)


@dataclass(frozen=True, slots=True)
class ArtifactVersion:
    id: ArtifactVersionId
    artifact_id: ArtifactId
    version_number: int
    status: VersionStatus
    locator: str | None
    media_type: str | None
    byte_size: int | None
    content_hash: ContentHash
    metadata: object | None
    created_by: ActorId
    created_at: datetime
    frozen_at: datetime | None = None
    row_version: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID) or not isinstance(self.artifact_id, UUID):
            raise TypeError("artifact version IDs must be UUID-compatible")
        if not isinstance(self.created_by, UUID):
            raise TypeError("created_by must be UUID-compatible")
        object.__setattr__(self, "id", ArtifactVersionId(self.id))
        object.__setattr__(self, "artifact_id", ArtifactId(self.artifact_id))
        object.__setattr__(self, "created_by", ActorId(self.created_by))
        object.__setattr__(self, "status", VersionStatus(self.status))
        if self.locator is not None and not isinstance(self.locator, str):
            raise TypeError("locator must be text or null")
        if self.media_type is not None:
            _validate_text(self.media_type, "media_type", 128)
        if self.byte_size is not None and (
            isinstance(self.byte_size, bool)
            or not isinstance(self.byte_size, int)
            or self.byte_size < 0
        ):
            raise ValueError("byte_size must be non-negative")
        object.__setattr__(self, "content_hash", ContentHash(self.content_hash))
        if self.metadata is not None:
            object.__setattr__(self, "metadata", freeze_json(self.metadata))
        _validate_version_number(self.version_number)
        object.__setattr__(self, "created_at", to_utc(self.created_at))
        if self.frozen_at is not None:
            object.__setattr__(self, "frozen_at", to_utc(self.frozen_at))
        if (
            self.status in {VersionStatus.FROZEN, VersionStatus.SUPERSEDED}
            and self.frozen_at is None
        ):
            raise ValueError("non-draft versions require frozen_at")
        _validate_row_version(self.row_version)

    def edit_metadata(
        self,
        *,
        locator: str | None,
        media_type: str | None,
        byte_size: int | None,
        metadata: object | None,
    ) -> Self:
        if self.status is not VersionStatus.DRAFT:
            raise ResearchBaseError(ErrorCode.IMMUTABLE_RECORD, "version metadata is immutable")
        return replace(
            self,
            locator=locator,
            media_type=media_type,
            byte_size=byte_size,
            metadata=metadata,
        )

    def freeze(self, clock: Clock) -> Self:
        require_transition(self.status, VersionStatus.FROZEN)
        return replace(
            self,
            status=VersionStatus.FROZEN,
            frozen_at=to_utc(clock.now()),
        )

    def transition_to(self, target: VersionStatus) -> Self:
        require_transition(self.status, target)
        return replace(self, status=target)


def _validate_text(value: str, field: str, max_length: int) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must not be blank")
    if len(value) > max_length:
        raise ValueError(f"{field} exceeds maximum length")


def _validate_version_number(value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("version_number must be positive")


def _validate_row_version(value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("row_version must be positive")
