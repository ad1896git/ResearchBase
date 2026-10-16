"""TEST ONLY PR2-15 minimal schema, physical provenance and migration evidence."""

from __future__ import annotations

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from tests.integration.phase2.test_pr2_15_decision import _command, _review
from tests.integration.phase2.test_pr2_15_decision import conclusion_env as _conclusion_env
from tests.integration.phase2.test_pr2_15_decision import decision_env as _decision_env
from tests.integration.phase2.test_pr2_15_decision import phase2_database_url as _database_url

pytestmark = pytest.mark.integration
pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)
conclusion_env = _conclusion_env
phase2_database_url = _database_url
decision_env = _decision_env
PREVIOUS = "0041_pr2_15_review_coordination"
REVISION = "0042_pr2_15_minimal_decision"
TABLES = {"decision_records", "decision_basis_conclusions", "decision_basis_reviews"}


def _config(url):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    return config


def _tables(conn):
    return set(
        conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'")).scalars()
    )


def _catalog(conn, names):
    """Existing predecessor tables must retain physical keys/indexes/guards."""
    return tuple(
        tuple(conn.execute(text(sql), {"names": list(names)}).all())
        for sql in (
            """SELECT table_name,column_name,data_type,udt_name,is_nullable,column_default
           FROM information_schema.columns WHERE table_schema='public'
             AND table_name=ANY(:names) ORDER BY 1,2""",
            """SELECT c.relname,k.conname,pg_get_constraintdef(k.oid)
           FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid
           WHERE c.relnamespace='public'::regnamespace AND c.relname=ANY(:names) ORDER BY 1,2""",
            """SELECT tablename,indexname,indexdef FROM pg_indexes
           WHERE schemaname='public' AND tablename=ANY(:names) ORDER BY 1,2""",
            """SELECT c.relname,t.tgname,pg_get_triggerdef(t.oid) FROM pg_trigger t
           JOIN pg_class c ON c.oid=t.tgrelid WHERE NOT t.tgisinternal
             AND c.relnamespace='public'::regnamespace AND c.relname=ANY(:names) ORDER BY 1,2""",
        )
    )


