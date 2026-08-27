from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from researchbase.domain.identity import Actor, ActorType
from researchbase.domain.organization import (
    LifecycleStatus,
    Project,
    ProjectId,
    Workspace,
    WorkspaceId,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.ids import ActorId
from researchbase.persistence.database import create_database_engine, create_session_factory
from researchbase.persistence.uow import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def session_factory() -> Iterator[sessionmaker]:
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL is not set; run against the real PostgreSQL service")
    engine = create_database_engine()
    factory = create_session_factory(engine)
    try:
        yield factory
    finally:
        engine.dispose()


@pytest.fixture
def uow_factory(session_factory: sessionmaker) -> Callable[[], SqlAlchemyUnitOfWork]:
    return lambda: SqlAlchemyUnitOfWork(session_factory)


def actor(external_key: str | None = None) -> Actor:
    return Actor(
        id=ActorId(uuid4()),
        actor_type=ActorType.HUMAN,
        display_name=f"Actor {uuid4()}",
        external_key=external_key,
        created_at=datetime.now(UTC),
    )


def project(created_by: ActorId, project_id: ProjectId | None = None) -> Project:
    return Project(
        id=project_id or ProjectId(uuid4()),
        name=f"Project {uuid4()}",
        created_by=created_by,
        created_at=datetime.now(UTC),
    )


def workspace(created_by: ActorId, project_id: ProjectId) -> Workspace:
    return Workspace(
        id=WorkspaceId(uuid4()),
        project_id=project_id,
        name=f"Workspace {uuid4()}",
        created_by=created_by,
        created_at=datetime.now(UTC),
    )


def test_commit_persists_cross_repository_records(
    uow_factory: Callable[[], SqlAlchemyUnitOfWork],
) -> None:
    created_actor = actor()
    created_project = project(created_actor.id)

    with uow_factory() as uow:
        uow.actors.add(created_actor)
        uow.projects.add(created_project)
        uow.commit()

    with uow_factory() as uow:
        assert uow.actors.get(created_actor.id) == created_actor
        assert uow.projects.get(created_project.id) == created_project


def test_explicit_rollback_discards_records(
    uow_factory: Callable[[], SqlAlchemyUnitOfWork],
) -> None:
    created_actor = actor()
    created_project = project(created_actor.id)

    with uow_factory() as uow:
        uow.actors.add(created_actor)
        uow.projects.add(created_project)
        uow.rollback()

    with uow_factory() as uow:
        assert uow.actors.get(created_actor.id) is None
        assert uow.projects.get(created_project.id) is None


def test_exception_rolls_back_all_repositories(
    uow_factory: Callable[[], SqlAlchemyUnitOfWork],
) -> None:
    created_actor = actor()
    created_project = project(created_actor.id)

    with pytest.raises(RuntimeError):
        with uow_factory() as uow:
            uow.actors.add(created_actor)
            uow.projects.add(created_project)
            raise RuntimeError("fail before commit")

    with uow_factory() as uow:
        assert uow.actors.get(created_actor.id) is None
        assert uow.projects.get(created_project.id) is None


def test_atomic_multi_repository_rollback_on_failure(
    uow_factory: Callable[[], SqlAlchemyUnitOfWork],
) -> None:
    created_actor = actor()
    created_project = project(created_actor.id)

    with pytest.raises(RuntimeError):
        with uow_factory() as uow:
            uow.actors.add(created_actor)
            uow.projects.add(created_project)
            raise RuntimeError("failure after both repository writes")

    with uow_factory() as uow:
        assert uow.actors.get(created_actor.id) is None
        assert uow.projects.get(created_project.id) is None


@pytest.mark.parametrize("missing", ["actor", "project"])
def test_workspace_foreign_keys_are_enforced_by_postgresql(
    uow_factory: Callable[[], SqlAlchemyUnitOfWork], missing: str
) -> None:
    created_actor = actor()
    project_id = ProjectId(uuid4())
    if missing == "actor":
        with uow_factory() as uow:
            uow.actors.add(created_actor)
            uow.projects.add(project(created_actor.id, project_id))
            uow.commit()
        created_by = ActorId(uuid4())
        with pytest.raises(IntegrityError):
            with uow_factory() as uow:
                uow.workspaces.add(workspace(created_by, project_id))
                uow.commit()
    else:
        with uow_factory() as uow:
            uow.actors.add(created_actor)
            uow.commit()
        with pytest.raises(IntegrityError):
            with uow_factory() as uow:
                uow.workspaces.add(workspace(created_actor.id, project_id))
                uow.commit()


def test_project_created_by_foreign_key_is_enforced_by_postgresql(
    uow_factory: Callable[[], SqlAlchemyUnitOfWork],
) -> None:
    with pytest.raises(IntegrityError):
        with uow_factory() as uow:
            uow.projects.add(project(ActorId(uuid4())))
            uow.commit()


def test_external_key_unique_constraint_is_enforced_by_postgresql(
    uow_factory: Callable[[], SqlAlchemyUnitOfWork],
) -> None:
    external_key = f"unique-{uuid4()}"
    first = actor(external_key)
    second = actor(external_key)

    with uow_factory() as uow:
        uow.actors.add(first)
        uow.commit()

    with pytest.raises(ResearchBaseError) as raised:
        with uow_factory() as uow:
            uow.actors.add(second)
            uow.commit()

    assert raised.value.code is ErrorCode.VALIDATION_ERROR
    assert isinstance(raised.value.__cause__, IntegrityError)


def test_repository_mapping_preserves_workspace_fields(
    uow_factory: Callable[[], SqlAlchemyUnitOfWork],
) -> None:
    created_actor = actor()
    created_project = project(created_actor.id)
    created_workspace = workspace(created_actor.id, created_project.id)

    with uow_factory() as uow:
        uow.actors.add(created_actor)
        uow.projects.add(created_project)
        uow.workspaces.add(created_workspace)
        uow.commit()

    with uow_factory() as uow:
        loaded = uow.workspaces.get(created_workspace.id)
        assert loaded == created_workspace
        assert loaded is not None
        assert loaded.lifecycle_status is LifecycleStatus.ACTIVE
