"""Application read models that do not expose persistence ORM objects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from researchbase.domain.identity import ActorType
from researchbase.domain.organization import LifecycleStatus, ProjectId, WorkspaceId
from researchbase.foundation.ids import ActorId


@dataclass(frozen=True, slots=True)
class ActorReadModel:
    id: ActorId
    actor_type: ActorType
    display_name: str
    external_key: str | None
    created_at: datetime
    retired_at: datetime | None
    row_version: int


@dataclass(frozen=True, slots=True)
class ProjectReadModel:
    id: ProjectId
    name: str
    description: str | None
    lifecycle_status: LifecycleStatus
    created_by: ActorId
    created_at: datetime
    row_version: int


@dataclass(frozen=True, slots=True)
class WorkspaceReadModel:
    id: WorkspaceId
    project_id: ProjectId
    name: str
    locator: str | None
    lifecycle_status: LifecycleStatus
    created_by: ActorId
    created_at: datetime
    row_version: int
