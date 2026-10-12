"""PR2-12 clean and frozen-0018 upgrade paths on disposable PostgreSQL."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

pytestmark = pytest.mark.integration
ADMIN_URL = "postgresql+psycopg://onephone@/postgres?host=/private/tmp&port=55442"


@pytest.mark.parametrize("start", ["base", "0018_current_pointer_same_parent_integrity"])
def test_upgrade_to_pr212_and_empty_downgrade(start):
    if os.getenv("RB_PR210_TEST_ADMIN_URL") != ADMIN_URL:
        pytest.fail("exact approved disposable PostgreSQL selector required")
    admin = create_engine(ADMIN_URL)
    with admin.connect() as conn:
        identity = conn.execute(text("""SELECT current_user,current_database(),
          current_setting('port'),current_setting('data_directory'),
          (SELECT system_identifier FROM pg_control_system())""")).one()
    assert tuple(map(str, identity)) == (
        "onephone", "postgres", "55442", "/private/tmp/rb-m3-postgres",
        "7695073913076924777",
    )
    name = f"researchbase_pr212_test_{uuid4().hex}"
    with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        assert not conn.execute(text("SELECT 1 FROM pg_database WHERE datname=:name"),
                                {"name": name}).first()
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    url = f"postgresql+psycopg://onephone@/{name}?host=/private/tmp&port=55442"
    try:
        config = Config("alembic.ini")
        config.set_main_option("sqlalchemy.url", url)
        if start != "base":
            command.upgrade(config, start)
        command.upgrade(config, "0034_pr2_10_exact_transcript_binding")
        engine = create_engine(url)
        with engine.connect() as conn:
            prior_indexes = set(conn.execute(text("""SELECT schemaname,tablename,
              indexname,indexdef FROM pg_indexes WHERE schemaname='public'""")).all())
            prior_tables = set(conn.execute(text("""SELECT tablename FROM pg_tables
              WHERE schemaname='public'""")).scalars().all())
        engine.dispose()
        command.upgrade(config, "head")
        engine = create_engine(url)
        with engine.connect() as conn:
            assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
                "0035_pr2_12_publication_draft"
            )
            for table in ("publications", "publication_lifecycle_events",
                          "manuscript_versions"):
                assert conn.execute(text("SELECT to_regclass(:name)"),
                                    {"name": table}).scalar_one() == table
            columns = conn.execute(text("""SELECT column_name FROM information_schema.columns
              WHERE table_name='manuscript_versions'""")).scalars().all()
            assert "hash_scheme" in columns
            assert conn.execute(text("""SELECT count(*) FROM information_schema.columns
              WHERE table_name='manuscript_versions' AND column_name='hash_scheme'
                AND is_nullable='NO'""")).scalar_one() == 1
            indexes = conn.execute(text("""SELECT t.relname, i.relname, am.amname,
              x.indisunique, pg_get_expr(x.indpred,x.indrelid),
              pg_get_indexdef(i.oid)
              FROM pg_class t JOIN pg_index x ON x.indrelid=t.oid
              JOIN pg_class i ON i.oid=x.indexrelid
              JOIN pg_am am ON am.oid=i.relam
              WHERE t.relname IN ('publications','manuscript_versions',
                'publication_lifecycle_events')""")).all()
            for table, column in (
                ("publications", "created_by"),
                ("manuscript_versions", "created_by"),
                ("publication_lifecycle_events", "actor_id"),
            ):
                matching = [row for row in indexes if row[0] == table
                            and row[5].endswith(f"USING btree ({column})")]
                assert len(matching) == 1, (table, column, indexes)
                assert matching[0][2:5] == ("btree", False, None)
                fk = conn.execute(text("""SELECT count(*) FROM pg_constraint c
                  JOIN pg_class t ON t.oid=c.conrelid
                  JOIN pg_attribute a ON a.attrelid=t.oid AND a.attnum=ANY(c.conkey)
                  WHERE t.relname=:table AND a.attname=:column AND c.contype='f'"""),
                                  {"table": table, "column": column}).scalar_one()
                assert fk == 1
        engine.dispose()
        command.downgrade(config, "0034_pr2_10_exact_transcript_binding")
        engine = create_engine(url)
        with engine.connect() as conn:
            assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
                "0034_pr2_10_exact_transcript_binding"
            )
            assert set(conn.execute(text("""SELECT schemaname,tablename,indexname,indexdef
              FROM pg_indexes WHERE schemaname='public'""")).all()) == prior_indexes
            assert set(conn.execute(text("""SELECT tablename FROM pg_tables
              WHERE schemaname='public'""")).scalars().all()) == prior_tables
        engine.dispose()
    finally:
        with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.execute(text("""SELECT pg_terminate_backend(pid) FROM pg_stat_activity
              WHERE datname=:name AND pid<>pg_backend_pid()"""), {"name": name})
            conn.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))
        admin.dispose()
