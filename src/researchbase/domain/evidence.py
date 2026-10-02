"""Dataset identity and immutable DatasetSnapshot domain objects for PR-06."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import NewType
from uuid import UUID

from researchbase.domain.organization import LifecycleStatus, ProjectId
from researchbase.foundation.canonical_json import canonical_json_bytes
from researchbase.foundation.frozen_json import freeze_json, thaw_json
from researchbase.foundation.hashing import ContentHash, sha256_canonical_json
from researchbase.foundation.ids import ActorId
from researchbase.foundation.time import to_utc

DatasetId = NewType("DatasetId", UUID)
DatasetSnapshotId = NewType("DatasetSnapshotId", UUID)


@dataclass(frozen=True, slots=True)
class Dataset:
    id: DatasetId
    project_id: ProjectId | None
    name: str
    created_by: ActorId
    created_at: datetime
    description: str | None = None
    source_locator: str | None = None
    lifecycle_status: LifecycleStatus = LifecycleStatus.ACTIVE
    row_version: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID):
            raise TypeError("dataset id must be UUID-compatible")
        if self.project_id is not None and not isinstance(self.project_id, UUID):
            raise TypeError("project id must be UUID-compatible")
        if not isinstance(self.created_by, UUID):
            raise TypeError("created_by must be UUID-compatible")
        object.__setattr__(self, "id", DatasetId(self.id))
        if self.project_id is not None:
            object.__setattr__(self, "project_id", ProjectId(self.project_id))
        object.__setattr__(self, "created_by", ActorId(self.created_by))
        object.__setattr__(self, "lifecycle_status", LifecycleStatus(self.lifecycle_status))
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name must not be blank")
        object.__setattr__(self, "created_at", to_utc(self.created_at))
        if self.row_version < 1:
            raise ValueError("row_version must be positive")


@dataclass(frozen=True, slots=True)
class DatasetSnapshot:
    id: DatasetSnapshotId
    dataset_id: DatasetId
    manifest_hash: ContentHash
    selection_definition: object
    manifest_locator: str | None
    content_hash: ContentHash
    created_by: ActorId
    created_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID) or not isinstance(self.dataset_id, UUID):
            raise TypeError("dataset snapshot IDs must be UUID-compatible")
        if not isinstance(self.created_by, UUID):
            raise TypeError("created_by must be UUID-compatible")
        object.__setattr__(self, "id", DatasetSnapshotId(self.id))
        object.__setattr__(self, "dataset_id", DatasetId(self.dataset_id))
        object.__setattr__(self, "manifest_hash", ContentHash(self.manifest_hash))
        object.__setattr__(self, "selection_definition", freeze_json(self.selection_definition))
        object.__setattr__(self, "content_hash", ContentHash(self.content_hash))
        canonical_json_bytes(thaw_json(self.selection_definition))
        object.__setattr__(self, "created_by", ActorId(self.created_by))
        object.__setattr__(self, "created_at", to_utc(self.created_at))
        if self.content_hash != sha256_canonical_json(self.material_payload()):
            raise ValueError("content_hash does not match dataset snapshot material")

    def material_payload(self) -> dict[str, object]:
        """Return the exact AD-PR06-001 scientific material."""
        return {
            "manifest_hash": str(self.manifest_hash),
            "selection_definition": thaw_json(self.selection_definition),
        }
