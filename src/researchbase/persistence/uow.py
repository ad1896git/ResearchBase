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
    Phase2IdentityRepository,
    ProjectRepository,
    ResearchQuestionRepository,
    RunRepository,
    StatisticalResultRepository,
    WorkspaceRepository,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.structured_logging import emit_uow_rollback
from researchbase.persistence.discussion_repository import SqlAlchemyDiscussionRepository
from researchbase.persistence.governance_repository import SqlAlchemyGovernanceRepository
from researchbase.persistence.internal_review_repository import SqlAlchemyInternalReviewRepository
from researchbase.persistence.literature_evidence_repository import (
    SqlAlchemyLiteratureEvidenceRepository,
)
from researchbase.persistence.literature_search_execution_repository import (
    SqlAlchemyLiteratureSearchExecutionRepository,
)
from researchbase.persistence.literature_search_plan_repository import (
    SqlAlchemyLiteratureSearchPlanRepository,
)
from researchbase.persistence.metadata_observation_repository import (
    SqlAlchemyMetadataObservationRepository,
)
from researchbase.persistence.phase2_identity_repository import SqlAlchemyPhase2IdentityRepository
from researchbase.persistence.publication_repository import SqlAlchemyPublicationRepository
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
from researchbase.persistence.scientific_conclusion_repository import (
    SqlAlchemyScientificConclusionRepository,
)
from researchbase.persistence.source_identity_repository import SqlAlchemySourceIdentityRepository
from researchbase.persistence.source_merge_repository import SqlAlchemySourceMergeRepository
from researchbase.persistence.source_version_repository import SqlAlchemySourceVersionRepository


