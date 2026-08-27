"""Minimal PR-02 create/get application commands."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace

from researchbase.application.dto import (
    ActorReadModel,
    ExperimentSpecReadModel,
    ExperimentSpecVersionReadModel,
    HypothesisReadModel,
    HypothesisVersionReadModel,
    ProjectReadModel,
    ResearchQuestionReadModel,
    ResearchQuestionVersionReadModel,
    WorkspaceReadModel,
)
from researchbase.application.ports import UnitOfWork
from researchbase.domain.experiment import (
    ExperimentSpec,
    ExperimentSpecId,
    ExperimentSpecVersion,
    ExperimentSpecVersionId,
)
from researchbase.domain.identity import Actor, ActorType
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
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.execution_context import ExecutionContext
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


UowFactory = Callable[[], UnitOfWork]


class ApplicationService:
    def __init__(self, uow_factory: UowFactory, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

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
            uow.hypotheses.update_current_version(
                hypothesis.id, version.id, hypothesis.row_version
            )
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
            uow.hypotheses.update_current_version(
                hypothesis.id, version.id, hypothesis.row_version
            )
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
            version = _new_experiment_spec_version(
                spec.id, command, actor_id, self._clock, 1
            )
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
            uow.experiment_specs.update_current_version(
                spec.id, version.id, spec.row_version
            )
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
            uow.experiment_specs.update_current_version(
                spec.id, version.id, spec.row_version
            )
            uow.commit()
            return _experiment_spec_version_read_model(
                replace(frozen, row_version=version.row_version + 1)
            )

    def get_experiment_spec(
        self, spec_id: ExperimentSpecId
    ) -> ExperimentSpecReadModel:
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

    def get_research_question(
        self, question_id: ResearchQuestionId
    ) -> ResearchQuestionReadModel:
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
