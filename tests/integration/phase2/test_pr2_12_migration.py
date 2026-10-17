"""PR2-12 clean and frozen-0018 upgrade paths on disposable PostgreSQL."""

from __future__ import annotations

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from tests.disposable_postgres import disposable_database

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("start", ["base", "0018_current_pointer_same_parent_integrity"])
def test_upgrade_to_pr212_and_empty_downgrade(start, monkeypatch):
    with disposable_database("researchbase_pr212_test_", "RB_PR210_TEST_ADMIN_URL") as url:
        monkeypatch.setenv("DATABASE_URL", url)
        config = Config("alembic.ini")
        config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
        if start != "base":
            command.upgrade(config, start)
        command.upgrade(config, "0034_pr2_10_exact_transcript_binding")
        engine = create_engine(url)
        with engine.connect() as conn:
            prior_indexes = set(
                conn.execute(
                    text("""SELECT schemaname,tablename,
              indexname,indexdef FROM pg_indexes WHERE schemaname='public'""")
                ).all()
            )
            prior_tables = set(
                conn.execute(
                    text("""SELECT tablename FROM pg_tables
              WHERE schemaname='public'""")
                )
                .scalars()
                .all()
            )
        engine.dispose()
        # This test verifies the exact PR2-12 revision, not later Phase 2 heads.
        command.upgrade(config, "0035_pr2_12_publication_draft")
        engine = create_engine(url)
        with engine.connect() as conn:
            assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
                "0035_pr2_12_publication_draft"
            )
            for table in ("publications", "publication_lifecycle_events", "manuscript_versions"):
                assert (
                    conn.execute(text("SELECT to_regclass(:name)"), {"name": table}).scalar_one()
                    == table
                )
            columns = (
                conn.execute(
                    text("""SELECT column_name FROM information_schema.columns
              WHERE table_name='manuscript_versions'""")
                )
                .scalars()
                .all()
            )
            assert "hash_scheme" in columns
            assert (
                conn.execute(
                    text("""SELECT count(*) FROM information_schema.columns
              WHERE table_name='manuscript_versions' AND column_name='hash_scheme'
                AND is_nullable='NO'""")
                ).scalar_one()
                == 1
            )
            indexes = conn.execute(
                text("""SELECT t.relname, i.relname, am.amname,
              x.indisunique, pg_get_expr(x.indpred,x.indrelid),
              pg_get_indexdef(i.oid)
              FROM pg_class t JOIN pg_index x ON x.indrelid=t.oid
              JOIN pg_class i ON i.oid=x.indexrelid
              JOIN pg_am am ON am.oid=i.relam
              WHERE t.relname IN ('publications','manuscript_versions',
                'publication_lifecycle_events')""")
            ).all()
            for table, column in (
                ("publications", "created_by"),
                ("manuscript_versions", "created_by"),
                ("publication_lifecycle_events", "actor_id"),
            ):
                matching = [
                    row
                    for row in indexes
                    if row[0] == table and row[5].endswith(f"USING btree ({column})")
                ]
                assert len(matching) == 1, (table, column, indexes)
                assert matching[0][2:5] == ("btree", False, None)
                fk = conn.execute(
                    text("""SELECT count(*) FROM pg_constraint c
                  JOIN pg_class t ON t.oid=c.conrelid
                  JOIN pg_attribute a ON a.attrelid=t.oid AND a.attnum=ANY(c.conkey)
                  WHERE t.relname=:table AND a.attname=:column AND c.contype='f'"""),
                    {"table": table, "column": column},
                ).scalar_one()
                assert fk == 1
        engine.dispose()
        command.downgrade(config, "0034_pr2_10_exact_transcript_binding")
        engine = create_engine(url)
        with engine.connect() as conn:
            assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
                "0034_pr2_10_exact_transcript_binding"
            )
            assert (
                set(
                    conn.execute(
                        text("""SELECT schemaname,tablename,indexname,indexdef
              FROM pg_indexes WHERE schemaname='public'""")
                    ).all()
                )
                == prior_indexes
            )
            assert (
                set(
                    conn.execute(
                        text("""SELECT tablename FROM pg_tables
              WHERE schemaname='public'""")
                    )
                    .scalars()
                    .all()
                )
                == prior_tables
            )
        engine.dispose()
