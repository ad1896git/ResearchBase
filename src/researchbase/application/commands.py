"""Minimal PR-02 create/get application commands."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from researchbase.application.dto import ActorReadModel, ProjectReadModel, WorkspaceReadModel
from researchbase.application.ports import UnitOfWork
from researchbase.domain.identity import Actor, ActorType
from researchbase.domain.organization import (
    LifecycleStatus,
    Project,
    ProjectId,
    Workspace,
    WorkspaceId,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.execution_context import ExecutionContext
from researchbase.foundation.ids import ActorId, new_typed_id
from researchbase.foundation.time import Clock


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


def _not_found(resource: str, identifier: object) -> ResearchBaseError:
    return ResearchBaseError(
        ErrorCode.NOT_FOUND,
        f"{resource} was not found",
        {"id": str(identifier)},
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
