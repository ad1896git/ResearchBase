"""Project creation checks authority before any write (Application layer, no database)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from researchbase.application.commands import ApplicationService, CreateProjectCommand
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.execution_context import ExecutionContext
from researchbase.foundation.time import FixedClock


class _Recorder:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.actor_present = True

    def get(self, _key):
        return object() if self.actor_present else None

    def add(self, entity) -> None:
        self.added.append(entity)


class _FakeUow:
    def __init__(self, recorder: _Recorder, events: list[str]) -> None:
        self.projects = recorder
        self.actors = recorder
        self._events = events

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> bool:
        return False

    def begin_serializable(self) -> None:
        self._events.append("begin")

    def commit(self) -> None:
        self._events.append("commit")


def _command(actor_id) -> CreateProjectCommand:
    context = ExecutionContext(actor_id=actor_id, request_id=uuid4(), client_type="cli")
    return CreateProjectCommand("Research", None, context)


def _service(recorder, events, authorizer):
    return ApplicationService(
        lambda: _FakeUow(recorder, events),
        FixedClock(datetime(2026, 11, 3, tzinfo=UTC)),
        project_creation_authorizer=authorizer,
    )


def test_refused_creation_writes_nothing():
    recorder, events = _Recorder(), []

    def refuse(uow, actor_id):
        raise ResearchBaseError(ErrorCode.FORBIDDEN, "current project authority is unavailable")

    with pytest.raises(ResearchBaseError) as caught:
        _service(recorder, events, refuse).create_project(_command(uuid4()))
    assert caught.value.code is ErrorCode.FORBIDDEN
    assert recorder.added == []
    assert "commit" not in events


def test_authorizer_runs_before_the_project_is_added():
    recorder, events = _Recorder(), []
    seen: list[object] = []

    def allow(uow, actor_id):
        events.append("authorize")
        seen.append(actor_id)

    actor = uuid4()
    _service(recorder, events, allow).create_project(_command(actor))
    assert seen == [actor]
    assert events.index("authorize") < events.index("commit")
    assert len(recorder.added) == 1


def test_missing_actor_is_still_rejected_after_authorization():
    recorder, events = _Recorder(), []
    recorder.actor_present = False
    with pytest.raises(ResearchBaseError):
        _service(recorder, events, lambda uow, actor_id: None).create_project(_command(uuid4()))
    assert recorder.added == []
