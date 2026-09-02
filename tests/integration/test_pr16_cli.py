# pyright: reportArgumentType=false

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event
from sqlalchemy.engine import Engine
from typer.testing import CliRunner

from researchbase.application.commands import (
    ApplicationService,
    CreateActorCommand,
)
from researchbase.application.governance import GovernanceService
from researchbase.application.governance_queries import GovernanceQueryService
from researchbase.application.provenance_queries import ProvenanceQueryService
from researchbase.cli.app import create_app
from researchbase.cli.composition import ServiceBundle
from researchbase.cli.output import to_jsonable
from researchbase.domain.identity import ActorType
from researchbase.foundation.execution_context import ExecutionContext
from researchbase.foundation.time import SystemClock
from researchbase.persistence.database import create_database_engine, create_session_factory
from researchbase.persistence.uow import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def cli_services() -> Iterator[tuple[ServiceBundle, Engine]]:
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL is not set; run against PostgreSQL")
    engine = create_database_engine()
    sessions = create_session_factory(engine)

    def uow_factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(sessions)

    services = ServiceBundle(
        ApplicationService(uow_factory, SystemClock()),
        ProvenanceQueryService(uow_factory),
        GovernanceService(uow_factory, SystemClock()),
        GovernanceQueryService(uow_factory),
    )
    try:
        yield services, engine
    finally:
        engine.dispose()


def _invoke(
    services: ServiceBundle,
    actor_id: UUID,
    *args: str,
    request_id: UUID | None = None,
) -> object:
    options = ["--actor-id", str(actor_id)]
    if request_id is not None:
        options.extend(["--request-id", str(request_id)])
    result = CliRunner().invoke(create_app(services), [*options, *args, "--json"])
    assert result.exit_code == 0, (args, result.stdout, result.stderr)
    assert result.stderr == ""
    parsed = json.loads(result.stdout)
    return parsed


def _invoke_dict(
    services: ServiceBundle,
    actor_id: UUID,
    *args: str,
    request_id: UUID | None = None,
) -> dict[str, object]:
    result = _invoke(services, actor_id, *args, request_id=request_id)
    assert isinstance(result, dict)
    return result


def _seed_actor(services: ServiceBundle) -> UUID:
    actor_context = ExecutionContext(actor_id=uuid4(), request_id=uuid4(), client_type="test")
    actor = services.application.create_actor(
        CreateActorCommand(ActorType.HUMAN, f"pr16-{uuid4()}", None, actor_context)
    )
    return UUID(str(actor.id))


