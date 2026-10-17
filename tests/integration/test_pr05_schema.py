from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from researchbase.persistence.database import create_database_engine

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def engine() -> Iterator[Engine]:
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL is not set; run against the real PostgreSQL service")
    value = create_database_engine()
    try:
        yield value
    finally:
        value.dispose()


def test_pr05_schema_columns_constraints_and_restrict_foreign_keys(engine: Engine) -> None:
    with engine.connect() as connection:
        assert {
            connection.execute(
                text("SELECT to_regclass(:name)"), {"name": f"public.{table}"}
            ).scalar_one()
            for table in ("experiment_specs", "experiment_spec_versions")
        } == {"experiment_specs", "experiment_spec_versions"}
        rows = connection.execute(
            text(
                """
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name IN ('experiment_specs', 'experiment_spec_versions')
                """
            )
        ).all()
        columns: dict[str, set[str]] = {}
        for row in rows:
            columns.setdefault(row.table_name, set()).add(row.column_name)
        assert columns["experiment_specs"] == {
            "id",
            "project_id",
            "hypothesis_id",
            "current_version_id",
            "created_by",
            "created_at",
            "row_version",
        }
        assert columns["experiment_spec_versions"] == {
            "id",
            "experiment_spec_id",
            "version_number",
            "status",
            "title",
            "objective",
            "protocol",
            "planned_metrics",
            "seed_policy",
            "analysis_plan",
            "content_hash",
            "created_by",
            "created_at",
            "frozen_at",
            "row_version",
        }
        foreign_keys = connection.execute(
            text(
                """
                SELECT tc.table_name, kcu.column_name, rc.delete_rule
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.table_schema = kcu.table_schema
                JOIN information_schema.referential_constraints rc
                  ON tc.constraint_name = rc.constraint_name
                 AND tc.constraint_schema = rc.constraint_schema
                WHERE tc.table_schema = 'public'
                  AND tc.table_name IN ('experiment_specs', 'experiment_spec_versions')
                """
            )
        ).all()
        assert all(row.delete_rule == "RESTRICT" for row in foreign_keys)
        assert {(row.table_name, row.column_name) for row in foreign_keys} >= {
            ("experiment_specs", "project_id"),
            ("experiment_specs", "hypothesis_id"),
            ("experiment_specs", "current_version_id"),
            ("experiment_specs", "created_by"),
            ("experiment_spec_versions", "experiment_spec_id"),
            ("experiment_spec_versions", "created_by"),
        }


def test_pr05_database_checks_reject_invalid_version_rows(engine: Engine) -> None:
    with engine.connect() as connection:
        with pytest.raises(IntegrityError):
            connection.execute(
                text(
                    "INSERT INTO experiment_spec_versions "
                    "(id, experiment_spec_id, version_number, status, title, objective, "
                    "protocol, created_by, created_at) "
                    "VALUES ('00000000-0000-0000-0000-000000000001', "
                    "'00000000-0000-0000-0000-000000000002', 0, 'DRAFT', 'x', 'y', '{}', "
                    "'00000000-0000-0000-0000-000000000003', now())"
                )
            )
        connection.rollback()
