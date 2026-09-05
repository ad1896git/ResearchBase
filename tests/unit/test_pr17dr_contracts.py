from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import DBAPIError

from researchbase.application.commands import ApplicationService, CreateProjectCommand
from researchbase.application.dto import (
    ProjectReadModel,
    ResearchQuestionVersionReadModel,
    WriteResult,
    write_result,
)
from researchbase.domain.organization import LifecycleStatus, ProjectId
from researchbase.domain.research import ResearchQuestionId, ResearchQuestionVersionId
from researchbase.foundation.errors import ErrorCode
from researchbase.foundation.execution_context import ExecutionContext
from researchbase.foundation.hashing import ContentHash
from researchbase.foundation.ids import ActorId
from researchbase.foundation.time import FixedClock
from researchbase.foundation.versioning import VersionStatus
from researchbase.persistence.uow import _normalize_database_error


@dataclass
class _DriverError(Exception):
    sqlstate: str

    @property
    def diag(self) -> object:
        return type("Diagnostic", (), {"constraint_name": None})()


@pytest.mark.parametrize(
    ("sqlstate", "expected"),
    [
        ("P17D1", ErrorCode.IMMUTABLE_RECORD),
        ("P17D2", ErrorCode.INVALID_STATE_TRANSITION),
        ("P17D3", ErrorCode.PROVENANCE_CLOSURE_VIOLATION),
        ("P17D4", ErrorCode.VALIDATION_ERROR),
        ("P17D5", ErrorCode.CONCURRENT_MODIFICATION),
    ],
)
def test_pr17d_sqlstates_normalize_to_semantic_errors(sqlstate: str, expected: ErrorCode) -> None:
    error = DBAPIError("UPDATE", {}, _DriverError(sqlstate), False)

    normalized = _normalize_database_error(error)

    assert normalized is not None
    assert normalized.code is expected


def test_write_result_converts_a_read_model_without_changing_adapter_model() -> None:
    project_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    actor_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    timestamp = datetime(2026, 9, 5, 1, 2, 3, 456789, tzinfo=UTC)
    project = ProjectReadModel(
        id=ProjectId(project_id),
        name="project",
        description=None,
        lifecycle_status=LifecycleStatus.ACTIVE,
        created_by=ActorId(actor_id),
        created_at=timestamp,
        row_version=3,
    )

    result = write_result(project, timestamp)

    assert isinstance(result, WriteResult)
    assert result.id == project_id
    assert result.version_id is None
    assert result.content_hash is None
    assert result.row_version == 3
    assert result.server_timestamp == timestamp
    assert project.name == "project"

    service = ApplicationService(lambda: object(), FixedClock(timestamp))  # type: ignore[arg-type]
    assert service.to_write_result(project) == result


def test_write_result_rejects_naive_server_timestamp() -> None:
    with pytest.raises(ValueError, match="UTC-aware"):
        WriteResult(
            id=uuid4(),
            version_id=None,
            content_hash=None,
            row_version=None,
            server_timestamp=datetime(2026, 9, 5, 1, 2, 3),
        )


def test_write_result_uses_version_identity_and_hash_for_version_writes() -> None:
    version_id = ResearchQuestionVersionId(uuid4())
    timestamp = datetime(2026, 9, 5, 1, 2, 3, tzinfo=UTC)
    version = ResearchQuestionVersionReadModel(
        id=version_id,
        research_question_id=ResearchQuestionId(uuid4()),
        version_number=1,
        status=VersionStatus.FROZEN,
        question_text="question",
        scope=None,
        rationale=None,
        content_hash=ContentHash("a" * 64),
        hash_scheme="sha256-canonical-json-v1",
        created_by=ActorId(uuid4()),
        created_at=timestamp,
        frozen_at=timestamp,
        row_version=2,
    )

    result = write_result(version, timestamp)

    assert result.id == version_id
    assert result.version_id == version_id
    assert result.content_hash == "a" * 64
    assert result.row_version == 2


def test_application_validation_failure_is_normalized_before_repository_work() -> None:
    context = ExecutionContext(
        actor_id=uuid4(),
        request_id=uuid4(),
        client_type="test",
    )

    def failing_uow_factory() -> object:
        raise ValueError("project name must not be blank")

    service = ApplicationService(
        failing_uow_factory,  # type: ignore[arg-type]
        FixedClock(datetime(2026, 9, 5, tzinfo=UTC)),
    )

    with pytest.raises(Exception) as raised:
        service.create_project(CreateProjectCommand("", None, context))

    assert getattr(raised.value, "code", None) is ErrorCode.VALIDATION_ERROR
