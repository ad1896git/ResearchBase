from __future__ import annotations

# pyright: reportArgumentType=false
import os
from collections.abc import Iterator
from dataclasses import asdict, dataclass, is_dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.encoders import jsonable_encoder
from fastapi.testclient import TestClient
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from tests.integration.test_pr14_governance_integration import _seed_graph

from researchbase.api.app import ServiceBundle, create_app
from researchbase.application.commands import (
    ApplicationService,
    CreateExperimentSpecCommand,
    CreateMetricDefinitionCommand,
    CreateProjectCommand,
    CreateRunCommand,
    FinishRunCommand,
    FreezeExperimentSpecCommand,
    FreezeMetricDefinitionCommand,
    RecordMeasurementCommand,
    StartRunCommand,
    WriteProjectionTarget,
)
from researchbase.application.governance import CreateAuditFindingCommand, GovernanceService
from researchbase.application.governance_queries import GovernanceQueryService
from researchbase.application.provenance_queries import ProvenanceQueryService
from researchbase.domain.governance import AuditFindingSeverity, GovernanceTargetType
from researchbase.domain.run import RunStatus
from researchbase.foundation.execution_context import ExecutionContext
from researchbase.foundation.time import SystemClock
from researchbase.persistence.database import create_database_engine, create_session_factory
from researchbase.persistence.uow import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.integration


def _json_value(value: object) -> object:
    if isinstance(value, tuple):
        encoded = jsonable_encoder([asdict(item) for item in value])
        return _normalize_utc(encoded)
    assert is_dataclass(value)
    return _normalize_utc(jsonable_encoder(asdict(value)))


