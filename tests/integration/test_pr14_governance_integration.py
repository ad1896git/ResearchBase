from __future__ import annotations

# Raw SQL is intentionally kept visibly exact for schema-contract tests.
# ruff: noqa: E501
import os
from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
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
from researchbase.domain.governance import GovernanceTargetType
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.execution_context import ExecutionContext
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
                "INSERT INTO experiment_spec_versions(id,experiment_spec_id,version_number,status,title,objective,protocol,content_hash,created_by,created_at,frozen_at) VALUES (:id,:parent,1,'FROZEN','t','o','{}',:hash,:actor,:now,:now)"
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
            text("UPDATE runs SET status='SUCCEEDED',inputs_sealed_at=:now WHERE id=:id"),
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
                "hash": "6" * 64,
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
                "hash": "7" * 64,
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
                "UPDATE claim_versions SET status='FROZEN',content_hash=:hash,frozen_at=:now WHERE id=:id"
            ),
            {"id": ids["claim_version"], "hash": "8" * 64, "now": now},
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
    claim = next(item for item in paths if item.target_id == ids["claim_version"])
    assert len(claim.paths) == 2
    assert {path.statistical_result_id for path in claim.paths} == {None, ids["stat"]}

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
