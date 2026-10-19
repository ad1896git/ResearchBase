"""Frozen PR-15 routes: transport DTOs mapped only to accepted Application calls."""

# pyright: reportArgumentType=false, reportCallIssue=false

from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextlib import suppress
from dataclasses import fields, is_dataclass
from datetime import date
from threading import Event
from types import UnionType
from typing import Annotated, Any, Union, get_args, get_origin, get_type_hints
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, create_model
from starlette.concurrency import run_in_threadpool

from researchbase.api.context import execution_context
from researchbase.api.errors import ErrorEnvelope
from researchbase.application.commands import (
    AttachRunArtifactInputCommand,
    AttachRunDatasetInputCommand,
    CreateArtifactCommand,
    CreateArtifactVersionCommand,
    CreateClaimCommand,
    CreateDatasetSnapshotCommand,
    CreateExperimentSpecCommand,
    CreateHypothesisCommand,
    CreateMetricDefinitionCommand,
    CreateProjectCommand,
    CreateResearchQuestionCommand,
    CreateRunCommand,
    FinishRunCommand,
    FreezeArtifactVersionCommand,
    FreezeClaimVersionCommand,
    FreezeExperimentSpecCommand,
    FreezeHypothesisCommand,
    FreezeMetricDefinitionCommand,
    FreezeResearchQuestionCommand,
    LinkEvidenceCommand,
    RecordMeasurementCommand,
    RecordStatisticalResultCommand,
    RegisterDatasetCommand,
    ReviseClaimCommand,
    ReviseExperimentSpecCommand,
    ReviseHypothesisCommand,
    ReviseMetricDefinitionCommand,
    ReviseResearchQuestionCommand,
    StartRunCommand,
    StatisticalResultInputCommand,
    WriteProjectionTarget,
)
from researchbase.application.dto import (
    ArtifactReadModel,
    ArtifactVersionReadModel,
    ClaimReadModel,
    ClaimVersionReadModel,
    DatasetReadModel,
    DatasetSnapshotReadModel,
    EvidenceRelationReadModel,
    ExperimentSpecReadModel,
    ExperimentSpecVersionReadModel,
    HypothesisReadModel,
    HypothesisVersionReadModel,
    MeasurementReadModel,
    MetricDefinitionReadModel,
    MetricDefinitionVersionReadModel,
    ProjectReadModel,
    ResearchQuestionReadModel,
    ResearchQuestionVersionReadModel,
    RunReadModel,
    StatisticalResultReadModel,
    WriteResult,
)
from researchbase.application.governance import (
    CreateAuditFindingCommand,
    CreateCorrectionRecordCommand,
    CreateImpactAssessmentCommand,
    ProposedImpactTarget,
)
from researchbase.application.governance_queries import DownstreamImpactTarget
from researchbase.application.literature_search_execution import (
    CancelLiteratureSearchExecution,
    CreateLiteratureSearchExecution,
    ExecuteLiteratureSearchExecution,
    LiteratureSearchExecutionService,
    RecoverLiteratureSearchExecution,
    SearchQueryInput,
    _http_disconnect,
)
from researchbase.application.literature_search_plan import (
    CreateLiteratureSearchPlan,
    EditLiteratureSearchPlanQuestions,
    LiteratureSearchPlanService,
    RemoveLiteratureSearchPlanQuestion,
    ReviseLiteratureSearchPlan,
    TransitionLiteratureSearchPlanVersion,
    UpdateLiteratureSearchPlanDraft,
)
from researchbase.application.novelty import (
    ExactReadQuery,
    NoveltyReadback,
    PriorArtReadback,
    PriorArtSelectionQuery,
    PriorArtSelectionReadback,
    RecordNoveltyAssessmentCommand,
    RecordPriorArtRelationCommand,
    RecordSearchCoverageCommand,
    SearchCoverageReadback,
)
from researchbase.application.provenance_queries import ClaimToRunsTraceDTO, RunProvenanceDTO
from researchbase.application.source_identity import (
    AddSourceIdentifier,
    RegisterLiteratureSource,
    RejectSourceIdentifier,
    VerifySourceIdentifier,
)
from researchbase.application.source_merge import (
    DecideSourceMerge,
    ProposeSourceMerge,
    RevokeSourceMergeApproval,
)
from researchbase.application.source_merge_execution import (
    ConsumeSourceMergeProposal,
    SourceMergeExecutionService,
)
from researchbase.application.source_version import (
    CreateSourceVersion,
    SourceVersionService,
    TransitionSourceVersion,
    UpdateSourceVersionDraft,
)
from researchbase.domain.claim import EvidenceRelationType
from researchbase.domain.governance import (
    AuditFinding,
    AuditFindingSeverity,
    CorrectionRecord,
    CorrectionType,
    GovernanceTargetType,
    ImpactAssessment,
    ImpactAssessmentConclusion,
    ImpactKind,
)
from researchbase.domain.literature_search_plan import (
    FrozenResearchQuestionReference,
    LiteratureSearchPlanMaterial,
    LiteratureSearchStrategy,
    LiteratureSourceScope,
)
from researchbase.domain.novelty import (
    ClosenessCriteria,
    NoveltyOutcome,
    PriorArtBasisInput,
    PriorArtKind,
    TimeScope,
)
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.domain.run import ArtifactInputRole, DatasetInputRole, RunStatus
from researchbase.domain.source_identity import IdentifierType, SourceKind
from researchbase.domain.source_version import (
    FrozenSourceReference,
    SourceVersionKind,
    SourceVersionMaterial,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.execution_context import ExecutionContext
from researchbase.foundation.frozen_json import FrozenJSONArray, FrozenJSONObject, thaw_json

_SCHEMA_CACHE: dict[type[Any], type[BaseModel]] = {}


def _safe_type(annotation: Any) -> Any:
    """Replace only unconstrained application ``object`` leaves with JSON values."""
    if annotation is object:
        return Any
    if (
        isinstance(annotation, type)
        and issubclass(annotation, str)
        and not hasattr(annotation, "__members__")
    ):
        return str
    if isinstance(annotation, type) and is_dataclass(annotation):
        return _response_schema(annotation)
    origin = get_origin(annotation)
    if origin in (Union, UnionType):
        return Union[tuple(_safe_type(item) for item in get_args(annotation))]  # noqa: UP007
    if origin is tuple:
        return tuple[tuple(_safe_type(item) for item in get_args(annotation))]
    if origin is list:
        return list[_safe_type(get_args(annotation)[0])]
    return annotation


def _response_schema(model: type[Any]) -> type[BaseModel]:
    cached = _SCHEMA_CACHE.get(model)
    if cached is not None:
        return cached
    hints = get_type_hints(model)
    schema = create_model(
        f"{model.__name__}Response",
        __config__=ConfigDict(extra="forbid"),
        **{
            field.name: (
                _safe_type(hints[field.name]),
                Field(..., alias={"from_date": "from", "through_date": "through"}[field.name])
                if model is TimeScope
                else ...,
            )
            for field in fields(model)
        },
    )
    _SCHEMA_CACHE[model] = schema
    return schema


ProjectReadModel = _response_schema(ProjectReadModel)
ResearchQuestionReadModel = _response_schema(ResearchQuestionReadModel)
ResearchQuestionVersionReadModel = _response_schema(ResearchQuestionVersionReadModel)
HypothesisReadModel = _response_schema(HypothesisReadModel)
HypothesisVersionReadModel = _response_schema(HypothesisVersionReadModel)
ExperimentSpecReadModel = _response_schema(ExperimentSpecReadModel)
ExperimentSpecVersionReadModel = _response_schema(ExperimentSpecVersionReadModel)
DatasetReadModel = _response_schema(DatasetReadModel)
DatasetSnapshotReadModel = _response_schema(DatasetSnapshotReadModel)
ArtifactReadModel = _response_schema(ArtifactReadModel)
ArtifactVersionReadModel = _response_schema(ArtifactVersionReadModel)
MetricDefinitionReadModel = _response_schema(MetricDefinitionReadModel)
MetricDefinitionVersionReadModel = _response_schema(MetricDefinitionVersionReadModel)
RunReadModel = _response_schema(RunReadModel)
RunProvenanceDTO = _response_schema(RunProvenanceDTO)
MeasurementReadModel = _response_schema(MeasurementReadModel)
StatisticalResultReadModel = _response_schema(StatisticalResultReadModel)
ClaimReadModel = _response_schema(ClaimReadModel)
ClaimVersionReadModel = _response_schema(ClaimVersionReadModel)
EvidenceRelationReadModel = _response_schema(EvidenceRelationReadModel)
ClaimToRunsTraceDTO = _response_schema(ClaimToRunsTraceDTO)
AuditFinding = _response_schema(AuditFinding)
ImpactAssessment = _response_schema(ImpactAssessment)
CorrectionRecord = _response_schema(CorrectionRecord)
DownstreamImpactTarget = _response_schema(DownstreamImpactTarget)


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceMergeProposalResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    proposal_id: UUID
    status: str
    proposal_basis_hash: str


class SourceMergeDecisionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approval_id: UUID
    proposal_id: UUID
    project_id: UUID
    decision: str


class SourceMergeProposalStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")
    proposal_id: UUID
    source_a_id: UUID
    source_b_id: UUID
    canonical_survivor_id: UUID
    proposal_basis_hash: str
    status: str
    affected_project_count: int
    decision_count: int
    project_decision: str | None
    project_decision_reason: str | None


class SourceMergeRevocationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str


class ProjectIn(InputModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class ResearchQuestionIn(InputModel):
    project_id: UUID
    question_text: str = Field(min_length=1)
    scope: Any | None = None
    rationale: str | None = None


class ReviseResearchQuestionIn(InputModel):
    question_text: str = Field(min_length=1)
    scope: Any | None = None
    rationale: str | None = None
    expected_row_version: int = Field(gt=0)
    base_version_id: UUID | None = None


class FreezeResearchQuestionIn(InputModel):
    research_question_id: UUID
    expected_row_version: int | None = Field(default=None, gt=0)


class FreezeHypothesisIn(InputModel):
    hypothesis_id: UUID
    expected_row_version: int | None = Field(default=None, gt=0)


class FreezeExperimentSpecIn(InputModel):
    experiment_spec_id: UUID
    expected_row_version: int | None = Field(default=None, gt=0)


class FreezeArtifactIn(InputModel):
    artifact_id: UUID
    expected_row_version: int | None = Field(default=None, gt=0)


class FreezeMetricDefinitionIn(InputModel):
    metric_definition_id: UUID
    expected_row_version: int | None = Field(default=None, gt=0)


class FreezeClaimIn(InputModel):
    claim_id: UUID
    expected_row_version: int | None = Field(default=None, gt=0)


class HypothesisIn(InputModel):
    project_id: UUID
    statement: str = Field(min_length=1)
    expected_direction: str | None = None
    success_criteria: Any | None = None
    rationale: str | None = None
    research_question_id: UUID | None = None


class ReviseHypothesisIn(InputModel):
    statement: str = Field(min_length=1)
    expected_direction: str | None = None
    success_criteria: Any | None = None
    rationale: str | None = None
    expected_row_version: int = Field(gt=0)
    base_version_id: UUID | None = None


class ExperimentSpecIn(InputModel):
    project_id: UUID
    hypothesis_id: UUID | None = None
    title: str = Field(min_length=1, max_length=255)
    objective: str = Field(min_length=1)
    protocol: Any
    planned_metrics: Any | None = None
    seed_policy: Any | None = None
    analysis_plan: Any | None = None


class ReviseExperimentSpecIn(InputModel):
    title: str = Field(min_length=1, max_length=255)
    objective: str = Field(min_length=1)
    protocol: Any
    planned_metrics: Any | None = None
    seed_policy: Any | None = None
    analysis_plan: Any | None = None
    expected_row_version: int = Field(gt=0)
    base_version_id: UUID | None = None


class DatasetIn(InputModel):
    project_id: UUID | None = None
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    source_locator: str | None = None


class DatasetSnapshotIn(InputModel):
    manifest_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    selection_definition: Any
    manifest_locator: str | None = None


class ArtifactIn(InputModel):
    project_id: UUID | None = None
    artifact_type: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class ArtifactVersionIn(InputModel):
    data: bytes | None = None
    content_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    locator: str | None = None
    media_type: str | None = Field(default=None, max_length=128)
    byte_size: int | None = Field(default=None, ge=0)
    metadata: Any | None = None


class MetricDefinitionIn(InputModel):
    project_id: UUID | None = None
    name: str = Field(min_length=1, max_length=255)
    definition: Any
    unit: str | None = Field(default=None, max_length=64)
    aggregation: str | None = Field(default=None, max_length=64)


class ReviseMetricDefinitionIn(InputModel):
    definition: Any
    unit: str | None = Field(default=None, max_length=64)
    aggregation: str | None = Field(default=None, max_length=64)
    expected_row_version: int = Field(gt=0)


class RunIn(InputModel):
    project_id: UUID
    experiment_spec_version_id: UUID
    run_type: str | None = Field(default=None, max_length=32)


class DatasetInputIn(InputModel):
    dataset_snapshot_id: UUID
    role: DatasetInputRole
    ordinal: int = Field(default=0, ge=0)
    expected_row_version: int = Field(gt=0)


class ArtifactInputIn(InputModel):
    artifact_version_id: UUID
    role: ArtifactInputRole
    ordinal: int = Field(default=0, ge=0)
    expected_row_version: int = Field(gt=0)


class TransitionIn(InputModel):
    expected_row_version: int = Field(gt=0)


class FinishRunIn(TransitionIn):
    outcome: RunStatus
    exit_code: int | None = None
    failure_reason: str | None = None


class MeasurementIn(InputModel):
    run_id: UUID
    metric_definition_version_id: UUID
    numeric_value: float | None = None
    structured_value: Any | None = None
    unit: str | None = Field(default=None, max_length=64)
    evaluation_scope: Any | None = None


class StatisticalInputIn(InputModel):
    measurement_id: UUID
    input_role: str = Field(default="input", min_length=1)
    ordinal: int = Field(default=0, ge=0)


class StatisticalResultIn(InputModel):
    project_id: UUID
    analysis_type: str = Field(min_length=1)
    result_payload: Any
    analysis_definition: Any
    inputs: list[StatisticalInputIn] = Field(min_length=1)


class ClaimIn(InputModel):
    project_id: UUID
    statement: str = Field(min_length=1)
    scope: Any | None = None
    qualification: str | None = None


class ReviseClaimIn(InputModel):
    statement: str | None = None
    scope: Any | None = None
    qualification: str | None = None
    expected_row_version: int = Field(gt=0)
    base_version_id: UUID | None = None


class EvidenceIn(InputModel):
    claim_id: UUID
    measurement_id: UUID | None = None
    statistical_result_id: UUID | None = None
    relation_type: EvidenceRelationType
    qualification: str | None = None
    expected_row_version: int = Field(gt=0)


class AuditFindingIn(InputModel):
    project_id: UUID
    finding_type: str = Field(min_length=1)
    severity: AuditFindingSeverity
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    target_type: GovernanceTargetType
    target_id: UUID


class ImpactTargetIn(InputModel):
    target_type: GovernanceTargetType
    target_id: UUID
    impact_kind: ImpactKind


class ImpactAssessmentIn(InputModel):
    project_id: UUID
    audit_finding_id: UUID | None = None
    assessment_payload: Any
    conclusion: ImpactAssessmentConclusion
    targets: list[ImpactTargetIn] = Field(min_length=1)


class CorrectionIn(InputModel):
    project_id: UUID
    target_type: GovernanceTargetType
    target_id: UUID
    correction_type: CorrectionType
    corrected_assertion: Any
    reason: str = Field(min_length=1)


class LiteratureSourceIn(InputModel):
    kind: SourceKind
    title: str = Field(min_length=1, max_length=2048)
    initial_identifier_type: IdentifierType | None = None
    initial_identifier_value: str | None = Field(default=None, max_length=2048)


class SourceIdentifierIn(InputModel):
    identifier_type: IdentifierType
    identifier_value: str = Field(min_length=1, max_length=2048)
    is_primary: bool = False
    binding_basis_artifact_version_id: UUID | None = None
    supersedes_rejected_identifier_id: UUID | None = None


class IdentifierStatusIn(InputModel):
    basis_artifact_version_id: UUID
    reason: str = Field(min_length=1, max_length=2048)


class SourceMergeProposalIn(InputModel):
    source_a_id: UUID
    source_b_id: UUID
    canonical_survivor_id: UUID
    rationale: str = Field(min_length=1, max_length=4096)
    supersedes_proposal_id: UUID | None = None
    evidence_artifact_ids: list[UUID] = Field(default_factory=list)


class SourceMergeDecisionIn(InputModel):
    reason: str | None = Field(default=None, max_length=2048)


class SourceMergeConsumeIn(InputModel):
    proposal_basis_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    identity_basis_artifact: SourceVersionReferenceIn


class SourceVersionReferenceIn(InputModel):
    id: UUID
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class SourceVersionIn(InputModel):
    version_kind: SourceVersionKind
    predecessor_source_version: SourceVersionReferenceIn | None = None
    correction_basis_artifact: SourceVersionReferenceIn | None = None
    title: str = Field(min_length=1)
    abstract: str | None = None
    authors: list[dict[str, str | None]]
    publication_date: date | None = None
    venue: str | None = None
    external_version_label: str | None = None
    fulltext_artifact: SourceVersionReferenceIn | None = None
    metadata: dict[str, str | None] | None = None


class SearchPlanQuestionReferenceIn(InputModel):
    research_question_id: UUID
    version_id: UUID
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class LiteratureSearchPlanIn(InputModel):
    objective: str = Field(min_length=1)
    source_scope: LiteratureSourceScope
    inclusion_criteria: dict[str, Any] | None = None
    exclusion_criteria: dict[str, Any] | None = None
    time_range: dict[str, date | None] | None = None
    language_scope: list[str] | None = None
    search_strategy: LiteratureSearchStrategy
    planned_providers: list[str]
    stopping_rule: dict[str, str] | None = None
    research_question_refs: list[SearchPlanQuestionReferenceIn] = Field(default_factory=list)


class LiteratureSearchExecutionQueryIn(InputModel):
    query_type: str = Field(default="TEXT", pattern="^TEXT$")
    query_text: str = Field(min_length=1, max_length=4096)
    perspective: str | None = Field(default=None, max_length=256)


class LiteratureSearchExecutionIn(InputModel):
    project_id: UUID
    search_plan_version_id: UUID
    provider_id: str = Field(min_length=1, max_length=128)
    provider_version: str = Field(min_length=1, max_length=128)
    queries: list[LiteratureSearchExecutionQueryIn] = Field(min_length=1, max_length=32)
    max_results: int = Field(default=20, ge=1, le=100)
    max_provider_attempts: int = Field(default=3, ge=1, le=3)
    timeout_seconds: int = Field(default=30, ge=1, le=30)
    execution_budget_seconds: int = Field(default=300, ge=1, le=600)


class LiteratureSearchExecutionScopeIn(InputModel):
    project_id: UUID


class SourceVersionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_version_id: str
    literature_source_id: str
    version_number: int
    status: str
    content_hash: str | None


class SourceVersionReadResult(SourceVersionResult):
    version_kind: str
    predecessor_source_version_id: str | None
    correction_basis_artifact_version_id: str | None
    title: str
    abstract: str | None
    authors: Any
    publication_date: str | None
    venue: str | None
    external_version_label: str | None
    fulltext_artifact_version_id: str | None
    metadata: Any
    hash_scheme: str
    frozen_at: str | None


class SourceMergeRecordResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_merge_record_id: str
    losing_source_id: str
    winning_source_id: str
    identity_basis_artifact_version_id: str
    reason: str
    merged_by: str
    merged_at: str
    content_hash: str


router = APIRouter(
    prefix="/v1",
    responses={
        404: {"model": ErrorEnvelope},
        409: {"model": ErrorEnvelope},
        422: {"model": ErrorEnvelope},
        500: {"model": ErrorEnvelope},
    },
)
Ctx = Annotated[ExecutionContext, Depends(execution_context)]


def _services(request: Request) -> Any:
    return request.app.state.services


def _verified_principal(request: Request) -> VerifiedPrincipal:
    principal = getattr(request.state, "verified_principal", None)
    if not isinstance(principal, VerifiedPrincipal):
        from researchbase.foundation.errors import ErrorCode, ResearchBaseError

        raise ResearchBaseError(
            ErrorCode.AUTHENTICATION_REQUIRED, "a trusted verified principal is required"
        )
    supplied_actor = request.headers.get("X-Actor-ID")
    if supplied_actor is not None and supplied_actor != str(principal.actor_id):
        from researchbase.foundation.errors import ErrorCode, ResearchBaseError

        raise ResearchBaseError(
            ErrorCode.FORBIDDEN, "X-Actor-ID does not match the authenticated principal"
        )
    return principal


def _http_json_value(value: object) -> object:
    """Return a fresh transport tree without exposing FrozenJSON wrappers."""
    if isinstance(value, FrozenJSONObject | FrozenJSONArray):
        return thaw_json(value)
    if isinstance(value, BaseModel):
        return {
            name: _http_json_value(getattr(value, name)) for name in value.__class__.model_fields
        }
    if isinstance(value, TimeScope):
        return value.material()
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _http_json_value(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, dict):
        return {key: _http_json_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [_http_json_value(item) for item in value]
    return value


def _json(value: object) -> Any:
    return jsonable_encoder(_http_json_value(value))


def _legacy_write(
    application: Any,
    target: WriteProjectionTarget,
    operation: Callable[[], WriteResult],
) -> Any:
    """Adapt a committed Application WriteResult to the accepted HTTP shape."""

    result = operation()
    return _json(application.project_write_result(result, target))


@router.post(
    "/projects", status_code=201, operation_id="create_project", response_model=ProjectReadModel
)
def create_project(body: ProjectIn, context: Ctx, request: Request) -> Any:
    application = _services(request).application
    return _legacy_write(
        application,
        WriteProjectionTarget.PROJECT,
        lambda: application.create_project(
            CreateProjectCommand(body.name, body.description, context)
        ),
    )


@router.post(
    "/research-questions",
    status_code=201,
    operation_id="create_research_question",
    response_model=ResearchQuestionReadModel,
)
def create_research_question(body: ResearchQuestionIn, context: Ctx, request: Request) -> Any:
    application = _services(request).application
    return _legacy_write(
        application,
        WriteProjectionTarget.RESEARCH_QUESTION,
        lambda: application.create_research_question(
            CreateResearchQuestionCommand(**body.model_dump(), context=context)
        ),
    )


@router.post(
    "/research-questions/{id}/versions",
    status_code=201,
    operation_id="revise_research_question",
    response_model=ResearchQuestionReadModel,
)
def revise_research_question(
    id: UUID, body: ReviseResearchQuestionIn, context: Ctx, request: Request
) -> Any:
    application = _services(request).application
    return _legacy_write(
        application,
        WriteProjectionTarget.RESEARCH_QUESTION,
        lambda: application.revise_research_question(
            ReviseResearchQuestionCommand(
                research_question_id=id, **body.model_dump(), context=context
            )
        ),
    )


@router.post(
    "/research-question-versions/{id}:freeze",
    operation_id="freeze_research_question_version",
    response_model=ResearchQuestionVersionReadModel,
)
def freeze_research_question(
    id: UUID, body: FreezeResearchQuestionIn, context: Ctx, request: Request
) -> Any:
    application = _services(request).application
    return _legacy_write(
        application,
        WriteProjectionTarget.RESEARCH_QUESTION_VERSION,
        lambda: application.freeze_research_question(
            FreezeResearchQuestionCommand(
                body.research_question_id, id, context, body.expected_row_version
            )
        ),
    )


@router.post(
    "/hypotheses",
    status_code=201,
    operation_id="create_hypothesis",
    response_model=HypothesisReadModel,
)
def create_hypothesis(body: HypothesisIn, context: Ctx, request: Request) -> Any:
    application = _services(request).application
    return _legacy_write(
        application,
        WriteProjectionTarget.HYPOTHESIS,
        lambda: application.create_hypothesis(
            CreateHypothesisCommand(**body.model_dump(), context=context)
        ),
    )


@router.post(
    "/hypotheses/{id}/versions",
    status_code=201,
    operation_id="revise_hypothesis",
    response_model=HypothesisReadModel,
)
def revise_hypothesis(id: UUID, body: ReviseHypothesisIn, context: Ctx, request: Request) -> Any:
    application = _services(request).application
    return _legacy_write(
        application,
        WriteProjectionTarget.HYPOTHESIS,
        lambda: application.revise_hypothesis(
            ReviseHypothesisCommand(hypothesis_id=id, **body.model_dump(), context=context)
        ),
    )


@router.post(
    "/hypothesis-versions/{id}:freeze",
    operation_id="freeze_hypothesis_version",
    response_model=HypothesisVersionReadModel,
)
def freeze_hypothesis(id: UUID, body: FreezeHypothesisIn, context: Ctx, request: Request) -> Any:
    application = _services(request).application
    return _legacy_write(
        application,
        WriteProjectionTarget.HYPOTHESIS_VERSION,
        lambda: application.freeze_hypothesis(
            FreezeHypothesisCommand(body.hypothesis_id, id, context, body.expected_row_version)
        ),
    )


@router.post(
    "/experiment-specs",
    status_code=201,
    operation_id="create_experiment_spec",
    response_model=ExperimentSpecReadModel,
)
def create_experiment_spec(body: ExperimentSpecIn, context: Ctx, request: Request) -> Any:
    application = _services(request).application
    return _legacy_write(
        application,
        WriteProjectionTarget.EXPERIMENT_SPEC,
        lambda: application.create_experiment_spec(
            CreateExperimentSpecCommand(**body.model_dump(), context=context)
        ),
    )


@router.post(
    "/experiment-specs/{id}/versions",
    status_code=201,
    operation_id="revise_experiment_spec",
    response_model=ExperimentSpecReadModel,
)
def revise_experiment_spec(
    id: UUID, body: ReviseExperimentSpecIn, context: Ctx, request: Request
) -> Any:
    application = _services(request).application
    return _legacy_write(
        application,
        WriteProjectionTarget.EXPERIMENT_SPEC,
        lambda: application.revise_experiment_spec(
            ReviseExperimentSpecCommand(experiment_spec_id=id, **body.model_dump(), context=context)
        ),
    )


@router.post(
    "/experiment-spec-versions/{id}:freeze",
    operation_id="freeze_experiment_spec_version",
    response_model=ExperimentSpecVersionReadModel,
)
def freeze_experiment_spec(
    id: UUID, body: FreezeExperimentSpecIn, context: Ctx, request: Request
) -> Any:
    application = _services(request).application
    return _legacy_write(
        application,
        WriteProjectionTarget.EXPERIMENT_SPEC_VERSION,
        lambda: application.freeze_experiment_spec(
            FreezeExperimentSpecCommand(
                body.experiment_spec_id, id, context, body.expected_row_version
            )
        ),
    )


@router.post(
    "/datasets", status_code=201, operation_id="register_dataset", response_model=DatasetReadModel
)
def register_dataset(body: DatasetIn, context: Ctx, request: Request) -> Any:
    application = _services(request).application
    return _legacy_write(
        application,
        WriteProjectionTarget.DATASET,
        lambda: application.register_dataset(
            RegisterDatasetCommand(**body.model_dump(), context=context)
        ),
    )


@router.post(
    "/datasets/{id}/snapshots",
    status_code=201,
    operation_id="create_dataset_snapshot",
    response_model=DatasetSnapshotReadModel,
)
def create_dataset_snapshot(
    id: UUID, body: DatasetSnapshotIn, context: Ctx, request: Request
) -> Any:
    application = _services(request).application
    return _legacy_write(
        application,
        WriteProjectionTarget.DATASET_SNAPSHOT,
        lambda: application.create_dataset_snapshot(
            CreateDatasetSnapshotCommand(dataset_id=id, **body.model_dump(), context=context)
        ),
    )


@router.post(
    "/artifacts", status_code=201, operation_id="create_artifact", response_model=ArtifactReadModel
)
def create_artifact(body: ArtifactIn, context: Ctx, request: Request) -> Any:
    application = _services(request).application
    return _legacy_write(
        application,
        WriteProjectionTarget.ARTIFACT,
        lambda: application.create_artifact(
            CreateArtifactCommand(**body.model_dump(), context=context)
        ),
    )


@router.post(
    "/artifacts/{id}/versions",
    status_code=201,
    operation_id="create_artifact_version",
    response_model=ArtifactVersionReadModel,
)
def create_artifact_version(
    id: UUID, body: ArtifactVersionIn, context: Ctx, request: Request
) -> Any:
    application = _services(request).application
    return _legacy_write(
        application,
        WriteProjectionTarget.ARTIFACT_VERSION,
        lambda: application.create_artifact_version(
            CreateArtifactVersionCommand(artifact_id=id, **body.model_dump(), context=context)
        ),
    )


@router.post(
    "/artifact-versions/{id}:freeze",
    operation_id="freeze_artifact_version",
    response_model=ArtifactVersionReadModel,
)
def freeze_artifact_version(
    id: UUID, body: FreezeArtifactIn, context: Ctx, request: Request
) -> Any:
    application = _services(request).application
    return _legacy_write(
        application,
        WriteProjectionTarget.ARTIFACT_VERSION,
        lambda: application.freeze_artifact_version(
            FreezeArtifactVersionCommand(body.artifact_id, id, context, body.expected_row_version)
        ),
    )


@router.post(
    "/metric-definitions",
    status_code=201,
    operation_id="create_metric_definition",
    response_model=MetricDefinitionReadModel,
)
def create_metric_definition(body: MetricDefinitionIn, context: Ctx, request: Request) -> Any:
    application = _services(request).application
    return _legacy_write(
        application,
        WriteProjectionTarget.METRIC_DEFINITION,
        lambda: application.create_metric_definition(
            CreateMetricDefinitionCommand(**body.model_dump(), context=context)
        ),
    )


@router.post(
    "/metric-definitions/{id}/versions",
    status_code=201,
    operation_id="revise_metric_definition",
    response_model=MetricDefinitionReadModel,
)
def revise_metric_definition(
    id: UUID, body: ReviseMetricDefinitionIn, context: Ctx, request: Request
) -> Any:
    application = _services(request).application
    return _legacy_write(
        application,
        WriteProjectionTarget.METRIC_DEFINITION,
        lambda: application.revise_metric_definition(
            ReviseMetricDefinitionCommand(
                metric_definition_id=id, **body.model_dump(), context=context
            )
        ),
    )


@router.post(
    "/metric-definition-versions/{id}:freeze",
    operation_id="freeze_metric_definition_version",
    response_model=MetricDefinitionVersionReadModel,
)
def freeze_metric_definition(
    id: UUID, body: FreezeMetricDefinitionIn, context: Ctx, request: Request
) -> Any:
    application = _services(request).application
    return _legacy_write(
        application,
        WriteProjectionTarget.METRIC_DEFINITION_VERSION,
        lambda: application.freeze_metric_definition(
            FreezeMetricDefinitionCommand(
                body.metric_definition_id, id, context, body.expected_row_version
            )
        ),
    )


@router.post("/runs", status_code=201, operation_id="create_run", response_model=RunReadModel)
def create_run(body: RunIn, context: Ctx, request: Request) -> Any:
    application = _services(request).application
    return _legacy_write(
        application,
        WriteProjectionTarget.RUN,
        lambda: application.create_run(CreateRunCommand(**body.model_dump(), context=context)),
    )


@router.post(
    "/runs/{id}/dataset-inputs",
    operation_id="attach_run_dataset_input",
    response_model=RunReadModel,
)
def attach_dataset(id: UUID, body: DatasetInputIn, context: Ctx, request: Request) -> Any:
    application = _services(request).application
    return _legacy_write(
        application,
        WriteProjectionTarget.RUN,
        lambda: application.attach_run_dataset_input(
            AttachRunDatasetInputCommand(run_id=id, **body.model_dump(), context=context)
        ),
    )


@router.post(
    "/runs/{id}/artifact-inputs",
    operation_id="attach_run_artifact_input",
    response_model=RunReadModel,
)
def attach_artifact(id: UUID, body: ArtifactInputIn, context: Ctx, request: Request) -> Any:
    application = _services(request).application
    return _legacy_write(
        application,
        WriteProjectionTarget.RUN,
        lambda: application.attach_run_artifact_input(
            AttachRunArtifactInputCommand(run_id=id, **body.model_dump(), context=context)
        ),
    )


@router.post("/runs/{id}:start", operation_id="start_run", response_model=RunReadModel)
def start_run(id: UUID, body: TransitionIn, context: Ctx, request: Request) -> Any:
    application = _services(request).application
    return _legacy_write(
        application,
        WriteProjectionTarget.RUN,
        lambda: application.start_run(StartRunCommand(id, body.expected_row_version, context)),
    )


@router.post("/runs/{id}:finish", operation_id="finish_run", response_model=RunReadModel)
def finish_run(id: UUID, body: FinishRunIn, context: Ctx, request: Request) -> Any:
    application = _services(request).application
    return _legacy_write(
        application,
        WriteProjectionTarget.RUN,
        lambda: application.finish_run(
            FinishRunCommand(run_id=id, **body.model_dump(), context=context)
        ),
    )


@router.get(
    "/runs/{id}/provenance", operation_id="get_run_provenance", response_model=RunProvenanceDTO
)
def run_provenance(id: UUID, request: Request) -> Any:
    return _json(_services(request).provenance.get_run_provenance(id))


@router.post(
    "/measurements",
    status_code=201,
    operation_id="record_measurement",
    response_model=MeasurementReadModel,
)
def record_measurement(body: MeasurementIn, context: Ctx, request: Request) -> Any:
    application = _services(request).application
    return _legacy_write(
        application,
        WriteProjectionTarget.MEASUREMENT,
        lambda: application.record_measurement(
            RecordMeasurementCommand(**body.model_dump(), context=context)
        ),
    )


@router.post(
    "/statistical-results",
    status_code=201,
    operation_id="record_statistical_result",
    response_model=StatisticalResultReadModel,
)
def record_statistical_result(body: StatisticalResultIn, context: Ctx, request: Request) -> Any:
    values = body.model_dump(exclude={"inputs"})
    inputs = tuple(StatisticalResultInputCommand(**item.model_dump()) for item in body.inputs)
    application = _services(request).application
    return _legacy_write(
        application,
        WriteProjectionTarget.STATISTICAL_RESULT,
        lambda: application.record_statistical_result(
            RecordStatisticalResultCommand(**values, inputs=inputs, context=context)
        ),
    )


@router.post("/claims", status_code=201, operation_id="create_claim", response_model=ClaimReadModel)
def create_claim(body: ClaimIn, context: Ctx, request: Request) -> Any:
    application = _services(request).application
    return _legacy_write(
        application,
        WriteProjectionTarget.CLAIM,
        lambda: application.create_claim(CreateClaimCommand(**body.model_dump(), context=context)),
    )


@router.post(
    "/claims/{id}/versions",
    status_code=201,
    operation_id="revise_claim",
    response_model=ClaimReadModel,
)
def revise_claim(id: UUID, body: ReviseClaimIn, context: Ctx, request: Request) -> Any:
    application = _services(request).application
    return _legacy_write(
        application,
        WriteProjectionTarget.CLAIM,
        lambda: application.revise_claim(
            ReviseClaimCommand(claim_id=id, **body.model_dump(), context=context)
        ),
    )


@router.post(
    "/claim-versions/{id}/evidence",
    status_code=201,
    operation_id="link_evidence",
    response_model=EvidenceRelationReadModel,
)
def link_evidence(id: UUID, body: EvidenceIn, context: Ctx, request: Request) -> Any:
    application = _services(request).application
    return _legacy_write(
        application,
        WriteProjectionTarget.EVIDENCE_RELATION,
        lambda: application.link_evidence(
            LinkEvidenceCommand(claim_version_id=id, **body.model_dump(), context=context)
        ),
    )


@router.post(
    "/claim-versions/{id}:freeze",
    operation_id="freeze_claim_version",
    response_model=ClaimVersionReadModel,
)
def freeze_claim(id: UUID, body: FreezeClaimIn, context: Ctx, request: Request) -> Any:
    application = _services(request).application
    return _legacy_write(
        application,
        WriteProjectionTarget.CLAIM_VERSION,
        lambda: application.freeze_claim_version(
            FreezeClaimVersionCommand(body.claim_id, id, context, body.expected_row_version)
        ),
    )


@router.get(
    "/claim-versions/{id}/trace",
    operation_id="trace_claim_to_runs",
    response_model=ClaimToRunsTraceDTO,
)
def claim_trace(id: UUID, request: Request) -> Any:
    return _json(_services(request).provenance.trace_claim_to_runs(id))


@router.post(
    "/audit-findings",
    status_code=201,
    operation_id="create_audit_finding",
    response_model=AuditFinding,
)
def create_audit_finding(body: AuditFindingIn, context: Ctx, request: Request) -> Any:
    return _json(
        _services(request).governance.create_audit_finding(
            CreateAuditFindingCommand(**body.model_dump(), context=context)
        )
    )


@router.post(
    "/impact-assessments",
    status_code=201,
    operation_id="create_impact_assessment",
    response_model=ImpactAssessment,
)
def create_impact_assessment(body: ImpactAssessmentIn, context: Ctx, request: Request) -> Any:
    values = body.model_dump(exclude={"targets"})
    targets = tuple(ProposedImpactTarget(**item.model_dump()) for item in body.targets)
    return _json(
        _services(request).governance.create_impact_assessment(
            CreateImpactAssessmentCommand(**values, targets=targets, context=context)
        )
    )


@router.post(
    "/corrections",
    status_code=201,
    operation_id="create_correction",
    response_model=CorrectionRecord,
)
def create_correction(body: CorrectionIn, context: Ctx, request: Request) -> Any:
    return _json(
        _services(request).governance.create_correction_record(
            CreateCorrectionRecordCommand(**body.model_dump(), context=context)
        )
    )


@router.get(
    "/impact/{target_type}/{target_id}",
    operation_id="get_downstream_impact",
    response_model=list[DownstreamImpactTarget],
)
def downstream_impact(
    target_type: GovernanceTargetType,
    target_id: UUID,
    request: Request,
    project_id: Annotated[UUID, Query()],
) -> Any:
    return _json(
        _services(request).governance_queries.downstream_impact(project_id, target_type, target_id)
    )


@router.post(
    "/projects/{project_id}/literature/sources",
    status_code=201,
    operation_id="register_literature_source",
)
def register_literature_source(
    project_id: UUID,
    body: LiteratureSourceIn,
    request: Request,
    idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
) -> Any:
    return _json(
        _services(request).literature.register_literature_source(
            RegisterLiteratureSource(
                principal=_verified_principal(request),
                project_id=project_id,
                kind=body.kind,
                title=body.title,
                request_id=idempotency_key,
                initial_identifier_type=body.initial_identifier_type,
                initial_identifier_value=body.initial_identifier_value,
            )
        )
    )


@router.post(
    "/projects/{project_id}/literature/sources/{source_id}/identifiers",
    status_code=201,
    operation_id="add_source_identifier",
)
def add_source_identifier(
    project_id: UUID,
    source_id: UUID,
    body: SourceIdentifierIn,
    request: Request,
    idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
) -> Any:
    return _json(
        _services(request).literature.add_source_identifier(
            AddSourceIdentifier(
                principal=_verified_principal(request),
                project_id=project_id,
                source_id=source_id,
                identifier_type=body.identifier_type,
                identifier_value=body.identifier_value,
                is_primary=body.is_primary,
                request_id=idempotency_key,
                binding_basis_artifact_version_id=body.binding_basis_artifact_version_id,
                supersedes_rejected_identifier_id=body.supersedes_rejected_identifier_id,
            )
        )
    )


@router.post(
    "/projects/{project_id}/literature/identifiers/{identifier_id}:verify",
    operation_id="verify_source_identifier",
)
def verify_source_identifier(
    project_id: UUID,
    identifier_id: UUID,
    body: IdentifierStatusIn,
    request: Request,
    idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
) -> Any:
    return _json(
        _services(request).literature.verify_source_identifier(
            VerifySourceIdentifier(
                principal=_verified_principal(request),
                project_id=project_id,
                identifier_id=identifier_id,
                basis_artifact_version_id=body.basis_artifact_version_id,
                reason=body.reason,
                request_id=idempotency_key,
            )
        )
    )


@router.post(
    "/projects/{project_id}/literature/identifiers/{identifier_id}:reject",
    operation_id="reject_source_identifier",
)
def reject_source_identifier(
    project_id: UUID,
    identifier_id: UUID,
    body: IdentifierStatusIn,
    request: Request,
    idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
) -> Any:
    return _json(
        _services(request).literature.reject_source_identifier(
            RejectSourceIdentifier(
                principal=_verified_principal(request),
                project_id=project_id,
                identifier_id=identifier_id,
                basis_artifact_version_id=body.basis_artifact_version_id,
                reason=body.reason,
                request_id=idempotency_key,
            )
        )
    )


@router.get(
    "/projects/{project_id}/literature/sources/{source_id}",
    operation_id="get_literature_source",
)
def get_literature_source(project_id: UUID, source_id: UUID, request: Request) -> Any:
    return _json(
        _services(request).literature.get_literature_source(
            _verified_principal(request), project_id, source_id
        )
    )


@router.get(
    "/projects/{project_id}/literature/sources:resolve",
    operation_id="find_source_by_identifier",
)
def find_source_by_identifier(
    project_id: UUID,
    request: Request,
    identifier_type: Annotated[IdentifierType, Query()],
    value: Annotated[str, Query(min_length=1, max_length=2048)],
) -> Any:
    return _json(
        _services(request).literature.find_source_by_identifier(
            _verified_principal(request), project_id, identifier_type, value
        )
    )


def _source_version_material(source_id: UUID, body: SourceVersionIn) -> SourceVersionMaterial:
    def reference(value: SourceVersionReferenceIn | None) -> FrozenSourceReference | None:
        if value is None:
            return None
        return FrozenSourceReference(value.id, value.content_hash)

    return SourceVersionMaterial(
        literature_source_id=source_id,
        version_kind=body.version_kind,
        predecessor_source_version=reference(body.predecessor_source_version),
        correction_basis_artifact=reference(body.correction_basis_artifact),
        title=body.title,
        abstract=body.abstract,
        authors=tuple(body.authors),
        publication_date=body.publication_date,
        venue=body.venue,
        external_version_label=body.external_version_label,
        fulltext_artifact=reference(body.fulltext_artifact),
        metadata=body.metadata,
    )


@router.post(
    "/projects/{project_id}/literature/sources/{source_id}/versions",
    status_code=201,
    operation_id="create_source_version",
    response_model=SourceVersionResult,
)
def create_source_version(
    project_id: UUID,
    source_id: UUID,
    body: SourceVersionIn,
    request: Request,
    idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
) -> Any:
    service: SourceVersionService = _services(request).source_versions
    return _json(
        service.create(
            CreateSourceVersion(
                _verified_principal(request),
                project_id,
                _source_version_material(source_id, body),
                idempotency_key,
            )
        )
    )


@router.patch(
    "/projects/{project_id}/literature/source-versions/{source_version_id}",
    operation_id="update_source_version_draft",
    response_model=SourceVersionResult,
)
def update_source_version_draft(
    project_id: UUID,
    source_version_id: UUID,
    body: SourceVersionIn,
    request: Request,
    source_id: Annotated[UUID, Query()],
    idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
) -> Any:
    service: SourceVersionService = _services(request).source_versions
    return _json(
        service.update(
            UpdateSourceVersionDraft(
                _verified_principal(request),
                project_id,
                source_version_id,
                _source_version_material(source_id, body),
                idempotency_key,
            )
        )
    )


@router.post(
    "/projects/{project_id}/literature/source-versions/{source_version_id}:freeze",
    operation_id="freeze_source_version",
    response_model=SourceVersionResult,
)
def freeze_source_version(
    project_id: UUID,
    source_version_id: UUID,
    request: Request,
    idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
) -> Any:
    return _json(
        _services(request).source_versions.freeze(
            TransitionSourceVersion(
                _verified_principal(request), project_id, source_version_id, idempotency_key
            )
        )
    )


@router.post(
    "/projects/{project_id}/literature/source-versions/{source_version_id}:abandon",
    operation_id="abandon_source_version",
    response_model=SourceVersionResult,
)
def abandon_source_version(
    project_id: UUID,
    source_version_id: UUID,
    request: Request,
    idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
) -> Any:
    return _json(
        _services(request).source_versions.abandon(
            TransitionSourceVersion(
                _verified_principal(request), project_id, source_version_id, idempotency_key
            )
        )
    )


@router.get(
    "/projects/{project_id}/literature/sources/{source_id}/versions",
    operation_id="list_source_versions",
    response_model=list[SourceVersionReadResult],
)
def list_source_versions(project_id: UUID, source_id: UUID, request: Request) -> Any:
    return _json(
        _services(request).source_versions.list(_verified_principal(request), project_id, source_id)
    )


@router.get(
    "/projects/{project_id}/literature/source-versions/{source_version_id}",
    operation_id="get_source_version",
    response_model=SourceVersionReadResult,
)
def get_source_version(project_id: UUID, source_version_id: UUID, request: Request) -> Any:
    return _json(
        _services(request).source_versions.get(
            _verified_principal(request), project_id, source_version_id
        )
    )


def _search_plan_service(request: Request) -> LiteratureSearchPlanService:
    service = getattr(_services(request), "literature_search_plans", None)
    if service is None:
        from researchbase.foundation.errors import ErrorCode, ResearchBaseError

        raise ResearchBaseError(
            ErrorCode.AUTHENTICATION_REQUIRED, "search plan service unavailable"
        )
    return service


def _search_plan_material(
    plan_id: UUID, body: LiteratureSearchPlanIn, *, include_refs: bool
) -> LiteratureSearchPlanMaterial:
    try:
        refs = (
            tuple(
                FrozenResearchQuestionReference(
                    item.research_question_id, item.version_id, item.content_hash
                )
                for item in body.research_question_refs
            )
            if include_refs
            else ()
        )
        return LiteratureSearchPlanMaterial(
            plan_id=plan_id,
            research_question_refs=refs,
            objective=body.objective,
            source_scope=body.source_scope,
            inclusion_criteria=body.inclusion_criteria,
            exclusion_criteria=body.exclusion_criteria,
            time_range=body.time_range,
            language_scope=tuple(body.language_scope) if body.language_scope is not None else None,
            search_strategy=body.search_strategy,
            planned_providers=tuple(body.planned_providers),
            stopping_rule=body.stopping_rule,
        )
    except (TypeError, ValueError) as exc:
        from researchbase.foundation.errors import ErrorCode, ResearchBaseError

        raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, str(exc)) from exc


@router.post(
    "/projects/{project_id}/literature/search-plans",
    status_code=201,
    operation_id="create_literature_search_plan",
)
def create_literature_search_plan(
    project_id: UUID,
    body: LiteratureSearchPlanIn,
    request: Request,
    idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
) -> Any:
    return _json(
        _search_plan_service(request).create(
            CreateLiteratureSearchPlan(
                _verified_principal(request),
                project_id,
                _search_plan_material(uuid4(), body, include_refs=True),
                idempotency_key,
            )
        )
    )


@router.get(
    "/projects/{project_id}/literature/search-plans", operation_id="list_literature_search_plans"
)
def list_literature_search_plans(project_id: UUID, request: Request) -> Any:
    return _json(_search_plan_service(request).list(_verified_principal(request), project_id))


@router.get(
    "/projects/{project_id}/literature/search-plans/{plan_id}",
    operation_id="get_literature_search_plan",
)
def get_literature_search_plan(project_id: UUID, plan_id: UUID, request: Request) -> Any:
    return _json(
        _search_plan_service(request).get(_verified_principal(request), project_id, plan_id)
    )


@router.post(
    "/projects/{project_id}/literature/search-plans/{plan_id}:revise",
    operation_id="revise_literature_search_plan",
)
def revise_literature_search_plan(
    project_id: UUID,
    plan_id: UUID,
    base_version_id: Annotated[UUID, Query()],
    request: Request,
    idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
) -> Any:
    return _json(
        _search_plan_service(request).revise(
            ReviseLiteratureSearchPlan(
                _verified_principal(request), project_id, plan_id, base_version_id, idempotency_key
            )
        )
    )


@router.put(
    "/projects/{project_id}/literature/search-plans/{plan_id}/versions/{version_id}",
    operation_id="update_literature_search_plan_draft",
)
def update_literature_search_plan_draft(
    project_id: UUID,
    plan_id: UUID,
    version_id: UUID,
    body: LiteratureSearchPlanIn,
    request: Request,
    idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
) -> Any:
    if body.research_question_refs:
        from researchbase.foundation.errors import ErrorCode, ResearchBaseError

        raise ResearchBaseError(
            ErrorCode.VALIDATION_ERROR,
            "question relations use the dedicated add/remove commands",
        )
    material = _search_plan_material(plan_id, body, include_refs=False)
    return _json(
        _search_plan_service(request).update(
            UpdateLiteratureSearchPlanDraft(
                _verified_principal(request),
                project_id,
                plan_id,
                version_id,
                material,
                idempotency_key,
            )
        )
    )


@router.post(
    "/projects/{project_id}/literature/search-plans/{plan_id}/versions/{version_id}/questions",
    operation_id="add_literature_search_plan_question",
)
def add_literature_search_plan_question(
    project_id: UUID,
    plan_id: UUID,
    version_id: UUID,
    research_question_version_id: Annotated[UUID, Query()],
    request: Request,
    idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
) -> Any:
    return _json(
        _search_plan_service(request).add_question(
            EditLiteratureSearchPlanQuestions(
                _verified_principal(request),
                project_id,
                plan_id,
                version_id,
                research_question_version_id,
                idempotency_key,
            )
        )
    )


@router.delete(
    "/projects/{project_id}/literature/search-plans/{plan_id}/versions/{version_id}/questions/{research_question_id}",
    operation_id="remove_literature_search_plan_question",
)
def remove_literature_search_plan_question(
    project_id: UUID,
    plan_id: UUID,
    version_id: UUID,
    research_question_id: UUID,
    request: Request,
    idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
) -> Any:
    return _json(
        _search_plan_service(request).remove_question(
            RemoveLiteratureSearchPlanQuestion(
                _verified_principal(request),
                project_id,
                plan_id,
                version_id,
                research_question_id,
                idempotency_key,
            )
        )
    )


@router.post(
    "/projects/{project_id}/literature/search-plans/{plan_id}/versions/{version_id}:freeze",
    operation_id="freeze_literature_search_plan",
)
def freeze_literature_search_plan(
    project_id: UUID,
    plan_id: UUID,
    version_id: UUID,
    request: Request,
    idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
) -> Any:
    return _json(
        _search_plan_service(request).freeze(
            TransitionLiteratureSearchPlanVersion(
                _verified_principal(request), project_id, plan_id, version_id, idempotency_key
            )
        )
    )


@router.post(
    "/projects/{project_id}/literature/search-plans/{plan_id}/versions/{version_id}:abandon",
    operation_id="abandon_literature_search_plan",
)
def abandon_literature_search_plan(
    project_id: UUID,
    plan_id: UUID,
    version_id: UUID,
    request: Request,
    idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
) -> Any:
    return _json(
        _search_plan_service(request).abandon(
            TransitionLiteratureSearchPlanVersion(
                _verified_principal(request), project_id, plan_id, version_id, idempotency_key
            )
        )
    )


def _search_execution_service(request: Request) -> LiteratureSearchExecutionService:
    service = getattr(_services(request), "literature_search_executions", None)
    if service is None:
        from researchbase.foundation.errors import ErrorCode, ResearchBaseError

        raise ResearchBaseError(ErrorCode.ADAPTER_UNAVAILABLE, "search adapter unavailable")
    return service


@router.post(
    "/literature/search-executions",
    status_code=201,
    operation_id="create_literature_search_execution",
)
def create_literature_search_execution(
    body: LiteratureSearchExecutionIn,
    request: Request,
    idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
) -> Any:
    principal = _verified_principal(request)
    return _json(
        _search_execution_service(request).create(
            CreateLiteratureSearchExecution(
                project_id=body.project_id,
                plan_version_id=body.search_plan_version_id,
                actor_id=principal.actor_id,
                deployment_id=principal.deployment_id,
                request_id=idempotency_key,
                provider_id=body.provider_id,
                provider_version=body.provider_version,
                queries=tuple(
                    SearchQueryInput(item.query_text, item.perspective, item.query_type)
                    for item in body.queries
                ),
                max_results=body.max_results,
                max_provider_attempts=body.max_provider_attempts,
                timeout_seconds=body.timeout_seconds,
                execution_budget_seconds=body.execution_budget_seconds,
                principal=principal,
            )
        )
    )


def _execution_command(
    command_type: type[
        ExecuteLiteratureSearchExecution
        | CancelLiteratureSearchExecution
        | RecoverLiteratureSearchExecution
    ],
    execution_id: UUID,
    body: LiteratureSearchExecutionScopeIn,
    request: Request,
    request_id: UUID,
) -> Any:
    principal = _verified_principal(request)
    command = command_type(
        execution_id=execution_id,
        actor_id=principal.actor_id,
        deployment_id=principal.deployment_id,
        request_id=request_id,
        project_id=body.project_id,
        principal=principal,
    )
    service = _search_execution_service(request)
    method = {
        ExecuteLiteratureSearchExecution: service.execute,
        CancelLiteratureSearchExecution: service.cancel,
        RecoverLiteratureSearchExecution: service.recover,
    }[command_type]
    return _json(method(command))


@router.post(
    "/literature/search-executions/{execution_id}:execute",
    status_code=202,
    operation_id="execute_literature_search_execution",
)
async def execute_literature_search_execution(
    execution_id: UUID,
    body: LiteratureSearchExecutionScopeIn,
    request: Request,
    idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
) -> Any:
    disconnected = Event()
    context_token = _http_disconnect.set(disconnected)

    async def watch_disconnect() -> None:
        while True:
            if (await request.receive())["type"] == "http.disconnect":
                disconnected.set()
                return

    watcher = asyncio.create_task(watch_disconnect())
    try:
        return await run_in_threadpool(
            lambda: _execution_command(
                ExecuteLiteratureSearchExecution, execution_id, body, request, idempotency_key
            ),
        )
    finally:
        watcher.cancel()
        try:
            with suppress(asyncio.CancelledError):
                await watcher
        finally:
            _http_disconnect.reset(context_token)


@router.post(
    "/literature/search-executions/{execution_id}:cancel",
    status_code=202,
    operation_id="cancel_literature_search_execution",
)
def cancel_literature_search_execution(
    execution_id: UUID,
    body: LiteratureSearchExecutionScopeIn,
    request: Request,
    idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
) -> Any:
    return _execution_command(
        CancelLiteratureSearchExecution, execution_id, body, request, idempotency_key
    )


@router.post(
    "/literature/search-executions/{execution_id}:recover",
    status_code=202,
    operation_id="recover_literature_search_execution",
)
def recover_literature_search_execution(
    execution_id: UUID,
    body: LiteratureSearchExecutionScopeIn,
    request: Request,
    idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
) -> Any:
    return _execution_command(
        RecoverLiteratureSearchExecution, execution_id, body, request, idempotency_key
    )


@router.get(
    "/literature/search-executions/{execution_id}",
    operation_id="get_literature_search_execution",
)
def get_literature_search_execution(
    execution_id: UUID, project_id: Annotated[UUID, Query()], request: Request
) -> Any:
    return _json(
        _search_execution_service(request).get(
            _verified_principal(request), project_id, execution_id
        )
    )


@router.get(
    "/literature/search-executions",
    operation_id="list_literature_search_executions",
)
def list_literature_search_executions(
    project_id: Annotated[UUID, Query()],
    request: Request,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    after: Annotated[UUID | None, Query()] = None,
) -> Any:
    return _json(
        _search_execution_service(request).list(
            _verified_principal(request), project_id, limit, after
        )
    )


@router.get(
    "/literature/search-executions/{execution_id}/provenance",
    operation_id="get_literature_search_execution_provenance",
)
def get_literature_search_execution_provenance(
    execution_id: UUID, project_id: Annotated[UUID, Query()], request: Request
) -> Any:
    return _json(
        _search_execution_service(request).get_provenance(
            _verified_principal(request), project_id, execution_id
        )
    )


@router.get(
    "/projects/{project_id}/literature/sources/{source_id}/identifiers",
    operation_id="list_source_identifiers",
)
def list_source_identifiers(project_id: UUID, source_id: UUID, request: Request) -> Any:
    return _json(
        _services(request).literature.list_source_identifiers(
            _verified_principal(request), project_id, source_id
        )
    )


@router.post(
    "/projects/{project_id}/literature/source-merge-proposals",
    status_code=201,
    operation_id="propose_source_merge",
    response_model=SourceMergeProposalResult,
)
def propose_source_merge(
    project_id: UUID,
    body: SourceMergeProposalIn,
    request: Request,
    idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
) -> Any:
    return _json(
        _services(request).source_merge.propose(
            ProposeSourceMerge(
                _verified_principal(request),
                project_id,
                body.source_a_id,
                body.source_b_id,
                body.canonical_survivor_id,
                body.rationale,
                idempotency_key,
                body.supersedes_proposal_id,
                tuple(body.evidence_artifact_ids),
            )
        )
    )


@router.post(
    "/projects/{project_id}/literature/source-merge-proposals/{proposal_id}:approve",
    operation_id="approve_source_merge",
    response_model=SourceMergeDecisionResult,
)
def approve_source_merge(
    project_id: UUID,
    proposal_id: UUID,
    request: Request,
    idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
) -> Any:
    return _json(
        _services(request).source_merge.decide(
            DecideSourceMerge(
                _verified_principal(request), project_id, proposal_id, "APPROVE", idempotency_key
            )
        )
    )


@router.post(
    "/projects/{project_id}/literature/source-merge-proposals/{proposal_id}:reject",
    operation_id="reject_source_merge",
    response_model=SourceMergeDecisionResult,
)
def reject_source_merge(
    project_id: UUID,
    proposal_id: UUID,
    body: SourceMergeDecisionIn,
    request: Request,
    idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
) -> Any:
    return _json(
        _services(request).source_merge.decide(
            DecideSourceMerge(
                _verified_principal(request),
                project_id,
                proposal_id,
                "REJECT",
                idempotency_key,
                body.reason,
            )
        )
    )


@router.post(
    "/projects/{project_id}/literature/source-merge-proposals/{proposal_id}:revoke",
    operation_id="revoke_source_merge_approval",
    response_model=SourceMergeRevocationResult,
)
def revoke_source_merge_approval(
    project_id: UUID,
    proposal_id: UUID,
    body: SourceMergeDecisionIn,
    request: Request,
    idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
) -> Any:
    _services(request).source_merge.revoke(
        RevokeSourceMergeApproval(
            _verified_principal(request),
            project_id,
            proposal_id,
            body.reason or "",
            idempotency_key,
        )
    )
    return {"status": "REVOKED"}


@router.get(
    "/projects/{project_id}/literature/source-merge-proposals/{proposal_id}",
    operation_id="get_source_merge_proposal",
    response_model=SourceMergeProposalStatus,
)
def get_source_merge_proposal(project_id: UUID, proposal_id: UUID, request: Request) -> Any:
    return _json(
        _services(request).source_merge.get(_verified_principal(request), project_id, proposal_id)
    )


@router.post(
    "/projects/{project_id}/literature/source-merge-proposals/{proposal_id}:consume",
    operation_id="consume_source_merge_proposal",
    response_model=SourceMergeRecordResult,
)
def consume_source_merge_proposal(
    project_id: UUID,
    proposal_id: UUID,
    body: SourceMergeConsumeIn,
    request: Request,
    idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
) -> Any:
    service: SourceMergeExecutionService = _services(request).source_merge_execution
    return _json(
        service.consume(
            ConsumeSourceMergeProposal(
                _verified_principal(request),
                project_id,
                proposal_id,
                body.proposal_basis_hash,
                FrozenSourceReference(
                    body.identity_basis_artifact.id,
                    body.identity_basis_artifact.content_hash,
                ),
                idempotency_key,
            )
        )
    )


def _novelty_uuid(value):
    if type(value) is UUID:
        return value
    if not isinstance(value, str):
        raise ValueError("canonical UUID required")
    parsed = UUID(value)
    if str(parsed) != value:
        raise ValueError("canonical UUID required")
    return parsed


NoveltyUUID = Annotated[UUID, BeforeValidator(_novelty_uuid)]


class SearchCoverageIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: NoveltyUUID
    search_plan_version_id: NoveltyUUID
    search_execution_ids: tuple[NoveltyUUID, ...] = Field(min_length=1, max_length=100)
    coverage_limitations: str


class PriorArtIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: NoveltyUUID
    claim_version_id: NoveltyUUID
    source_version_id: NoveltyUUID
    relation: PriorArtKind
    rationale: str
    literature_evidence_ids: tuple[NoveltyUUID, ...] = Field(min_length=1, max_length=100)
    supersedes_prior_art_relation_id: NoveltyUUID | None = None


class PriorArtSelectionIn(InputModel):
    claim_version_id: NoveltyUUID
    source_version_id: NoveltyUUID


class PriorArtBasisIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prior_art_relation_id: NoveltyUUID
    search_result_resolution_id: NoveltyUUID


class ClosenessCriteriaIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    statements: tuple[str, ...] = Field(min_length=1, max_length=100)


class NoveltyAssessmentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: NoveltyUUID
    claim_version_id: NoveltyUUID
    search_coverage_id: NoveltyUUID
    assessment: NoveltyOutcome
    limitations: str
    supersedes_assessment_id: NoveltyUUID | None = None
    prior_art_basis: tuple[PriorArtBasisIn, ...] = Field(default=(), max_length=100)
    scope_statement: str | None = None
    closeness_criteria: ClosenessCriteriaIn | None = None


@router.post(
    "/projects/{project_id}/search-coverage",
    operation_id="record_search_coverage",
    response_model=_response_schema(SearchCoverageReadback),
)
def record_search_coverage(project_id: NoveltyUUID, body: SearchCoverageIn, request: Request):
    return _json(
        _services(request).novelty.record_search_coverage(
            _verified_principal(request),
            RecordSearchCoverageCommand(project_id=project_id, **body.model_dump()),
        )
    )


@router.get(
    "/projects/{project_id}/search-coverage/{id}",
    operation_id="read_search_coverage",
    response_model=_response_schema(SearchCoverageReadback),
)
def read_search_coverage(project_id: NoveltyUUID, id: NoveltyUUID, request: Request):
    return _json(
        _services(request).novelty.read_search_coverage(
            _verified_principal(request), ExactReadQuery(project_id, id)
        )
    )


@router.post(
    "/projects/{project_id}/prior-art-relations",
    operation_id="record_prior_art_relation",
    response_model=_response_schema(PriorArtReadback),
)
def record_prior_art_relation(project_id: NoveltyUUID, body: PriorArtIn, request: Request):
    return _json(
        _services(request).novelty.record_prior_art_relation(
            _verified_principal(request),
            RecordPriorArtRelationCommand(project_id=project_id, **body.model_dump()),
        )
    )


@router.get(
    "/projects/{project_id}/prior-art-relations/selection",
    operation_id="select_prior_art_relation",
    response_model=_response_schema(PriorArtSelectionReadback),
)
def select_prior_art_relation(
    project_id: NoveltyUUID,
    query: Annotated[PriorArtSelectionIn, Query()],
    request: Request,
):
    return _json(
        _services(request).novelty.select_prior_art_relation(
            _verified_principal(request),
            PriorArtSelectionQuery(project_id, query.claim_version_id, query.source_version_id),
        )
    )


@router.get(
    "/projects/{project_id}/prior-art-relations/{id}",
    operation_id="read_prior_art_relation",
    response_model=_response_schema(PriorArtReadback),
)
def read_prior_art_relation(project_id: NoveltyUUID, id: NoveltyUUID, request: Request):
    return _json(
        _services(request).novelty.read_prior_art_relation(
            _verified_principal(request), ExactReadQuery(project_id, id)
        )
    )


@router.post(
    "/projects/{project_id}/novelty-assessments",
    operation_id="record_novelty_assessment",
    response_model=_response_schema(NoveltyReadback),
)
def record_novelty_assessment(project_id: NoveltyUUID, body: NoveltyAssessmentIn, request: Request):
    try:
        command = RecordNoveltyAssessmentCommand(
            project_id=project_id,
            **body.model_dump(exclude={"prior_art_basis", "closeness_criteria"}),
            prior_art_basis=tuple(
                PriorArtBasisInput(**x.model_dump()) for x in body.prior_art_basis
            ),
            closeness_criteria=ClosenessCriteria(body.closeness_criteria.statements)
            if body.closeness_criteria
            else None,
        )
    except (ValueError, TypeError):
        raise ResearchBaseError(
            ErrorCode.VALIDATION_ERROR, "invalid closed novelty command"
        ) from None
    return _json(
        _services(request).novelty.record_novelty_assessment(_verified_principal(request), command)
    )


@router.get(
    "/projects/{project_id}/novelty-assessments/{id}",
    operation_id="read_novelty_assessment",
    response_model=_response_schema(NoveltyReadback),
)
def read_novelty_assessment(project_id: NoveltyUUID, id: NoveltyUUID, request: Request):
    return _json(
        _services(request).novelty.read_novelty_assessment(
            _verified_principal(request), ExactReadQuery(project_id, id)
        )
    )
