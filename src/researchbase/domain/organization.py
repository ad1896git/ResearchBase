"""Minimal project and workspace domain objects owned by PR-02."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import NewType
from uuid import UUID

from researchbase.foundation.enums import BaseStrEnum
from researchbase.foundation.ids import ActorId
from researchbase.foundation.time import to_utc

ProjectId = NewType("ProjectId", UUID)
WorkspaceId = NewType("WorkspaceId", UUID)


class LifecycleStatus(BaseStrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    RETIRED = "retired"


@dataclass(frozen=True, slots=True)
class Project:
    id: ProjectId
    name: str
    created_by: ActorId
    created_at: datetime
    description: str | None = None
    lifecycle_status: LifecycleStatus = LifecycleStatus.ACTIVE
    row_version: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID) or not isinstance(self.created_by, UUID):
            raise TypeError("project IDs must be UUID-compatible")
        object.__setattr__(self, "id", ProjectId(self.id))
        object.__setattr__(self, "created_by", ActorId(self.created_by))
        object.__setattr__(self, "lifecycle_status", LifecycleStatus(self.lifecycle_status))
        if not self.name.strip():
            raise ValueError("name must not be blank")
        object.__setattr__(self, "created_at", to_utc(self.created_at))
        if self.row_version < 1:
            raise ValueError("row_version must be positive")


@dataclass(frozen=True, slots=True)
class Workspace:
    id: WorkspaceId
    project_id: ProjectId
    name: str
    created_by: ActorId
    created_at: datetime
    locator: str | None = None
    lifecycle_status: LifecycleStatus = LifecycleStatus.ACTIVE
    row_version: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID) or not isinstance(self.project_id, UUID):
            raise TypeError("workspace IDs must be UUID-compatible")
        if not isinstance(self.created_by, UUID):
            raise TypeError("created_by must be UUID-compatible")
        object.__setattr__(self, "id", WorkspaceId(self.id))
        object.__setattr__(self, "project_id", ProjectId(self.project_id))
        object.__setattr__(self, "created_by", ActorId(self.created_by))
        object.__setattr__(self, "lifecycle_status", LifecycleStatus(self.lifecycle_status))
        if not self.name.strip():
            raise ValueError("name must not be blank")
        object.__setattr__(self, "created_at", to_utc(self.created_at))
        if self.row_version < 1:
            raise ValueError("row_version must be positive")
