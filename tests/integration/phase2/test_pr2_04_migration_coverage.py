"""PR2-04 upgrade preservation and independently exercised downgrade sentinels."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from alembic import command
from alembic.script import ScriptDirectory
from scripts.pr2_04_pytest_evidence import FactRecorder
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from tests.integration.phase2.test_pr2_01_source_identity import _authorized_service
from tests.integration.phase2.test_pr2_03_review_guards import _freeze, _setup
from tests.integration.phase2.test_pr2_04_execution_migration import (
    PARENT,
    REVISION,
    _alembic,
    _upgrade,
)
from tests.integration.phase2.test_pr2_04_schema_coverage import (
    A,
    C,
    E,
    Q,
    R,
    TABLES,
    V,
    _material,
    _rows,
)

# This order is the frozen revision's preflight order. For each case we
# deliberately leave the selected table as its first nonempty sentinel. FK
# parents stay populated; independent cases prove no earlier sentinel masks it.
PREFLIGHT_ORDER = (C, V, R, Q, A, E)
FROZEN_PR204 = "ea216c9babea322808b3885f563d276b571575ab"


def _catalog(engine) -> dict:
    with engine.connect() as connection:
        inspector = inspect(connection)
        return {
            "revision": connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one(),
            "tables": inspector.get_table_names(),
            "constraints": [
                list(row)
                for row in connection.execute(
                    text("""
                SELECT conrelid::regclass::text,conname,pg_get_constraintdef(oid)
                  FROM pg_constraint WHERE connamespace='public'::regnamespace
                 ORDER BY conrelid::regclass::text,conname
            """)
                )
            ],
            "triggers": [
                list(row)
                for row in connection.execute(
                    text("""
                SELECT tgrelid::regclass::text,tgname,tgenabled,pg_get_triggerdef(oid)
                  FROM pg_trigger WHERE NOT tgisinternal
                 ORDER BY tgrelid::regclass::text,tgname
            """)
                )
            ],
            "functions": [
                list(row)
                for row in connection.execute(
                    text("""
                SELECT proname,pg_get_functiondef(oid) FROM pg_proc
                 WHERE pronamespace='public'::regnamespace AND proname LIKE 'pr204_%'
                 ORDER BY proname
            """)
                )
            ],
        }


@pytest.mark.parametrize(
    "origin", ["base", "0018", PARENT], ids=["fresh", "phase1_0018", "populated_0023a"]
)
@pytest.mark.pr204_requirements("PR204-MIG-01")
def test_upgrade_paths_preserve_complete_existing_rows_and_exact_table_delta(
    phase2_database_url: str,
    origin: str,
    pr204_trace: FactRecorder,
) -> None:
    engine = create_engine(phase2_database_url)
    try:
        if origin == PARENT:
            # Route only fixture migration selection to the accepted parent. All
            # identity, question, review and freeze behavior remains actual code/PG.
            with patch(
                "tests.integration.phase2.test_pr2_03_review_guards._authorized_service",
                side_effect=lambda url: _authorized_service(url, migration_revision=PARENT),
            ):
                setup_engine, plans, principal, project, plan, version = _setup(phase2_database_url)
                _freeze(setup_engine, plans, principal, project, plan, version)
            setup_engine.dispose()
        elif origin != "base":
            _upgrade(phase2_database_url, origin)
        with engine.connect() as connection:
            before_tables = set(inspect(connection).get_table_names()) - {"alembic_version"}
            before = {
                table: sorted(
                    connection.execute(text(f'SELECT to_jsonb(t)::text FROM "{table}" t')).scalars()
                )
                for table in before_tables
            }
        if origin == PARENT:
            assert before["projects"] and before["actors"]
            assert before["project_memberships"]
            assert before["literature_search_plan_versions"]
            assert before["research_question_versions"]
        _upgrade(phase2_database_url)
        with engine.connect() as connection:
            after_tables = set(inspect(connection).get_table_names()) - {"alembic_version"}
            after = {
                table: sorted(
                    connection.execute(text(f'SELECT to_jsonb(t)::text FROM "{table}" t')).scalars()
                )
                for table in before_tables
            }
            revisions = list(
                connection.execute(text("SELECT version_num FROM alembic_version")).scalars()
            )
        scripts = ScriptDirectory.from_config(_alembic(phase2_database_url))
        revision = scripts.get_revision(REVISION)
        assert revision is not None
        pr204_trace.record(
            origin=origin,
            before_counts={t: len(r) for t, r in before.items()},
            after_counts={t: len(r) for t, r in after.items()},
            existing_rows_identical=before == after,
            added_tables=sorted(after_tables - before_tables),
            current_revisions=revisions,
            heads=scripts.get_heads(),
            parent=revision.down_revision,
        )
        assert before == after
        assert revisions == [REVISION]
        assert scripts.get_heads() == ["0025_pr2_04_reservation_guards"]
        assert revision.down_revision == PARENT
        if origin == PARENT:
            assert after_tables - before_tables == set(TABLES)
        else:
            assert set(TABLES) <= after_tables
    finally:
        engine.dispose()


@pytest.mark.pr204_requirements("PR204-MIG-02")
def test_empty_downgrade_removes_exact_tables_and_reupgrade_restores_catalog(
    phase2_database_url: str,
    pr204_trace: FactRecorder,
) -> None:
    _upgrade(phase2_database_url)
    engine = create_engine(phase2_database_url)
    try:
        before = _catalog(engine)
        assert all(not rows for rows in _rows(engine).values())
        with patch.dict("os.environ", {"DATABASE_URL": phase2_database_url}):
            command.downgrade(_alembic(phase2_database_url), PARENT)
        downgraded = _catalog(engine)
        assert downgraded["revision"] == PARENT
        assert set(before["tables"]) - set(downgraded["tables"]) == set(TABLES)
        assert downgraded["functions"] == []
        _upgrade(phase2_database_url)
        after = _catalog(engine)
        pr204_trace.record(
            before_catalog=before,
            downgraded_catalog=downgraded,
            reupgraded_catalog=after,
            durable_counts={t: len(r) for t, r in _rows(engine).items()},
        )
        assert after == before
    finally:
        engine.dispose()


@pytest.mark.parametrize("sentinel", PREFLIGHT_ORDER)
@pytest.mark.pr204_requirements("PR204-MIG-02")
def test_each_populated_table_independently_refuses_downgrade_before_any_ddl(
    phase2_database_url: str,
    sentinel: str,
    pr204_trace: FactRecorder,
) -> None:
    stage = "planned" if sentinel == E else "reserved" if sentinel == A else "terminal"
    # Historical0024 preflight fixture remains distinct from current0025 graph.
    with patch("tests.integration.phase2.test_pr2_04_schema_coverage._setup",
               side_effect=lambda url: _setup(url, migration_revision=REVISION)):
        material = _material(phase2_database_url, stage, hits=0 if sentinel == Q else 1)
    engine = material["engine"]
    try:
        # Test-only removal of immutable audit rows is confined to the disposable
        # fixture database and committed with all guards reenabled. Concrete FK
        # constraints stay enabled. No scientific FK or migration is modified.
        with engine.begin() as connection:
            for earlier in PREFLIGHT_ORDER[: PREFLIGHT_ORDER.index(sentinel)]:
                if earlier in (C, V):
                    connection.execute(text(f"ALTER TABLE {earlier} DISABLE TRIGGER USER"))
                    connection.execute(text(f"DELETE FROM {earlier}"))
                    connection.execute(text(f"ALTER TABLE {earlier} ENABLE TRIGGER USER"))
        rows_before = _rows(engine)
        counts_before = {table: len(rows) for table, rows in rows_before.items()}
        assert counts_before[sentinel] > 0
        assert all(
            counts_before[table] == 0
            for table in PREFLIGHT_ORDER[: PREFLIGHT_ORDER.index(sentinel)]
        )
        catalog_before = _catalog(engine)
        statements = []

        def observe_sql(_connection, _cursor, statement, _parameters, _context, _executemany):
            statements.append(statement)

        event.listen(Engine, "before_cursor_execute", observe_sql)
        try:
            with pytest.raises(
                RuntimeError, match="requires all PR2-04 tables to be empty"
            ) as caught:
                with patch.dict("os.environ", {"DATABASE_URL": phase2_database_url}):
                    command.downgrade(_alembic(phase2_database_url), PARENT)
        finally:
            event.remove(Engine, "before_cursor_execute", observe_sql)
        rows_after, catalog_after = _rows(engine), _catalog(engine)
        pr204_trace.record(
            sentinel=sentinel,
            inspection_order=list(PREFLIGHT_ORDER),
            before_counts=counts_before,
            after_counts={t: len(r) for t, r in rows_after.items()},
            refusal_type=type(caught.value).__name__,
            refusal_message=str(caught.value),
            rejected_sqlstate=None,
            rejection_source="migration_preflight",
            catalog_identical=catalog_before == catalog_after,
            durable_rows_identical=rows_before == rows_after,
            revision=catalog_after["revision"],
            actual_downgrade_sql=statements,
        )
        assert not any(sql.lstrip().upper().startswith(("DROP ", "ALTER ", "TRUNCATE ", "DELETE "))
                       for sql in statements)
        assert rows_before == rows_after
        assert catalog_before == catalog_after
        assert catalog_after["revision"] == REVISION
    finally:
        engine.dispose()


@pytest.mark.pr204_requirements("PR204-MIG-02", "PR204-REG-01")
def test_historical_migration_bytes_match_frozen_accepted_tree(pr204_trace: FactRecorder) -> None:
    # A02: FROZEN_PR204 remains provenance; no original ancestry claim.
    from scripts.pr2_04_recovery_bindings import baseline, validate_migration_prefix
    binding = baseline()
    checks = validate_migration_prefix()
    hashes = {}
    for path, digest in binding["source_sha256"].items():
        if path.startswith("migrations/versions/"):
            current = hashlib.sha256(Path(path).read_bytes()).hexdigest()
            assert current == digest
            hashes[path] = {"recovery_parent_sha256": digest, "current_sha256": current}
    assert hashes
    scripts = ScriptDirectory.from_config(_alembic("postgresql://unused"))
    child = scripts.get_revision("0025_pr2_04_reservation_guards")
    assert child is not None and child.down_revision == REVISION
    assert scripts.get_heads() == ["0025_pr2_04_reservation_guards"]
    pr204_trace.record(historical_reference=FROZEN_PR204,
        historical_ancestry_recovered=False, recovery_baseline=binding["migration_base"],
        recovery_migration_hashes=hashes, topology=checks)
