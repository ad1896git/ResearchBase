# pyright: reportArgumentType=false, reportOptionalSubscript=false, reportIndexIssue=false, reportAttributeAccessIssue=false

"""PR-18 catalog and query-plan hardening checks."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from scripts import pr18_evidence
from sqlalchemy import text
from sqlalchemy.engine import Engine
from tests.contracts.pr18_manifest import FROZEN_REQUIRED_INDEXES

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
    name: (
        str(definition["table"]),
        tuple(definition["columns"]),  # type: ignore[arg-type]
        bool(definition["unique"]),
        definition["predicate"],  # type: ignore[return-value]
    )
    for name, definition in FROZEN_REQUIRED_INDEXES.items()
}


def test_frozen_manifest_includes_workspace_name_uniqueness() -> None:
    assert EXPECTED_INDEXES["uq_workspaces_project_name"] == (
        "workspaces",
        ("project_id", "name"),
        True,
        None,
    )
    assert FROZEN_REQUIRED_INDEXES["uq_workspaces_project_name"]["source"].endswith(
        "0002_actor_project_workspace.py"
    )


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

    with engine.connect() as connection:
        critical_names = {
            row.index_name
            for row in connection.execute(
                text(
                    "SELECT c.relname AS index_name "
                    "FROM pg_class AS c "
                    "JOIN pg_namespace AS n ON n.oid = c.relnamespace "
                    "WHERE n.nspname = 'public' AND c.relkind = 'i' "
                    "AND (c.relname LIKE 'uq_%' OR c.relname LIKE 'ix_%')"
                )
            ).all()
        }
    assert critical_names == set(EXPECTED_INDEXES)


def test_catalog_projection_is_independent_and_exact(engine: Engine) -> None:
    projection = pr18_evidence.collect_catalog_verification(engine)
    assert projection["exact_required_coverage"] is True
    assert projection["missing_required"] == []
    assert projection["mismatches"] == {}
    assert projection["unexpected_critical_names"] == []
    assert projection["migration_required"] is False
    assert all(Path(source["source"]).exists() for source in projection["expected_manifest"])


def test_actual_query_service_explain_paths_are_structurally_audited(engine: Engine) -> None:
    collector = getattr(pr18_evidence, "collect_query_explain_baselines", None)
    assert callable(collector)

    baselines = collector(engine)
    assert set(baselines) == {
        "run_provenance",
        "claim_trace",
        "downstream_impact",
        "audit_findings",
    }
    for baseline in baselines.values():
        assert baseline["production_operation"]
        assert baseline["statements"]
        assert baseline["required_relations"]
        assert baseline["representative_rows"] >= 100
        assert baseline["structural_assertions"]["select_only"] is True
        assert baseline["structural_assertions"]["no_cartesian_product"] is True
        assert baseline["structural_assertions"]["no_write_or_lock"] is True
        assert all(
            item["sql"].lstrip().upper().startswith("SELECT") for item in baseline["statements"]
        )
        assert all(item["plan"]["node_types"] for item in baseline["statements"])

    assert baselines["audit_findings"]["index_usable"] is True
