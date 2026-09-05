"""Synchronous SQLAlchemy UnitOfWork for one application transaction."""

from __future__ import annotations

from collections.abc import Callable
from types import TracebackType

from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker

from researchbase.application.ports import (
    ActorRepository,
    ArtifactRepository,
    ArtifactVersionRepository,
    ClaimRepository,
    DatasetRepository,
    DatasetSnapshotRepository,
    ExperimentSpecRepository,
    GovernanceRepository,
    HypothesisRepository,
    MeasurementRepository,
    MetricDefinitionRepository,
    MetricDefinitionVersionRepository,
    ProjectRepository,
    ResearchQuestionRepository,
    RunRepository,
    StatisticalResultRepository,
    WorkspaceRepository,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.governance_repository import SqlAlchemyGovernanceRepository
from researchbase.persistence.repositories import (
    SqlAlchemyActorRepository,
    SqlAlchemyArtifactRepository,
    SqlAlchemyArtifactVersionRepository,
    SqlAlchemyClaimRepository,
    SqlAlchemyDatasetRepository,
    SqlAlchemyDatasetSnapshotRepository,
    SqlAlchemyExperimentSpecRepository,
    SqlAlchemyHypothesisRepository,
    SqlAlchemyMeasurementRepository,
    SqlAlchemyMetricDefinitionRepository,
    SqlAlchemyMetricDefinitionVersionRepository,
    SqlAlchemyProjectRepository,
    SqlAlchemyResearchQuestionRepository,
    SqlAlchemyRunRepository,
    SqlAlchemyStatisticalResultRepository,
    SqlAlchemyWorkspaceRepository,
)


def _normalize_database_error(exc: BaseException) -> ResearchBaseError | None:
    """Classify expected PostgreSQL failures from stable driver metadata."""
    if not isinstance(exc, DBAPIError):
        return None
    original = exc.orig
    sqlstate = getattr(original, "sqlstate", None)
    diagnostic = getattr(original, "diag", None)
    constraint = getattr(diagnostic, "constraint_name", None)
    if sqlstate == "P17D1":
        return ResearchBaseError(ErrorCode.IMMUTABLE_RECORD, "record is immutable")
    if sqlstate == "P17D2":
        return ResearchBaseError(ErrorCode.INVALID_STATE_TRANSITION, "invalid state transition")
    if sqlstate == "P17D3":
        return ResearchBaseError(
            ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
            "parent state does not permit this relation",
        )
    if sqlstate == "23503":
        return ResearchBaseError(
            ErrorCode.REFERENTIAL_INTEGRITY_ERROR, "referential integrity violation"
        )
    if sqlstate == "23505":
        duplicate_map = {
            "uq_research_question_versions_parent_version": (
                ErrorCode.VALIDATION_ERROR,
                "version_number is already in use for this parent",
            ),
            "uq_hypothesis_versions_parent_version": (
                ErrorCode.VALIDATION_ERROR,
                "version_number is already in use for this parent",
            ),
            "uq_experiment_spec_versions_parent_version": (
                ErrorCode.VALIDATION_ERROR,
                "version_number is already in use for this parent",
            ),
            "uq_metric_definition_versions_parent_version": (
                ErrorCode.VALIDATION_ERROR,
                "version_number is already in use for this parent",
            ),
            "uq_dataset_snapshots_dataset_content_hash": (
                ErrorCode.DUPLICATE_CONTENT,
                "dataset snapshot content already exists for this dataset",
            ),
            "uq_artifact_versions_artifact_content_hash": (
                ErrorCode.DUPLICATE_CONTENT,
                "artifact version content already exists for this artifact",
            ),
            "uq_artifact_versions_artifact_version": (
                ErrorCode.VALIDATION_ERROR,
                "version number is already in use for this artifact",
            ),
            "uq_actors_external_key": (
                ErrorCode.VALIDATION_ERROR,
                "external_key is already in use",
            ),
            "run_dataset_inputs_pkey": (
                ErrorCode.VALIDATION_ERROR,
                "run input is already attached",
            ),
            "run_artifact_inputs_pkey": (
                ErrorCode.VALIDATION_ERROR,
                "run input is already attached",
            ),
            "statistical_result_inputs_pkey": (
                ErrorCode.VALIDATION_ERROR,
                "statistical result input is already attached",
            ),
            "uq_evidence_measurement": (
                ErrorCode.VALIDATION_ERROR,
                "evidence relation is already attached",
            ),
            "uq_evidence_stat": (
                ErrorCode.VALIDATION_ERROR,
                "evidence relation is already attached",
            ),
        }
        mapped = duplicate_map.get(constraint) if isinstance(constraint, str) else None
        if mapped is not None:
            code, message = mapped
            return ResearchBaseError(code, message)
    return None


class SqlAlchemyUnitOfWork:
    actors: ActorRepository
    projects: ProjectRepository
    workspaces: WorkspaceRepository
    research_questions: ResearchQuestionRepository
    hypotheses: HypothesisRepository
    experiment_specs: ExperimentSpecRepository
    datasets: DatasetRepository
    dataset_snapshots: DatasetSnapshotRepository
    artifacts: ArtifactRepository
    artifact_versions: ArtifactVersionRepository
    metric_definitions: MetricDefinitionRepository
    metric_definition_versions: MetricDefinitionVersionRepository
    measurements: MeasurementRepository
    statistical_results: StatisticalResultRepository
    runs: RunRepository
    claims: ClaimRepository
    governance: GovernanceRepository

    def __init__(self, session_factory: Callable[[], Session] | sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._session: Session | None = None

        self._committed = False

    def __enter__(self) -> SqlAlchemyUnitOfWork:
        self._session = self._session_factory()
        self._session.begin()
        self.actors = SqlAlchemyActorRepository(self._session)
        self.projects = SqlAlchemyProjectRepository(self._session)
        self.workspaces = SqlAlchemyWorkspaceRepository(self._session)
        self.research_questions = SqlAlchemyResearchQuestionRepository(self._session)
        self.hypotheses = SqlAlchemyHypothesisRepository(self._session)
        self.experiment_specs = SqlAlchemyExperimentSpecRepository(self._session)
        self.datasets = SqlAlchemyDatasetRepository(self._session)
        self.dataset_snapshots = SqlAlchemyDatasetSnapshotRepository(self._session)
        self.artifacts = SqlAlchemyArtifactRepository(self._session)
        self.artifact_versions = SqlAlchemyArtifactVersionRepository(self._session)
        self.metric_definitions = SqlAlchemyMetricDefinitionRepository(self._session)
        self.metric_definition_versions = SqlAlchemyMetricDefinitionVersionRepository(self._session)
        self.measurements = SqlAlchemyMeasurementRepository(self._session)
        self.statistical_results = SqlAlchemyStatisticalResultRepository(self._session)
        self.runs = SqlAlchemyRunRepository(self._session)
        self.claims = SqlAlchemyClaimRepository(self._session)
        self.governance = SqlAlchemyGovernanceRepository(self._session)
        return self

    def commit(self) -> None:
        try:
            self._require_session().commit()
        except DBAPIError as exc:
            normalized = _normalize_database_error(exc)
            if normalized is not None:
                raise normalized from exc
            raise
        self._committed = True

    def rollback(self) -> None:
        self._require_session().rollback()
        self._committed = False

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._session is None:
            return
        if exc_type is not None or not self._committed:
            self._session.rollback()
        self._session.close()
        self._session = None
        if exc_value is not None:
            normalized = _normalize_database_error(exc_value)
            if normalized is not None:
                raise normalized from exc_value

    def _require_session(self) -> Session:
        if self._session is None:
            raise RuntimeError("UnitOfWork must be entered before use")
        return self._session
