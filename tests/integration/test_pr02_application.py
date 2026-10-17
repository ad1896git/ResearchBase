from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from researchbase.application.commands import (
    CreateActorCommand,
    CreateProjectCommand,
    CreateWorkspaceCommand,
)
from researchbase.application.dto import ActorReadModel, ProjectReadModel, WorkspaceReadModel
from researchbase.domain.identity import ActorType
from researchbase.domain.organization import LifecycleStatus
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.execution_context import ExecutionContext
from researchbase.foundation.ids import ActorId
from researchbase.foundation.time import FixedClock
from researchbase.persistence.database import create_database_engine, create_session_factory
from researchbase.persistence.uow import SqlAlchemyUnitOfWork
from tests.application_compat import LegacyApplicationService as ApplicationService

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def service_factory() -> Iterator[Callable[[], ApplicationService]]:
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL is not set; run against the real PostgreSQL service")
    engine = create_database_engine()
    sessions = create_session_factory(engine)
    clock = FixedClock(datetime(2026, 8, 27, 0, 0, tzinfo=UTC))
    try:
        yield lambda: ApplicationService(lambda: SqlAlchemyUnitOfWork(sessions), clock)
    finally:
        engine.dispose()


def context(actor_id: UUID | None = None) -> ExecutionContext:
    return ExecutionContext(
        actor_id=actor_id or uuid4(),
        request_id=uuid4(),
        client_type="test",
    )


def test_create_and_get_actor(service_factory: Callable[[], ApplicationService]) -> None:
    service = service_factory()
    command = CreateActorCommand(ActorType.AGENT, f"Agent {uuid4()}", f"ext-{uuid4()}", context())

    created = service.create_actor(command)
    loaded = service.get_actor(ActorId(created.id))

    assert isinstance(created, ActorReadModel)
    assert loaded == created
    assert created.actor_type is ActorType.AGENT
    assert created.row_version == 1


def test_create_project_and_workspace_propagate_context_actor(
    service_factory: Callable[[], ApplicationService],
) -> None:
    service = service_factory()
    actor_record = service.create_actor(
        CreateActorCommand(ActorType.HUMAN, f"Owner {uuid4()}", None, context())
    )
    actor_context = context(actor_record.id)

    created_project = service.create_project(
        CreateProjectCommand(f"Project {uuid4()}", "description", actor_context)
    )
    created_workspace = service.create_workspace(
        CreateWorkspaceCommand(
            created_project.id,
            f"Workspace {uuid4()}",
            "/tmp/work",
            actor_context,
        )
    )

    assert isinstance(created_project, ProjectReadModel)
    assert isinstance(created_workspace, WorkspaceReadModel)
    assert created_project.created_by == actor_record.id
    assert created_workspace.created_by == actor_record.id
    assert created_workspace.project_id == created_project.id
    assert created_project.lifecycle_status is LifecycleStatus.ACTIVE


def test_get_missing_record_uses_machine_readable_not_found(
    service_factory: Callable[[], ApplicationService],
) -> None:
    with pytest.raises(ResearchBaseError) as raised:
        service_factory().get_actor(ActorId(uuid4()))

    assert raised.value.code is ErrorCode.NOT_FOUND


def test_create_project_requires_existing_actor(
    service_factory: Callable[[], ApplicationService],
) -> None:
    with pytest.raises(ResearchBaseError) as raised:
        service_factory().create_project(
            CreateProjectCommand(f"Project {uuid4()}", None, context())
        )

    assert raised.value.code is ErrorCode.NOT_FOUND


def test_duplicate_external_key_uses_stable_validation_error(
    service_factory: Callable[[], ApplicationService],
) -> None:
    service = service_factory()
    external_key = f"duplicate-{uuid4()}"
    service.create_actor(
        CreateActorCommand(ActorType.SERVICE, f"One {uuid4()}", external_key, context())
    )

    with pytest.raises(ResearchBaseError) as raised:
        service.create_actor(
            CreateActorCommand(ActorType.SERVICE, f"Two {uuid4()}", external_key, context())
        )

    assert raised.value.code is ErrorCode.VALIDATION_ERROR
    assert raised.value.details == {"field": "external_key"}
