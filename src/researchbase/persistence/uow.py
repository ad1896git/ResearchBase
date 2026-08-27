"""Synchronous SQLAlchemy UnitOfWork for one application transaction."""

from __future__ import annotations

from collections.abc import Callable
from types import TracebackType

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from researchbase.application.ports import (
    ActorRepository,
    ArtifactRepository,
    ArtifactVersionRepository,
    DatasetRepository,
    DatasetSnapshotRepository,
    ExperimentSpecRepository,
    HypothesisRepository,
    MetricDefinitionRepository,
    MetricDefinitionVersionRepository,
    ProjectRepository,
    ResearchQuestionRepository,
    RunRepository,
    WorkspaceRepository,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.repositories import (
    SqlAlchemyActorRepository,
    SqlAlchemyArtifactRepository,
    SqlAlchemyArtifactVersionRepository,
    SqlAlchemyDatasetRepository,
    SqlAlchemyDatasetSnapshotRepository,
    SqlAlchemyExperimentSpecRepository,
    SqlAlchemyHypothesisRepository,
    SqlAlchemyMetricDefinitionRepository,
    SqlAlchemyMetricDefinitionVersionRepository,
    SqlAlchemyProjectRepository,
    SqlAlchemyResearchQuestionRepository,
    SqlAlchemyRunRepository,
    SqlAlchemyWorkspaceRepository,
)


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
    runs: RunRepository

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
        self.runs = SqlAlchemyRunRepository(self._session)
        return self

    def commit(self) -> None:
        try:
            self._require_session().commit()
        except IntegrityError as exc:
            if "uq_actors_external_key" in str(exc.orig):
                raise ResearchBaseError(
                    ErrorCode.VALIDATION_ERROR,
                    "external_key is already in use",
                    {"field": "external_key"},
                ) from exc
            if (
                "uq_research_question_versions_parent_version" in str(exc.orig)
                or "uq_hypothesis_versions_parent_version" in str(exc.orig)
                or "uq_experiment_spec_versions_parent_version" in str(exc.orig)
                or "uq_metric_definition_versions_parent_version" in str(exc.orig)
            ):
                raise ResearchBaseError(
                    ErrorCode.VALIDATION_ERROR,
                    "version_number is already in use for this parent",
                    {"field": "version_number"},
                ) from exc
            if "uq_dataset_snapshots_dataset_content_hash" in str(exc.orig):
                raise ResearchBaseError(
                    ErrorCode.DUPLICATE_CONTENT,
                    "dataset snapshot content already exists for this dataset",
                ) from exc
            if "uq_artifact_versions_artifact_content_hash" in str(exc.orig):
                raise ResearchBaseError(
                    ErrorCode.DUPLICATE_CONTENT,
                    "artifact version content already exists for this artifact",
                ) from exc
            if "uq_artifact_versions_artifact_version" in str(exc.orig):
                raise ResearchBaseError(
                    ErrorCode.VALIDATION_ERROR,
                    "version number is already in use for this artifact",
                    {"field": "version_number"},
                ) from exc
            if "run_dataset_inputs_pkey" in str(exc.orig) or "run_artifact_inputs_pkey" in str(
                exc.orig
            ):
                raise ResearchBaseError(
                    ErrorCode.VALIDATION_ERROR,
                    "run input is already attached",
                ) from exc
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

    def _require_session(self) -> Session:
        if self._session is None:
            raise RuntimeError("UnitOfWork must be entered before use")
        return self._session
