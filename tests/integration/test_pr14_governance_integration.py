from __future__ import annotations

# Raw SQL is intentionally kept visibly exact for schema-contract tests.
# ruff: noqa: E501
import os
import threading
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError

from researchbase.application.governance import (
    CreateAuditFindingCommand,
    CreateCorrectionRecordCommand,
    CreateImpactAssessmentCommand,
    GovernanceService,
    ProposedImpactTarget,
    TargetResolverRegistry,
    TransitionAuditFindingCommand,
)
from researchbase.application.governance_queries import GovernanceQueryService, ValidityState
from researchbase.application.provenance_queries import ProvenanceQueryService
from researchbase.domain.governance import GovernanceTargetType
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.execution_context import ExecutionContext
from researchbase.foundation.hashing import sha256_canonical_json
from researchbase.foundation.time import FixedClock
from researchbase.persistence.database import create_database_engine, create_session_factory
from researchbase.persistence.governance_repository import SqlAlchemyGovernanceRepository
from researchbase.persistence.uow import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def engine() -> Iterator[Engine]:
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL is not set; run against PostgreSQL")
    value = create_database_engine()
    try:
        yield value
    finally:
        value.dispose()


def _seed_graph(engine: Engine) -> dict[str, UUID]:
    ids = {
        name: uuid4()
        for name in (
            "actor",
            "project",
            "spec",
            "spec_version",
            "artifact",
            "artifact_version",
            "dataset",
            "snapshot",
            "run",
            "metric",
            "metric_version",
            "measurement",
            "stat",
            "claim",
            "claim_version",
            "evidence_direct",
            "evidence_stat",
        )
    }
    now = datetime(2026, 8, 30, tzinfo=UTC)
    measurement_hash = str(
        sha256_canonical_json(
            {
                "run_id": str(ids["run"]),
                "metric_definition_version_id": str(ids["metric_version"]),
                "numeric_value": 1.0,
                "structured_value": None,
                "unit": None,
                "evaluation_scope": None,
            }
        )
    )
    statistical_result_hash = str(
        sha256_canonical_json(
            {
                "analysis_type": "mean",
                "result_payload": {},
                "analysis_definition": {},
            }
        )
    )
    with engine.begin() as c:
        c.execute(
            text(
                "INSERT INTO actors(id,actor_type,display_name,created_at) VALUES (:id,'human','auditor',:now)"
            ),
            {"id": ids["actor"], "now": now},
        )
        c.execute(
            text(
                "INSERT INTO projects(id,name,created_by,created_at) VALUES (:id,'PR14',:actor,:now)"
            ),
            {"id": ids["project"], "actor": ids["actor"], "now": now},
        )
        c.execute(
            text(
                "INSERT INTO experiment_specs(id,project_id,created_by,created_at) VALUES (:id,:project,:actor,:now)"
            ),
            {"id": ids["spec"], "project": ids["project"], "actor": ids["actor"], "now": now},
        )
        c.execute(
            text(
                "INSERT INTO experiment_spec_versions(id,experiment_spec_id,version_number,status,title,objective,protocol,content_hash,created_by,created_at,frozen_at) VALUES (:id,:parent,1,'FROZEN','t','o','{\"steps\":[\"execute\"]}',:hash,:actor,:now,:now)"
            ),
            {
                "id": ids["spec_version"],
                "parent": ids["spec"],
                "hash": "1" * 64,
                "actor": ids["actor"],
                "now": now,
            },
        )
        c.execute(
            text(
                "INSERT INTO artifacts(id,project_id,artifact_type,name,created_by,created_at) VALUES (:id,:project,'code','A1',:actor,:now)"
            ),
            {"id": ids["artifact"], "project": ids["project"], "actor": ids["actor"], "now": now},
        )
        c.execute(
            text(
                "INSERT INTO artifact_versions(id,artifact_id,version_number,status,content_hash,created_by,created_at,frozen_at) VALUES (:id,:parent,1,'FROZEN',:hash,:actor,:now,:now)"
            ),
            {
                "id": ids["artifact_version"],
                "parent": ids["artifact"],
                "hash": "2" * 64,
                "actor": ids["actor"],
                "now": now,
            },
        )
        c.execute(
            text(
                "INSERT INTO datasets(id,project_id,name,created_by,created_at) VALUES (:id,:project,'D1',:actor,:now)"
            ),
            {"id": ids["dataset"], "project": ids["project"], "actor": ids["actor"], "now": now},
        )
        c.execute(
            text(
                "INSERT INTO dataset_snapshots(id,dataset_id,manifest_hash,selection_definition,content_hash,created_by,created_at) VALUES (:id,:parent,:manifest,'{}',:hash,:actor,:now)"
            ),
            {
                "id": ids["snapshot"],
                "parent": ids["dataset"],
                "manifest": "3" * 64,
                "hash": "4" * 64,
                "actor": ids["actor"],
                "now": now,
            },
        )
        c.execute(
            text(
                "INSERT INTO runs(id,project_id,experiment_spec_version_id,status,created_by,created_at) VALUES (:id,:project,:spec,'PLANNED',:actor,:now)"
            ),
            {
                "id": ids["run"],
                "project": ids["project"],
                "spec": ids["spec_version"],
                "actor": ids["actor"],
                "now": now,
            },
        )
        c.execute(
            text(
                "INSERT INTO run_artifact_inputs(run_id,artifact_version_id,role) VALUES (:run,:target,'source_code')"
            ),
            {"run": ids["run"], "target": ids["artifact_version"]},
        )
        c.execute(
            text(
                "INSERT INTO run_dataset_inputs(run_id,dataset_snapshot_id,role) VALUES (:run,:target,'test')"
            ),
            {"run": ids["run"], "target": ids["snapshot"]},
        )
        c.execute(
            text(
                "UPDATE runs SET status='RUNNING', inputs_sealed_at=:now, "
                "started_at=:now, row_version=2 WHERE id=:id"
            ),
            {"id": ids["run"], "now": now},
        )
        c.execute(
            text(
                "UPDATE runs SET status='SUCCEEDED', finished_at=:now, exit_code=0, "
                "row_version=3 WHERE id=:id"
            ),
            {"id": ids["run"], "now": now},
        )
        c.execute(
            text(
                "INSERT INTO metric_definitions(id,project_id,name,created_by,created_at) VALUES (:id,:project,'m',:actor,:now)"
            ),
            {"id": ids["metric"], "project": ids["project"], "actor": ids["actor"], "now": now},
        )
        c.execute(
            text(
                "INSERT INTO metric_definition_versions(id,metric_definition_id,version_number,status,definition,content_hash,created_by,created_at,frozen_at) VALUES (:id,:parent,1,'FROZEN','{}',:hash,:actor,:now,:now)"
            ),
            {
                "id": ids["metric_version"],
                "parent": ids["metric"],
                "hash": "5" * 64,
                "actor": ids["actor"],
                "now": now,
            },
        )
        c.execute(
            text(
                "INSERT INTO measurements(id,run_id,metric_definition_version_id,numeric_value,content_hash,created_by,created_at) VALUES (:id,:run,:metric,1.0,:hash,:actor,:now)"
            ),
            {
                "id": ids["measurement"],
                "run": ids["run"],
                "metric": ids["metric_version"],
                "hash": measurement_hash,
                "actor": ids["actor"],
                "now": now,
            },
        )
        c.execute(
            text(
                "INSERT INTO statistical_results(id,project_id,analysis_type,result_payload,analysis_definition,content_hash,created_by,created_at) VALUES (:id,:project,'mean','{}','{}',:hash,:actor,:now)"
            ),
            {
                "id": ids["stat"],
                "project": ids["project"],
                "hash": statistical_result_hash,
                "actor": ids["actor"],
                "now": now,
            },
        )
        c.execute(
            text(
                "INSERT INTO statistical_result_inputs(statistical_result_id,measurement_id,input_role) VALUES (:stat,:measurement,'input')"
            ),
            {"stat": ids["stat"], "measurement": ids["measurement"]},
        )
        c.execute(
            text(
                "INSERT INTO claims(id,project_id,created_by,created_at) VALUES (:id,:project,:actor,:now)"
            ),
            {"id": ids["claim"], "project": ids["project"], "actor": ids["actor"], "now": now},
        )
        c.execute(
            text(
                "INSERT INTO claim_versions(id,claim_id,version_number,status,statement,created_by,created_at) VALUES (:id,:parent,1,'DRAFT','claim',:actor,:now)"
            ),
            {
                "id": ids["claim_version"],
                "parent": ids["claim"],
                "actor": ids["actor"],
                "now": now,
            },
        )
        c.execute(
            text(
                "INSERT INTO evidence_relations(id,claim_version_id,measurement_id,relation_type,created_by,created_at) VALUES (:id,:claim,:measurement,'supports',:actor,:now)"
            ),
            {
                "id": ids["evidence_direct"],
                "claim": ids["claim_version"],
                "measurement": ids["measurement"],
                "actor": ids["actor"],
                "now": now,
            },
        )
        c.execute(
            text(
                "INSERT INTO evidence_relations(id,claim_version_id,statistical_result_id,relation_type,created_by,created_at) VALUES (:id,:claim,:stat,'supports',:actor,:now)"
            ),
            {
                "id": ids["evidence_stat"],
                "claim": ids["claim_version"],
                "stat": ids["stat"],
                "actor": ids["actor"],
                "now": now,
            },
        )
        c.execute(
            text(
                "UPDATE claim_versions SET status='FROZEN',support_set_hash=:support_hash,"
                "content_hash=:hash,frozen_at=:now,row_version=2 WHERE id=:id"
            ),
            {
                "id": ids["claim_version"],
                "support_hash": "9" * 64,
                "hash": "8" * 64,
                "now": now,
            },
        )
    return ids


