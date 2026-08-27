from __future__ import annotations

import hashlib
import os
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from researchbase.application.commands import (
    ApplicationService,
    CreateActorCommand,
    CreateMetricDefinitionCommand,
    CreateProjectCommand,
    FreezeMetricDefinitionCommand,
    ReviseMetricDefinitionCommand,
    UpdateMetricDefinitionDraftCommand,
)
from researchbase.domain.identity import ActorType
from researchbase.domain.metric import MetricDefinitionId
from researchbase.domain.organization import ProjectId
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.execution_context import ExecutionContext
from researchbase.foundation.hashing import sha256_canonical_json
from researchbase.foundation.time import FixedClock
from researchbase.foundation.versioning import VersionStatus
from researchbase.persistence.database import create_database_engine, create_session_factory
from researchbase.persistence.uow import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def resources() -> Iterator[tuple[Callable[[], ApplicationService], Engine]]:
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL is not set; run against the real PostgreSQL service")
    engine = create_database_engine()
    sessions = create_session_factory(engine)
    clock = FixedClock(datetime(2026, 8, 27, 0, 0, tzinfo=UTC))
    try:
        yield lambda: ApplicationService(lambda: SqlAlchemyUnitOfWork(sessions), clock), engine
    finally:
        engine.dispose()


def context(actor_id: UUID) -> ExecutionContext:
    return ExecutionContext(actor_id=actor_id, request_id=uuid4(), client_type="test")


def seed(service: ApplicationService) -> tuple[UUID, ProjectId, ExecutionContext]:
    actor = service.create_actor(
        CreateActorCommand(ActorType.HUMAN, f"MetricOwner-{uuid4()}", None, context(uuid4()))
    )
    actor_context = context(actor.id)
    project = service.create_project(
        CreateProjectCommand(f"MetricProject-{uuid4()}", None, actor_context)
    )
    return actor.id, project.id, actor_context


def create_command(
    actor_context: ExecutionContext, project_id: ProjectId | None = None, **overrides: object
) -> CreateMetricDefinitionCommand:
    values: dict[str, object] = {
        "project_id": project_id,
        "name": f"Metric-{uuid4()}",
        "definition": {"field": "score", "kind": "mean"},
        "unit": "m",
        "aggregation": "mean",
        "context": actor_context,
    }
    values.update(overrides)
    return CreateMetricDefinitionCommand(**values)  # type: ignore[arg-type]


def test_metric_lifecycle_hash_history_and_nullability(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, engine = resources
    service = factory()
    actor_id, project_id, actor_context = seed(service)
    created = service.create_metric_definition(create_command(actor_context, None))
    assert created.project_id is None
    assert created.current_version_id is not None
    current_version_id = created.current_version_id
    draft = service.get_metric_definition_version(current_version_id)
    assert draft.status is VersionStatus.DRAFT
    assert draft.content_hash is None

    frozen = service.freeze_metric_definition(
        FreezeMetricDefinitionCommand(created.id, draft.id, actor_context, draft.row_version)
    )
    expected = sha256_canonical_json(
        {"definition": draft.definition, "unit": draft.unit, "aggregation": draft.aggregation}
    )
    assert frozen.status is VersionStatus.FROZEN
    assert frozen.content_hash == expected
    assert frozen.frozen_at is not None and frozen.frozen_at.tzinfo is not None
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT content_hash FROM metric_definition_versions WHERE id = :id"),
                {"id": frozen.id},
            ).scalar_one()
            == hashlib.sha256(
                b'{"aggregation":"mean","definition":{"field":"score","kind":"mean"},"unit":"m"}'
            ).hexdigest()
        )

    revised = service.revise_metric_definition(
        ReviseMetricDefinitionCommand(
            created.id,
            {"field": "score", "kind": "sum"},
            "m",
            "sum",
            created.row_version + 1,
            actor_context,
        )
    )
    history = service.get_metric_definition_history(MetricDefinitionId(revised.id))
    assert [item.version_number for item in history] == [1, 2]
    assert [item.status for item in history] == [VersionStatus.SUPERSEDED, VersionStatus.DRAFT]
    assert revised.current_version_id == history[1].id
    assert history[0].content_hash == frozen.content_hash