def _normalize_utc(value: object) -> object:
    if isinstance(value, dict):
        return {key: _normalize_utc(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_utc(item) for item in value]
    if isinstance(value, str) and value.endswith("+00:00"):
        return f"{value[:-6]}Z"
    return value


def _state_counts(engine: Engine) -> tuple[int, ...]:
    tables = (
        "projects",
        "runs",
        "measurements",
        "statistical_results",
        "claim_versions",
        "evidence_relations",
        "audit_findings",
        "impact_assessments",
        "correction_records",
    )
    with engine.connect() as connection:
        return tuple(
            int(connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one())
            for table in tables
        )


class OneShotFailureApplication:
    def __init__(self, delegate: ApplicationService) -> None:
        self.delegate = delegate
        self.fail_next_project = False

    def __getattr__(self, name: str) -> object:
        return getattr(self.delegate, name)

    def create_project(self, command: object) -> object:
        if self.fail_next_project:
            self.fail_next_project = False
            raise RuntimeError("controlled private database detail")
        return self.delegate.create_project(command)  # type: ignore[arg-type]


@dataclass
class RecoveryServices:
    application: object
    provenance: object
    governance: object
    governance_queries: object


@pytest.fixture(scope="module")
def real_services() -> Iterator[tuple[ServiceBundle, Engine]]:
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL is not set; run against PostgreSQL")
    engine = create_database_engine()
    sessions = create_session_factory(engine)

    def uow_factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(sessions)

    clock = SystemClock()
    yield (
        ServiceBundle(
            ApplicationService(uow_factory, clock),
            ProvenanceQueryService(uow_factory),
            GovernanceService(uow_factory, clock),
            GovernanceQueryService(uow_factory),
        ),
        engine,
    )
    engine.dispose()


def test_real_postgresql_query_is_application_equivalent_read_only_and_sql_bounded(
    real_services: tuple[ServiceBundle, Engine],
) -> None:
    services, engine = real_services
    ids = _seed_graph(engine)
    state_before = _state_counts(engine)
    statements: list[str] = []

    def capture(_conn: object, _cursor: object, statement: str, *_args: object) -> None:
        statements.append(statement.lstrip().split(None, 1)[0].upper())

    event.listen(engine, "before_cursor_execute", capture)
    try:
        direct = services.provenance.get_run_provenance(ids["run"])
        direct_count = len(statements)
        statements.clear()
        response = TestClient(create_app(services)).get(f"/v1/runs/{ids['run']}/provenance")
        http_count = len(statements)
    finally:
        event.remove(engine, "before_cursor_execute", capture)

    assert response.status_code == 200
    assert response.json() == _json_value(direct)
    assert http_count == direct_count
    assert set(statements) <= {"SELECT"}
    assert _state_counts(engine) == state_before


@pytest.mark.parametrize(
    ("direct_call", "path"),
    [
        (
            lambda services, ids: services.provenance.trace_claim_to_runs(ids["claim_version"]),
            lambda ids: f"/v1/claim-versions/{ids['claim_version']}/trace",
        ),
        (
            lambda services, ids: services.governance_queries.downstream_impact(
                ids["project"], "artifact_version", ids["artifact_version"]
            ),
            lambda ids: (
                f"/v1/impact/artifact_version/{ids['artifact_version']}?project_id={ids['project']}"
            ),
        ),
    ],
)
def test_trace_and_impact_http_queries_are_equivalent_read_only_and_add_no_sql(
    real_services: tuple[ServiceBundle, Engine],
    direct_call: object,
    path: object,
) -> None:
    services, engine = real_services
    ids = _seed_graph(engine)
    state_before = _state_counts(engine)
    statements: list[str] = []

    def capture(_conn: object, _cursor: object, statement: str, *_args: object) -> None:
        statements.append(statement.lstrip().split(None, 1)[0].upper())

    event.listen(engine, "before_cursor_execute", capture)
    try:
        direct = direct_call(services, ids)  # type: ignore[operator]
        direct_sql = tuple(statements)
        statements.clear()
        response = TestClient(create_app(services)).get(path(ids))  # type: ignore[operator]
        http_sql = tuple(statements)
    finally:
        event.remove(engine, "before_cursor_execute", capture)

    assert response.status_code == 200
    assert response.json() == _json_value(direct)
    assert http_sql == direct_sql
    assert set(http_sql) <= {"SELECT"}
    assert _state_counts(engine) == state_before
    if "trace" in path(ids):  # type: ignore[operator]
        assert len(response.json()["paths"]) >= 2
    else:
        assert sum(len(target["paths"]) for target in response.json()) >= 2


@pytest.mark.parametrize(
    ("route", "mode"),
    [("trace", "small"), ("trace", "multipath"), ("impact", "small"), ("impact", "multipath")],
)
def test_trace_and_impact_sql_counts_are_bounded_across_fixture_cardinality(
    real_services: tuple[ServiceBundle, Engine], route: str, mode: str
) -> None:
    services, engine = real_services
    ids = _seed_graph(engine)
    if route == "trace" and mode == "small":
        ids["small_claim_version"] = uuid4()
        ids["small_evidence"] = uuid4()
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO claim_versions "
                    "(id,claim_id,version_number,status,statement,created_by,created_at) "
                    "VALUES (:id,:claim,2,'DRAFT','small claim',:actor,:now)"
                ),
                {
                    "id": ids["small_claim_version"],
                    "claim": ids["claim"],
                    "actor": ids["actor"],
                    "now": datetime(2026, 8, 30, tzinfo=UTC),
                },
            )
            connection.execute(
                text(
                    "INSERT INTO evidence_relations "
                    "(id,claim_version_id,measurement_id,relation_type,created_by,created_at) "
                    "VALUES (:id,:claim,:measurement,'SUPPORTS',:actor,:now)"
                ),
                {
                    "id": ids["small_evidence"],
                    "claim": ids["small_claim_version"],
                    "measurement": ids["measurement"],
                    "actor": ids["actor"],
                    "now": datetime(2026, 8, 30, tzinfo=UTC),
                },
            )
    target_key = "stat" if route == "impact" and mode == "small" else "artifact_version"
    target_type = "statistical_result" if target_key == "stat" else "artifact_version"
    state_before = _state_counts(engine)
    if route == "trace":
        claim_version_id = ids.get("small_claim_version", ids["claim_version"])
        direct_path = f"/v1/claim-versions/{claim_version_id}/trace"

        def direct_call() -> object:
            return services.provenance.trace_claim_to_runs(claim_version_id)

    else:
        direct_path = f"/v1/impact/{target_type}/{ids[target_key]}?project_id={ids['project']}"

        def direct_call() -> object:
            return services.governance_queries.downstream_impact(
                ids["project"], target_type, ids[target_key]
            )

    statements: list[str] = []

    def capture(_conn: object, _cursor: object, statement: str, *_args: object) -> None:
        statements.append(statement.lstrip().split(None, 1)[0].upper())

    event.listen(engine, "before_cursor_execute", capture)
    try:
        direct = direct_call()
        direct_selects = statements.count("SELECT")
        statements.clear()
        response = TestClient(create_app(services)).get(direct_path)
        http_selects = statements.count("SELECT")
        writes = sum(statements.count(kind) for kind in ("INSERT", "UPDATE", "DELETE"))
    finally:
        event.remove(engine, "before_cursor_execute", capture)

    assert response.status_code == 200
    assert response.json() == _json_value(direct)
    assert http_selects == direct_selects
    assert writes == 0
    assert _state_counts(engine) == state_before
    cardinality = (
        len(response.json()["paths"])
        if route == "trace"
        else sum(len(target["paths"]) for target in response.json())
    )
    assert cardinality == (1 if mode == "small" else (2 if route == "trace" else 5))


