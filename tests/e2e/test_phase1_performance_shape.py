"""PR-17 query purity and SQL performance-shape acceptance."""

# pyright: reportArgumentType=false

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event
from tests.e2e.support import _request_headers, fresh_fixture, run_workflow

from researchbase.application.commands import (
    AttachRunArtifactInputCommand,
    AttachRunDatasetInputCommand,
    CreateClaimCommand,
    CreateRunCommand,
    FinishRunCommand,
    FreezeClaimVersionCommand,
    LinkEvidenceCommand,
    RecordMeasurementCommand,
    RecordStatisticalResultCommand,
    StartRunCommand,
    StatisticalResultInputCommand,
)
from researchbase.domain.claim import EvidenceRelationType
from researchbase.domain.governance import GovernanceTargetType
from researchbase.domain.run import ArtifactInputRole, DatasetInputRole, RunStatus

pytestmark = [pytest.mark.integration, pytest.mark.phase1_golden]


def _capture(engine: Any, action: Any) -> tuple[Any, list[str]]:
    statements: list[str] = []

    def observe(
        _connection: Any,
        _cursor: Any,
        statement: str,
        _parameters: Any,
        _context: Any,
        _executemany: Any,
    ) -> None:
        statements.append(statement.lstrip().split(None, 1)[0].upper())

    event.listen(engine, "before_cursor_execute", observe)
    try:
        result = action()
    finally:
        event.remove(engine, "before_cursor_execute", observe)
    return result, statements


def _scale_graph(fixture: Any, ids: Any, size: int) -> tuple[UUID, UUID]:
    app = fixture.fresh_application()
    context = fixture.context
    measurements: list[UUID] = []
    statistical_results: list[UUID] = []
    for index in range(size):
        run = app.create_run(
            CreateRunCommand(
                ids.project_id,
                ids.experiment_spec_version_id,
                f"scale-{size}-{index}",
                context,
            )
        )
        run = app.attach_run_dataset_input(
            AttachRunDatasetInputCommand(
                run.id, ids.dataset_snapshot_id, DatasetInputRole.TEST, 0, run.row_version, context
            )
        )
        run = app.attach_run_artifact_input(
            AttachRunArtifactInputCommand(
                run.id,
                ids.artifact_version_id,
                ArtifactInputRole.SOURCE_CODE,
                0,
                run.row_version,
                context,
            )
        )
        run = app.start_run(StartRunCommand(run.id, run.row_version, context))
        run = app.finish_run(
            FinishRunCommand(run.id, RunStatus.SUCCEEDED, 0, None, run.row_version, context)
        )
        measurement = app.record_measurement(
            RecordMeasurementCommand(
                run.id,
                ids.metric_definition_version_id,
                float(index + 1),
                None,
                "ms",
                {"scale": size, "ordinal": index},
                context,
            )
        )
        statistical = app.record_statistical_result(
            RecordStatisticalResultCommand(
                ids.project_id,
                "mean",
                {"mean": float(index + 1)},
                {"method": "arithmetic"},
                (StatisticalResultInputCommand(measurement.id, "input", 0),),
                context,
            )
        )
        measurements.append(UUID(str(measurement.id)))
        statistical_results.append(UUID(str(statistical.id)))

    claim = app.create_claim(
        CreateClaimCommand(ids.project_id, f"scaled claim {size}", {"scale": size}, None, context)
    )
    version = app.get_current_claim_version(claim.id)
    for measurement_id, statistical_id in zip(measurements, statistical_results, strict=True):
        relation = app.link_evidence(
            LinkEvidenceCommand(
                claim.id,
                version.id,
                measurement_id,
                None,
                EvidenceRelationType.SUPPORTS,
                "direct",
                version.row_version,
                context,
            )
        )
        version = app.get_current_claim_version(claim.id)
        del relation
        app.link_evidence(
            LinkEvidenceCommand(
                claim.id,
                version.id,
                None,
                statistical_id,
                EvidenceRelationType.SUPPORTS,
                "statistical",
                version.row_version,
                context,
            )
        )
        version = app.get_current_claim_version(claim.id)
    app.freeze_claim_version(
        FreezeClaimVersionCommand(claim.id, version.id, context, version.row_version)
    )
    return UUID(str(claim.id)), UUID(str(version.id))


def _cli_query(fixture: Any, args: list[str]) -> Any:
    return fixture.cli_runner.invoke(
        fixture.cli_app,
        [
            "--actor-id",
            str(fixture.actor_id),
            "--request-id",
            str(uuid4()),
            "--correlation-id",
            str(fixture.context.correlation_id),
            "--causation-id",
            str(fixture.context.causation_id),
            "--client-name",
            "pr17-performance",
            "--client-version",
            "1",
            *args,
            "--json",
        ],
    )