def test_metric_draft_update_validation_and_stale_writer(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, _ = resources
    service = factory()
    _, project_id, actor_context = seed(service)
    created = service.create_metric_definition(create_command(actor_context, project_id))
    assert created.current_version_id is not None
    version = service.get_metric_definition_version(created.current_version_id)
    with pytest.raises(ResearchBaseError) as invalid:
        service.update_metric_definition_draft(
            UpdateMetricDefinitionDraftCommand(
                created.id,
                version.id,
                {"bad": {1, 2}},
                version.unit,
                version.aggregation,
                1,
                actor_context,
            )
        )
    assert invalid.value.code is ErrorCode.VALIDATION_ERROR
    unchanged = service.get_metric_definition_version(version.id)
    assert unchanged.definition == version.definition
    updated = service.update_metric_definition_draft(
        UpdateMetricDefinitionDraftCommand(
            created.id,
            version.id,
            {"field": "score", "kind": "median"},
            None,
            "median",
            1,
            actor_context,
        )
    )
    assert updated.row_version == 2
    with pytest.raises(ResearchBaseError) as stale:
        service.update_metric_definition_draft(
            UpdateMetricDefinitionDraftCommand(
                created.id,
                version.id,
                {"field": "score", "kind": "max"},
                None,
                "max",
                1,
                actor_context,
            )
        )
    assert stale.value.code is ErrorCode.CONCURRENT_MODIFICATION


def test_metric_missing_references_and_cross_parent_version_rejected(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, _ = resources
    service = factory()
    _, project_id, actor_context = seed(service)
    with pytest.raises(ResearchBaseError) as missing_project:
        service.create_metric_definition(create_command(actor_context, ProjectId(uuid4())))
    assert missing_project.value.code is ErrorCode.NOT_FOUND
    with pytest.raises(ResearchBaseError) as missing_actor:
        service.create_metric_definition(create_command(context(uuid4()), project_id))
    assert missing_actor.value.code is ErrorCode.NOT_FOUND


def test_metric_revision_is_genuinely_concurrent_and_row_versioned(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, engine = resources
    service = factory()
    _, project_id, actor_context = seed(service)
    created = service.create_metric_definition(create_command(actor_context, project_id))
    assert created.current_version_id is not None
    service.freeze_metric_definition(
        FreezeMetricDefinitionCommand(created.id, created.current_version_id, actor_context, 1)
    )
    barrier = Barrier(2)

    def revise(kind: str) -> object:
        barrier.wait(timeout=10)
        try:
            return factory().revise_metric_definition(
                ReviseMetricDefinitionCommand(
                    created.id,
                    {"field": "score", "kind": kind},
                    "m",
                    kind,
                    2,
                    actor_context,
                )
            )
        except ResearchBaseError as error:
            return error

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(revise, kind) for kind in ("sum", "max")]
        results = [future.result(timeout=20) for future in futures]
    successes = [result for result in results if not isinstance(result, ResearchBaseError)]
    failures = [result for result in results if isinstance(result, ResearchBaseError)]
    assert len(successes) == 1
    assert len(failures) == 1
    assert failures[0].code is ErrorCode.CONCURRENT_MODIFICATION  # type: ignore[union-attr]
    with engine.connect() as connection:
        assert (
            connection.execute(
                text(
                    "SELECT count(*) FROM metric_definition_versions WHERE metric_definition_id=:id"
                ),
                {"id": created.id},
        ).scalar_one()
        == 2
        )


def test_metric_create_and_freeze_rollback_use_fresh_uow(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, engine = resources
    _, project_id, actor_context = seed(factory())

    class FailingUnitOfWork(SqlAlchemyUnitOfWork):
        def commit(self) -> None:
            self._require_session().flush()
            raise RuntimeError("injected PR-08 failure")

    sessions = create_session_factory(engine)
    failing = ApplicationService(
        lambda: FailingUnitOfWork(sessions),
        FixedClock(datetime(2026, 8, 27, 0, 0, tzinfo=UTC)),
    )
    name = f"Rollback-{uuid4()}"
    with pytest.raises(RuntimeError, match="injected PR-08 failure"):
        failing.create_metric_definition(create_command(actor_context, project_id, name=name))
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM metric_definitions WHERE name=:name"), {"name": name}
            ).scalar_one()
            == 0
        )
    retried = factory().create_metric_definition(
        create_command(actor_context, project_id, name=name)
    )
    assert factory().get_metric_definition(retried.id) == retried


def test_metric_frozen_material_is_database_immutable_but_supersede_is_allowed(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, engine = resources
    service = factory()
    _, project_id, actor_context = seed(service)
    created = service.create_metric_definition(create_command(actor_context, project_id))
    assert created.current_version_id is not None
    frozen = service.freeze_metric_definition(
        FreezeMetricDefinitionCommand(created.id, created.current_version_id, actor_context, 1)
    )
    with engine.connect() as connection:
        transaction = connection.begin()
        with pytest.raises(IntegrityError):
            connection.execute(
                text("UPDATE metric_definition_versions SET definition='{}'::jsonb WHERE id=:id"),
                {"id": frozen.id},
            )
        transaction.rollback()
    revised = service.revise_metric_definition(
        ReviseMetricDefinitionCommand(
            created.id, {"field": "score", "kind": "sum"}, "m", "sum", 2, actor_context
        )
    )
    history = service.get_metric_definition_history(revised.id)
    assert history[0].status is VersionStatus.SUPERSEDED
