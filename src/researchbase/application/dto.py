"""Application read models that do not expose persistence ORM objects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from researchbase.domain.identity import ActorType
from researchbase.domain.organization import LifecycleStatus, ProjectId, WorkspaceId
from researchbase.domain.research import (
    HypothesisId,
    HypothesisVersionId,
    ResearchQuestionId,
    ResearchQuestionVersionId,
)
from researchbase.foundation.hashing import ContentHash
from researchbase.foundation.ids import ActorId
from researchbase.foundation.versioning import VersionStatus


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


@dataclass(frozen=True, slots=True)
class ResearchQuestionVersionReadModel:
    id: ResearchQuestionVersionId
    research_question_id: ResearchQuestionId
    version_number: int
    status: VersionStatus
    question_text: str
    scope: object | None
    rationale: str | None
    content_hash: ContentHash | None
    hash_scheme: str | None
    created_by: ActorId
    created_at: datetime
    frozen_at: datetime | None
    row_version: int


@dataclass(frozen=True, slots=True)
class ResearchQuestionReadModel:
    id: ResearchQuestionId
    project_id: ProjectId
    created_by: ActorId
    created_at: datetime
    current_version_id: ResearchQuestionVersionId
    row_version: int


@dataclass(frozen=True, slots=True)
class HypothesisVersionReadModel:
    id: HypothesisVersionId
    hypothesis_id: HypothesisId
    version_number: int
    status: VersionStatus
    statement: str
    expected_direction: str | None
    success_criteria: object | None
    rationale: str | None
    content_hash: ContentHash | None
    hash_scheme: str | None
    created_by: ActorId
    created_at: datetime
    frozen_at: datetime | None
    row_version: int


@dataclass(frozen=True, slots=True)
class HypothesisReadModel:
    id: HypothesisId
    project_id: ProjectId
    research_question_id: ResearchQuestionId | None
    created_by: ActorId
    created_at: datetime
    current_version_id: HypothesisVersionId
    row_version: int