def _services(engine: Engine) -> tuple[GovernanceService, GovernanceQueryService]:
    sessions = create_session_factory(engine)

    def factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(sessions)

    return (
        GovernanceService(factory, FixedClock(datetime(2026, 8, 30, 1, tzinfo=UTC))),
        GovernanceQueryService(factory),
    )


def _provenance_service(engine: Engine) -> ProvenanceQueryService:
    sessions = create_session_factory(engine)

    def factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(sessions)

    return ProvenanceQueryService(factory)


def _context(actor_id: UUID) -> ExecutionContext:
    return ExecutionContext(actor_id=actor_id, request_id=uuid4(), client_type="test")


def test_closed_resolver_commands_downstream_validity_and_history(engine: Engine) -> None:
    ids = _seed_graph(engine)
    service, queries = _services(engine)
    context = _context(ids["actor"])
    assert TargetResolverRegistry().supported_types == set(GovernanceTargetType)

    finding = service.create_audit_finding(
        CreateAuditFindingCommand(
            ids["project"],
            "code_bug",
            "major",
            "A1 bug",
            "incorrect implementation",
            "artifact_version",
            ids["artifact_version"],
            context,
        )
    )
    assert str(finding.target_content_hash) == "2" * 64
    paths = queries.downstream_impact(ids["project"], "artifact_version", ids["artifact_version"])
    assert any(item.target_type.value == "run" and item.target_id == ids["run"] for item in paths)
    assert any(
        item.target_type.value == "statistical_result" and item.target_id == ids["stat"]
        for item in paths
    )
    claim = next(item for item in paths if item.target_id == ids["claim_version"])
    assert len(claim.paths) == 2
    assert {path.statistical_result_id for path in claim.paths} == {None, ids["stat"]}
    assert {path.evidence_relation_id for path in claim.paths} == {
        ids["evidence_direct"],
        ids["evidence_stat"],
    }
    assert {path.statistical_input_role for path in claim.paths} == {None, "input"}
    assert {path.statistical_input_ordinal for path in claim.paths} == {None, 0}

    assessment = service.create_impact_assessment(
        CreateImpactAssessmentCommand(
            ids["project"],
            finding.id,
            {"basis": "code review"},
            "stale",
            (ProposedImpactTarget("claim_version", ids["claim_version"], "stale"),),
            context,
        )
    )
    projection = queries.validity_projection(ids["project"], "claim_version", ids["claim_version"])
    assert projection.state is ValidityState.STALE
    assert projection.target_type is GovernanceTargetType.CLAIM_VERSION
    assert projection.target_id == ids["claim_version"]
    assert projection.finding_ids == (finding.id,)
    assert projection.assessment_ids == (assessment.id,)

    before = (
        engine.connect()
        .execute(
            text("SELECT content_hash FROM claim_versions WHERE id=:id"),
            {"id": ids["claim_version"]},
        )
        .scalar_one()
    )
    correction = service.create_correction_record(
        CreateCorrectionRecordCommand(
            ids["project"],
            "claim_version",
            ids["claim_version"],
            "factual",
            {"statement": "corrected in new history"},
            "source corrected",
            context,
        )
    )
    after = (
        engine.connect()
        .execute(
            text("SELECT content_hash FROM claim_versions WHERE id=:id"),
            {"id": ids["claim_version"]},
        )
        .scalar_one()
    )
    assert before == after == "8" * 64
    assert (
        correction.id
        in queries.validity_projection(
            ids["project"], "claim_version", ids["claim_version"]
        ).correction_ids
    )

    with pytest.raises(ResearchBaseError) as missing:
        service.create_audit_finding(
            CreateAuditFindingCommand(
                ids["project"], "x", "info", "x", "x", "run", uuid4(), context
            )
        )
    assert missing.value.code is ErrorCode.NOT_FOUND
    with pytest.raises(ResearchBaseError) as unsupported:
        service.create_audit_finding(
            CreateAuditFindingCommand(
                ids["project"], "x", "info", "x", "x", "project", ids["project"], context
            )
        )
    assert unsupported.value.code is ErrorCode.VALIDATION_ERROR