def test_real_postgresql_cli_write_chain_and_fresh_application_reads(
    cli_services: tuple[ServiceBundle, Engine],
) -> None:
    services, _engine = cli_services
    actor_id = _seed_actor(services)
    project = _invoke_dict(
        services,
        actor_id,
        "project",
        "create",
        "--name",
        f"pr16-{uuid4()}",
        request_id=uuid4(),
    )
    project_id = UUID(str(project["id"]))

    spec = _invoke_dict(
        services,
        actor_id,
        "spec",
        "create",
        "--project-id",
        str(project_id),
        "--title",
        "CLI spec",
        "--objective",
        "adapter equivalence",
        "--protocol",
        '{"steps":["execute"]}',
    )
    spec_id = UUID(str(spec["id"]))
    spec_version_id = UUID(str(spec["current_version_id"]))
    frozen_spec = _invoke_dict(
        services,
        actor_id,
        "spec",
        "freeze",
        "--experiment-spec-id",
        str(spec_id),
        "--version-id",
        str(spec_version_id),
        "--expected-row-version",
        "1",
    )
    assert frozen_spec["status"] == "FROZEN"

    run = _invoke_dict(
        services,
        actor_id,
        "run",
        "create",
        "--project-id",
        str(project_id),
        "--experiment-spec-version-id",
        str(spec_version_id),
    )
    run_id = UUID(str(run["id"]))
    started = _invoke_dict(
        services,
        actor_id,
        "run",
        "start",
        "--run-id",
        str(run_id),
        "--expected-row-version",
        str(run["row_version"]),
    )
    finished = _invoke_dict(
        services,
        actor_id,
        "run",
        "finish",
        "--run-id",
        str(run_id),
        "--outcome",
        "SUCCEEDED",
        "--exit-code",
        "0",
        "--expected-row-version",
        str(started["row_version"]),
    )
    assert finished["status"] == "SUCCEEDED"

    metric = _invoke_dict(
        services,
        actor_id,
        "metric",
        "create",
        "--project-id",
        str(project_id),
        "--name",
        f"latency-{uuid4()}",
        "--definition",
        '{"kind":"mean"}',
        "--unit",
        "ms",
        "--aggregation",
        "mean",
    )
    metric_id = UUID(str(metric["id"]))
    metric_version_id = UUID(str(metric["current_version_id"]))
    _invoke_dict(
        services,
        actor_id,
        "metric",
        "freeze",
        "--metric-definition-id",
        str(metric_id),
        "--version-id",
        str(metric_version_id),
        "--expected-row-version",
        "1",
    )
    measurement = _invoke_dict(
        services,
        actor_id,
        "measurement",
        "create",
        "--run-id",
        str(run_id),
        "--metric-definition-version-id",
        str(metric_version_id),
        "--structured-value",
        '{"latencies":[1.0,2.0]}',
        "--unit",
        "ms",
    )
    measurement_id = UUID(str(measurement["id"]))
    statistical = _invoke_dict(
        services,
        actor_id,
        "stats",
        "create",
        "--project-id",
        str(project_id),
        "--analysis-type",
        "mean",
        "--result-payload",
        '{"mean":1.5}',
        "--analysis-definition",
        '{"method":"arithmetic"}',
        "--inputs",
        json.dumps([{"measurement_id": str(measurement_id)}]),
    )
    statistical_result_id = UUID(str(statistical["id"]))

    claim = _invoke_dict(
        services,
        actor_id,
        "claim",
        "create",
        "--project-id",
        str(project_id),
        "--statement",
        "The run has a measured latency.",
    )
    claim_id = UUID(str(claim["id"]))
    claim_version_id = UUID(str(claim["current_version_id"]))
    _invoke_dict(
        services,
        actor_id,
        "claim",
        "add-evidence",
        "--claim-id",
        str(claim_id),
        "--claim-version-id",
        str(claim_version_id),
        "--measurement-id",
        str(measurement_id),
        "--relation-type",
        "supports",
        "--expected-row-version",
        "1",
    )
    _invoke_dict(
        services,
        actor_id,
        "claim",
        "add-evidence",
        "--claim-id",
        str(claim_id),
        "--claim-version-id",
        str(claim_version_id),
        "--statistical-result-id",
        str(statistical_result_id),
        "--relation-type",
        "supports",
        "--expected-row-version",
        "2",
    )
    frozen_claim = _invoke_dict(
        services,
        actor_id,
        "claim",
        "freeze",
        "--claim-id",
        str(claim_id),
        "--version-id",
        str(claim_version_id),
        "--expected-row-version",
        "3",
    )
    assert frozen_claim["status"] == "FROZEN"

    finding = _invoke_dict(
        services,
        actor_id,
        "audit",
        "create",
        "--project-id",
        str(project_id),
        "--finding-type",
        "cli-test",
        "--severity",
        "minor",
        "--title",
        "CLI finding",
        "--description",
        "CLI governance chain",
        "--target-type",
        "run",
        "--target-id",
        str(run_id),
    )
    _invoke_dict(
        services,
        actor_id,
        "impact",
        "assess",
        "--project-id",
        str(project_id),
        "--audit-finding-id",
        str(finding["id"]),
        "--assessment-payload",
        '{"source":"cli"}',
        "--conclusion",
        "requires_review",
        "--targets",
        json.dumps(
            [
                {
                    "target_type": "claim_version",
                    "target_id": str(claim_version_id),
                    "impact_kind": "requires_review",
                }
            ]
        ),
    )

    assert services.application.get_project(project_id).id == project_id
    assert services.application.get_run(run_id).status.value == "SUCCEEDED"
    assert services.application.get_measurement(measurement_id).structured_value == {
        "latencies": [1.0, 2.0]
    }
    assert (
        services.application.get_statistical_result(statistical_result_id).id
        == statistical_result_id
    )
    assert services.application.get_claim_version(claim_version_id).status.value == "FROZEN"


