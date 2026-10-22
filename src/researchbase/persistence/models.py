"""SQLAlchemy persistence models for the PR-02 identity slice."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CHAR,
    BigInteger,
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
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION, JSONB
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
        CheckConstraint(
            "command_name IN ( 'create_research_task','create_task_plan','add_task_step', 'add_task_step_dependency','seal_task_plan','cancel_research_task')"  # noqa: E501
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


class ResearchTaskEventsModel(Base):
    __tablename__ = "research_task_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ( 'CREATED','PLAN_CREATED','STEP_ADDED','DEPENDENCY_ADDED','PLAN_SEALED','CANCELLED')"  # noqa: E501
        ),
        CheckConstraint("sequence >= 1"),
        CheckConstraint("task_row_version >= 1"),
        UniqueConstraint("research_task_id", "id"),
        UniqueConstraint("research_task_id", "sequence"),
        UniqueConstraint("research_task_id", "task_row_version"),
        CheckConstraint("(sequence = task_row_version"),
        CheckConstraint(
            "( (event_type = 'CREATED' AND prior_status IS NULL AND new_status = 'CREATED') OR (event_type = 'PLAN_CREATED' AND prior_status = 'CREATED' AND new_status = 'PLANNING') OR (event_type IN ('STEP_ADDED','DEPENDENCY_ADDED','PLAN_SEALED') AND prior_status = 'PLANNING' AND new_status = 'PLANNING') OR (event_type = 'CANCELLED' AND prior_status IN ('CREATED','PLANNING') AND new_status = 'CANCELLED')"  # noqa: E501
        ),
        CheckConstraint("(event_type = 'CREATED' OR prior_status IS NOT NULL"),
        CheckConstraint(
            "(CASE WHEN event_type = 'CANCELLED' THEN reason IS NOT NULL AND length(btrim(reason)) > 0 AND reason IS NFC NORMALIZED ELSE reason IS NULL END"  # noqa: E501
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
        Index("pr301_task_events_actor", "actor_id"),
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
