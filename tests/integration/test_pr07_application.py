from __future__ import annotations

import hashlib
import os
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from researchbase.application.commands import (
    ApplicationService,
    CreateActorCommand,
    CreateArtifactCommand,
    CreateArtifactVersionCommand,
    CreateProjectCommand,
    FreezeArtifactVersionCommand,
    SetArtifactCurrentVersionCommand,
    UpdateArtifactVersionDraftCommand,
)
from researchbase.domain.artifact import ArtifactId, ArtifactVersionId
from researchbase.domain.identity import ActorType
from researchbase.domain.organization import ProjectId
from researchbase.foundation.artifact_store import (
    ArtifactStore,
    ContentAddressedFilesystemArtifactStore,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.execution_context import ExecutionContext
from researchbase.foundation.time import FixedClock
from researchbase.foundation.versioning import VersionStatus
from researchbase.persistence.database import create_database_engine, create_session_factory
from researchbase.persistence.uow import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.integration


class BarrierStore:
    def __init__(self, delegate: ArtifactStore, barrier: Barrier) -> None:
        self.delegate = delegate
        self.barrier = barrier

    def put_verified(self, data: bytes, expected_hash: str | None = None) -> str:
        result = self.delegate.put_verified(data, expected_hash)
        self.barrier.wait(timeout=10)
        return result

    def open(self, identity: str) -> bytes:
        return self.delegate.open(identity)

    def exists(self, identity: str) -> bool:
        return self.delegate.exists(identity)

    def verify(self, identity: str) -> bool:
        return self.delegate.verify(identity)


@pytest.fixture(scope="module")
def resources(
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[tuple[Callable[..., ApplicationService], Engine, ArtifactStore]]:
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL is not set; run against the real PostgreSQL service")
    engine = create_database_engine()
    sessions = create_session_factory(engine)
    store = ContentAddressedFilesystemArtifactStore(tmp_path_factory.mktemp("pr07-store"))
    clock = FixedClock(datetime(2026, 8, 27, 0, 0, tzinfo=UTC))
    try:
        yield (
            lambda custom_store=None: ApplicationService(
                lambda: SqlAlchemyUnitOfWork(sessions), clock, custom_store or store
            ),
            engine,
            store,
        )
    finally:
        engine.dispose()


def context(actor_id: UUID | None = None) -> ExecutionContext:
    return ExecutionContext(actor_id=actor_id or uuid4(), request_id=uuid4(), client_type="test")


def seed(service: ApplicationService) -> tuple[UUID, ProjectId, ExecutionContext]:
    actor = service.create_actor(
        CreateActorCommand(ActorType.HUMAN, f"ArtifactOwner-{uuid4()}", None, context())
    )
    actor_context = context(actor.id)
    project = service.create_project(
        CreateProjectCommand(f"ArtifactProject-{uuid4()}", None, actor_context)
    )
    return actor.id, project.id, actor_context


def artifact_command(
    project_id: ProjectId | None, actor_context: ExecutionContext, **overrides: object
) -> CreateArtifactCommand:
    values: dict[str, object] = {
        "project_id": project_id,
        "artifact_type": "text/plain",
        "name": f"Artifact-{uuid4()}",
        "description": "artifact description",
        "context": actor_context,
    }
    values.update(overrides)
    return CreateArtifactCommand(**values)  # type: ignore[arg-type]


def version_command(
    artifact_id: ArtifactId,
    actor_context: ExecutionContext,
    **overrides: object,
) -> CreateArtifactVersionCommand:
    values: dict[str, object] = {
        "artifact_id": artifact_id,
        "data": b"fixed PR-07 bytes",
        "content_hash": None,
        "locator": None,
        "media_type": "text/plain",
        "byte_size": None,
        "metadata": {"label": "initial"},
        "context": actor_context,
    }
    values.update(overrides)
    return CreateArtifactVersionCommand(**values)  # type: ignore[arg-type]


def test_create_get_artifact_supports_nullable_project_and_validates_ownership(
    resources: tuple[Callable[..., ApplicationService], Engine, ArtifactStore],
) -> None:
    factory, _, _ = resources
    service = factory()
    actor_id, project_id, actor_context = seed(service)
    created = service.create_artifact(artifact_command(project_id, actor_context))

    assert service.get_artifact(created.id) == created
    assert created.project_id == project_id
    assert created.created_by == actor_id
    assert service.create_artifact(artifact_command(None, actor_context)).project_id is None

    with pytest.raises(ResearchBaseError) as missing_project:
        service.create_artifact(artifact_command(ProjectId(uuid4()), actor_context))
    assert missing_project.value.code is ErrorCode.NOT_FOUND

    with pytest.raises(ResearchBaseError) as missing_actor:
        service.create_artifact(artifact_command(None, context()))
    assert missing_actor.value.code is ErrorCode.NOT_FOUND


def test_exact_bytes_sha256_is_black_box_proven_and_metadata_is_not_identity(
    resources: tuple[Callable[..., ApplicationService], Engine, ArtifactStore],
) -> None:
    factory, engine, store = resources
    service = factory()
    _, project_id, actor_context = seed(service)
    artifact = service.create_artifact(artifact_command(project_id, actor_context))
    payload = b"fixed PR-07 bytes"
    expected_hash = hashlib.sha256(payload).hexdigest()
    created = service.create_artifact_version(
        version_command(ArtifactId(artifact.id), actor_context, data=payload)
    )

    assert created.content_hash == expected_hash
    assert created.content_hash != hashlib.sha256(b"metadata").hexdigest()
    assert store.verify("sha256:" + expected_hash)
    assert store.open("sha256:" + expected_hash) == payload
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT content_hash FROM artifact_versions WHERE id = :id"),
            {"id": created.id},
        ).scalar_one() == expected_hash

    retry = service.create_artifact_version(
        version_command(
            ArtifactId(artifact.id),
            actor_context,
            locator="file:///different-locator",
            media_type="application/octet-stream",
            metadata={"label": "retry"},
        )
    )
    assert retry.id == created.id
    loaded = service.get_artifact_version(created.id)
    assert loaded.locator == created.locator
    assert loaded.metadata == created.metadata


def test_artifact_version_rejects_hash_and_size_mismatch_and_missing_store_object(
    resources: tuple[Callable[..., ApplicationService], Engine, ArtifactStore],
) -> None:
    factory, engine, _ = resources
    service = factory()
    _, project_id, actor_context = seed(service)
    artifact = service.create_artifact(artifact_command(project_id, actor_context))
    artifact_id = ArtifactId(artifact.id)

    with pytest.raises(ResearchBaseError) as wrong_hash:
        service.create_artifact_version(
            version_command(artifact_id, actor_context, content_hash="0" * 64)
        )
    assert wrong_hash.value.code is ErrorCode.VALIDATION_ERROR

    with pytest.raises(ResearchBaseError) as wrong_size:
        service.create_artifact_version(
            version_command(artifact_id, actor_context, data=b"payload", byte_size=99)
        )
    assert wrong_size.value.code is ErrorCode.VALIDATION_ERROR

    with pytest.raises(ResearchBaseError) as missing_store:
        service.create_artifact_version(
            version_command(
                artifact_id,
                actor_context,
                data=None,
                content_hash="a" * 64,
                locator="sha256:" + "a" * 64,
                byte_size=1,
            )
        )
    assert missing_store.value.code is ErrorCode.VALIDATION_ERROR
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT count(*) FROM artifact_versions WHERE artifact_id = :id"),
            {"id": artifact.id},
        ).scalar_one() == 0


