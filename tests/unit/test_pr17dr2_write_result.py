from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from researchbase.application.commands import (
    ApplicationService,
    CreateProjectCommand,
    WriteProjectionTarget,
)
from researchbase.application.dto import WriteResult
from researchbase.domain.identity import Actor, ActorType
from researchbase.foundation.execution_context import ExecutionContext
from researchbase.foundation.ids import ActorId
from researchbase.foundation.time import FixedClock


class _ProjectUow:
    def __init__(self, actor: Actor) -> None:
        self.actors = SimpleNamespace(get=lambda actor_id: actor if actor.id == actor_id else None)
        self.projects = SimpleNamespace(add=lambda project: None)
        self.committed = False

    def __enter__(self) -> _ProjectUow:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def commit(self) -> None:
        self.committed = True


def test_real_application_write_command_returns_shared_write_result() -> None:
    actor_id = ActorId(uuid4())
    actor = Actor(
        id=actor_id,
        actor_type=ActorType.HUMAN,
        display_name="Reviewer",
        external_key=None,
        created_at=datetime(2026, 9, 5, tzinfo=UTC),
    )
    uow = _ProjectUow(actor)
    timestamp = datetime(2026, 9, 5, 1, 2, 3, tzinfo=UTC)
    service = ApplicationService(lambda: uow, FixedClock(timestamp))  # type: ignore[arg-type]

    result = service.create_project(
        CreateProjectCommand(
            name="project",
            description=None,
            context=ExecutionContext(actor_id=actor_id, request_id=uuid4(), client_type="agent"),
        )
    )

    assert isinstance(result, WriteResult)
    assert result.version_id is None
    assert result.content_hash is None
    assert result.row_version == 1
    assert result.server_timestamp == timestamp
    assert set(WriteResult.model_fields) == {
        "id",
        "version_id",
        "content_hash",
        "row_version",
        "server_timestamp",
    }


def test_application_projection_uses_the_write_result_identifier() -> None:
    service = ApplicationService(lambda: object(), FixedClock(datetime(2026, 9, 5, tzinfo=UTC)))  # type: ignore[arg-type]
    expected_id = uuid4()
    observed: list[object] = []

    def get_project(project_id: object) -> object:
        observed.append(project_id)
        return object()

    service.get_project = get_project  # type: ignore[method-assign]

    result = service.project_write_result(
        WriteResult(id=expected_id, server_timestamp=datetime(2026, 9, 5, tzinfo=UTC)),
        WriteProjectionTarget.PROJECT,
    )

    assert result is not None
    assert observed == [expected_id]


def test_version_projection_requires_a_stable_version_identifier() -> None:
    service = ApplicationService(lambda: object(), FixedClock(datetime(2026, 9, 5, tzinfo=UTC)))  # type: ignore[arg-type]

    with pytest.raises(Exception, match="requires version_id"):
        service.project_write_result(
            WriteResult(id=uuid4(), server_timestamp=datetime(2026, 9, 5, tzinfo=UTC)),
            WriteProjectionTarget.CLAIM_VERSION,
        )


def test_write_result_is_immutable_and_rejects_extra_fields() -> None:
    result = WriteResult(
        id=uuid4(),
        server_timestamp=datetime(2026, 9, 5, tzinfo=UTC),
    )

    with pytest.raises((TypeError, ValueError)):
        result.row_version = 2  # type: ignore[misc]

    with pytest.raises(ValueError, match="extra"):
        WriteResult(
            id=uuid4(),
            server_timestamp=datetime(2026, 9, 5, tzinfo=UTC),
            payload="forbidden",  # type: ignore[call-arg]
        )
