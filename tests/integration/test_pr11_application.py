from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError

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
    RecordStatisticalResultCommand,
    StartRunCommand,
    StatisticalResultInputCommand,
)
from researchbase.application.dto import StatisticalResultInputReadModel
from researchbase.domain.identity import ActorType
from researchbase.domain.measurement import MeasurementId
from researchbase.domain.organization import ProjectId
from researchbase.domain.run import RunStatus
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.execution_context import ExecutionContext
from researchbase.foundation.time import FixedClock
from researchbase.persistence.database import create_database_engine, create_session_factory
from researchbase.persistence.uow import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def resources() -> Iterator[tuple[Callable[[], ApplicationService], Engine]]:
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL is not set; run against the real PostgreSQL service")
    engine = create_database_engine()
    sessions = create_session_factory(engine)
    clock = FixedClock(datetime(2026, 8, 29, 0, 0, tzinfo=UTC))
    try:
        yield lambda: ApplicationService(lambda: SqlAlchemyUnitOfWork(sessions), clock), engine
    finally:
        engine.dispose()


def independent_canonical_json_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def context(actor_id: UUID) -> ExecutionContext:
    return ExecutionContext(actor_id=actor_id, request_id=uuid4(), client_type="test")


def seed_project(
    service: ApplicationService, label: str
) -> tuple[UUID, ProjectId, ExecutionContext]:
    actor = service.create_actor(
        CreateActorCommand(ActorType.HUMAN, f"{label}-actor-{uuid4()}", None, context(uuid4()))
    )
    actor_context = context(actor.id)
    project = service.create_project(
        CreateProjectCommand(f"{label}-project-{uuid4()}", None, actor_context)
    )
    return actor.id, project.id, actor_context