def test_store_verification_precedes_database_registration(
    resources: tuple[Callable[..., ApplicationService], Engine, ArtifactStore],
) -> None:
    factory, engine, store = resources
    order: list[str] = []
    barrier = Barrier(1)

    class OrderedStore(BarrierStore):
        def put_verified(self, data: bytes, expected_hash: str | None = None) -> str:
            order.append("store")
            return super().put_verified(data, expected_hash)

    ordered_store = OrderedStore(store, barrier)
    service = factory(ordered_store)
    _, project_id, actor_context = seed(service)

    def observe_db(
        _conn: object,
        _cursor: object,
        statement: str,
        _parameters: object,
        _context: object,
        _executemany: bool,
    ) -> None:
        if "INSERT INTO artifact_versions" in statement:
            order.append("db")

    event.listen(engine, "before_cursor_execute", observe_db)
    try:
        artifact = service.create_artifact(artifact_command(project_id, actor_context))
        service.create_artifact_version(
            version_command(ArtifactId(artifact.id), actor_context, data=b"ordered bytes")
        )
    finally:
        event.remove(engine, "before_cursor_execute", observe_db)
    assert order.index("store") < order.index("db")


def test_create_freeze_history_current_pointer_and_draft_stale_writer(
    resources: tuple[Callable[..., ApplicationService], Engine, ArtifactStore],
) -> None:
    factory, _, _ = resources
    service = factory()
    _, project_id, actor_context = seed(service)
    artifact = service.create_artifact(artifact_command(project_id, actor_context))
    artifact_id = ArtifactId(artifact.id)
    first = service.create_artifact_version(version_command(artifact_id, actor_context))
    assert first.status is VersionStatus.DRAFT
    assert service.get_artifact(artifact.id).current_version_id == first.id

    updated = service.update_artifact_version_draft(
        UpdateArtifactVersionDraftCommand(
            artifact_id=artifact_id,
            version_id=ArtifactVersionId(first.id),
            locator="file:///draft-edit",
            media_type="text/plain",
            byte_size=len(b"fixed PR-07 bytes"),
            metadata={"label": "draft-edit"},
            expected_row_version=first.row_version,
            context=actor_context,
        )
    )
    assert updated.row_version == first.row_version + 1
    with pytest.raises(ResearchBaseError) as stale:
        service.update_artifact_version_draft(
            UpdateArtifactVersionDraftCommand(
                artifact_id=artifact_id,
                version_id=ArtifactVersionId(first.id),
                locator="file:///stale",
                media_type="text/plain",
                byte_size=len(b"fixed PR-07 bytes"),
                metadata={"label": "stale"},
                expected_row_version=first.row_version,
                context=actor_context,
            )
        )
    assert stale.value.code is ErrorCode.CONCURRENT_MODIFICATION

    frozen = service.freeze_artifact_version(
        FreezeArtifactVersionCommand(
            artifact_id=artifact_id,
            version_id=ArtifactVersionId(first.id),
            expected_row_version=updated.row_version,
            context=actor_context,
        )
    )
    assert frozen.status is VersionStatus.FROZEN
    assert frozen.content_hash == first.content_hash
    second = service.create_artifact_version(
        version_command(artifact_id, actor_context, data=b"second bytes")
    )
    history = service.get_artifact_history(artifact_id)
    assert [item.version_number for item in history] == [1, 2]
    assert history[0].status is VersionStatus.SUPERSEDED
    assert history[-1].id == second.id
    assert service.get_artifact(artifact.id).current_version_id == second.id


