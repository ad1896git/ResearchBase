"""Application read models that do not expose persistence ORM objects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from researchbase.domain.artifact import ArtifactId, ArtifactVersionId
from researchbase.domain.evidence import DatasetId, DatasetSnapshotId
from researchbase.domain.experiment import ExperimentSpecId, ExperimentSpecVersionId
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


@dataclass(frozen=True, slots=True)
class ExperimentSpecVersionReadModel:
    id: ExperimentSpecVersionId
    experiment_spec_id: ExperimentSpecId
    version_number: int
    status: VersionStatus
    title: str
    objective: str
    protocol: object
    planned_metrics: object | None
    seed_policy: object | None
    analysis_plan: object | None
    content_hash: ContentHash | None
    hash_scheme: str | None
    created_by: ActorId
    created_at: datetime
    frozen_at: datetime | None
    row_version: int


@dataclass(frozen=True, slots=True)
class ExperimentSpecReadModel:
    id: ExperimentSpecId
    project_id: ProjectId
    hypothesis_id: HypothesisId | None
    created_by: ActorId
    created_at: datetime
    current_version_id: ExperimentSpecVersionId
    row_version: int


@dataclass(frozen=True, slots=True)
class DatasetReadModel:
    id: DatasetId
    project_id: ProjectId | None
    name: str
    description: str | None
    source_locator: str | None
    lifecycle_status: LifecycleStatus
    created_by: ActorId
    created_at: datetime
    row_version: int


@dataclass(frozen=True, slots=True)
class DatasetSnapshotReadModel:
    id: DatasetSnapshotId
    dataset_id: DatasetId
    manifest_hash: ContentHash
    selection_definition: object
    manifest_locator: str | None
    content_hash: ContentHash
    created_by: ActorId
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ArtifactReadModel:
    id: ArtifactId
    project_id: ProjectId | None
    artifact_type: str
    name: str
    description: str | None
    current_version_id: ArtifactVersionId | None
    created_by: ActorId
    created_at: datetime
    row_version: int


@dataclass(frozen=True, slots=True)
class ArtifactVersionReadModel:
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
    frozen_at: datetime | None
    row_version: int
