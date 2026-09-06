"""PR-18 catalog and query-plan hardening checks."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine

from researchbase.persistence.database import create_database_engine

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def engine() -> Iterator[Engine]:
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL is not set; run against PostgreSQL 18")
    value = create_database_engine()
    try:
        yield value
    finally:
        value.dispose()


EXPECTED_INDEXES: dict[str, tuple[str, tuple[str, ...], bool, str | None]] = {
    "uq_actors_external_key": ("actors", ("external_key",), True, "(external_key IS NOT NULL)"),
    "uq_research_question_versions_parent_version": (
        "research_question_versions",
        ("research_question_id", "version_number"),
        True,
        None,
    ),
    "uq_hypothesis_versions_parent_version": (
        "hypothesis_versions",
        ("hypothesis_id", "version_number"),
        True,
        None,
    ),
    "uq_experiment_spec_versions_parent_version": (
        "experiment_spec_versions",
        ("experiment_spec_id", "version_number"),
        True,
        None,
    ),
    "uq_artifact_versions_artifact_version": (
        "artifact_versions",
        ("artifact_id", "version_number"),
        True,
        None,
    ),
    "uq_metric_definition_versions_parent_version": (
        "metric_definition_versions",
        ("metric_definition_id", "version_number"),
        True,
        None,
    ),
    "uq_claim_versions_parent_version": (
        "claim_versions",
        ("claim_id", "version_number"),
        True,
        None,
    ),
    "uq_artifact_versions_artifact_content_hash": (
        "artifact_versions",
        ("artifact_id", "content_hash"),
        True,
        None,
    ),
    "uq_dataset_snapshots_dataset_content_hash": (
        "dataset_snapshots",
        ("dataset_id", "content_hash"),
        True,
        None,
    ),
    "uq_evidence_measurement": (
        "evidence_relations",
        ("claim_version_id", "measurement_id", "relation_type"),
        True,
        "(measurement_id IS NOT NULL)",
    ),
    "uq_evidence_stat": (
        "evidence_relations",
        ("claim_version_id", "statistical_result_id", "relation_type"),
        True,
        "(statistical_result_id IS NOT NULL)",
    ),
    "ix_audit_findings_project": ("audit_findings", ("project_id",), False, None),
    "ix_audit_findings_target": (
        "audit_findings",
        ("project_id", "target_type", "target_id"),
        False,
        None,
    ),
    "ix_impact_assessments_project": (
        "impact_assessments",
        ("project_id",),
        False,
        None,
    ),
    "ix_impact_assessments_finding": (
        "impact_assessments",
        ("audit_finding_id",),
        False,
        None,
    ),
    "ix_impact_targets_target": (
        "impact_targets",
        ("target_type", "target_id"),
        False,
        None,
    ),
    "ix_correction_records_target": (
        "correction_records",
        ("project_id", "target_type", "target_id", "created_at", "id"),
        False,
        None,
    ),
}


def test_required_phase1_indexes_match_live_catalog(engine: Engine) -> None:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT c.relname AS index_name, t.relname AS table_name, "
                "i.indisunique, array_agg(a.attname ORDER BY keys.ordinality), "
                "pg_get_expr(i.indpred, i.indrelid) "
                "FROM pg_index AS i "
                "JOIN pg_class AS c ON c.oid = i.indexrelid "
                "JOIN pg_class AS t ON t.oid = i.indrelid "
                "JOIN LATERAL unnest(i.indkey) WITH ORDINALITY AS keys(attnum, ordinality) ON true "
                "JOIN pg_attribute AS a ON a.attrelid = i.indrelid AND a.attnum = keys.attnum "
                "WHERE c.relnamespace = 'public'::regnamespace "
                "AND c.relname = ANY(:names) "
                "GROUP BY c.relname, t.relname, i.indisunique, i.indpred, i.indrelid"
            ),
            {"names": list(EXPECTED_INDEXES)},
        ).all()

    actual = {
        row.index_name: (row.table_name, tuple(row.array_agg), row.indisunique, row.pg_get_expr)
        for row in rows
    }
    assert actual == EXPECTED_INDEXES


def _plan_shape(connection: Any, statement: str) -> dict[str, object]:
    raw = connection.execute(text(f"EXPLAIN (FORMAT JSON) {statement}")).scalar_one()
    document = raw[0] if isinstance(raw, list) else raw
    assert isinstance(document, dict)
    plan = document["Plan"]
    assert isinstance(plan, dict)
    return {
        "node_type": plan["Node Type"],
        "relation": plan.get("Relation Name"),
        "index": plan.get("Index Name"),
        "plan_rows": plan["Plan Rows"],
        "total_cost": plan["Total Cost"],
    }


def test_phase1_query_explain_baselines_are_json_and_bounded(engine: Engine) -> None:
    queries = {
        "claim_evidence": (
            "SELECT id, measurement_id, statistical_result_id FROM evidence_relations "
            "WHERE claim_version_id = '00000000-0000-0000-0000-000000000000'"
        ),
        "governance_target": (
            "SELECT id FROM audit_findings WHERE project_id = "
            "'00000000-0000-0000-0000-000000000000' "
            "AND target_type = 'artifact_version' AND target_id = "
            "'00000000-0000-0000-0000-000000000000'"
        ),
        "correction_target": (
            "SELECT id FROM correction_records WHERE project_id = "
            "'00000000-0000-0000-0000-000000000000' "
            "AND target_type = 'artifact_version' AND target_id = "
            "'00000000-0000-0000-0000-000000000000' "
            "ORDER BY created_at, id"
        ),
    }
    with engine.connect() as connection:
        shapes = {name: _plan_shape(connection, statement) for name, statement in queries.items()}

    assert set(shapes) == set(queries)
    assert all(isinstance(shape["node_type"], str) for shape in shapes.values())
    assert all(isinstance(shape["plan_rows"], int) for shape in shapes.values())
    assert all(
        isinstance(shape["total_cost"], int | float) and shape["total_cost"] >= 0
        for shape in shapes.values()
    )
    assert json.dumps(shapes, sort_keys=True)