def test_0042_exact_minimal_schema_fks_indexes_and_no_extra_tables(phase2_database_url):
    config = _config(phase2_database_url)
    assert ScriptDirectory.from_config(config).get_heads() == ["0051_b06_revision_action"]
    command.upgrade(config, PREVIOUS)
    engine = create_engine(phase2_database_url)
    try:
        with engine.connect() as conn:
            before = _tables(conn)
            prior_catalog = _catalog(conn, before)
        command.upgrade(config, REVISION)
        with engine.connect() as conn:
            assert _tables(conn) - before == TABLES
            assert before <= _tables(conn)
            assert _catalog(conn, before) == prior_catalog
            columns = conn.execute(
                text("""SELECT table_name,column_name,udt_name,is_nullable
              FROM information_schema.columns WHERE table_schema='public'
                AND table_name=ANY(:names)"""),
                {"names": list(TABLES)},
            ).all()
            actual = {
                table: {name: (kind, nullable) for t, name, kind, nullable in columns if t == table}
                for table in TABLES
            }
            required = {
                "decision_records": {
                    "id": ("uuid", "NO"),
                    "project_id": ("uuid", "NO"),
                    "decision_type": ("varchar", "NO"),
                    "question": ("text", "NO"),
                    "decision": ("varchar", "NO"),
                    "rationale": ("text", "NO"),
                    "decided_by": ("uuid", "NO"),
                    "decided_at": ("timestamptz", "NO"),
                    "supersedes_decision_id": ("uuid", "YES"),
                    "basis_set_hash": ("bpchar", "NO"),
                    "content_hash": ("bpchar", "NO"),
                    "hash_scheme": ("varchar", "NO"),
                },
                "decision_basis_conclusions": {
                    "decision_id": ("uuid", "NO"),
                    "scientific_conclusion_version_id": ("uuid", "NO"),
                    "ordinal": ("int4", "NO"),
                },
                "decision_basis_reviews": {
                    "decision_id": ("uuid", "NO"),
                    "internal_review_record_id": ("uuid", "NO"),
                    "ordinal": ("int4", "NO"),
                },
            }
            assert actual == required
            foreign = conn.execute(
                text("""SELECT c.relname,a.attname,p.relname,pa.attname,k.confdeltype
              FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid
              JOIN pg_class p ON p.oid=k.confrelid
              JOIN pg_attribute a ON a.attrelid=c.oid AND a.attnum=k.conkey[1]
              JOIN pg_attribute pa ON pa.attrelid=p.oid AND pa.attnum=k.confkey[1]
              WHERE k.contype='f' AND c.relnamespace='public'::regnamespace
                AND c.relname=ANY(:names)"""),
                {"names": list(TABLES)},
            ).all()
            assert set(map(tuple, foreign)) == {
                ("decision_records", "project_id", "projects", "id", "r"),
                ("decision_records", "decided_by", "actors", "id", "r"),
                ("decision_records", "supersedes_decision_id", "decision_records", "id", "r"),
                ("decision_basis_conclusions", "decision_id", "decision_records", "id", "r"),
                (
                    "decision_basis_conclusions",
                    "scientific_conclusion_version_id",
                    "scientific_conclusion_versions",
                    "id",
                    "r",
                ),
                ("decision_basis_reviews", "decision_id", "decision_records", "id", "r"),
                (
                    "decision_basis_reviews",
                    "internal_review_record_id",
                    "internal_review_records",
                    "id",
                    "r",
                ),
            }
            indexes = conn.execute(
                text("""SELECT c.relname,array_agg(a.attname ORDER BY keys.ordinality)
              FROM pg_index i JOIN pg_class c ON c.oid=i.indrelid
              JOIN LATERAL unnest(i.indkey) WITH ORDINALITY keys(attnum,ordinality) ON true
              JOIN pg_attribute a ON a.attrelid=c.oid AND a.attnum=keys.attnum
              WHERE i.indisvalid AND c.relnamespace='public'::regnamespace AND c.relname=ANY(:names)
              GROUP BY c.relname,i.indexrelid"""),
                {"names": list(TABLES)},
            ).all()
            physical = {(table, tuple(cols)) for table, cols in indexes}
            assert {
                ("decision_records", ("project_id",)),
                ("decision_records", ("decided_by",)),
                ("decision_records", ("supersedes_decision_id",)),
                ("decision_basis_conclusions", ("scientific_conclusion_version_id",)),
                ("decision_basis_reviews", ("internal_review_record_id",)),
                ("decision_basis_conclusions", ("decision_id", "scientific_conclusion_version_id")),
                ("decision_basis_conclusions", ("decision_id", "ordinal")),
                ("decision_basis_reviews", ("decision_id", "internal_review_record_id")),
                ("decision_basis_reviews", ("decision_id", "ordinal")),
            } <= physical
    finally:
        engine.dispose()


def test_0042_empty_roundtrip_preserves_every_predecessor_table(phase2_database_url):
    config = _config(phase2_database_url)
    command.upgrade(config, PREVIOUS)
    engine = create_engine(phase2_database_url)
    try:
        with engine.connect() as conn:
            before = _tables(conn)
            catalog = _catalog(conn, before)
        command.upgrade(config, REVISION)
        command.downgrade(config, PREVIOUS)
        with engine.connect() as conn:
            assert _tables(conn) == before
            assert _catalog(conn, before) == catalog
            assert (
                conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                == PREVIOUS
            )
        command.upgrade(config, REVISION)
        with engine.connect() as conn:
            assert _tables(conn) == before | TABLES
            assert _catalog(conn, before) == catalog
            assert (
                conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                == REVISION
            )
    finally:
        engine.dispose()


def test_0042_downgrade_refuses_committed_history_without_loss(decision_env, phase2_database_url):
    service, _, actor, _, base = decision_env
    _review(decision_env)
    request = _command(decision_env)
    saved = service.record_decision(actor, request)
    engine = base[8]

    def history():
        with engine.connect() as conn:
            return tuple(
                tuple(conn.execute(text(f"SELECT * FROM {table} ORDER BY 1,2")).all())
                for table in sorted(TABLES)
            )

    with engine.connect() as conn:
        installed_revision = conn.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one()
    before = history()
    with pytest.raises(DBAPIError):
        command.downgrade(_config(phase2_database_url), PREVIOUS)
    assert history() == before
    with engine.connect() as conn:
        assert TABLES <= _tables(conn)
        assert (
            conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == installed_revision
        )
    assert service.record_decision(actor, request) == saved
