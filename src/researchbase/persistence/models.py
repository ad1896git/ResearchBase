"""SQLAlchemy persistence models for the PR-02 identity slice."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CHAR,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, DOUBLE_PRECISION, JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from researchbase.domain.claim import EvidenceRelationType
from researchbase.domain.governance import (
    AuditFindingSeverity,
    AuditFindingStatus,
    CorrectionType,
    GovernanceTargetType,
    ImpactAssessmentConclusion,
    ImpactKind,
)
from researchbase.domain.identity import ActorType
from researchbase.domain.organization import LifecycleStatus
from researchbase.persistence.database import Base
from researchbase.persistence.enum_codec import PersistedCanonicalEnum


class ActorModel(Base):
    __tablename__ = "actors"
    __table_args__ = (
        CheckConstraint("actor_type IN ('HUMAN', 'AGENT', 'SERVICE')", name="ck_actors_actor_type"),
        Index(
            "uq_actors_external_key",
            "external_key",
            unique=True,
            postgresql_where=text("external_key IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    actor_type: Mapped[str] = mapped_column(PersistedCanonicalEnum(ActorType, 16), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    external_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    row_version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1"), default=1
    )


class ProjectModel(Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint(
            "lifecycle_status IN ('ACTIVE', 'ARCHIVED', 'RETIRED')",
            name="ck_projects_lifecycle_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    lifecycle_status: Mapped[str] = mapped_column(
        PersistedCanonicalEnum(LifecycleStatus, 20),
        nullable=False,
        server_default=text("'ACTIVE'"),
    )
    created_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    row_version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1"), default=1
    )


class WorkspaceModel(Base):
    __tablename__ = "workspaces"
    __table_args__ = (
        CheckConstraint(
            "lifecycle_status IN ('ACTIVE', 'ARCHIVED', 'RETIRED')",
            name="ck_workspaces_lifecycle_status",
        ),
        Index("uq_workspaces_project_name", "project_id", "name", unique=True),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    project_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    locator: Mapped[str | None] = mapped_column(Text, nullable=True)
    lifecycle_status: Mapped[str] = mapped_column(
        PersistedCanonicalEnum(LifecycleStatus, 20),
        nullable=False,
        server_default=text("'ACTIVE'"),
    )
    created_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    row_version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1"), default=1
    )


class ResearchQuestionModel(Base):
    __tablename__ = "research_questions"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    project_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False
    )
    current_version_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("research_question_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    created_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    row_version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1"), default=1
    )


class ResearchQuestionVersionModel(Base):
    __tablename__ = "research_question_versions"
    __table_args__ = (
        CheckConstraint("version_number > 0", name="ck_research_question_versions_version_number"),
        CheckConstraint(
            "status IN ('DRAFT', 'FROZEN', 'SUPERSEDED', 'ABANDONED')",
            name="ck_research_question_versions_status",
        ),
        UniqueConstraint(
            "research_question_id",
            "version_number",
            name="uq_research_question_versions_parent_version",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    research_question_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("research_questions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[object | None] = mapped_column(JSONB, nullable=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(CHAR(64), nullable=True)
    created_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    row_version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1"), default=1
    )


class HypothesisModel(Base):
    __tablename__ = "hypotheses"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    project_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False
    )
    research_question_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("research_questions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    current_version_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("hypothesis_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    created_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    row_version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1"), default=1
    )


class HypothesisVersionModel(Base):
    __tablename__ = "hypothesis_versions"
    __table_args__ = (
        CheckConstraint("version_number > 0", name="ck_hypothesis_versions_version_number"),
        CheckConstraint(
            "status IN ('DRAFT', 'FROZEN', 'SUPERSEDED', 'ABANDONED')",
            name="ck_hypothesis_versions_status",
        ),
        UniqueConstraint(
            "hypothesis_id", "version_number", name="uq_hypothesis_versions_parent_version"
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    hypothesis_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("hypotheses.id", ondelete="RESTRICT"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    expected_direction: Mapped[str | None] = mapped_column(String(64), nullable=True)
    success_criteria: Mapped[object | None] = mapped_column(JSONB, nullable=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(CHAR(64), nullable=True)
    created_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    row_version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1"), default=1
    )


class ExperimentSpecModel(Base):
    __tablename__ = "experiment_specs"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    project_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False
    )
    hypothesis_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("hypotheses.id", ondelete="RESTRICT"),
        nullable=True,
    )
    current_version_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("experiment_spec_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    created_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    row_version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1"), default=1
    )


class ExperimentSpecVersionModel(Base):
    __tablename__ = "experiment_spec_versions"
    __table_args__ = (
        CheckConstraint("version_number > 0", name="ck_experiment_spec_versions_version_number"),
        CheckConstraint(
            "status IN ('DRAFT', 'FROZEN', 'SUPERSEDED', 'ABANDONED')",
            name="ck_experiment_spec_versions_status",
        ),
        UniqueConstraint(
            "experiment_spec_id",
            "version_number",
            name="uq_experiment_spec_versions_parent_version",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    experiment_spec_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("experiment_specs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    protocol: Mapped[object] = mapped_column(JSONB, nullable=False)
    planned_metrics: Mapped[object | None] = mapped_column(JSONB, nullable=True)
    seed_policy: Mapped[object | None] = mapped_column(JSONB, nullable=True)
    analysis_plan: Mapped[object | None] = mapped_column(JSONB, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(CHAR(64), nullable=True)
    created_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    row_version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1"), default=1
    )


class DatasetModel(Base):
    __tablename__ = "datasets"
    __table_args__ = (
        CheckConstraint(
            "lifecycle_status IN ('ACTIVE', 'ARCHIVED', 'RETIRED')",
            name="ck_datasets_lifecycle_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    project_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_locator: Mapped[str | None] = mapped_column(Text, nullable=True)
    lifecycle_status: Mapped[str] = mapped_column(
        PersistedCanonicalEnum(LifecycleStatus, 20),
        nullable=False,
        server_default=text("'ACTIVE'"),
    )
    created_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    row_version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1"), default=1
    )


class DatasetSnapshotModel(Base):
    __tablename__ = "dataset_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "dataset_id", "content_hash", name="uq_dataset_snapshots_dataset_content_hash"
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    dataset_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("datasets.id", ondelete="RESTRICT"), nullable=False
    )
    manifest_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    selection_definition: Mapped[object] = mapped_column(JSONB, nullable=False)
    manifest_locator: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    created_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ArtifactModel(Base):
    __tablename__ = "artifacts"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    project_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=True
    )
    artifact_type: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_version_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("artifact_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    created_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    row_version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1"), default=1
    )


class ArtifactVersionModel(Base):
    __tablename__ = "artifact_versions"
    __table_args__ = (
        CheckConstraint("version_number > 0", name="ck_artifact_versions_version_number"),
        CheckConstraint(
            "status IN ('DRAFT', 'FROZEN', 'SUPERSEDED', 'ABANDONED')",
            name="ck_artifact_versions_status",
        ),
        CheckConstraint(
            "byte_size IS NULL OR byte_size >= 0", name="ck_artifact_versions_byte_size"
        ),
        UniqueConstraint(
            "artifact_id", "version_number", name="uq_artifact_versions_artifact_version"
        ),
        UniqueConstraint(
            "artifact_id", "content_hash", name="uq_artifact_versions_artifact_content_hash"
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    artifact_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("artifacts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    locator: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    byte_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    content_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    metadata_json: Mapped[object | None] = mapped_column("metadata", JSONB, nullable=True)
    created_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    row_version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1"), default=1
    )


class MetricDefinitionModel(Base):
    __tablename__ = "metric_definitions"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    project_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    current_version_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=True
    )
    created_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    row_version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1"), default=1
    )


class MetricDefinitionVersionModel(Base):
    __tablename__ = "metric_definition_versions"
    __table_args__ = (
        CheckConstraint("version_number > 0", name="ck_metric_definition_versions_version_number"),
        CheckConstraint(
            "status IN ('DRAFT', 'FROZEN', 'SUPERSEDED', 'ABANDONED')",
            name="ck_metric_definition_versions_status",
        ),
        UniqueConstraint(
            "metric_definition_id",
            "version_number",
            name="uq_metric_definition_versions_parent_version",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    metric_definition_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("metric_definitions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    definition: Mapped[object] = mapped_column(JSONB, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    aggregation: Mapped[str | None] = mapped_column(String(64), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(CHAR(64), nullable=True)
    created_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    row_version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1"), default=1
    )


class RunModel(Base):
    __tablename__ = "runs"
    __table_args__ = (
        UniqueConstraint("id", "project_id", name="pr316_run_project_uq"),
        CheckConstraint(
            "status IN ('PLANNED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'CANCELLED')",
            name="ck_runs_status",
        ),
        CheckConstraint(
            "(status = 'PLANNED' AND inputs_sealed_at IS NULL) OR "
            "(status <> 'PLANNED' AND inputs_sealed_at IS NOT NULL)",
            name="ck_runs_inputs_sealed",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    project_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False
    )
    experiment_spec_version_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("experiment_spec_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    run_type: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default=text("'experiment'")
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    inputs_sealed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    row_version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1"), default=1
    )


class RunDatasetInputModel(Base):
    __tablename__ = "run_dataset_inputs"
    __table_args__ = (
        CheckConstraint(
            "role IN ('train', 'validation', 'test', 'calibration', 'auxiliary', 'other')",
            name="ck_run_dataset_inputs_role",
        ),
    )

    run_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("runs.id", ondelete="RESTRICT"), primary_key=True
    )
    dataset_snapshot_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("dataset_snapshots.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    role: Mapped[str] = mapped_column(String(32), primary_key=True)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))


class RunArtifactInputModel(Base):
    __tablename__ = "run_artifact_inputs"
    __table_args__ = (
        CheckConstraint(
            "role IN ('source_code', 'model', 'checkpoint', 'configuration', "
            "'environment_manifest', 'script', 'dependency_lock', 'other')",
            name="ck_run_artifact_inputs_role",
        ),
    )

    run_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("runs.id", ondelete="RESTRICT"), primary_key=True
    )
    artifact_version_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("artifact_versions.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    role: Mapped[str] = mapped_column(String(32), primary_key=True)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))


class MeasurementModel(Base):
    __tablename__ = "measurements"
    __table_args__ = (
        CheckConstraint(
            "(numeric_value IS NOT NULL AND structured_value IS NULL) OR "
            "(numeric_value IS NULL AND structured_value IS NOT NULL)",
            name="ck_measurements_value_xor",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    run_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("runs.id", ondelete="RESTRICT"), nullable=False
    )
    metric_definition_version_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("metric_definition_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    numeric_value: Mapped[float | None] = mapped_column(DOUBLE_PRECISION(), nullable=True)
    structured_value: Mapped[object | None] = mapped_column(JSONB(none_as_null=True), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evaluation_scope: Mapped[object | None] = mapped_column(JSONB(none_as_null=True), nullable=True)
    content_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    created_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StatisticalResultModel(Base):
    __tablename__ = "statistical_results"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    project_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False
    )
    analysis_type: Mapped[str] = mapped_column(String(64), nullable=False)
    result_payload: Mapped[object] = mapped_column(JSONB(), nullable=False)
    analysis_definition: Mapped[object] = mapped_column(JSONB(), nullable=False)
    content_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    created_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StatisticalResultInputModel(Base):
    __tablename__ = "statistical_result_inputs"

    statistical_result_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("statistical_results.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    measurement_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("measurements.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    input_role: Mapped[str] = mapped_column(
        String(32), primary_key=True, server_default=text("'input'")
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))


class ClaimModel(Base):
    __tablename__ = "claims"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    project_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False
    )
    current_version_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("claim_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    created_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    row_version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1"), default=1
    )


class ClaimVersionModel(Base):
    __tablename__ = "claim_versions"
    __table_args__ = (
        CheckConstraint("version_number > 0", name="ck_claim_versions_version_number"),
        CheckConstraint(
            "status IN ('DRAFT', 'FROZEN', 'SUPERSEDED', 'ABANDONED')",
            name="ck_claim_versions_status",
        ),
        UniqueConstraint("claim_id", "version_number", name="uq_claim_versions_parent_version"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    claim_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("claims.id", ondelete="RESTRICT"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[object | None] = mapped_column(JSONB, nullable=True)
    qualification: Mapped[str | None] = mapped_column(Text, nullable=True)
    support_set_hash: Mapped[str | None] = mapped_column(CHAR(64), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(CHAR(64), nullable=True)
    created_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    row_version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1"), default=1
    )


class EvidenceRelationModel(Base):
    __tablename__ = "evidence_relations"
    __table_args__ = (
        CheckConstraint(
            "relation_type IN ('SUPPORTS', 'CONTRADICTS', 'QUALIFIES', 'CONTEXT')",
            name="ck_evidence_relations_relation_type",
        ),
        CheckConstraint(
            "(measurement_id IS NOT NULL AND statistical_result_id IS NULL) OR "
            "(measurement_id IS NULL AND statistical_result_id IS NOT NULL)",
            name="ck_evidence_relations_source_xor",
        ),
        Index(
            "uq_evidence_measurement",
            "claim_version_id",
            "measurement_id",
            "relation_type",
            unique=True,
            postgresql_where=text("measurement_id IS NOT NULL"),
        ),
        Index(
            "uq_evidence_stat",
            "claim_version_id",
            "statistical_result_id",
            "relation_type",
            unique=True,
            postgresql_where=text("statistical_result_id IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    claim_version_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("claim_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    measurement_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("measurements.id", ondelete="RESTRICT"),
        nullable=True,
    )
    statistical_result_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("statistical_results.id", ondelete="RESTRICT"),
        nullable=True,
    )
    relation_type: Mapped[str] = mapped_column(
        PersistedCanonicalEnum(EvidenceRelationType, 32), nullable=False
    )
    qualification: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuditFindingModel(Base):
    __tablename__ = "audit_findings"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('INFO','MINOR','MAJOR','CRITICAL')",
            name="ck_audit_findings_severity",
        ),
        CheckConstraint(
            "status IN ('OPEN','CONFIRMED','DISMISSED','RESOLVED')",
            name="ck_audit_findings_status",
        ),
        CheckConstraint(
            "target_type IN ("
            "'EXPERIMENT_SPEC_VERSION','DATASET_SNAPSHOT','ARTIFACT_VERSION','RUN',"
            "'METRIC_DEFINITION_VERSION','MEASUREMENT','STATISTICAL_RESULT','CLAIM_VERSION')",
            name="ck_audit_findings_target_type",
        ),
        Index("ix_audit_findings_project", "project_id"),
        Index("ix_audit_findings_target", "project_id", "target_type", "target_id"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    project_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False
    )
    finding_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(
        PersistedCanonicalEnum(AuditFindingSeverity, 16), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    target_type: Mapped[str] = mapped_column(
        PersistedCanonicalEnum(GovernanceTargetType, 64), nullable=False
    )
    target_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    target_content_hash: Mapped[str | None] = mapped_column(CHAR(64), nullable=True)
    status: Mapped[str] = mapped_column(
        PersistedCanonicalEnum(AuditFindingStatus, 20),
        nullable=False,
        server_default=text("'OPEN'"),
    )
    created_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    row_version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1"), default=1
    )


class ImpactAssessmentModel(Base):
    __tablename__ = "impact_assessments"
    __table_args__ = (
        CheckConstraint(
            "conclusion IN ('NO_IMPACT','STALE','INVALID','REQUIRES_REVIEW','UNKNOWN')",
            name="ck_impact_assessments_conclusion",
        ),
        Index("ix_impact_assessments_project", "project_id"),
        Index("ix_impact_assessments_finding", "audit_finding_id"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    project_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False
    )
    audit_finding_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("audit_findings.id", ondelete="RESTRICT"),
        nullable=True,
    )
    assessment_payload: Mapped[object] = mapped_column(JSONB, nullable=False)
    conclusion: Mapped[str] = mapped_column(
        PersistedCanonicalEnum(ImpactAssessmentConclusion, 32), nullable=False
    )
    created_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    content_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)


class ImpactTargetModel(Base):
    __tablename__ = "impact_targets"
    __table_args__ = (
        CheckConstraint(
            "impact_kind IN ('DIRECT','DOWNSTREAM','STALE','INVALID','REQUIRES_REVIEW')",
            name="ck_impact_targets_kind",
        ),
        CheckConstraint(
            "target_type IN ("
            "'EXPERIMENT_SPEC_VERSION','DATASET_SNAPSHOT','ARTIFACT_VERSION','RUN',"
            "'METRIC_DEFINITION_VERSION','MEASUREMENT','STATISTICAL_RESULT','CLAIM_VERSION')",
            name="ck_impact_targets_target_type",
        ),
        Index("ix_impact_targets_target", "target_type", "target_id"),
    )

    impact_assessment_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("impact_assessments.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    target_type: Mapped[str] = mapped_column(
        PersistedCanonicalEnum(GovernanceTargetType, 64), primary_key=True
    )
    target_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    target_content_hash: Mapped[str | None] = mapped_column(CHAR(64), nullable=True)
    impact_kind: Mapped[str] = mapped_column(PersistedCanonicalEnum(ImpactKind, 32), nullable=False)


class CorrectionRecordModel(Base):
    __tablename__ = "correction_records"
    __table_args__ = (
        CheckConstraint(
            "correction_type IN ('FACTUAL','METADATA','COMPUTATIONAL','ATTRIBUTION','OTHER')",
            name="ck_correction_records_type",
        ),
        CheckConstraint(
            "target_type IN ("
            "'EXPERIMENT_SPEC_VERSION','DATASET_SNAPSHOT','ARTIFACT_VERSION','RUN',"
            "'METRIC_DEFINITION_VERSION','MEASUREMENT','STATISTICAL_RESULT','CLAIM_VERSION')",
            name="ck_correction_records_target_type",
        ),
        Index(
            "ix_correction_records_target",
            "project_id",
            "target_type",
            "target_id",
            "created_at",
            "id",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    project_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False
    )
    target_type: Mapped[str] = mapped_column(
        PersistedCanonicalEnum(GovernanceTargetType, 64), nullable=False
    )
    target_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    target_content_hash: Mapped[str | None] = mapped_column(CHAR(64), nullable=True)
    correction_type: Mapped[str] = mapped_column(
        PersistedCanonicalEnum(CorrectionType, 32), nullable=False
    )
    corrected_assertion: Mapped[object] = mapped_column(JSONB, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    content_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)


class LiteratureSearchPlanModel(Base):
    __tablename__ = "literature_search_plans"
    __table_args__ = (
        UniqueConstraint("project_id", "id", name="uq_literature_search_plans_project_id"),
        UniqueConstraint("id", "current_version_id", name="uq_lsp_id_current_version"),
        ForeignKeyConstraint(
            ["id", "current_version_id"],
            ["literature_search_plan_versions.plan_id", "literature_search_plan_versions.id"],
            name="fk_lsp_current_version_same_plan",
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    project_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False
    )
    current_version_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True))
    created_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))


class LiteratureSearchPlanVersionModel(Base):
    __tablename__ = "literature_search_plan_versions"
    __table_args__ = (
        CheckConstraint("version_number > 0", name="ck_lspv_version_number"),
        CheckConstraint(
            "status IN ('DRAFT','FROZEN','SUPERSEDED','ABANDONED')", name="ck_lspv_status"
        ),
        UniqueConstraint("plan_id", "version_number", name="uq_lspv_plan_version"),
        UniqueConstraint("plan_id", "id", name="uq_lspv_plan_id"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    plan_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("literature_search_plans.id", ondelete="RESTRICT"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    source_scope: Mapped[str] = mapped_column(String(32), nullable=False)
    inclusion_criteria: Mapped[object | None] = mapped_column(JSONB)
    exclusion_criteria: Mapped[object | None] = mapped_column(JSONB)
    time_range: Mapped[object | None] = mapped_column(JSONB)
    language_scope: Mapped[list[str] | None] = mapped_column(JSONB)
    search_strategy: Mapped[str] = mapped_column(String(32), nullable=False)
    planned_providers: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    stopping_rule: Mapped[object | None] = mapped_column(JSONB)
    content_hash: Mapped[str | None] = mapped_column(CHAR(64))
    hash_scheme: Mapped[str] = mapped_column(String(32), nullable=False)
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))


class SearchPlanQuestionInputModel(Base):
    __tablename__ = "search_plan_question_inputs"
    __table_args__ = (
        CheckConstraint("ordinal >= 0", name="ck_spqi_ordinal"),
        UniqueConstraint("plan_version_id", "ordinal", name="uq_spqi_ordinal"),
    )

    plan_version_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("literature_search_plan_versions.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    research_question_version_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("research_question_versions.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)


class LiteratureSearchPlanCommandReceiptModel(Base):
    __tablename__ = "literature_search_plan_command_receipts"
    __table_args__ = (
        UniqueConstraint(
            "deployment_id",
            "actor_id",
            "project_id",
            "command_name",
            "request_id",
            name="uq_lsp_receipt_scope",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    deployment_id: Mapped[str] = mapped_column(String(255), nullable=False)
    actor_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    project_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False
    )
    command_name: Mapped[str] = mapped_column(String(64), nullable=False)
    request_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    request_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    hash_scheme: Mapped[str] = mapped_column(String(32), nullable=False)
    result_plan_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("literature_search_plans.id", ondelete="RESTRICT"),
        nullable=False,
    )
    result_plan_version_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("literature_search_plan_versions.id", ondelete="RESTRICT"),
    )
    result_dto_version: Mapped[int] = mapped_column(Integer, nullable=False)
    result_dto: Mapped[object] = mapped_column(JSONB, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LiteratureSearchExecutionModel(Base):
    __tablename__ = "literature_search_executions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PLANNED','RUNNING','SUCCEEDED','FAILED','CANCELLED','UNKNOWN')",
            name="ck_lse_status",
        ),
        CheckConstraint("row_version > 0", name="ck_lse_row_version"),
        CheckConstraint(
            "strategy_id = 'explicit_queries' AND strategy_version = '1'",
            name="ck_lse_strategy",
        ),
        CheckConstraint(
            "started_at IS NULL OR finished_at IS NULL OR finished_at >= started_at",
            name="ck_lse_finished_after_start",
        ),
        UniqueConstraint("project_id", "idempotency_key", name="uq_lse_project_idempotency"),
        UniqueConstraint("project_id", "id", name="uq_lse_project_id"),
        Index("ix_lse_project_created", "project_id", "created_at", "id"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    project_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False
    )
    search_plan_version_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("literature_search_plan_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    strategy_id: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="PLANNED")
    requested_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    executed_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    execution_context: Mapped[object] = mapped_column(JSONB, nullable=False)
    idempotency_key: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    failure_code: Mapped[str | None] = mapped_column(String(64))
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    created_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LiteratureSearchQueryRecordModel(Base):
    __tablename__ = "search_query_records"
    __table_args__ = (
        UniqueConstraint("provider_attempt_id", name="uq_sqrec_provider_attempt"),
        UniqueConstraint(
            "literature_search_execution_id", "ordinal", name="uq_sqr_execution_ordinal"
        ),
        UniqueConstraint(
            "literature_search_execution_id", "query_hash", name="uq_sqr_execution_hash"
        ),
        CheckConstraint("ordinal >= 0", name="ck_sqr_ordinal"),
        ForeignKeyConstraint(
            ["literature_search_execution_id", "provider_attempt_id"],
            [
                "literature_search_provider_attempts.execution_id",
                "literature_search_provider_attempts.id",
            ],
            name="fk_sqr_attempt_same_execution",
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    literature_search_execution_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("literature_search_executions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    provider_attempt_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    perspective: Mapped[str | None] = mapped_column(Text)
    provider_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_version: Mapped[str | None] = mapped_column(String(128))
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    query_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    hash_scheme: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="sha256-cjson-v1"
    )
    created_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LiteratureSearchProviderAttemptModel(Base):
    __tablename__ = "literature_search_provider_attempts"
    __table_args__ = (
        UniqueConstraint(
            "execution_id", "query_index", "attempt_number", name="uq_lspa_attempt_number"
        ),
        CheckConstraint("query_index >= 0", name="ck_lspa_query_index"),
        CheckConstraint("attempt_number > 0", name="ck_lspa_attempt_number"),
        CheckConstraint("provider_request_key = id", name="ck_lspa_request_key_is_attempt_id"),
        CheckConstraint("row_version > 0", name="ck_lspa_row_version"),
        CheckConstraint(
            "retry_after_seconds IS NULL OR retry_after_seconds >= 0",
            name="ck_lspa_retry_after",
        ),
        CheckConstraint("result_count IS NULL OR result_count >= 0", name="ck_lspa_result_count"),
        CheckConstraint("deadline_at > reserved_at", name="ck_lspa_deadline_after_reserve"),
        CheckConstraint(
            "recovery_after = deadline_at + interval '30 seconds'",
            name="ck_lspa_recovery_after_deadline",
        ),
        CheckConstraint(
            "(status = 'RESERVED' AND completed_at IS NULL AND delivery_certainty IS NULL "
            "AND failure_code IS NULL AND result_count IS NULL AND query_record_id IS NULL "
            "AND invoked_at IS NULL AND returned_at IS NULL AND provider_request_id IS NULL "
            "AND retry_after_seconds IS NULL AND warning_codes IS NULL) OR "
            "(status = 'SUCCEEDED' AND completed_at IS NOT NULL AND invoked_at IS NOT NULL "
            "AND returned_at IS NOT NULL AND delivery_certainty = 'RESPONSE_RECEIVED' "
            "AND failure_code IS NULL AND result_count IS NOT NULL AND query_record_id IS NOT NULL "
            "AND warning_codes IS NOT NULL) OR "
            "(status IN ('RETRYABLE_FAILURE','PERMANENT_FAILURE','CANCELLED','UNKNOWN') "
            "AND completed_at IS NOT NULL AND delivery_certainty IS NOT NULL "
            "AND failure_code IS NOT NULL AND result_count = 0 AND warning_codes IS NOT NULL "
            "AND ((invoked_at IS NULL AND query_record_id IS NULL) OR "
            "(invoked_at IS NOT NULL AND query_record_id IS NOT NULL)))",
            name="ck_lspa_outcome_shape",
        ),
        CheckConstraint(
            "status IN ('RESERVED','SUCCEEDED','RETRYABLE_FAILURE','PERMANENT_FAILURE',"
            "'CANCELLED','UNKNOWN')",
            name="ck_lspa_status",
        ),
        UniqueConstraint("execution_id", "id", name="uq_lspa_execution_id"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    execution_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("literature_search_executions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    query_index: Mapped[int] = mapped_column(Integer, nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    provider_request_key: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    reserved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recovery_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="RESERVED")
    query_record_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "search_query_records.id",
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
    )
    invoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivery_certainty: Mapped[str | None] = mapped_column(String(24))
    provider_request_id: Mapped[str | None] = mapped_column(String(256))
    failure_code: Mapped[str | None] = mapped_column(String(64))
    retry_after_seconds: Mapped[int | None] = mapped_column(Integer)
    warning_codes: Mapped[object | None] = mapped_column(JSONB)
    result_count: Mapped[int | None] = mapped_column(Integer)
    row_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    created_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LiteratureSearchResultRecordModel(Base):
    __tablename__ = "search_result_records"
    __table_args__ = (
        UniqueConstraint("search_query_record_id", "rank", name="uq_srr_query_rank"),
        CheckConstraint("rank >= 0", name="ck_srr_rank"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    search_query_record_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("search_query_records.id", ondelete="RESTRICT"),
        nullable=False,
    )
    external_identifier: Mapped[str | None] = mapped_column(String(1024))
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(2048), nullable=False)
    url: Mapped[str | None] = mapped_column(String(4096))
    snippet: Mapped[str | None] = mapped_column(String(4096))
    provider_score: Mapped[object | None] = mapped_column(Numeric())
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    content_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    hash_scheme: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="sha256-cjson-v1"
    )
    created_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LiteratureSearchExecutionEventModel(Base):
    __tablename__ = "literature_search_execution_events"
    __table_args__ = (
        UniqueConstraint("execution_id", "sequence", name="uq_lsee_execution_sequence"),
        UniqueConstraint("execution_id", "new_row_version", name="uq_lsee_mutation_coordinate"),
        CheckConstraint("sequence >= 0", name="ck_lsee_sequence"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    execution_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("literature_search_executions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    attempt_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("literature_search_provider_attempts.id", ondelete="RESTRICT"),
    )
    prior_status: Mapped[str | None] = mapped_column(String(16))
    new_status: Mapped[str] = mapped_column(String(16), nullable=False)
    prior_row_version: Mapped[int | None] = mapped_column(Integer)
    new_row_version: Mapped[int] = mapped_column(Integer, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LiteratureSearchExecutionCommandReceiptModel(Base):
    __tablename__ = "literature_search_execution_command_receipts"
    __table_args__ = (
        UniqueConstraint(
            "deployment_id",
            "actor_id",
            "project_id",
            "command_name",
            "request_id",
            name="uq_lse_receipt_scope",
        ),
        ForeignKeyConstraint(
            ["project_id", "result_execution_id"],
            ["literature_search_executions.project_id", "literature_search_executions.id"],
            name="fk_lse_receipt_execution_same_project",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "jsonb_typeof(result_dto) = 'object' AND "
            "result_dto->>'execution_id' = result_execution_id::text AND "
            "result_dto->>'command_name' = command_name AND "
            "jsonb_typeof(result_dto->'accepted_at') = 'string' AND "
            "jsonb_typeof(result_dto->'accepted_row_version') = 'number' AND "
            "(result_dto->>'accepted_row_version')::integer > 0 AND "
            "result_dto ?& ARRAY['execution_id','command_name','accepted_at',"
            "'accepted_row_version'] AND result_dto - "
            "ARRAY['execution_id','command_name','accepted_at','accepted_row_version'] "
            "= '{}'::jsonb",
            name="ck_lse_receipt_admission_dto",
        ),
        CheckConstraint("length(btrim(deployment_id)) > 0", name="ck_lse_receipt_deployment"),
        CheckConstraint("hash_scheme = 'sha256-cjson-v1'", name="ck_lse_receipt_hash_scheme"),
        CheckConstraint("result_dto_version = 1", name="ck_lse_receipt_dto_version"),
        CheckConstraint("created_by = actor_id", name="ck_lse_receipt_actor_attribution"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    deployment_id: Mapped[str] = mapped_column(String(255), nullable=False)
    actor_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    project_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    command_name: Mapped[str] = mapped_column(String(48), nullable=False)
    request_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    request_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    hash_scheme: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="sha256-cjson-v1"
    )
    result_execution_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    result_dto_version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1")
    )
    result_dto: Mapped[object] = mapped_column(JSONB, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# PR3-01 planning tables: exact frozen constraints; no implicit ORM indexes.


class ResearchTasksModel(Base):
    __tablename__ = "research_tasks"
    __table_args__ = (
        CheckConstraint(
            "num_nonnulls(budget_policy_id, termination_policy_id, checkpoint_policy_id) IN (0,3)",
            name="pr304_policy_bundle",
        ),  # noqa: E501
        ForeignKeyConstraint(
            ["id", "budget_policy_id"],
            ["execution_budgets.research_task_id", "execution_budgets.id"],
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),  # noqa: E501
        ForeignKeyConstraint(
            ["id", "termination_policy_id"],
            ["termination_policies.research_task_id", "termination_policies.id"],
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),  # noqa: E501
        ForeignKeyConstraint(
            ["id", "checkpoint_policy_id"],
            ["checkpoint_policies.research_task_id", "checkpoint_policies.id"],
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),  # noqa: E501
        Index("pr304_tasks_checkpoint", "id", "checkpoint_policy_id"),
        Index("pr304_tasks_termination", "id", "termination_policy_id"),
        Index("pr304_tasks_budget", "id", "budget_policy_id"),
        CheckConstraint(
            "task_type IN ( 'LITERATURE_RESEARCH','HYPOTHESIS_GENERATION','EXPERIMENT_DESIGN', 'EXPERIMENT_EXECUTION','ANALYSIS','CLAIM_REVISION','MANUSCRIPT_DRAFTING', 'INTERNAL_REVIEW','END_TO_END_RESEARCH','REPLICATION','OTHER')"  # noqa: E501
        ),
        CheckConstraint(
            "length(btrim(objective)) BETWEEN 1 AND 8192 AND objective IS NFC NORMALIZED"
        ),
        CheckConstraint(
            "length(btrim(strategy_id)) > 0 AND strategy_id IS NFC NORMALIZED AND lower(btrim(strategy_id)) NOT IN ('latest','main','master')"  # noqa: E501
        ),
        CheckConstraint(
            "length(btrim(strategy_version)) > 0 AND strategy_version IS NFC NORMALIZED AND lower(btrim(strategy_version)) NOT IN ('latest','main','master')"  # noqa: E501
        ),
        CheckConstraint("autonomy_level IN ('A0','A1','A2','A3')"),
        CheckConstraint("status IN ('CREATED','PLANNING','CANCELLED')"),
        CheckConstraint("row_version >= 1"),
        UniqueConstraint("id", "project_id"),
        CheckConstraint("(started_at IS NULL AND current_step_id IS NULL"),
        CheckConstraint("((status = 'CANCELLED') = (finished_at IS NOT NULL)"),
        CheckConstraint("(finished_at IS NULL OR finished_at >= created_at"),
        CheckConstraint(
            "(plan_sealed_at IS NULL OR (status IN ('PLANNING','CANCELLED') AND plan_sealed_at >= created_at)"  # noqa: E501
        ),
        Index("pr301_tasks_project", "project_id", "created_at", "id"),
        Index("pr301_tasks_requester", "requested_by"),
        ForeignKeyConstraint(
            ["id", "current_step_id"],
            ["research_task_steps.research_task_id", "research_task_steps.id"],
            name="pr301_current_step_same_task",
            ondelete="RESTRICT",
        ),
    )
    id = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, nullable=False)
    project_id = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False
    )
    requested_by = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    task_type = mapped_column(Text, nullable=False)
    objective = mapped_column(Text, nullable=False)
    strategy_id = mapped_column(Text, nullable=False)
    strategy_version = mapped_column(Text, nullable=False)
    autonomy_level = mapped_column(Text, nullable=False)
    status = mapped_column(Text, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), nullable=False)
    started_at = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at = mapped_column(DateTime(timezone=True), nullable=True)
    plan_sealed_at = mapped_column(DateTime(timezone=True), nullable=True)
    current_step_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    row_version = mapped_column(Integer, nullable=False)

    budget_policy_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)

    termination_policy_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)

    checkpoint_policy_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)


class ResearchTaskStepsModel(Base):
    __tablename__ = "research_task_steps"
    __table_args__ = (
        CheckConstraint(
            "step_type IN ( 'PLAN','RESEARCH','RETRIEVE','HYPOTHESIZE','DESIGN_EXPERIMENT','CODE','DEBUG', 'EXECUTE','ANALYZE','CRITIQUE','WRITE','REVIEW','HUMAN_CHECKPOINT','PROMOTE','OTHER')"  # noqa: E501
        ),
        CheckConstraint("ordinal >= 1"),
        CheckConstraint("status IN ('PENDING','CANCELLED')"),
        CheckConstraint(
            "agent_role IS NULL OR (length(btrim(agent_role)) BETWEEN 1 AND 128 AND agent_role IS NFC NORMALIZED)"  # noqa: E501
        ),
        CheckConstraint(
            "capability_id IS NULL OR (length(btrim(capability_id)) BETWEEN 1 AND 128 AND capability_id IS NFC NORMALIZED)"  # noqa: E501
        ),
        CheckConstraint("retry_count = 0"),
        CheckConstraint("row_version >= 1"),
        UniqueConstraint("research_task_id", "id"),
        UniqueConstraint("research_task_id", "ordinal"),
        CheckConstraint("(parent_step_id IS DISTINCT FROM id"),
        CheckConstraint("(started_at IS NULL AND failure_code IS NULL"),
        CheckConstraint("((status = 'CANCELLED') = (finished_at IS NOT NULL)"),
        ForeignKeyConstraint(
            ["research_task_id", "parent_step_id"],
            ["research_task_steps.research_task_id", "research_task_steps.id"],
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        Index("pr301_steps_parent", "research_task_id", "parent_step_id"),
    )
    id = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, nullable=False)
    research_task_id = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("research_tasks.id", ondelete="RESTRICT"),
        nullable=False,
    )
    step_type = mapped_column(Text, nullable=False)
    ordinal = mapped_column(Integer, nullable=False)
    parent_step_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    status = mapped_column(Text, nullable=False)
    agent_role = mapped_column(Text, nullable=True)
    capability_id = mapped_column(Text, nullable=True)
    started_at = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at = mapped_column(DateTime(timezone=True), nullable=True)
    retry_count = mapped_column(Integer, nullable=False, server_default=text("0"))
    failure_code = mapped_column(Text, nullable=True)
    row_version = mapped_column(Integer, nullable=False)


class ResearchTaskStepDependenciesModel(Base):
    __tablename__ = "research_task_step_dependencies"
    __table_args__ = (
        PrimaryKeyConstraint("research_task_id", "predecessor_id", "dependent_id"),
        CheckConstraint("(predecessor_id <> dependent_id"),
        ForeignKeyConstraint(
            ["research_task_id", "predecessor_id"],
            ["research_task_steps.research_task_id", "research_task_steps.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["research_task_id", "dependent_id"],
            ["research_task_steps.research_task_id", "research_task_steps.id"],
            ondelete="RESTRICT",
        ),
        Index("pr301_dependency_reverse", "research_task_id", "dependent_id", "predecessor_id"),
    )
    research_task_id = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("research_tasks.id", ondelete="RESTRICT"),
        nullable=False,
    )
    predecessor_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    dependent_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)


class ResearchTaskInputsModel(Base):
    __tablename__ = "research_task_inputs"
    __table_args__ = (
        CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'"),
        CheckConstraint(
            "(num_nonnulls(research_question_version_id, hypothesis_version_id, claim_version_id, source_version_id, artifact_version_id, manuscript_version_id) = 1"  # noqa: E501
        ),
        CheckConstraint(
            "(CASE WHEN source_version_id IS NOT NULL OR manuscript_version_id IS NOT NULL THEN hash_scheme IS NOT NULL AND hash_scheme = 'sha256-cjson-v1' ELSE hash_scheme IS NULL END"  # noqa: E501
        ),
        Index(
            "pr301_ti_research_question",
            "research_task_id",
            "research_question_version_id",
            unique=True,
            postgresql_where=text("research_question_version_id IS NOT NULL"),
        ),
        Index(
            "pr301_ti_research_question_ref",
            "research_question_version_id",
            postgresql_where=text("research_question_version_id IS NOT NULL"),
        ),
        Index(
            "pr301_ti_hypothesis",
            "research_task_id",
            "hypothesis_version_id",
            unique=True,
            postgresql_where=text("hypothesis_version_id IS NOT NULL"),
        ),
        Index(
            "pr301_ti_hypothesis_ref",
            "hypothesis_version_id",
            postgresql_where=text("hypothesis_version_id IS NOT NULL"),
        ),
        Index(
            "pr301_ti_claim",
            "research_task_id",
            "claim_version_id",
            unique=True,
            postgresql_where=text("claim_version_id IS NOT NULL"),
        ),
        Index(
            "pr301_ti_claim_ref",
            "claim_version_id",
            postgresql_where=text("claim_version_id IS NOT NULL"),
        ),
        Index(
            "pr301_ti_source",
            "research_task_id",
            "source_version_id",
            unique=True,
            postgresql_where=text("source_version_id IS NOT NULL"),
        ),
        Index(
            "pr301_ti_source_ref",
            "source_version_id",
            postgresql_where=text("source_version_id IS NOT NULL"),
        ),
        Index(
            "pr301_ti_artifact",
            "research_task_id",
            "artifact_version_id",
            unique=True,
            postgresql_where=text("artifact_version_id IS NOT NULL"),
        ),
        Index(
            "pr301_ti_artifact_ref",
            "artifact_version_id",
            postgresql_where=text("artifact_version_id IS NOT NULL"),
        ),
        Index(
            "pr301_ti_manuscript",
            "research_task_id",
            "manuscript_version_id",
            unique=True,
            postgresql_where=text("manuscript_version_id IS NOT NULL"),
        ),
        Index(
            "pr301_ti_manuscript_ref",
            "manuscript_version_id",
            postgresql_where=text("manuscript_version_id IS NOT NULL"),
        ),
    )
    id = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, nullable=False)
    research_task_id = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("research_tasks.id", ondelete="RESTRICT"),
        nullable=False,
    )
    research_question_version_id = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("research_question_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    hypothesis_version_id = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("hypothesis_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    claim_version_id = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("claim_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    source_version_id = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("source_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    artifact_version_id = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("artifact_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    manuscript_version_id = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("manuscript_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    content_hash = mapped_column(Text, nullable=False)
    hash_scheme = mapped_column(Text, nullable=True)


class ResearchTaskStepInputsModel(Base):
    __tablename__ = "research_task_step_inputs"
    __table_args__ = (
        CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'"),
        CheckConstraint(
            "(num_nonnulls(research_question_version_id, hypothesis_version_id, claim_version_id, source_version_id, artifact_version_id, manuscript_version_id) = 1"  # noqa: E501
        ),
        CheckConstraint(
            "(CASE WHEN source_version_id IS NOT NULL OR manuscript_version_id IS NOT NULL THEN hash_scheme IS NOT NULL AND hash_scheme = 'sha256-cjson-v1' ELSE hash_scheme IS NULL END"  # noqa: E501
        ),
        ForeignKeyConstraint(
            ["research_task_id", "step_id"],
            ["research_task_steps.research_task_id", "research_task_steps.id"],
            ondelete="RESTRICT",
        ),
        Index(
            "pr301_si_research_question",
            "research_task_id",
            "step_id",
            "research_question_version_id",
            unique=True,
            postgresql_where=text("research_question_version_id IS NOT NULL"),
        ),
        Index(
            "pr301_si_research_question_ref",
            "research_question_version_id",
            postgresql_where=text("research_question_version_id IS NOT NULL"),
        ),
        Index(
            "pr301_si_hypothesis",
            "research_task_id",
            "step_id",
            "hypothesis_version_id",
            unique=True,
            postgresql_where=text("hypothesis_version_id IS NOT NULL"),
        ),
        Index(
            "pr301_si_hypothesis_ref",
            "hypothesis_version_id",
            postgresql_where=text("hypothesis_version_id IS NOT NULL"),
        ),
        Index(
            "pr301_si_claim",
            "research_task_id",
            "step_id",
            "claim_version_id",
            unique=True,
            postgresql_where=text("claim_version_id IS NOT NULL"),
        ),
        Index(
            "pr301_si_claim_ref",
            "claim_version_id",
            postgresql_where=text("claim_version_id IS NOT NULL"),
        ),
        Index(
            "pr301_si_source",
            "research_task_id",
            "step_id",
            "source_version_id",
            unique=True,
            postgresql_where=text("source_version_id IS NOT NULL"),
        ),
        Index(
            "pr301_si_source_ref",
            "source_version_id",
            postgresql_where=text("source_version_id IS NOT NULL"),
        ),
        Index(
            "pr301_si_artifact",
            "research_task_id",
            "step_id",
            "artifact_version_id",
            unique=True,
            postgresql_where=text("artifact_version_id IS NOT NULL"),
        ),
        Index(
            "pr301_si_artifact_ref",
            "artifact_version_id",
            postgresql_where=text("artifact_version_id IS NOT NULL"),
        ),
        Index(
            "pr301_si_manuscript",
            "research_task_id",
            "step_id",
            "manuscript_version_id",
            unique=True,
            postgresql_where=text("manuscript_version_id IS NOT NULL"),
        ),
        Index(
            "pr301_si_manuscript_ref",
            "manuscript_version_id",
            postgresql_where=text("manuscript_version_id IS NOT NULL"),
        ),
    )
    id = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, nullable=False)
    research_task_id = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("research_tasks.id", ondelete="RESTRICT"),
        nullable=False,
    )
    step_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    research_question_version_id = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("research_question_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    hypothesis_version_id = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("hypothesis_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    claim_version_id = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("claim_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    source_version_id = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("source_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    artifact_version_id = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("artifact_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    manuscript_version_id = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("manuscript_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    content_hash = mapped_column(Text, nullable=False)
    hash_scheme = mapped_column(Text, nullable=True)


class ResearchTaskCommandReceiptsModel(Base):
    __tablename__ = "research_task_command_receipts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["research_task_id", "project_id", "result_search_session_id"],
            [
                "experiment_search_sessions.research_task_id",
                "experiment_search_sessions.project_id",
                "experiment_search_sessions.id",
            ],
            name="pr316_receipt_session_fk",
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["research_task_id", "result_search_session_id", "result_search_node_id"],
            [
                "experiment_search_nodes.research_task_id",
                "experiment_search_nodes.search_session_id",
                "experiment_search_nodes.id",
            ],
            name="pr316_receipt_node_fk",
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["research_task_id", "result_search_session_id", "result_search_event_id"],
            [
                "experiment_search_events.research_task_id",
                "experiment_search_events.search_session_id",
                "experiment_search_events.id",
            ],
            name="pr316_receipt_event_fk",
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        CheckConstraint(
            "(pr316_command_event(command_name) IS NULL AND "
            "num_nonnulls(result_search_session_id,result_search_node_id,result_search_event_id)=0)"
            " OR (pr316_command_event(command_name) IS NOT NULL AND result_search_session_id "
            "IS NOT NULL AND result_search_event_id IS NOT NULL AND resulting_row_version>=2 "
            "AND ((command_name= 'create_search_session' AND result_search_node_id IS NULL) "
            "OR (command_name= 'append_search_node' AND result_search_node_id IS NOT NULL)))",
            name="pr316_receipt_shape_ck",
        ),
        Index(
            "pr316_receipt_session", "research_task_id", "project_id", "result_search_session_id"
        ),
        Index(
            "pr316_receipt_node",
            "research_task_id",
            "result_search_session_id",
            "result_search_node_id",
        ),
        Index(
            "pr316_receipt_event_scope",
            "research_task_id",
            "result_search_session_id",
            "result_search_event_id",
        ),
        Index(
            "pr316_receipt_event_uq",
            "result_search_event_id",
            unique=True,
            postgresql_where=text("result_search_event_id IS NOT NULL"),
        ),
        Index("pr303_receipt_policy", "result_tool_policy_id", "project_id"),
        Index(
            "pr303_receipt_invocation",
            "research_task_id",
            "project_id",
            "result_capability_invocation_id",
        ),
        Index(
            "pr303_receipt_event",
            "result_capability_event_id",
            unique=True,
            postgresql_where=text("result_capability_event_id IS NOT NULL"),
        ),
        CheckConstraint("request_hash ~ '^[0-9a-f]{64}$'"),
        CheckConstraint("hash_scheme = 'sha256-cjson-v1'"),
        CheckConstraint("material_version = 1"),
        CheckConstraint("resulting_row_version >= 1"),
        UniqueConstraint("project_id", "actor_id", "command_id"),
        UniqueConstraint("research_task_id", "id"),
        UniqueConstraint("research_task_id", "resulting_row_version"),
        UniqueConstraint("research_task_id", "actor_id", "command_id", "resulting_row_version"),
        ForeignKeyConstraint(
            ["research_task_id", "project_id"],
            ["research_tasks.id", "research_tasks.project_id"],
            ondelete="RESTRICT",
        ),
        Index("pr301_receipts_actor", "actor_id"),
        Index("pr301_receipts_project_time", "project_id", "completed_at", "id"),
        UniqueConstraint("research_task_id", "project_id", "id", name="pr303_receipt_scope_key"),
        CheckConstraint(
            "command_name IN ( 'create_research_task' , 'create_task_plan' , 'add_task_step' "
            ", 'add_task_step_dependency' , 'seal_task_plan' , 'cancel_research_task' , "
            "'bind_task_policies' , 'reserve_task_budget' , 'settle_task_budget' , "
            "'evaluate_task_termination' , 'request_human_checkpoint' , "
            "'respond_human_checkpoint' , 'register_agent_tool_policy' , "
            "'request_capability_invocation' , 'start_capability_invocation' , "
            "'finish_capability_invocation' , 'create_search_session' , 'append_search_node' "
            ")",
            name="pr316_command_names",
        ),
        ForeignKeyConstraint(
            ["result_tool_policy_id", "project_id"],
            ["agent_tool_policies.id", "agent_tool_policies.project_id"],
            ondelete="RESTRICT",
            name="pr303_receipt_policy_fk",
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["research_task_id", "project_id", "result_capability_invocation_id"],
            [
                "capability_invocations.research_task_id",
                "capability_invocations.project_id",
                "capability_invocations.id",
            ],
            ondelete="RESTRICT",
            name="pr303_receipt_invocation_fk",
            deferrable=True,
            initially="DEFERRED",
        ),
        ForeignKeyConstraint(
            ["research_task_id", "project_id", "result_capability_event_id"],
            [
                "capability_invocation_events.research_task_id",
                "capability_invocation_events.project_id",
                "capability_invocation_events.id",
            ],
            ondelete="RESTRICT",
            name="pr303_receipt_event_fk",
            deferrable=True,
            initially="DEFERRED",
        ),
        CheckConstraint(
            "(command_name = 'register_agent_tool_policy' AND result_tool_policy_id IS NOT "
            "NULL AND num_nonnulls(result_capability_invocation_id,result_capability_event_id,"
            "resulting_invocation_revision) = 0) OR (command_name IN "
            "('request_capability_invocation','start_capability_invocation',"
            "'finish_capability_invocation') AND num_nonnulls(result_tool_policy_id,"
            "result_capability_invocation_id,result_capability_event_id,"
            "resulting_invocation_revision) = 4 AND resulting_invocation_revision BETWEEN 1 "
            "AND 3) OR (command_name NOT IN ('register_agent_tool_policy',"
            "'request_capability_invocation','start_capability_invocation',"
            "'finish_capability_invocation') AND num_nonnulls(result_tool_policy_id,"
            "result_capability_invocation_id,result_capability_event_id,"
            "resulting_invocation_revision) = 0)",
            name="pr303_receipt_shape",
        ),
    )
    id = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, nullable=False)
    project_id = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False
    )
    actor_id = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    command_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    command_name = mapped_column(Text, nullable=False)
    research_task_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    request_hash = mapped_column(Text, nullable=False)
    hash_scheme = mapped_column(Text, nullable=False)
    material_version = mapped_column(Integer, nullable=False)
    resulting_row_version = mapped_column(Integer, nullable=False)
    completed_at = mapped_column(DateTime(timezone=True), nullable=False)
    result_tool_policy_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    result_capability_invocation_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    result_capability_event_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    resulting_invocation_revision = mapped_column(Integer, nullable=True)

    result_search_session_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    result_search_node_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    result_search_event_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)


class ResearchTaskEventsModel(Base):
    __tablename__ = "research_task_events"
    __table_args__ = (
        Index("pr303_task_event_policy", "result_tool_policy_id"),
        Index("pr303_task_event_invocation", "research_task_id", "result_capability_invocation_id"),
        Index("pr303_task_event_capability", "result_capability_event_id"),
        Index(
            "pr304_events_receipt_tuple",
            "research_task_id",
            "actor_id",
            "command_id",
            "task_row_version",
        ),
        CheckConstraint("sequence >= 1"),
        CheckConstraint("task_row_version >= 1"),
        UniqueConstraint("research_task_id", "id"),
        UniqueConstraint("research_task_id", "sequence"),
        UniqueConstraint("research_task_id", "task_row_version"),
        CheckConstraint("(sequence = task_row_version"),
        CheckConstraint(
            "event_type = 'CREATED' OR prior_status IS NOT NULL", name="pr304_event_prior"
        ),
        CheckConstraint("NOT stop_success", name="pr304_event_stop_slice"),
        ForeignKeyConstraint(
            ["research_task_id", "actor_id", "command_id", "task_row_version"],
            [
                "research_task_command_receipts.research_task_id",
                "research_task_command_receipts.actor_id",
                "research_task_command_receipts.command_id",
                "research_task_command_receipts.resulting_row_version",
            ],
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        Index("pr301_task_events_actor", "actor_id"),
        ForeignKeyConstraint(
            ["result_tool_policy_id"],
            ["agent_tool_policies.id"],
            ondelete="RESTRICT",
            name="pr303_task_event_policy_fk",
        ),
        ForeignKeyConstraint(
            ["research_task_id", "result_capability_invocation_id"],
            ["capability_invocations.research_task_id", "capability_invocations.id"],
            ondelete="RESTRICT",
            name="pr303_task_event_invocation_fk",
        ),
        ForeignKeyConstraint(
            ["result_capability_event_id"],
            ["capability_invocation_events.id"],
            ondelete="RESTRICT",
            name="pr303_task_event_capability_fk",
        ),
        CheckConstraint(
            "event_type IN ( 'CREATED' , 'PLAN_CREATED' , 'STEP_ADDED' , 'DEPENDENCY_ADDED' ,"
            " 'PLAN_SEALED' , 'CANCELLED' , 'POLICIES_BOUND' , 'BUDGET_RESERVED' , "
            "'BUDGET_SETTLED' , 'TERMINATION_EVALUATED' , 'CHECKPOINT_REQUESTED' , "
            "'CHECKPOINT_RESPONDED' , 'TOOL_POLICY_REGISTERED' , 'CAPABILITY_REQUESTED' , "
            "'CAPABILITY_STARTED' , 'CAPABILITY_FINISHED' , 'SEARCH_SESSION_CREATED' , "
            "'SEARCH_NODE_APPENDED' )",
            name="pr316_task_event_names",
        ),
        CheckConstraint(
            "(event_type = 'CREATED' AND prior_status IS NULL AND new_status = 'CREATED' ) OR"
            " (event_type = 'PLAN_CREATED' AND prior_status = 'CREATED' AND new_status = "
            "'PLANNING' ) OR (event_type IN ( 'STEP_ADDED' , 'DEPENDENCY_ADDED' , "
            "'PLAN_SEALED' ) AND prior_status = 'PLANNING' AND new_status = 'PLANNING' ) OR "
            "(event_type = 'CANCELLED' AND prior_status IN ( 'CREATED' , 'PLANNING' ) AND "
            "new_status = 'CANCELLED' ) OR (event_type IN ( 'POLICIES_BOUND' , "
            "'BUDGET_RESERVED' , 'BUDGET_SETTLED' , 'TERMINATION_EVALUATED' , "
            "'CHECKPOINT_REQUESTED' , 'CHECKPOINT_RESPONDED' , 'TOOL_POLICY_REGISTERED' , "
            "'CAPABILITY_REQUESTED' , 'CAPABILITY_STARTED' , 'CAPABILITY_FINISHED' ) AND "
            "prior_status IN ( 'CREATED' , 'PLANNING' , 'CANCELLED' ) AND new_status = "
            "prior_status) OR (event_type IN ( 'SEARCH_SESSION_CREATED' , "
            "'SEARCH_NODE_APPENDED' ) AND prior_status IN ( 'CREATED' , 'PLANNING' ) AND "
            "new_status = prior_status)",
            name="pr316_task_event_states",
        ),
        CheckConstraint(
            "CASE WHEN event_type IN ( 'CANCELLED' , 'POLICIES_BOUND' , 'BUDGET_RESERVED' , "
            "'BUDGET_SETTLED' , 'TERMINATION_EVALUATED' , 'CHECKPOINT_REQUESTED' , "
            "'CHECKPOINT_RESPONDED' , 'TOOL_POLICY_REGISTERED' , 'CAPABILITY_REQUESTED' , "
            "'CAPABILITY_STARTED' , 'CAPABILITY_FINISHED' , 'SEARCH_SESSION_CREATED' , "
            "'SEARCH_NODE_APPENDED' ) THEN reason IS NOT NULL AND length(btrim(reason)) "
            "BETWEEN 1 AND 8192 AND reason IS NFC NORMALIZED ELSE reason IS NULL END",
            name="pr316_task_event_reason",
        ),
        CheckConstraint(
            "event_type IN ( 'BUDGET_RESERVED','BUDGET_SETTLED','TERMINATION_EVALUATED',"
            "'CAPABILITY_REQUESTED','CAPABILITY_FINISHED') OR NOT (stop_human OR stop_policy "
            "OR stop_budget OR stop_repeated_failure OR stop_no_improvement OR stop_success)",
            name="pr303_event_stop_kind",
        ),
        CheckConstraint(
            "(event_type = 'TOOL_POLICY_REGISTERED' AND result_tool_policy_id IS NOT NULL AND "
            "result_capability_invocation_id IS NULL AND result_capability_event_id IS NULL) "
            "OR (event_type IN ('CAPABILITY_REQUESTED','CAPABILITY_STARTED',"
            "'CAPABILITY_FINISHED') AND num_nonnulls(result_tool_policy_id,"
            "result_capability_invocation_id,result_capability_event_id) = 3) OR (event_type "
            "NOT IN ('TOOL_POLICY_REGISTERED','CAPABILITY_REQUESTED','CAPABILITY_STARTED',"
            "'CAPABILITY_FINISHED') AND num_nonnulls(result_tool_policy_id,"
            "result_capability_invocation_id,result_capability_event_id) = 0)",
            name="pr303_task_event_shape",
        ),
    )
    id = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, nullable=False)
    research_task_id = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("research_tasks.id", ondelete="RESTRICT"),
        nullable=False,
    )
    actor_id = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    command_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    event_type = mapped_column(Text, nullable=False)
    sequence = mapped_column(Integer, nullable=False)
    task_row_version = mapped_column(Integer, nullable=False)
    prior_status = mapped_column(Text, nullable=True)
    new_status = mapped_column(Text, nullable=False)
    reason = mapped_column(Text, nullable=True)
    occurred_at = mapped_column(DateTime(timezone=True), nullable=False)

    stop_human = mapped_column(Boolean, nullable=False, server_default=text("false"))

    stop_policy = mapped_column(Boolean, nullable=False, server_default=text("false"))

    stop_budget = mapped_column(Boolean, nullable=False, server_default=text("false"))

    stop_repeated_failure = mapped_column(Boolean, nullable=False, server_default=text("false"))

    stop_no_improvement = mapped_column(Boolean, nullable=False, server_default=text("false"))

    stop_success = mapped_column(Boolean, nullable=False, server_default=text("false"))
    result_tool_policy_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    result_capability_invocation_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    result_capability_event_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)


class ResearchTaskStepEventsModel(Base):
    __tablename__ = "research_task_step_events"
    __table_args__ = (
        CheckConstraint("event_type IN ('PLANNED','CANCELLED')"),
        CheckConstraint("sequence >= 1"),
        CheckConstraint("step_row_version >= 1"),
        CheckConstraint("task_row_version >= 1"),
        UniqueConstraint("research_task_id", "id"),
        UniqueConstraint("research_task_id", "step_id", "sequence"),
        CheckConstraint("(sequence = step_row_version"),
        CheckConstraint(
            "((event_type = 'PLANNED' AND prior_status IS NULL AND new_status = 'PENDING' AND step_row_version = 1) OR (event_type = 'CANCELLED' AND prior_status IS NOT NULL AND prior_status = 'PENDING' AND new_status = 'CANCELLED' AND step_row_version = 2)"  # noqa: E501
        ),
        CheckConstraint(
            "(CASE WHEN event_type = 'CANCELLED' THEN reason IS NOT NULL AND length(btrim(reason)) > 0 AND reason IS NFC NORMALIZED ELSE reason IS NULL END"  # noqa: E501
        ),
        ForeignKeyConstraint(
            ["research_task_id", "step_id"],
            ["research_task_steps.research_task_id", "research_task_steps.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["research_task_id", "actor_id", "command_id", "task_row_version"],
            [
                "research_task_command_receipts.research_task_id",
                "research_task_command_receipts.actor_id",
                "research_task_command_receipts.command_id",
                "research_task_command_receipts.resulting_row_version",
            ],
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        Index("pr301_step_events_actor", "actor_id"),
    )
    id = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, nullable=False)
    research_task_id = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("research_tasks.id", ondelete="RESTRICT"),
        nullable=False,
    )
    step_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    actor_id = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    command_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    event_type = mapped_column(Text, nullable=False)
    sequence = mapped_column(Integer, nullable=False)
    step_row_version = mapped_column(Integer, nullable=False)
    task_row_version = mapped_column(Integer, nullable=False)
    prior_status = mapped_column(Text, nullable=True)
    new_status = mapped_column(Text, nullable=False)
    reason = mapped_column(Text, nullable=True)
    occurred_at = mapped_column(DateTime(timezone=True), nullable=False)


class ResearchTaskReceiptEventsModel(Base):
    __tablename__ = "research_task_receipt_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["research_task_id", "receipt_id"],
            [
                "research_task_command_receipts.research_task_id",
                "research_task_command_receipts.id",
            ],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["research_task_id", "event_id"],
            ["research_task_events.research_task_id", "research_task_events.id"],
            ondelete="RESTRICT",
        ),
        Index("pr301_receipt_events_task", "research_task_id"),
    )
    receipt_id = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, nullable=False)
    research_task_id = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("research_tasks.id", ondelete="RESTRICT"),
        nullable=False,
    )
    event_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)


class ResearchTaskReceiptStepEventsModel(Base):
    __tablename__ = "research_task_receipt_step_events"
    __table_args__ = (
        PrimaryKeyConstraint("receipt_id", "step_event_id"),
        ForeignKeyConstraint(
            ["research_task_id", "receipt_id"],
            [
                "research_task_command_receipts.research_task_id",
                "research_task_command_receipts.id",
            ],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["research_task_id", "step_event_id"],
            ["research_task_step_events.research_task_id", "research_task_step_events.id"],
            ondelete="RESTRICT",
        ),
        Index("pr301_receipt_step_events_task", "research_task_id"),
    )
    receipt_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    research_task_id = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("research_tasks.id", ondelete="RESTRICT"),
        nullable=False,
    )
    step_event_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)


class ExecutionBudgetsModel(Base):
    __tablename__ = "execution_budgets"
    __table_args__ = (
        Index("pr304_budgets_time", "research_task_id", "created_at", "id"),
        Index("pr304_budgets_receipt", "research_task_id", "receipt_id"),
        CheckConstraint("max_wall_time_seconds > 0"),
        CheckConstraint("max_agent_steps > 0"),
        CheckConstraint("max_llm_calls > 0"),
        CheckConstraint("max_search_calls > 0"),
        CheckConstraint("max_code_iterations > 0"),
        CheckConstraint("max_experiment_runs > 0"),
        CheckConstraint("max_tree_nodes > 0"),
        CheckConstraint("max_tree_depth > 0"),
        CheckConstraint("max_parallel_branches > 0"),
        CheckConstraint("max_gpu_hours >= 0 AND max_gpu_hours < 'Infinity'::numeric"),
        CheckConstraint("max_token_cost > 0 AND max_token_cost < 'Infinity'::numeric"),
        CheckConstraint("currency = 'USD'"),
        CheckConstraint(
            "length(btrim(pricing_basis)) BETWEEN 1 AND 512 AND pricing_basis IS NFC NORMALIZED AND lower(btrim(pricing_basis)) NOT IN ('latest','main','master')"  # noqa: E501
        ),
        CheckConstraint("hard_stop"),
        CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'"),
        CheckConstraint("hash_scheme = 'sha256-cjson-v1'"),
        UniqueConstraint("research_task_id", "id"),
        ForeignKeyConstraint(
            ["research_task_id", "receipt_id"],
            [
                "research_task_command_receipts.research_task_id",
                "research_task_command_receipts.id",
            ],
            ondelete="RESTRICT",
        ),
    )
    id = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, nullable=False)
    research_task_id = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("research_tasks.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at = mapped_column(DateTime(timezone=True), nullable=False)
    receipt_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    max_wall_time_seconds = mapped_column(Integer, nullable=False)
    max_agent_steps = mapped_column(BigInteger, nullable=False)
    max_llm_calls = mapped_column(BigInteger, nullable=False)
    max_search_calls = mapped_column(BigInteger, nullable=False)
    max_code_iterations = mapped_column(BigInteger, nullable=False)
    max_experiment_runs = mapped_column(BigInteger, nullable=False)
    max_tree_nodes = mapped_column(BigInteger, nullable=False)
    max_tree_depth = mapped_column(Integer, nullable=False)
    max_parallel_branches = mapped_column(Integer, nullable=False)
    max_gpu_hours = mapped_column(Numeric(20, 6), nullable=False)
    max_token_cost = mapped_column(Numeric(20, 6), nullable=False)
    currency = mapped_column(Text, nullable=False)
    pricing_basis = mapped_column(Text, nullable=False)
    hard_stop = mapped_column(Boolean, nullable=False)
    content_hash = mapped_column(Text, nullable=False)
    hash_scheme = mapped_column(Text, nullable=False)


class TerminationPoliciesModel(Base):
    __tablename__ = "termination_policies"
    __table_args__ = (
        Index(
            "pr304_termination_metric",
            "score_metric_version_id",
            postgresql_where=text("score_metric_version_id IS NOT NULL"),
        ),  # noqa: E501
        Index("pr304_termination_time", "research_task_id", "created_at", "id"),
        Index("pr304_termination_receipt", "research_task_id", "receipt_id"),
        CheckConstraint("repeated_failure_threshold > 0"),
        CheckConstraint("max_no_improvement_iterations > 0"),
        CheckConstraint("budget_stop"),
        CheckConstraint("human_stop"),
        CheckConstraint("policy_stop"),
        CheckConstraint("score_direction IN ('MAXIMIZE','MINIMIZE')"),
        CheckConstraint(
            "length(btrim(evaluator_version)) BETWEEN 1 AND 128 AND evaluator_version IS NFC NORMALIZED AND lower(btrim(evaluator_version)) NOT IN ('latest','main','master')"  # noqa: E501
        ),
        CheckConstraint("NOT min_progress_enabled"),
        CheckConstraint("min_progress_score IS NULL"),
        CheckConstraint("NOT duplicate_hypothesis_enabled"),
        CheckConstraint("duplicate_hypothesis_threshold IS NULL"),
        CheckConstraint("NOT confidence_stop_enabled"),
        CheckConstraint("confidence_stop_threshold IS NULL"),
        CheckConstraint("NOT success_condition_enabled"),
        CheckConstraint("success_condition IS NULL"),
        CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'"),
        CheckConstraint("hash_scheme = 'sha256-cjson-v1'"),
        CheckConstraint(
            "num_nonnulls(score_metric_version_id, score_direction, evaluator_version) IN (0,3)"
        ),
        UniqueConstraint("research_task_id", "id"),
        ForeignKeyConstraint(
            ["research_task_id", "receipt_id"],
            [
                "research_task_command_receipts.research_task_id",
                "research_task_command_receipts.id",
            ],
            ondelete="RESTRICT",
        ),
    )
    id = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, nullable=False)
    research_task_id = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("research_tasks.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at = mapped_column(DateTime(timezone=True), nullable=False)
    receipt_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    repeated_failure_threshold = mapped_column(Integer, nullable=False)
    max_no_improvement_iterations = mapped_column(Integer, nullable=False)
    budget_stop = mapped_column(Boolean, nullable=False)
    human_stop = mapped_column(Boolean, nullable=False)
    policy_stop = mapped_column(Boolean, nullable=False)
    score_metric_version_id = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("metric_definition_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    score_direction = mapped_column(Text, nullable=True)
    evaluator_version = mapped_column(Text, nullable=True)
    min_progress_enabled = mapped_column(Boolean, nullable=False)
    min_progress_score = mapped_column(Numeric(20, 6), nullable=True)
    duplicate_hypothesis_enabled = mapped_column(Boolean, nullable=False)
    duplicate_hypothesis_threshold = mapped_column(Numeric(20, 6), nullable=True)
    confidence_stop_enabled = mapped_column(Boolean, nullable=False)
    confidence_stop_threshold = mapped_column(Numeric(20, 6), nullable=True)
    success_condition_enabled = mapped_column(Boolean, nullable=False)
    success_condition = mapped_column(Text, nullable=True)
    content_hash = mapped_column(Text, nullable=False)
    hash_scheme = mapped_column(Text, nullable=False)


class CheckpointPoliciesModel(Base):
    __tablename__ = "checkpoint_policies"
    __table_args__ = (
        Index("pr304_checkpoint_policy_time", "research_task_id", "created_at", "id"),
        Index("pr304_checkpoint_policy_receipt", "research_task_id", "receipt_id"),
        CheckConstraint(
            "required_types <@ ARRAY['plan_review','hypothesis_selection','experiment_approval','budget_extension','code_risk','claim_freeze','manuscript_release','exception']::text[] AND array_position(required_types,NULL) IS NULL"  # noqa: E501
        ),
        CheckConstraint("timeout_seconds > 0"),
        CheckConstraint("maximum_autonomy IN ('A0','A1','A2','A3')"),
        CheckConstraint("array_position(allowed_code_paths,NULL) IS NULL"),
        CheckConstraint("network_mode IN ('DENY','ALLOWLIST')"),
        CheckConstraint("array_position(allowed_network_hosts,NULL) IS NULL"),
        CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'"),
        CheckConstraint("hash_scheme = 'sha256-cjson-v1'"),
        CheckConstraint("a3_authorized = (maximum_autonomy = 'A3')"),
        CheckConstraint("network_mode <> 'DENY' OR cardinality(allowed_network_hosts) = 0"),
        CheckConstraint("network_mode <> 'ALLOWLIST' OR cardinality(allowed_network_hosts) > 0"),
        CheckConstraint(
            "a3_authorized OR (cardinality(allowed_code_paths) = 0 AND network_mode = 'DENY')"
        ),
        UniqueConstraint("research_task_id", "id"),
        ForeignKeyConstraint(
            ["research_task_id", "receipt_id"],
            [
                "research_task_command_receipts.research_task_id",
                "research_task_command_receipts.id",
            ],
            ondelete="RESTRICT",
        ),
    )
    id = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, nullable=False)
    research_task_id = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("research_tasks.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at = mapped_column(DateTime(timezone=True), nullable=False)
    receipt_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    required_types = mapped_column(ARRAY(Text), nullable=False)
    timeout_seconds = mapped_column(Integer, nullable=False)
    maximum_autonomy = mapped_column(Text, nullable=False)
    a3_authorized = mapped_column(Boolean, nullable=False)
    allowed_code_paths = mapped_column(ARRAY(Text), nullable=False)
    network_mode = mapped_column(Text, nullable=False)
    allowed_network_hosts = mapped_column(ARRAY(Text), nullable=False)
    content_hash = mapped_column(Text, nullable=False)
    hash_scheme = mapped_column(Text, nullable=False)


class CheckpointPolicyDatasetScopesModel(Base):
    __tablename__ = "checkpoint_policy_dataset_scopes"
    __table_args__ = (
        Index("pr304_dataset_scope_time", "research_task_id", "created_at", "id"),
        Index("pr304_dataset_scope_ref", "dataset_snapshot_id"),
        Index("pr304_dataset_scope_receipt", "research_task_id", "receipt_id"),
        Index("pr304_dataset_scope_policy", "research_task_id", "checkpoint_policy_id"),
        CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'"),
        UniqueConstraint("checkpoint_policy_id", "dataset_snapshot_id"),
        ForeignKeyConstraint(
            ["research_task_id", "checkpoint_policy_id"],
            ["checkpoint_policies.research_task_id", "checkpoint_policies.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["research_task_id", "receipt_id"],
            [
                "research_task_command_receipts.research_task_id",
                "research_task_command_receipts.id",
            ],
            ondelete="RESTRICT",
        ),
    )
    id = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, nullable=False)
    research_task_id = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("research_tasks.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at = mapped_column(DateTime(timezone=True), nullable=False)
    receipt_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    checkpoint_policy_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    dataset_snapshot_id = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("dataset_snapshots.id", ondelete="RESTRICT"),
        nullable=False,
    )
    content_hash = mapped_column(Text, nullable=False)


class CheckpointPolicyMetricScopesModel(Base):
    __tablename__ = "checkpoint_policy_metric_scopes"
    __table_args__ = (
        Index("pr304_metric_scope_time", "research_task_id", "created_at", "id"),
        Index("pr304_metric_scope_ref", "metric_definition_version_id"),
        Index("pr304_metric_scope_receipt", "research_task_id", "receipt_id"),
        Index("pr304_metric_scope_policy", "research_task_id", "checkpoint_policy_id"),
        CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'"),
        UniqueConstraint("checkpoint_policy_id", "metric_definition_version_id"),
        ForeignKeyConstraint(
            ["research_task_id", "checkpoint_policy_id"],
            ["checkpoint_policies.research_task_id", "checkpoint_policies.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["research_task_id", "receipt_id"],
            [
                "research_task_command_receipts.research_task_id",
                "research_task_command_receipts.id",
            ],
            ondelete="RESTRICT",
        ),
    )
    id = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, nullable=False)
    research_task_id = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("research_tasks.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at = mapped_column(DateTime(timezone=True), nullable=False)
    receipt_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    checkpoint_policy_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    metric_definition_version_id = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("metric_definition_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    content_hash = mapped_column(Text, nullable=False)


class BudgetReservationsModel(Base):
    __tablename__ = "budget_reservations"
    __table_args__ = (
        Index("pr304_reservations_deadline", "deadline", "research_task_id", "id"),
        Index("pr304_reservations_time", "research_task_id", "created_at", "id"),
        Index("pr304_reservations_step", "research_task_id", "step_id"),
        Index("pr304_reservations_budget", "research_task_id", "budget_id"),
        Index("pr304_reservations_receipt", "research_task_id", "receipt_id"),
        CheckConstraint("wall_time_seconds > 0"),
        CheckConstraint("agent_steps >= 0"),
        CheckConstraint("llm_calls >= 0"),
        CheckConstraint("search_calls >= 0"),
        CheckConstraint("code_iterations >= 0"),
        CheckConstraint("experiment_runs >= 0"),
        CheckConstraint("tree_nodes >= 0"),
        CheckConstraint("gpu_hours >= 0 AND gpu_hours < 'Infinity'::numeric"),
        CheckConstraint("token_cost >= 0 AND token_cost < 'Infinity'::numeric"),
        CheckConstraint("observed_depth >= 0"),
        CheckConstraint("observed_parallel_branches > 0"),
        CheckConstraint("deadline > created_at"),
        UniqueConstraint("research_task_id", "id"),
        UniqueConstraint("research_task_id", "operation_id"),
        ForeignKeyConstraint(
            ["research_task_id", "receipt_id"],
            [
                "research_task_command_receipts.research_task_id",
                "research_task_command_receipts.id",
            ],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["research_task_id", "budget_id"],
            ["execution_budgets.research_task_id", "execution_budgets.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["research_task_id", "step_id"],
            ["research_task_steps.research_task_id", "research_task_steps.id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "research_task_id", "id", "operation_id", name="pr303_reservation_operation_key"
        ),
    )
    id = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, nullable=False)
    research_task_id = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("research_tasks.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at = mapped_column(DateTime(timezone=True), nullable=False)
    receipt_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    budget_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    step_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    operation_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    wall_time_seconds = mapped_column(Integer, nullable=False)
    agent_steps = mapped_column(BigInteger, nullable=False)
    llm_calls = mapped_column(BigInteger, nullable=False)
    search_calls = mapped_column(BigInteger, nullable=False)
    code_iterations = mapped_column(BigInteger, nullable=False)
    experiment_runs = mapped_column(BigInteger, nullable=False)
    tree_nodes = mapped_column(BigInteger, nullable=False)
    gpu_hours = mapped_column(Numeric(20, 6), nullable=False)
    token_cost = mapped_column(Numeric(20, 6), nullable=False)
    observed_depth = mapped_column(Integer, nullable=False)
    observed_parallel_branches = mapped_column(Integer, nullable=False)
    deadline = mapped_column(DateTime(timezone=True), nullable=False)


class BudgetUsageRecordsModel(Base):
    __tablename__ = "budget_usage_records"
    __table_args__ = (
        Index("pr304_usage_time", "research_task_id", "created_at", "id"),
        Index("pr304_usage_receipt", "research_task_id", "receipt_id"),
        Index(
            "pr304_usage_one_final",
            "research_task_id",
            "reservation_id",
            unique=True,
            postgresql_where=text("is_final"),
        ),
        CheckConstraint("outcome IN ('SUCCEEDED','FAILED','CANCELLED','PRUNED','UNKNOWN')"),
        CheckConstraint("wall_time_seconds >= 0"),
        CheckConstraint("agent_steps >= 0"),
        CheckConstraint("llm_calls >= 0"),
        CheckConstraint("search_calls >= 0"),
        CheckConstraint("code_iterations >= 0"),
        CheckConstraint("experiment_runs >= 0"),
        CheckConstraint("tree_nodes >= 0"),
        CheckConstraint("gpu_hours >= 0 AND gpu_hours < 'Infinity'::numeric"),
        CheckConstraint("token_cost >= 0 AND token_cost < 'Infinity'::numeric"),
        CheckConstraint("failure_streak >= 0"),
        CheckConstraint("no_improvement_streak >= 0"),
        CheckConstraint("score > '-Infinity'::numeric AND score < 'Infinity'::numeric"),
        CheckConstraint(
            "length(btrim(evaluator_version)) BETWEEN 1 AND 128 AND evaluator_version IS NFC NORMALIZED AND lower(btrim(evaluator_version)) NOT IN ('latest','main','master')"  # noqa: E501
        ),
        CheckConstraint("settled_at = created_at"),
        CheckConstraint("is_final = (outcome <> 'UNKNOWN')"),
        CheckConstraint("(score IS NULL) = (evaluator_version IS NULL)"),
        UniqueConstraint("research_task_id", "id"),
        UniqueConstraint("research_task_id", "reservation_id", "receipt_id"),
        ForeignKeyConstraint(
            ["research_task_id", "receipt_id"],
            [
                "research_task_command_receipts.research_task_id",
                "research_task_command_receipts.id",
            ],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["research_task_id", "reservation_id"],
            ["budget_reservations.research_task_id", "budget_reservations.id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "research_task_id", "reservation_id", "id", name="pr303_usage_reservation_key"
        ),
    )
    id = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, nullable=False)
    research_task_id = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("research_tasks.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at = mapped_column(DateTime(timezone=True), nullable=False)
    receipt_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    reservation_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    outcome = mapped_column(Text, nullable=False)
    is_final = mapped_column(Boolean, nullable=False)
    wall_time_seconds = mapped_column(Integer, nullable=False)
    agent_steps = mapped_column(BigInteger, nullable=False)
    llm_calls = mapped_column(BigInteger, nullable=False)
    search_calls = mapped_column(BigInteger, nullable=False)
    code_iterations = mapped_column(BigInteger, nullable=False)
    experiment_runs = mapped_column(BigInteger, nullable=False)
    tree_nodes = mapped_column(BigInteger, nullable=False)
    gpu_hours = mapped_column(Numeric(20, 6), nullable=False)
    token_cost = mapped_column(Numeric(20, 6), nullable=False)
    failure_streak = mapped_column(Integer, nullable=False)
    no_improvement_streak = mapped_column(Integer, nullable=False)
    score = mapped_column(Numeric(20, 6), nullable=True)
    evaluator_version = mapped_column(Text, nullable=True)
    settled_at = mapped_column(DateTime(timezone=True), nullable=False)


class HumanCheckpointsModel(Base):
    __tablename__ = "human_checkpoints"
    __table_args__ = (
        Index(
            "pr304_checkpoint_expiry",
            "expires_at",
            "research_task_id",
            "id",
            postgresql_where=text("status = 'PENDING'"),
        ),  # noqa: E501
        Index("pr304_checkpoint_time", "research_task_id", "created_at", "id"),
        Index(
            "pr304_checkpoint_responder",
            "responded_by",
            postgresql_where=text("responded_by IS NOT NULL"),
        ),  # noqa: E501
        Index("pr304_checkpoint_step", "research_task_id", "step_id"),
        Index(
            "pr304_checkpoint_response_receipt",
            "research_task_id",
            "response_receipt_id",
            postgresql_where=text("response_receipt_id IS NOT NULL"),
        ),  # noqa: E501
        Index("pr304_checkpoint_receipt", "research_task_id", "receipt_id"),
        Index(
            "pr304_checkpoint_one_pending",
            "research_task_id",
            "step_id",
            "checkpoint_type",
            unique=True,
            postgresql_nulls_not_distinct=True,
            postgresql_where=text("status = 'PENDING'"),
        ),  # noqa: E501
        CheckConstraint(
            "checkpoint_type IN ('plan_review','hypothesis_selection','experiment_approval','budget_extension','code_risk','claim_freeze','manuscript_release','exception')"  # noqa: E501
        ),
        CheckConstraint("status IN ('PENDING','APPROVED','REJECTED','MODIFIED','EXPIRED')"),
        CheckConstraint("length(btrim(reason)) BETWEEN 1 AND 8192 AND reason IS NFC NORMALIZED"),
        CheckConstraint("requested_at = created_at"),
        CheckConstraint("expires_at > requested_at"),
        CheckConstraint(
            "length(btrim(response_reason)) BETWEEN 1 AND 8192 AND response_reason IS NFC NORMALIZED"  # noqa: E501
        ),
        CheckConstraint("row_version IN (1,2)"),
        CheckConstraint(
            "(status = 'PENDING' AND row_version = 1 AND num_nonnulls(responded_at,responded_by,response_reason,response_receipt_id) = 0)\n    OR (status IN ('APPROVED','REJECTED','MODIFIED') AND row_version = 2 AND num_nonnulls(responded_at,responded_by,response_reason,response_receipt_id) = 4 AND responded_at >= requested_at AND responded_at < expires_at)\n    OR (status = 'EXPIRED' AND row_version = 2 AND num_nonnulls(responded_at,response_reason,response_receipt_id) = 3 AND responded_at >= expires_at AND responded_by IS NULL)"  # noqa: E501
        ),
        CheckConstraint(
            "(checkpoint_type = 'budget_extension') = (proposed_budget_id IS NOT NULL)"
        ),
        UniqueConstraint("research_task_id", "id"),
        UniqueConstraint("research_task_id", "proposed_budget_id"),
        ForeignKeyConstraint(
            ["research_task_id", "receipt_id"],
            [
                "research_task_command_receipts.research_task_id",
                "research_task_command_receipts.id",
            ],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["research_task_id", "response_receipt_id"],
            [
                "research_task_command_receipts.research_task_id",
                "research_task_command_receipts.id",
            ],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["research_task_id", "step_id"],
            ["research_task_steps.research_task_id", "research_task_steps.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["research_task_id", "proposed_budget_id"],
            ["execution_budgets.research_task_id", "execution_budgets.id"],
            ondelete="RESTRICT",
        ),
    )
    id = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, nullable=False)
    research_task_id = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("research_tasks.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at = mapped_column(DateTime(timezone=True), nullable=False)
    receipt_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    step_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    checkpoint_type = mapped_column(Text, nullable=False)
    status = mapped_column(Text, nullable=False)
    reason = mapped_column(Text, nullable=False)
    requested_at = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at = mapped_column(DateTime(timezone=True), nullable=False)
    responded_at = mapped_column(DateTime(timezone=True), nullable=True)
    responded_by = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=True
    )
    response_reason = mapped_column(Text, nullable=True)
    row_version = mapped_column(Integer, nullable=False)
    response_receipt_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    proposed_budget_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)


# ADR-0023 S1 internal persistence mappings. Migration 0079 owns guards and DDL.
class AgentVersionModel(Base):
    __tablename__ = "agent_versions"
    __table_args__ = (UniqueConstraint("id", "project_id", "actor_id"),)
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, nullable=False)
    project_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False
    )
    actor_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    agent_role: Mapped[str] = mapped_column(Text, nullable=False)
    runtime_type: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_template_version: Mapped[str] = mapped_column(Text, nullable=False)
    model_profile_id: Mapped[str] = mapped_column(Text, nullable=False)
    tool_policy_version: Mapped[str] = mapped_column(Text, nullable=False)
    capability_set_hash: Mapped[str] = mapped_column(Text, nullable=False)
    configuration_artifact_version_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("artifact_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    configuration_content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    hash_scheme: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AgentAvailabilityModel(Base):
    __tablename__ = "agent_availability"
    agent_version_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("agent_versions.id", ondelete="RESTRICT"),
        primary_key=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(Text, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    changed_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AgentCommandReceiptModel(Base):
    __tablename__ = "agent_command_receipts"
    __table_args__ = (
        Index(
            "pr302s2_receipt_execution_uq",
            "result_execution_id",
            unique=True,
            postgresql_where=text("result_execution_id IS NOT NULL"),
        ),
        Index(
            "pr302s2_receipt_event_uq",
            "result_execution_event_id",
            unique=True,
            postgresql_where=text("result_execution_event_id IS NOT NULL"),
        ),
    )
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, nullable=False)
    project_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False
    )
    caller_actor_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    command_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    operation: Mapped[str] = mapped_column(Text, nullable=False)
    request_hash: Mapped[str] = mapped_column(Text, nullable=False)
    hash_scheme: Mapped[str] = mapped_column(Text, nullable=False)
    result_actor_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("actors.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"),
        nullable=True,
    )
    result_binding_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "actor_subject_bindings.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=True,
    )
    result_membership_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "project_memberships.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=True,
    )
    result_role_assignment_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "project_role_assignments.id",
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=True,
    )
    result_binding_event_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "actor_subject_binding_events.id",
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=True,
    )
    result_membership_event_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "project_membership_events.id",
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=True,
    )
    result_role_event_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "project_role_events.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"
        ),
        nullable=True,
    )
    result_agent_version_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("agent_versions.id", ondelete="RESTRICT", deferrable=True, initially="DEFERRED"),
        nullable=True,
    )
    result_availability_event_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "agent_availability_events.id",
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=True,
    )
    result_execution_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "agent_execution_instances.id",
            name="pr302s2_receipt_execution_fk",
            onupdate="NO ACTION",
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=True,
    )
    result_execution_event_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "agent_execution_events.id",
            name="pr302s2_receipt_event_fk",
            onupdate="NO ACTION",
            ondelete="RESTRICT",
            deferrable=True,
            initially="DEFERRED",
        ),
        nullable=True,
    )
    resulting_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AgentAvailabilityEventModel(Base):
    __tablename__ = "agent_availability_events"
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, nullable=False)
    agent_version_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("agent_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    prior_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_status: Mapped[str] = mapped_column(Text, nullable=False)
    actor_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    receipt_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("agent_command_receipts.id", ondelete="RESTRICT"),
        nullable=False,
    )


# PR3-03 inert metadata. Migration 0080 owns the persisted schema and guards.


class ToolPolicyRowModel(Base):
    __tablename__ = "agent_tool_policies"
    __table_args__ = (
        CheckConstraint(
            "length(btrim(version)) BETWEEN 1 AND 512 AND version IS NFC NORMALIZED AND "
            "lower(btrim(version)) NOT IN ('latest','current','main','master')"
        ),
        CheckConstraint("capability_set_hash ~ '^[0-9a-f]{64}$'"),
        CheckConstraint("max_tool_calls > 0"),
        CheckConstraint(
            "max_parallel_invocations > 0 AND max_parallel_invocations <= max_tool_calls"
        ),
        CheckConstraint("filesystem_scope = 'DENY'"),
        CheckConstraint("network_scope = 'DENY'"),
        CheckConstraint("compute_scope = 'DENY'"),
        CheckConstraint("external_effect_scope = 'DENY'"),
        CheckConstraint("registry_content_hash ~ '^[0-9a-f]{64}$'"),
        CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'"),
        CheckConstraint("hash_scheme = 'sha256-cjson-v1'"),
        UniqueConstraint("project_id", "version"),
        UniqueConstraint("id", "project_id"),
        ForeignKeyConstraint(
            ["registration_task_id", "project_id"],
            ["research_tasks.id", "research_tasks.project_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["registration_task_id", "project_id", "receipt_id"],
            [
                "research_task_command_receipts.research_task_id",
                "research_task_command_receipts.project_id",
                "research_task_command_receipts.id",
            ],
            ondelete="RESTRICT",
        ),
        Index("pr303_policy_registration", "registration_task_id", "project_id", "receipt_id"),
        Index("pr303_policy_registry", "registry_artifact_version_id"),
        Index("pr303_policy_creator", "created_by"),
        Index("pr303_policy_time", "project_id", "created_at", "id"),
    )
    id = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, nullable=False)
    project_id = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False
    )
    registration_task_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    receipt_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    version = mapped_column(Text, nullable=False)
    capability_set_hash = mapped_column(Text, nullable=False)
    max_tool_calls = mapped_column(Integer, nullable=False)
    max_parallel_invocations = mapped_column(Integer, nullable=False)
    filesystem_scope = mapped_column(Text, nullable=False)
    network_scope = mapped_column(Text, nullable=False)
    compute_scope = mapped_column(Text, nullable=False)
    external_effect_scope = mapped_column(Text, nullable=False)
    registry_artifact_version_id = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("artifact_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    registry_content_hash = mapped_column(Text, nullable=False)
    content_hash = mapped_column(Text, nullable=False)
    hash_scheme = mapped_column(Text, nullable=False)
    created_by = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    created_at = mapped_column(DateTime(timezone=True), nullable=False)


class ToolPolicyPermissionRowModel(Base):
    __tablename__ = "agent_tool_policy_permissions"
    __table_args__ = (
        CheckConstraint("parameter_schema_hash ~ '^[0-9a-f]{64}$'"),
        CheckConstraint("effect IN ('ALLOW','DENY')"),
        UniqueConstraint(
            "policy_id",
            "capability_id",
            "capability_version",
            "operation",
            "adapter_id",
            "adapter_version",
            "parameter_schema_hash",
            "effect",
        ),
        ForeignKeyConstraint(
            ["policy_id", "project_id"],
            ["agent_tool_policies.id", "agent_tool_policies.project_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "length(btrim(capability_id)) BETWEEN 1 AND 128 AND capability_id IS NFC NORMALIZED"
        ),
        CheckConstraint(
            "length(btrim(capability_version)) BETWEEN 1 AND 512 AND capability_version IS NFC "
            "NORMALIZED"
        ),
        CheckConstraint(
            "length(btrim(operation)) BETWEEN 1 AND 128 AND operation IS NFC NORMALIZED"
        ),
        CheckConstraint(
            "length(btrim(adapter_id)) BETWEEN 1 AND 128 AND adapter_id IS NFC NORMALIZED"
        ),
        CheckConstraint(
            "length(btrim(adapter_version)) BETWEEN 1 AND 512 AND adapter_version IS NFC NORMALIZED"
        ),
        Index("pr303_permission_scope", "policy_id", "project_id"),
        Index("pr303_permission_project", "project_id", "policy_id"),
    )
    id = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, nullable=False)
    policy_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    project_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    capability_id = mapped_column(Text, nullable=False)
    capability_version = mapped_column(Text, nullable=False)
    operation = mapped_column(Text, nullable=False)
    adapter_id = mapped_column(Text, nullable=False)
    adapter_version = mapped_column(Text, nullable=False)
    parameter_schema_hash = mapped_column(Text, nullable=False)
    effect = mapped_column(Text, nullable=False)


class CapabilityInvocationsModel(Base):
    __tablename__ = "capability_invocations"
    __table_args__ = (
        CheckConstraint("policy_content_hash ~ '^[0-9a-f]{64}$'"),
        CheckConstraint("mode = 'CONTRACT_FAKE'"),
        CheckConstraint("parameter_schema_hash ~ '^[0-9a-f]{64}$'"),
        CheckConstraint("harness_content_hash ~ '^[0-9a-f]{64}$'"),
        CheckConstraint("parameters_content_hash ~ '^[0-9a-f]{64}$'"),
        CheckConstraint("requested_parameters_hash ~ '^[0-9a-f]{64}$'"),
        CheckConstraint("parameters_byte_size BETWEEN 1 AND 65536"),
        CheckConstraint("trace_content_hash ~ '^[0-9a-f]{64}$'"),
        CheckConstraint(
            "status IN ( 'REQUESTED','RUNNING','SUCCEEDED','FAILED','UNKNOWN_OUTCOME','CANCELLED')"
        ),
        CheckConstraint("row_version BETWEEN 1 AND 3"),
        CheckConstraint(
            "octet_length(result_summary) <= 8192 AND result_summary IS NFC NORMALIZED"
        ),
        UniqueConstraint("research_task_id", "project_id", "id"),
        UniqueConstraint("research_task_id", "id"),
        UniqueConstraint("research_task_id", "id", "reservation_id"),
        ForeignKeyConstraint(
            ["research_task_id", "project_id"],
            ["research_tasks.id", "research_tasks.project_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["research_task_id", "step_id"],
            ["research_task_steps.research_task_id", "research_task_steps.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["agent_version_id", "project_id", "agent_actor_id"],
            ["agent_versions.id", "agent_versions.project_id", "agent_versions.actor_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["policy_id", "project_id"],
            ["agent_tool_policies.id", "agent_tool_policies.project_id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["research_task_id", "reservation_id", "id"],
            [
                "budget_reservations.research_task_id",
                "budget_reservations.id",
                "budget_reservations.operation_id",
            ],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["research_task_id", "reservation_id", "usage_record_id"],
            [
                "budget_usage_records.research_task_id",
                "budget_usage_records.reservation_id",
                "budget_usage_records.id",
            ],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["research_task_id", "retry_parent_id"],
            ["capability_invocations.research_task_id", "capability_invocations.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["research_task_id", "project_id", "request_receipt_id"],
            [
                "research_task_command_receipts.research_task_id",
                "research_task_command_receipts.project_id",
                "research_task_command_receipts.id",
            ],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["research_task_id", "project_id", "start_receipt_id"],
            [
                "research_task_command_receipts.research_task_id",
                "research_task_command_receipts.project_id",
                "research_task_command_receipts.id",
            ],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["research_task_id", "project_id", "finish_receipt_id"],
            [
                "research_task_command_receipts.research_task_id",
                "research_task_command_receipts.project_id",
                "research_task_command_receipts.id",
            ],
            ondelete="RESTRICT",
        ),
        CheckConstraint("retry_parent_id IS DISTINCT FROM id"),
        CheckConstraint("(trace_artifact_version_id IS NULL) = (trace_content_hash IS NULL)"),
        CheckConstraint("started_at IS NULL OR started_at >= created_at"),
        CheckConstraint("finished_at IS NULL OR finished_at >= coalesce(started_at, created_at)"),
        CheckConstraint(
            "(status = 'REQUESTED' AND row_version = 1 AND num_nonnulls(started_at, "
            "finished_at,start_receipt_id,finish_receipt_id,usage_record_id, "
            "trace_artifact_version_id,result_summary,error_code) = 0) OR (status = 'RUNNING' "
            "AND row_version = 2 AND started_at IS NOT NULL AND start_receipt_id IS NOT NULL "
            "AND num_nonnulls(finished_at, finish_receipt_id,usage_record_id,"
            "trace_artifact_version_id,result_summary,error_code) = 0) OR (status = "
            "'CANCELLED' AND row_version = 2 AND started_at IS NULL AND start_receipt_id IS "
            "NULL AND finished_at IS NOT NULL AND finish_receipt_id IS NOT NULL AND "
            "usage_record_id IS NOT NULL) OR (status IN ('SUCCEEDED','FAILED',"
            "'UNKNOWN_OUTCOME','CANCELLED') AND row_version = 3 AND num_nonnulls(started_at,"
            "start_receipt_id,finished_at,finish_receipt_id,usage_record_id) = 5)"
        ),
        CheckConstraint(
            "CASE WHEN status IN ('FAILED','UNKNOWN_OUTCOME') THEN error_code IS NOT NULL AND "
            "error_code IN ('ADAPTER_UNAVAILABLE','INVALID_STATE_TRANSITION') ELSE error_code "
            "IS NULL END"
        ),
        CheckConstraint(
            "length(btrim(capability_id)) BETWEEN 1 AND 128 AND capability_id IS NFC NORMALIZED"
        ),
        CheckConstraint(
            "length(btrim(capability_version)) BETWEEN 1 AND 512 AND capability_version IS NFC "
            "NORMALIZED"
        ),
        CheckConstraint(
            "length(btrim(operation)) BETWEEN 1 AND 128 AND operation IS NFC NORMALIZED"
        ),
        CheckConstraint(
            "length(btrim(adapter_id)) BETWEEN 1 AND 128 AND adapter_id IS NFC NORMALIZED"
        ),
        CheckConstraint(
            "length(btrim(adapter_version)) BETWEEN 1 AND 512 AND adapter_version IS NFC NORMALIZED"
        ),
        CheckConstraint("length(btrim(skill_id)) BETWEEN 1 AND 128 AND skill_id IS NFC NORMALIZED"),
        CheckConstraint(
            "length(btrim(skill_version)) BETWEEN 1 AND 512 AND skill_version IS NFC NORMALIZED"
        ),
        CheckConstraint(
            "length(btrim(strategy_id)) BETWEEN 1 AND 128 AND strategy_id IS NFC NORMALIZED"
        ),
        CheckConstraint(
            "length(btrim(strategy_version)) BETWEEN 1 AND 512 AND strategy_version IS NFC "
            "NORMALIZED"
        ),
        Index("pr303_invocation_task_time", "research_task_id", "created_at", "id"),
        Index("pr303_invocation_project", "project_id", "research_task_id", "id"),
        Index("pr303_invocation_step", "research_task_id", "step_id"),
        Index("pr303_invocation_version", "agent_version_id", "project_id", "agent_actor_id"),
        Index("pr303_invocation_actor", "agent_actor_id"),
        Index("pr303_invocation_requester", "requested_by"),
        Index("pr303_invocation_policy", "policy_id", "project_id"),
        Index("pr303_invocation_harness", "harness_artifact_version_id"),
        Index("pr303_invocation_parameters", "parameters_artifact_version_id"),
        Index(
            "pr303_invocation_trace",
            "trace_artifact_version_id",
            postgresql_where=text("trace_artifact_version_id IS NOT NULL"),
        ),
        Index(
            "pr303_invocation_retry",
            "research_task_id",
            "retry_parent_id",
            postgresql_where=text("retry_parent_id IS NOT NULL"),
        ),
        Index("pr303_invocation_usage", "research_task_id", "reservation_id", "usage_record_id"),
    )
    id = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, nullable=False)
    project_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    research_task_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    step_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    agent_version_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    agent_actor_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    requested_by = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    policy_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    policy_content_hash = mapped_column(Text, nullable=False)
    mode = mapped_column(Text, nullable=False)
    capability_id = mapped_column(Text, nullable=False)
    capability_version = mapped_column(Text, nullable=False)
    operation = mapped_column(Text, nullable=False)
    adapter_id = mapped_column(Text, nullable=False)
    adapter_version = mapped_column(Text, nullable=False)
    parameter_schema_hash = mapped_column(Text, nullable=False)
    skill_id = mapped_column(Text, nullable=False)
    skill_version = mapped_column(Text, nullable=False)
    strategy_id = mapped_column(Text, nullable=False)
    strategy_version = mapped_column(Text, nullable=False)
    harness_artifact_version_id = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("artifact_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    harness_content_hash = mapped_column(Text, nullable=False)
    parameters_artifact_version_id = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("artifact_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    parameters_content_hash = mapped_column(Text, nullable=False)
    requested_parameters_hash = mapped_column(Text, nullable=False)
    parameters_byte_size = mapped_column(Integer, nullable=False)
    reservation_id = mapped_column(PostgreSQLUUID(as_uuid=True), unique=True, nullable=False)
    usage_record_id = mapped_column(PostgreSQLUUID(as_uuid=True), unique=True, nullable=True)
    trace_artifact_version_id = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("artifact_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    trace_content_hash = mapped_column(Text, nullable=True)
    retry_parent_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    status = mapped_column(Text, nullable=False)
    row_version = mapped_column(Integer, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), nullable=False)
    started_at = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at = mapped_column(DateTime(timezone=True), nullable=True)
    request_receipt_id = mapped_column(PostgreSQLUUID(as_uuid=True), unique=True, nullable=False)
    start_receipt_id = mapped_column(PostgreSQLUUID(as_uuid=True), unique=True, nullable=True)
    finish_receipt_id = mapped_column(PostgreSQLUUID(as_uuid=True), unique=True, nullable=True)
    result_summary = mapped_column(Text, nullable=True)
    error_code = mapped_column(Text, nullable=True)


class CapabilityInvocationRefsModel(Base):
    __tablename__ = "capability_invocation_refs"
    __table_args__ = (
        CheckConstraint("direction IN ('INPUT','OUTPUT')"),
        CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'"),
        ForeignKeyConstraint(
            ["research_task_id", "project_id", "invocation_id"],
            [
                "capability_invocations.research_task_id",
                "capability_invocations.project_id",
                "capability_invocations.id",
            ],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["research_task_id", "project_id", "receipt_id"],
            [
                "research_task_command_receipts.research_task_id",
                "research_task_command_receipts.project_id",
                "research_task_command_receipts.id",
            ],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "num_nonnulls(research_question_version_id,hypothesis_version_id, claim_version_id,"
            "source_version_id,artifact_version_id,manuscript_version_id) = 1"
        ),
        CheckConstraint(
            "CASE WHEN source_version_id IS NOT NULL OR manuscript_version_id IS NOT NULL THEN "
            "hash_scheme IS NOT NULL AND hash_scheme = 'sha256-cjson-v1' ELSE hash_scheme IS "
            "NULL END"
        ),
        CheckConstraint("direction <> 'OUTPUT' OR artifact_version_id IS NOT NULL"),
        Index("pr303_refs_owner", "invocation_id", "direction", "id"),
        Index("pr303_refs_scope", "research_task_id", "project_id", "invocation_id"),
        Index("pr303_refs_receipt", "research_task_id", "project_id", "receipt_id"),
        Index(
            "pr303_refs_research_question",
            "invocation_id",
            "direction",
            "research_question_version_id",
            unique=True,
            postgresql_where=text("research_question_version_id IS NOT NULL"),
        ),
        Index(
            "pr303_refs_research_question_target",
            "research_question_version_id",
            postgresql_where=text("research_question_version_id IS NOT NULL"),
        ),
        Index(
            "pr303_refs_hypothesis",
            "invocation_id",
            "direction",
            "hypothesis_version_id",
            unique=True,
            postgresql_where=text("hypothesis_version_id IS NOT NULL"),
        ),
        Index(
            "pr303_refs_hypothesis_target",
            "hypothesis_version_id",
            postgresql_where=text("hypothesis_version_id IS NOT NULL"),
        ),
        Index(
            "pr303_refs_claim",
            "invocation_id",
            "direction",
            "claim_version_id",
            unique=True,
            postgresql_where=text("claim_version_id IS NOT NULL"),
        ),
        Index(
            "pr303_refs_claim_target",
            "claim_version_id",
            postgresql_where=text("claim_version_id IS NOT NULL"),
        ),
        Index(
            "pr303_refs_source",
            "invocation_id",
            "direction",
            "source_version_id",
            unique=True,
            postgresql_where=text("source_version_id IS NOT NULL"),
        ),
        Index(
            "pr303_refs_source_target",
            "source_version_id",
            postgresql_where=text("source_version_id IS NOT NULL"),
        ),
        Index(
            "pr303_refs_artifact",
            "invocation_id",
            "direction",
            "artifact_version_id",
            unique=True,
            postgresql_where=text("artifact_version_id IS NOT NULL"),
        ),
        Index(
            "pr303_refs_artifact_target",
            "artifact_version_id",
            postgresql_where=text("artifact_version_id IS NOT NULL"),
        ),
        Index(
            "pr303_refs_manuscript",
            "invocation_id",
            "direction",
            "manuscript_version_id",
            unique=True,
            postgresql_where=text("manuscript_version_id IS NOT NULL"),
        ),
        Index(
            "pr303_refs_manuscript_target",
            "manuscript_version_id",
            postgresql_where=text("manuscript_version_id IS NOT NULL"),
        ),
    )
    id = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, nullable=False)
    project_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    research_task_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    invocation_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    receipt_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    direction = mapped_column(Text, nullable=False)
    research_question_version_id = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("research_question_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    hypothesis_version_id = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("hypothesis_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    claim_version_id = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("claim_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    source_version_id = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("source_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    artifact_version_id = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("artifact_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    manuscript_version_id = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("manuscript_versions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    content_hash = mapped_column(Text, nullable=False)
    hash_scheme = mapped_column(Text, nullable=True)


class CapabilityInvocationEventsModel(Base):
    __tablename__ = "capability_invocation_events"
    __table_args__ = (
        CheckConstraint("sequence BETWEEN 1 AND 4"),
        CheckConstraint("invocation_row_version BETWEEN 1 AND 3"),
        CheckConstraint("event_type IN ('REQUESTED','STARTED','FINISHED','RECONCILED')"),
        CheckConstraint(
            "new_status IN ( 'REQUESTED','RUNNING','SUCCEEDED','FAILED','UNKNOWN_OUTCOME',"
            "'CANCELLED')"
        ),
        CheckConstraint("reconciled_outcome IN ('SUCCEEDED','FAILED','CANCELLED')"),
        CheckConstraint("length(btrim(reason)) BETWEEN 1 AND 8192 AND reason IS NFC NORMALIZED"),
        UniqueConstraint("research_task_id", "project_id", "id"),
        UniqueConstraint("invocation_id", "sequence"),
        ForeignKeyConstraint(
            ["research_task_id", "project_id", "invocation_id"],
            [
                "capability_invocations.research_task_id",
                "capability_invocations.project_id",
                "capability_invocations.id",
            ],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["research_task_id", "invocation_id", "reservation_id"],
            [
                "capability_invocations.research_task_id",
                "capability_invocations.id",
                "capability_invocations.reservation_id",
            ],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["research_task_id", "project_id", "receipt_id"],
            [
                "research_task_command_receipts.research_task_id",
                "research_task_command_receipts.project_id",
                "research_task_command_receipts.id",
            ],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["research_task_id", "reservation_id", "usage_record_id"],
            [
                "budget_usage_records.research_task_id",
                "budget_usage_records.reservation_id",
                "budget_usage_records.id",
            ],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "(event_type = 'REQUESTED' AND sequence = 1 AND invocation_row_version = 1 AND "
            "prior_status IS NULL AND new_status = 'REQUESTED' AND usage_record_id IS NULL) OR "
            "(event_type = 'STARTED' AND sequence = 2 AND invocation_row_version = 2 AND "
            "prior_status = 'REQUESTED' AND new_status = 'RUNNING' AND usage_record_id IS NULL)"
            " OR (event_type = 'FINISHED' AND usage_record_id IS NOT NULL AND ((sequence = 2 "
            "AND invocation_row_version = 2 AND prior_status = 'REQUESTED' AND new_status = "
            "'CANCELLED') OR (sequence = 3 AND invocation_row_version = 3 AND prior_status = "
            "'RUNNING' AND new_status IN ('SUCCEEDED','FAILED','UNKNOWN_OUTCOME','CANCELLED')))"
            ") OR (event_type = 'RECONCILED' AND sequence = 4 AND invocation_row_version = 3 "
            "AND prior_status = 'UNKNOWN_OUTCOME' AND new_status = 'UNKNOWN_OUTCOME' AND "
            "usage_record_id IS NOT NULL)"
        ),
        CheckConstraint("event_type = 'REQUESTED' OR prior_status IS NOT NULL"),
        CheckConstraint("(event_type = 'RECONCILED') = (reconciled_outcome IS NOT NULL)"),
        Index("pr303_events_scope", "research_task_id", "project_id", "invocation_id"),
        Index("pr303_events_reservation", "research_task_id", "invocation_id", "reservation_id"),
        Index("pr303_events_actor", "actor_id"),
        Index("pr303_events_usage", "research_task_id", "reservation_id", "usage_record_id"),
    )
    id = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, nullable=False)
    project_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    research_task_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    invocation_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    reservation_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    receipt_id = mapped_column(PostgreSQLUUID(as_uuid=True), unique=True, nullable=False)
    sequence = mapped_column(Integer, nullable=False)
    invocation_row_version = mapped_column(Integer, nullable=False)
    event_type = mapped_column(Text, nullable=False)
    prior_status = mapped_column(Text, nullable=True)
    new_status = mapped_column(Text, nullable=False)
    reconciled_outcome = mapped_column(Text, nullable=True)
    usage_record_id = mapped_column(PostgreSQLUUID(as_uuid=True), unique=True, nullable=True)
    actor_id = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("actors.id", ondelete="RESTRICT"), nullable=False
    )
    occurred_at = mapped_column(DateTime(timezone=True), nullable=False)
    reason = mapped_column(Text, nullable=False)


# PR3-02-S2 inert intent mappings. Migration 0081 owns the guards and DDL.


class AgentExecutionInstanceModel(Base):
    __tablename__ = "agent_execution_instances"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pr302s2_exec_pk"),
        CheckConstraint(
            "substring(id::text from 15 for 1) = '7' AND "
            "substring(id::text from 20 for 1) IN ('8','9','a','b')",
            name="pr302s2_exec_id_ck",
        ),
        CheckConstraint("status = 'CREATED'", name="pr302s2_exec_status_ck"),
        CheckConstraint("revision = 1", name="pr302s2_exec_revision_ck"),
        CheckConstraint(
            "task_revision_at_creation BETWEEN 1 AND 2147483647",
            name="pr302s2_exec_task_revision_ck",
        ),
        CheckConstraint("isfinite(created_at)", name="pr302s2_exec_time_ck"),
        CheckConstraint(
            "input_ref_hash ~ '^[0-9a-f]{64}$' AND harness_content_hash ~ '^[0-9a-f]{64}$'",
            name="pr302s2_exec_hashes_ck",
        ),
        CheckConstraint(
            "input_ref_hash_scheme = 'sha256-cjson-v1' AND harness_hash_scheme = 'sha256-bytes-v1'",
            name="pr302s2_exec_schemes_ck",
        ),
        ForeignKeyConstraint(
            ["research_task_id", "project_id"],
            ["research_tasks.id", "research_tasks.project_id"],
            name="pr302s2_exec_task_fk",
            onupdate="NO ACTION",
            ondelete="RESTRICT",
            deferrable=False,
            match="SIMPLE",
        ),
        ForeignKeyConstraint(
            ["research_task_id", "research_task_step_id"],
            ["research_task_steps.research_task_id", "research_task_steps.id"],
            name="pr302s2_exec_step_fk",
            onupdate="NO ACTION",
            ondelete="RESTRICT",
            deferrable=False,
            match="SIMPLE",
        ),
        ForeignKeyConstraint(
            ["agent_version_id", "project_id", "actor_id"],
            ["agent_versions.id", "agent_versions.project_id", "agent_versions.actor_id"],
            name="pr302s2_exec_version_fk",
            onupdate="NO ACTION",
            ondelete="RESTRICT",
            deferrable=False,
            match="SIMPLE",
        ),
        Index("pr302s2_exec_project_task", "project_id", "research_task_id", "id"),
        Index("pr302s2_exec_task_step", "research_task_id", "research_task_step_id"),
        Index("pr302s2_exec_version", "agent_version_id", "project_id", "actor_id"),
        Index("pr302s2_exec_actor", "actor_id"),
        Index("pr302s2_exec_harness", "harness_artifact_version_id"),
    )
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, nullable=False)
    project_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "projects.id",
            name="pr302s2_exec_project_fk",
            onupdate="NO ACTION",
            ondelete="RESTRICT",
            deferrable=False,
            match="SIMPLE",
        ),
        nullable=False,
    )
    research_task_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    research_task_step_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=True
    )
    task_revision_at_creation: Mapped[int] = mapped_column(Integer, nullable=False)
    agent_version_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    actor_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "actors.id",
            name="pr302s2_exec_actor_fk",
            onupdate="NO ACTION",
            ondelete="RESTRICT",
            deferrable=False,
            match="SIMPLE",
        ),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(Text, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    input_ref_hash: Mapped[str] = mapped_column(Text, nullable=False)
    input_ref_hash_scheme: Mapped[str] = mapped_column(Text, nullable=False)
    harness_artifact_version_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "artifact_versions.id",
            name="pr302s2_exec_harness_fk",
            onupdate="NO ACTION",
            ondelete="RESTRICT",
            deferrable=False,
            match="SIMPLE",
        ),
        nullable=False,
    )
    harness_content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    harness_hash_scheme: Mapped[str] = mapped_column(Text, nullable=False)


class AgentExecutionEventModel(Base):
    __tablename__ = "agent_execution_events"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pr302s2_event_pk"),
        CheckConstraint(
            "substring(id::text from 15 for 1) = '7' AND "
            "substring(id::text from 20 for 1) IN ('8','9','a','b')",
            name="pr302s2_event_id_ck",
        ),
        CheckConstraint(
            "sequence = 1 AND prior_status IS NULL AND new_status = 'CREATED'",
            name="pr302s2_event_initial_ck",
        ),
        CheckConstraint("isfinite(occurred_at)", name="pr302s2_event_time_ck"),
        CheckConstraint("reason = 'Execution intent created.'", name="pr302s2_event_reason_ck"),
        UniqueConstraint("execution_id", name="pr302s2_event_execution_uq"),
        UniqueConstraint("receipt_id", name="pr302s2_event_receipt_uq"),
        Index("pr302s2_event_actor", "actor_id"),
    )
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, nullable=False)
    execution_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "agent_execution_instances.id",
            name="pr302s2_event_execution_fk",
            onupdate="NO ACTION",
            ondelete="RESTRICT",
            deferrable=False,
            match="SIMPLE",
        ),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    prior_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_status: Mapped[str] = mapped_column(Text, nullable=False)
    actor_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "actors.id",
            name="pr302s2_event_actor_fk",
            onupdate="NO ACTION",
            ondelete="RESTRICT",
            deferrable=False,
            match="SIMPLE",
        ),
        nullable=False,
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    receipt_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "agent_command_receipts.id",
            name="pr302s2_event_receipt_fk",
            onupdate="NO ACTION",
            ondelete="RESTRICT",
            deferrable=False,
            match="SIMPLE",
        ),
        nullable=False,
    )


class ExperimentSearchSessionModel(Base):
    __tablename__ = "experiment_search_sessions"
    __table_args__ = (
        CheckConstraint(
            "(root_experiment_spec_version_id IS NULL AND root_experiment_spec_content_hash "
            "IS NULL) OR (root_experiment_spec_version_id IS NOT NULL AND "
            "root_experiment_spec_content_hash IS NOT NULL AND "
            "root_experiment_spec_content_hash ~ '^[0-9a-f]{64}$' )",
            name="pr316_session_experiment_spec_pair_ck",
        ),
        PrimaryKeyConstraint("id", name="pr316_session_pk"),
        CheckConstraint("pr316_uuid7(id)", name="pr316_session_id_ck"),
        CheckConstraint("isfinite(created_at)", name="pr316_session_time_ck"),
        UniqueConstraint("receipt_id", name="pr316_session_receipt_uq"),
        ForeignKeyConstraint(
            ["created_by"],
            ["actors.id"],
            name="pr316_session_actor_fk",
            ondelete="RESTRICT",
            deferrable=False,
        ),
        ForeignKeyConstraint(
            ["research_task_id", "receipt_id"],
            [
                "research_task_command_receipts.research_task_id",
                "research_task_command_receipts.id",
            ],
            name="pr316_session_receipt_fk",
            ondelete="RESTRICT",
            deferrable=False,
        ),
        UniqueConstraint("research_task_id", "id", name="pr316_session_scope_uq"),
        UniqueConstraint("research_task_id", "project_id", "id", name="pr316_session_project_uq"),
        ForeignKeyConstraint(
            ["research_task_id", "project_id"],
            ["research_tasks.id", "research_tasks.project_id"],
            name="pr316_session_task_fk",
            ondelete="RESTRICT",
            deferrable=False,
        ),
        ForeignKeyConstraint(
            ["research_task_id", "budget_id"],
            ["execution_budgets.research_task_id", "execution_budgets.id"],
            name="pr316_session_budget_fk",
            ondelete="RESTRICT",
            deferrable=False,
        ),
        ForeignKeyConstraint(
            ["root_hypothesis_version_id"],
            ["hypothesis_versions.id"],
            name="pr316_session_hypothesis_fk",
            ondelete="RESTRICT",
            deferrable=False,
        ),
        CheckConstraint(
            "(root_hypothesis_version_id IS NULL AND root_hypothesis_content_hash IS NULL) OR"
            " (root_hypothesis_version_id IS NOT NULL AND root_hypothesis_content_hash IS NOT"
            " NULL AND root_hypothesis_content_hash ~ '^[0-9a-f]{64}$' )",
            name="pr316_session_hypothesis_pair_ck",
        ),
        ForeignKeyConstraint(
            ["root_experiment_spec_version_id"],
            ["experiment_spec_versions.id"],
            name="pr316_session_experiment_spec_fk",
            ondelete="RESTRICT",
            deferrable=False,
        ),
        Index("pr316_session_task_project", "research_task_id", "project_id"),
        Index("pr316_session_budget", "research_task_id", "budget_id"),
        Index("pr316_session_project", "project_id", "id"),
        Index("pr316_session_hypothesis", "root_hypothesis_version_id"),
        Index("pr316_session_spec", "root_experiment_spec_version_id"),
        Index("pr316_session_actor", "created_by"),
        Index("pr316_session_receipt", "research_task_id", "receipt_id"),
    )
    id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    project_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    research_task_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    budget_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    root_hypothesis_version_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    root_hypothesis_content_hash = mapped_column(Text, nullable=True)
    root_experiment_spec_version_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    root_experiment_spec_content_hash = mapped_column(Text, nullable=True)
    created_by = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), nullable=False)
    receipt_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)


class ExperimentSearchNodeModel(Base):
    __tablename__ = "experiment_search_nodes"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pr316_node_pk"),
        CheckConstraint("pr316_uuid7(id)", name="pr316_node_id_ck"),
        CheckConstraint("isfinite(created_at)", name="pr316_node_time_ck"),
        UniqueConstraint("receipt_id", name="pr316_node_receipt_uq"),
        ForeignKeyConstraint(
            ["created_by"],
            ["actors.id"],
            name="pr316_node_actor_fk",
            ondelete="RESTRICT",
            deferrable=False,
        ),
        ForeignKeyConstraint(
            ["research_task_id", "receipt_id"],
            [
                "research_task_command_receipts.research_task_id",
                "research_task_command_receipts.id",
            ],
            name="pr316_node_receipt_fk",
            ondelete="RESTRICT",
            deferrable=False,
        ),
        UniqueConstraint("research_task_id", "search_session_id", "id", name="pr316_node_scope_uq"),
        ForeignKeyConstraint(
            ["research_task_id", "search_session_id"],
            ["experiment_search_sessions.research_task_id", "experiment_search_sessions.id"],
            name="pr316_node_session_fk",
            ondelete="RESTRICT",
            deferrable=False,
        ),
        ForeignKeyConstraint(
            ["research_task_id", "search_session_id", "parent_node_id"],
            [
                "experiment_search_nodes.research_task_id",
                "experiment_search_nodes.search_session_id",
                "experiment_search_nodes.id",
            ],
            name="pr316_node_parent_fk",
            ondelete="RESTRICT",
            deferrable=False,
        ),
        ForeignKeyConstraint(
            ["research_task_id", "reservation_id", "id"],
            [
                "budget_reservations.research_task_id",
                "budget_reservations.id",
                "budget_reservations.operation_id",
            ],
            name="pr316_node_reservation_fk",
            ondelete="RESTRICT",
            deferrable=False,
        ),
        UniqueConstraint("reservation_id", name="pr316_node_reservation_uq"),
        CheckConstraint(
            "(parent_node_id IS NULL AND depth=0) OR (parent_node_id IS NOT NULL AND "
            "parent_node_id<>id AND depth>0)",
            name="pr316_node_depth_ck",
        ),
        CheckConstraint(
            "branch_kind IN ( 'NEW_DIRECTION' , 'REFINEMENT' , 'ABLATION' , 'BASELINE' , "
            "'SCALE_UP' , 'DEBUG' , 'REPLICATION' )",
            name="pr316_node_branch_ck",
        ),
        CheckConstraint("pr316_reason(mutation_reason)", name="pr316_node_reason_ck"),
        ForeignKeyConstraint(
            ["hypothesis_version_id"],
            ["hypothesis_versions.id"],
            name="pr316_node_hypothesis_fk",
            ondelete="RESTRICT",
            deferrable=False,
        ),
        CheckConstraint(
            "(hypothesis_version_id IS NULL AND hypothesis_content_hash IS NULL) OR "
            "(hypothesis_version_id IS NOT NULL AND hypothesis_content_hash IS NOT NULL AND "
            "hypothesis_content_hash ~ '^[0-9a-f]{64}$' )",
            name="pr316_node_hypothesis_pair_ck",
        ),
        ForeignKeyConstraint(
            ["experiment_spec_version_id"],
            ["experiment_spec_versions.id"],
            name="pr316_node_experiment_spec_fk",
            ondelete="RESTRICT",
            deferrable=False,
        ),
        CheckConstraint(
            "(experiment_spec_version_id IS NULL AND experiment_spec_content_hash IS NULL) OR"
            " (experiment_spec_version_id IS NOT NULL AND experiment_spec_content_hash IS NOT"
            " NULL AND experiment_spec_content_hash ~ '^[0-9a-f]{64}$' )",
            name="pr316_node_experiment_spec_pair_ck",
        ),
        Index(
            "pr316_node_one_root",
            "search_session_id",
            unique=True,
            postgresql_where=text("parent_node_id IS NULL"),
        ),
        Index("pr316_node_parent", "research_task_id", "search_session_id", "parent_node_id"),
        Index("pr316_node_order", "search_session_id", "depth", "id"),
        Index("pr316_node_hypothesis", "hypothesis_version_id"),
        Index("pr316_node_spec", "experiment_spec_version_id"),
        Index("pr316_node_reservation", "research_task_id", "reservation_id", "id"),
        Index("pr316_node_actor", "created_by"),
        Index("pr316_node_receipt", "research_task_id", "receipt_id"),
    )
    id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    research_task_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    search_session_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    parent_node_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    depth = mapped_column(Integer, nullable=False)
    branch_kind = mapped_column(Text, nullable=False)
    mutation_reason = mapped_column(Text, nullable=False)
    hypothesis_version_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    hypothesis_content_hash = mapped_column(Text, nullable=True)
    experiment_spec_version_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    experiment_spec_content_hash = mapped_column(Text, nullable=True)
    reservation_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    created_by = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), nullable=False)
    receipt_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)


class ExperimentSearchNodeRunModel(Base):
    __tablename__ = "experiment_search_node_runs"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pr316_link_pk"),
        CheckConstraint("pr316_uuid7(id)", name="pr316_link_id_ck"),
        CheckConstraint("isfinite(created_at)", name="pr316_link_time_ck"),
        UniqueConstraint("receipt_id", name="pr316_link_receipt_uq"),
        ForeignKeyConstraint(
            ["created_by"],
            ["actors.id"],
            name="pr316_link_actor_fk",
            ondelete="RESTRICT",
            deferrable=False,
        ),
        ForeignKeyConstraint(
            ["research_task_id", "receipt_id"],
            [
                "research_task_command_receipts.research_task_id",
                "research_task_command_receipts.id",
            ],
            name="pr316_link_receipt_fk",
            ondelete="RESTRICT",
            deferrable=False,
        ),
        UniqueConstraint(
            "research_task_id", "search_session_id", "node_id", "id", name="pr316_link_scope_uq"
        ),
        UniqueConstraint("search_session_id", "node_id", "run_id", name="pr316_link_pair_uq"),
        ForeignKeyConstraint(
            ["research_task_id", "project_id", "search_session_id"],
            [
                "experiment_search_sessions.research_task_id",
                "experiment_search_sessions.project_id",
                "experiment_search_sessions.id",
            ],
            name="pr316_link_session_fk",
            ondelete="RESTRICT",
            deferrable=False,
        ),
        ForeignKeyConstraint(
            ["research_task_id", "search_session_id", "node_id"],
            [
                "experiment_search_nodes.research_task_id",
                "experiment_search_nodes.search_session_id",
                "experiment_search_nodes.id",
            ],
            name="pr316_link_node_fk",
            ondelete="RESTRICT",
            deferrable=False,
        ),
        ForeignKeyConstraint(
            ["run_id", "project_id"],
            ["runs.id", "runs.project_id"],
            name="pr316_link_run_fk",
            ondelete="RESTRICT",
            deferrable=False,
        ),
        Index("pr316_link_session_project", "research_task_id", "project_id", "search_session_id"),
        Index("pr316_link_run", "run_id", "project_id"),
        Index("pr316_link_order", "node_id", "id"),
        Index("pr316_link_actor", "created_by"),
        Index("pr316_link_receipt", "research_task_id", "receipt_id"),
    )
    id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    project_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    research_task_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    search_session_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    node_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    run_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    created_by = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), nullable=False)
    receipt_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)


class ExperimentSearchEventModel(Base):
    __tablename__ = "experiment_search_events"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pr316_event_pk"),
        CheckConstraint("pr316_uuid7(id)", name="pr316_event_id_ck"),
        CheckConstraint("isfinite(occurred_at)", name="pr316_event_time_ck"),
        UniqueConstraint("receipt_id", name="pr316_event_receipt_uq"),
        ForeignKeyConstraint(
            ["actor_id"],
            ["actors.id"],
            name="pr316_event_actor_fk",
            ondelete="RESTRICT",
            deferrable=False,
        ),
        ForeignKeyConstraint(
            ["research_task_id", "receipt_id"],
            [
                "research_task_command_receipts.research_task_id",
                "research_task_command_receipts.id",
            ],
            name="pr316_event_receipt_fk",
            ondelete="RESTRICT",
            deferrable=False,
        ),
        UniqueConstraint(
            "research_task_id", "search_session_id", "id", name="pr316_event_scope_uq"
        ),
        UniqueConstraint("search_session_id", "sequence", name="pr316_event_sequence_uq"),
        CheckConstraint("sequence>=1", name="pr316_event_sequence_ck"),
        CheckConstraint(
            "event_type IN ( 'SESSION_CREATED' , 'NODE_APPENDED' )", name="pr316_event_kind_ck"
        ),
        CheckConstraint("pr316_reason(reason)", name="pr316_event_reason_ck"),
        CheckConstraint(
            "(event_type= 'SESSION_CREATED' AND node_id IS NULL) OR (event_type= "
            "'NODE_APPENDED' AND node_id IS NOT NULL)",
            name="pr316_event_shape_ck",
        ),
        ForeignKeyConstraint(
            ["research_task_id", "search_session_id"],
            ["experiment_search_sessions.research_task_id", "experiment_search_sessions.id"],
            name="pr316_event_session_fk",
            ondelete="RESTRICT",
            deferrable=False,
        ),
        ForeignKeyConstraint(
            ["research_task_id", "search_session_id", "node_id"],
            [
                "experiment_search_nodes.research_task_id",
                "experiment_search_nodes.search_session_id",
                "experiment_search_nodes.id",
            ],
            name="pr316_event_node_fk",
            ondelete="RESTRICT",
            deferrable=False,
        ),
        Index(
            "pr316_event_one_creation",
            "search_session_id",
            unique=True,
            postgresql_where=text("event_type= 'SESSION_CREATED'"),
        ),
        Index(
            "pr316_event_one_node_creation",
            "node_id",
            unique=True,
            postgresql_where=text("event_type= 'NODE_APPENDED'"),
        ),
        Index("pr316_event_node", "research_task_id", "search_session_id", "node_id"),
        Index("pr316_event_actor", "actor_id"),
        Index("pr316_event_receipt", "research_task_id", "receipt_id"),
    )
    id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    research_task_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    search_session_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    node_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    sequence = mapped_column(Integer, nullable=False)
    event_type = mapped_column(Text, nullable=False)
    reason = mapped_column(Text, nullable=False)
    actor_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    occurred_at = mapped_column(DateTime(timezone=True), nullable=False)
    receipt_id = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
