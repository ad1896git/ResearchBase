"""Minimal PR-02 create/get application commands."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace

from researchbase.application.dto import (
    ActorReadModel,
    HypothesisReadModel,
    HypothesisVersionReadModel,
    ProjectReadModel,
    ResearchQuestionReadModel,
    ResearchQuestionVersionReadModel,
    WorkspaceReadModel,
)
from researchbase.application.ports import UnitOfWork
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
