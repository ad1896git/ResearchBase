from __future__ import annotations

import os
import threading
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Event
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from tests.application_compat import LegacyApplicationService as ApplicationService

from researchbase.application.commands import (
    AttachRunArtifactInputCommand,
    AttachRunDatasetInputCommand,
    CreateActorCommand,
    CreateArtifactCommand,
    CreateArtifactVersionCommand,
    CreateDatasetSnapshotCommand,
    CreateExperimentSpecCommand,
    CreateProjectCommand,
    CreateRunCommand,
    FinishRunCommand,
    FreezeArtifactVersionCommand,
    FreezeExperimentSpecCommand,
    RegisterDatasetCommand,
    ReviseExperimentSpecCommand,
    StartRunCommand,
)
from researchbase.application.dto import (
    ArtifactVersionReadModel,
    DatasetSnapshotReadModel,
    RunArtifactInputReadModel,
    RunDatasetInputReadModel,
    RunReadModel,
)
from researchbase.domain.artifact import ArtifactId, ArtifactVersionId
from researchbase.domain.identity import ActorType
from researchbase.domain.organization import ProjectId
from researchbase.domain.run import ArtifactInputRole, DatasetInputRole, RunId, RunStatus
from researchbase.foundation.artifact_store import ContentAddressedFilesystemArtifactStore
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.execution_context import ExecutionContext
from researchbase.foundation.time import FixedClock
from researchbase.foundation.versioning import VersionStatus
from researchbase.persistence.database import create_database_engine, create_session_factory
from researchbase.persistence.repositories import SqlAlchemyRunRepository
from researchbase.persistence.uow import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def resources(
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[tuple[Callable[[], ApplicationService], Engine]]:
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL is not set; run against the real PostgreSQL service")
    engine = create_database_engine()
    sessions = create_session_factory(engine)
    store = ContentAddressedFilesystemArtifactStore(tmp_path_factory.mktemp("pr09r2-store"))
    clock = FixedClock(datetime(2026, 8, 28, 0, 0, tzinfo=UTC))
    try:
        yield (
            lambda: ApplicationService(lambda: SqlAlchemyUnitOfWork(sessions), clock, store),
            engine,
        )
    finally:
        engine.dispose()


def context(actor_id: UUID | None = None) -> ExecutionContext:
    return ExecutionContext(actor_id=actor_id or uuid4(), request_id=uuid4(), client_type="test")


def seed(service: ApplicationService) -> tuple[UUID, ProjectId, ExecutionContext]:
    actor = service.create_actor(
        CreateActorCommand(ActorType.HUMAN, f"PR09R2-owner-{uuid4()}", None, context())
    )
    actor_context = context(actor.id)
    project = service.create_project(
        CreateProjectCommand(f"PR09R2-project-{uuid4()}", None, actor_context)
    )
    return actor.id, project.id, actor_context


def frozen_spec(
    service: ApplicationService, project_id: ProjectId, actor_context: ExecutionContext
):
    spec = service.create_experiment_spec(
        CreateExperimentSpecCommand(
            project_id,
            None,
            "PR09R2 experiment",
            "PR09R2 objective",
            {"steps": ["execute"]},
            None,
            None,
            None,
            actor_context,
        )
    )
    assert spec.current_version_id is not None
    frozen = service.freeze_experiment_spec(
        FreezeExperimentSpecCommand(spec.id, spec.current_version_id, actor_context, 1)
    )
    return spec, frozen


def dataset_snapshot(
    service: ApplicationService,
    project_id: ProjectId,
    actor_context: ExecutionContext,
    *,
    manifest_hash: str = "a" * 64,
    selection_definition: object | None = None,
) -> DatasetSnapshotReadModel:
    dataset = service.register_dataset(
        RegisterDatasetCommand(project_id, f"PR09R2-dataset-{uuid4()}", None, None, actor_context)
    )
    return service.create_dataset_snapshot(
        CreateDatasetSnapshotCommand(
            dataset.id,
            manifest_hash,
            selection_definition or {"split": "test"},
            None,
            actor_context,
        )
    )


def artifact_version(
    service: ApplicationService, project_id: ProjectId, actor_context: ExecutionContext, data: bytes
) -> tuple[UUID, ArtifactVersionReadModel]:
    artifact = service.create_artifact(
        CreateArtifactCommand(
            project_id, "text/plain", f"PR09R2-artifact-{uuid4()}", None, actor_context
        )
    )
    version = service.create_artifact_version(
        CreateArtifactVersionCommand(
            ArtifactId(artifact.id), data, None, None, "text/plain", None, None, actor_context
        )
    )
    frozen = service.freeze_artifact_version(
        FreezeArtifactVersionCommand(
            ArtifactId(artifact.id),
            ArtifactVersionId(version.id),
            actor_context,
            version.row_version,
        )
    )
    return artifact.id, frozen


def prepared_run(
    service: ApplicationService,
) -> tuple[RunReadModel, DatasetSnapshotReadModel, ArtifactVersionReadModel, ExecutionContext]:
    _, project_id, actor_context = seed(service)
    _, frozen = frozen_spec(service, project_id, actor_context)
    snapshot = dataset_snapshot(service, project_id, actor_context)
    _, artifact = artifact_version(service, project_id, actor_context, b"PR09R2 artifact")
    run = service.create_run(CreateRunCommand(project_id, frozen.id, None, actor_context))
    return run, snapshot, artifact, actor_context


def full_run_state(
    service: ApplicationService, run_id: RunId
) -> tuple[
    RunReadModel,
    tuple[RunDatasetInputReadModel, ...],
    tuple[RunArtifactInputReadModel, ...],
]:
    reader = service
    return (
        reader.get_run(run_id),
        tuple(reader.list_run_dataset_inputs(run_id)),
        tuple(reader.list_run_artifact_inputs(run_id)),
    )


def fresh_scalar(engine: Engine, statement: str, parameters: dict[str, object]) -> Any:
    sessions = create_session_factory(engine)
    with SqlAlchemyUnitOfWork(sessions) as uow:
        return uow._require_session().execute(text(statement), parameters).scalar_one()


@dataclass(frozen=True)
class SqlProof:
    statement: str
    same_transaction_visible: bool


@contextmanager
def observe_target_sql(
    engine: Engine,
    fragment: str,
    visibility_statement: str,
    visibility_parameters: dict[str, object],
) -> Iterator[list[SqlProof]]:
    proofs: list[SqlProof] = []
    observing = threading.local()

    def after_cursor_execute(
        connection: Any,
        _cursor: Any,
        statement: str,
        _parameters: Any,
        _context: Any,
        _executemany: bool,
    ) -> None:
        if getattr(observing, "active", False):
            return
        normalized = " ".join(statement.lower().split())
        if fragment not in normalized:
            return
        observing.active = True
        try:
            visible = bool(
                connection.execute(text(visibility_statement), visibility_parameters).scalar_one()
            )
            proofs.append(SqlProof(statement, visible))
        finally:
            observing.active = False

    event.listen(engine, "after_cursor_execute", after_cursor_execute)
    try:
        yield proofs
    finally:
        event.remove(engine, "after_cursor_execute", after_cursor_execute)


class FailingUnitOfWork(SqlAlchemyUnitOfWork):
    def commit(self) -> None:
        self._require_session().flush()
        raise RuntimeError("injected PR-09R2 failure after target SQL")


def test_real_sql_atomicity_uses_same_transaction_visibility_and_complete_rollback(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, engine = resources
    service = factory()
    _, project_id, actor_context = seed(service)
    _, frozen_spec_version = frozen_spec(service, project_id, actor_context)
    sessions = create_session_factory(engine)
    clock = FixedClock(datetime(2026, 8, 28, 0, 0, tzinfo=UTC))
    failing = ApplicationService(lambda: FailingUnitOfWork(sessions), clock)

    with observe_target_sql(
        engine,
        "insert into runs",
        "SELECT count(*) FROM runs WHERE project_id=:project_id "
        "AND experiment_spec_version_id=:spec_id",
        {"project_id": project_id, "spec_id": frozen_spec_version.id},
    ) as create_proof:
        with pytest.raises(RuntimeError, match="after target SQL"):
            failing.create_run(
                CreateRunCommand(project_id, frozen_spec_version.id, None, actor_context)
            )
    assert len(create_proof) == 1
    assert create_proof[0].same_transaction_visible
    assert (
        fresh_scalar(
            engine,
            "SELECT count(*) FROM runs WHERE project_id=:project_id "
            "AND experiment_spec_version_id=:spec_id",
            {"project_id": project_id, "spec_id": frozen_spec_version.id},
        )
        == 0
    )
    retried = service.create_run(
        CreateRunCommand(project_id, frozen_spec_version.id, None, actor_context)
    )
    assert (
        fresh_scalar(
            engine,
            "SELECT count(*) FROM runs WHERE id=:run_id",
            {"run_id": retried.id},
        )
        == 1
    )

    run, snapshot, artifact, actor_context = prepared_run(service)
    before = full_run_state(factory(), run.id)
    with observe_target_sql(
        engine,
        "insert into run_dataset_inputs",
        "SELECT count(*) FROM run_dataset_inputs WHERE run_id=:run_id "
        "AND dataset_snapshot_id=:snapshot_id",
        {"run_id": run.id, "snapshot_id": snapshot.id},
    ) as dataset_proof:
        with pytest.raises(RuntimeError, match="after target SQL"):
            failing.attach_run_dataset_input(
                AttachRunDatasetInputCommand(
                    run.id, snapshot.id, DatasetInputRole.TEST, 0, run.row_version, actor_context
                )
            )
    assert len(dataset_proof) == 1
    assert dataset_proof[0].same_transaction_visible
    assert full_run_state(factory(), run.id) == before
    retried_dataset = service.attach_run_dataset_input(
        AttachRunDatasetInputCommand(
            run.id, snapshot.id, DatasetInputRole.TEST, 0, run.row_version, actor_context
        )
    )
    assert factory().list_run_dataset_inputs(run.id) == [
        RunDatasetInputReadModel(run.id, snapshot.id, DatasetInputRole.TEST, 0)
    ]

    before = full_run_state(factory(), run.id)
    with observe_target_sql(
        engine,
        "insert into run_artifact_inputs",
        "SELECT count(*) FROM run_artifact_inputs WHERE run_id=:run_id "
        "AND artifact_version_id=:artifact_id",
        {"run_id": run.id, "artifact_id": artifact.id},
    ) as artifact_proof:
        with pytest.raises(RuntimeError, match="after target SQL"):
            failing.attach_run_artifact_input(
                AttachRunArtifactInputCommand(
                    run.id,
                    artifact.id,
                    ArtifactInputRole.MODEL,
                    0,
                    retried_dataset.row_version,
                    actor_context,
                )
            )
    assert len(artifact_proof) == 1
    assert artifact_proof[0].same_transaction_visible
    assert full_run_state(factory(), run.id) == before
    retried_artifact = service.attach_run_artifact_input(
        AttachRunArtifactInputCommand(
            run.id,
            artifact.id,
            ArtifactInputRole.MODEL,
            0,
            retried_dataset.row_version,
            actor_context,
        )
    )
    assert factory().list_run_artifact_inputs(run.id) == [
        RunArtifactInputReadModel(run.id, artifact.id, ArtifactInputRole.MODEL, 0)
    ]

    before = full_run_state(factory(), run.id)
    with observe_target_sql(
        engine,
        "update runs",
        "SELECT status = 'RUNNING' AND inputs_sealed_at IS NOT NULL "
        "AND started_at IS NOT NULL FROM runs WHERE id=:run_id",
        {"run_id": run.id},
    ) as start_proof:
        with pytest.raises(RuntimeError, match="after target SQL"):
            failing.start_run(StartRunCommand(run.id, retried_artifact.row_version, actor_context))
    assert len(start_proof) == 1
    assert start_proof[0].same_transaction_visible
    assert full_run_state(factory(), run.id) == before
    started = service.start_run(
        StartRunCommand(run.id, retried_artifact.row_version, actor_context)
    )

    before = full_run_state(factory(), run.id)
    with observe_target_sql(
        engine,
        "update runs",
        "SELECT status = 'SUCCEEDED' AND finished_at IS NOT NULL "
        "AND exit_code = 0 FROM runs WHERE id=:run_id",
        {"run_id": run.id},
    ) as finish_proof:
        with pytest.raises(RuntimeError, match="after target SQL"):
            failing.finish_run(
                FinishRunCommand(
                    run.id, RunStatus.SUCCEEDED, 0, None, started.row_version, actor_context
                )
            )
    assert len(finish_proof) == 1
    assert finish_proof[0].same_transaction_visible
    assert full_run_state(factory(), run.id) == before
    finished = service.finish_run(
        FinishRunCommand(run.id, RunStatus.SUCCEEDED, 0, None, started.row_version, actor_context)
    )
    assert finished.status is RunStatus.SUCCEEDED


class ControlledCommitUnitOfWork(SqlAlchemyUnitOfWork):
    def __init__(
        self,
        session_factory: Callable[[], Session],
        flushed: Event,
        allow_commit: Event,
    ) -> None:
        super().__init__(session_factory)
        self._flushed = flushed
        self._allow_commit = allow_commit

    def commit(self) -> None:
        self._require_session().flush()
        self._flushed.set()
        if not self._allow_commit.wait(timeout=20):
            raise RuntimeError("serialization test did not release commit")
        super().commit()


def run_serialization_case(
    factory: Callable[[], ApplicationService],
    engine: Engine,
    run: RunReadModel,
    snapshot: DatasetSnapshotReadModel,
    actor_context: ExecutionContext,
    *,
    attach_first: bool,
) -> tuple[RunReadModel, list[RunDatasetInputReadModel], dict[str, int]]:
    sessions = create_session_factory(engine)
    clock = FixedClock(datetime(2026, 8, 28, 0, 0, tzinfo=UTC))
    attach_flushed = Event()
    start_flushed = Event()
    allow_attach = Event()
    allow_start = Event()
    active = {"attach": Event(), "start": Event()}
    locked = {"attach": Event(), "start": Event()}
    lock_attempted = {"attach": Event(), "start": Event()}
    lock_acquired = {"attach": Event(), "start": Event()}
    txids: dict[str, int] = {}
    role_local = threading.local()
    original = SqlAlchemyRunRepository.get_for_update
    txid_lock = threading.Lock()

    def is_run_lock(statement: str) -> bool:
        normalized = " ".join(statement.lower().split())
        return "from runs" in normalized and "for update" in normalized

    def before_cursor_execute(
        _connection: Any,
        _cursor: Any,
        statement: str,
        _parameters: Any,
        _context: Any,
        _executemany: bool,
    ) -> None:
        role = getattr(role_local, "role", None)
        if role in {"attach", "start"} and is_run_lock(statement):
            lock_attempted[role].set()

    def after_cursor_execute(
        _connection: Any,
        _cursor: Any,
        statement: str,
        _parameters: Any,
        _context: Any,
        _executemany: bool,
    ) -> None:
        role = getattr(role_local, "role", None)
        if role in {"attach", "start"} and is_run_lock(statement):
            lock_acquired[role].set()

    def synchronized(repository: SqlAlchemyRunRepository, run_id: Any) -> Any:
        role = getattr(role_local, "role", None)
        if role in {"attach", "start"}:
            txid = int(repository._session.execute(text("SELECT txid_current()")).scalar_one())
            with txid_lock:
                txids[role] = txid
            active[role].set()
        result = original(repository, run_id)
        if role in {"attach", "start"}:
            locked[role].set()
        return result

    attach_service = ApplicationService(
        lambda: ControlledCommitUnitOfWork(sessions, attach_flushed, allow_attach), clock
    )
    start_service = ApplicationService(
        lambda: ControlledCommitUnitOfWork(sessions, start_flushed, allow_start), clock
    )

    def attach_worker() -> RunReadModel:
        role_local.role = "attach"
        return attach_service.attach_run_dataset_input(
            AttachRunDatasetInputCommand(
                run.id, snapshot.id, DatasetInputRole.TEST, 0, run.row_version, actor_context
            )
        )

    def start_worker() -> RunReadModel:
        role_local.role = "start"
        try:
            return factory().start_run(StartRunCommand(run.id, run.row_version, actor_context))
        except ResearchBaseError as exc:
            if exc.code is not ErrorCode.CONCURRENT_MODIFICATION:
                raise
            role_local.role = "retry"
            refreshed = factory().get_run(run.id)
            return factory().start_run(
                StartRunCommand(run.id, refreshed.row_version, actor_context)
            )

    def controlled_start_worker() -> RunReadModel:
        role_local.role = "start"
        return start_service.start_run(StartRunCommand(run.id, run.row_version, actor_context))

    def assert_workers_active() -> None:
        assert active["attach"].is_set()
        assert active["start"].is_set()
        assert len(txids) == 2
        assert txids["attach"] != txids["start"]

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(SqlAlchemyRunRepository, "get_for_update", synchronized)
        event.listen(engine, "before_cursor_execute", before_cursor_execute)
        event.listen(engine, "after_cursor_execute", after_cursor_execute)
        try:
            with ThreadPoolExecutor(max_workers=2) as executor:
                if attach_first:
                    attach_future = executor.submit(attach_worker)
                    assert locked["attach"].wait(timeout=20)
                    assert lock_acquired["attach"].is_set()
                    assert attach_flushed.wait(timeout=20)
                    start_future = executor.submit(start_worker)
                    assert active["start"].wait(timeout=20)
                    assert lock_attempted["start"].is_set()
                    assert not lock_acquired["start"].is_set()
                    assert_workers_active()
                    allow_attach.set()
                    attached = attach_future.result(timeout=20)
                    started = start_future.result(timeout=20)
                    assert attached.row_version == run.row_version + 1
                    assert started.status is RunStatus.RUNNING
                else:
                    start_future = executor.submit(controlled_start_worker)
                    assert locked["start"].wait(timeout=20)
                    assert lock_acquired["start"].is_set()
                    assert start_flushed.wait(timeout=20)
                    attach_future = executor.submit(attach_worker)
                    assert active["attach"].wait(timeout=20)
                    assert lock_attempted["attach"].is_set()
                    assert not lock_acquired["attach"].is_set()
                    assert_workers_active()
                    allow_start.set()
                    started = start_future.result(timeout=20)
                    with pytest.raises(ResearchBaseError) as stale:
                        attach_future.result(timeout=20)
                    assert stale.value.code is ErrorCode.CONCURRENT_MODIFICATION
                    assert started.status is RunStatus.RUNNING
        finally:
            event.remove(engine, "before_cursor_execute", before_cursor_execute)
            event.remove(engine, "after_cursor_execute", after_cursor_execute)

    assert lock_acquired["attach"].is_set()
    assert lock_acquired["start"].is_set()

    final = factory().get_run(run.id)
    inputs = factory().list_run_dataset_inputs(run.id)
    return final, inputs, txids


def test_attach_first_serialization_commits_edge_before_start_and_retries_start(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, engine = resources
    service = factory()
    run, snapshot, _, actor_context = prepared_run(service)
    final, inputs, txids = run_serialization_case(
        factory, engine, run, snapshot, actor_context, attach_first=True
    )
    assert len(txids) == 2
    assert final.status is RunStatus.RUNNING
    assert final.inputs_sealed_at is not None
    assert len(inputs) == 1
    assert inputs[0].dataset_snapshot_id == snapshot.id
    assert final.row_version == run.row_version + 2


def test_start_first_serialization_rejects_late_attach_without_edge(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, engine = resources
    service = factory()
    run, snapshot, _, actor_context = prepared_run(service)
    final, inputs, txids = run_serialization_case(
        factory, engine, run, snapshot, actor_context, attach_first=False
    )
    assert len(txids) == 2
    assert final.status is RunStatus.RUNNING
    assert final.inputs_sealed_at is not None
    assert inputs == []
    assert final.row_version == run.row_version + 1


def test_exact_provenance_stays_on_frozen_versions_and_snapshots(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, _ = resources
    service = factory()
    _, project_id, actor_context = seed(service)
    spec, frozen_v1 = frozen_spec(service, project_id, actor_context)
    run = service.create_run(CreateRunCommand(project_id, frozen_v1.id, None, actor_context))

    identity_before = service.get_experiment_spec(spec.id)
    assert identity_before.row_version == 2
    revised = service.revise_experiment_spec(
        ReviseExperimentSpecCommand(
            spec.id,
            "PR09R2 experiment V2",
            "PR09R2 objective V2",
            {"steps": ["execute", "verify"]},
            None,
            None,
            None,
            identity_before.row_version,
            actor_context,
        )
    )
    assert revised.current_version_id != frozen_v1.id
    assert service.get_run(run.id).experiment_spec_version_id == frozen_v1.id

    artifact_identity, artifact_a1 = artifact_version(
        service, project_id, actor_context, b"PR09R2 artifact A1"
    )
    run = service.attach_run_artifact_input(
        AttachRunArtifactInputCommand(
            run.id, artifact_a1.id, ArtifactInputRole.MODEL, 0, run.row_version, actor_context
        )
    )
    artifact_a2 = service.create_artifact_version(
        CreateArtifactVersionCommand(
            ArtifactId(artifact_identity),
            b"PR09R2 artifact A2",
            None,
            None,
            "text/plain",
            None,
            None,
            actor_context,
        )
    )
    assert service.get_artifact(ArtifactId(artifact_identity)).current_version_id == artifact_a2.id
    assert service.list_run_artifact_inputs(run.id)[0].artifact_version_id == artifact_a1.id

    dataset = service.register_dataset(
        RegisterDatasetCommand(
            project_id, f"PR09R2 exact dataset-{uuid4()}", None, None, actor_context
        )
    )
    dataset_d1 = service.create_dataset_snapshot(
        CreateDatasetSnapshotCommand(dataset.id, "b" * 64, {"selection": "D1"}, None, actor_context)
    )
    run = service.attach_run_dataset_input(
        AttachRunDatasetInputCommand(
            run.id, dataset_d1.id, DatasetInputRole.TEST, 0, run.row_version, actor_context
        )
    )
    dataset_d2 = service.create_dataset_snapshot(
        CreateDatasetSnapshotCommand(dataset.id, "c" * 64, {"selection": "D2"}, None, actor_context)
    )
    assert dataset_d2.id != dataset_d1.id
    assert service.list_run_dataset_inputs(run.id)[0].dataset_snapshot_id == dataset_d1.id


def test_stale_dataset_attach_has_no_side_effects(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, _ = resources
    service = factory()
    run, snapshot, _, actor_context = prepared_run(service)
    first_reader = factory().get_run(run.id)
    stale_reader = factory().get_run(run.id)
    winner = factory().attach_run_dataset_input(
        AttachRunDatasetInputCommand(
            run.id, snapshot.id, DatasetInputRole.TEST, 0, first_reader.row_version, actor_context
        )
    )
    after_winner = full_run_state(factory(), run.id)
    with pytest.raises(ResearchBaseError) as stale:
        factory().attach_run_dataset_input(
            AttachRunDatasetInputCommand(
                run.id,
                snapshot.id,
                DatasetInputRole.VALIDATION,
                1,
                stale_reader.row_version,
                actor_context,
            )
        )
    assert stale.value.code is ErrorCode.CONCURRENT_MODIFICATION
    assert full_run_state(factory(), run.id) == after_winner
    assert winner.row_version == run.row_version + 1
    assert len(factory().list_run_dataset_inputs(run.id)) == 1


def test_stale_artifact_attach_has_no_side_effects(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, _ = resources
    service = factory()
    run, _, artifact, actor_context = prepared_run(service)
    first_reader = factory().get_run(run.id)
    stale_reader = factory().get_run(run.id)
    winner = factory().attach_run_artifact_input(
        AttachRunArtifactInputCommand(
            run.id, artifact.id, ArtifactInputRole.MODEL, 0, first_reader.row_version, actor_context
        )
    )
    after_winner = full_run_state(factory(), run.id)
    with pytest.raises(ResearchBaseError) as stale:
        factory().attach_run_artifact_input(
            AttachRunArtifactInputCommand(
                run.id,
                artifact.id,
                ArtifactInputRole.CHECKPOINT,
                1,
                stale_reader.row_version,
                actor_context,
            )
        )
    assert stale.value.code is ErrorCode.CONCURRENT_MODIFICATION
    assert full_run_state(factory(), run.id) == after_winner
    assert winner.row_version == run.row_version + 1
    assert len(factory().list_run_artifact_inputs(run.id)) == 1


def test_stale_start_has_no_side_effects(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, _ = resources
    service = factory()
    run, snapshot, artifact, actor_context = prepared_run(service)
    run = service.attach_run_dataset_input(
        AttachRunDatasetInputCommand(
            run.id, snapshot.id, DatasetInputRole.TEST, 0, run.row_version, actor_context
        )
    )
    run = service.attach_run_artifact_input(
        AttachRunArtifactInputCommand(
            run.id, artifact.id, ArtifactInputRole.MODEL, 0, run.row_version, actor_context
        )
    )
    first_reader = factory().get_run(run.id)
    stale_reader = factory().get_run(run.id)
    winner = factory().start_run(StartRunCommand(run.id, first_reader.row_version, actor_context))
    after_winner = full_run_state(factory(), run.id)
    with pytest.raises(ResearchBaseError) as stale:
        factory().start_run(StartRunCommand(run.id, stale_reader.row_version, actor_context))
    assert stale.value.code is ErrorCode.CONCURRENT_MODIFICATION
    assert full_run_state(factory(), run.id) == after_winner
    assert winner.status is RunStatus.RUNNING
    assert winner.row_version == run.row_version + 1


def test_stale_finish_has_no_side_effects(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, _ = resources
    service = factory()
    run, snapshot, artifact, actor_context = prepared_run(service)
    run = service.attach_run_dataset_input(
        AttachRunDatasetInputCommand(
            run.id, snapshot.id, DatasetInputRole.TEST, 0, run.row_version, actor_context
        )
    )
    run = service.attach_run_artifact_input(
        AttachRunArtifactInputCommand(
            run.id, artifact.id, ArtifactInputRole.MODEL, 0, run.row_version, actor_context
        )
    )
    started = service.start_run(StartRunCommand(run.id, run.row_version, actor_context))
    first_reader = factory().get_run(run.id)
    stale_reader = factory().get_run(run.id)
    winner = factory().finish_run(
        FinishRunCommand(
            run.id, RunStatus.SUCCEEDED, 0, None, first_reader.row_version, actor_context
        )
    )
    after_winner = full_run_state(factory(), run.id)
    with pytest.raises(ResearchBaseError) as stale:
        factory().finish_run(
            FinishRunCommand(
                run.id, RunStatus.FAILED, 1, "stale", stale_reader.row_version, actor_context
            )
        )
    assert stale.value.code is ErrorCode.CONCURRENT_MODIFICATION
    assert full_run_state(factory(), run.id) == after_winner
    assert started.status is RunStatus.RUNNING
    assert winner.status is RunStatus.SUCCEEDED
    assert winner.row_version == started.row_version + 1


def test_finalized_superseded_exact_refs_remain_closure_valid_and_startable(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, _ = resources
    service = factory()
    _, project_id, actor_context = seed(service)
    spec, spec_v1 = frozen_spec(service, project_id, actor_context)
    artifact_id, artifact_a1 = artifact_version(
        service, project_id, actor_context, b"PR09R3 artifact A1"
    )
    dataset = service.register_dataset(
        RegisterDatasetCommand(project_id, f"PR09R3 dataset-{uuid4()}", None, None, actor_context)
    )
    dataset_d1 = service.create_dataset_snapshot(
        CreateDatasetSnapshotCommand(dataset.id, "b" * 64, {"selection": "D1"}, None, actor_context)
    )
    run = service.create_run(CreateRunCommand(project_id, spec_v1.id, None, actor_context))
    run = service.attach_run_dataset_input(
        AttachRunDatasetInputCommand(
            run.id, dataset_d1.id, DatasetInputRole.TEST, 0, run.row_version, actor_context
        )
    )
    run = service.attach_run_artifact_input(
        AttachRunArtifactInputCommand(
            run.id, artifact_a1.id, ArtifactInputRole.MODEL, 0, run.row_version, actor_context
        )
    )

    spec_v2 = service.revise_experiment_spec(
        ReviseExperimentSpecCommand(
            spec.id,
            "PR09R3 experiment V2",
            "PR09R3 objective V2",
            {"steps": ["execute", "verify"]},
            None,
            None,
            None,
            service.get_experiment_spec(spec.id).row_version,
            actor_context,
        )
    )
    artifact_a2 = service.create_artifact_version(
        CreateArtifactVersionCommand(
            ArtifactId(artifact_id),
            b"PR09R3 artifact A2",
            None,
            None,
            "text/plain",
            None,
            None,
            actor_context,
        )
    )
    service.freeze_artifact_version(
        FreezeArtifactVersionCommand(
            ArtifactId(artifact_id),
            ArtifactVersionId(artifact_a2.id),
            actor_context,
            artifact_a2.row_version,
        )
    )
    dataset_d2 = service.create_dataset_snapshot(
        CreateDatasetSnapshotCommand(dataset.id, "c" * 64, {"selection": "D2"}, None, actor_context)
    )

    assert spec_v2.current_version_id != spec_v1.id
    assert dataset_d2.id != dataset_d1.id
    assert service.get_run(run.id).experiment_spec_version_id == spec_v1.id
    assert service.list_run_artifact_inputs(run.id)[0].artifact_version_id == artifact_a1.id
    assert service.list_run_dataset_inputs(run.id)[0].dataset_snapshot_id == dataset_d1.id

    planned_report = service.validate_run_closure(run.id)
    assert planned_report.complete
    started = service.start_run(StartRunCommand(run.id, run.row_version, actor_context))
    assert service.validate_run_closure(run.id).complete
    finished = service.finish_run(
        FinishRunCommand(run.id, RunStatus.SUCCEEDED, 0, None, started.row_version, actor_context)
    )
    assert finished.status is RunStatus.SUCCEEDED
    assert service.validate_run_closure(run.id).complete


def test_superseded_versions_remain_ineligible_for_new_authoring(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, _ = resources
    service = factory()
    _, project_id, actor_context = seed(service)
    spec, spec_v1 = frozen_spec(service, project_id, actor_context)
    revised_spec = service.revise_experiment_spec(
        ReviseExperimentSpecCommand(
            spec.id,
            "PR09R3 revised",
            "PR09R3 objective",
            {"steps": ["revised"]},
            None,
            None,
            None,
            service.get_experiment_spec(spec.id).row_version,
            actor_context,
        )
    )
    with pytest.raises(ResearchBaseError) as create_error:
        service.create_run(CreateRunCommand(project_id, spec_v1.id, None, actor_context))
    assert create_error.value.code is ErrorCode.VERSION_NOT_FROZEN
    assert revised_spec.current_version_id != spec_v1.id

    artifact_id, artifact_a1 = artifact_version(
        service, project_id, actor_context, b"PR09R3 authoring A1"
    )
    _, second_spec = frozen_spec(service, project_id, actor_context)
    run = service.create_run(CreateRunCommand(project_id, second_spec.id, None, actor_context))
    artifact_a2 = service.create_artifact_version(
        CreateArtifactVersionCommand(
            ArtifactId(artifact_id),
            b"PR09R3 authoring A2",
            None,
            None,
            "text/plain",
            None,
            None,
            actor_context,
        )
    )
    assert artifact_a2.status is VersionStatus.DRAFT
    with pytest.raises(ResearchBaseError) as attach_error:
        service.attach_run_artifact_input(
            AttachRunArtifactInputCommand(
                run.id, artifact_a1.id, ArtifactInputRole.MODEL, 0, run.row_version, actor_context
            )
        )
    assert attach_error.value.code is ErrorCode.VERSION_NOT_FROZEN


def test_abandoned_exact_refs_remain_closure_invalid(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, engine = resources
    service = factory()
    _, project_id, actor_context = seed(service)
    _, spec_v1 = frozen_spec(service, project_id, actor_context)
    artifact_id, artifact_a1 = artifact_version(
        service, project_id, actor_context, b"PR09R3 abandoned"
    )
    run = service.create_run(CreateRunCommand(project_id, spec_v1.id, None, actor_context))
    run = service.attach_run_artifact_input(
        AttachRunArtifactInputCommand(
            run.id, artifact_a1.id, ArtifactInputRole.MODEL, 0, run.row_version, actor_context
        )
    )
    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE experiment_spec_versions "
                "DISABLE TRIGGER pr17d_experiment_spec_version_update"
            )
        )
        try:
            connection.execute(
                text(
                    "UPDATE experiment_spec_versions SET status='ABANDONED', "
                    "content_hash=NULL, frozen_at=NULL, "
                    "row_version=row_version + 1 WHERE id=:id"
                ),
                {"id": spec_v1.id},
            )
        finally:
            connection.execute(
                text(
                    "ALTER TABLE experiment_spec_versions "
                    "ENABLE TRIGGER pr17d_experiment_spec_version_update"
                )
            )
    with engine.begin() as connection:
        connection.execute(
            text("ALTER TABLE artifact_versions DISABLE TRIGGER artifact_versions_frozen_immutable")
        )
        connection.execute(
            text("ALTER TABLE artifact_versions DISABLE TRIGGER pr17d_artifact_version_update")
        )
        try:
            connection.execute(
                text(
                    "UPDATE artifact_versions SET status='ABANDONED', "
                    "row_version=row_version + 1 WHERE id=:id"
                ),
                {"id": artifact_a1.id},
            )
        finally:
            connection.execute(
                text("ALTER TABLE artifact_versions ENABLE TRIGGER pr17d_artifact_version_update")
            )
            connection.execute(
                text(
                    "ALTER TABLE artifact_versions "
                    "ENABLE TRIGGER artifact_versions_frozen_immutable"
                )
            )
    report = service.validate_run_closure(run.id)
    assert not report.complete
    assert [violation.object_type for violation in report.violations] == [
        "ArtifactVersion",
        "ExperimentSpecVersion",
    ]
