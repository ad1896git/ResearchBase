"""Real PostgreSQL lifecycle, preservation and fail-closed checks for approved 0043."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from alembic import command
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import DBAPIError

from tests.integration.phase2 import test_pr2_04_schema_coverage as coverage
from tests.integration.phase2.test_pr2_03_review_guards import _setup
from tests.integration.phase2.test_pr2_04_execution_migration import _alembic, _upgrade

PARENT = "0042_pr2_15_minimal_decision"
REVISION = "0043_pr2_04_schema_contract"


def _snapshot(engine):
    """Every public row, plus logical schema (exclude physical rewrite/OID details)."""
    with engine.connect() as connection:
        tables = inspect(connection).get_table_names()
        return {
            "rows": {
                table: sorted(
                    connection.execute(text(f'SELECT to_jsonb(t)::text FROM "{table}" t')).scalars()
                )
                for table in tables
                if table != "alembic_version"
            },
            "revision": connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar(),
            "schema": {
                "columns": list(
                    connection.execute(
                        text("""
                    SELECT table_name,column_name,data_type,is_nullable,column_default
                    FROM information_schema.columns WHERE table_schema='public'
                    ORDER BY table_name,ordinal_position
                """)
                    )
                ),
                "constraints": list(
                    connection.execute(
                        text("""
                    SELECT conrelid::regclass::text,conname,pg_get_constraintdef(oid)
                    FROM pg_constraint WHERE connamespace='public'::regnamespace
                    ORDER BY 1,2
                """)
                    )
                ),
                "indexes": list(
                    connection.execute(
                        text("""
                    SELECT tablename,indexname,indexdef FROM pg_indexes
                    WHERE schemaname='public' ORDER BY 1,2
                """)
                    )
                ),
                "triggers": list(
                    connection.execute(
                        text("""
                    SELECT tgrelid::regclass::text,tgname,tgenabled,pg_get_triggerdef(oid)
                    FROM pg_trigger WHERE NOT tgisinternal ORDER BY 1,2
                """)
                    )
                ),
                "functions": list(
                    connection.execute(
                        text("""
                    SELECT proname,pg_get_functiondef(oid) FROM pg_proc
                    WHERE pronamespace='public'::regnamespace ORDER BY 1,2
                """)
                    )
                ),
            },
        }


def _parent_material(url, stage):
    # Use accepted Application commands against 0042, without upgrading the fixture to head.
    with patch.object(
        coverage, "_setup", side_effect=lambda url: _setup(url, migration_revision=PARENT)
    ):
        return coverage._material(url, stage)


def _second_material(url, material, stage):
    setup = tuple(
        material[key] for key in ("engine", "plans", "principal", "project", "plan", "version")
    )
    # Reuse the established first owner and frozen plan; bootstrap is one-shot.
    with patch.object(coverage, "_setup", return_value=setup), patch.object(coverage, "_freeze"):
        return coverage._material(url, stage)


def _downgrade(url):
    command.downgrade(_alembic(url), PARENT)


def _assert_repaired(engine):
    with engine.connect() as connection:
        catalog = inspect(connection)
        for table, expected in coverage.UNIQUE_COLUMNS.items():
            assert expected <= {
                tuple(item["column_names"]) for item in catalog.get_unique_constraints(table)
            }
        assert (
            str(
                dict((c["name"], c["type"]) for c in catalog.get_columns(coverage.C))[
                    "result_dto_version"
                ]
            )
            == "SMALLINT"
        )
        for table in coverage.TABLES:
            for fk in catalog.get_foreign_keys(table):
                columns = tuple(fk["constrained_columns"])
                assert connection.execute(
                    text("""
                    SELECT EXISTS (
                      SELECT 1 FROM pg_index i JOIN pg_class idx ON idx.oid=i.indexrelid
                      JOIN pg_am am ON am.oid=idx.relam
                      WHERE i.indrelid=to_regclass(:table) AND i.indpred IS NULL
                        AND i.indexprs IS NULL AND i.indisvalid AND am.amname='btree'
                        AND (SELECT array_agg(a.attname::text ORDER BY k.ordinality)
                          FROM unnest(i.indkey) WITH ORDINALITY k(attnum,ordinality)
                          JOIN pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=k.attnum
                          WHERE k.ordinality<=:size)=CAST(:columns AS text[]))
                """),
                    {"table": table, "size": len(columns), "columns": list(columns)},
                ).scalar_one()
        assert any(
            idx["column_names"] == ["project_id", "status", "created_at", "id"]
            for idx in catalog.get_indexes(coverage.E)
        )


def test_empty_upgrade_downgrade_and_reupgrade(phase2_database_url):
    url = phase2_database_url
    _upgrade(url, PARENT)
    engine = create_engine(url)
    try:
        before = _snapshot(engine)
        _downgrade(url)  # Already at parent: no-op sanity check.
        _upgrade(url, "head")
        _assert_repaired(engine)
        assert _snapshot(engine)["rows"] == before["rows"]
        _downgrade(url)
        assert _snapshot(engine) == before
        _upgrade(url, "head")
        _assert_repaired(engine)
    finally:
        engine.dispose()


@pytest.mark.parametrize("stage", ["planned", "reserved", "sealed", "terminal"])
def test_populated_0042_roundtrip_preserves_every_row_and_schema(phase2_database_url, stage):
    url = phase2_database_url
    material = _parent_material(url, stage)
    engine = material["engine"]
    _second_material(url, material, stage)
    try:
        before = _snapshot(engine)
        assert before["revision"] == PARENT
        assert before["rows"][coverage.C] and before["rows"][coverage.E]
        if stage == "reserved":
            assert (
                sum(row["query_record_id"] is None for row in coverage._rows(engine)[coverage.A])
                == 2
            )
        if stage in {"sealed", "terminal"}:
            assert all(before["rows"][table] for table in coverage.TABLES)
        _upgrade(url, REVISION)
        after = _snapshot(engine)
        assert after["revision"] == REVISION
        assert after["rows"] == before["rows"]
        _assert_repaired(engine)
        _downgrade(url)
        assert _snapshot(engine) == before
        _upgrade(url, REVISION)
        assert _snapshot(engine) == after
    finally:
        engine.dispose()


@pytest.mark.parametrize("corruption", ["attempt_query", "scoped_query", "receipt_range"])
def test_preflight_rejects_conflicting_data_without_partial_ddl(phase2_database_url, corruption):
    url = phase2_database_url
    material = _parent_material(url, "sealed")
    _second_material(url, material, "sealed")
    engine = material["engine"]
    try:
        rows = coverage._rows(engine)
        # Intentionally corrupt only this disposable test DB. Guards must be bypassed
        # to model preexisting invalid history; migration itself never bypasses them.
        with engine.begin() as connection:
            if corruption == "attempt_query":
                table = coverage.A
                connection.execute(text(f"ALTER TABLE {table} DISABLE TRIGGER USER"))
                connection.execute(
                    text(f"UPDATE {table} SET query_record_id=:query WHERE id=:id"),
                    {
                        "query": rows[coverage.A][0]["query_record_id"],
                        "id": rows[coverage.A][1]["id"],
                    },
                )
                diagnostic, state = (
                    "duplicate literature_search_provider_attempts.query_record_id",
                    "23505",
                )
            elif corruption == "scoped_query":
                # A duplicate scoped key also violates the old global PK. Remove its
                # concrete dependents explicitly so this defensive preflight is reachable.
                for table in (coverage.A, coverage.R):
                    for fk in inspect(connection).get_foreign_keys(table):
                        if fk["referred_table"] == coverage.Q:
                            connection.execute(
                                text(f'ALTER TABLE {table} DROP CONSTRAINT "{fk["name"]}"')
                            )
                table = coverage.Q
                for fk in inspect(connection).get_foreign_keys(table):
                    if fk["referred_table"] == coverage.A:
                        connection.execute(
                            text(f'ALTER TABLE {table} DROP CONSTRAINT "{fk["name"]}"')
                        )
                pk = inspect(connection).get_pk_constraint(table)["name"]
                connection.execute(text(f'ALTER TABLE {table} DROP CONSTRAINT "{pk}"'))
                connection.execute(text(f"ALTER TABLE {table} DISABLE TRIGGER USER"))
                connection.execute(
                    text(f"""UPDATE {table} SET id=:first_id,
                    literature_search_execution_id=:execution,ordinal=1,query_hash=:hash
                    WHERE id=:second_id"""),
                    {
                        "first_id": rows[table][0]["id"],
                        "second_id": rows[table][1]["id"],
                        "execution": rows[table][0]["literature_search_execution_id"],
                        "hash": "b" * 64,
                    },
                )
                diagnostic, state = (
                    "duplicate search_query_records scoped execution/id key",
                    "23505",
                )
            else:
                table = coverage.C
                for check in inspect(connection).get_check_constraints(table):
                    if "result_dto_version" in check["sqltext"]:
                        connection.execute(
                            text(f'ALTER TABLE {table} DROP CONSTRAINT "{check["name"]}"')
                        )
                connection.execute(text(f"ALTER TABLE {table} DISABLE TRIGGER USER"))
                connection.execute(text(f"UPDATE {table} SET result_dto_version=32768"))
                diagnostic, state = "receipt result_dto_version outside SMALLINT range", "22003"
            connection.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
            connection.execute(text(f"ALTER TABLE {table} ENABLE TRIGGER USER"))
        before = _snapshot(engine)
        with pytest.raises(DBAPIError, match=f"0043 preflight: {diagnostic}") as error:
            _upgrade(url, REVISION)
        assert getattr(error.value.orig, "sqlstate", None) == state
        assert _snapshot(engine) == before
    finally:
        engine.dispose()


def test_downgrade_restricts_unexpected_dependents_without_partial_ddl(phase2_database_url):
    url = phase2_database_url
    _upgrade(url, "head")
    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text("""CREATE TABLE task12_dependent (
                execution_id UUID,query_id UUID,
                FOREIGN KEY (execution_id,query_id) REFERENCES search_query_records
                  (literature_search_execution_id,id) ON DELETE RESTRICT)""")
            )
        before = _snapshot(engine)
        with pytest.raises(DBAPIError) as error:
            _downgrade(url)
        assert getattr(error.value.orig, "sqlstate", None) == "2BP01"
        assert _snapshot(engine) == before
    finally:
        engine.dispose()
