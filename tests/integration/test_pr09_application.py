from __future__ import annotations

import os
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
from researchbase.domain.run import ArtifactInputRole, DatasetInputRole, RunStatus
from researchbase.foundation.artifact_store import ContentAddressedFilesystemArtifactStore
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.execution_context import ExecutionContext
from researchbase.foundation.time import FixedClock
from researchbase.persistence.database import create_database_engine, create_session_factory
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
                run.id, outcome, 1, "expected test outcome", started.row_version, actor_context
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

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = [executor.submit(start), executor.submit(start)]
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

    def finish(outcome: RunStatus) -> RunReadModel:
        return factory().finish_run(
            FinishRunCommand(run.id, outcome, 0, None, started.row_version, actor_context)
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = [
            executor.submit(finish, RunStatus.SUCCEEDED),
            executor.submit(finish, RunStatus.FAILED),
        ]
    outcomes = [future.exception() for future in results]
    assert sum(error is None for error in outcomes) == 1
    assert (
        sum(
            isinstance(error, ResearchBaseError) and error.code is ErrorCode.CONCURRENT_MODIFICATION
            for error in outcomes
        )
        == 1
    )


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
    run, snapshot, artifact, actor_context = prepared_run(service)
    sessions = create_session_factory(engine)

    class FailingUnitOfWork(SqlAlchemyUnitOfWork):
        def commit(self) -> None:
            self._require_session().flush()
            raise RuntimeError("injected PR-09 failure")

    failing = ApplicationService(
        lambda: FailingUnitOfWork(sessions),
        FixedClock(datetime(2026, 8, 28, 0, 0, tzinfo=UTC)),
    )
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
