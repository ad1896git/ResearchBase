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


def test_pr08_schema_is_exact_and_restrictive(engine: Engine) -> None:
    expected = {
        "metric_definitions": {
            "id",
            "project_id",
            "name",
            "current_version_id",
            "created_by",
            "created_at",
            "row_version",
        },
        "metric_definition_versions": {
            "id",
            "metric_definition_id",
            "version_number",
            "status",
            "definition",
            "unit",
            "aggregation",
            "content_hash",
            "created_by",
            "created_at",
            "frozen_at",
            "row_version",
        },
    }
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT table_name, column_name FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name IN "
                "('metric_definitions','metric_definition_versions')"
            )
        ).all()
        actual: dict[str, set[str]] = {}
        for row in rows:
            actual.setdefault(row.table_name, set()).add(row.column_name)
        assert actual == expected
        fks = connection.execute(
            text(
                "SELECT tc.table_name, kcu.column_name, rc.delete_rule "
                "FROM information_schema.table_constraints tc "
                "JOIN information_schema.key_column_usage kcu "
                "ON tc.constraint_name=kcu.constraint_name "
                "AND tc.table_schema=kcu.table_schema "
                "JOIN information_schema.referential_constraints rc "
                "ON tc.constraint_name=rc.constraint_name "
                "AND tc.constraint_schema=rc.constraint_schema "
                "WHERE tc.table_schema='public' AND tc.table_name IN "
                "('metric_definitions','metric_definition_versions')"
            )
        ).all()
        assert fks and all(row.delete_rule == "RESTRICT" for row in fks)
        assert {row.column_name for row in fks} >= {
            "project_id",
            "created_by",
            "current_version_id",
            "metric_definition_id",
        }
        uniques = connection.execute(
            text(
                "SELECT kcu.column_name FROM information_schema.table_constraints tc "
                "JOIN information_schema.key_column_usage kcu "
                "ON tc.constraint_name=kcu.constraint_name "
                "AND tc.table_schema=kcu.table_schema "
                "WHERE tc.table_name='metric_definition_versions' "
                "AND tc.constraint_type='UNIQUE'"
            )
        ).all()
        assert {row.column_name for row in uniques} == {"metric_definition_id", "version_number"}


def test_pr08_status_and_version_checks_exist(engine: Engine) -> None:
    with engine.connect() as connection:
        checks = [
            row.check_clause
            for row in connection.execute(
                text(
                    "SELECT cc.check_clause FROM information_schema.table_constraints tc "
                    "JOIN information_schema.check_constraints cc "
                    "ON tc.constraint_name=cc.constraint_name "
                    "AND tc.constraint_schema=cc.constraint_schema "
                    "WHERE tc.table_name='metric_definition_versions'"
                )
            )
        ]
        assert any("version_number" in value and "> 0" in value for value in checks)
        assert any("status" in value and "DRAFT" in value for value in checks)
