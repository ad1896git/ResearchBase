from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from tests.integration.pr12_support import postgres_resources
from tests.integration.test_pr09_application import (
    frozen_artifact,
    frozen_dataset,
    frozen_spec,
)
from tests.integration.test_pr12_application import seed_claim, seed_measurement, seed_project

from researchbase.application.commands import (
    ApplicationService,
    AttachRunArtifactInputCommand,
    AttachRunDatasetInputCommand,
    CreateRunCommand,
    FreezeClaimVersionCommand,
    LinkEvidenceCommand,
    RecordMeasurementCommand,
    RecordStatisticalResultCommand,
    StatisticalResultInputCommand,
)
from researchbase.application.provenance_queries import ProvenanceQueryService
from researchbase.domain.run import ArtifactInputRole, DatasetInputRole
from researchbase.foundation.artifact_store import ContentAddressedFilesystemArtifactStore
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.time import FixedClock
from researchbase.persistence.database import create_session_factory
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


def test_statistical_result_all_inputs_preserve_paths_while_runs_are_deduplicated(
    resources: tuple[Callable[[], ApplicationService], Engine],
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