def seed_measurement(
    service: ApplicationService,
    project_id: ProjectId,
    actor_context: ExecutionContext,
    label: str,
    *,
    numeric_value: float = 1.25,
) -> tuple[MeasurementId, ProjectId]:
    metric = service.create_metric_definition(
        CreateMetricDefinitionCommand(
            project_id,
            f"{label}-metric-{uuid4()}",
            {"kind": "mean"},
            "ms",
            "mean",
            actor_context,
        )
    )
    assert metric.current_version_id is not None
    metric_version = service.freeze_metric_definition(
        FreezeMetricDefinitionCommand(metric.id, metric.current_version_id, actor_context, 1)
    )
    spec = service.create_experiment_spec(
        CreateExperimentSpecCommand(
            project_id,
            None,
            f"{label}-spec",
            "StatisticalResult test objective",
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
    finished = service.finish_run(
        FinishRunCommand(run.id, RunStatus.SUCCEEDED, 0, None, started.row_version, actor_context)
    )
    measurement = service.record_measurement(
        RecordMeasurementCommand(
            finished.id,
            metric_version.id,
            numeric_value,
            None,
            "ms",
            {"split": "test"},
            actor_context,
        )
    )
    return measurement.id, project_id


def record_result(
    service: ApplicationService,
    project_id: ProjectId,
    actor_context: ExecutionContext,
    inputs: tuple[StatisticalResultInputCommand, ...],
    *,
    analysis_type: str = "t_test",
    result_payload: object = None,
    analysis_definition: object = None,
):
    return service.record_statistical_result(
        RecordStatisticalResultCommand(
            project_id,
            analysis_type,
            {"p_value": 0.01} if result_payload is None else result_payload,
            {"method": "student", "alternative": "two-sided"}
            if analysis_definition is None
            else analysis_definition,
            inputs,
            actor_context,
        )
    )


def test_record_statistical_result_persists_parent_and_exact_input(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, _ = resources
    service = factory()
    actor_id, project_id, actor_context = seed_project(service, "single")
    measurement_id, _ = seed_measurement(service, project_id, actor_context, "single")

    result = record_result(
        service,
        project_id,
        actor_context,
        (StatisticalResultInputCommand(measurement_id),),
    )

    assert result.project_id == project_id
    assert result.created_by == actor_id
    assert factory().get_statistical_result(result.id) == result
    assert factory().list_statistical_result_inputs(result.id) == [
        StatisticalResultInputReadModel(result.id, measurement_id, "input", 0)
    ]


def test_multiple_inputs_are_deterministically_ordered_and_same_measurement_roles_are_allowed(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, _ = resources
    service = factory()
    _, project_id, actor_context = seed_project(service, "multiple")
    measurement_one, _ = seed_measurement(
        service, project_id, actor_context, "multiple", numeric_value=1.0
    )
    measurement_two, _ = seed_measurement(
        service, project_id, actor_context, "multiple", numeric_value=2.0
    )

    result = record_result(
        service,
        project_id,
        actor_context,
        (
            StatisticalResultInputCommand(measurement_two, "secondary", 1),
            StatisticalResultInputCommand(measurement_one, "input", 0),
            StatisticalResultInputCommand(measurement_one, "secondary", 0),
        ),
    )

    assert factory().list_statistical_result_inputs(result.id) == [
        StatisticalResultInputReadModel(result.id, measurement_one, "input", 0),
        StatisticalResultInputReadModel(result.id, measurement_one, "secondary", 0),
        StatisticalResultInputReadModel(result.id, measurement_two, "secondary", 1),
    ]


def test_duplicate_same_measurement_and_role_is_rejected_before_persistence(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, _ = resources
    service = factory()
    _, project_id, actor_context = seed_project(service, "duplicate")
    measurement_id, _ = seed_measurement(service, project_id, actor_context, "duplicate")
    input_edge = StatisticalResultInputCommand(measurement_id, "input", 0)

    with pytest.raises(ResearchBaseError) as exc_info:
        record_result(service, project_id, actor_context, (input_edge, input_edge))

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert factory().list_statistical_results_for_project(project_id) == []


def test_zero_inputs_and_invalid_input_fields_are_stable_application_errors(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, _ = resources
    service = factory()
    _, project_id, actor_context = seed_project(service, "invalid-input")
    measurement_id, _ = seed_measurement(service, project_id, actor_context, "invalid-input")

    for inputs in (
        (),
        (StatisticalResultInputCommand(measurement_id, "", 0),),
        (StatisticalResultInputCommand(measurement_id, "x" * 33, 0),),
        (StatisticalResultInputCommand(measurement_id, "input", -1),),
    ):
        with pytest.raises(ResearchBaseError) as exc_info:
            record_result(service, project_id, actor_context, inputs)
        assert exc_info.value.code is ErrorCode.VALIDATION_ERROR

    assert factory().list_statistical_results_for_project(project_id) == []


@pytest.mark.parametrize("analysis_type", ["", "x" * 65])
def test_analysis_type_validation_does_not_leak_raw_errors(
    resources: tuple[Callable[[], ApplicationService], Engine], analysis_type: str
) -> None:
    factory, _ = resources
    service = factory()
    _, project_id, actor_context = seed_project(service, "invalid-analysis")
    measurement_id, _ = seed_measurement(service, project_id, actor_context, "invalid-analysis")

    with pytest.raises(ResearchBaseError) as exc_info:
        record_result(
            service,
            project_id,
            actor_context,
            (StatisticalResultInputCommand(measurement_id),),
            analysis_type=analysis_type,
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert factory().list_statistical_results_for_project(project_id) == []


def test_missing_and_cross_project_measurements_are_rejected(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, _ = resources
    service = factory()
    _, project_one, context_one = seed_project(service, "provenance-one")
    _, project_two, context_two = seed_project(service, "provenance-two")
    measurement_two, _ = seed_measurement(service, project_two, context_two, "provenance-two")

    with pytest.raises(ResearchBaseError) as missing:
        record_result(
            service,
            project_one,
            context_one,
            (StatisticalResultInputCommand(MeasurementId(uuid4())),),
        )
    assert missing.value.code is ErrorCode.NOT_FOUND

    with pytest.raises(ResearchBaseError) as cross_project:
        record_result(
            service,
            project_one,
            context_one,
            (StatisticalResultInputCommand(measurement_two),),
        )
    assert cross_project.value.code is ErrorCode.REFERENTIAL_INTEGRITY_ERROR
    assert factory().list_statistical_results_for_project(project_one) == []


def test_hash_matches_independent_oracle_key_order_is_equivalent_and_duplicate_hashes_are_allowed(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, _ = resources
    service = factory()
    _, project_id, actor_context = seed_project(service, "hash")
    measurement_id, _ = seed_measurement(service, project_id, actor_context, "hash")
    input_edge = (StatisticalResultInputCommand(measurement_id),)

    first = record_result(
        service,
        project_id,
        actor_context,
        input_edge,
        result_payload={"z": 1, "a": [True, None]},
        analysis_definition={"b": "two-sided", "a": "student"},
    )
    second = record_result(
        service,
        project_id,
        actor_context,
        input_edge,
        result_payload={"a": [True, None], "z": 1},
        analysis_definition={"a": "student", "b": "two-sided"},
    )
    expected = independent_canonical_json_sha256(
        {
            "analysis_type": "t_test",
            "result_payload": {"z": 1, "a": [True, None]},
            "analysis_definition": {"b": "two-sided", "a": "student"},
        }
    )

    assert first.content_hash == expected
    assert second.content_hash == expected
    assert first.id != second.id
    assert factory().get_statistical_result(first.id).content_hash == expected
    assert factory().get_statistical_result(second.id).content_hash == expected


def test_unserializable_material_returns_validation_error_not_serializer_error(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, _ = resources
    service = factory()
    _, project_id, actor_context = seed_project(service, "unserializable")
    measurement_id, _ = seed_measurement(service, project_id, actor_context, "unserializable")

    with pytest.raises(ResearchBaseError) as exc_info:
        record_result(
            service,
            project_id,
            actor_context,
            (StatisticalResultInputCommand(measurement_id),),
            result_payload=object(),
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert factory().list_statistical_results_for_project(project_id) == []


def test_statistical_result_is_immutable_against_real_postgresql_update_attacks(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, engine = resources
    service = factory()
    _, project_id, actor_context = seed_project(service, "parent-immutable")
    measurement_id, _ = seed_measurement(service, project_id, actor_context, "parent-immutable")
    result = record_result(
        service,
        project_id,
        actor_context,
        (StatisticalResultInputCommand(measurement_id),),
    )
    mutations = {
        "project_id": "CAST(:value AS uuid)",
        "analysis_type": ":value",
        "result_payload": "CAST(:value AS jsonb)",
        "analysis_definition": "CAST(:value AS jsonb)",
        "content_hash": ":value",
        "created_by": "CAST(:value AS uuid)",
        "created_at": "CAST(:value AS timestamptz)",
    }
    values = {
        "project_id": str(uuid4()),
        "analysis_type": "other",
        "result_payload": '{"changed":true}',
        "analysis_definition": '{"changed":true}',
        "content_hash": "f" * 64,
        "created_by": str(uuid4()),
        "created_at": "2026-08-30T00:00:00+00:00",
    }

    for field, expression in mutations.items():
        with pytest.raises(DBAPIError):
            with engine.begin() as connection:
                connection.execute(
                    text(f"UPDATE statistical_results SET {field}={expression} WHERE id=:id"),
                    {"id": result.id, "value": values[field]},
                )
        assert factory().get_statistical_result(result.id) == result


def test_statistical_result_input_set_is_immutable_against_real_postgresql_attacks(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, engine = resources
    service = factory()
    _, project_id, actor_context = seed_project(service, "input-immutable")
    measurement_one, _ = seed_measurement(
        service, project_id, actor_context, "input-immutable", numeric_value=1.0
    )
    measurement_two, _ = seed_measurement(
        service, project_id, actor_context, "input-immutable", numeric_value=2.0
    )
    result = record_result(
        service,
        project_id,
        actor_context,
        (StatisticalResultInputCommand(measurement_one),),
    )
    baseline = factory().list_statistical_result_inputs(result.id)

    with pytest.raises(DBAPIError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO statistical_result_inputs "
                    "(statistical_result_id, measurement_id, input_role, ordinal) "
                    "VALUES (:result_id, :measurement_id, 'secondary', 1)"
                ),
                {"result_id": result.id, "measurement_id": measurement_two},
            )

    mutations = {
        "statistical_result_id": str(uuid4()),
        "measurement_id": str(measurement_two),
        "input_role": "secondary",
        "ordinal": 9,
    }
    for field, value in mutations.items():
        with pytest.raises(DBAPIError):
            with engine.begin() as connection:
                connection.execute(
                    text(
                        f"UPDATE statistical_result_inputs SET {field}=:value "
                        "WHERE statistical_result_id=:result_id AND measurement_id=:measurement_id "
                        "AND input_role='input'"
                    ),
                    {
                        "value": value,
                        "result_id": result.id,
                        "measurement_id": measurement_one,
                    },
                )

    with pytest.raises(DBAPIError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "DELETE FROM statistical_result_inputs WHERE statistical_result_id=:result_id "
                    "AND measurement_id=:measurement_id AND input_role='input'"
                ),
                {"result_id": result.id, "measurement_id": measurement_one},
            )

    assert factory().list_statistical_result_inputs(result.id) == baseline


def test_statistical_result_atomicity_observes_inserts_then_rolls_back_and_retries(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, engine = resources
    service = factory()
    _, project_id, actor_context = seed_project(service, "atomicity")
    measurement_one, _ = seed_measurement(
        service, project_id, actor_context, "atomicity", numeric_value=1.0
    )
    measurement_two, _ = seed_measurement(
        service, project_id, actor_context, "atomicity", numeric_value=2.0
    )
    sessions = create_session_factory(engine)
    observed_inserts: list[str] = []
    same_transaction_counts: list[tuple[int, int]] = []

    def after_cursor_execute(
        _connection: object,
        _cursor: object,
        statement: str,
        _parameters: object,
        _context: object,
        _executemany: bool,
    ) -> None:
        normalized = statement.lstrip().upper()
        if normalized.startswith("INSERT INTO STATISTICAL_RESULTS") or normalized.startswith(
            "INSERT INTO STATISTICAL_RESULT_INPUTS"
        ):
            observed_inserts.append(statement)

    class FailingUnitOfWork(SqlAlchemyUnitOfWork):
        def commit(self) -> None:
            session = self._require_session()
            session.flush()
            parent_count = session.execute(
                text("SELECT count(*) FROM statistical_results WHERE project_id=:project_id"),
                {"project_id": project_id},
            ).scalar_one()
            input_count = session.execute(
                text(
                    "SELECT count(*) FROM statistical_result_inputs sri "
                    "JOIN statistical_results sr ON sr.id=sri.statistical_result_id "
                    "WHERE sr.project_id=:project_id"
                ),
                {"project_id": project_id},
            ).scalar_one()
            same_transaction_counts.append((parent_count, input_count))
            raise RuntimeError("injected PR-11 statistical result failure")

    event.listen(engine, "after_cursor_execute", after_cursor_execute)
    try:
        failing = ApplicationService(
            lambda: FailingUnitOfWork(sessions),
            FixedClock(datetime(2026, 8, 29, tzinfo=UTC)),
        )
        with pytest.raises(RuntimeError, match="injected PR-11 statistical result failure"):
            record_result(
                failing,
                project_id,
                actor_context,
                (
                    StatisticalResultInputCommand(measurement_one, "input", 0),
                    StatisticalResultInputCommand(measurement_two, "secondary", 1),
                ),
            )
    finally:
        event.remove(engine, "after_cursor_execute", after_cursor_execute)

    assert sum("INSERT INTO STATISTICAL_RESULTS" in item.upper() for item in observed_inserts) == 1
    assert (
        sum("INSERT INTO STATISTICAL_RESULT_INPUTS" in item.upper() for item in observed_inserts)
        == 2
    )
    assert same_transaction_counts == [(1, 2)]
    assert factory().list_statistical_results_for_project(project_id) == []

    retried = record_result(
        service,
        project_id,
        actor_context,
        (
            StatisticalResultInputCommand(measurement_one, "input", 0),
            StatisticalResultInputCommand(measurement_two, "secondary", 1),
        ),
    )
    assert len(factory().list_statistical_results_for_project(project_id)) == 1
    assert factory().list_statistical_result_inputs(retried.id) == [
        StatisticalResultInputReadModel(retried.id, measurement_one, "input", 0),
        StatisticalResultInputReadModel(retried.id, measurement_two, "secondary", 1),
    ]


def test_exact_measurement_provenance_survives_later_measurement_creation(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, _ = resources
    service = factory()
    _, project_id, actor_context = seed_project(service, "provenance-history")
    measurement_one, _ = seed_measurement(
        service, project_id, actor_context, "provenance-history", numeric_value=1.0
    )
    result = record_result(
        service,
        project_id,
        actor_context,
        (StatisticalResultInputCommand(measurement_one),),
    )
    before = factory().get_statistical_result(result.id)
    measurement_two, _ = seed_measurement(
        service, project_id, actor_context, "provenance-history", numeric_value=2.0
    )

    assert measurement_two != measurement_one
    assert factory().list_statistical_result_inputs(result.id) == [
        StatisticalResultInputReadModel(result.id, measurement_one, "input", 0)
    ]
    assert factory().get_statistical_result(result.id) == before


def test_project_query_isolated_and_deterministic_and_returns_dtos(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, _ = resources
    service = factory()
    _, project_one, context_one = seed_project(service, "query-one")
    _, project_two, context_two = seed_project(service, "query-two")
    measurement_one, _ = seed_measurement(service, project_one, context_one, "query-one")
    measurement_two, _ = seed_measurement(service, project_two, context_two, "query-two")
    first = record_result(
        service,
        project_one,
        context_one,
        (StatisticalResultInputCommand(measurement_one),),
    )
    second = record_result(
        service,
        project_one,
        context_one,
        (StatisticalResultInputCommand(measurement_one, "secondary"),),
    )
    other = record_result(
        service,
        project_two,
        context_two,
        (StatisticalResultInputCommand(measurement_two),),
    )

    listed = factory().list_statistical_results_for_project(project_one)
    assert [item.id for item in listed] == sorted([first.id, second.id])
    assert all(item.project_id == project_one for item in listed)
    assert factory().list_statistical_results_for_project(project_two) == [other]
    assert not hasattr(listed[0], "_sa_instance_state")


@pytest.mark.parametrize(
    ("table", "where", "parameters"),
    [
        ("projects", "id=:id", "project"),
        ("actors", "id=:id", "actor"),
        ("measurements", "id=:id", "measurement"),
        ("statistical_results", "id=:id", "result"),
    ],
)
def test_referenced_rows_are_behaviorally_restrictive(
    resources: tuple[Callable[[], ApplicationService], Engine],
    table: str,
    where: str,
    parameters: str,
) -> None:
    factory, engine = resources
    service = factory()
    actor_id, project_id, actor_context = seed_project(service, f"fk-{table}")
    measurement_id, _ = seed_measurement(service, project_id, actor_context, f"fk-{table}")
    result = record_result(
        service,
        project_id,
        actor_context,
        (StatisticalResultInputCommand(measurement_id),),
    )
    ids = {
        "project": project_id,
        "actor": actor_id,
        "measurement": measurement_id,
        "result": result.id,
    }

    with pytest.raises(DBAPIError):
        with engine.begin() as connection:
            connection.execute(
                text(f"DELETE FROM {table} WHERE {where}"),
                {"id": ids[parameters]},
            )

    assert factory().get_statistical_result(result.id) == result
    assert factory().get_measurement(measurement_id) is not None