def test_real_postgresql_http_golden_flow_uses_application_semantics(
    real_services: tuple[ServiceBundle, Engine],
) -> None:
    services, engine = real_services
    actor_id = uuid4()
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO actors(id,actor_type,display_name,created_at) "
                "VALUES (:id,'HUMAN','pr15-http',:now)"
            ),
            {"id": actor_id, "now": datetime.now(UTC)},
        )
    client = TestClient(create_app(services))
    headers = {"X-Actor-ID": str(actor_id), "X-Request-ID": str(uuid4())}

    project = client.post("/v1/projects", json={"name": f"PR15-{uuid4()}"}, headers=headers)
    assert project.status_code == 201
    project_id = UUID(project.json()["id"])

    spec = client.post(
        "/v1/experiment-specs",
        json={
            "project_id": str(project_id),
            "title": "HTTP spec",
            "objective": "prove adapter equivalence",
            "protocol": {"steps": ["execute"]},
        },
        headers=headers,
    )
    assert spec.status_code == 201
    spec_body = spec.json()
    draft_reference = client.post(
        "/v1/runs",
        json={
            "project_id": str(project_id),
            "experiment_spec_version_id": spec_body["current_version_id"],
        },
        headers=headers,
    )
    assert draft_reference.status_code == 409
    assert draft_reference.json()["error"]["code"] == "VERSION_NOT_FROZEN"
    stale_freeze = client.post(
        f"/v1/experiment-spec-versions/{spec_body['current_version_id']}:freeze",
        json={"experiment_spec_id": spec_body["id"], "expected_row_version": 999},
        headers=headers,
    )
    assert stale_freeze.status_code == 409
    assert stale_freeze.json()["error"]["code"] == "CONCURRENT_MODIFICATION"
    frozen_spec = client.post(
        f"/v1/experiment-spec-versions/{spec_body['current_version_id']}:freeze",
        json={
            "experiment_spec_id": spec_body["id"],
            "expected_row_version": 1,
        },
        headers=headers,
    )
    assert frozen_spec.status_code == 200

    other_project = client.post(
        "/v1/projects", json={"name": f"PR15-other-{uuid4()}"}, headers=headers
    )
    assert other_project.status_code == 201
    wrong_project = client.post(
        "/v1/runs",
        json={
            "project_id": other_project.json()["id"],
            "experiment_spec_version_id": frozen_spec.json()["id"],
        },
        headers=headers,
    )
    assert wrong_project.status_code == 409
    assert wrong_project.json()["error"]["code"] == "REFERENTIAL_INTEGRITY_ERROR"

    run = client.post(
        "/v1/runs",
        json={
            "project_id": str(project_id),
            "experiment_spec_version_id": frozen_spec.json()["id"],
        },
        headers=headers,
    )
    assert run.status_code == 201
    run_id = run.json()["id"]
    started = client.post(
        f"/v1/runs/{run_id}:start",
        json={"expected_row_version": run.json()["row_version"]},
        headers=headers,
    )
    assert started.status_code == 200
    immutable_input = client.post(
        f"/v1/runs/{run_id}/dataset-inputs",
        json={
            "dataset_snapshot_id": str(uuid4()),
            "role": "test",
            "expected_row_version": started.json()["row_version"],
        },
        headers=headers,
    )
    assert immutable_input.status_code == 409
    assert immutable_input.json()["error"]["code"] == "IMMUTABLE_RECORD"
    finished = client.post(
        f"/v1/runs/{run_id}:finish",
        json={
            "expected_row_version": started.json()["row_version"],
            "outcome": "SUCCEEDED",
            "exit_code": 0,
        },
        headers=headers,
    )
    assert finished.status_code == 200

    metric = client.post(
        "/v1/metric-definitions",
        json={
            "project_id": str(project_id),
            "name": f"metric-{uuid4()}",
            "definition": {"kind": "mean"},
            "unit": "ms",
            "aggregation": "mean",
        },
        headers=headers,
    )
    assert metric.status_code == 201
    metric_body = metric.json()
    metric_version = client.post(
        f"/v1/metric-definition-versions/{metric_body['current_version_id']}:freeze",
        json={"metric_definition_id": metric_body["id"], "expected_row_version": 1},
        headers=headers,
    )
    assert metric_version.status_code == 200
    measurement = client.post(
        "/v1/measurements",
        json={
            "run_id": run_id,
            "metric_definition_version_id": metric_version.json()["id"],
            "structured_value": {"latencies": [1.0, 2.0]},
            "unit": "ms",
        },
        headers=headers,
    )
    assert measurement.status_code == 201
    provenance = client.get(f"/v1/runs/{run_id}/provenance")
    assert provenance.status_code == 200
    assert provenance.json()["run_id"] == run_id

    audit = client.post(
        "/v1/audit-findings",
        json={
            "project_id": str(project_id),
            "finding_type": "adapter_test",
            "severity": "minor",
            "title": "HTTP flow",
            "description": "created through accepted governance service",
            "target_type": "run",
            "target_id": run_id,
        },
        headers=headers,
    )
    assert audit.status_code == 201

    assert services.application.get_project(project_id).id == project_id
    spec_history = services.application.get_experiment_spec_history(UUID(spec_body["id"]))
    assert spec_history[0].status.value == "FROZEN"
    assert services.application.get_run(UUID(run_id)).status.value == "SUCCEEDED"
    persisted_measurement = services.application.get_measurement(UUID(measurement.json()["id"]))
    assert persisted_measurement.structured_value == {"latencies": [1.0, 2.0]}
    assert services.governance_queries.get_audit_finding(UUID(audit.json()["id"])) is not None

    context = ExecutionContext(actor_id=actor_id, request_id=uuid4(), client_type="test")
    direct_project = services.application.project_write_result(
        services.application.create_project(
            CreateProjectCommand(f"PR15-direct-{uuid4()}", None, context)
        ),
        WriteProjectionTarget.PROJECT,
    )
    direct_spec = services.application.project_write_result(
        services.application.create_experiment_spec(
            CreateExperimentSpecCommand(
                direct_project.id,
                None,
                "HTTP spec",
                "prove adapter equivalence",
                {"steps": ["execute"]},
                None,
                None,
                None,
                context,
            )
        ),
        WriteProjectionTarget.EXPERIMENT_SPEC,
    )
    direct_frozen_spec = services.application.project_write_result(
        services.application.freeze_experiment_spec(
            FreezeExperimentSpecCommand(direct_spec.id, direct_spec.current_version_id, context, 1)
        ),
        WriteProjectionTarget.EXPERIMENT_SPEC_VERSION,
    )
    direct_run = services.application.project_write_result(
        services.application.create_run(
            CreateRunCommand(direct_project.id, direct_frozen_spec.id, None, context)
        ),
        WriteProjectionTarget.RUN,
    )
    direct_started = services.application.project_write_result(
        services.application.start_run(
            StartRunCommand(direct_run.id, direct_run.row_version, context)
        ),
        WriteProjectionTarget.RUN,
    )
    direct_finished = services.application.project_write_result(
        services.application.finish_run(
            FinishRunCommand(
                direct_run.id,
                RunStatus.SUCCEEDED,
                0,
                None,
                direct_started.row_version,
                context,
            )
        ),
        WriteProjectionTarget.RUN,
    )
    direct_metric = services.application.project_write_result(
        services.application.create_metric_definition(
            CreateMetricDefinitionCommand(
                direct_project.id,
                f"metric-{uuid4()}",
                {"kind": "mean"},
                "ms",
                "mean",
                context,
            )
        ),
        WriteProjectionTarget.METRIC_DEFINITION,
    )
    direct_metric_version = services.application.project_write_result(
        services.application.freeze_metric_definition(
            FreezeMetricDefinitionCommand(
                direct_metric.id, direct_metric.current_version_id, context, 1
            )
        ),
        WriteProjectionTarget.METRIC_DEFINITION_VERSION,
    )
    direct_measurement = services.application.project_write_result(
        services.application.record_measurement(
            RecordMeasurementCommand(
                direct_run.id,
                direct_metric_version.id,
                None,
                {"latencies": [1.0, 2.0]},
                "ms",
                None,
                context,
            )
        ),
        WriteProjectionTarget.MEASUREMENT,
    )
    direct_audit = services.governance.create_audit_finding(
        CreateAuditFindingCommand(
            direct_project.id,
            "adapter_test",
            AuditFindingSeverity.MINOR,
            "HTTP flow",
            "created through accepted governance service",
            GovernanceTargetType.RUN,
            direct_run.id,
            context,
        )
    )
    assert frozen_spec.json()["status"] == direct_frozen_spec.status.value
    assert frozen_spec.json()["content_hash"] == direct_frozen_spec.content_hash
    assert finished.json()["status"] == direct_finished.status.value
    assert finished.json()["row_version"] == direct_finished.row_version
    assert measurement.json()["structured_value"] == direct_measurement.structured_value
    assert measurement.json()["unit"] == direct_measurement.unit
    assert audit.json()["severity"] == direct_audit.severity.value
    assert audit.json()["status"] == direct_audit.status.value

    invalid = client.post(
        f"/v1/runs/{run_id}:finish",
        json={
            "expected_row_version": finished.json()["row_version"],
            "outcome": "SUCCEEDED",
        },
        headers=headers,
    )
    assert invalid.status_code == 409
    assert invalid.json()["error"]["code"] == "INVALID_STATE_TRANSITION"


