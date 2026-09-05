from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from tests.application_compat import LegacyApplicationService as ApplicationService
from tests.integration.pr12_support import postgres_resources
from tests.integration.test_pr09_application import (
    frozen_artifact,
    frozen_dataset,
    frozen_spec,
)
from tests.integration.test_pr12_application import seed_claim, seed_measurement, seed_project

from researchbase.application.closure import (
    BatchLookup,
    ProvenanceClosureValidator,
)
from researchbase.application.commands import (
    AttachRunArtifactInputCommand,
    AttachRunDatasetInputCommand,
    CreateArtifactVersionCommand,
    CreateDatasetSnapshotCommand,
    CreateMetricDefinitionCommand,
    CreateRunCommand,
    FinishRunCommand,
    FreezeArtifactVersionCommand,
    FreezeClaimVersionCommand,
    FreezeExperimentSpecCommand,
    FreezeMetricDefinitionCommand,
    LinkEvidenceCommand,
    RecordMeasurementCommand,
    RecordStatisticalResultCommand,
    ReviseClaimCommand,
    ReviseExperimentSpecCommand,
    ReviseMetricDefinitionCommand,
    StartRunCommand,
    StatisticalResultInputCommand,
)
from researchbase.application.provenance_queries import ProvenanceQueryService
from researchbase.domain.artifact import ArtifactId, ArtifactVersionId
from researchbase.domain.experiment import ExperimentSpecId
from researchbase.domain.metric import MetricDefinitionId
from researchbase.domain.run import ArtifactInputRole, DatasetInputRole, RunStatus
from researchbase.foundation.artifact_store import ContentAddressedFilesystemArtifactStore
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.time import FixedClock
from researchbase.persistence.database import create_session_factory
from researchbase.persistence.repositories import (
    SqlAlchemyArtifactVersionRepository,
    SqlAlchemyExperimentSpecRepository,
    SqlAlchemyMeasurementRepository,
    SqlAlchemyRunRepository,
    SqlAlchemyStatisticalResultRepository,
)
from researchbase.persistence.uow import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def resources(
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[tuple[Callable[[], ApplicationService], Engine]]:
    for _baseline_factory, engine in postgres_resources():
        sessions = create_session_factory(engine)
        store = ContentAddressedFilesystemArtifactStore(tmp_path_factory.mktemp("pr13-store"))

        def make_service(
            sessions=sessions,
            store=store,
        ) -> ApplicationService:
            return ApplicationService(
                lambda: SqlAlchemyUnitOfWork(sessions),
                FixedClock(datetime(2026, 8, 30, 0, 0, tzinfo=UTC)),
                store,
            )

        yield (
            make_service,
            engine,
        )


def query_service(engine: Engine) -> ProvenanceQueryService:
    sessions = create_session_factory(engine)
    return ProvenanceQueryService(lambda: SqlAlchemyUnitOfWork(sessions))


def test_missing_roots_use_stable_not_found(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    _, engine = resources
    queries = query_service(engine)

    with pytest.raises(ResearchBaseError) as run_error:
        queries.get_run_provenance(uuid4())
    with pytest.raises(ResearchBaseError) as claim_error:
        queries.trace_claim_to_runs(uuid4())

    assert run_error.value.code is ErrorCode.NOT_FOUND
    assert claim_error.value.code is ErrorCode.NOT_FOUND


def test_direct_measurement_trace_preserves_exact_path_and_run(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, engine = resources
    service = factory()
    _, project_id, actor_context = seed_project(service, "pr13-direct")
    measurement_id = seed_measurement(service, project_id, actor_context, "pr13-direct")
    measurement = service.get_measurement(measurement_id)
    claim, version = seed_claim(service, project_id, actor_context)
    relation = service.link_evidence(
        LinkEvidenceCommand(
            claim.id,
            version.id,
            measurement_id,
            None,
            "contradicts",
            "Unicode：精确限定",
            version.row_version,
            actor_context,
        )
    )
    linked = service.get_current_claim_version(claim.id)
    frozen = service.freeze_claim_version(
        FreezeClaimVersionCommand(claim.id, linked.id, actor_context, linked.row_version)
    )

    trace = query_service(engine).trace_claim_to_runs(frozen.id)

    assert [item.run_id for item in trace.runs] == [str(measurement.run_id)]
    assert len(trace.paths) == 1
    assert trace.paths[0].evidence_relation_id == str(relation.id)
    assert trace.paths[0].relation_type == "contradicts"
    assert trace.paths[0].qualification == "Unicode：精确限定"
    assert trace.paths[0].measurement_id == str(measurement_id)
    assert trace.paths[0].run_id == str(measurement.run_id)
    assert trace.closure.complete is True


def test_run_queries_preserve_exact_inputs_and_execute_selects_only(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, engine = resources
    service = factory()
    _, project_id, actor_context = seed_project(service, "pr13-run-inputs")
    spec_id = frozen_spec(service, project_id, actor_context)
    snapshot = frozen_dataset(service, project_id, actor_context)
    artifact = frozen_artifact(service, project_id, actor_context)
    run = service.create_run(CreateRunCommand(project_id, spec_id, None, actor_context))
    run = service.attach_run_dataset_input(
        AttachRunDatasetInputCommand(
            run.id, snapshot.id, DatasetInputRole.TEST, 2, run.row_version, actor_context
        )
    )
    run = service.attach_run_artifact_input(
        AttachRunArtifactInputCommand(
            run.id, artifact.id, ArtifactInputRole.MODEL, 1, run.row_version, actor_context
        )
    )
    before = (
        engine.connect()
        .execute(
            text("SELECT status, row_version, inputs_sealed_at FROM runs WHERE id=:id"),
            {"id": run.id},
        )
        .one()
    )
    statements: list[str] = []

    def observe(_conn, _cursor, statement, _parameters, _context, _executemany) -> None:
        statements.append(statement.lstrip().split(None, 1)[0].upper())

    event.listen(engine, "before_cursor_execute", observe)
    try:
        queries = query_service(engine)
        inputs = queries.trace_run_to_inputs(run.id)
        provenance = queries.get_run_provenance(run.id)
    finally:
        event.remove(engine, "before_cursor_execute", observe)
    after = (
        engine.connect()
        .execute(
            text("SELECT status, row_version, inputs_sealed_at FROM runs WHERE id=:id"),
            {"id": run.id},
        )
        .one()
    )

    assert inputs.experiment_spec_version_id == str(spec_id)
    assert [(item.target_id, item.role, item.ordinal) for item in inputs.dataset_inputs] == [
        (str(snapshot.id), "test", 2)
    ]
    assert [(item.target_id, item.role, item.ordinal) for item in inputs.artifact_inputs] == [
        (str(artifact.id), "model", 1)
    ]
    assert provenance.dataset_inputs == inputs.dataset_inputs
    assert provenance.artifact_inputs == inputs.artifact_inputs
    assert before == after
    assert statements
    assert set(statements) == {"SELECT"}
    assert len(statements) == 16


def test_statistical_result_all_inputs_preserve_paths_while_runs_are_deduplicated(
    resources: tuple[Callable[[], ApplicationService], Engine],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory, engine = resources
    service = factory()
    _, project_id, actor_context = seed_project(service, "pr13-three-paths")
    first_id = seed_measurement(service, project_id, actor_context, "pr13-three-paths")
    first = service.get_measurement(first_id)
    second = service.record_measurement(
        RecordMeasurementCommand(
            first.run_id,
            first.metric_definition_version_id,
            2.0,
            None,
            "ms",
            {"split": "secondary"},
            actor_context,
        )
    )
    third = service.record_measurement(
        RecordMeasurementCommand(
            first.run_id,
            first.metric_definition_version_id,
            3.0,
            None,
            "ms",
            {"split": "tertiary"},
            actor_context,
        )
    )
    result = service.record_statistical_result(
        RecordStatisticalResultCommand(
            project_id,
            "aggregate",
            {"mean": 2.0},
            {"method": "mean"},
            (
                StatisticalResultInputCommand(third.id, "tertiary", 2),
                StatisticalResultInputCommand(first.id, "primary", 0),
                StatisticalResultInputCommand(second.id, "secondary", 1),
            ),
            actor_context,
        )
    )
    claim, version = seed_claim(service, project_id, actor_context)
    service.link_evidence(
        LinkEvidenceCommand(
            claim.id,
            version.id,
            None,
            result.id,
            "qualifies",
            None,
            version.row_version,
            actor_context,
        )
    )
    current = service.get_current_claim_version(claim.id)
    frozen = service.freeze_claim_version(
        FreezeClaimVersionCommand(claim.id, current.id, actor_context, current.row_version)
    )

    counts = {"claim": 0, "run": 0}
    original_claim = ProvenanceClosureValidator.validate_claim_version_in_uow
    original_run = ProvenanceClosureValidator.validate_run_in_uow

    def count_claim(self, *args, **kwargs):
        counts["claim"] += 1
        return original_claim(self, *args, **kwargs)

    def count_run(self, *args, **kwargs):
        counts["run"] += 1
        return original_run(self, *args, **kwargs)

    monkeypatch.setattr(ProvenanceClosureValidator, "validate_claim_version_in_uow", count_claim)
    monkeypatch.setattr(ProvenanceClosureValidator, "validate_run_in_uow", count_run)
    traces = tuple(query_service(engine).trace_claim_to_runs(frozen.id) for _ in range(3))

    assert traces == (traces[0],) * 3
    assert len(traces[0].runs) == 1
    assert len(traces[0].paths) == 3
    assert [item.statistical_result_input_ordinal for item in traces[0].paths] == [0, 1, 2]
    assert [item.measurement_id for item in traces[0].paths] == [
        str(first.id),
        str(second.id),
        str(third.id),
    ]
    assert counts == {"claim": 3, "run": 3}


def test_draft_claim_with_empty_evidence_returns_empty_trace_and_truthful_closure(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, engine = resources
    service = factory()
    _, project_id, actor_context = seed_project(service, "pr13-empty-draft")
    _, version = seed_claim(service, project_id, actor_context)

    trace = query_service(engine).trace_claim_to_runs(version.id)
    closure = query_service(engine).get_claim_closure_report(version.id)

    assert trace.runs == ()
    assert trace.paths == ()
    assert trace.closure == closure
    assert closure.complete is False
    assert "VERSION_NOT_FROZEN" in {item.code for item in closure.violations}


def test_historical_trace_is_unchanged_after_all_current_state_advances(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, engine = resources
    service = factory()
    _, project_id, actor_context = seed_project(service, "pr13-history")
    spec_v1 = frozen_spec(service, project_id, actor_context)
    snapshot_v1 = frozen_dataset(service, project_id, actor_context)
    artifact_v1 = frozen_artifact(service, project_id, actor_context)
    run = service.create_run(CreateRunCommand(project_id, spec_v1, None, actor_context))
    run = service.attach_run_dataset_input(
        AttachRunDatasetInputCommand(
            run.id, snapshot_v1.id, DatasetInputRole.TEST, 0, run.row_version, actor_context
        )
    )
    run = service.attach_run_artifact_input(
        AttachRunArtifactInputCommand(
            run.id, artifact_v1.id, ArtifactInputRole.MODEL, 0, run.row_version, actor_context
        )
    )
    run = service.start_run(StartRunCommand(run.id, run.row_version, actor_context))
    run = service.finish_run(
        FinishRunCommand(run.id, RunStatus.SUCCEEDED, 0, None, run.row_version, actor_context)
    )
    metric = service.create_metric_definition(
        CreateMetricDefinitionCommand(
            project_id, "historical metric", {"kind": "mean"}, "ms", "mean", actor_context
        )
    )
    assert metric.current_version_id is not None
    metric_v1 = service.freeze_metric_definition(
        FreezeMetricDefinitionCommand(metric.id, metric.current_version_id, actor_context, 1)
    )
    measurement = service.record_measurement(
        RecordMeasurementCommand(
            run.id, metric_v1.id, 1.0, None, "ms", {"split": "test"}, actor_context
        )
    )
    claim, claim_v1 = seed_claim(service, project_id, actor_context)
    service.link_evidence(
        LinkEvidenceCommand(
            claim.id,
            claim_v1.id,
            measurement.id,
            None,
            "supports",
            None,
            claim_v1.row_version,
            actor_context,
        )
    )
    claim_v1 = service.get_current_claim_version(claim.id)
    claim_v1 = service.freeze_claim_version(
        FreezeClaimVersionCommand(claim.id, claim_v1.id, actor_context, claim_v1.row_version)
    )
    queries = query_service(engine)
    trace_before = queries.trace_claim_to_runs(claim_v1.id)
    run_before = queries.get_run_provenance(run.id)

    with engine.connect() as connection:
        spec_identity_id = connection.execute(
            text("SELECT experiment_spec_id FROM experiment_spec_versions WHERE id=:id"),
            {"id": spec_v1},
        ).scalar_one()
    spec_identity = service.get_experiment_spec(ExperimentSpecId(spec_identity_id))
    spec_v2 = service.revise_experiment_spec(
        ReviseExperimentSpecCommand(
            spec_identity.id,
            "later spec",
            "later objective",
            {"steps": ["later"]},
            None,
            None,
            None,
            spec_identity.row_version,
            actor_context,
        )
    )
    service.freeze_experiment_spec(
        FreezeExperimentSpecCommand(spec_identity.id, spec_v2.current_version_id, actor_context, 1)
    )
    service.create_dataset_snapshot(
        CreateDatasetSnapshotCommand(
            snapshot_v1.dataset_id, "b" * 64, {"split": "later"}, None, actor_context
        )
    )
    artifact_v2 = service.create_artifact_version(
        CreateArtifactVersionCommand(
            ArtifactId(artifact_v1.artifact_id),
            b"later artifact",
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
            ArtifactId(artifact_v1.artifact_id),
            ArtifactVersionId(artifact_v2.id),
            actor_context,
            artifact_v2.row_version,
        )
    )
    metric_identity = service.get_metric_definition(MetricDefinitionId(metric.id))
    metric_v2 = service.revise_metric_definition(
        ReviseMetricDefinitionCommand(
            metric_identity.id,
            {"kind": "median"},
            "ms",
            "median",
            metric_identity.row_version,
            actor_context,
        )
    )
    assert metric_v2.current_version_id is not None
    service.freeze_metric_definition(
        FreezeMetricDefinitionCommand(
            metric_identity.id, metric_v2.current_version_id, actor_context, 1
        )
    )
    current_claim = service.get_claim(claim.id)
    service.revise_claim(
        ReviseClaimCommand(
            claim.id,
            "later claim",
            {"population": "later"},
            None,
            current_claim.row_version,
            actor_context,
        )
    )

    assert queries.trace_claim_to_runs(claim_v1.id) == trace_before
    assert queries.get_run_provenance(run.id) == run_before
    assert trace_before.paths[0].metric_definition_version_id == str(metric_v1.id)
    assert run_before.experiment_spec_version_id == str(spec_v1)
    assert run_before.dataset_inputs[0].target_id == str(snapshot_v1.id)
    assert run_before.artifact_inputs[0].target_id == str(artifact_v1.id)


def test_trace_isolated_by_exact_cross_project_paths(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, engine = resources
    service = factory()
    traces = []
    for label in ("pr13-project-a", "pr13-project-b"):
        _, project_id, actor_context = seed_project(service, label)
        measurement_id = seed_measurement(service, project_id, actor_context, label)
        claim, version = seed_claim(service, project_id, actor_context)
        service.link_evidence(
            LinkEvidenceCommand(
                claim.id,
                version.id,
                measurement_id,
                None,
                "context",
                "same role names",
                version.row_version,
                actor_context,
            )
        )
        version = service.get_current_claim_version(claim.id)
        version = service.freeze_claim_version(
            FreezeClaimVersionCommand(claim.id, version.id, actor_context, version.row_version)
        )
        traces.append(query_service(engine).trace_claim_to_runs(version.id))

    assert traces[0].project_id != traces[1].project_id
    assert {item.run_id for item in traces[0].runs}.isdisjoint(
        {item.run_id for item in traces[1].runs}
    )


def test_trace_sql_and_closure_calls_are_bounded_by_stages_and_unique_runs(
    resources: tuple[Callable[[], ApplicationService], Engine],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory, engine = resources
    original_claim = ProvenanceClosureValidator.validate_claim_version_in_uow
    original_run = ProvenanceClosureValidator.validate_run_in_uow
    calls = {"claim": 0, "run": 0}

    def count_claim(self, *args, **kwargs):
        calls["claim"] += 1
        return original_claim(self, *args, **kwargs)

    def count_run(self, *args, **kwargs):
        calls["run"] += 1
        return original_run(self, *args, **kwargs)

    monkeypatch.setattr(ProvenanceClosureValidator, "validate_claim_version_in_uow", count_claim)
    monkeypatch.setattr(ProvenanceClosureValidator, "validate_run_in_uow", count_run)
    observations: list[tuple[int, int, int, int]] = []

    for path_count, run_count in ((2, 1), (3, 1), (12, 9), (24, 15)):
        service = factory()
        _, project_id, actor_context = seed_project(
            service, f"pr13r-scale-{path_count}-{run_count}"
        )
        measurements = [
            service.get_measurement(
                seed_measurement(service, project_id, actor_context, f"scale-{path_count}-{i}")
            )
            for i in range(run_count)
        ]
        first = measurements[0]
        for index in range(run_count, path_count):
            measurements.append(
                service.record_measurement(
                    RecordMeasurementCommand(
                        first.run_id,
                        first.metric_definition_version_id,
                        float(index + 1),
                        None,
                        "ms",
                        {"scale_index": index},
                        actor_context,
                    )
                )
            )
        result = service.record_statistical_result(
            RecordStatisticalResultCommand(
                project_id,
                "scale",
                {"count": path_count - 1},
                {"method": "identity"},
                tuple(
                    StatisticalResultInputCommand(item.id, f"input-{index}", index)
                    for index, item in enumerate(measurements[1:])
                ),
                actor_context,
            )
        )
        claim, version = seed_claim(service, project_id, actor_context)
        service.link_evidence(
            LinkEvidenceCommand(
                claim.id,
                version.id,
                first.id,
                None,
                "supports",
                "direct",
                version.row_version,
                actor_context,
            )
        )
        current = service.get_current_claim_version(claim.id)
        service.link_evidence(
            LinkEvidenceCommand(
                claim.id,
                current.id,
                None,
                result.id,
                "qualifies",
                "aggregate",
                current.row_version,
                actor_context,
            )
        )
        current = service.get_current_claim_version(claim.id)
        frozen = service.freeze_claim_version(
            FreezeClaimVersionCommand(claim.id, current.id, actor_context, current.row_version)
        )
        sql: list[str] = []

        def observe(
            _conn,
            _cursor,
            statement,
            _parameters,
            _context,
            _executemany,
            target=sql,
        ) -> None:
            target.append(statement.lstrip().split(None, 1)[0].upper())

        before = calls.copy()
        event.listen(engine, "before_cursor_execute", observe)
        try:
            trace = query_service(engine).trace_claim_to_runs(frozen.id)
        finally:
            event.remove(engine, "before_cursor_execute", observe)
        observations.append(
            (
                len(sql),
                calls["claim"] - before["claim"],
                calls["run"] - before["run"],
                len(trace.paths),
            )
        )
        assert len(trace.runs) == run_count
        assert set(sql) == {"SELECT"}

    assert observations == [
        (15, 1, 1, 2),
        (15, 1, 1, 3),
        (15, 1, 9, 12),
        (15, 1, 15, 24),
    ]


@pytest.mark.parametrize("missing_count", [1, 2])
def test_trace_missing_measurements_are_cache_only_and_stage_bounded(
    resources: tuple[Callable[[], ApplicationService], Engine],
    monkeypatch: pytest.MonkeyPatch,
    missing_count: int,
) -> None:
    factory, engine = resources
    service = factory()
    _, project_id, actor_context = seed_project(service, f"pr13r2-missing-{missing_count}")
    first = service.get_measurement(
        seed_measurement(service, project_id, actor_context, f"missing-{missing_count}-0")
    )
    measurements = [first]
    for index in range(1, 4):
        measurements.append(
            service.record_measurement(
                RecordMeasurementCommand(
                    first.run_id,
                    first.metric_definition_version_id,
                    float(index + 1),
                    None,
                    "ms",
                    {"missing_index": index},
                    actor_context,
                )
            )
        )
    result = service.record_statistical_result(
        RecordStatisticalResultCommand(
            project_id,
            "missing-cache",
            {"count": 4},
            {"method": "identity"},
            tuple(
                StatisticalResultInputCommand(item.id, f"input-{index}", index)
                for index, item in enumerate(measurements)
            ),
            actor_context,
        )
    )
    claim, version = seed_claim(service, project_id, actor_context)
    service.link_evidence(
        LinkEvidenceCommand(
            claim.id,
            version.id,
            None,
            result.id,
            "supports",
            None,
            version.row_version,
            actor_context,
        )
    )
    current = service.get_current_claim_version(claim.id)
    frozen = service.freeze_claim_version(
        FreezeClaimVersionCommand(claim.id, current.id, actor_context, current.row_version)
    )
    missing_ids = {item.id for item in measurements[-missing_count:]}
    original_many = SqlAlchemyMeasurementRepository.get_many
    original_by_runs = SqlAlchemyMeasurementRepository.list_by_runs

    def omit_from_many(self, ids):
        return [item for item in original_many(self, ids) if item.id not in missing_ids]

    def omit_from_runs(self, ids):
        return [item for item in original_by_runs(self, ids) if item.id not in missing_ids]

    def forbidden_get(self, measurement_id):
        raise AssertionError(f"per-ID fallback attempted for {measurement_id}")

    monkeypatch.setattr(SqlAlchemyMeasurementRepository, "get_many", omit_from_many)
    monkeypatch.setattr(SqlAlchemyMeasurementRepository, "list_by_runs", omit_from_runs)
    monkeypatch.setattr(SqlAlchemyMeasurementRepository, "get", forbidden_get)
    statements: list[str] = []

    def observe(_conn, _cursor, statement, _parameters, _context, _executemany) -> None:
        statements.append(statement.lstrip().split(None, 1)[0].upper())

    event.listen(engine, "before_cursor_execute", observe)
    try:
        trace = query_service(engine).trace_claim_to_runs(frozen.id)
    finally:
        event.remove(engine, "before_cursor_execute", observe)

    missing_violations = [
        item
        for item in trace.closure.violations
        if item.object_type == "Measurement" and item.code == ErrorCode.NOT_FOUND.value
    ]
    assert len(statements) == 15
    assert set(statements) == {"SELECT"}
    assert {item.object_id for item in missing_violations} == {str(item) for item in missing_ids}
    assert all(item.path[-1] == "measurement" for item in missing_violations)


def test_trace_missing_result_and_run_input_descendants_never_fall_back(
    resources: tuple[Callable[[], ApplicationService], Engine],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory, engine = resources
    service = factory()
    _, project_id, actor_context = seed_project(service, "pr13r2-missing-descendants")
    measurement_id = seed_measurement(service, project_id, actor_context, "missing-descendants")
    measurement = service.get_measurement(measurement_id)
    result = service.record_statistical_result(
        RecordStatisticalResultCommand(
            project_id,
            "missing-result",
            {"value": 1},
            {"method": "identity"},
            (StatisticalResultInputCommand(measurement.id, "primary", 0),),
            actor_context,
        )
    )
    claim, version = seed_claim(service, project_id, actor_context)
    service.link_evidence(
        LinkEvidenceCommand(
            claim.id,
            version.id,
            None,
            result.id,
            "supports",
            None,
            version.row_version,
            actor_context,
        )
    )
    current = service.get_current_claim_version(claim.id)
    frozen = service.freeze_claim_version(
        FreezeClaimVersionCommand(claim.id, current.id, actor_context, current.row_version)
    )

    monkeypatch.setattr(SqlAlchemyStatisticalResultRepository, "get_many", lambda self, ids: [])
    monkeypatch.setattr(
        SqlAlchemyStatisticalResultRepository,
        "get",
        lambda self, result_id: (_ for _ in ()).throw(
            AssertionError(f"result fallback attempted for {result_id}")
        ),
    )
    trace = query_service(engine).trace_claim_to_runs(frozen.id)
    assert [(item.code, item.object_type, item.object_id) for item in trace.closure.violations] == [
        (ErrorCode.NOT_FOUND.value, "StatisticalResult", str(result.id))
    ]

    run = service.get_run(measurement.run_id)
    artifact = frozen_artifact(service, project_id, actor_context)
    draft_run = service.create_run(
        CreateRunCommand(project_id, run.experiment_spec_version_id, None, actor_context)
    )
    draft_run = service.attach_run_artifact_input(
        AttachRunArtifactInputCommand(
            draft_run.id,
            artifact.id,
            ArtifactInputRole.MODEL,
            0,
            draft_run.row_version,
            actor_context,
        )
    )
    monkeypatch.setattr(SqlAlchemyArtifactVersionRepository, "get_many", lambda self, ids: [])
    monkeypatch.setattr(
        SqlAlchemyArtifactVersionRepository,
        "get",
        lambda self, version_id: (_ for _ in ()).throw(
            AssertionError(f"artifact fallback attempted for {version_id}")
        ),
    )
    run_trace = query_service(engine).get_run_provenance(draft_run.id)
    assert any(
        item.code == ErrorCode.NOT_FOUND.value
        and item.object_type == "ArtifactVersion"
        and item.object_id == str(artifact.id)
        for item in run_trace.closure.violations
    )


def test_trace_never_requested_reference_is_a_stable_context_violation(
    resources: tuple[Callable[[], ApplicationService], Engine],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory, engine = resources
    service = factory()
    _, project_id, actor_context = seed_project(service, "pr13r2-never-requested")
    measurement_id = seed_measurement(service, project_id, actor_context, "never-requested")
    claim, version = seed_claim(service, project_id, actor_context)
    service.link_evidence(
        LinkEvidenceCommand(
            claim.id,
            version.id,
            measurement_id,
            None,
            "supports",
            None,
            version.row_version,
            actor_context,
        )
    )
    current = service.get_current_claim_version(claim.id)
    frozen = service.freeze_claim_version(
        FreezeClaimVersionCommand(claim.id, current.id, actor_context, current.row_version)
    )
    original_load = ProvenanceQueryService._load_claim_context

    def omit_membership(self, uow, relations):
        context = original_load(self, uow, relations)
        key = next(UUID(str(item.measurement_id)) for item in relations if item.measurement_id)
        context.measurements = BatchLookup(
            values={
                item_id: item
                for item_id, item in context.measurements.values.items()
                if item_id != key
            },
            requested_ids=frozenset(
                item_id for item_id in context.measurements.requested_ids if item_id != key
            ),
        )
        return context

    monkeypatch.setattr(ProvenanceQueryService, "_load_claim_context", omit_membership)
    monkeypatch.setattr(
        SqlAlchemyMeasurementRepository,
        "get",
        lambda self, item_id: (_ for _ in ()).throw(
            AssertionError(f"never-requested fallback attempted for {item_id}")
        ),
    )

    trace = query_service(engine).trace_claim_to_runs(frozen.id)

    observed = [
        (item.code, item.object_type, item.object_id, item.path[-1])
        for item in trace.closure.violations
    ]
    assert observed == [
        ("PROVENANCE_CONTEXT_INCOMPLETE", "Measurement", str(measurement_id), "measurement")
    ]


def test_run_requested_missing_spec_is_deterministic_and_cache_only(
    resources: tuple[Callable[[], ApplicationService], Engine],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory, engine = resources
    service = factory()
    _, project_id, actor_context = seed_project(service, "pr13r3-missing-spec")
    measurement = service.get_measurement(
        seed_measurement(service, project_id, actor_context, "pr13r3-missing-spec")
    )
    run = service.get_run(measurement.run_id)
    fallback_calls = {"spec": 0, "dataset_inputs": 0, "artifact_inputs": 0}

    monkeypatch.setattr(SqlAlchemyExperimentSpecRepository, "get_versions", lambda self, ids: [])

    def forbidden_spec_get(self, version_id):
        fallback_calls["spec"] += 1
        raise AssertionError(f"spec fallback attempted for {version_id}")

    def forbidden_dataset_inputs(self, run_id):
        fallback_calls["dataset_inputs"] += 1
        raise AssertionError(f"dataset-input fallback attempted for {run_id}")

    def forbidden_artifact_inputs(self, run_id):
        fallback_calls["artifact_inputs"] += 1
        raise AssertionError(f"artifact-input fallback attempted for {run_id}")

    monkeypatch.setattr(SqlAlchemyExperimentSpecRepository, "get_version", forbidden_spec_get)
    monkeypatch.setattr(SqlAlchemyRunRepository, "list_dataset_inputs", forbidden_dataset_inputs)
    monkeypatch.setattr(SqlAlchemyRunRepository, "list_artifact_inputs", forbidden_artifact_inputs)

    select_counts: list[int] = []
    observed = []
    for _ in range(3):
        statements: list[str] = []

        def observe(
            _conn,
            _cursor,
            statement,
            _parameters,
            _context,
            _executemany,
            statement_log=statements,
        ) -> None:
            statement_log.append(statement.lstrip().split(None, 1)[0].upper())

        event.listen(engine, "before_cursor_execute", observe)
        try:
            observed.append(query_service(engine).get_run_provenance(run.id).closure)
        finally:
            event.remove(engine, "before_cursor_execute", observe)
        assert set(statements) == {"SELECT"}
        select_counts.append(len(statements))

    assert observed[0] == observed[1] == observed[2]
    assert observed[0].complete is False
    assert observed[0].visited_count == 1
    assert [
        (
            item.code,
            item.object_type,
            item.object_id,
            item.path,
            item.message,
        )
        for item in observed[0].violations
    ] == [
        (
            ErrorCode.NOT_FOUND.value,
            "ExperimentSpecVersion",
            str(run.experiment_spec_version_id),
            ("run", "experiment_spec_version"),
            "experiment spec version was not found",
        )
    ]
    assert fallback_calls == {"spec": 0, "dataset_inputs": 0, "artifact_inputs": 0}
    assert select_counts == [6, 6, 6]


def test_run_never_requested_spec_is_deterministic_and_non_contextual_still_works(
    resources: tuple[Callable[[], ApplicationService], Engine],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory, engine = resources
    service = factory()
    _, project_id, actor_context = seed_project(service, "pr13r3-never-requested-spec")
    measurement = service.get_measurement(
        seed_measurement(service, project_id, actor_context, "pr13r3-never-requested-spec")
    )
    run = service.get_run(measurement.run_id)
    sessions = create_session_factory(engine)
    validator = ProvenanceClosureValidator(lambda: SqlAlchemyUnitOfWork(sessions))

    repository_backed = validator.validate_run(run.id)
    assert repository_backed.complete is True

    original_load = ProvenanceQueryService._load_run_context

    def omit_spec_membership(uow, run_ids):
        context = original_load(uow, run_ids)
        context.spec_versions = BatchLookup()
        return context

    fallback_calls = {"spec": 0}

    def forbidden_spec_get(self, version_id):
        fallback_calls["spec"] += 1
        raise AssertionError(f"spec fallback attempted for {version_id}")

    monkeypatch.setattr(
        ProvenanceQueryService,
        "_load_run_context",
        staticmethod(omit_spec_membership),
    )
    monkeypatch.setattr(SqlAlchemyExperimentSpecRepository, "get_version", forbidden_spec_get)

    observed = [query_service(engine).get_run_provenance(run.id).closure for _ in range(3)]

    assert observed[0] == observed[1] == observed[2]
    assert observed[0].complete is False
    assert observed[0].visited_count == 1
    assert [
        (item.code, item.object_type, item.object_id, item.path, item.message)
        for item in observed[0].violations
    ] == [
        (
            "PROVENANCE_CONTEXT_INCOMPLETE",
            "ExperimentSpecVersion",
            str(run.experiment_spec_version_id),
            ("run", "experiment_spec_version"),
            "ExperimentSpecVersion was referenced but never requested by the closure batch",
        )
    ]
    assert fallback_calls == {"spec": 0}