def test_invalid_metadata_is_a_stable_validation_error(
    resources: tuple[Callable[..., ApplicationService], Engine, ArtifactStore],
) -> None:
    factory, _, _ = resources
    service = factory()
    _, project_id, actor_context = seed(service)
    artifact = service.create_artifact(artifact_command(project_id, actor_context))

    with pytest.raises(ResearchBaseError) as raised:
        service.create_artifact_version(
            version_command(ArtifactId(artifact.id), actor_context, metadata=object())
        )
    assert raised.value.code is ErrorCode.VALIDATION_ERROR


def test_cross_parent_current_pointer_is_rejected_and_concurrent_duplicate_is_idempotent(
    resources: tuple[Callable[..., ApplicationService], Engine, ArtifactStore],
) -> None:
    factory, engine, store = resources
    service = factory()
    _, project_id, actor_context = seed(service)
    first_artifact = service.create_artifact(artifact_command(project_id, actor_context))
    second_artifact = service.create_artifact(artifact_command(project_id, actor_context))
    first_version = service.create_artifact_version(
        version_command(ArtifactId(first_artifact.id), actor_context, data=b"first-parent")
    )
    second_version = service.create_artifact_version(
        version_command(ArtifactId(second_artifact.id), actor_context, data=b"second-parent")
    )
    with pytest.raises(ResearchBaseError) as wrong_parent:
        service.set_artifact_current_version(
            SetArtifactCurrentVersionCommand(
                artifact_id=ArtifactId(first_artifact.id),
                version_id=ArtifactVersionId(second_version.id),
                expected_row_version=first_artifact.row_version + 1,
                context=actor_context,
            )
        )
    assert wrong_parent.value.code is ErrorCode.REFERENTIAL_INTEGRITY_ERROR
    assert service.get_artifact(first_artifact.id).current_version_id == first_version.id

    barrier = Barrier(2)
    concurrent_service = factory(BarrierStore(store, barrier))
    duplicate_artifact = service.create_artifact(artifact_command(project_id, actor_context))
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(
                concurrent_service.create_artifact_version,
                version_command(ArtifactId(duplicate_artifact.id), actor_context),
            )
            for _ in range(2)
        ]
        results = [future.result(timeout=20) for future in futures]
    assert results[0].id == results[1].id
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT count(*) FROM artifact_versions WHERE artifact_id = :id"),
            {"id": duplicate_artifact.id},
        ).scalar_one() == 1


