from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError

from researchbase.application.closure import ClosureReport, ProvenanceClosureValidator
from researchbase.application.commands import (
    ApplicationService,
    CreateActorCommand,
    CreateExperimentSpecCommand,
    CreateMetricDefinitionCommand,
    CreateProjectCommand,
    CreateRunCommand,
    FinishRunCommand,
    FreezeExperimentSpecCommand,
    FreezeMetricDefinitionCommand,
    RecordMeasurementCommand,
    ReviseMetricDefinitionCommand,
    StartRunCommand,
)
from researchbase.domain.identity import ActorType
from researchbase.domain.metric import MetricDefinitionVersionId
from researchbase.domain.organization import ProjectId
from researchbase.domain.run import RunId, RunStatus
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
    clock = FixedClock(datetime(2026, 8, 28, 0, 0, tzinfo=UTC))
    try:
        yield lambda: ApplicationService(lambda: SqlAlchemyUnitOfWork(sessions), clock), engine
    finally:
        engine.dispose()


def context(actor_id: UUID) -> ExecutionContext:
    return ExecutionContext(actor_id=actor_id, request_id=uuid4(), client_type="test")


def seed(service: ApplicationService) -> tuple[UUID, ProjectId, ExecutionContext]:
    actor = service.create_actor(
        CreateActorCommand(ActorType.HUMAN, f"MeasurementOwner-{uuid4()}", None, context(uuid4()))
    )
    actor_context = context(actor.id)
    project = service.create_project(
        CreateProjectCommand(f"MeasurementProject-{uuid4()}", None, actor_context)
    )
    return actor.id, project.id, actor_context


def frozen_metric(
    service: ApplicationService,
    project_id: ProjectId,
    actor_context: ExecutionContext,
    *,
    unit: str | None,
):
    metric = service.create_metric_definition(
        CreateMetricDefinitionCommand(
            project_id,
            f"Metric-{uuid4()}",
            {"kind": "mean"},
            unit,
            "mean",
            actor_context,
        )
    )
    assert metric.current_version_id is not None
    frozen = service.freeze_metric_definition(
        FreezeMetricDefinitionCommand(metric.id, metric.current_version_id, actor_context, 1)
    )
    return metric, frozen


def succeeded_run(
    service: ApplicationService, project_id: ProjectId, actor_context: ExecutionContext
):
    spec = service.create_experiment_spec(
        CreateExperimentSpecCommand(
            project_id,
            None,
            "Measurement experiment",
            "Measurement objective",
            {"steps": ["execute"]},
            None,
            None,
            None,
            actor_context,
        )
    )
    assert spec.current_version_id is not None
    frozen_spec = service.freeze_experiment_spec(
        FreezeExperimentSpecCommand(spec.id, spec.current_version_id, actor_context, 1)
    )
    run = service.create_run(CreateRunCommand(project_id, frozen_spec.id, None, actor_context))
    started = service.start_run(StartRunCommand(run.id, run.row_version, actor_context))
    return service.finish_run(
        FinishRunCommand(run.id, RunStatus.SUCCEEDED, 0, None, started.row_version, actor_context)
    )


def record(
    service: ApplicationService,
    run_id: RunId,
    metric_version_id: MetricDefinitionVersionId,
    actor_context: ExecutionContext,
    *,
    numeric_value: float | None = 1.25,
    structured_value: object | None = None,
    unit: str | None = "ms",
    evaluation_scope: object | None = None,
):
    return service.record_measurement(
        RecordMeasurementCommand(
            run_id,
            metric_version_id,
            numeric_value,
            structured_value,
            unit,
            evaluation_scope,
            actor_context,
        )
    )


