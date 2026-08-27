from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from researchbase.application.commands import (
    ApplicationService,
    CreateActorCommand,
    CreateDatasetSnapshotCommand,
    CreateProjectCommand,
    RegisterDatasetCommand,
)
from researchbase.domain.evidence import DatasetId
from researchbase.domain.identity import ActorType
from researchbase.domain.organization import ProjectId
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.execution_context import ExecutionContext
from researchbase.foundation.hashing import sha256_canonical_json
from researchbase.foundation.time import FixedClock
from researchbase.persistence.database import create_database_engine, create_session_factory
from researchbase.persistence.uow import SqlAlchemyUnitOfWork

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
    return ExecutionContext(actor_id=actor_id or uuid4(), request_id=uuid4(), client_type="test")


def seed(service: ApplicationService) -> tuple[UUID, ProjectId, ExecutionContext]:
    actor = service.create_actor(
        CreateActorCommand(ActorType.HUMAN, f"DatasetOwner-{uuid4()}", None, context())
    )
    actor_context = context(actor.id)
    project = service.create_project(
        CreateProjectCommand(f"DatasetProject-{uuid4()}", None, actor_context)
    )
    return actor.id, project.id, actor_context


def register_command(
    project_id: ProjectId | None, actor_context: ExecutionContext, **overrides: object
) -> RegisterDatasetCommand:
    values: dict[str, object] = {
        "project_id": project_id,
        "name": f"Dataset-{uuid4()}",
        "description": "dataset description",
        "source_locator": "s3://bucket/source",
        "context": actor_context,
    }
    values.update(overrides)
    return RegisterDatasetCommand(**values)  # type: ignore[arg-type]


def snapshot_command(
    dataset_id: DatasetId, actor_context: ExecutionContext, **overrides: object
) -> CreateDatasetSnapshotCommand:
    values: dict[str, object] = {
        "dataset_id": dataset_id,
        "manifest_hash": "a" * 64,
        "selection_definition": {"split": "train", "where": {"status": "ready"}},
        "manifest_locator": "file:///first/manifest.json",
        "context": actor_context,
    }
    values.update(overrides)
    return CreateDatasetSnapshotCommand(**values)  # type: ignore[arg-type]


def test_register_and_get_dataset_accepts_nullable_project(
    service_factory: Callable[[], ApplicationService],
) -> None:
    service = service_factory()
    actor_id, project_id, actor_context = seed(service)
    created = service.register_dataset(register_command(project_id, actor_context))
    loaded = service.get_dataset(created.id)

    assert loaded == created
    assert created.project_id == project_id
    assert created.created_by == actor_id

    external = service.register_dataset(register_command(None, actor_context))
    assert service.get_dataset(external.id).project_id is None


def test_register_dataset_requires_actor_and_existing_project(
    service_factory: Callable[[], ApplicationService],
) -> None:
    service = service_factory()
    with pytest.raises(ResearchBaseError) as missing_actor:
        service.register_dataset(register_command(None, context()))
    assert missing_actor.value.code is ErrorCode.NOT_FOUND

    _, _, actor_context = seed(service)
    with pytest.raises(ResearchBaseError) as missing_project:
        service.register_dataset(register_command(ProjectId(uuid4()), actor_context))
    assert missing_project.value.code is ErrorCode.NOT_FOUND


def test_snapshot_create_get_and_locator_independent_idempotency(
    service_factory: Callable[[], ApplicationService],
) -> None:
    service = service_factory()
    _, project_id, actor_context = seed(service)
    dataset = service.register_dataset(register_command(project_id, actor_context))

    first = service.create_dataset_snapshot(snapshot_command(DatasetId(dataset.id), actor_context))
    retry = service.create_dataset_snapshot(
        snapshot_command(
            DatasetId(dataset.id), actor_context, manifest_locator="file:///second/manifest.json"
        )
    )
    loaded = service.get_dataset_snapshot(first.id)

    assert retry.id == first.id
    assert retry.content_hash == first.content_hash
    assert loaded.manifest_locator == "file:///first/manifest.json"


def test_same_material_on_different_datasets_creates_distinct_snapshots(
    service_factory: Callable[[], ApplicationService],
) -> None:
    service = service_factory()
    _, project_id, actor_context = seed(service)
    first_dataset = service.register_dataset(register_command(project_id, actor_context))
    second_dataset = service.register_dataset(register_command(project_id, actor_context))
    first = service.create_dataset_snapshot(
        snapshot_command(DatasetId(first_dataset.id), actor_context)
    )
    second = service.create_dataset_snapshot(
        snapshot_command(DatasetId(second_dataset.id), actor_context)
    )

    assert first.id != second.id
    assert first.content_hash == second.content_hash


