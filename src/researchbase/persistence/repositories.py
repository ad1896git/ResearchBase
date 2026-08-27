"""Explicit SQLAlchemy repository adapters for PR-02 domain models."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from researchbase.domain.identity import Actor, ActorType
from researchbase.domain.organization import (
    LifecycleStatus,
    Project,
    ProjectId,
    Workspace,
    WorkspaceId,
)
from researchbase.foundation.ids import ActorId
from researchbase.persistence.models import ActorModel, ProjectModel, WorkspaceModel


class SqlAlchemyActorRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, actor: Actor) -> None:
        self._session.add(
            ActorModel(
                id=actor.id,
                actor_type=actor.actor_type.value,
                display_name=actor.display_name,
                external_key=actor.external_key,
                created_at=actor.created_at,
                retired_at=actor.retired_at,
                row_version=actor.row_version,
            )
        )

    def get(self, actor_id: ActorId) -> Actor | None:
        model = self._session.get(ActorModel, actor_id)
        return _actor_from_model(model) if model is not None else None

    def get_by_external_key(self, external_key: str) -> Actor | None:
        model = self._session.scalar(
            select(ActorModel).where(ActorModel.external_key == external_key)
        )
        return _actor_from_model(model) if model is not None else None


class SqlAlchemyProjectRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, project: Project) -> None:
        self._session.add(
            ProjectModel(
                id=project.id,
                name=project.name,
                description=project.description,
                lifecycle_status=project.lifecycle_status.value,
                created_by=project.created_by,
                created_at=project.created_at,
                row_version=project.row_version,
            )
        )

    def get(self, project_id: ProjectId) -> Project | None:
        model = self._session.get(ProjectModel, project_id)
        return _project_from_model(model) if model is not None else None


class SqlAlchemyWorkspaceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, workspace: Workspace) -> None:
        self._session.add(
            WorkspaceModel(
                id=workspace.id,
                project_id=workspace.project_id,
                name=workspace.name,
                locator=workspace.locator,
                lifecycle_status=workspace.lifecycle_status.value,
                created_by=workspace.created_by,
                created_at=workspace.created_at,
                row_version=workspace.row_version,
            )
        )

    def get(self, workspace_id: WorkspaceId) -> Workspace | None:
        model = self._session.get(WorkspaceModel, workspace_id)
        return _workspace_from_model(model) if model is not None else None


def _actor_from_model(model: ActorModel) -> Actor:
    return Actor(
        id=ActorId(model.id),
        actor_type=ActorType(model.actor_type),
        display_name=model.display_name,
        external_key=model.external_key,
        created_at=model.created_at,
        retired_at=model.retired_at,
        row_version=model.row_version,
    )


def _project_from_model(model: ProjectModel) -> Project:
    return Project(
        id=ProjectId(model.id),
        name=model.name,
        description=model.description,
        lifecycle_status=LifecycleStatus(model.lifecycle_status),
        created_by=ActorId(model.created_by),
        created_at=model.created_at,
        row_version=model.row_version,
    )


def _workspace_from_model(model: WorkspaceModel) -> Workspace:
    return Workspace(
        id=WorkspaceId(model.id),
        project_id=ProjectId(model.project_id),
        name=model.name,
        locator=model.locator,
        lifecycle_status=LifecycleStatus(model.lifecycle_status),
        created_by=ActorId(model.created_by),
        created_at=model.created_at,
        row_version=model.row_version,
    )
