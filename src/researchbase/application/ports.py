"""Repository and transaction ports used by application commands."""

from __future__ import annotations

from types import TracebackType
from typing import Protocol

from researchbase.domain.identity import Actor
from researchbase.domain.organization import Project, ProjectId, Workspace, WorkspaceId
from researchbase.foundation.ids import ActorId


class ActorRepository(Protocol):
    def add(self, actor: Actor) -> None: ...

    def get(self, actor_id: ActorId) -> Actor | None: ...

    def get_by_external_key(self, external_key: str) -> Actor | None: ...


class ProjectRepository(Protocol):
    def add(self, project: Project) -> None: ...

    def get(self, project_id: ProjectId) -> Project | None: ...


class WorkspaceRepository(Protocol):
    def add(self, workspace: Workspace) -> None: ...

    def get(self, workspace_id: WorkspaceId) -> Workspace | None: ...


class UnitOfWork(Protocol):
    actors: ActorRepository
    projects: ProjectRepository
    workspaces: WorkspaceRepository

    def __enter__(self) -> UnitOfWork: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...