@pytest.mark.parametrize("manifest_hash", ["", " ", "g" * 64, object()])
def test_snapshot_rejects_invalid_manifest_hash(
    service_factory: Callable[[], ApplicationService], manifest_hash: object
) -> None:
    service = service_factory()
    _, project_id, actor_context = seed(service)
    dataset = service.register_dataset(register_command(project_id, actor_context))

    with pytest.raises(ResearchBaseError) as raised:
        service.create_dataset_snapshot(
            snapshot_command(DatasetId(dataset.id), actor_context, manifest_hash=manifest_hash)
        )
    assert raised.value.code is ErrorCode.VALIDATION_ERROR


def test_snapshot_rejects_unserializable_selection_definition(
    service_factory: Callable[[], ApplicationService],
) -> None:
    service = service_factory()
    _, project_id, actor_context = seed(service)
    dataset = service.register_dataset(register_command(project_id, actor_context))

    with pytest.raises(ResearchBaseError) as raised:
        service.create_dataset_snapshot(
            snapshot_command(DatasetId(dataset.id), actor_context, selection_definition=object())
        )
    assert raised.value.code is ErrorCode.VALIDATION_ERROR
    assert isinstance(raised.value.__cause__, TypeError | ValueError)


def test_snapshot_material_hash_differential_is_single_variable() -> None:
    baseline = {"manifest_hash": "a" * 64, "selection_definition": {"split": "train"}}
    manifest_variant = {**baseline, "manifest_hash": "b" * 64}
    selection_variant = {**baseline, "selection_definition": {"split": "test"}}

    baseline_hash = sha256_canonical_json(baseline)
    assert sha256_canonical_json(manifest_variant) != baseline_hash
    assert sha256_canonical_json(selection_variant) != baseline_hash


def test_snapshot_immutability_trigger_rejects_direct_update(
    service_factory: Callable[[], ApplicationService],
) -> None:
    service = service_factory()
    _, project_id, actor_context = seed(service)
    dataset = service.register_dataset(register_command(project_id, actor_context))
    snapshot = service.create_dataset_snapshot(
        snapshot_command(DatasetId(dataset.id), actor_context)
    )
    engine = create_database_engine()
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            with pytest.raises(IntegrityError):
                connection.execute(
                    text(
                        "UPDATE dataset_snapshots SET manifest_locator = "
                        "'file:///changed' WHERE id = :id"
                    ),
                    {"id": snapshot.id},
                )
            transaction.rollback()
    finally:
        engine.dispose()


def test_snapshot_late_failure_rolls_back_and_retry_is_single_row(
    service_factory: Callable[[], ApplicationService],
) -> None:
    service = service_factory()
    _, project_id, actor_context = seed(service)
    dataset = service.register_dataset(register_command(project_id, actor_context))
    engine = create_database_engine()
    sessions = create_session_factory(engine)

    class FailingUnitOfWork(SqlAlchemyUnitOfWork):
        def commit(self) -> None:
            self._require_session().flush()
            raise RuntimeError("injected before commit")

    failing_service = ApplicationService(
        lambda: FailingUnitOfWork(sessions), FixedClock(datetime(2026, 8, 27, 0, 0, tzinfo=UTC))
    )
    try:
        with pytest.raises(RuntimeError, match="injected"):
            failing_service.create_dataset_snapshot(
                snapshot_command(DatasetId(dataset.id), actor_context)
            )
        with engine.connect() as connection:
            count = connection.execute(
                text("SELECT count(*) FROM dataset_snapshots WHERE dataset_id = :dataset_id"),
                {"dataset_id": dataset.id},
            ).scalar_one()
        assert count == 0
    finally:
        engine.dispose()

    retried = service.create_dataset_snapshot(
        snapshot_command(DatasetId(dataset.id), actor_context)
    )
    assert retried.id


def test_concurrent_same_content_creation_is_idempotent(
    service_factory: Callable[[], ApplicationService],
) -> None:
    service = service_factory()
    _, project_id, actor_context = seed(service)
    dataset = service.register_dataset(register_command(project_id, actor_context))
    barrier = Barrier(2)
    engine = create_database_engine()
    sessions = create_session_factory(engine)

    class SynchronizedUnitOfWork(SqlAlchemyUnitOfWork):
        def commit(self) -> None:
            barrier.wait(timeout=10)
            super().commit()

    synchronized_service = ApplicationService(
        lambda: SynchronizedUnitOfWork(sessions),
        FixedClock(datetime(2026, 8, 27, 0, 0, tzinfo=UTC)),
    )
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(
                    synchronized_service.create_dataset_snapshot,
                    snapshot_command(DatasetId(dataset.id), actor_context),
                )
                for _ in range(2)
            ]
            results = [future.result(timeout=20) for future in futures]
        assert results[0].id == results[1].id
        with engine.connect() as connection:
            count = connection.execute(
                text("SELECT count(*) FROM dataset_snapshots WHERE dataset_id = :dataset_id"),
                {"dataset_id": dataset.id},
            ).scalar_one()
        assert count == 1
    finally:
        engine.dispose()
