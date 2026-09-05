"""Application read models that do not expose persistence ORM objects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from researchbase.domain.artifact import ArtifactId, ArtifactVersionId
from researchbase.domain.claim import (
    ClaimId,
    ClaimVersionId,
    EvidenceRelationId,
    EvidenceRelationType,
)
from researchbase.domain.evidence import DatasetId, DatasetSnapshotId
from researchbase.domain.experiment import ExperimentSpecId, ExperimentSpecVersionId
from researchbase.domain.identity import ActorType
from researchbase.domain.measurement import MeasurementId
from researchbase.domain.metric import MetricDefinitionId, MetricDefinitionVersionId
from researchbase.domain.organization import LifecycleStatus, ProjectId, WorkspaceId
from researchbase.domain.research import (
    HypothesisId,
    HypothesisVersionId,
    ResearchQuestionId,
    ResearchQuestionVersionId,
)
from researchbase.domain.run import (
    ArtifactInputRole,
    DatasetInputRole,
    RunId,
    RunStatus,
)
from researchbase.domain.statistical_result import StatisticalResultId
from researchbase.foundation.hashing import ContentHash
from researchbase.foundation.ids import ActorId
from researchbase.foundation.versioning import VersionStatus


class WriteResult(BaseModel):
    """Stable internal envelope for Application write consumers."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    version_id: UUID | None = None
    content_hash: str | None = None
    row_version: int | None = None
    server_timestamp: datetime

    @field_validator("server_timestamp")
    @classmethod
    def _utc_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("server_timestamp must be UTC-aware")
        return value.astimezone(UTC)


def write_result(value: Any, server_timestamp: datetime) -> WriteResult:
    """Convert a typed Application read model into the shared write envelope."""

    if not hasattr(value, "id"):
        raise TypeError("write result value must expose an id")
    version_id = getattr(value, "version_id", None)
    if version_id is None and hasattr(value, "version_number"):
        version_id = value.id
    if version_id is None:
        version_id = getattr(value, "current_version_id", None)
    content_hash = getattr(value, "content_hash", None)
    return WriteResult(
        id=UUID(str(value.id)),
        version_id=UUID(str(version_id)) if version_id is not None else None,
        content_hash=str(content_hash) if content_hash is not None else None,
        row_version=getattr(value, "row_version", None),
        server_timestamp=server_timestamp,
    )


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


@dataclass(frozen=True, slots=True)
class MetricDefinitionVersionReadModel:
    id: MetricDefinitionVersionId
    metric_definition_id: MetricDefinitionId
    version_number: int
    status: VersionStatus
    definition: object
    unit: str | None
    aggregation: str | None
    content_hash: ContentHash | None
    hash_scheme: str | None
    created_by: ActorId
    created_at: datetime
    frozen_at: datetime | None
    row_version: int


@dataclass(frozen=True, slots=True)
class MetricDefinitionReadModel:
    id: MetricDefinitionId
    project_id: ProjectId | None
    name: str
    created_by: ActorId
    created_at: datetime
    current_version_id: MetricDefinitionVersionId | None
    row_version: int


@dataclass(frozen=True, slots=True)
class MeasurementReadModel:
    id: MeasurementId
    run_id: RunId
    metric_definition_version_id: MetricDefinitionVersionId
    numeric_value: float | None
    structured_value: object | None
    unit: str | None
    evaluation_scope: object | None
    content_hash: ContentHash
    created_by: ActorId
    created_at: datetime


@dataclass(frozen=True, slots=True)
class StatisticalResultReadModel:
    id: StatisticalResultId
    project_id: ProjectId
    analysis_type: str
    result_payload: object
    analysis_definition: object
    content_hash: ContentHash
    created_by: ActorId
    created_at: datetime


@dataclass(frozen=True, slots=True)
class StatisticalResultInputReadModel:
    statistical_result_id: StatisticalResultId
    measurement_id: MeasurementId
    input_role: str
    ordinal: int


@dataclass(frozen=True, slots=True)
class ClaimReadModel:
    id: ClaimId
    project_id: ProjectId
    created_by: ActorId
    created_at: datetime
    current_version_id: ClaimVersionId
    row_version: int


@dataclass(frozen=True, slots=True)
class ClaimVersionReadModel:
    id: ClaimVersionId
    claim_id: ClaimId
    version_number: int
    status: VersionStatus
    statement: str
    scope: object | None
    qualification: str | None
    support_set_hash: ContentHash | None
    content_hash: ContentHash | None
    hash_scheme: str | None
    created_by: ActorId
    created_at: datetime
    frozen_at: datetime | None
    row_version: int


@dataclass(frozen=True, slots=True)
class EvidenceRelationReadModel:
    id: EvidenceRelationId
    claim_version_id: ClaimVersionId
    measurement_id: MeasurementId | None
    statistical_result_id: StatisticalResultId | None
    relation_type: EvidenceRelationType
    qualification: str | None
    created_by: ActorId
    created_at: datetime


@dataclass(frozen=True, slots=True)
class RunReadModel:
    id: RunId
    project_id: ProjectId
    experiment_spec_version_id: ExperimentSpecVersionId
    run_type: str
    status: RunStatus
    inputs_sealed_at: datetime | None
    started_at: datetime | None
    finished_at: datetime | None
    exit_code: int | None
    failure_reason: str | None
    created_by: ActorId
    created_at: datetime
    row_version: int


@dataclass(frozen=True, slots=True)
class RunDatasetInputReadModel:
    run_id: RunId
    dataset_snapshot_id: DatasetSnapshotId
    role: DatasetInputRole
    ordinal: int


@dataclass(frozen=True, slots=True)
class RunArtifactInputReadModel:
    run_id: RunId
    artifact_version_id: ArtifactVersionId
    role: ArtifactInputRole
    ordinal: int
