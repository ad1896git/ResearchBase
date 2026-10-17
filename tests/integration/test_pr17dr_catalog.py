from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine

from researchbase.persistence.database import create_database_engine
from tests.contracts.pr17dr_manifest import PR17D_FUNCTIONS, PR17D_TRIGGERS

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


def test_literal_prefix_ownership_is_not_a_wildcard() -> None:
    owned = ["pr17d_x", "pr17d_", "pr17d_x_y"]
    not_owned = ["pr17dx", "apr17d_x", "xpr17d_"]
    assert all(name.startswith("pr17d_") for name in owned)
    assert not any(name.startswith("pr17d_") for name in not_owned)


def test_postgresql_catalog_matches_independent_frozen_manifest(engine: Engine) -> None:
    with engine.connect() as connection:
        functions = {
            tuple(row)
            for row in connection.execute(
                text(
                    "SELECT n.nspname, p.proname, pg_get_function_identity_arguments(p.oid), "
                    "pg_get_function_result(p.oid), l.lanname "
                    "FROM pg_proc AS p "
                    "JOIN pg_namespace AS n ON n.oid = p.pronamespace "
                    "JOIN pg_language AS l ON l.oid = p.prolang "
                    "WHERE n.nspname = 'public' AND left(p.proname, 6) = 'pr17d_'"
                )
            ).all()
        }
        expected_functions = {
            ("public", name, "", "trigger", "plpgsql") for name in PR17D_FUNCTIONS
        }
        assert functions == expected_functions

        triggers = {
            (
                row.schema_name,
                row.trigger_name,
                row.table_name,
                row.timing,
                tuple(row.events),
                row.level,
                row.function_schema,
                row.function_name,
                row.enabled,
            )
            for row in connection.execute(
                text(
                    "SELECT tn.nspname AS schema_name, t.tgname AS trigger_name, "
                    "c.relname AS table_name, "
                    "CASE WHEN (t.tgtype & 2) = 2 THEN 'BEFORE' "
                    "WHEN (t.tgtype & 64) = 64 THEN 'INSTEAD OF' ELSE 'AFTER' END AS timing, "
                    "array_remove(ARRAY["
                    "CASE WHEN (t.tgtype & 4) = 4 THEN 'INSERT'::text END, "
                    "CASE WHEN (t.tgtype & 8) = 8 THEN 'DELETE'::text END, "
                    "CASE WHEN (t.tgtype & 16) = 16 THEN 'UPDATE'::text END, "
                    "CASE WHEN (t.tgtype & 32) = 32 THEN 'TRUNCATE'::text END], NULL) AS events, "
                    "CASE WHEN (t.tgtype & 1) = 1 THEN 'ROW' ELSE 'STATEMENT' END AS level, "
                    "pn.nspname AS function_schema, p.proname AS function_name, "
                    "t.tgenabled AS enabled "
                    "FROM pg_trigger AS t "
                    "JOIN pg_class AS c ON c.oid = t.tgrelid "
                    "JOIN pg_namespace AS tn ON tn.oid = c.relnamespace "
                    "JOIN pg_proc AS p ON p.oid = t.tgfoid "
                    "JOIN pg_namespace AS pn ON pn.oid = p.pronamespace "
                    "WHERE tn.nspname = 'public' AND NOT t.tgisinternal "
                    "AND left(t.tgname, 6) = 'pr17d_'"
                )
            ).all()
        }
        expected_triggers = {
            ("public", name, table, "BEFORE", (event,), "ROW", "public", function, "O")
            for name, table, event, function in PR17D_TRIGGERS
        }
        assert triggers == expected_triggers

        constraints = connection.execute(
            text(
                "SELECT n.nspname, c.conname FROM pg_constraint AS c "
                "JOIN pg_namespace AS n ON n.oid = c.connamespace "
                "WHERE n.nspname = 'public' AND left(c.conname, 6) = 'pr17d_'"
            )
        ).all()
        assert constraints == []

    bound = {function for _name, _table, _event, function in PR17D_TRIGGERS}
    assert bound == set(PR17D_FUNCTIONS)