def test_record_numeric_measurement_uses_exact_independent_hash(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, _ = resources
    service = factory()
    _, project_id, actor_context = seed(service)
    metric, version = frozen_metric(service, project_id, actor_context, unit="ms")
    run = succeeded_run(service, project_id, actor_context)

    measurement = record(
        service, run.id, version.id, actor_context, evaluation_scope={"split": "test"}
    )

    material = {
        "run_id": str(run.id),
        "metric_definition_version_id": str(version.id),
        "numeric_value": 1.25,
        "structured_value": None,
        "unit": "ms",
        "evaluation_scope": {"split": "test"},
    }
    assert measurement.metric_definition_version_id == version.id
    assert measurement.content_hash == sha256_canonical_json(material)
    assert measurement.id != metric.id
    assert factory().get_measurement(measurement.id) == measurement


def test_structured_measurements_and_duplicate_content_are_allowed(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, _ = resources
    service = factory()
    _, project_id, actor_context = seed(service)
    _, version = frozen_metric(service, project_id, actor_context, unit=None)
    run = succeeded_run(service, project_id, actor_context)

    first = record(
        service,
        run.id,
        version.id,
        actor_context,
        numeric_value=None,
        structured_value={"label": "ok", "values": [1, 2]},
        unit="custom",
    )
    second = record(
        service,
        run.id,
        version.id,
        actor_context,
        numeric_value=None,
        structured_value={"values": [1, 2], "label": "ok"},
        unit="custom",
    )
    assert first.content_hash == second.content_hash
    assert first.id != second.id
    listed_ids = [item.id for item in factory().list_measurements_for_run(run.id)]
    assert len(listed_ids) == 2
    assert set(listed_ids) == {first.id, second.id}


@pytest.mark.parametrize(
    ("numeric_value", "structured_value"),
    [(None, None), (1.0, {"value": 1})],
)
def test_value_xor_is_enforced_at_application_boundary(
    resources: tuple[Callable[[], ApplicationService], Engine],
    numeric_value: float | None,
    structured_value: object | None,
) -> None:
    factory, _ = resources
    service = factory()
    _, project_id, actor_context = seed(service)
    _, version = frozen_metric(service, project_id, actor_context, unit=None)
    run = succeeded_run(service, project_id, actor_context)
    with pytest.raises(ResearchBaseError) as error:
        record(
            service,
            run.id,
            version.id,
            actor_context,
            numeric_value=numeric_value,
            structured_value=structured_value,
            unit=None,
        )
    assert error.value.code is ErrorCode.VALIDATION_ERROR
    assert factory().list_measurements_for_run(run.id) == []


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_numeric_values_are_rejected(
    resources: tuple[Callable[[], ApplicationService], Engine], value: float
) -> None:
    factory, _ = resources
    service = factory()
    _, project_id, actor_context = seed(service)
    _, version = frozen_metric(service, project_id, actor_context, unit=None)
    run = succeeded_run(service, project_id, actor_context)
    with pytest.raises(ResearchBaseError) as error:
        record(service, run.id, version.id, actor_context, numeric_value=value, unit=None)
    assert error.value.code is ErrorCode.VALIDATION_ERROR


def test_unrepresentable_numeric_values_return_stable_validation_error(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, _ = resources
    service = factory()
    _, project_id, actor_context = seed(service)
    _, version = frozen_metric(service, project_id, actor_context, unit=None)
    run = succeeded_run(service, project_id, actor_context)
    with pytest.raises(ResearchBaseError) as error:
        record(  # type: ignore[arg-type]
            service, run.id, version.id, actor_context, numeric_value=10**400, unit=None
        )
    assert error.value.code is ErrorCode.VALIDATION_ERROR


def test_eligibility_requires_succeeded_run_and_frozen_metric(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, _ = resources
    service = factory()
    _, project_id, actor_context = seed(service)
    metric = service.create_metric_definition(
        CreateMetricDefinitionCommand(project_id, f"Draft-{uuid4()}", {}, None, None, actor_context)
    )
    assert metric.current_version_id is not None
    spec_run = service.create_experiment_spec(
        CreateExperimentSpecCommand(
            project_id,
            None,
            "Draft run spec",
            "Objective",
            {"step": 1},
            None,
            None,
            None,
            actor_context,
        )
    )
    assert spec_run.current_version_id is not None
    service.freeze_experiment_spec(
        FreezeExperimentSpecCommand(spec_run.id, spec_run.current_version_id, actor_context, 1)
    )
    run = service.create_run(
        CreateRunCommand(project_id, spec_run.current_version_id, None, actor_context)
    )
    with pytest.raises(ResearchBaseError) as planned:
        record(service, run.id, metric.current_version_id, actor_context, unit=None)
    assert planned.value.code in {ErrorCode.INVALID_STATE_TRANSITION, ErrorCode.VERSION_NOT_FROZEN}

    succeeded = succeeded_run(service, project_id, actor_context)
    with pytest.raises(ResearchBaseError) as draft:
        record(service, succeeded.id, metric.current_version_id, actor_context, unit=None)
    assert draft.value.code is ErrorCode.VERSION_NOT_FROZEN

    sessions = create_session_factory(resources[1])
    with SqlAlchemyUnitOfWork(sessions) as uow:
        draft_version = uow.metric_definition_versions.get(metric.current_version_id)
        assert draft_version is not None
        abandoned = draft_version.transition_to(VersionStatus.ABANDONED)
        uow.metric_definition_versions.update(abandoned, draft_version.row_version)
        uow.commit()
    with pytest.raises(ResearchBaseError) as abandoned_error:
        record(service, succeeded.id, metric.current_version_id, actor_context, unit=None)
    assert abandoned_error.value.code is ErrorCode.VERSION_NOT_FROZEN


def test_run_state_matrix_rejects_planned_running_failed_and_cancelled(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, _ = resources
    service = factory()
    _, project_id, actor_context = seed(service)
    _, version = frozen_metric(service, project_id, actor_context, unit=None)
    spec_source = succeeded_run(service, project_id, actor_context)
    planned = service.create_run(
        CreateRunCommand(project_id, spec_source.experiment_spec_version_id, None, actor_context)
    )
    for run in (
        planned,
        service.start_run(StartRunCommand(planned.id, planned.row_version, actor_context)),
    ):
        with pytest.raises(ResearchBaseError) as error:
            record(service, run.id, version.id, actor_context, unit=None)
        assert error.value.code is ErrorCode.INVALID_STATE_TRANSITION

    for outcome in (RunStatus.FAILED, RunStatus.CANCELLED):
        started = service.create_run(
            CreateRunCommand(
                project_id, spec_source.experiment_spec_version_id, None, actor_context
            )
        )
        started = service.start_run(StartRunCommand(started.id, started.row_version, actor_context))
        terminal = service.finish_run(
            FinishRunCommand(started.id, outcome, 1, "test", started.row_version, actor_context)
        )
        with pytest.raises(ResearchBaseError) as error:
            record(service, terminal.id, version.id, actor_context, unit=None)
        assert error.value.code is ErrorCode.INVALID_STATE_TRANSITION


def test_incomplete_provenance_closure_is_rejected(
    resources: tuple[Callable[[], ApplicationService], Engine],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory, _ = resources
    service = factory()
    _, project_id, actor_context = seed(service)
    _, version = frozen_metric(service, project_id, actor_context, unit=None)
    run = succeeded_run(service, project_id, actor_context)

    def incomplete(
        _validator: ProvenanceClosureValidator, _uow: object, _run_id: RunId
    ) -> ClosureReport:
        return ClosureReport(complete=False, visited_count=1, violations=[])

    monkeypatch.setattr(ProvenanceClosureValidator, "validate_run_in_uow", incomplete)
    with pytest.raises(ResearchBaseError) as error:
        record(service, run.id, version.id, actor_context, unit=None)
    assert error.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION


def test_unit_compatibility_is_exact_and_project_scope_is_enforced(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, _ = resources
    service = factory()
    _, project_id, actor_context = seed(service)
    _, version = frozen_metric(service, project_id, actor_context, unit="ms")
    run = succeeded_run(service, project_id, actor_context)
    with pytest.raises(ResearchBaseError) as mismatch:
        record(service, run.id, version.id, actor_context, unit="s")
    assert mismatch.value.code is ErrorCode.VALIDATION_ERROR
    accepted = record(service, run.id, version.id, actor_context, unit=None)
    assert accepted.unit is None

    other_actor = service.create_actor(
        CreateActorCommand(ActorType.HUMAN, f"Other-{uuid4()}", None, context(uuid4()))
    )
    other_context = context(other_actor.id)
    other_project = service.create_project(
        CreateProjectCommand(f"OtherProject-{uuid4()}", None, other_context)
    )
    _, other_version = frozen_metric(service, other_project.id, other_context, unit=None)
    with pytest.raises(ResearchBaseError) as project_error:
        record(service, run.id, other_version.id, actor_context, unit=None)
    assert project_error.value.code is ErrorCode.REFERENTIAL_INTEGRITY_ERROR


def test_exact_provenance_survives_metric_current_pointer_change(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, _ = resources
    service = factory()
    _, project_id, actor_context = seed(service)
    metric, version_one = frozen_metric(service, project_id, actor_context, unit=None)
    run = succeeded_run(service, project_id, actor_context)
    measurement = record(service, run.id, version_one.id, actor_context, unit=None)
    revised = service.revise_metric_definition(
        ReviseMetricDefinitionCommand(
            metric.id,
            {"kind": "median"},
            None,
            "median",
            metric.row_version + 1,
            actor_context,
        )
    )
    assert revised.current_version_id is not None
    assert revised.current_version_id != version_one.id
    with pytest.raises(ResearchBaseError) as superseded:
        record(service, run.id, version_one.id, actor_context, unit=None)
    assert superseded.value.code is ErrorCode.VERSION_NOT_FROZEN
    assert factory().get_measurement(measurement.id).metric_definition_version_id == version_one.id


def test_measurements_are_database_immutable_and_fk_restricted(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, engine = resources
    service = factory()
    actor_id, project_id, actor_context = seed(service)
    metric, version = frozen_metric(service, project_id, actor_context, unit=None)
    run = succeeded_run(service, project_id, actor_context)
    measurement = record(service, run.id, version.id, actor_context, unit=None)

    updates = {
        "id": uuid4(),
        "run_id": run.id,
        "metric_definition_version_id": version.id,
        "numeric_value": 2.0,
        "structured_value": '{"replacement": true}',
        "unit": "bad",
        "evaluation_scope": '{"replacement": true}',
        "content_hash": "a" * 64,
        "created_by": actor_id,
        "created_at": datetime(2026, 8, 29, tzinfo=UTC),
    }
    for column, value in updates.items():
        with pytest.raises(DBAPIError):
            with engine.begin() as connection:
                connection.execute(
                    text(f"UPDATE measurements SET {column}=:value WHERE id=:id"),
                    {"id": measurement.id, "value": value},
                )
    with pytest.raises(DBAPIError):
        with engine.begin() as connection:
            connection.execute(
                text("DELETE FROM measurements WHERE id=:id"), {"id": measurement.id}
            )
    assert factory().get_measurement(measurement.id) is not None

    with pytest.raises(DBAPIError):
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM actors WHERE id=:id"), {"id": actor_id})

    revised = service.revise_metric_definition(
        ReviseMetricDefinitionCommand(
            metric.id,
            {"kind": "median"},
            None,
            "median",
            metric.row_version + 1,
            actor_context,
        )
    )
    assert revised.current_version_id is not None
    with pytest.raises(DBAPIError):
        with engine.begin() as connection:
            connection.execute(
                text("DELETE FROM metric_definition_versions WHERE id=:id"),
                {"id": version.id},
            )
    with pytest.raises(DBAPIError):
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM runs WHERE id=:id"), {"id": run.id})


def test_database_check_enforces_measurement_value_xor(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, engine = resources
    service = factory()
    actor_id, project_id, actor_context = seed(service)
    _, version = frozen_metric(service, project_id, actor_context, unit=None)
    run = succeeded_run(service, project_id, actor_context)
    insert = text(
        "INSERT INTO measurements "
        "(id, run_id, metric_definition_version_id, numeric_value, structured_value, "
        "unit, evaluation_scope, content_hash, created_by, created_at) "
        "VALUES (:id, :run_id, :metric_id, :numeric_value, CAST(:structured_value AS jsonb), "
        "NULL, NULL, :content_hash, :created_by, :created_at)"
    )
    parameters = {
        "run_id": run.id,
        "metric_id": version.id,
        "content_hash": "b" * 64,
        "created_by": actor_id,
        "created_at": datetime(2026, 8, 28, tzinfo=UTC),
    }
    with pytest.raises(DBAPIError):
        with engine.begin() as connection:
            connection.execute(
                insert,
                {
                    **parameters,
                    "id": uuid4(),
                    "numeric_value": None,
                    "structured_value": None,
                },
            )
    with pytest.raises(DBAPIError):
        with engine.begin() as connection:
            connection.execute(
                insert,
                {
                    **parameters,
                    "id": uuid4(),
                    "numeric_value": 1.0,
                    "structured_value": "{}",
                },
            )
    assert factory().list_measurements_for_run(run.id) == []


def test_record_measurement_atomicity_observes_real_insert_and_retries_once(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, engine = resources
    service = factory()
    _, project_id, actor_context = seed(service)
    _, version = frozen_metric(service, project_id, actor_context, unit=None)
    run = succeeded_run(service, project_id, actor_context)
    sessions = create_session_factory(engine)
    observed_inserts: list[str] = []
    same_transaction_counts: list[int] = []

    def after_cursor_execute(
        _connection: object,
        _cursor: object,
        statement: str,
        _parameters: object,
        _context: object,
        _executemany: bool,
    ) -> None:
        if statement.lstrip().upper().startswith("INSERT INTO MEASUREMENTS"):
            observed_inserts.append(statement)

    class FailingUnitOfWork(SqlAlchemyUnitOfWork):
        def commit(self) -> None:
            session = self._require_session()
            session.flush()
            same_transaction_counts.append(
                session.execute(
                    text("SELECT count(*) FROM measurements WHERE run_id=:run_id"),
                    {"run_id": run.id},
                ).scalar_one()
            )
            raise RuntimeError("injected PR-10 measurement failure")

    event.listen(engine, "after_cursor_execute", after_cursor_execute)
    try:
        failing = ApplicationService(
            lambda: FailingUnitOfWork(sessions),
            FixedClock(datetime(2026, 8, 28, 0, 0, tzinfo=UTC)),
        )
        with pytest.raises(RuntimeError, match="injected PR-10 measurement failure"):
            record(failing, run.id, version.id, actor_context, unit=None)
    finally:
        event.remove(engine, "after_cursor_execute", after_cursor_execute)

    assert len(observed_inserts) == 1
    assert same_transaction_counts == [1]
    assert factory().list_measurements_for_run(run.id) == []
    retried = record(service, run.id, version.id, actor_context, unit=None)
    assert len(factory().list_measurements_for_run(run.id)) == 1
    assert factory().get_measurement(retried.id) is not None