def test_concurrent_distinct_content_gets_parent_local_version_numbers(
    resources: tuple[Callable[..., ApplicationService], Engine, ArtifactStore],
) -> None:
    factory, engine, store = resources
    service = factory()
    _, project_id, actor_context = seed(service)
    artifact = service.create_artifact(artifact_command(project_id, actor_context))
    service.create_artifact_version(
        version_command(ArtifactId(artifact.id), actor_context, data=b"base content")
    )
    concurrent_service = factory(BarrierStore(store, Barrier(2)))

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(
                concurrent_service.create_artifact_version,
                version_command(ArtifactId(artifact.id), actor_context, data=payload),
            )
            for payload in (b"distinct content one", b"distinct content two")
        ]
        results = [future.result(timeout=20) for future in futures]

    assert sorted(result.version_number for result in results) == [2, 3]
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT count(*) FROM artifact_versions WHERE artifact_id = :id"),
            {"id": artifact.id},
        ).scalar_one() == 3


def test_store_success_db_failure_rolls_back_but_keeps_verified_bytes(
    resources: tuple[Callable[..., ApplicationService], Engine, ArtifactStore],
) -> None:
    factory, engine, store = resources
    service = factory()
    _, project_id, actor_context = seed(service)
    artifact = service.create_artifact(artifact_command(project_id, actor_context))
    sessions = create_session_factory(engine)

    class FailingUnitOfWork(SqlAlchemyUnitOfWork):
        def commit(self) -> None:
            self._require_session().flush()
            raise RuntimeError("injected before commit")

    failing_service = ApplicationService(
        lambda: FailingUnitOfWork(sessions),
        FixedClock(datetime(2026, 8, 27, 0, 0, tzinfo=UTC)),
        store,
    )
    payload = b"store survives db rollback"
    expected_hash = hashlib.sha256(payload).hexdigest()
    with pytest.raises(RuntimeError, match="injected"):
        failing_service.create_artifact_version(
            version_command(ArtifactId(artifact.id), actor_context, data=payload)
        )
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT count(*) FROM artifact_versions WHERE artifact_id = :id"),
            {"id": artifact.id},
        ).scalar_one() == 0
    assert store.verify("sha256:" + expected_hash)
    retried = service.create_artifact_version(
        version_command(ArtifactId(artifact.id), actor_context, data=payload)
    )
    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT id FROM artifact_versions WHERE artifact_id = :id"),
            {"id": artifact.id},
        ).all()
    assert len(row) == 1
    assert row[0].id == retried.id


@pytest.mark.parametrize(
    ("column", "expression"),
    [
        ("artifact_id", "'aaaaaaaa-aaaa-7aaa-8aaa-aaaaaaaaaaaa'"),
        ("locator", "'file:///tampered'"),
        ("media_type", "'application/tampered'"),
        ("byte_size", "999"),
        ("content_hash", "repeat('e', 64)"),
        ("metadata", "jsonb_build_object('tampered', true)"),
        ("created_by", "'bbbbbbbb-bbbb-7bbb-8bbb-bbbbbbbbbbbb'"),
        ("created_at", "now()"),
        ("version_number", "99"),
    ],
)
def test_frozen_version_trigger_rejects_every_material_update(
    resources: tuple[Callable[..., ApplicationService], Engine, ArtifactStore],
    column: str,
    expression: str,
) -> None:
    factory, engine, _ = resources
    service = factory()
    _, project_id, actor_context = seed(service)
    artifact = service.create_artifact(artifact_command(project_id, actor_context))
    version = service.create_artifact_version(
        version_command(ArtifactId(artifact.id), actor_context)
    )
    frozen = service.freeze_artifact_version(
        FreezeArtifactVersionCommand(
            artifact_id=ArtifactId(artifact.id),
            version_id=ArtifactVersionId(version.id),
            expected_row_version=version.row_version,
            context=actor_context,
        )
    )
    statement = text(
        f"UPDATE artifact_versions SET {column} = {expression} WHERE id = :version_id"
    )
    try:
        with engine.connect() as connection:
            before = connection.execute(
                text(
                    "SELECT artifact_id, locator, media_type, byte_size, content_hash, metadata, "
                    "created_by, created_at, version_number FROM artifact_versions "
                    "WHERE id = :version_id"
                ),
                {"version_id": frozen.id},
            ).one()
        with engine.connect() as connection:
            transaction = connection.begin()
            with pytest.raises(IntegrityError):
                connection.execute(statement, {"version_id": frozen.id})
            transaction.rollback()
        with engine.connect() as connection:
            after = connection.execute(
                text(
                    "SELECT artifact_id, locator, media_type, byte_size, content_hash, metadata, "
                    "created_by, created_at, version_number FROM artifact_versions "
                    "WHERE id = :version_id"
                ),
                {"version_id": frozen.id},
            ).one()
        assert after == before
    finally:
        pass