def test_lifecycle_stale_writer_and_database_immutability(engine: Engine) -> None:
    ids = _seed_graph(engine)
    service, _ = _services(engine)
    context = _context(ids["actor"])
    finding = service.create_audit_finding(
        CreateAuditFindingCommand(
            ids["project"], "audit", "minor", "finding", "detail", "run", ids["run"], context
        )
    )
    confirmed = service.transition_audit_finding(
        TransitionAuditFindingCommand(finding.id, "confirmed", 1, context)
    )
    assert confirmed.row_version == 2
    with pytest.raises(ResearchBaseError) as stale:
        service.transition_audit_finding(
            TransitionAuditFindingCommand(finding.id, "dismissed", 1, context)
        )
    assert stale.value.code is ErrorCode.CONCURRENT_MODIFICATION
    assessment = service.create_impact_assessment(
        CreateImpactAssessmentCommand(
            ids["project"],
            finding.id,
            {},
            "unknown",
            (ProposedImpactTarget("run", ids["run"], "requires_review"),),
            context,
        )
    )
    correction = service.create_correction_record(
        CreateCorrectionRecordCommand(
            ids["project"], "run", ids["run"], "other", {}, "note", context
        )
    )
    for statement, values in (
        (
            "UPDATE impact_assessments SET conclusion='stale' WHERE id=:id",
            {"id": assessment.id},
        ),
        ("UPDATE correction_records SET reason='changed' WHERE id=:id", {"id": correction.id}),
        (
            "UPDATE impact_targets SET impact_kind='stale' WHERE impact_assessment_id=:id",
            {"id": assessment.id},
        ),
    ):
        with engine.begin() as c:
            with pytest.raises(DBAPIError):
                c.execute(text(statement), values)


