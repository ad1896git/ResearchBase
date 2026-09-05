"""Frozen PR-15 routes: transport DTOs mapped only to accepted Application calls."""

# pyright: reportArgumentType=false, reportCallIssue=false

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, fields, is_dataclass
from types import UnionType
from typing import Annotated, Any, Union, get_args, get_origin, get_type_hints
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, Field, create_model

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
from researchbase.application.provenance_queries import ClaimToRunsTraceDTO, RunProvenanceDTO
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
from researchbase.domain.run import ArtifactInputRole, DatasetInputRole, RunStatus
from researchbase.foundation.execution_context import ExecutionContext

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
        **{field.name: (_safe_type(hints[field.name]), ...) for field in fields(model)},
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


def _json(value: object) -> Any:
    return jsonable_encoder(asdict(value) if is_dataclass(value) else value)


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
