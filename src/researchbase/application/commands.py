"""Minimal PR-02 create/get application commands."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace

from researchbase.application.closure import ClosureReport, ProvenanceClosureValidator
from researchbase.application.dto import (
    ActorReadModel,
    ArtifactReadModel,
    ArtifactVersionReadModel,
    DatasetReadModel,
    DatasetSnapshotReadModel,
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
    RunArtifactInputReadModel,
    RunDatasetInputReadModel,
    RunReadModel,
    WorkspaceReadModel,
)
from researchbase.application.ports import UnitOfWork
from researchbase.domain.artifact import Artifact, ArtifactId, ArtifactVersion, ArtifactVersionId
from researchbase.domain.evidence import Dataset, DatasetId, DatasetSnapshot, DatasetSnapshotId
from researchbase.domain.experiment import (
    ExperimentSpec,
    ExperimentSpecId,
    ExperimentSpecVersion,
    ExperimentSpecVersionId,
)
from researchbase.domain.identity import Actor, ActorType
from researchbase.domain.measurement import Measurement, MeasurementId
from researchbase.domain.metric import (
    MetricDefinition,
    MetricDefinitionId,
    MetricDefinitionVersion,
    MetricDefinitionVersionId,
)
from researchbase.domain.organization import (
    LifecycleStatus,
    Project,
    ProjectId,
    Workspace,
    WorkspaceId,
)
from researchbase.domain.research import (
    Hypothesis,
    HypothesisId,
    HypothesisVersion,
    HypothesisVersionId,
    ResearchQuestion,
    ResearchQuestionId,
    ResearchQuestionVersion,
    ResearchQuestionVersionId,
)
from researchbase.domain.run import (
    ArtifactInputRole,
    DatasetInputRole,
    Run,
    RunArtifactInput,
    RunDatasetInput,
    RunId,
    RunStatus,
)
from researchbase.foundation.artifact_store import ArtifactStore
from researchbase.foundation.canonical_json import canonical_json_bytes
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.execution_context import ExecutionContext
from researchbase.foundation.hashing import ContentHash, sha256_canonical_json
from researchbase.foundation.ids import ActorId, new_typed_id
from researchbase.foundation.time import Clock
from researchbase.foundation.versioning import VersionStatus


@dataclass(frozen=True, slots=True)
class CreateActorCommand:
    actor_type: ActorType | str
    display_name: str
    external_key: str | None
    context: ExecutionContext


@dataclass(frozen=True, slots=True)
class CreateProjectCommand:
    name: str
    description: str | None
    context: ExecutionContext


@dataclass(frozen=True, slots=True)
class CreateWorkspaceCommand:
    project_id: ProjectId
    name: str
    locator: str | None
    context: ExecutionContext


@dataclass(frozen=True, slots=True)
class CreateResearchQuestionCommand:
    project_id: ProjectId
    question_text: str
    scope: object | None
    rationale: str | None
    context: ExecutionContext


@dataclass(frozen=True, slots=True)
class ReviseResearchQuestionCommand:
    research_question_id: ResearchQuestionId
    question_text: str
    scope: object | None
    rationale: str | None
    expected_row_version: int
    context: ExecutionContext
    base_version_id: ResearchQuestionVersionId | None = None


@dataclass(frozen=True, slots=True)
class UpdateResearchQuestionDraftCommand:
    research_question_id: ResearchQuestionId
    version_id: ResearchQuestionVersionId
    question_text: str
    scope: object | None
    rationale: str | None
    expected_row_version: int
    context: ExecutionContext


@dataclass(frozen=True, slots=True)
class FreezeResearchQuestionCommand:
    research_question_id: ResearchQuestionId
    version_id: ResearchQuestionVersionId
    context: ExecutionContext
    expected_row_version: int | None = None


@dataclass(frozen=True, slots=True)
class CreateHypothesisCommand:
    project_id: ProjectId
    statement: str
    expected_direction: str | None
    success_criteria: object | None
    rationale: str | None
    context: ExecutionContext
    research_question_id: ResearchQuestionId | None = None


@dataclass(frozen=True, slots=True)
class ReviseHypothesisCommand:
    hypothesis_id: HypothesisId
    statement: str
    expected_direction: str | None
    success_criteria: object | None
    rationale: str | None
    expected_row_version: int
    context: ExecutionContext
    base_version_id: HypothesisVersionId | None = None


@dataclass(frozen=True, slots=True)
class UpdateHypothesisDraftCommand:
    hypothesis_id: HypothesisId
    version_id: HypothesisVersionId
    statement: str
    expected_direction: str | None
    success_criteria: object | None
    rationale: str | None
    expected_row_version: int
    context: ExecutionContext


@dataclass(frozen=True, slots=True)
class FreezeHypothesisCommand:
    hypothesis_id: HypothesisId
    version_id: HypothesisVersionId
    context: ExecutionContext
    expected_row_version: int | None = None


@dataclass(frozen=True, slots=True)
class CreateExperimentSpecCommand:
    project_id: ProjectId
    hypothesis_id: HypothesisId | None
    title: str
    objective: str
    protocol: object
    planned_metrics: object | None
    seed_policy: object | None
    analysis_plan: object | None
    context: ExecutionContext


@dataclass(frozen=True, slots=True)
class ReviseExperimentSpecCommand:
    experiment_spec_id: ExperimentSpecId
    title: str
    objective: str
    protocol: object
    planned_metrics: object | None
    seed_policy: object | None
    analysis_plan: object | None
    expected_row_version: int
    context: ExecutionContext
    base_version_id: ExperimentSpecVersionId | None = None


@dataclass(frozen=True, slots=True)
class UpdateExperimentSpecDraftCommand:
    experiment_spec_id: ExperimentSpecId
    version_id: ExperimentSpecVersionId
    title: str
    objective: str
    protocol: object
    planned_metrics: object | None
    seed_policy: object | None
    analysis_plan: object | None
    expected_row_version: int
    context: ExecutionContext


@dataclass(frozen=True, slots=True)
class FreezeExperimentSpecCommand:
    experiment_spec_id: ExperimentSpecId
    version_id: ExperimentSpecVersionId
    context: ExecutionContext
    expected_row_version: int | None = None


@dataclass(frozen=True, slots=True)
class CreateMetricDefinitionCommand:
    project_id: ProjectId | None
    name: str
    definition: object
    unit: str | None
    aggregation: str | None
    context: ExecutionContext


@dataclass(frozen=True, slots=True)
class ReviseMetricDefinitionCommand:
    metric_definition_id: MetricDefinitionId
    definition: object
    unit: str | None
    aggregation: str | None
    expected_row_version: int
    context: ExecutionContext


@dataclass(frozen=True, slots=True)
class UpdateMetricDefinitionDraftCommand:
    metric_definition_id: MetricDefinitionId
    version_id: MetricDefinitionVersionId
    definition: object
    unit: str | None
    aggregation: str | None
    expected_row_version: int
    context: ExecutionContext


@dataclass(frozen=True, slots=True)
class FreezeMetricDefinitionCommand:
    metric_definition_id: MetricDefinitionId
    version_id: MetricDefinitionVersionId
    context: ExecutionContext
    expected_row_version: int | None = None


@dataclass(frozen=True, slots=True)
class CreateRunCommand:
    project_id: ProjectId
    experiment_spec_version_id: ExperimentSpecVersionId
    run_type: str | None
    context: ExecutionContext


@dataclass(frozen=True, slots=True)
class AttachRunDatasetInputCommand:
    run_id: RunId
    dataset_snapshot_id: DatasetSnapshotId
    role: DatasetInputRole | str
    ordinal: int
    expected_row_version: int
    context: ExecutionContext


@dataclass(frozen=True, slots=True)
class AttachRunArtifactInputCommand:
    run_id: RunId
    artifact_version_id: ArtifactVersionId
    role: ArtifactInputRole | str
    ordinal: int
    expected_row_version: int
    context: ExecutionContext


@dataclass(frozen=True, slots=True)
class StartRunCommand:
    run_id: RunId
    expected_row_version: int
    context: ExecutionContext


@dataclass(frozen=True, slots=True)
class FinishRunCommand:
    run_id: RunId
    outcome: RunStatus | str
    exit_code: int | None
    failure_reason: str | None
    expected_row_version: int
    context: ExecutionContext


@dataclass(frozen=True, slots=True)
class RecordMeasurementCommand:
    run_id: RunId
    metric_definition_version_id: MetricDefinitionVersionId
    numeric_value: float | None
    structured_value: object | None
    unit: str | None
    evaluation_scope: object | None
    context: ExecutionContext


# Explicit version-suffixed aliases keep the public command vocabulary aligned with
# the existing owning-domain commands without introducing another implementation path.
UpdateMetricDefinitionVersionDraftCommand = UpdateMetricDefinitionDraftCommand
FreezeMetricDefinitionVersionCommand = FreezeMetricDefinitionCommand


@dataclass(frozen=True, slots=True)
class RegisterDatasetCommand:
    project_id: ProjectId | None
    name: str
    description: str | None
    source_locator: str | None
    context: ExecutionContext


@dataclass(frozen=True, slots=True)
class CreateDatasetSnapshotCommand:
    dataset_id: DatasetId
    manifest_hash: str | ContentHash
    selection_definition: object
    manifest_locator: str | None
    context: ExecutionContext


@dataclass(frozen=True, slots=True)
class CreateArtifactCommand:
    project_id: ProjectId | None
    artifact_type: str
    name: str
    description: str | None
    context: ExecutionContext


@dataclass(frozen=True, slots=True)
class CreateArtifactVersionCommand:
    artifact_id: ArtifactId
    data: bytes | None
    content_hash: str | ContentHash | None
    locator: str | None
    media_type: str | None
    byte_size: int | None
    metadata: object | None
    context: ExecutionContext


@dataclass(frozen=True, slots=True)
class UpdateArtifactVersionDraftCommand:
    artifact_id: ArtifactId
    version_id: ArtifactVersionId
    locator: str | None
    media_type: str | None
    byte_size: int | None
    metadata: object | None
    expected_row_version: int
    context: ExecutionContext


@dataclass(frozen=True, slots=True)
class FreezeArtifactVersionCommand:
    artifact_id: ArtifactId
    version_id: ArtifactVersionId
    context: ExecutionContext
    expected_row_version: int | None = None


@dataclass(frozen=True, slots=True)
class SetArtifactCurrentVersionCommand:
    artifact_id: ArtifactId
    version_id: ArtifactVersionId
    expected_row_version: int
    context: ExecutionContext


UowFactory = Callable[[], UnitOfWork]


class ApplicationService:
    def __init__(
        self, uow_factory: UowFactory, clock: Clock, artifact_store: ArtifactStore | None = None
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._artifact_store = artifact_store

    def create_actor(self, command: CreateActorCommand) -> ActorReadModel:
        with self._uow_factory() as uow:
            if (
                command.external_key is not None
                and uow.actors.get_by_external_key(command.external_key) is not None
            ):
                raise ResearchBaseError(
                    ErrorCode.VALIDATION_ERROR,
                    "external_key is already in use",
                    {"field": "external_key"},
                )
            actor = Actor(
                id=new_typed_id(ActorId),
                actor_type=ActorType(command.actor_type),
                display_name=command.display_name,
                external_key=command.external_key,
                created_at=self._clock.now(),
            )
            uow.actors.add(actor)
            uow.commit()
            return _actor_read_model(actor)

    def create_project(self, command: CreateProjectCommand) -> ProjectReadModel:
        actor_id = ActorId(command.context.actor_id)
        with self._uow_factory() as uow:
            _require_actor(uow, actor_id)
            project = Project(
                id=new_typed_id(ProjectId),
                name=command.name,
                description=command.description,
                created_by=actor_id,
                created_at=self._clock.now(),
            )
            uow.projects.add(project)
            uow.commit()
            return _project_read_model(project)

    def create_workspace(self, command: CreateWorkspaceCommand) -> WorkspaceReadModel:
        actor_id = ActorId(command.context.actor_id)
        with self._uow_factory() as uow:
            _require_actor(uow, actor_id)
            project = uow.projects.get(ProjectId(command.project_id))
            if project is None:
                raise _not_found("project", command.project_id)
            workspace = Workspace(
                id=new_typed_id(WorkspaceId),
                project_id=project.id,
                name=command.name,
                locator=command.locator,
                created_by=actor_id,
                created_at=self._clock.now(),
            )
            uow.workspaces.add(workspace)
            uow.commit()
            return _workspace_read_model(workspace)

    def create_research_question(
        self, command: CreateResearchQuestionCommand
    ) -> ResearchQuestionReadModel:
        actor_id = ActorId(command.context.actor_id)
        with self._uow_factory() as uow:
            project = _require_project(uow, ProjectId(command.project_id))
            _require_actor(uow, actor_id)
            question = ResearchQuestion(
                id=new_typed_id(ResearchQuestionId),
                project_id=project.id,
                created_by=actor_id,
                created_at=self._clock.now(),
            )
            version = _new_question_version(
                question.id,
                command,
                actor_id,
                self._clock,
                uow.research_questions.max_version_number(question.id) + 1,
            )
            uow.research_questions.add(question)
            uow.research_questions.add_version(version)
            uow.research_questions.update_current_version(
                question.id, version.id, question.row_version, increment=False
            )
            uow.commit()
            return _research_question_read_model(replace(question, current_version_id=version.id))

    def revise_research_question(
        self, command: ReviseResearchQuestionCommand
    ) -> ResearchQuestionReadModel:
        actor_id = ActorId(command.context.actor_id)
        question_id = ResearchQuestionId(command.research_question_id)
        with self._uow_factory() as uow:
            _require_actor(uow, actor_id)
            question = uow.research_questions.get_for_update(question_id)
            if question is None:
                raise _not_found("research question", question_id)
            _require_expected_row_version(question.row_version, command.expected_row_version)
            base = _question_base_version(uow, question, command.base_version_id)
            version = _new_question_version(
                question.id,
                command,
                actor_id,
                self._clock,
                uow.research_questions.max_version_number(question.id) + 1,
            )
            if base.status is VersionStatus.FROZEN:
                uow.research_questions.update_version(
                    base.transition_to(VersionStatus.SUPERSEDED), base.row_version
                )
            uow.research_questions.add_version(version)
            uow.research_questions.update_current_version(
                question.id, version.id, question.row_version
            )
            uow.commit()
            return _research_question_read_model(
                replace(
                    question,
                    current_version_id=version.id,
                    row_version=question.row_version + 1,
                )
            )

    def update_research_question_draft(
        self, command: UpdateResearchQuestionDraftCommand
    ) -> ResearchQuestionVersionReadModel:
        actor_id = ActorId(command.context.actor_id)
        with self._uow_factory() as uow:
            _require_actor(uow, actor_id)
            question = uow.research_questions.get(ResearchQuestionId(command.research_question_id))
            if question is None:
                raise _not_found("research question", command.research_question_id)
            version = _require_question_version_parent(
                uow.research_questions.get_version_for_update(
                    ResearchQuestionVersionId(command.version_id)
                ),
                question.id,
            )
            _require_question_version_parent(version, question.id)
            _require_expected_row_version(version.row_version, command.expected_row_version)
            try:
                updated = version.edit_material(
                    question_text=command.question_text,
                    scope=command.scope,
                    rationale=command.rationale,
                )
            except ValueError as exc:
                raise _validation_error(str(exc), "question_text") from exc
            uow.research_questions.update_version(updated, version.row_version)
            uow.commit()
            return _research_question_version_read_model(
                replace(updated, row_version=version.row_version + 1)
            )

    def freeze_research_question(
        self, command: FreezeResearchQuestionCommand
    ) -> ResearchQuestionVersionReadModel:
        actor_id = ActorId(command.context.actor_id)
        question_id = ResearchQuestionId(command.research_question_id)
        with self._uow_factory() as uow:
            _require_actor(uow, actor_id)
            question = uow.research_questions.get_for_update(question_id)
            if question is None:
                raise _not_found("research question", question_id)
            version = _require_question_version_parent(
                uow.research_questions.get_version_for_update(
                    ResearchQuestionVersionId(command.version_id)
                ),
                question.id,
            )
            _require_question_version_parent(version, question.id)
            if command.expected_row_version is not None:
                _require_expected_row_version(version.row_version, command.expected_row_version)
            frozen = version.freeze(self._clock)
            uow.research_questions.update_version(frozen, version.row_version)
            uow.research_questions.update_current_version(
                question.id, version.id, question.row_version
            )
            uow.commit()
            return _research_question_version_read_model(
                replace(frozen, row_version=version.row_version + 1)
            )

    def get_research_question_history(
        self, question_id: ResearchQuestionId
    ) -> list[ResearchQuestionVersionReadModel]:
        with self._uow_factory() as uow:
            if uow.research_questions.get(ResearchQuestionId(question_id)) is None:
                raise _not_found("research question", question_id)
            return [
                _research_question_version_read_model(version)
                for version in uow.research_questions.list_history(ResearchQuestionId(question_id))
            ]

    def create_hypothesis(self, command: CreateHypothesisCommand) -> HypothesisReadModel:
        actor_id = ActorId(command.context.actor_id)
        with self._uow_factory() as uow:
            project = _require_project(uow, ProjectId(command.project_id))
            _require_actor(uow, actor_id)
            question_id = command.research_question_id
            if question_id is not None:
                question = uow.research_questions.get(ResearchQuestionId(question_id))
                if question is None:
                    raise _not_found("research question", question_id)
                _require_same_project(project.id, question.project_id)
            hypothesis = Hypothesis(
                id=new_typed_id(HypothesisId),
                project_id=project.id,
                research_question_id=question_id,
                created_by=actor_id,
                created_at=self._clock.now(),
            )
            version = _new_hypothesis_version(
                hypothesis.id,
                command,
                actor_id,
                self._clock,
                uow.hypotheses.max_version_number(hypothesis.id) + 1,
            )
            uow.hypotheses.add(hypothesis)
            uow.hypotheses.add_version(version)
            uow.hypotheses.update_current_version(
                hypothesis.id, version.id, hypothesis.row_version, increment=False
            )
            uow.commit()
            return _hypothesis_read_model(replace(hypothesis, current_version_id=version.id))

    def revise_hypothesis(self, command: ReviseHypothesisCommand) -> HypothesisReadModel:
        actor_id = ActorId(command.context.actor_id)
        hypothesis_id = HypothesisId(command.hypothesis_id)
        with self._uow_factory() as uow:
            _require_actor(uow, actor_id)
            hypothesis = uow.hypotheses.get_for_update(hypothesis_id)
            if hypothesis is None:
                raise _not_found("hypothesis", hypothesis_id)
            _require_expected_row_version(hypothesis.row_version, command.expected_row_version)
            base = _hypothesis_base_version(uow, hypothesis, command.base_version_id)
            if command.base_version_id is None and base.status is not VersionStatus.FROZEN:
                raise ResearchBaseError(
                    ErrorCode.INVALID_STATE_TRANSITION,
                    "hypothesis revision requires a frozen current version",
                )
            version = _new_hypothesis_version(
                hypothesis.id,
                command,
                actor_id,
                self._clock,
                uow.hypotheses.max_version_number(hypothesis.id) + 1,
            )
            if base.status is VersionStatus.FROZEN:
                uow.hypotheses.update_version(
                    base.transition_to(VersionStatus.SUPERSEDED), base.row_version
                )
            uow.hypotheses.add_version(version)
            uow.hypotheses.update_current_version(hypothesis.id, version.id, hypothesis.row_version)
            uow.commit()
            return _hypothesis_read_model(
                replace(
                    hypothesis,
                    current_version_id=version.id,
                    row_version=hypothesis.row_version + 1,
                )
            )

    def update_hypothesis_draft(
        self, command: UpdateHypothesisDraftCommand
    ) -> HypothesisVersionReadModel:
        actor_id = ActorId(command.context.actor_id)
        with self._uow_factory() as uow:
            _require_actor(uow, actor_id)
            hypothesis = uow.hypotheses.get(HypothesisId(command.hypothesis_id))
            if hypothesis is None:
                raise _not_found("hypothesis", command.hypothesis_id)
            version = _require_hypothesis_version_parent(
                uow.hypotheses.get_version_for_update(HypothesisVersionId(command.version_id)),
                hypothesis.id,
            )
            _require_hypothesis_version_parent(version, hypothesis.id)
            _require_expected_row_version(version.row_version, command.expected_row_version)
            try:
                updated = version.edit_material(
                    statement=command.statement,
                    expected_direction=command.expected_direction,
                    success_criteria=command.success_criteria,
                    rationale=command.rationale,
                )
            except ValueError as exc:
                raise _validation_error(str(exc), "statement") from exc
            uow.hypotheses.update_version(updated, version.row_version)
            uow.commit()
            return _hypothesis_version_read_model(
                replace(updated, row_version=version.row_version + 1)
            )

    def freeze_hypothesis(self, command: FreezeHypothesisCommand) -> HypothesisVersionReadModel:
        actor_id = ActorId(command.context.actor_id)
        hypothesis_id = HypothesisId(command.hypothesis_id)
        with self._uow_factory() as uow:
            _require_actor(uow, actor_id)
            hypothesis = uow.hypotheses.get_for_update(hypothesis_id)
            if hypothesis is None:
                raise _not_found("hypothesis", hypothesis_id)
            version = _require_hypothesis_version_parent(
                uow.hypotheses.get_version_for_update(HypothesisVersionId(command.version_id)),
                hypothesis.id,
            )
            _require_hypothesis_version_parent(version, hypothesis.id)
            if command.expected_row_version is not None:
                _require_expected_row_version(version.row_version, command.expected_row_version)
            frozen = version.freeze(self._clock)
            uow.hypotheses.update_version(frozen, version.row_version)
            uow.hypotheses.update_current_version(hypothesis.id, version.id, hypothesis.row_version)
            uow.commit()
            return _hypothesis_version_read_model(
                replace(frozen, row_version=version.row_version + 1)
            )

    def get_hypothesis_history(
        self, hypothesis_id: HypothesisId
    ) -> list[HypothesisVersionReadModel]:
        with self._uow_factory() as uow:
            if uow.hypotheses.get(HypothesisId(hypothesis_id)) is None:
                raise _not_found("hypothesis", hypothesis_id)
            return [
                _hypothesis_version_read_model(version)
                for version in uow.hypotheses.list_history(HypothesisId(hypothesis_id))
            ]

    def create_experiment_spec(
        self, command: CreateExperimentSpecCommand
    ) -> ExperimentSpecReadModel:
        actor_id = ActorId(command.context.actor_id)
        with self._uow_factory() as uow:
            project = _require_project(uow, ProjectId(command.project_id))
            _require_actor(uow, actor_id)
            if command.hypothesis_id is not None:
                hypothesis = uow.hypotheses.get(HypothesisId(command.hypothesis_id))
                if hypothesis is None:
                    raise _not_found("hypothesis", command.hypothesis_id)
                _require_same_project(project.id, hypothesis.project_id)
            spec = ExperimentSpec(
                id=new_typed_id(ExperimentSpecId),
                project_id=project.id,
                hypothesis_id=(
                    HypothesisId(command.hypothesis_id)
                    if command.hypothesis_id is not None
                    else None
                ),
                created_by=actor_id,
                created_at=self._clock.now(),
            )
            version = _new_experiment_spec_version(spec.id, command, actor_id, self._clock, 1)
            uow.experiment_specs.add(spec)
            uow.experiment_specs.add_version(version)
            uow.experiment_specs.update_current_version(
                spec.id, version.id, spec.row_version, increment=False
            )
            uow.commit()
            return _experiment_spec_read_model(replace(spec, current_version_id=version.id))

    def revise_experiment_spec(
        self, command: ReviseExperimentSpecCommand
    ) -> ExperimentSpecReadModel:
        actor_id = ActorId(command.context.actor_id)
        spec_id = ExperimentSpecId(command.experiment_spec_id)
        with self._uow_factory() as uow:
            _require_actor(uow, actor_id)
            spec = uow.experiment_specs.get_for_update(spec_id)
            if spec is None:
                raise _not_found("experiment spec", spec_id)
            _require_expected_row_version(spec.row_version, command.expected_row_version)
            base = _experiment_spec_base_version(uow, spec, command.base_version_id)
            if command.base_version_id is None and base.status is not VersionStatus.FROZEN:
                raise ResearchBaseError(
                    ErrorCode.INVALID_STATE_TRANSITION,
                    "experiment spec revision requires a frozen current version",
                )
            version = _new_experiment_spec_version(
                spec.id,
                command,
                actor_id,
                self._clock,
                uow.experiment_specs.max_version_number(spec.id) + 1,
            )
            if base.status is VersionStatus.FROZEN:
                uow.experiment_specs.update_version(
                    base.transition_to(VersionStatus.SUPERSEDED), base.row_version
                )
            uow.experiment_specs.add_version(version)
            uow.experiment_specs.update_current_version(spec.id, version.id, spec.row_version)
            uow.commit()
            return _experiment_spec_read_model(
                replace(spec, current_version_id=version.id, row_version=spec.row_version + 1)
            )

    def update_experiment_spec_draft(
        self, command: UpdateExperimentSpecDraftCommand
    ) -> ExperimentSpecVersionReadModel:
        actor_id = ActorId(command.context.actor_id)
        with self._uow_factory() as uow:
            _require_actor(uow, actor_id)
            spec = uow.experiment_specs.get(ExperimentSpecId(command.experiment_spec_id))
            if spec is None:
                raise _not_found("experiment spec", command.experiment_spec_id)
            version = _require_experiment_spec_version_parent(
                uow.experiment_specs.get_version_for_update(
                    ExperimentSpecVersionId(command.version_id)
                ),
                spec.id,
            )
            _require_expected_row_version(version.row_version, command.expected_row_version)
            try:
                updated = version.edit_material(
                    title=command.title,
                    objective=command.objective,
                    protocol=command.protocol,
                    planned_metrics=command.planned_metrics,
                    seed_policy=command.seed_policy,
                    analysis_plan=command.analysis_plan,
                )
            except ValueError as exc:
                raise _validation_error(str(exc), "material") from exc
            updated.validate_material()
            uow.experiment_specs.update_version(updated, version.row_version)
            uow.commit()
            return _experiment_spec_version_read_model(
                replace(updated, row_version=version.row_version + 1)
            )

    def freeze_experiment_spec(
        self, command: FreezeExperimentSpecCommand
    ) -> ExperimentSpecVersionReadModel:
        actor_id = ActorId(command.context.actor_id)
        spec_id = ExperimentSpecId(command.experiment_spec_id)
        with self._uow_factory() as uow:
            _require_actor(uow, actor_id)
            spec = uow.experiment_specs.get_for_update(spec_id)
            if spec is None:
                raise _not_found("experiment spec", spec_id)
            version = _require_experiment_spec_version_parent(
                uow.experiment_specs.get_version_for_update(
                    ExperimentSpecVersionId(command.version_id)
                ),
                spec.id,
            )
            if command.expected_row_version is not None:
                _require_expected_row_version(version.row_version, command.expected_row_version)
            if spec.hypothesis_id is not None:
                hypothesis = uow.hypotheses.get(spec.hypothesis_id)
                if hypothesis is None:
                    raise _not_found("hypothesis", spec.hypothesis_id)
                _require_same_project(spec.project_id, hypothesis.project_id)
            frozen = version.freeze(self._clock)
            uow.experiment_specs.update_version(frozen, version.row_version)
            uow.experiment_specs.update_current_version(spec.id, version.id, spec.row_version)
            uow.commit()
            return _experiment_spec_version_read_model(
                replace(frozen, row_version=version.row_version + 1)
            )

    def get_experiment_spec(self, spec_id: ExperimentSpecId) -> ExperimentSpecReadModel:
        with self._uow_factory() as uow:
            spec = uow.experiment_specs.get(ExperimentSpecId(spec_id))
            if spec is None:
                raise _not_found("experiment spec", spec_id)
            return _experiment_spec_read_model(spec)

    def get_experiment_spec_history(
        self, spec_id: ExperimentSpecId
    ) -> list[ExperimentSpecVersionReadModel]:
        with self._uow_factory() as uow:
            if uow.experiment_specs.get(ExperimentSpecId(spec_id)) is None:
                raise _not_found("experiment spec", spec_id)
            return [
                _experiment_spec_version_read_model(version)
                for version in uow.experiment_specs.list_history(ExperimentSpecId(spec_id))
            ]

    def create_metric_definition(
        self, command: CreateMetricDefinitionCommand
    ) -> MetricDefinitionReadModel:
        actor_id = ActorId(command.context.actor_id)
        with self._uow_factory() as uow:
            _require_actor(uow, actor_id)
            project_id = ProjectId(command.project_id) if command.project_id is not None else None
            if project_id is not None:
                _require_project(uow, project_id)
            try:
                metric = MetricDefinition(
                    id=new_typed_id(MetricDefinitionId),
                    project_id=project_id,
                    name=command.name,
                    created_by=actor_id,
                    created_at=self._clock.now(),
                )
                version = _new_metric_definition_version(
                    metric.id, command, actor_id, self._clock, 1
                )
            except (TypeError, ValueError, ResearchBaseError) as exc:
                if isinstance(exc, ResearchBaseError):
                    raise
                raise _validation_error(str(exc), "metric definition") from exc
            uow.metric_definitions.add(metric)
            uow.metric_definition_versions.add(version)
            uow.metric_definitions.update_current_version(
                metric.id, version.id, metric.row_version, increment=False
            )
            uow.commit()
            return _metric_definition_read_model(replace(metric, current_version_id=version.id))

    def revise_metric_definition(
        self, command: ReviseMetricDefinitionCommand
    ) -> MetricDefinitionReadModel:
        actor_id = ActorId(command.context.actor_id)
        metric_id = MetricDefinitionId(command.metric_definition_id)
        with self._uow_factory() as uow:
            _require_actor(uow, actor_id)
            metric = uow.metric_definitions.get_for_update(metric_id)
            if metric is None:
                raise _not_found("metric definition", metric_id)
            _require_expected_row_version(metric.row_version, command.expected_row_version)
            current = _metric_current_version(uow, metric)
            if current is None or current.status is not VersionStatus.FROZEN:
                raise ResearchBaseError(
                    ErrorCode.INVALID_STATE_TRANSITION,
                    "metric definition revision requires a frozen current version",
                )
            version = _new_metric_definition_version(
                metric.id,
                command,
                actor_id,
                self._clock,
                uow.metric_definition_versions.max_version_number(metric.id) + 1,
            )
            uow.metric_definition_versions.update(
                current.transition_to(VersionStatus.SUPERSEDED), current.row_version
            )
            uow.metric_definition_versions.add(version)
            uow.metric_definitions.update_current_version(metric.id, version.id, metric.row_version)
            uow.commit()
            return _metric_definition_read_model(
                replace(metric, current_version_id=version.id, row_version=metric.row_version + 1)
            )

    def update_metric_definition_draft(
        self, command: UpdateMetricDefinitionDraftCommand
    ) -> MetricDefinitionVersionReadModel:
        actor_id = ActorId(command.context.actor_id)
        metric_id = MetricDefinitionId(command.metric_definition_id)
        with self._uow_factory() as uow:
            _require_actor(uow, actor_id)
            metric = uow.metric_definitions.get(metric_id)
            if metric is None:
                raise _not_found("metric definition", metric_id)
            version = uow.metric_definition_versions.get_for_update(
                MetricDefinitionVersionId(command.version_id)
            )
            version = _require_metric_version_parent(version, metric.id)
            _require_expected_row_version(version.row_version, command.expected_row_version)
            updated = version.edit_material(
                definition=command.definition,
                unit=command.unit,
                aggregation=command.aggregation,
            )
            uow.metric_definition_versions.update(updated, version.row_version)
            uow.commit()
            return _metric_definition_version_read_model(
                replace(updated, row_version=version.row_version + 1)
            )

    def freeze_metric_definition(
        self, command: FreezeMetricDefinitionCommand
    ) -> MetricDefinitionVersionReadModel:
        actor_id = ActorId(command.context.actor_id)
        metric_id = MetricDefinitionId(command.metric_definition_id)
        with self._uow_factory() as uow:
            _require_actor(uow, actor_id)
            metric = uow.metric_definitions.get_for_update(metric_id)
            if metric is None:
                raise _not_found("metric definition", metric_id)
            version = _require_metric_version_parent(
                uow.metric_definition_versions.get_for_update(
                    MetricDefinitionVersionId(command.version_id)
                ),
                metric.id,
            )
            if command.expected_row_version is not None:
                _require_expected_row_version(version.row_version, command.expected_row_version)
            frozen = version.freeze(self._clock)
            uow.metric_definition_versions.update(frozen, version.row_version)
            uow.metric_definitions.update_current_version(metric.id, version.id, metric.row_version)
            uow.commit()
            return _metric_definition_version_read_model(
                replace(frozen, row_version=version.row_version + 1)
            )

    def update_metric_definition_version_draft(
        self, command: UpdateMetricDefinitionVersionDraftCommand
    ) -> MetricDefinitionVersionReadModel:
        return self.update_metric_definition_draft(command)

    def freeze_metric_definition_version(
        self, command: FreezeMetricDefinitionVersionCommand
    ) -> MetricDefinitionVersionReadModel:
        return self.freeze_metric_definition(command)

    def get_metric_definition(self, metric_id: MetricDefinitionId) -> MetricDefinitionReadModel:
        with self._uow_factory() as uow:
            metric = uow.metric_definitions.get(MetricDefinitionId(metric_id))
            if metric is None:
                raise _not_found("metric definition", metric_id)
            return _metric_definition_read_model(metric)

    def get_metric_definition_version(
        self, version_id: MetricDefinitionVersionId
    ) -> MetricDefinitionVersionReadModel:
        with self._uow_factory() as uow:
            version = uow.metric_definition_versions.get(MetricDefinitionVersionId(version_id))
            if version is None:
                raise _not_found("metric definition version", version_id)
            return _metric_definition_version_read_model(version)

    def get_metric_definition_history(
        self, metric_id: MetricDefinitionId
    ) -> list[MetricDefinitionVersionReadModel]:
        with self._uow_factory() as uow:
            metric_id = MetricDefinitionId(metric_id)
            if uow.metric_definitions.get(metric_id) is None:
                raise _not_found("metric definition", metric_id)
            return [
                _metric_definition_version_read_model(version)
                for version in uow.metric_definition_versions.list_history(metric_id)
            ]

    def create_run(self, command: CreateRunCommand) -> RunReadModel:
        actor_id = ActorId(command.context.actor_id)
        project_id = ProjectId(command.project_id)
        spec_version_id = ExperimentSpecVersionId(command.experiment_spec_version_id)
        with self._uow_factory() as uow:
            _require_actor(uow, actor_id)
            project = _require_project(uow, project_id)
            spec_version = uow.experiment_specs.get_version(spec_version_id)
            if spec_version is None:
                raise _not_found("experiment spec version", spec_version_id)
            if spec_version.status is not VersionStatus.FROZEN:
                raise ResearchBaseError(
                    ErrorCode.VERSION_NOT_FROZEN,
                    "run requires a frozen experiment spec version",
                )
            spec = uow.experiment_specs.get(spec_version.experiment_spec_id)
            if spec is None:
                raise _not_found("experiment spec", spec_version.experiment_spec_id)
            if spec.project_id != project.id:
                raise ResearchBaseError(
                    ErrorCode.REFERENTIAL_INTEGRITY_ERROR,
                    "run project must match experiment spec project",
                )
            try:
                run = Run(
                    id=new_typed_id(RunId),
                    project_id=project.id,
                    experiment_spec_version_id=spec_version.id,
                    run_type=command.run_type or "experiment",
                    status=RunStatus.PLANNED,
                    created_by=actor_id,
                    created_at=self._clock.now(),
                )
            except (TypeError, ValueError) as exc:
                raise _validation_error(str(exc), "run") from exc
            uow.runs.add(run)
            uow.commit()
            return _run_read_model(run)

    def get_run(self, run_id: RunId) -> RunReadModel:
        with self._uow_factory() as uow:
            run = uow.runs.get(RunId(run_id))
            if run is None:
                raise _not_found("run", run_id)
            return _run_read_model(run)

    def list_run_dataset_inputs(self, run_id: RunId) -> list[RunDatasetInputReadModel]:
        with self._uow_factory() as uow:
            run = uow.runs.get(RunId(run_id))
            if run is None:
                raise _not_found("run", run_id)
            return [
                _run_dataset_input_read_model(item) for item in uow.runs.list_dataset_inputs(run.id)
            ]

    def list_run_artifact_inputs(self, run_id: RunId) -> list[RunArtifactInputReadModel]:
        with self._uow_factory() as uow:
            run = uow.runs.get(RunId(run_id))
            if run is None:
                raise _not_found("run", run_id)
            return [
                _run_artifact_input_read_model(item)
                for item in uow.runs.list_artifact_inputs(run.id)
            ]

    def attach_run_dataset_input(self, command: AttachRunDatasetInputCommand) -> RunReadModel:
        actor_id = ActorId(command.context.actor_id)
        with self._uow_factory() as uow:
            _require_actor(uow, actor_id)
            run = uow.runs.get_for_update(RunId(command.run_id))
            if run is None:
                raise _not_found("run", command.run_id)
            _require_expected_row_version(run.row_version, command.expected_row_version)
            if run.status is not RunStatus.PLANNED:
                raise ResearchBaseError(ErrorCode.IMMUTABLE_RECORD, "run inputs are sealed")
            snapshot = uow.dataset_snapshots.get(DatasetSnapshotId(command.dataset_snapshot_id))
            if snapshot is None:
                raise _not_found("dataset snapshot", command.dataset_snapshot_id)
            try:
                input = RunDatasetInput(
                    run.id,
                    snapshot.id,
                    DatasetInputRole(command.role),
                    command.ordinal,
                )
            except (TypeError, ValueError) as exc:
                raise _validation_error(str(exc), "dataset input") from exc
            uow.runs.add_dataset_input(input)
            updated = replace(run, row_version=run.row_version + 1)
            uow.runs.update(updated, run.row_version)
            uow.commit()
            return _run_read_model(updated)

    def attach_run_artifact_input(self, command: AttachRunArtifactInputCommand) -> RunReadModel:
        actor_id = ActorId(command.context.actor_id)
        with self._uow_factory() as uow:
            _require_actor(uow, actor_id)
            run = uow.runs.get_for_update(RunId(command.run_id))
            if run is None:
                raise _not_found("run", command.run_id)
            _require_expected_row_version(run.row_version, command.expected_row_version)
            if run.status is not RunStatus.PLANNED:
                raise ResearchBaseError(ErrorCode.IMMUTABLE_RECORD, "run inputs are sealed")
            version = uow.artifact_versions.get(ArtifactVersionId(command.artifact_version_id))
            if version is None:
                raise _not_found("artifact version", command.artifact_version_id)
            if version.status is not VersionStatus.FROZEN:
                raise ResearchBaseError(
                    ErrorCode.VERSION_NOT_FROZEN,
                    "run artifact inputs require frozen artifact versions",
                )
            try:
                input = RunArtifactInput(
                    run.id,
                    version.id,
                    ArtifactInputRole(command.role),
                    command.ordinal,
                )
            except (TypeError, ValueError) as exc:
                raise _validation_error(str(exc), "artifact input") from exc
            uow.runs.add_artifact_input(input)
            updated = replace(run, row_version=run.row_version + 1)
            uow.runs.update(updated, run.row_version)
            uow.commit()
            return _run_read_model(updated)

    def start_run(self, command: StartRunCommand) -> RunReadModel:
        actor_id = ActorId(command.context.actor_id)
        with self._uow_factory() as uow:
            _require_actor(uow, actor_id)
            run = uow.runs.get_for_update(RunId(command.run_id))
            if run is None:
                raise _not_found("run", command.run_id)
            _require_expected_row_version(run.row_version, command.expected_row_version)
            report = ProvenanceClosureValidator(self._uow_factory).validate_run_in_uow(uow, run.id)
            if not report.complete:
                raise ResearchBaseError(
                    ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                    "run provenance closure is incomplete",
                    {"violations": len(report.violations)},
                )
            started = run.start(self._clock)
            uow.runs.update(started, run.row_version)
            uow.commit()
            return _run_read_model(replace(started, row_version=run.row_version + 1))

    def finish_run(self, command: FinishRunCommand) -> RunReadModel:
        actor_id = ActorId(command.context.actor_id)
        with self._uow_factory() as uow:
            _require_actor(uow, actor_id)
            run = uow.runs.get_for_update(RunId(command.run_id))
            if run is None:
                raise _not_found("run", command.run_id)
            _require_expected_row_version(run.row_version, command.expected_row_version)
            finished = run.finish(command.outcome, self._clock)
            finished = replace(
                finished, exit_code=command.exit_code, failure_reason=command.failure_reason
            )
            uow.runs.update(finished, run.row_version)
            uow.commit()
            return _run_read_model(replace(finished, row_version=run.row_version + 1))

    def record_measurement(self, command: RecordMeasurementCommand) -> MeasurementReadModel:
        actor_id = ActorId(command.context.actor_id)
        run_id = RunId(command.run_id)
        metric_version_id = MetricDefinitionVersionId(command.metric_definition_version_id)
        if command.numeric_value is not None and (
            isinstance(command.numeric_value, bool)
            or not isinstance(command.numeric_value, int | float)
        ):
            raise _validation_error("numeric_value must be a number", "numeric_value")
        try:
            numeric_value = (
                float(command.numeric_value) if command.numeric_value is not None else None
            )
        except OverflowError as exc:
            raise _validation_error(
                "numeric_value is not representable as DOUBLE PRECISION", "numeric_value"
            ) from exc
        with self._uow_factory() as uow:
            _require_actor(uow, actor_id)
            run = uow.runs.get(run_id)
            if run is None:
                raise _not_found("run", run_id)
            if run.status is not RunStatus.SUCCEEDED:
                raise ResearchBaseError(
                    ErrorCode.INVALID_STATE_TRANSITION,
                    "measurements require a succeeded run",
                )
            if run.inputs_sealed_at is None:
                raise ResearchBaseError(
                    ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                    "measurements require sealed run inputs",
                )
            closure = ProvenanceClosureValidator(self._uow_factory).validate_run_in_uow(uow, run.id)
            if not closure.complete:
                raise ResearchBaseError(
                    ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                    "run provenance closure is incomplete",
                    {"violations": len(closure.violations)},
                )
            metric_version = uow.metric_definition_versions.get(metric_version_id)
            if metric_version is None:
                raise _not_found("metric definition version", metric_version_id)
            if metric_version.status is not VersionStatus.FROZEN:
                raise ResearchBaseError(
                    ErrorCode.VERSION_NOT_FROZEN,
                    "measurements require a frozen metric definition version",
                )
            metric = uow.metric_definitions.get(metric_version.metric_definition_id)
            if metric is None:
                raise _not_found("metric definition", metric_version.metric_definition_id)
            if metric.project_id is not None and metric.project_id != run.project_id:
                raise ResearchBaseError(
                    ErrorCode.REFERENTIAL_INTEGRITY_ERROR,
                    "measurement metric must belong to the run project",
                )
            if (
                metric_version.unit is not None
                and command.unit is not None
                and metric_version.unit != command.unit
            ):
                raise _validation_error(
                    "measurement unit must exactly match metric definition unit", "unit"
                )
            material = {
                "run_id": str(run.id),
                "metric_definition_version_id": str(metric_version.id),
                "numeric_value": numeric_value,
                "structured_value": command.structured_value,
                "unit": command.unit,
                "evaluation_scope": command.evaluation_scope,
            }
            try:
                content_hash = sha256_canonical_json(material)
            except (TypeError, ValueError) as exc:
                raise _validation_error(
                    "measurement material is not valid canonical JSON", "measurement"
                ) from exc
            measurement = Measurement(
                id=new_typed_id(MeasurementId),
                run_id=run.id,
                metric_definition_version_id=metric_version.id,
                numeric_value=numeric_value,
                structured_value=command.structured_value,
                unit=command.unit,
                evaluation_scope=command.evaluation_scope,
                content_hash=content_hash,
                created_by=actor_id,
                created_at=self._clock.now(),
            )
            uow.measurements.add(measurement)
            uow.commit()
            return _measurement_read_model(measurement)

    def get_measurement(self, measurement_id: MeasurementId) -> MeasurementReadModel:
        with self._uow_factory() as uow:
            measurement = uow.measurements.get(MeasurementId(measurement_id))
            if measurement is None:
                raise _not_found("measurement", measurement_id)
            return _measurement_read_model(measurement)

    def list_measurements_for_run(self, run_id: RunId) -> list[MeasurementReadModel]:
        with self._uow_factory() as uow:
            run = uow.runs.get(RunId(run_id))
            if run is None:
                raise _not_found("run", run_id)
            return [_measurement_read_model(item) for item in uow.measurements.list_by_run(run.id)]

    def validate_run_closure(self, run_id: RunId) -> ClosureReport:
        return ProvenanceClosureValidator(self._uow_factory).validate_run(RunId(run_id))

    def get_research_question(self, question_id: ResearchQuestionId) -> ResearchQuestionReadModel:
        with self._uow_factory() as uow:
            question = uow.research_questions.get(ResearchQuestionId(question_id))
            if question is None:
                raise _not_found("research question", question_id)
            return _research_question_read_model(question)

    def get_hypothesis(self, hypothesis_id: HypothesisId) -> HypothesisReadModel:
        with self._uow_factory() as uow:
            hypothesis = uow.hypotheses.get(HypothesisId(hypothesis_id))
            if hypothesis is None:
                raise _not_found("hypothesis", hypothesis_id)
            return _hypothesis_read_model(hypothesis)

    def get_actor(self, actor_id: ActorId) -> ActorReadModel:
        with self._uow_factory() as uow:
            actor = uow.actors.get(ActorId(actor_id))
            if actor is None:
                raise _not_found("actor", actor_id)
            return _actor_read_model(actor)

    def get_project(self, project_id: ProjectId) -> ProjectReadModel:
        with self._uow_factory() as uow:
            project = uow.projects.get(ProjectId(project_id))
            if project is None:
                raise _not_found("project", project_id)
            return _project_read_model(project)

    def get_workspace(self, workspace_id: WorkspaceId) -> WorkspaceReadModel:
        with self._uow_factory() as uow:
            workspace = uow.workspaces.get(WorkspaceId(workspace_id))
            if workspace is None:
                raise _not_found("workspace", workspace_id)
            return _workspace_read_model(workspace)

    def register_dataset(self, command: RegisterDatasetCommand) -> DatasetReadModel:
        actor_id = ActorId(command.context.actor_id)
        with self._uow_factory() as uow:
            _require_actor(uow, actor_id)
            if command.project_id is not None:
                _require_project(uow, ProjectId(command.project_id))
            try:
                dataset = Dataset(
                    id=new_typed_id(DatasetId),
                    project_id=(
                        ProjectId(command.project_id) if command.project_id is not None else None
                    ),
                    name=command.name,
                    description=command.description,
                    source_locator=command.source_locator,
                    created_by=actor_id,
                    created_at=self._clock.now(),
                )
            except ValueError as exc:
                raise _validation_error(str(exc), "dataset") from exc
            uow.datasets.add(dataset)
            uow.commit()
            return _dataset_read_model(dataset)

    def get_dataset(self, dataset_id: DatasetId) -> DatasetReadModel:
        with self._uow_factory() as uow:
            dataset = uow.datasets.get(DatasetId(dataset_id))
            if dataset is None:
                raise _not_found("dataset", dataset_id)
            return _dataset_read_model(dataset)

    def create_dataset_snapshot(
        self, command: CreateDatasetSnapshotCommand
    ) -> DatasetSnapshotReadModel:
        actor_id = ActorId(command.context.actor_id)
        dataset_id = DatasetId(command.dataset_id)
        manifest_hash = _normalize_content_hash(command.manifest_hash, "manifest_hash")
        try:
            canonical_json_bytes(command.selection_definition)
        except (TypeError, ValueError) as exc:
            raise _validation_error(
                "selection_definition is not valid canonical JSON", "selection_definition"
            ) from exc
        content_hash = sha256_canonical_json(
            {
                "manifest_hash": str(manifest_hash),
                "selection_definition": command.selection_definition,
            }
        )

        try:
            with self._uow_factory() as uow:
                _require_dataset(uow, dataset_id)
                _require_actor(uow, actor_id)
                existing = uow.dataset_snapshots.find_by_dataset_and_content_hash(
                    dataset_id, str(content_hash)
                )
                if existing is not None:
                    return _dataset_snapshot_read_model(existing)
                snapshot = DatasetSnapshot(
                    id=new_typed_id(DatasetSnapshotId),
                    dataset_id=dataset_id,
                    manifest_hash=manifest_hash,
                    selection_definition=command.selection_definition,
                    manifest_locator=command.manifest_locator,
                    content_hash=content_hash,
                    created_by=actor_id,
                    created_at=self._clock.now(),
                )
                uow.dataset_snapshots.add(snapshot)
                uow.commit()
                return _dataset_snapshot_read_model(snapshot)
        except ResearchBaseError as exc:
            if exc.code is not ErrorCode.DUPLICATE_CONTENT:
                raise

        with self._uow_factory() as uow:
            existing = uow.dataset_snapshots.find_by_dataset_and_content_hash(
                dataset_id, str(content_hash)
            )
            if existing is None:
                raise ResearchBaseError(
                    ErrorCode.DUPLICATE_CONTENT,
                    "dataset snapshot creation raced without a visible winner",
                )
            return _dataset_snapshot_read_model(existing)

    def get_dataset_snapshot(self, snapshot_id: DatasetSnapshotId) -> DatasetSnapshotReadModel:
        with self._uow_factory() as uow:
            snapshot = uow.dataset_snapshots.get(DatasetSnapshotId(snapshot_id))
            if snapshot is None:
                raise _not_found("dataset snapshot", snapshot_id)
            return _dataset_snapshot_read_model(snapshot)

    def create_artifact(self, command: CreateArtifactCommand) -> ArtifactReadModel:
        actor_id = ActorId(command.context.actor_id)
        with self._uow_factory() as uow:
            _require_actor(uow, actor_id)
            if command.project_id is not None:
                _require_project(uow, ProjectId(command.project_id))
            try:
                artifact = Artifact(
                    id=new_typed_id(ArtifactId),
                    project_id=(
                        ProjectId(command.project_id) if command.project_id is not None else None
                    ),
                    artifact_type=command.artifact_type,
                    name=command.name,
                    description=command.description,
                    created_by=actor_id,
                    created_at=self._clock.now(),
                )
            except (TypeError, ValueError) as exc:
                raise _validation_error(str(exc), "artifact") from exc
            uow.artifacts.add(artifact)
            uow.commit()
            return _artifact_read_model(artifact)

    def get_artifact(self, artifact_id: ArtifactId) -> ArtifactReadModel:
        with self._uow_factory() as uow:
            artifact = uow.artifacts.get(ArtifactId(artifact_id))
            if artifact is None:
                raise _not_found("artifact", artifact_id)
            return _artifact_read_model(artifact)

    def create_artifact_version(
        self, command: CreateArtifactVersionCommand
    ) -> ArtifactVersionReadModel:
        store = _require_artifact_store(self._artifact_store)
        content_hash, locator, byte_size = _verify_or_store_artifact(
            store,
            command.data,
            command.content_hash,
            command.locator,
            command.byte_size,
        )
        actor_id = ActorId(command.context.actor_id)
        artifact_id = ArtifactId(command.artifact_id)
        try:
            with self._uow_factory() as uow:
                _require_actor(uow, actor_id)
                artifact = uow.artifacts.get_for_update(artifact_id)
                if artifact is None:
                    raise _not_found("artifact", artifact_id)
                existing = uow.artifact_versions.find_by_artifact_and_content_hash(
                    artifact_id, str(content_hash)
                )
                if existing is not None:
                    return _artifact_version_read_model(existing)
                current = None
                if artifact.current_version_id is not None:
                    current = uow.artifact_versions.get_for_update(artifact.current_version_id)
                    if current is None:
                        raise _not_found("artifact version", artifact.current_version_id)
                    if current.artifact_id != artifact.id:
                        raise ResearchBaseError(
                            ErrorCode.REFERENTIAL_INTEGRITY_ERROR,
                            "current version must belong to the artifact",
                        )
                try:
                    version = ArtifactVersion(
                        id=new_typed_id(ArtifactVersionId),
                        artifact_id=artifact.id,
                        version_number=uow.artifact_versions.max_version_number(artifact.id) + 1,
                        status=VersionStatus.DRAFT,
                        locator=locator,
                        media_type=command.media_type,
                        byte_size=byte_size,
                        content_hash=content_hash,
                        metadata=command.metadata,
                        created_by=actor_id,
                        created_at=self._clock.now(),
                    )
                except (TypeError, ValueError) as exc:
                    raise _validation_error(str(exc), "artifact version") from exc
                if current is not None and current.status is VersionStatus.FROZEN:
                    uow.artifact_versions.update(
                        current.transition_to(VersionStatus.SUPERSEDED), current.row_version
                    )
                uow.artifact_versions.add(version)
                uow.artifacts.update_current_version(artifact.id, version.id, artifact.row_version)
                uow.commit()
                return _artifact_version_read_model(version)
        except ResearchBaseError as exc:
            if exc.code is not ErrorCode.DUPLICATE_CONTENT:
                raise

        with self._uow_factory() as uow:
            existing = uow.artifact_versions.find_by_artifact_and_content_hash(
                artifact_id, str(content_hash)
            )
            if existing is None:
                raise ResearchBaseError(
                    ErrorCode.DUPLICATE_CONTENT,
                    "artifact version creation raced without a visible winner",
                )
            return _artifact_version_read_model(existing)

    def get_artifact_version(self, version_id: ArtifactVersionId) -> ArtifactVersionReadModel:
        with self._uow_factory() as uow:
            version = uow.artifact_versions.get(ArtifactVersionId(version_id))
            if version is None:
                raise _not_found("artifact version", version_id)
            return _artifact_version_read_model(version)

    def get_artifact_history(self, artifact_id: ArtifactId) -> list[ArtifactVersionReadModel]:
        with self._uow_factory() as uow:
            if uow.artifacts.get(ArtifactId(artifact_id)) is None:
                raise _not_found("artifact", artifact_id)
            return [
                _artifact_version_read_model(version)
                for version in uow.artifact_versions.list_history(ArtifactId(artifact_id))
            ]

    def update_artifact_version_draft(
        self, command: UpdateArtifactVersionDraftCommand
    ) -> ArtifactVersionReadModel:
        store = _require_artifact_store(self._artifact_store)
        actor_id = ActorId(command.context.actor_id)
        artifact_id = ArtifactId(command.artifact_id)
        version_id = ArtifactVersionId(command.version_id)
        with self._uow_factory() as uow:
            _require_actor(uow, actor_id)
            artifact = uow.artifacts.get_for_update(artifact_id)
            if artifact is None:
                raise _not_found("artifact", artifact_id)
            version = uow.artifact_versions.get_for_update(version_id)
            if version is None:
                raise _not_found("artifact version", version_id)
            if version.artifact_id != artifact.id:
                raise ResearchBaseError(
                    ErrorCode.REFERENTIAL_INTEGRITY_ERROR,
                    "artifact version must belong to the artifact",
                )
            _require_expected_row_version(version.row_version, command.expected_row_version)
            verified_size = _verify_stored_artifact(store, version.content_hash, command.byte_size)
            try:
                updated = version.edit_metadata(
                    locator=command.locator,
                    media_type=command.media_type,
                    byte_size=verified_size,
                    metadata=command.metadata,
                )
            except (TypeError, ValueError) as exc:
                raise _validation_error(str(exc), "artifact version") from exc
            uow.artifact_versions.update(updated, version.row_version)
            uow.commit()
            return _artifact_version_read_model(
                replace(updated, row_version=version.row_version + 1)
            )

    def freeze_artifact_version(
        self, command: FreezeArtifactVersionCommand
    ) -> ArtifactVersionReadModel:
        store = _require_artifact_store(self._artifact_store)
        actor_id = ActorId(command.context.actor_id)
        artifact_id = ArtifactId(command.artifact_id)
        version_id = ArtifactVersionId(command.version_id)
        with self._uow_factory() as uow:
            _require_actor(uow, actor_id)
            artifact = uow.artifacts.get_for_update(artifact_id)
            if artifact is None:
                raise _not_found("artifact", artifact_id)
            version = uow.artifact_versions.get_for_update(version_id)
            if version is None:
                raise _not_found("artifact version", version_id)
            if version.artifact_id != artifact.id:
                raise ResearchBaseError(
                    ErrorCode.REFERENTIAL_INTEGRITY_ERROR,
                    "artifact version must belong to the artifact",
                )
            if command.expected_row_version is not None:
                _require_expected_row_version(version.row_version, command.expected_row_version)
            _verify_stored_artifact(store, version.content_hash, version.byte_size)
            frozen = version.freeze(self._clock)
            uow.artifact_versions.update(frozen, version.row_version)
            uow.artifacts.update_current_version(artifact.id, version.id, artifact.row_version)
            uow.commit()
            return _artifact_version_read_model(
                replace(frozen, row_version=version.row_version + 1)
            )

    def set_artifact_current_version(
        self, command: SetArtifactCurrentVersionCommand
    ) -> ArtifactReadModel:
        actor_id = ActorId(command.context.actor_id)
        artifact_id = ArtifactId(command.artifact_id)
        version_id = ArtifactVersionId(command.version_id)
        with self._uow_factory() as uow:
            _require_actor(uow, actor_id)
            artifact = uow.artifacts.get_for_update(artifact_id)
            if artifact is None:
                raise _not_found("artifact", artifact_id)
            uow.artifacts.update_current_version(
                artifact.id, version_id, command.expected_row_version
            )
            uow.commit()
            return _artifact_read_model(
                replace(
                    artifact,
                    current_version_id=version_id,
                    row_version=artifact.row_version + 1,
                )
            )


def _require_actor(uow: UnitOfWork, actor_id: ActorId) -> Actor:
    actor = uow.actors.get(actor_id)
    if actor is None:
        raise _not_found("actor", actor_id)
    return actor


def _require_project(uow: UnitOfWork, project_id: ProjectId) -> Project:
    project = uow.projects.get(project_id)
    if project is None:
        raise _not_found("project", project_id)
    return project


def _require_dataset(uow: UnitOfWork, dataset_id: DatasetId) -> Dataset:
    dataset = uow.datasets.get(dataset_id)
    if dataset is None:
        raise _not_found("dataset", dataset_id)
    return dataset


def _normalize_content_hash(value: str | ContentHash, field: str) -> ContentHash:
    try:
        return ContentHash(value)
    except (TypeError, ValueError) as exc:
        raise _validation_error(f"{field} must be a valid SHA-256 hex digest", field) from exc


def _require_expected_row_version(actual: int, expected: int) -> None:
    if actual != expected:
        raise ResearchBaseError(
            ErrorCode.CONCURRENT_MODIFICATION,
            "resource was modified concurrently",
            {"expected_row_version": expected, "actual_row_version": actual},
        )


def _new_question_version(
    parent_id: ResearchQuestionId,
    command: CreateResearchQuestionCommand | ReviseResearchQuestionCommand,
    actor_id: ActorId,
    clock: Clock,
    version_number: int = 1,
) -> ResearchQuestionVersion:
    try:
        return ResearchQuestionVersion(
            id=new_typed_id(ResearchQuestionVersionId),
            research_question_id=parent_id,
            version_number=version_number,
            status=VersionStatus.DRAFT,
            question_text=command.question_text,
            scope=command.scope,
            rationale=command.rationale,
            created_by=actor_id,
            created_at=clock.now(),
        )
    except ValueError as exc:
        raise _validation_error(str(exc), "question_text") from exc


def _new_hypothesis_version(
    parent_id: HypothesisId,
    command: CreateHypothesisCommand | ReviseHypothesisCommand,
    actor_id: ActorId,
    clock: Clock,
    version_number: int = 1,
) -> HypothesisVersion:
    try:
        return HypothesisVersion(
            id=new_typed_id(HypothesisVersionId),
            hypothesis_id=parent_id,
            version_number=version_number,
            status=VersionStatus.DRAFT,
            statement=command.statement,
            expected_direction=command.expected_direction,
            success_criteria=command.success_criteria,
            rationale=command.rationale,
            created_by=actor_id,
            created_at=clock.now(),
        )
    except ValueError as exc:
        raise _validation_error(str(exc), "statement") from exc


def _new_experiment_spec_version(
    parent_id: ExperimentSpecId,
    command: CreateExperimentSpecCommand | ReviseExperimentSpecCommand,
    actor_id: ActorId,
    clock: Clock,
    version_number: int,
) -> ExperimentSpecVersion:
    try:
        version = ExperimentSpecVersion(
            id=new_typed_id(ExperimentSpecVersionId),
            experiment_spec_id=parent_id,
            version_number=version_number,
            status=VersionStatus.DRAFT,
            title=command.title,
            objective=command.objective,
            protocol=command.protocol,
            planned_metrics=command.planned_metrics,
            seed_policy=command.seed_policy,
            analysis_plan=command.analysis_plan,
            created_by=actor_id,
            created_at=clock.now(),
        )
        version.validate_material()
        return version
    except ValueError as exc:
        raise _validation_error(str(exc), "material") from exc


def _new_metric_definition_version(
    parent_id: MetricDefinitionId,
    command: CreateMetricDefinitionCommand | ReviseMetricDefinitionCommand,
    actor_id: ActorId,
    clock: Clock,
    version_number: int,
) -> MetricDefinitionVersion:
    try:
        version = MetricDefinitionVersion(
            id=new_typed_id(MetricDefinitionVersionId),
            metric_definition_id=parent_id,
            version_number=version_number,
            status=VersionStatus.DRAFT,
            definition=command.definition,
            unit=command.unit,
            aggregation=command.aggregation,
            created_by=actor_id,
            created_at=clock.now(),
        )
        version.validate_material()
        return version
    except (TypeError, ValueError) as exc:
        raise _validation_error(str(exc), "material") from exc


def _question_base_version(
    uow: UnitOfWork,
    question: ResearchQuestion,
    base_version_id: ResearchQuestionVersionId | None,
) -> ResearchQuestionVersion:
    version = (
        uow.research_questions.get_version(base_version_id)
        if base_version_id is not None
        else uow.research_questions.get_current_version(question.id)
    )
    return _require_question_version_parent(version, question.id)


def _hypothesis_base_version(
    uow: UnitOfWork,
    hypothesis: Hypothesis,
    base_version_id: HypothesisVersionId | None,
) -> HypothesisVersion:
    version = (
        uow.hypotheses.get_version(base_version_id)
        if base_version_id is not None
        else uow.hypotheses.get_current_version(hypothesis.id)
    )
    return _require_hypothesis_version_parent(version, hypothesis.id)


def _experiment_spec_base_version(
    uow: UnitOfWork,
    spec: ExperimentSpec,
    base_version_id: ExperimentSpecVersionId | None,
) -> ExperimentSpecVersion:
    version = (
        uow.experiment_specs.get_version(base_version_id)
        if base_version_id is not None
        else uow.experiment_specs.get_current_version(spec.id)
    )
    return _require_experiment_spec_version_parent(version, spec.id)


def _require_question_version_parent(
    version: ResearchQuestionVersion | None, question_id: ResearchQuestionId
) -> ResearchQuestionVersion:
    if version is None:
        raise _not_found("research question version", question_id)
    if version.research_question_id != question_id:
        raise ResearchBaseError(
            ErrorCode.REFERENTIAL_INTEGRITY_ERROR,
            "version does not belong to the research question",
        )
    return version


def _require_hypothesis_version_parent(
    version: HypothesisVersion | None, hypothesis_id: HypothesisId
) -> HypothesisVersion:
    if version is None:
        raise _not_found("hypothesis version", hypothesis_id)
    if version.hypothesis_id != hypothesis_id:
        raise ResearchBaseError(
            ErrorCode.REFERENTIAL_INTEGRITY_ERROR,
            "version does not belong to the hypothesis",
        )
    return version


def _require_experiment_spec_version_parent(
    version: ExperimentSpecVersion | None, spec_id: ExperimentSpecId
) -> ExperimentSpecVersion:
    if version is None:
        raise _not_found("experiment spec version", spec_id)
    if version.experiment_spec_id != spec_id:
        raise ResearchBaseError(
            ErrorCode.REFERENTIAL_INTEGRITY_ERROR,
            "version does not belong to the experiment spec",
        )
    return version


def _metric_current_version(
    uow: UnitOfWork, metric: MetricDefinition
) -> MetricDefinitionVersion | None:
    if metric.current_version_id is None:
        return None
    version = uow.metric_definition_versions.get_for_update(metric.current_version_id)
    return _require_metric_version_parent(version, metric.id)


def _require_metric_version_parent(
    version: MetricDefinitionVersion | None, metric_id: MetricDefinitionId
) -> MetricDefinitionVersion:
    if version is None:
        raise _not_found("metric definition version", metric_id)
    if version.metric_definition_id != metric_id:
        raise ResearchBaseError(
            ErrorCode.REFERENTIAL_INTEGRITY_ERROR,
            "metric definition version must belong to the metric definition",
        )
    return version


def _require_same_project(left: ProjectId, right: ProjectId) -> None:
    if left != right:
        raise ResearchBaseError(
            ErrorCode.REFERENTIAL_INTEGRITY_ERROR,
            "linked research question must belong to the same project",
        )


def _not_found(resource: str, identifier: object) -> ResearchBaseError:
    return ResearchBaseError(
        ErrorCode.NOT_FOUND,
        f"{resource} was not found",
        {"id": str(identifier)},
    )


def _validation_error(message: str, field: str) -> ResearchBaseError:
    return ResearchBaseError(ErrorCode.VALIDATION_ERROR, message, {"field": field})


def _research_question_read_model(question: ResearchQuestion) -> ResearchQuestionReadModel:
    if question.current_version_id is None:
        raise ResearchBaseError(
            ErrorCode.VALIDATION_ERROR, "research question has no current version"
        )
    return ResearchQuestionReadModel(
        id=question.id,
        project_id=question.project_id,
        created_by=question.created_by,
        created_at=question.created_at,
        current_version_id=question.current_version_id,
        row_version=question.row_version,
    )


def _research_question_version_read_model(
    version: ResearchQuestionVersion,
) -> ResearchQuestionVersionReadModel:
    return ResearchQuestionVersionReadModel(
        id=version.id,
        research_question_id=version.research_question_id,
        version_number=version.version_number,
        status=version.status,
        question_text=version.question_text,
        scope=version.scope,
        rationale=version.rationale,
        content_hash=version.content_hash,
        hash_scheme=version.hash_scheme,
        created_by=version.created_by,
        created_at=version.created_at,
        frozen_at=version.frozen_at,
        row_version=version.row_version,
    )


def _hypothesis_read_model(hypothesis: Hypothesis) -> HypothesisReadModel:
    if hypothesis.current_version_id is None:
        raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, "hypothesis has no current version")
    return HypothesisReadModel(
        id=hypothesis.id,
        project_id=hypothesis.project_id,
        research_question_id=hypothesis.research_question_id,
        created_by=hypothesis.created_by,
        created_at=hypothesis.created_at,
        current_version_id=hypothesis.current_version_id,
        row_version=hypothesis.row_version,
    )


def _hypothesis_version_read_model(version: HypothesisVersion) -> HypothesisVersionReadModel:
    return HypothesisVersionReadModel(
        id=version.id,
        hypothesis_id=version.hypothesis_id,
        version_number=version.version_number,
        status=version.status,
        statement=version.statement,
        expected_direction=version.expected_direction,
        success_criteria=version.success_criteria,
        rationale=version.rationale,
        content_hash=version.content_hash,
        hash_scheme=version.hash_scheme,
        created_by=version.created_by,
        created_at=version.created_at,
        frozen_at=version.frozen_at,
        row_version=version.row_version,
    )


def _experiment_spec_read_model(spec: ExperimentSpec) -> ExperimentSpecReadModel:
    if spec.current_version_id is None:
        raise ResearchBaseError(
            ErrorCode.VALIDATION_ERROR, "experiment spec has no current version"
        )
    return ExperimentSpecReadModel(
        id=spec.id,
        project_id=spec.project_id,
        hypothesis_id=spec.hypothesis_id,
        created_by=spec.created_by,
        created_at=spec.created_at,
        current_version_id=spec.current_version_id,
        row_version=spec.row_version,
    )


def _experiment_spec_version_read_model(
    version: ExperimentSpecVersion,
) -> ExperimentSpecVersionReadModel:
    return ExperimentSpecVersionReadModel(
        id=version.id,
        experiment_spec_id=version.experiment_spec_id,
        version_number=version.version_number,
        status=version.status,
        title=version.title,
        objective=version.objective,
        protocol=version.protocol,
        planned_metrics=version.planned_metrics,
        seed_policy=version.seed_policy,
        analysis_plan=version.analysis_plan,
        content_hash=version.content_hash,
        hash_scheme=version.hash_scheme,
        created_by=version.created_by,
        created_at=version.created_at,
        frozen_at=version.frozen_at,
        row_version=version.row_version,
    )


def _actor_read_model(actor: Actor) -> ActorReadModel:
    return ActorReadModel(
        id=actor.id,
        actor_type=actor.actor_type,
        display_name=actor.display_name,
        external_key=actor.external_key,
        created_at=actor.created_at,
        retired_at=actor.retired_at,
        row_version=actor.row_version,
    )


def _project_read_model(project: Project) -> ProjectReadModel:
    return ProjectReadModel(
        id=project.id,
        name=project.name,
        description=project.description,
        lifecycle_status=LifecycleStatus(project.lifecycle_status),
        created_by=project.created_by,
        created_at=project.created_at,
        row_version=project.row_version,
    )


def _workspace_read_model(workspace: Workspace) -> WorkspaceReadModel:
    return WorkspaceReadModel(
        id=workspace.id,
        project_id=workspace.project_id,
        name=workspace.name,
        locator=workspace.locator,
        lifecycle_status=LifecycleStatus(workspace.lifecycle_status),
        created_by=workspace.created_by,
        created_at=workspace.created_at,
        row_version=workspace.row_version,
    )


def _dataset_read_model(dataset: Dataset) -> DatasetReadModel:
    return DatasetReadModel(
        id=dataset.id,
        project_id=dataset.project_id,
        name=dataset.name,
        description=dataset.description,
        source_locator=dataset.source_locator,
        lifecycle_status=dataset.lifecycle_status,
        created_by=dataset.created_by,
        created_at=dataset.created_at,
        row_version=dataset.row_version,
    )


def _dataset_snapshot_read_model(
    snapshot: DatasetSnapshot,
) -> DatasetSnapshotReadModel:
    return DatasetSnapshotReadModel(
        id=snapshot.id,
        dataset_id=snapshot.dataset_id,
        manifest_hash=snapshot.manifest_hash,
        selection_definition=snapshot.selection_definition,
        manifest_locator=snapshot.manifest_locator,
        content_hash=snapshot.content_hash,
        created_by=snapshot.created_by,
        created_at=snapshot.created_at,
    )


def _artifact_read_model(artifact: Artifact) -> ArtifactReadModel:
    return ArtifactReadModel(
        id=artifact.id,
        project_id=artifact.project_id,
        artifact_type=artifact.artifact_type,
        name=artifact.name,
        description=artifact.description,
        current_version_id=artifact.current_version_id,
        created_by=artifact.created_by,
        created_at=artifact.created_at,
        row_version=artifact.row_version,
    )


def _artifact_version_read_model(version: ArtifactVersion) -> ArtifactVersionReadModel:
    return ArtifactVersionReadModel(
        id=version.id,
        artifact_id=version.artifact_id,
        version_number=version.version_number,
        status=version.status,
        locator=version.locator,
        media_type=version.media_type,
        byte_size=version.byte_size,
        content_hash=version.content_hash,
        metadata=version.metadata,
        created_by=version.created_by,
        created_at=version.created_at,
        frozen_at=version.frozen_at,
        row_version=version.row_version,
    )


def _metric_definition_read_model(metric: MetricDefinition) -> MetricDefinitionReadModel:
    return MetricDefinitionReadModel(
        id=metric.id,
        project_id=metric.project_id,
        name=metric.name,
        created_by=metric.created_by,
        created_at=metric.created_at,
        current_version_id=metric.current_version_id,
        row_version=metric.row_version,
    )


def _metric_definition_version_read_model(
    version: MetricDefinitionVersion,
) -> MetricDefinitionVersionReadModel:
    return MetricDefinitionVersionReadModel(
        id=version.id,
        metric_definition_id=version.metric_definition_id,
        version_number=version.version_number,
        status=version.status,
        definition=version.definition,
        unit=version.unit,
        aggregation=version.aggregation,
        content_hash=version.content_hash,
        hash_scheme=version.hash_scheme,
        created_by=version.created_by,
        created_at=version.created_at,
        frozen_at=version.frozen_at,
        row_version=version.row_version,
    )


def _measurement_read_model(measurement: Measurement) -> MeasurementReadModel:
    return MeasurementReadModel(
        id=measurement.id,
        run_id=measurement.run_id,
        metric_definition_version_id=measurement.metric_definition_version_id,
        numeric_value=measurement.numeric_value,
        structured_value=measurement.structured_value,
        unit=measurement.unit,
        evaluation_scope=measurement.evaluation_scope,
        content_hash=measurement.content_hash,
        created_by=measurement.created_by,
        created_at=measurement.created_at,
    )


def _run_read_model(run: Run) -> RunReadModel:
    return RunReadModel(
        id=run.id,
        project_id=run.project_id,
        experiment_spec_version_id=run.experiment_spec_version_id,
        run_type=run.run_type,
        status=run.status,
        inputs_sealed_at=run.inputs_sealed_at,
        started_at=run.started_at,
        finished_at=run.finished_at,
        exit_code=run.exit_code,
        failure_reason=run.failure_reason,
        created_by=run.created_by,
        created_at=run.created_at,
        row_version=run.row_version,
    )


def _run_dataset_input_read_model(
    input: RunDatasetInput,
) -> RunDatasetInputReadModel:
    return RunDatasetInputReadModel(
        run_id=input.run_id,
        dataset_snapshot_id=input.dataset_snapshot_id,
        role=input.role,
        ordinal=input.ordinal,
    )


def _run_artifact_input_read_model(
    input: RunArtifactInput,
) -> RunArtifactInputReadModel:
    return RunArtifactInputReadModel(
        run_id=input.run_id,
        artifact_version_id=input.artifact_version_id,
        role=input.role,
        ordinal=input.ordinal,
    )


def _require_artifact_store(store: ArtifactStore | None) -> ArtifactStore:
    if store is None:
        raise ResearchBaseError(
            ErrorCode.VALIDATION_ERROR,
            "ArtifactStore is required for ArtifactVersion commands",
        )
    return store


def _verify_or_store_artifact(
    store: ArtifactStore,
    data: bytes | None,
    supplied_hash: str | ContentHash | None,
    locator: str | None,
    declared_size: int | None,
) -> tuple[ContentHash, str, int]:
    try:
        if data is not None:
            if not isinstance(data, bytes):
                raise TypeError("artifact data must be bytes")
            expected = f"sha256:{ContentHash(supplied_hash)}" if supplied_hash is not None else None
            identity = store.put_verified(data, expected)
            content_hash = _content_hash_from_store_identity(identity)
            if not store.verify(identity):
                raise ValueError("stored artifact failed verification")
            actual_size = len(data)
        else:
            if supplied_hash is None:
                raise ValueError("content_hash is required when data is absent")
            content_hash = ContentHash(supplied_hash)
            identity = _store_identity(content_hash)
            actual_size = _verify_stored_artifact(store, content_hash, declared_size)
        if declared_size is not None and declared_size != actual_size:
            raise ValueError("byte_size does not match verified artifact bytes")
        return content_hash, locator or identity, actual_size
    except (OSError, TypeError, ValueError) as exc:
        raise _validation_error(str(exc), "artifact content") from exc


def _verify_stored_artifact(
    store: ArtifactStore, content_hash: ContentHash, declared_size: int | None
) -> int:
    identity = _store_identity(content_hash)
    try:
        if not store.verify(identity):
            raise ValueError("artifact store object is missing or failed verification")
        actual_size = len(store.open(identity))
    except (OSError, TypeError, ValueError) as exc:
        raise _validation_error(str(exc), "artifact content") from exc
    if declared_size is not None and declared_size != actual_size:
        raise _validation_error("byte_size does not match verified artifact bytes", "byte_size")
    return actual_size


def _store_identity(content_hash: ContentHash) -> str:
    return f"sha256:{content_hash}"


def _content_hash_from_store_identity(identity: str) -> ContentHash:
    if not isinstance(identity, str) or not identity.startswith("sha256:"):
        raise ValueError("ArtifactStore returned an invalid content identity")
    return ContentHash(identity.removeprefix("sha256:"))