def test_real_concurrent_stale_finding_writers_have_one_winner(
    engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    ids = _seed_graph(engine)
    service, queries = _services(engine)
    context = _context(ids["actor"])
    finding = service.create_audit_finding(
        CreateAuditFindingCommand(
            ids["project"], "concurrency", "minor", "finding", "detail", "run", ids["run"], context
        )
    )

    original_get = SqlAlchemyGovernanceRepository.get_audit_finding
    barrier = threading.Barrier(2)
    counter_lock = threading.Lock()
    synchronized_reads = 0

    def synchronized_get(repository: object, finding_id: UUID) -> object:
        nonlocal synchronized_reads
        result = original_get(repository, finding_id)  # type: ignore[arg-type]
        with counter_lock:
            synchronized_reads += 1
            should_wait = finding_id == finding.id and synchronized_reads <= 2
        if should_wait:
            barrier.wait(timeout=10)
        return result

    monkeypatch.setattr(SqlAlchemyGovernanceRepository, "get_audit_finding", synchronized_get)

    def transition(status: str) -> object:
        try:
            return service.transition_audit_finding(
                TransitionAuditFindingCommand(finding.id, status, 1, context)
            )
        except ResearchBaseError as error:
            return error

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(executor.map(transition, ("confirmed", "dismissed")))

    assert sum(isinstance(result, ResearchBaseError) for result in results) == 1
    errors = [result for result in results if isinstance(result, ResearchBaseError)]
    assert errors[0].code is ErrorCode.CONCURRENT_MODIFICATION
    winners = [result for result in results if not isinstance(result, ResearchBaseError)]
    assert len(winners) == 1
    final = queries.get_audit_finding(finding.id)
    assert final is not None
    assert final.row_version == 2
    assert final.status.value in {"confirmed", "dismissed"}


def test_dataset_downstream_path_and_validity_precedence_and_dismissal(
    engine: Engine,
) -> None:
    ids = _seed_graph(engine)
    service, queries = _services(engine)
    context = _context(ids["actor"])
    finding = service.create_audit_finding(
        CreateAuditFindingCommand(
            ids["project"],
            "dataset_issue",
            "major",
            "dataset",
            "dataset issue",
            "dataset_snapshot",
            ids["snapshot"],
            context,
        )
    )
    paths = queries.downstream_impact(ids["project"], "dataset_snapshot", ids["snapshot"])
    assert {item.target_id for item in paths} >= {
        ids["run"],
        ids["measurement"],
        ids["stat"],
        ids["claim_version"],
    }
    claim = next(item for item in paths if item.target_id == ids["claim_version"])
    assert any(path.statistical_result_id == ids["stat"] for path in claim.paths)

    stale = service.create_impact_assessment(
        CreateImpactAssessmentCommand(
            ids["project"],
            finding.id,
            {"source": "dataset"},
            "stale",
            (ProposedImpactTarget("claim_version", ids["claim_version"], "stale"),),
            context,
        )
    )
    invalid = service.create_impact_assessment(
        CreateImpactAssessmentCommand(
            ids["project"],
            finding.id,
            {"source": "reassessment"},
            "invalid",
            (ProposedImpactTarget("claim_version", ids["claim_version"], "invalid"),),
            context,
        )
    )
    projection = queries.validity_projection(ids["project"], "claim_version", ids["claim_version"])
    assert projection.state is ValidityState.INVALID
    assert projection.assessment_ids == tuple(sorted((stale.id, invalid.id), key=str))
    service.transition_audit_finding(
        TransitionAuditFindingCommand(finding.id, "confirmed", 1, context)
    )
    service.transition_audit_finding(
        TransitionAuditFindingCommand(finding.id, "dismissed", 2, context)
    )
    dismissed = queries.validity_projection(ids["project"], "claim_version", ids["claim_version"])
    assert dismissed.state is ValidityState.NOT_ASSESSED
    assert queries.list_impact_assessments(finding.id) == (stale, invalid)


def test_code_bug_correction_preserves_exact_historical_trace(engine: Engine) -> None:
    ids = _seed_graph(engine)
    service, queries = _services(engine)
    provenance = _provenance_service(engine)
    context = _context(ids["actor"])
    before_trace = provenance.trace_claim_to_runs(ids["claim_version"])
    with engine.connect() as connection:
        before = connection.execute(
            text(
                "SELECT r.status AS run_status, r.row_version AS run_row_version, "
                "r.inputs_sealed_at, m.content_hash AS measurement_hash, "
                "s.content_hash AS stat_hash, c.content_hash AS claim_hash "
                "FROM runs r JOIN measurements m ON m.run_id=r.id "
                "JOIN statistical_result_inputs sri ON sri.measurement_id=m.id "
                "JOIN statistical_results s ON s.id=sri.statistical_result_id "
                "JOIN claim_versions c ON c.id=:claim_id WHERE r.id=:run_id"
            ),
            {"claim_id": ids["claim_version"], "run_id": ids["run"]},
        ).one()
    finding = service.create_audit_finding(
        CreateAuditFindingCommand(
            ids["project"],
            "code_bug",
            "critical",
            "bug",
            "bad code",
            "artifact_version",
            ids["artifact_version"],
            context,
        )
    )
    assessment = service.create_impact_assessment(
        CreateImpactAssessmentCommand(
            ids["project"],
            finding.id,
            {"basis": "code review"},
            "invalid",
            (ProposedImpactTarget("claim_version", ids["claim_version"], "invalid"),),
            context,
        )
    )
    correction = service.create_correction_record(
        CreateCorrectionRecordCommand(
            ids["project"],
            "artifact_version",
            ids["artifact_version"],
            "computational",
            {"fixed": True},
            "new correction history",
            context,
        )
    )
    after_trace = provenance.trace_claim_to_runs(ids["claim_version"])
    with engine.connect() as connection:
        after = connection.execute(
            text(
                "SELECT r.status AS run_status, r.row_version AS run_row_version, "
                "r.inputs_sealed_at, m.content_hash AS measurement_hash, "
                "s.content_hash AS stat_hash, c.content_hash AS claim_hash "
                "FROM runs r JOIN measurements m ON m.run_id=r.id "
                "JOIN statistical_result_inputs sri ON sri.measurement_id=m.id "
                "JOIN statistical_results s ON s.id=sri.statistical_result_id "
                "JOIN claim_versions c ON c.id=:claim_id WHERE r.id=:run_id"
            ),
            {"claim_id": ids["claim_version"], "run_id": ids["run"]},
        ).one()
    assert before == after
    assert before_trace == after_trace
    assert (
        queries.validity_projection(ids["project"], "claim_version", ids["claim_version"]).state
        is ValidityState.INVALID
    )
    assert (
        assessment.id
        in queries.validity_projection(
            ids["project"], "claim_version", ids["claim_version"]
        ).assessment_ids
    )
    assert correction.target_id == ids["artifact_version"]


def test_downstream_select_count_is_stage_bounded(engine: Engine) -> None:
    ids = _seed_graph(engine)
    _, queries = _services(engine)
    statements: list[str] = []

    def capture(
        _connection: object,
        _cursor: object,
        statement: str,
        _parameters: object,
        _context: object,
        _executemany: bool,
    ) -> None:
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    def count_for_query() -> tuple[int, int]:
        statements.clear()
        result = queries.downstream_impact(
            ids["project"], "artifact_version", ids["artifact_version"]
        )
        return len(statements), len(result)

    event.listen(engine, "before_cursor_execute", capture)
    try:
        small_count, small_targets = count_for_query()
        with engine.begin() as connection:
            for _ in range(12):
                run_id, measurement_id = uuid4(), uuid4()
                now = datetime(2026, 8, 30, tzinfo=UTC)
                connection.execute(
                    text(
                        "INSERT INTO runs(id,project_id,experiment_spec_version_id,status,created_by,created_at) "
                        "VALUES (:run,:project,:spec,'PLANNED',:actor,:now)"
                    ),
                    {
                        "run": run_id,
                        "project": ids["project"],
                        "spec": ids["spec_version"],
                        "actor": ids["actor"],
                        "now": now,
                    },
                )
                connection.execute(
                    text(
                        "INSERT INTO run_artifact_inputs(run_id,artifact_version_id,role) VALUES (:run,:artifact,'source_code')"
                    ),
                    {"run": run_id, "artifact": ids["artifact_version"]},
                )
                connection.execute(
                    text(
                        "UPDATE runs SET status='RUNNING', inputs_sealed_at=:now, "
                        "started_at=:now, row_version=2 WHERE id=:run"
                    ),
                    {"run": run_id, "now": now},
                )
                connection.execute(
                    text(
                        "UPDATE runs SET status='SUCCEEDED', finished_at=:now, exit_code=0, "
                        "row_version=3 WHERE id=:run"
                    ),
                    {"run": run_id, "now": now},
                )
                connection.execute(
                    text(
                        "INSERT INTO measurements(id,run_id,metric_definition_version_id,numeric_value,content_hash,created_by,created_at) "
                        "VALUES (:measurement,:run,:metric,1.0,:hash,:actor,:now)"
                    ),
                    {
                        "measurement": measurement_id,
                        "run": run_id,
                        "metric": ids["metric_version"],
                        "hash": uuid4().hex * 2,
                        "actor": ids["actor"],
                        "now": now,
                    },
                )
        large_count, large_targets = count_for_query()
    finally:
        event.remove(engine, "before_cursor_execute", capture)

    assert large_targets > small_targets
    assert large_count <= small_count + 1


def test_impact_target_resolution_is_batch_bounded(engine: Engine) -> None:
    ids = _seed_graph(engine)
    service, _ = _services(engine)
    context = _context(ids["actor"])
    finding = service.create_audit_finding(
        CreateAuditFindingCommand(
            ids["project"], "batch", "minor", "batch", "batch", "run", ids["run"], context
        )
    )
    run_ids = [ids["run"]]
    with engine.begin() as connection:
        now = datetime(2026, 8, 30, tzinfo=UTC)
        for _ in range(15):
            run_id = uuid4()
            run_ids.append(run_id)
            connection.execute(
                text(
                    "INSERT INTO runs(id,project_id,experiment_spec_version_id,status,created_by,created_at) "
                    "VALUES (:run,:project,:spec,'PLANNED',:actor,:now)"
                ),
                {
                    "run": run_id,
                    "project": ids["project"],
                    "spec": ids["spec_version"],
                    "actor": ids["actor"],
                    "now": now,
                },
            )
    statements: list[str] = []

    def capture(
        _connection: object,
        _cursor: object,
        statement: str,
        _parameters: object,
        _context: object,
        _executemany: bool,
    ) -> None:
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    event.listen(engine, "before_cursor_execute", capture)
    try:
        assessment = service.create_impact_assessment(
            CreateImpactAssessmentCommand(
                ids["project"],
                finding.id,
                {"count": len(run_ids)},
                "requires_review",
                tuple(ProposedImpactTarget("run", run_id, "downstream") for run_id in run_ids),
                context,
            )
        )
    finally:
        event.remove(engine, "before_cursor_execute", capture)

    assert len(assessment.targets) == len(run_ids)
    assert sum("FROM runs" in statement for statement in statements) == 1


def test_governance_foreign_keys_restrict_deletes(engine: Engine) -> None:
    ids = _seed_graph(engine)
    service, _ = _services(engine)
    context = _context(ids["actor"])
    finding = service.create_audit_finding(
        CreateAuditFindingCommand(
            ids["project"], "fk", "info", "fk", "fk", "run", ids["run"], context
        )
    )
    assessment = service.create_impact_assessment(
        CreateImpactAssessmentCommand(
            ids["project"],
            finding.id,
            {},
            "unknown",
            (ProposedImpactTarget("run", ids["run"], "requires_review"),),
            context,
        )
    )
    for statement, values in (
        ("DELETE FROM audit_findings WHERE id=:id", {"id": finding.id}),
        ("DELETE FROM impact_assessments WHERE id=:id", {"id": assessment.id}),
        ("DELETE FROM projects WHERE id=:id", {"id": ids["project"]}),
        ("DELETE FROM actors WHERE id=:id", {"id": ids["actor"]}),
    ):
        with engine.begin() as connection:
            with pytest.raises(DBAPIError):
                connection.execute(text(statement), values)

    for statement, values in (
        (
            "DELETE FROM impact_targets WHERE impact_assessment_id=:id",
            {"id": assessment.id},
        ),
        (
            "INSERT INTO impact_targets(impact_assessment_id,target_type,target_id,impact_kind) "
            "VALUES (:id,'measurement',:target,'downstream')",
            {"id": assessment.id, "target": ids["measurement"]},
        ),
    ):
        with engine.begin() as c:
            with pytest.raises(DBAPIError):
                c.execute(text(statement), values)


@pytest.mark.parametrize(
    ("method_name", "table_name", "operation"),
    (
        ("add_audit_finding", "audit_findings", "finding"),
        ("add_impact_assessment", "impact_assessments", "assessment"),
        ("add_correction_record", "correction_records", "correction"),
    ),
)
def test_governance_create_rolls_back_after_real_sql_and_retry_is_exact(
    engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
    method_name: str,
    table_name: str,
    operation: str,
) -> None:
    ids = _seed_graph(engine)
    service, _ = _services(engine)
    context = _context(ids["actor"])
    finding = None
    if operation == "assessment":
        finding = service.create_audit_finding(
            CreateAuditFindingCommand(
                ids["project"],
                "atomic-parent",
                "minor",
                "parent",
                "parent",
                "run",
                ids["run"],
                context,
            )
        )

    def invoke() -> object:
        if operation == "finding":
            return service.create_audit_finding(
                CreateAuditFindingCommand(
                    ids["project"],
                    "atomic",
                    "major",
                    "atomic",
                    "failure",
                    "run",
                    ids["run"],
                    context,
                )
            )
        if operation == "assessment":
            assert finding is not None
            return service.create_impact_assessment(
                CreateImpactAssessmentCommand(
                    ids["project"],
                    finding.id,
                    {},
                    "unknown",
                    (ProposedImpactTarget("run", ids["run"], "requires_review"),),
                    context,
                )
            )
        return service.create_correction_record(
            CreateCorrectionRecordCommand(
                ids["project"], "run", ids["run"], "other", {}, "atomic", context
            )
        )

    original = getattr(SqlAlchemyGovernanceRepository, method_name)
    sql_occurred = False

    def fail_after_flush(repository: object, value: object) -> None:
        nonlocal sql_occurred
        original(repository, value)
        sql_occurred = True
        raise RuntimeError("injected after SQL")

    monkeypatch.setattr(SqlAlchemyGovernanceRepository, method_name, fail_after_flush)
    with pytest.raises(RuntimeError, match="injected after SQL"):
        invoke()
    assert sql_occurred
    with engine.connect() as c:
        failed_count = c.execute(
            text(f"SELECT count(*) FROM {table_name} WHERE project_id=:project"),
            {"project": ids["project"]},
        ).scalar_one()
    assert failed_count == (
        1 if operation == "assessment" and table_name == "audit_findings" else 0
    )

    monkeypatch.setattr(SqlAlchemyGovernanceRepository, method_name, original)
    invoke()
    with engine.connect() as c:
        assert (
            c.execute(
                text(f"SELECT count(*) FROM {table_name} WHERE project_id=:project"),
                {"project": ids["project"]},
            ).scalar_one()
            == 1
        )