def test_application_http_cli_queries_are_read_only_and_formatting_adds_no_selects(
    tmp_path: Path,
) -> None:
    with fresh_fixture(tmp_path, "gsas-query-purity") as fixture:
        ids = run_workflow(fixture, "application")
        direct_run, direct_run_sql = _capture(
            fixture.engine, lambda: fixture.provenance.get_run_provenance(ids.run_id)
        )
        direct_trace, direct_trace_sql = _capture(
            fixture.engine, lambda: fixture.provenance.trace_claim_to_runs(ids.claim_version_id)
        )
        direct_impact, direct_impact_sql = _capture(
            fixture.engine,
            lambda: fixture.governance_queries.downstream_impact(
                ids.project_id, GovernanceTargetType.ARTIFACT_VERSION, ids.artifact_version_id
            ),
        )

        http_run, http_run_sql = _capture(
            fixture.engine,
            lambda: fixture.client.get(
                f"/v1/runs/{ids.run_id}/provenance", headers=_request_headers(fixture)
            ),
        )
        http_trace, http_trace_sql = _capture(
            fixture.engine,
            lambda: fixture.client.get(
                f"/v1/claim-versions/{ids.claim_version_id}/trace",
                headers=_request_headers(fixture),
            ),
        )
        http_impact, http_impact_sql = _capture(
            fixture.engine,
            lambda: fixture.client.get(
                f"/v1/impact/artifact_version/{ids.artifact_version_id}",
                params={"project_id": str(ids.project_id)},
                headers=_request_headers(fixture),
            ),
        )
        cli_run, cli_run_sql = _capture(
            fixture.engine,
            lambda: _cli_query(fixture, ["run", "provenance", "--run-id", str(ids.run_id)]),
        )
        cli_trace, cli_trace_sql = _capture(
            fixture.engine,
            lambda: _cli_query(
                fixture, ["claim", "trace", "--claim-version-id", str(ids.claim_version_id)]
            ),
        )
        cli_impact, cli_impact_sql = _capture(
            fixture.engine,
            lambda: _cli_query(
                fixture,
                [
                    "impact",
                    "show",
                    "--project-id",
                    str(ids.project_id),
                    "--target-type",
                    "artifact_version",
                    "--target-id",
                    str(ids.artifact_version_id),
                ],
            ),
        )

    assert http_run.status_code == 200
    assert http_trace.status_code == 200
    assert http_impact.status_code == 200
    assert cli_run.exit_code == 0
    assert cli_trace.exit_code == 0
    assert cli_impact.exit_code == 0
    all_sql = (
        direct_run_sql
        + direct_trace_sql
        + direct_impact_sql
        + http_run_sql
        + http_trace_sql
        + http_impact_sql
        + cli_run_sql
        + cli_trace_sql
        + cli_impact_sql
    )
    assert all(statement == "SELECT" for statement in all_sql)
    assert http_run_sql == direct_run_sql
    assert http_trace_sql == direct_trace_sql
    assert http_impact_sql == direct_impact_sql
    assert cli_run_sql == direct_run_sql
    assert cli_trace_sql == direct_trace_sql
    assert cli_impact_sql == direct_impact_sql
    assert http_run.json()["run_id"] == direct_run.run_id
    assert http_trace.json()["claim_version_id"] == direct_trace.claim_version_id
    assert json.loads(cli_run.stdout)["run_id"] == direct_run.run_id
    assert json.loads(cli_trace.stdout)["claim_version_id"] == direct_trace.claim_version_id


def test_scaled_queries_are_stage_bounded_and_preserve_trace_paths(tmp_path: Path) -> None:
    measured: list[tuple[int, int, int, int, int, int]] = []
    for size in (1, 3, 6):
        with fresh_fixture(tmp_path / str(size), f"gsas-scale-{size}") as fixture:
            ids = run_workflow(fixture, "application")
            _claim_id, claim_version_id = _scale_graph(fixture, ids, size)
            run_result, run_sql = _capture(
                fixture.engine,
                lambda ids=ids: fixture.provenance.get_run_provenance(ids.run_id),
            )
            trace_result, trace_sql = _capture(
                fixture.engine,
                lambda claim_version_id=claim_version_id: fixture.provenance.trace_claim_to_runs(
                    claim_version_id
                ),
            )
            impact_result, impact_sql = _capture(
                fixture.engine,
                lambda ids=ids: fixture.governance_queries.downstream_impact(
                    ids.project_id,
                    GovernanceTargetType.ARTIFACT_VERSION,
                    ids.artifact_version_id,
                ),
            )
            assert run_result.closure.complete is True
            assert trace_result.closure.complete is True
            assert len(trace_result.runs) == size
            assert len(trace_result.paths) == size * 2
            assert impact_result
            assert all(statement == "SELECT" for statement in run_sql + trace_sql + impact_sql)
            measured.append(
                (
                    size,
                    len(run_sql),
                    len(trace_sql),
                    len(impact_sql),
                    len(trace_result.paths),
                    len(impact_result),
                )
            )

    small = measured[0]
    for current in measured[1:]:
        assert current[1] <= small[1] + 1
        assert current[2] <= small[2] + 1
        assert current[3] <= small[3] + 1
    assert [item[0] for item in measured] == [1, 3, 6]
    assert [item[4] for item in measured] == [2, 6, 12]
