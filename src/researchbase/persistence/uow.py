"""Synchronous SQLAlchemy UnitOfWork for one application transaction."""

from __future__ import annotations

from collections.abc import Callable
from types import TracebackType

from sqlalchemy import create_engine
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker

from researchbase.agent_runtime.ports.agent_repository import UncertainAgentCommit
from researchbase.agent_runtime.ports.task_repository import UncertainTaskCommit
from researchbase.application.ports import (
    ActorRepository,
    ArtifactRepository,
    ArtifactVersionRepository,
    AuthorshipRepository,
    ClaimRepository,
    DatasetRepository,
    DatasetSnapshotRepository,
    DiscussionHypothesisRepository,
    ExperimentSpecRepository,
    GovernanceRepository,
    HypothesisRepository,
    MeasurementRepository,
    MetricDefinitionRepository,
    MetricDefinitionVersionRepository,
    Phase2IdentityRepository,
    PreparedSubmissionRepository,
    ProjectRepository,
    ResearchQuestionRepository,
    RunRepository,
    SearchResultResolutionRepository,
    StatisticalResultRepository,
    StrategyCandidatePromotionRepository,
    WorkspaceRepository,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.structured_logging import emit_uow_rollback
from researchbase.persistence.agent_version_repository import SqlAlchemyAgentRepository
from researchbase.persistence.approval_repository import SqlAlchemyApprovalRepository
from researchbase.persistence.authorship_repository import SqlAlchemyAuthorshipRepository
from researchbase.persistence.capability_gateway_repository import SqlAlchemyGatewayRepository
from researchbase.persistence.context_repository import SqlAlchemyContextRepository
from researchbase.persistence.decision_repository import SqlAlchemyDecisionRepository
from researchbase.persistence.discussion_hypothesis_repository import (
    SqlAlchemyDiscussionHypothesisRepository,
)
from researchbase.persistence.discussion_repository import SqlAlchemyDiscussionRepository
from researchbase.persistence.experiment_search_repository import (
    SqlAlchemyExperimentSearchRepository,
)
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
from researchbase.persistence.manuscript_freeze_repository import (
    SqlAlchemyManuscriptFreezeRepository,
)
from researchbase.persistence.metadata_observation_repository import (
    SqlAlchemyMetadataObservationRepository,
)
from researchbase.persistence.novelty_repository import SqlAlchemyNoveltyRepository
from researchbase.persistence.phase2_identity_repository import SqlAlchemyPhase2IdentityRepository
from researchbase.persistence.prepared_submission_repository import (
    SqlAlchemyPreparedSubmissionRepository,
)
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
from researchbase.persistence.research_task_repository import SqlAlchemyResearchTaskRepository
from researchbase.persistence.revision_action_repository import SqlAlchemyRevisionActionRepository
from researchbase.persistence.scientific_conclusion_repository import (
    SqlAlchemyScientificConclusionRepository,
)
from researchbase.persistence.search_result_resolution_repository import (
    SqlAlchemySearchResultResolutionRepository,
)
from researchbase.persistence.source_identity_repository import SqlAlchemySourceIdentityRepository
from researchbase.persistence.source_merge_repository import SqlAlchemySourceMergeRepository
from researchbase.persistence.source_version_repository import SqlAlchemySourceVersionRepository
from researchbase.persistence.strategy_candidate_promotion_repository import (
    SqlAlchemyStrategyCandidatePromotionRepository,
)
from researchbase.persistence.task_safety_repository import SqlAlchemyTaskSafetyRepository


def _normalize_database_error(
    exc: BaseException, *, retry_deadlocks: bool = False
) -> ResearchBaseError | None:
    """Classify expected PostgreSQL failures from stable driver metadata."""
    if not isinstance(exc, DBAPIError):
        return None
    original = exc.orig
    sqlstate = getattr(original, "sqlstate", None)
    diagnostic = getattr(original, "diag", None)
    constraint = getattr(diagnostic, "constraint_name", None)
    if sqlstate == "40P01" and retry_deadlocks:
        return ResearchBaseError(
            ErrorCode.CONCURRENT_MODIFICATION,
            "deadlocked serializable transaction must be retried",
        )
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
    if sqlstate == "23P01" and constraint == "ex_project_role_assignments_role_interval":
        return ResearchBaseError(
            ErrorCode.INVALID_STATE_TRANSITION,
            "role interval overlaps an existing role assignment",
        )
    if sqlstate == "23514":
        if constraint == "pr302_scope":
            return ResearchBaseError(ErrorCode.FORBIDDEN, "Agent enrollment scope is unavailable")
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
            "uq_project_role_assignments_open": (
                ErrorCode.INVALID_STATE_TRANSITION,
                "open role assignment already exists for this membership and role",
            ),
            "uq_project_role_events_assignment_request": (
                ErrorCode.IDEMPOTENCY_CONFLICT,
                "role event request_id already used for this role assignment",
            ),
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
    if state == "55P03":
        # Preserve the generic Decision classification for other command surfaces.
        # The opted-in writers distinguish receipt recovery from mutation retries.
        return ResearchBaseError(
            ErrorCode.INVALID_STATE_TRANSITION,
            "decision lock timeout",
            {"reload_governance_receipt": True},
        )
    codes = {
        "P17R1": ErrorCode.INVALID_STATE_TRANSITION,
        "P17F1": ErrorCode.IMMUTABLE_RECORD,
        "P17F2": ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
        "P17F3": ErrorCode.IDEMPOTENCY_CONFLICT,
        "40001": ErrorCode.CONCURRENT_MODIFICATION,
        "40P01": ErrorCode.CONCURRENT_MODIFICATION,
    }
    code = codes.get(state) if isinstance(state, str) else None
    if code is not None:
        return ResearchBaseError(code, "decision transaction rejected")
    constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
    if state == "23505" and constraint == "decision_records_pkey":
        return ResearchBaseError(
            ErrorCode.IDEMPOTENCY_CONFLICT,
            "reload exact Decision after rollback",
            {"reload_decision": True},
        )
    if state == "23505" and constraint in {"uq_b08_issue_terminal", "review_issue_events_pkey"}:
        return ResearchBaseError(ErrorCode.IDEMPOTENCY_CONFLICT, "reload issue disposition")
    if state == "23505" and constraint == "uq_b07_decision_concern":
        return ResearchBaseError(
            ErrorCode.IDEMPOTENCY_CONFLICT, "concern decision already recorded"
        )
    if state == "23505" and constraint == "pk_b07_action_re_review":
        return ResearchBaseError(ErrorCode.IDEMPOTENCY_CONFLICT, "reload concern correspondence")
    if state == "23505" and constraint == "uq_revision_action_predecessor":
        return ResearchBaseError(
            ErrorCode.INVALID_STATE_TRANSITION, "predecessor already superseded"
        )
    normalized = _normalize_database_error(exc)
    if normalized is not None:
        return normalized
    # Unknown failures are not classified as safe to retry or as a successful commit.
    return ResearchBaseError(ErrorCode.INVALID_STATE_TRANSITION, "decision transaction failed")


def _issue_disposition_database_error(exc: DBAPIError) -> ResearchBaseError:
    """B08 separates read-only timeout recovery from fresh-UoW mutation retries."""
    error = _decision_database_error(exc)
    if getattr(exc.orig, "sqlstate", None) == "55P03":
        return ResearchBaseError(
            ErrorCode.CONCURRENT_MODIFICATION,
            "issue disposition lock timeout",
            {"reload_b08_receipt": True},
        )
    if getattr(exc.orig, "sqlstate", None) in {"40001", "40P01"}:
        return ResearchBaseError(error.code, error.message, {"retryable_b08": True})
    return error


def _approval_database_error(exc: DBAPIError, *, strict: bool = False) -> ResearchBaseError:
    state = getattr(exc.orig, "sqlstate", None)
    codes = {
        "P10B1": ErrorCode.DECISION_BASIS_INVALID,
        "P04M3": ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
        "P14P1": ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
        "P14I1": ErrorCode.IMMUTABLE_RECORD,
        "P14A1": ErrorCode.FORBIDDEN,
        "P16P1": ErrorCode.APPROVAL_PURPOSE_TARGET_COMMAND_INVALID,
        "P16T1": ErrorCode.APPROVAL_TARGET_STALE,
        "P16R1": ErrorCode.REJECTION_RECONSIDERATION_REQUIRED,
        "P16B1": ErrorCode.DECISION_BASIS_INVALID,
        "P16G1": ErrorCode.APPROVAL_GATE_FAILED,
        "P16C1": ErrorCode.CONFLICT_OF_INTEREST,
        "P16A1": ErrorCode.FORBIDDEN,
    }
    constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
    if state in {"40001", "40P01"}:
        return ResearchBaseError(
            ErrorCode.CONCURRENT_MODIFICATION,
            "decision transaction rejected",
            {"retryable_b13": True},
        )
    if state == "P13S1":
        return ResearchBaseError(ErrorCode.GRANT_STALE, "issuing authority lost")
    if state == "P13G1":
        return ResearchBaseError(ErrorCode.GRANT_INVALID, "grant unavailable")
    if state == "23505" and constraint == "uq_b13_command_key":
        return ResearchBaseError(
            ErrorCode.IDEMPOTENCY_CONFLICT, "command key already committed", {"b13_key_race": True}
        )
    if state == "23505" and constraint in {
        "uq_b17_frozen_publication",
        "uq_b17_package_consumption",
    }:
        return ResearchBaseError(ErrorCode.CONCURRENT_MODIFICATION, "competing package freeze")
    if state in {"P15S1", "P15S2", "P15S3"}:
        return ResearchBaseError(
            {
                "P15S1": ErrorCode.IMMUTABLE_RECORD,
                "P15S2": ErrorCode.INVALID_STATE_TRANSITION,
                "P15S3": ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
            }[state],
            "package transaction rejected",
        )
    if state == "23505" and constraint == "uq_b13_consumption_grant":
        return ResearchBaseError(ErrorCode.GRANT_INVALID, "grant already consumed")
    if state == "23514" and constraint == "ck_b13_result_tuple":
        return ResearchBaseError(
            ErrorCode.APPROVAL_PURPOSE_TARGET_COMMAND_INVALID, "result binding unavailable"
        )
    if state == "23505" and constraint == "uq_b10_successor_reconsideration":
        return ResearchBaseError(ErrorCode.IDEMPOTENCY_CONFLICT, "reconsideration already used")
    if state == "23514" and constraint in {"ck_b10_request_links"}:
        return ResearchBaseError(
            ErrorCode.REJECTION_RECONSIDERATION_REQUIRED, "successor links required"
        )
    if state == "23514" and constraint in {
        "ck_b10_text_bounds",
        "ck_b10_finite_time",
        "ck_b10_decision_pair",
    }:
        return ResearchBaseError(ErrorCode.VALIDATION_ERROR, "invalid reconsideration material")
    if state == "23514" and constraint in {"ck_b09_request_tuple", "ck_b09_grant_tuple"}:
        return ResearchBaseError(
            ErrorCode.APPROVAL_PURPOSE_TARGET_COMMAND_INVALID, "unlisted approval tuple"
        )
    if state == "23505" and constraint in {
        "uq_b09_pending_conclusion",
        "uq_b09_pending_manuscript",
    }:
        return ResearchBaseError(
            ErrorCode.IDEMPOTENCY_CONFLICT, "pending exact approval already exists"
        )
    if state in {"55P03", "57014"}:
        return ResearchBaseError(ErrorCode.CONCURRENT_MODIFICATION, "database wait timed out")
    if state in codes:
        return ResearchBaseError(codes[state], "approval transaction rejected")
    if strict:
        ready_codes = {
            "P17F1": ErrorCode.IMMUTABLE_RECORD,
            "P17F2": ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
            "P17D1": ErrorCode.IMMUTABLE_RECORD,
            "P04M1": ErrorCode.IMMUTABLE_RECORD,
            "P04M2": ErrorCode.APPROVAL_GATE_FAILED,
            "P14B1": ErrorCode.APPROVAL_GATE_FAILED,
            "P14C1": ErrorCode.CONCURRENT_MODIFICATION,
            "23503": ErrorCode.REFERENTIAL_INTEGRITY_ERROR,
        }
        if state in ready_codes:
            return ResearchBaseError(ready_codes[state], "readiness transaction rejected")
        if state == "23505" and constraint in {"uq_b14_ready_event", "uq_b14_ready_consumption"}:
            return ResearchBaseError(ErrorCode.IMMUTABLE_RECORD, "READY history already sealed")
        if state == "23514" and constraint in {
            "ck_b14a_publication_status",
            "ck_b14a_event_tuple",
            "ck_b14a_event_time",
            "ck_b13_hash",
            "ck_b13_time",
            "ck_b13_dto",
        }:
            return ResearchBaseError(
                ErrorCode.VALIDATION_ERROR, "invalid closed readiness material"
            )
        raise RuntimeError("readiness transaction failed; recover by exact command key") from None
    return _decision_database_error(exc)


def _authorship_database_error(exc: DBAPIError) -> ResearchBaseError:
    state = getattr(exc.orig, "sqlstate", None)
    codes = {
        "P17A1": ErrorCode.IMMUTABLE_RECORD,
        "P17A2": ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
        "P17A3": ErrorCode.VALIDATION_ERROR,
        "23503": ErrorCode.REFERENTIAL_INTEGRITY_ERROR,
        "23514": ErrorCode.VALIDATION_ERROR,
        "23502": ErrorCode.VALIDATION_ERROR,
        "23505": ErrorCode.CONCURRENT_MODIFICATION,
        "40001": ErrorCode.CONCURRENT_MODIFICATION,
        "40P01": ErrorCode.CONCURRENT_MODIFICATION,
        "55P03": ErrorCode.CONCURRENT_MODIFICATION,
        "57014": ErrorCode.CONCURRENT_MODIFICATION,
    }
    error = ResearchBaseError(
        codes.get(state, ErrorCode.INVALID_STATE_TRANSITION)
        if isinstance(state, str)
        else ErrorCode.INVALID_STATE_TRANSITION,
        "authorship transaction rejected",
    )
    error._authorship_retryable = state in {"40001", "40P01"}  # type: ignore[attr-defined]
    return error


def _manuscript_freeze_database_error(exc: DBAPIError) -> ResearchBaseError:
    state = getattr(exc.orig, "sqlstate", None)
    codes = {
        "P04M1": ErrorCode.IMMUTABLE_RECORD,
        "P04M2": ErrorCode.INVALID_STATE_TRANSITION,
        "P04M3": ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
        "23503": ErrorCode.REFERENTIAL_INTEGRITY_ERROR,
        "23514": ErrorCode.VALIDATION_ERROR,
        "23502": ErrorCode.VALIDATION_ERROR,
        "23505": ErrorCode.CONCURRENT_MODIFICATION,
        "40001": ErrorCode.CONCURRENT_MODIFICATION,
        "40P01": ErrorCode.CONCURRENT_MODIFICATION,
        "55P03": ErrorCode.CONCURRENT_MODIFICATION,
        "57014": ErrorCode.CONCURRENT_MODIFICATION,
    }
    if state in codes:
        return ResearchBaseError(
            codes[state],
            "manuscript transaction rejected",
            {"retryable_b04": state in {"40001", "40P01"}},
        )
    return _decision_database_error(exc)


class SqlAlchemyUnitOfWork:
    prepared_submission: PreparedSubmissionRepository
    manuscript_freeze: SqlAlchemyManuscriptFreezeRepository
    authorship: AuthorshipRepository
    strategy_candidates: StrategyCandidatePromotionRepository
    search_result_resolutions: SearchResultResolutionRepository
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
    discussion_hypothesis: DiscussionHypothesisRepository
    discussion: SqlAlchemyDiscussionRepository
    scientific_conclusion: SqlAlchemyScientificConclusionRepository
    publication: SqlAlchemyPublicationRepository
    revision_action: SqlAlchemyRevisionActionRepository
    approval: SqlAlchemyApprovalRepository
    decision: SqlAlchemyDecisionRepository
    gateway: SqlAlchemyGatewayRepository
    task_safety: SqlAlchemyTaskSafetyRepository
    research_tasks: SqlAlchemyResearchTaskRepository
    experiment_search: SqlAlchemyExperimentSearchRepository

    def __init__(
        self,
        session_factory: Callable[[], Session] | sessionmaker[Session],
        *,
        pr204_error_normalization: bool = False,
        context_artifact_store=None,
    ) -> None:
        self._session_factory = session_factory
        self._pr204_error_normalization = pr204_error_normalization
        self._context_artifact_store = context_artifact_store
        self._publication_entry_error_normalization = False
        self._decision_error_normalization = False
        self._prepare_submission_error_normalization = False
        self._approval_error_normalization = False
        self._package_preparation_error_normalization = False
        self._strict_approval_error_normalization = False
        self._authorship_error_normalization = False
        self._serializable_retry_normalization = False
        self._b02_error_normalization = False
        self._b01_error_normalization = False
        self._b03_error_normalization = False
        self._novelty_error_normalization = False
        self._manuscript_freeze_error_normalization = False
        self._internal_review_error_normalization = False
        self._issue_disposition_error_normalization = False
        self._session: Session | None = None

        self._committed = False
        self._search_command = False

    def __enter__(self) -> SqlAlchemyUnitOfWork:
        self._search_command = False
        self._publication_entry_error_normalization = False
        self._decision_error_normalization = False
        self._prepare_submission_error_normalization = False
        self._approval_error_normalization = False
        self._package_preparation_error_normalization = False
        self._strict_approval_error_normalization = False
        self._authorship_error_normalization = False
        self._serializable_retry_normalization = False
        self._b02_error_normalization = False
        self._b01_error_normalization = False
        self._b03_error_normalization = False
        self._novelty_error_normalization = False
        self._manuscript_freeze_error_normalization = False
        self._internal_review_error_normalization = False
        self._issue_disposition_error_normalization = False
        self._research_task_error_normalization = False
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
        self.strategy_candidates = SqlAlchemyStrategyCandidatePromotionRepository(self._session)
        self.search_result_resolutions = SqlAlchemySearchResultResolutionRepository(self._session)
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
        self.discussion_hypothesis = SqlAlchemyDiscussionHypothesisRepository(self._session)
        self.scientific_conclusion = SqlAlchemyScientificConclusionRepository(self._session)
        self.publication = SqlAlchemyPublicationRepository(self._session)
        self.manuscript_freeze = SqlAlchemyManuscriptFreezeRepository(self._session)
        self.internal_review = SqlAlchemyInternalReviewRepository(self._session)
        self.revision_action = SqlAlchemyRevisionActionRepository(self._session)
        self.decision = SqlAlchemyDecisionRepository(self._session)
        self.research_tasks = SqlAlchemyResearchTaskRepository(self._session)
        self.gateway = SqlAlchemyGatewayRepository(self._session)
        self.task_safety = SqlAlchemyTaskSafetyRepository(self._session)
        self.experiment_search = SqlAlchemyExperimentSearchRepository(self._session)
        self.context_reads = SqlAlchemyContextRepository(
            self._session, self, self._context_artifact_store
        )
        from researchbase.persistence.agent_execution_repository import (
            SqlAlchemyExecutionRepository,
        )

        self.executions = SqlAlchemyExecutionRepository(self._session)
        self.agents = SqlAlchemyAgentRepository(self._session)
        self.approval = SqlAlchemyApprovalRepository(self._session)
        self.authorship = SqlAlchemyAuthorshipRepository(self._session)
        self.prepared_submission = SqlAlchemyPreparedSubmissionRepository(self._session)
        self.novelty = SqlAlchemyNoveltyRepository(self._session)
        return self

    def enable_manuscript_freeze_error_normalization(self) -> None:
        self._decision_error_normalization = True
        self._manuscript_freeze_error_normalization = True

    def begin_discussion_hypothesis(self, *, read_only: bool) -> None:
        self._decision_error_normalization = True
        self._b03_error_normalization = True
        self.discussion_hypothesis.prepare(read_only=read_only)
        self.literature_search_plan = SqlAlchemyLiteratureSearchPlanRepository(
            self._require_session(), protected_reads=True
        )

    def begin_execution_intent(self) -> None:
        self.begin_agent_command()
        self._intent_error_normalization = True

    def begin_agent_command(self) -> None:
        self.begin_research_task()
        self._research_task_error_normalization = False
        self._agent_error_normalization = True

    def begin_gateway_command(self) -> None:
        self.begin_research_task()
        self._gateway_error_normalization = True

    def begin_experiment_search(self) -> None:
        """Configure the existing writer transaction without executing SQL."""
        self.begin_research_task()
        self._search_command = True

    def begin_research_task(self) -> None:
        """Configure isolation before the literal first SHARE statement."""
        self._decision_error_normalization = True
        self._research_task_error_normalization = True
        self._gateway_error_normalization = False
        session = self._require_session()
        session.autoflush = False
        session.connection(
            execution_options={
                "isolation_level": "READ COMMITTED",
                "postgresql_readonly": False,
            }
        )
        self.enable_revision_action_snapshot_reads()

    def begin_formal_read(self) -> None:
        """One lock-free snapshot, including nested authorization and verification."""
        session = self._require_session()
        session.autoflush = False
        session.connection(
            execution_options={
                "isolation_level": "REPEATABLE READ",
                "postgresql_readonly": True,
            }
        )
        self.enable_revision_action_snapshot_reads()
        self.literature_search_plan = SqlAlchemyLiteratureSearchPlanRepository(
            session, protected_reads=True
        )

    def begin_resolution(self, *, read_only: bool) -> None:
        """Configure B01 before SQL; transaction options emit no preceding query."""
        self._decision_error_normalization = True
        self._b01_error_normalization = True
        session = self._require_session()
        session.autoflush = False
        session.connection(
            execution_options={
                "isolation_level": "REPEATABLE READ" if read_only else "READ COMMITTED",
                "postgresql_readonly": read_only,
            }
        )
        self.enable_revision_action_snapshot_reads()

    def begin_strategy(self, *, read_only: bool) -> None:
        self.begin_resolution(read_only=read_only)
        self._b01_error_normalization = False
        self._b02_error_normalization = True

    def enable_novelty_error_normalization(self) -> None:
        self._decision_error_normalization = True
        self._novelty_error_normalization = True

    def begin_serializable(self) -> None:
        """Set SERIALIZABLE before the first SQL statement in this UoW."""

        self._require_session().connection(execution_options={"isolation_level": "SERIALIZABLE"})

    def commit(self) -> None:
        try:
            if self._search_command:
                self.experiment_search.before_commit()
            self._require_session().commit()
        except DBAPIError as exc:
            if self._decision_error_normalization:
                raise self._command_database_error(exc) from None
            normalized = _normalize_database_error(
                exc, retry_deadlocks=self._serializable_retry_normalization
            )
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

    def enable_serializable_retry_normalization(self) -> None:
        """Opt in to deadlock translation for Discussion/Conclusion retries only."""
        self._serializable_retry_normalization = True

    def configure_revision_transaction(self, *, readonly: bool = False) -> None:
        """Configure a fresh B06 connection before any transactional statement."""
        from researchbase.persistence.database import configure_revision_connection

        self._require_session().autoflush = False
        connection = self._require_session().connection(
            execution_options={
                "isolation_level": "REPEATABLE READ" if readonly else "READ COMMITTED",
                "postgresql_readonly": readonly,
            }
        )
        configure_revision_connection(connection)

    def configure_grant_transaction(self, *, consuming: bool = False) -> None:
        from researchbase.persistence.database import configure_revision_connection

        session = self._require_session()
        session.autoflush = False
        connection = session.connection(
            execution_options={
                "isolation_level": "SERIALIZABLE" if consuming else "READ COMMITTED",
                "postgresql_readonly": False,
            }
        )
        configure_revision_connection(connection)
        self.enable_revision_action_snapshot_reads()

    def configure_approval_transaction(self, *, readonly: bool = False) -> None:
        """B09 uses the existing pre-BEGIN connection timeout configuration."""
        session = self._require_session()
        session.autoflush = False
        if readonly:
            session.connection(
                execution_options={
                    "isolation_level": "REPEATABLE READ",
                    "postgresql_readonly": True,
                }
            )
        else:
            self.configure_revision_transaction()
        self.enable_revision_action_snapshot_reads()

    def enable_revision_action_snapshot_reads(self) -> None:
        """Read-only closure adapters after RevisionAction's protected table snapshot.

        Ordinary commands keep their locking adapters. Frozen Claim material is
        immutable; mutable source/evidence and ownership facts are SHARE-protected
        for this UoW, avoiding late row-lock inversions with owning writers.
        """
        session = self._require_session()
        self.publication = SqlAlchemyPublicationRepository(session, protected_reads=True)
        self.literature_evidence = SqlAlchemyLiteratureEvidenceRepository(
            session, protected_reads=True
        )
        self.scientific_conclusion = SqlAlchemyScientificConclusionRepository(
            session, protected_reads=True
        )
        self.source_version = SqlAlchemySourceVersionRepository(session, protected_reads=True)

    def enable_approval_error_normalization(self, *, strict: bool = False) -> None:
        self._decision_error_normalization = True
        self._approval_error_normalization = True
        self._strict_approval_error_normalization = strict

    def enable_package_preparation_error_normalization(self) -> None:
        self._decision_error_normalization = True
        self._package_preparation_error_normalization = True

    def enable_authorship_error_normalization(self) -> None:
        self._decision_error_normalization = True
        self._authorship_error_normalization = True

    def enable_internal_review_error_normalization(self) -> None:
        self._decision_error_normalization = True
        self._internal_review_error_normalization = True

    def enable_issue_disposition_error_normalization(self) -> None:
        self._decision_error_normalization = True
        self._issue_disposition_error_normalization = True

    def enable_publication_entry_error_normalization(self) -> None:
        self._decision_error_normalization = True
        self._publication_entry_error_normalization = True

    def enable_b23_error_normalization(self) -> None:
        self._decision_error_normalization = True
        self._b23_error_normalization = True

    def _command_database_error(self, exc: DBAPIError) -> ResearchBaseError:
        if getattr(self, "_intent_error_normalization", False):
            state = getattr(exc.orig, "sqlstate", None)
            name = str(getattr(getattr(exc.orig, "diag", None), "constraint_name", None))
            tags = {
                "pr302s2_preheld": ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                "pr302s2_scope": ErrorCode.FORBIDDEN,
                "pr302s2_state": ErrorCode.INVALID_STATE_TRANSITION,
                "pr302s2_cas": ErrorCode.CONCURRENT_MODIFICATION,
                "pr302s2_binding": ErrorCode.REFERENTIAL_INTEGRITY_ERROR,
                "pr302s2_not_frozen": ErrorCode.VERSION_NOT_FROZEN,
                "pr302s2_unresolved": ErrorCode.FROZEN_REFERENCE_REQUIRED,
                "pr302s2_provenance": ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                "pr302s2_late_history": ErrorCode.IMMUTABLE_RECORD,
                "pr302s2_completeness": ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                "pr302s2_immutable": ErrorCode.IMMUTABLE_RECORD,
                "pr302s2_exec_status_ck": ErrorCode.INVALID_STATE_TRANSITION,
                **{
                    n: ErrorCode.PROVENANCE_CLOSURE_VIOLATION
                    for n in (
                        "pr302s2_exec_revision_ck",
                        "pr302s2_event_initial_ck",
                        "pr302s2_event_reason_ck",
                        "pr302s2_receipt_shape_ck",
                    )
                },
            }
            code = tags.get(name) if state == "23514" else None
            if state == "22023" and name == "pr302s2_value_type":
                code = ErrorCode.VALIDATION_ERROR
            if state == "23505" and name in {
                "pr302s2_event_execution_uq",
                "pr302s2_event_receipt_uq",
                "pr302s2_receipt_execution_uq",
                "pr302s2_receipt_event_uq",
            }:
                code = ErrorCode.PROVENANCE_CLOSURE_VIOLATION
            if state in {"22P02", "22003", "22007", "22008"}:
                code = ErrorCode.VALIDATION_ERROR
            if code is not None:
                return ResearchBaseError(code, "Intent command rejected")
        if getattr(self, "_agent_error_normalization", False):
            state = getattr(exc.orig, "sqlstate", None)
            name = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
            code = {
                "pr302_validation": ErrorCode.VALIDATION_ERROR,
                "pr302_state": ErrorCode.INVALID_STATE_TRANSITION,
                "pr302_immutable": ErrorCode.IMMUTABLE_RECORD,
                "pr302_not_frozen": ErrorCode.VERSION_NOT_FROZEN,
                "pr302_scope": ErrorCode.FORBIDDEN,
                "pr302_provenance": ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
            }.get(str(name)) or {
                "23503": ErrorCode.REFERENTIAL_INTEGRITY_ERROR,
                "23514": ErrorCode.VALIDATION_ERROR,
                "23502": ErrorCode.VALIDATION_ERROR,
                "23505": ErrorCode.CONCURRENT_MODIFICATION,
                **{
                    s: ErrorCode.CONCURRENT_MODIFICATION
                    for s in ("40001", "40P01", "55P03", "57014")
                },
            }.get(str(state))
            if code is not None:
                return ResearchBaseError(
                    code, "Agent command rejected", {"retryable_pr302": state in {"40001", "40P01"}}
                )
            raise UncertainAgentCommit(
                "Agent transaction uncertain; reconcile exact receipt"
            ) from None
        if getattr(self, "_research_task_error_normalization", False):
            state = getattr(exc.orig, "sqlstate", None)
            name = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
            guards = {
                "pr301_validation": ErrorCode.VALIDATION_ERROR,
                "pr301_state": ErrorCode.INVALID_STATE_TRANSITION,
                "pr301_immutable": ErrorCode.IMMUTABLE_RECORD,
                "pr301_not_frozen": ErrorCode.VERSION_NOT_FROZEN,
                "pr301_scope": ErrorCode.FORBIDDEN,
                "pr301_provenance": ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
            }
            if getattr(self, "_search_command", False):
                # S4 uses the admitted 0082 guards in the existing planning UoW.
                # Preserve their semantic codes when a forced check rejects DML.
                guards.update(
                    {
                        "pr316_validation": ErrorCode.VALIDATION_ERROR,
                        "pr316_preheld": ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                        "pr316_scope": ErrorCode.FORBIDDEN,
                        "pr316_state": ErrorCode.INVALID_STATE_TRANSITION,
                        "pr316_not_frozen": ErrorCode.VERSION_NOT_FROZEN,
                        "pr316_provenance": ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                        "pr316_completeness": ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                        "pr316_reference": ErrorCode.REFERENTIAL_INTEGRITY_ERROR,
                        "pr316_immutable": ErrorCode.IMMUTABLE_RECORD,
                        "pr316_activation": ErrorCode.INVALID_STATE_TRANSITION,
                    }
                )
            codes = {
                "23503": ErrorCode.REFERENTIAL_INTEGRITY_ERROR,
                "23514": ErrorCode.VALIDATION_ERROR,
                "23502": ErrorCode.VALIDATION_ERROR,
                "23505": ErrorCode.VALIDATION_ERROR,
                **{
                    s: ErrorCode.CONCURRENT_MODIFICATION
                    for s in ("40001", "40P01", "55P03", "57014")
                },
            }
            if getattr(self, "_gateway_error_normalization", False) and state == "23505":
                if name in {
                    "agent_tool_policies_pkey",
                    "agent_tool_policies_project_id_version_key",
                    "capability_invocations_pkey",
                }:
                    codes["23505"] = ErrorCode.CONCURRENT_MODIFICATION
                elif name == "research_task_command_receipt_project_id_actor_id_command_i_key":
                    codes["23505"] = ErrorCode.IDEMPOTENCY_CONFLICT
            code = guards.get(str(name)) or codes.get(str(state))
            if code is not None:
                return ResearchBaseError(
                    code,
                    "planning transaction rejected",
                    {"retryable_pr301": state in {"40001", "40P01"}},
                )
            raise UncertainTaskCommit(
                "planning transaction uncertain; reconcile the exact receipt"
            ) from None
        if getattr(self, "_b23_error_normalization", False):
            state = getattr(exc.orig, "sqlstate", None)
            name = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
            codes = {
                "P17F1": ErrorCode.IMMUTABLE_RECORD,
                "P17F2": ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                "P17E1": ErrorCode.IMMUTABLE_RECORD,
                "P17D1": ErrorCode.IMMUTABLE_RECORD,
                "P17D2": ErrorCode.INVALID_STATE_TRANSITION,
                "P17D3": ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                "P17D4": ErrorCode.VALIDATION_ERROR,
                "P23A1": ErrorCode.FORBIDDEN,
                "P23C1": ErrorCode.CONFLICT_OF_INTEREST,
                "23503": ErrorCode.REFERENTIAL_INTEGRITY_ERROR,
                "23514": ErrorCode.VALIDATION_ERROR,
                "40001": ErrorCode.CONCURRENT_MODIFICATION,
                "40P01": ErrorCode.CONCURRENT_MODIFICATION,
            }
            if state == "23505" and name == "uq_revision_action_predecessor":
                return ResearchBaseError(
                    ErrorCode.CONCURRENT_MODIFICATION,
                    "predecessor concurrently used",
                    {"b23": True, "retryable_b23": False},
                )
            if state in codes:
                return ResearchBaseError(
                    codes[state],
                    "novelty review transaction rejected",
                    {"b23": True, "retryable_b23": state in {"40001", "40P01"}},
                )
            raise RuntimeError(
                "novelty review transaction failed; recover by exact entitled read"
            ) from None
        if self._b03_error_normalization:
            state = getattr(exc.orig, "sqlstate", None)
            name = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
            codes = {
                "P17D1": ErrorCode.IMMUTABLE_RECORD,
                "P17D3": ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                "40001": ErrorCode.CONCURRENT_MODIFICATION,
                "40P01": ErrorCode.CONCURRENT_MODIFICATION,
                "55P03": ErrorCode.CONCURRENT_MODIFICATION,
            }
            if state in codes:
                return ResearchBaseError(codes[state], "admission transaction rejected")
            if state == "23505" and name == "uq_b03_candidate":
                return ResearchBaseError(ErrorCode.DUPLICATE_CONTENT, "candidate already admitted")
            if state == "23505" and name == (
                "discussion_command_receipts_deployment_id_project_id_actor_id_key"
            ):
                return ResearchBaseError(
                    ErrorCode.CONCURRENT_MODIFICATION, "reload scoped admission receipt"
                )
            if state == "23503" and isinstance(name, str) and name.startswith("fk_b03_"):
                return ResearchBaseError(
                    ErrorCode.REFERENTIAL_INTEGRITY_ERROR, "invalid admission reference"
                )
            if state == "23514" and isinstance(name, str) and name.startswith("ck_b03_"):
                return ResearchBaseError(ErrorCode.VALIDATION_ERROR, "invalid admission material")
            raise exc
        if self._package_preparation_error_normalization:
            state = getattr(exc.orig, "sqlstate", None)
            codes = {
                "P17F1": ErrorCode.IMMUTABLE_RECORD,
                "P17F2": ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                "P16A1": ErrorCode.FORBIDDEN,
                "P16G1": ErrorCode.APPROVAL_GATE_FAILED,
                "P15S1": ErrorCode.IMMUTABLE_RECORD,
                "P15S2": ErrorCode.INVALID_STATE_TRANSITION,
                "P15S3": ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                "23503": ErrorCode.REFERENTIAL_INTEGRITY_ERROR,
                "23514": ErrorCode.VALIDATION_ERROR,
                "23502": ErrorCode.VALIDATION_ERROR,
                **{
                    key: ErrorCode.CONCURRENT_MODIFICATION
                    for key in ("23505", "40001", "40P01", "55P03", "57014")
                },
            }
            if state in codes:
                return ResearchBaseError(
                    codes[state],
                    "package transaction rejected",
                    {
                        "retryable_b15": state in {"40001", "40P01"},
                        "consent_unique_b16": state == "23505"
                        and getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
                        in {
                            "uq_author_consents_root",
                            "uq_author_consents_successor",
                            "pk_author_consents",
                        },
                    },
                )
            raise RuntimeError(
                "package transaction failed; recover by entitled exact read"
            ) from None
        if self._publication_entry_error_normalization:
            state = getattr(exc.orig, "sqlstate", None)
            name = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
            if state in {"40001", "40P01"}:
                return ResearchBaseError(
                    ErrorCode.CONCURRENT_MODIFICATION,
                    "entry transaction rejected",
                    {"retryable_b14a": True},
                )
            if state == "23505" and name == "publication_lifecycle_events_pkey":
                return ResearchBaseError(
                    ErrorCode.IDEMPOTENCY_CONFLICT,
                    "reload exact entry",
                    {"b14a_pk_collision": True},
                )
            codes = {
                "P14C1": ErrorCode.CONCURRENT_MODIFICATION,
                "P14P1": ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                "P14B1": ErrorCode.APPROVAL_GATE_FAILED,
                "P14A1": ErrorCode.FORBIDDEN,
                "P14I1": ErrorCode.IMMUTABLE_RECORD,
                "P04M1": ErrorCode.IMMUTABLE_RECORD,
                "P04M2": ErrorCode.INVALID_STATE_TRANSITION,
                "P04M3": ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                "P17D1": ErrorCode.IMMUTABLE_RECORD,
                "P17F1": ErrorCode.IMMUTABLE_RECORD,
                "P17F2": ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                "23503": ErrorCode.REFERENTIAL_INTEGRITY_ERROR,
                "22003": ErrorCode.CONCURRENT_MODIFICATION,
                "55P03": ErrorCode.CONCURRENT_MODIFICATION,
                "57014": ErrorCode.CONCURRENT_MODIFICATION,
            }
            if state == "23505" and name in {"uq_b14a_initial_event", "uq_b14a_review_entry"}:
                return ResearchBaseError(
                    ErrorCode.INVALID_STATE_TRANSITION, "lifecycle event already exists"
                )
            if state == "23514" and name in {
                "ck_b14a_publication_status",
                "ck_b14a_event_tuple",
                "ck_b14a_event_time",
            }:
                return ResearchBaseError(
                    ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "invalid entry graph"
                )
            if state in codes:
                return ResearchBaseError(codes[state], "publication entry transaction rejected")
            # Programming, infrastructure and unknown commit failures remain unexpected.
            raise exc
        if self._prepare_submission_error_normalization:
            state = getattr(exc.orig, "sqlstate", None)
            constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
            if state in {"55P03", "57014"}:
                return ResearchBaseError(
                    ErrorCode.CONCURRENT_MODIFICATION, "database wait timed out"
                )
            if state == "23514" and constraint in {"ck_b12_decision_policy", "ck_b12_text_bounds"}:
                return ResearchBaseError(ErrorCode.VALIDATION_ERROR, "invalid preparation material")

        if self._issue_disposition_error_normalization:
            return _issue_disposition_database_error(exc)
        if self._internal_review_error_normalization:
            state = getattr(exc.orig, "sqlstate", None)
            codes = {
                "P05R1": ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                "P17D1": ErrorCode.IMMUTABLE_RECORD,
                "P17E1": ErrorCode.IMMUTABLE_RECORD,
                "P17E2": ErrorCode.REVIEW_TARGET_NOT_FROZEN,
                "23503": ErrorCode.REFERENTIAL_INTEGRITY_ERROR,
                "23514": ErrorCode.VALIDATION_ERROR,
                "23502": ErrorCode.VALIDATION_ERROR,
                **{
                    key: ErrorCode.CONCURRENT_MODIFICATION
                    for key in ("23505", "40001", "40P01", "55P03", "57014")
                },
            }
            if state in codes:
                return ResearchBaseError(
                    codes[state],
                    "review transaction rejected",
                    {"retryable_b05": state in {"40001", "40P01"}},
                )
            raise RuntimeError("review transaction failed; recover by exact request ID") from None
        if (
            getattr(exc.orig, "sqlstate", None) == "23505"
            and getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
            == "uq_m1_one_draft_manuscript"
        ):
            return ResearchBaseError(
                ErrorCode.IDEMPOTENCY_CONFLICT, "publication already has a draft"
            )
        if self._manuscript_freeze_error_normalization:
            return _manuscript_freeze_database_error(exc)
        if self._b02_error_normalization:
            state = getattr(exc.orig, "sqlstate", None)
            constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
            if state in {"40001", "40P01"}:
                return ResearchBaseError(
                    ErrorCode.CONCURRENT_MODIFICATION,
                    "strategy transaction conflict",
                    {"retryable_b02": True},
                )
            if state in {"P22B1", "P22B2"}:
                return ResearchBaseError(
                    ErrorCode.IMMUTABLE_RECORD
                    if state == "P22B1"
                    else ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                    "strategy history guard rejected write",
                )
            if state == "23505":
                if constraint in {"uq_b02_q_candidate", "uq_b02_h_candidate"}:
                    return ResearchBaseError(
                        ErrorCode.DUPLICATE_CONTENT, "candidate already admitted"
                    )
                if constraint in {"pk_b02_capture", "pk_b02_q", "pk_b02_h"}:
                    return ResearchBaseError(
                        ErrorCode.CONCURRENT_MODIFICATION,
                        "strategy ID concurrently inserted",
                        {"reread_b02": True},
                    )
            if state in {"55P03", "57014"}:
                return ResearchBaseError(
                    ErrorCode.CONCURRENT_MODIFICATION, "strategy transaction timeout"
                )
            normalized = _normalize_database_error(exc)
            if normalized is not None:
                return normalized
            raise RuntimeError("strategy transaction failed; recover by exact command ID") from None
        if self._b01_error_normalization:
            state = getattr(exc.orig, "sqlstate", None)
            constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
            if state in {"40001", "40P01"}:
                return ResearchBaseError(
                    ErrorCode.CONCURRENT_MODIFICATION,
                    "resolution transaction conflict",
                    {"retryable_b01": True},
                )
            if state == "23505":
                if constraint == "search_result_resolutions_search_result_record_id_source_id_key":
                    return ResearchBaseError(
                        ErrorCode.DUPLICATE_CONTENT, "resolution tuple already exists"
                    )
                if constraint == "search_result_resolutions_pkey":
                    return ResearchBaseError(
                        ErrorCode.CONCURRENT_MODIFICATION,
                        "resolution ID concurrently inserted",
                        {"reread_b01": True},
                    )
            normalized = _normalize_database_error(exc)
            if normalized is not None:
                return normalized
            raise RuntimeError(
                "resolution transaction failed; recover by exact resolution ID"
            ) from None
        if self._authorship_error_normalization:
            return _authorship_database_error(exc)
        if self._novelty_error_normalization:
            state = getattr(exc.orig, "sqlstate", None)
            constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
            if state in {"40001", "40P01"}:
                return ResearchBaseError(
                    ErrorCode.CONCURRENT_MODIFICATION,
                    "novelty transaction conflict",
                    {"retryable_novelty": True},
                )
            if constraint in {
                "ck_b21_capture_version",
                "ck_b21_capture_count",
                "ck_b21_resolution_hash",
                "uq_b21_resolutions_pair",
                "pk_b21_resolutions",
            }:
                return ResearchBaseError(
                    ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "invalid saved capture structure"
                )
            if constraint in {
                "ck_b22_prior_art_material",
                "ck_b22_prior_art_not_self",
                "fk_b22_prior_art_predecessor",
            }:
                return ResearchBaseError(
                    ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "invalid correction ancestry"
                )
            if state in {"55P03", "57014"}:
                raise RuntimeError("novelty transaction timeout") from None
            if constraint in {"uq_pr218_novelty_predecessor", "uq_b22_prior_art_predecessor"}:
                return ResearchBaseError(
                    ErrorCode.CONCURRENT_MODIFICATION, "predecessor concurrently superseded"
                )
            if constraint in {
                "ck_pr218_novelty_initial_slice",
                "ck_b19_novelty_material",
                "ck_b20_novelty_material",
            }:
                return ResearchBaseError(
                    ErrorCode.INVALID_STATE_TRANSITION, "unsupported novelty outcome material"
                )
            if constraint and (
                constraint.startswith("ck_b20_")
                or constraint.startswith("uq_b20_")
                or constraint.startswith("pk_b20_")
            ):
                return ResearchBaseError(
                    ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "invalid screening structure"
                )
            normalized = _normalize_database_error(exc)
            if normalized is not None:
                return normalized
            raise RuntimeError("novelty transaction failed; recover by exact request ID") from None
        return (
            _approval_database_error(exc, strict=self._strict_approval_error_normalization)
            if self._approval_error_normalization
            else _decision_database_error(exc)
        )

    def enable_prepare_submission_error_normalization(self) -> None:
        self._decision_error_normalization = True
        self._prepare_submission_error_normalization = True

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
            raise self._command_database_error(exc_value) from None
        if exc_value is None and cleanup_error is not None:
            if isinstance(cleanup_error, DBAPIError):
                raise self._command_database_error(cleanup_error) from None
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
            normalized = _normalize_database_error(
                exc_value, retry_deadlocks=self._serializable_retry_normalization
            )
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


def search_result_resolution_uow_factory(url: str) -> Callable[[], SqlAlchemyUnitOfWork]:
    """Startup options bound even B01's first statement, before SET LOCAL is legal."""
    engine = create_engine(
        url,
        connect_args={
            "options": "-c lock_timeout=10s -c statement_timeout=30s",
            "connect_timeout": 10,
        },
    )
    sessions = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    return lambda: SqlAlchemyUnitOfWork(sessions)


def strategy_candidate_promotion_uow_factory(url: str) -> Callable[[], SqlAlchemyUnitOfWork]:
    """The startup timeout bounds B02's first SHARE wait before SET LOCAL."""
    return search_result_resolution_uow_factory(url)


def research_task_uow_factory(url: str) -> Callable[[], SqlAlchemyUnitOfWork]:
    """Dedicated pool with startup bounds, so SHARE is the very first SQL."""
    return search_result_resolution_uow_factory(url)


def agent_execution_uow_factory(url: str) -> Callable[[], SqlAlchemyUnitOfWork]:
    """Reuse the accepted startup-timeout factory for the intent write boundary."""
    return search_result_resolution_uow_factory(url)