def _normalize_database_error(exc: BaseException) -> ResearchBaseError | None:
    """Classify expected PostgreSQL failures from stable driver metadata."""
    if not isinstance(exc, DBAPIError):
        return None
    original = exc.orig
    sqlstate = getattr(original, "sqlstate", None)
    diagnostic = getattr(original, "diag", None)
    constraint = getattr(diagnostic, "constraint_name", None)
    if sqlstate == "40001":
        return ResearchBaseError(
            ErrorCode.CONCURRENT_MODIFICATION,
            "serializable transaction must be retried",
        )
    if sqlstate == "P17D1":
        return ResearchBaseError(ErrorCode.IMMUTABLE_RECORD, "record is immutable")
    if sqlstate == "P17D2":
        return ResearchBaseError(ErrorCode.INVALID_STATE_TRANSITION, "invalid state transition")
    if sqlstate == "P17D3":
        return ResearchBaseError(
            ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
            "parent state does not permit this relation",
        )
    if sqlstate == "P17D4":
        return ResearchBaseError(ErrorCode.VALIDATION_ERROR, "database preflight validation failed")
    if sqlstate == "P17D5":
        return ResearchBaseError(
            ErrorCode.CONCURRENT_MODIFICATION,
            "resource was modified concurrently",
        )
    if sqlstate == "23514":
        if constraint == "ck_project_owner_coverage":
            return ResearchBaseError(
                ErrorCode.OWNER_COVERAGE_GAP,
                "operation would break continuous project OWNER coverage",
            )
        if "immutable" in str(original).lower():
            return ResearchBaseError(ErrorCode.IMMUTABLE_RECORD, "record is immutable")
        return ResearchBaseError(ErrorCode.VALIDATION_ERROR, "database check constraint violated")
    if sqlstate == "23503":
        return ResearchBaseError(
            ErrorCode.REFERENTIAL_INTEGRITY_ERROR, "referential integrity violation"
        )
    if sqlstate == "23505":
        duplicate_map = {
            "uq_source_identifier_live_value": (
                ErrorCode.IDENTIFIER_ALREADY_BOUND,
                "identifier is already bound",
            ),
            "uq_source_identifier_corrected_predecessor": (
                ErrorCode.SOURCE_IDENTITY_CONFLICT,
                "rejected identifier already has a corrected successor",
            ),
            "uq_literature_command_receipt_scope": (
                ErrorCode.CONCURRENT_MODIFICATION,
                "literature command receipt was concurrently committed",
            ),
            "uq_lse_project_idempotency": (
                ErrorCode.IDEMPOTENCY_CONFLICT,
                "execution idempotency key already exists",
            ),
            "uq_lse_receipt_scope": (
                ErrorCode.CONCURRENT_MODIFICATION,
                "execution command receipt was concurrently committed",
            ),
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
            details = None
            if constraint == "uq_actors_external_key":
                details = {"field": "external_key"}
            elif constraint in {
                "uq_research_question_versions_parent_version",
                "uq_hypothesis_versions_parent_version",
                "uq_experiment_spec_versions_parent_version",
                "uq_metric_definition_versions_parent_version",
                "uq_artifact_versions_artifact_version",
            }:
                details = {"field": "version_number"}
            return ResearchBaseError(code, message, details)
    return None


def _decision_database_error(exc: DBAPIError) -> ResearchBaseError:
    """PR2-15 opt-in classification from driver codes, never raw diagnostics."""
    state = getattr(exc.orig, "sqlstate", None)
    codes = {
        "P17F1": ErrorCode.IMMUTABLE_RECORD,
        "P17F2": ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
        "P17F3": ErrorCode.IDEMPOTENCY_CONFLICT,
        "40001": ErrorCode.CONCURRENT_MODIFICATION,
        "40P01": ErrorCode.CONCURRENT_MODIFICATION,
    }
    code = codes.get(state) if isinstance(state, str) else None
    if code is not None:
        return ResearchBaseError(code, "decision transaction rejected")
    normalized = _normalize_database_error(exc)
    if normalized is not None:
        return normalized
    # Unknown failures are not classified as safe to retry or as a successful commit.
    return ResearchBaseError(ErrorCode.INVALID_STATE_TRANSITION, "decision transaction failed")


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
    phase2_identity: Phase2IdentityRepository
    source_identity: SqlAlchemySourceIdentityRepository
    source_merge: SqlAlchemySourceMergeRepository
    source_version: SqlAlchemySourceVersionRepository
    literature_search_plan: SqlAlchemyLiteratureSearchPlanRepository
    metadata_observations: SqlAlchemyMetadataObservationRepository
    literature_evidence: SqlAlchemyLiteratureEvidenceRepository
    literature_search_execution: SqlAlchemyLiteratureSearchExecutionRepository
    discussion: SqlAlchemyDiscussionRepository
    scientific_conclusion: SqlAlchemyScientificConclusionRepository
    publication: SqlAlchemyPublicationRepository

    def __init__(
        self,
        session_factory: Callable[[], Session] | sessionmaker[Session],
        *,
        pr204_error_normalization: bool = False,
    ) -> None:
        self._session_factory = session_factory
        self._pr204_error_normalization = pr204_error_normalization
        self._decision_error_normalization = False
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
        self.phase2_identity = SqlAlchemyPhase2IdentityRepository(self._session)
        self.metadata_observations = SqlAlchemyMetadataObservationRepository(self._session)
        self.source_identity = SqlAlchemySourceIdentityRepository(self._session)
        self.source_merge = SqlAlchemySourceMergeRepository(self._session)
        self.source_version = SqlAlchemySourceVersionRepository(self._session)
        self.literature_evidence = SqlAlchemyLiteratureEvidenceRepository(self._session)
        self.literature_search_plan = SqlAlchemyLiteratureSearchPlanRepository(self._session)
        self.literature_search_execution = SqlAlchemyLiteratureSearchExecutionRepository(
            self._session
        )
        self.discussion = SqlAlchemyDiscussionRepository(self._session)
        self.scientific_conclusion = SqlAlchemyScientificConclusionRepository(self._session)
        self.publication = SqlAlchemyPublicationRepository(self._session)
        self.internal_review = SqlAlchemyInternalReviewRepository(self._session)
        return self

    def begin_serializable(self) -> None:
        """Set SERIALIZABLE before the first SQL statement in this UoW."""

        self._require_session().connection(execution_options={"isolation_level": "SERIALIZABLE"})

    def commit(self) -> None:
        try:
            self._require_session().commit()
        except DBAPIError as exc:
            if self._decision_error_normalization:
                raise _decision_database_error(exc) from None
            normalized = _normalize_database_error(exc)
            if (
                normalized is None
                and self._pr204_error_normalization
                and getattr(exc.orig, "sqlstate", None) == "40P01"
            ):
                normalized = ResearchBaseError(
                    ErrorCode.CONCURRENT_MODIFICATION,
                    "deadlocked PR2-04 transaction must be retried",
                )
            if (
                normalized is None
                and self._pr204_error_normalization
                and exc.connection_invalidated
            ):
                normalized = ResearchBaseError(
                    ErrorCode.CONCURRENT_MODIFICATION,
                    "PR2-04 transaction connection was lost; reread before retry",
                )
            if normalized is not None:
                raise normalized from exc
            raise
        self._committed = True

    def rollback(self) -> None:
        self._require_session().rollback()
        self._committed = False

    def enable_decision_error_normalization(self) -> None:
        """Apply the command's nondisclosing boundary without changing older commands."""
        self._decision_error_normalization = True

    def _exit_decision(self, exc_value: BaseException | None) -> None:
        session = self._require_session()
        cleanup_error: BaseException | None = None
        try:
            if exc_value is not None or not self._committed:
                try:
                    session.rollback()
                    emit_uow_rollback(getattr(getattr(exc_value, "code", None), "value", None))
                except BaseException as exc:
                    cleanup_error = exc
        finally:
            try:
                session.close()
            except BaseException as exc:
                cleanup_error = cleanup_error or exc
            finally:
                self._session = None
        if isinstance(exc_value, DBAPIError):
            raise _decision_database_error(exc_value) from None
        if exc_value is None and cleanup_error is not None:
            if isinstance(cleanup_error, DBAPIError):
                raise _decision_database_error(cleanup_error) from None
            raise cleanup_error

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._session is None:
            return
        if self._decision_error_normalization:
            self._exit_decision(exc_value)
            return
        if self._pr204_error_normalization:
            cleanup_error: BaseException | None = None
            try:
                if exc_type is not None or not self._committed:
                    try:
                        self._session.rollback()
                        emit_uow_rollback(getattr(getattr(exc_value, "code", None), "value", None))
                    except BaseException as rollback_error:
                        cleanup_error = rollback_error
            finally:
                try:
                    self._session.close()
                except BaseException as close_error:
                    cleanup_error = cleanup_error or close_error
                finally:
                    self._session = None
            if cleanup_error is not None:
                if exc_value is None:
                    normalized_cleanup = (
                        _normalize_database_error(cleanup_error)
                        if isinstance(cleanup_error, DBAPIError)
                        else None
                    )
                    if (
                        normalized_cleanup is None
                        and isinstance(cleanup_error, DBAPIError)
                        and (
                            cleanup_error.connection_invalidated
                            or getattr(cleanup_error.orig, "sqlstate", None) == "40P01"
                        )
                    ):
                        normalized_cleanup = ResearchBaseError(
                            ErrorCode.CONCURRENT_MODIFICATION,
                            "PR2-04 transaction cleanup failed; reread before retry",
                        )
                    if normalized_cleanup is not None:
                        raise normalized_cleanup from cleanup_error
                    raise cleanup_error
                if hasattr(exc_value, "add_note"):
                    exc_value.add_note(
                        "PR2-04 transaction cleanup failed; session closure attempted"
                    )
        else:
            if exc_type is not None or not self._committed:
                self._session.rollback()
                emit_uow_rollback(getattr(getattr(exc_value, "code", None), "value", None))
            self._session.close()
            self._session = None
        if exc_value is not None:
            normalized = _normalize_database_error(exc_value)
            if (
                normalized is None
                and self._pr204_error_normalization
                and isinstance(exc_value, DBAPIError)
                and getattr(exc_value.orig, "sqlstate", None) == "40P01"
            ):
                normalized = ResearchBaseError(
                    ErrorCode.CONCURRENT_MODIFICATION,
                    "deadlocked PR2-04 transaction must be retried",
                )
            if (
                normalized is None
                and self._pr204_error_normalization
                and isinstance(exc_value, DBAPIError)
                and exc_value.connection_invalidated
            ):
                normalized = ResearchBaseError(
                    ErrorCode.CONCURRENT_MODIFICATION,
                    "PR2-04 transaction connection was lost; reread before retry",
                )
            if normalized is not None:
                raise normalized from exc_value

    def _require_session(self) -> Session:
        if self._session is None:
            raise RuntimeError("UnitOfWork must be entered before use")
        return self._session