def test_real_postgresql_cli_queries_are_read_only_and_add_no_selects(
    cli_services: tuple[ServiceBundle, Engine],
) -> None:
    services, engine = cli_services
    actor_id = _seed_actor(services)
    project = _invoke_dict(services, actor_id, "project", "create", "--name", f"query-{uuid4()}")
    project_id = UUID(str(project["id"]))

    # Query purity is measured against a real persisted Application graph created by the
    # accepted seed helper, while the CLI invocation and serialization remain the subject.
    from tests.integration.test_pr14_governance_integration import _seed_graph

    ids = _seed_graph(engine)
    statements: list[str] = []

    def capture(_connection: object, _cursor: object, statement: str, *_args: object) -> None:
        statements.append(statement.lstrip().split(None, 1)[0].upper())

    event.listen(engine, "before_cursor_execute", capture)
    try:
        direct_provenance = services.provenance.get_run_provenance(ids["run"])
        direct_provenance_sql = tuple(statements)
        statements.clear()
        provenance = _invoke_dict(
            services, actor_id, "run", "provenance", "--run-id", str(ids["run"])
        )
        cli_provenance_sql = tuple(statements)
        statements.clear()
        direct_trace = services.provenance.trace_claim_to_runs(ids["claim_version"])
        direct_trace_sql = tuple(statements)
        statements.clear()
        trace = _invoke_dict(
            services,
            actor_id,
            "claim",
            "trace",
            "--claim-version-id",
            str(ids["claim_version"]),
        )
        cli_trace_sql = tuple(statements)
        statements.clear()
        direct_impact = services.governance_queries.downstream_impact(
            ids["project"], "artifact_version", ids["artifact_version"]
        )
        direct_impact_sql = tuple(statements)
        statements.clear()
        impact = _invoke(
            services,
            actor_id,
            "impact",
            "show",
            "--project-id",
            str(ids["project"]),
            "--target-type",
            "artifact_version",
            "--target-id",
            str(ids["artifact_version"]),
        )
        cli_impact_sql = tuple(statements)
    finally:
        event.remove(engine, "before_cursor_execute", capture)

    assert isinstance(provenance, dict)
    assert isinstance(trace, dict)
    assert provenance == to_jsonable(direct_provenance)
    assert trace == to_jsonable(direct_trace)
    assert provenance["run_id"] == str(direct_provenance.run_id)
    assert trace["claim_version_id"] == str(direct_trace.claim_version_id)
    assert isinstance(impact, list)
    assert impact == to_jsonable(direct_impact)
    assert len(impact) == len(direct_impact)
    assert cli_provenance_sql == direct_provenance_sql
    assert cli_trace_sql == direct_trace_sql
    assert cli_impact_sql == direct_impact_sql
    assert all(
        statement == "SELECT" for statement in cli_provenance_sql + cli_trace_sql + cli_impact_sql
    )
    assert "INSERT" not in statements and "UPDATE" not in statements and "DELETE" not in statements
    assert services.application.get_project(project_id).id == project_id


def test_cli_query_invalid_uuid_is_a_transport_error_without_application_call(
    cli_services: tuple[ServiceBundle, Engine],
) -> None:
    services, _engine = cli_services
    actor_id = _seed_actor(services)
    result = CliRunner().invoke(
        create_app(services),
        [
            "--actor-id",
            str(actor_id),
            "run",
            "provenance",
            "--run-id",
            "bad",
            "--json",
        ],
    )
    assert result.exit_code == 2
    assert result.stdout == ""
    assert json.loads(result.stderr)["error"]["code"] == "VALIDATION_ERROR"