def test_real_postgresql_error_then_next_request_recovers(
    real_services: tuple[ServiceBundle, Engine],
) -> None:
    services, engine = real_services
    ids = _seed_graph(engine)
    client = TestClient(create_app(services))

    missing = client.get("/v1/runs/00000000-0000-0000-0000-000000000000/provenance")
    recovered = client.get(f"/v1/runs/{ids['run']}/provenance")

    assert missing.status_code == 404
    assert recovered.status_code == 200
    assert recovered.json()["run_id"] == str(ids["run"])


def test_real_postgresql_full_error_recovery_sequence(
    real_services: tuple[ServiceBundle, Engine],
) -> None:
    services, engine = real_services
    ids = _seed_graph(engine)
    application = OneShotFailureApplication(services.application)
    recovery_services = RecoveryServices(
        application,
        services.provenance,
        services.governance,
        services.governance_queries,
    )
    client = TestClient(create_app(recovery_services), raise_server_exceptions=False)
    headers = {"X-Actor-ID": str(ids["actor"])}

    valid_write = client.post("/v1/projects", json={"name": f"recovery-{uuid4()}"}, headers=headers)
    assert valid_write.status_code == 201
    project_id = UUID(valid_write.json()["id"])

    handled = client.get("/v1/runs/00000000-0000-0000-0000-000000000000/provenance")
    assert handled.status_code == 404
    assert client.get(f"/v1/runs/{ids['run']}/provenance").status_code == 200

    invalid = client.post("/v1/projects", json={}, headers=headers)
    assert invalid.status_code == 422
    assert client.get(f"/v1/runs/{ids['run']}/provenance").status_code == 200

    application.fail_next_project = True
    unexpected = client.post("/v1/projects", json={"name": f"fail-{uuid4()}"}, headers=headers)
    assert unexpected.status_code == 500
    assert "database detail" not in unexpected.text
    assert client.get(f"/v1/runs/{ids['run']}/provenance").status_code == 200

    assert services.application.get_project(project_id).id == project_id
