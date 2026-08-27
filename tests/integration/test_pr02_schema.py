from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine

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


def test_pr02_tables_and_constraints_exist_in_postgresql(engine: Engine) -> None:
    with engine.connect() as connection:
        tables = {
            connection.execute(text("SELECT to_regclass(:name)"), {"name": name}).scalar_one()
            for name in ("public.actors", "public.projects", "public.workspaces")
        }
        assert tables == {"actors", "projects", "workspaces"}

        constraints = connection.execute(
            text(
                """
                SELECT tc.table_name, tc.constraint_type, cc.check_clause
                FROM information_schema.table_constraints tc
                LEFT JOIN information_schema.check_constraints cc
                  ON tc.constraint_name = cc.constraint_name
                WHERE tc.table_schema = 'public'
                  AND tc.table_name IN ('actors', 'projects', 'workspaces')
                  AND tc.constraint_type IN ('CHECK', 'FOREIGN KEY')
                """
            )
        ).all()
        checks = " ".join(row.check_clause or "" for row in constraints)
        assert "human" in checks and "agent" in checks and "service" in checks
        assert "active" in checks and "archived" in checks and "retired" in checks

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
                  AND tc.table_name IN ('projects', 'workspaces')
                """
            )
        ).all()
        assert {(row.table_name, row.column_name, row.delete_rule) for row in foreign_keys} >= {
            ("projects", "created_by", "RESTRICT"),
            ("workspaces", "project_id", "RESTRICT"),
            ("workspaces", "created_by", "RESTRICT"),
        }
