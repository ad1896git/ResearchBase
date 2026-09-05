from __future__ import annotations

import os
import threading
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError

from researchbase.application.commands import (
    ApplicationService,
    AttachRunArtifactInputCommand,
    AttachRunDatasetInputCommand,
    CancelRunCommand,
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
    StartRunCommand,
)
from researchbase.application.dto import (
    ArtifactVersionReadModel,
    DatasetSnapshotReadModel,
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
    store = ContentAddressedFilesystemArtifactStore(tmp_path_factory.mktemp("pr09-store"))
    clock = FixedClock(datetime(2026, 8, 28, 0, 0, tzinfo=UTC))
    try:
        yield (
            lambda: ApplicationService(lambda: SqlAlchemyUnitOfWork(sessions), clock, store),
            engine,
        )
    finally:
        engine.dispose()


def context(actor_id: UUID) -> ExecutionContext:
    return ExecutionContext(actor_id=actor_id, request_id=uuid4(), client_type="test")


def synchronize_run_lock(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    original = SqlAlchemyRunRepository.get_for_update
    barrier = threading.Barrier(2)
    reached = [0]
    reached_lock = threading.Lock()
    state = threading.local()

    def synchronized(repository: SqlAlchemyRunRepository, run_id: RunId):
        if not getattr(state, "passed", False):
            with reached_lock:
                reached[0] += 1
            barrier.wait(timeout=10)
            state.passed = True
        return original(repository, run_id)

    monkeypatch.setattr(SqlAlchemyRunRepository, "get_for_update", synchronized)
    return reached


def seed(service: ApplicationService) -> tuple[UUID, ProjectId, ExecutionContext]:
    actor = service.create_actor(
        CreateActorCommand(ActorType.HUMAN, f"RunOwner-{uuid4()}", None, context(uuid4()))
    )
    actor_context = context(actor.id)
    project = service.create_project(
        CreateProjectCommand(f"RunProject-{uuid4()}", None, actor_context)
    )
    return actor.id, project.id, actor_context


def frozen_spec(
    service: ApplicationService, project_id: ProjectId, actor_context: ExecutionContext
):
    spec = service.create_experiment_spec(
        CreateExperimentSpecCommand(
            project_id,
            None,
            "Run experiment",
            "Run objective",
            {"steps": ["execute"]},
            None,
            None,
            None,
            actor_context,
        )
    )
    assert spec.current_version_id is not None
    service.freeze_experiment_spec(
        FreezeExperimentSpecCommand(spec.id, spec.current_version_id, actor_context, 1)
    )
    return spec.current_version_id


def frozen_dataset(
    service: ApplicationService, project_id: ProjectId, actor_context: ExecutionContext
):
    dataset = service.register_dataset(
        RegisterDatasetCommand(project_id, f"Dataset-{uuid4()}", None, None, actor_context)
    )
    return service.create_dataset_snapshot(
        CreateDatasetSnapshotCommand(dataset.id, "a" * 64, {"split": "test"}, None, actor_context)
    )


def frozen_artifact(
    service: ApplicationService, project_id: ProjectId, actor_context: ExecutionContext
):
    artifact = service.create_artifact(
        CreateArtifactCommand(project_id, "text/plain", f"Artifact-{uuid4()}", None, actor_context)
    )
    version = service.create_artifact_version(
        CreateArtifactVersionCommand(
            ArtifactId(artifact.id),
            b"run input",
            None,
            None,
            "text/plain",
            None,
            None,
            actor_context,
        )
    )
    return service.freeze_artifact_version(
        FreezeArtifactVersionCommand(
            ArtifactId(artifact.id),
            ArtifactVersionId(version.id),
            actor_context,
            version.row_version,
        )
    )


def prepared_run(
    service: ApplicationService,
) -> tuple[RunReadModel, DatasetSnapshotReadModel, ArtifactVersionReadModel, ExecutionContext]:
    _, project_id, actor_context = seed(service)
    spec_version_id = frozen_spec(service, project_id, actor_context)
    snapshot = frozen_dataset(service, project_id, actor_context)
    artifact = frozen_artifact(service, project_id, actor_context)
    run = service.create_run(CreateRunCommand(project_id, spec_version_id, None, actor_context))
    return run, snapshot, artifact, actor_context


def test_run_create_attach_start_finish_and_exact_inputs(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, engine = resources
    service = factory()
    _, project_id, actor_context = seed(service)
    spec_version_id = frozen_spec(service, project_id, actor_context)
    snapshot = frozen_dataset(service, project_id, actor_context)
    artifact = frozen_artifact(service, project_id, actor_context)
    run = service.create_run(CreateRunCommand(project_id, spec_version_id, None, actor_context))
    assert run.status is RunStatus.PLANNED
    assert run.inputs_sealed_at is None
    dataset_input = service.attach_run_dataset_input(
        AttachRunDatasetInputCommand(
            run.id, snapshot.id, DatasetInputRole.TEST, 0, run.row_version, actor_context
        )
    )
    artifact_input = service.attach_run_artifact_input(
        AttachRunArtifactInputCommand(
            run.id,
            artifact.id,
            ArtifactInputRole.MODEL,
            0,
            dataset_input.row_version,
            actor_context,
        )
    )
    started = service.start_run(StartRunCommand(run.id, artifact_input.row_version, actor_context))
    assert started.status is RunStatus.RUNNING
    assert started.inputs_sealed_at is not None
    assert started.started_at is not None
    finished = service.finish_run(
        FinishRunCommand(
            run.id, RunStatus.SUCCEEDED, None, None, started.row_version, actor_context
        )
    )
    assert finished.status is RunStatus.SUCCEEDED
    assert finished.finished_at is not None
    with pytest.raises(ResearchBaseError) as sealed:
        service.attach_run_dataset_input(
            AttachRunDatasetInputCommand(
                run.id,
                snapshot.id,
                DatasetInputRole.AUXILIARY,
                1,
                finished.row_version,
                actor_context,
            )
        )
    assert sealed.value.code is ErrorCode.IMMUTABLE_RECORD
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT experiment_spec_version_id FROM runs WHERE id=:id"), {"id": run.id}
            ).scalar_one()
            == spec_version_id
        )


def test_planned_run_can_be_cancelled_without_adapter_surface(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, _ = resources
    service = factory()
    run, _snapshot, _artifact, actor_context = prepared_run(service)

    cancelled = service.cancel_run(CancelRunCommand(run.id, run.row_version, actor_context))

    assert cancelled.status is RunStatus.CANCELLED
    assert cancelled.inputs_sealed_at is not None
    assert cancelled.finished_at is not None
    assert cancelled.started_at is None


def test_run_rejects_unfrozen_spec_and_draft_artifact(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, _ = resources
    service = factory()
    _, project_id, actor_context = seed(service)
    spec = service.create_experiment_spec(
        CreateExperimentSpecCommand(
            project_id,
            None,
            "Draft spec",
            "Objective",
            {"step": 1},
            None,
            None,
            None,
            actor_context,
        )
    )
    assert spec.current_version_id is not None
    with pytest.raises(ResearchBaseError) as error:
        service.create_run(
            CreateRunCommand(project_id, spec.current_version_id, "experiment", actor_context)
        )
    assert error.value.code is ErrorCode.VERSION_NOT_FROZEN


def test_run_duplicate_and_stale_mutations_are_stable(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, _ = resources
    service = factory()
    run, snapshot, artifact, actor_context = prepared_run(service)
    attached = service.attach_run_dataset_input(
        AttachRunDatasetInputCommand(
            run.id, snapshot.id, DatasetInputRole.TEST, 0, run.row_version, actor_context
        )
    )
    with pytest.raises(ResearchBaseError) as duplicate:
        service.attach_run_dataset_input(
            AttachRunDatasetInputCommand(
                run.id,
                snapshot.id,
                DatasetInputRole.TEST,
                0,
                attached.row_version,
                actor_context,
            )
        )
    assert duplicate.value.code is ErrorCode.VALIDATION_ERROR
    with pytest.raises(ResearchBaseError) as stale:
        service.attach_run_artifact_input(
            AttachRunArtifactInputCommand(
                run.id,
                artifact.id,
                ArtifactInputRole.MODEL,
                0,
                run.row_version,
                actor_context,
            )
        )
    assert stale.value.code is ErrorCode.CONCURRENT_MODIFICATION


def test_run_terminal_outcomes_and_closure_are_deterministic(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, _ = resources
    for outcome in (RunStatus.FAILED, RunStatus.CANCELLED):
        service = factory()
        run, snapshot, artifact, actor_context = prepared_run(service)
        current = service.attach_run_dataset_input(
            AttachRunDatasetInputCommand(
                run.id, snapshot.id, DatasetInputRole.TEST, 0, run.row_version, actor_context
            )
        )
        current = service.attach_run_artifact_input(
            AttachRunArtifactInputCommand(
                run.id,
                artifact.id,
                ArtifactInputRole.MODEL,
                0,
                current.row_version,
                actor_context,
            )
        )
        report = service.validate_run_closure(run.id)
        assert report.complete is True
        assert report.visited_count == 4
        assert report.violations == []
        started = service.start_run(StartRunCommand(run.id, current.row_version, actor_context))
        finished = service.finish_run(
            FinishRunCommand(
                run.id,
                outcome,
                1 if outcome is RunStatus.FAILED else None,
                "expected test outcome" if outcome is RunStatus.FAILED else None,
                started.row_version,
                actor_context,
            )
        )
        assert finished.status is outcome
        with pytest.raises(ResearchBaseError) as terminal:
            service.finish_run(
                FinishRunCommand(
                    run.id, RunStatus.SUCCEEDED, 0, None, finished.row_version, actor_context
                )
            )
        assert terminal.value.code is ErrorCode.INVALID_STATE_TRANSITION


def test_concurrent_start_and_finish_use_row_version(
    resources: tuple[Callable[[], ApplicationService], Engine],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory, _ = resources
    service = factory()
    run, snapshot, artifact, actor_context = prepared_run(service)
    current = service.attach_run_dataset_input(
        AttachRunDatasetInputCommand(
            run.id, snapshot.id, DatasetInputRole.TEST, 0, run.row_version, actor_context
        )
    )
    current = service.attach_run_artifact_input(
        AttachRunArtifactInputCommand(
            run.id, artifact.id, ArtifactInputRole.MODEL, 0, current.row_version, actor_context
        )
    )

    def start() -> RunReadModel:
        return factory().start_run(StartRunCommand(run.id, current.row_version, actor_context))

    with monkeypatch.context() as patch:
        reached = synchronize_run_lock(patch)
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = [executor.submit(start), executor.submit(start)]
    assert reached == [2]
    outcomes = [future.exception() for future in results]
    assert sum(error is None for error in outcomes) == 1
    assert (
        sum(
            isinstance(error, ResearchBaseError) and error.code is ErrorCode.CONCURRENT_MODIFICATION
            for error in outcomes
        )
        == 1
    )
    started = service.get_run(run.id)
    assert started.status is RunStatus.RUNNING
    assert started.inputs_sealed_at is not None
    assert started.row_version == current.row_version + 1

    finish_commands = [
        (RunStatus.SUCCEEDED, 0, "writer-a-success"),
        (RunStatus.FAILED, 73, "writer-b-failure"),
    ]

    def finish(outcome: RunStatus, exit_code: int, failure_reason: str) -> RunReadModel:
        return factory().finish_run(
            FinishRunCommand(
                run.id, outcome, exit_code, failure_reason, started.row_version, actor_context
            )
        )

    with monkeypatch.context() as patch:
        reached = synchronize_run_lock(patch)
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = [executor.submit(finish, *command) for command in finish_commands]
    assert reached == [2]
    outcomes = [future.exception() for future in results]
    assert sum(error is None for error in outcomes) == 1
    assert (
        sum(
            isinstance(error, ResearchBaseError) and error.code is ErrorCode.CONCURRENT_MODIFICATION
            for error in outcomes
        )
        == 1
    )
    winner_index = next(index for index, future in enumerate(results) if future.exception() is None)
    winner_status, winner_exit_code, winner_failure_reason = finish_commands[winner_index]
    finished = service.get_run(run.id)
    assert finished.status is winner_status
    assert finished.finished_at is not None
    assert finished.exit_code == winner_exit_code
    assert finished.failure_reason == winner_failure_reason
    assert finished.row_version == started.row_version + 1


def test_attach_vs_start_has_genuine_deterministic_overlap(
    resources: tuple[Callable[[], ApplicationService], Engine],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory, _ = resources
    service = factory()
    run, snapshot, _, actor_context = prepared_run(service)

    def start() -> RunReadModel:
        return factory().start_run(StartRunCommand(run.id, run.row_version, actor_context))

    def attach() -> RunReadModel:
        return factory().attach_run_dataset_input(
            AttachRunDatasetInputCommand(
                run.id, snapshot.id, DatasetInputRole.TEST, 0, run.row_version, actor_context
            )
        )

    with monkeypatch.context() as patch:
        reached = synchronize_run_lock(patch)
        with ThreadPoolExecutor(max_workers=2) as executor:
            start_future = executor.submit(start)
            attach_future = executor.submit(attach)
    assert reached == [2]
    start_error = start_future.exception()
    attach_error = attach_future.exception()
    if attach_error is None:
        assert service.list_run_dataset_inputs(run.id)[0].dataset_snapshot_id == snapshot.id
        assert isinstance(start_error, ResearchBaseError)
        assert start_error.code is ErrorCode.CONCURRENT_MODIFICATION
        refreshed = factory().get_run(run.id)
        service.start_run(StartRunCommand(run.id, refreshed.row_version, actor_context))
    else:
        assert isinstance(attach_error, ResearchBaseError)
        assert attach_error.code is ErrorCode.CONCURRENT_MODIFICATION
        assert start_error is None
        assert service.list_run_dataset_inputs(run.id) == []
    final = factory().get_run(run.id)
    assert final.status is RunStatus.RUNNING
    assert final.inputs_sealed_at is not None
    assert final.row_version in {2, 3}


def test_post_seal_trigger_and_fk_restrict_preserve_provenance(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, engine = resources
    service = factory()
    run, snapshot, artifact, actor_context = prepared_run(service)
    current = service.attach_run_dataset_input(
        AttachRunDatasetInputCommand(
            run.id, snapshot.id, DatasetInputRole.TEST, 0, run.row_version, actor_context
        )
    )
    current = service.attach_run_artifact_input(
        AttachRunArtifactInputCommand(
            run.id, artifact.id, ArtifactInputRole.MODEL, 0, current.row_version, actor_context
        )
    )
    service.start_run(StartRunCommand(run.id, current.row_version, actor_context))
    with pytest.raises(DBAPIError):
        with engine.begin() as connection:
            connection.execute(
                text("DELETE FROM run_dataset_inputs WHERE run_id=:run_id"),
                {"run_id": run.id},
            )
    with pytest.raises(DBAPIError):
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM runs WHERE id=:run_id"), {"run_id": run.id})
    assert service.get_run(run.id).status is RunStatus.RUNNING


def test_run_create_attach_start_finish_roll_back_after_flush(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, engine = resources
    service = factory()
    _, project_id, actor_context = seed(service)
    spec_version_id = frozen_spec(service, project_id, actor_context)
    sessions = create_session_factory(engine)
    observed_insert = False

    class FailingUnitOfWork(SqlAlchemyUnitOfWork):
        def commit(self) -> None:
            nonlocal observed_insert
            self._require_session().flush()
            observed_insert = True
            raise RuntimeError("injected PR-09 failure")

    failing = ApplicationService(
        lambda: FailingUnitOfWork(sessions),
        FixedClock(datetime(2026, 8, 28, 0, 0, tzinfo=UTC)),
    )
    with pytest.raises(RuntimeError, match="injected PR-09 failure"):
        failing.create_run(CreateRunCommand(project_id, spec_version_id, None, actor_context))
    assert observed_insert
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM runs WHERE project_id=:project_id"),
                {"project_id": project_id},
            ).scalar_one()
            == 0
        )
    retried = service.create_run(CreateRunCommand(project_id, spec_version_id, None, actor_context))
    assert retried.status is RunStatus.PLANNED

    run, snapshot, artifact, actor_context = prepared_run(service)
    with pytest.raises(RuntimeError, match="injected PR-09 failure"):
        failing.attach_run_dataset_input(
            AttachRunDatasetInputCommand(
                run.id, snapshot.id, DatasetInputRole.TEST, 0, run.row_version, actor_context
            )
        )
    assert factory().get_run(run.id).row_version == run.row_version
    assert factory().list_run_dataset_inputs(run.id) == []

    current = service.attach_run_dataset_input(
        AttachRunDatasetInputCommand(
            run.id, snapshot.id, DatasetInputRole.TEST, 0, run.row_version, actor_context
        )
    )
    with pytest.raises(RuntimeError, match="injected PR-09 failure"):
        failing.attach_run_artifact_input(
            AttachRunArtifactInputCommand(
                run.id, artifact.id, ArtifactInputRole.MODEL, 0, current.row_version, actor_context
            )
        )
    assert factory().get_run(run.id).row_version == current.row_version
    assert factory().list_run_artifact_inputs(run.id) == []
    current = service.attach_run_artifact_input(
        AttachRunArtifactInputCommand(
            run.id, artifact.id, ArtifactInputRole.MODEL, 0, current.row_version, actor_context
        )
    )
    with pytest.raises(RuntimeError, match="injected PR-09 failure"):
        failing.start_run(StartRunCommand(run.id, current.row_version, actor_context))
    rolled_back_start = factory().get_run(run.id)
    assert rolled_back_start.status is RunStatus.PLANNED
    assert rolled_back_start.inputs_sealed_at is None

    started = service.start_run(StartRunCommand(run.id, current.row_version, actor_context))
    with pytest.raises(RuntimeError, match="injected PR-09 failure"):
        failing.finish_run(
            FinishRunCommand(
                run.id, RunStatus.SUCCEEDED, 0, None, started.row_version, actor_context
            )
        )
    rolled_back_finish = factory().get_run(run.id)
    assert rolled_back_finish.status is RunStatus.RUNNING
    assert rolled_back_finish.finished_at is None


def test_sealed_input_trigger_blocks_all_retarget_and_mutation_attacks(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, engine = resources
    service = factory()
    _, project_id, actor_context = seed(service)
    spec_version_id = frozen_spec(service, project_id, actor_context)
    snapshot = frozen_dataset(service, project_id, actor_context)
    artifact = frozen_artifact(service, project_id, actor_context)

    def create_run() -> RunReadModel:
        return service.create_run(
            CreateRunCommand(project_id, spec_version_id, None, actor_context)
        )

    def add_inputs(
        run: RunReadModel, dataset_role: DatasetInputRole, artifact_role: ArtifactInputRole
    ) -> RunReadModel:
        run = service.attach_run_dataset_input(
            AttachRunDatasetInputCommand(
                run.id, snapshot.id, dataset_role, 0, run.row_version, actor_context
            )
        )
        return service.attach_run_artifact_input(
            AttachRunArtifactInputCommand(
                run.id, artifact.id, artifact_role, 0, run.row_version, actor_context
            )
        )

    sealed_a = add_inputs(create_run(), DatasetInputRole.TEST, ArtifactInputRole.MODEL)
    planned_b = create_run()
    planned_c = add_inputs(create_run(), DatasetInputRole.VALIDATION, ArtifactInputRole.SOURCE_CODE)
    sealed_d = add_inputs(create_run(), DatasetInputRole.CALIBRATION, ArtifactInputRole.CHECKPOINT)
    sealed_e = add_inputs(create_run(), DatasetInputRole.AUXILIARY, ArtifactInputRole.CONFIGURATION)
    sealed_f = add_inputs(create_run(), DatasetInputRole.OTHER, ArtifactInputRole.SCRIPT)
    for run in (sealed_a, sealed_d, sealed_e, sealed_f):
        service.start_run(StartRunCommand(run.id, run.row_version, actor_context))

    def reject(statement: str, parameters: dict[str, object]) -> None:
        with pytest.raises(DBAPIError):
            with engine.begin() as connection:
                connection.execute(text(statement), parameters)

    for table, id_column in (
        ("run_dataset_inputs", "dataset_snapshot_id"),
        ("run_artifact_inputs", "artifact_version_id"),
    ):
        reject(
            f"UPDATE {table} SET run_id=:new_id WHERE run_id=:old_id",
            {"new_id": planned_b.id, "old_id": sealed_a.id},
        )
        reject(
            f"UPDATE {table} SET run_id=:new_id WHERE run_id=:old_id",
            {"new_id": sealed_d.id, "old_id": planned_c.id},
        )
        reject(
            f"UPDATE {table} SET run_id=:new_id WHERE run_id=:old_id",
            {"new_id": sealed_f.id, "old_id": sealed_e.id},
        )
        reject(
            f"UPDATE {table} SET role='other' WHERE run_id=:run_id",
            {"run_id": sealed_a.id},
        )
        reject(
            f"UPDATE {table} SET ordinal=ordinal+1 WHERE run_id=:run_id",
            {"run_id": sealed_a.id},
        )
        reject(
            f"DELETE FROM {table} WHERE run_id=:run_id",
            {"run_id": sealed_a.id},
        )
        reject(
            f"INSERT INTO {table} (run_id, {id_column}, role, ordinal) "
            f"VALUES (:run_id, :object_id, 'other', 0)",
            {
                "run_id": sealed_a.id,
                "object_id": snapshot.id if table == "run_dataset_inputs" else artifact.id,
            },
        )

    assert service.get_run(sealed_a.id).status is RunStatus.RUNNING
    assert [item.role for item in service.list_run_dataset_inputs(sealed_a.id)] == [
        DatasetInputRole.TEST
    ]
    assert [item.role for item in service.list_run_artifact_inputs(sealed_a.id)] == [
        ArtifactInputRole.MODEL
    ]


def test_closure_dto_orders_multiple_violations_and_blocks_start(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, engine = resources
    service = factory()
    _, project_id, actor_context = seed(service)
    draft_spec = service.create_experiment_spec(
        CreateExperimentSpecCommand(
            project_id,
            None,
            "Draft closure spec",
            "Draft objective",
            {"step": "draft"},
            None,
            None,
            None,
            actor_context,
        )
    )
    assert draft_spec.current_version_id is not None
    dataset_snapshot = frozen_dataset(service, project_id, actor_context)
    artifact = service.create_artifact(
        CreateArtifactCommand(project_id, "text/plain", f"Draft-{uuid4()}", None, actor_context)
    )
    draft_artifact = service.create_artifact_version(
        CreateArtifactVersionCommand(
            ArtifactId(artifact.id),
            b"draft run input",
            None,
            None,
            "text/plain",
            None,
            None,
            actor_context,
        )
    )
    run_id = uuid4()
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO runs (id, project_id, experiment_spec_version_id, run_type, status, "
                "created_by, created_at, row_version) VALUES "
                "(:id, :project_id, :spec_id, 'experiment', 'PLANNED', :actor_id, :created_at, 1)"
            ),
            {
                "id": run_id,
                "project_id": project_id,
                "spec_id": draft_spec.current_version_id,
                "actor_id": actor_context.actor_id,
                "created_at": datetime(2026, 8, 28, 0, 0, tzinfo=UTC),
            },
        )
        connection.execute(
            text(
                "INSERT INTO run_dataset_inputs (run_id, dataset_snapshot_id, role, ordinal) "
                "VALUES (:run_id, :snapshot_id, 'test', 0)"
            ),
            {"run_id": run_id, "snapshot_id": dataset_snapshot.id},
        )
        connection.execute(
            text(
                "INSERT INTO run_artifact_inputs (run_id, artifact_version_id, role, ordinal) "
                "VALUES (:run_id, :artifact_id, 'model', 0)"
            ),
            {"run_id": run_id, "artifact_id": draft_artifact.id},
        )
    report = service.validate_run_closure(RunId(run_id))
    repeated = service.validate_run_closure(RunId(run_id))
    assert report == repeated
    assert report.complete is False
    assert report.visited_count == 4
    assert [violation.code for violation in report.violations] == [
        ErrorCode.VERSION_NOT_FROZEN.value,
        ErrorCode.VERSION_NOT_FROZEN.value,
    ]
    assert report.violations[0].object_type == "ArtifactVersion"
    assert report.violations[1].object_type == "ExperimentSpecVersion"
    for violation in report.violations:
        assert violation.code
        assert violation.object_type
        assert violation.object_id
        assert violation.path
        assert violation.message
    with pytest.raises(ResearchBaseError) as error:
        service.start_run(StartRunCommand(RunId(run_id), 1, actor_context))
    assert error.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    fresh = factory().get_run(RunId(run_id))
    assert fresh.status is RunStatus.PLANNED
    assert fresh.inputs_sealed_at is None
    assert fresh.started_at is None
    assert fresh.row_version == 1


def test_pr09_fk_restrict_matrix_rejects_all_referenced_deletes(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, engine = resources
    service = factory()
    actor_id, project_id, actor_context = seed(service)
    spec_version_id = frozen_spec(service, project_id, actor_context)
    snapshot = frozen_dataset(service, project_id, actor_context)
    artifact = frozen_artifact(service, project_id, actor_context)
    run = service.create_run(CreateRunCommand(project_id, spec_version_id, None, actor_context))
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
    service.start_run(StartRunCommand(run.id, run.row_version, actor_context))
    deletes = [
        ("projects", project_id),
        ("experiment_spec_versions", spec_version_id),
        ("actors", actor_id),
        ("dataset_snapshots", snapshot.id),
        ("artifact_versions", artifact.id),
        ("runs", run.id),
    ]
    for table, identifier in deletes:
        with pytest.raises(DBAPIError):
            with engine.begin() as connection:
                connection.execute(text(f"DELETE FROM {table} WHERE id=:id"), {"id": identifier})
    assert factory().get_run(run.id).status is RunStatus.RUNNING
    assert len(factory().list_run_dataset_inputs(run.id)) == 1
    assert len(factory().list_run_artifact_inputs(run.id)) == 1
