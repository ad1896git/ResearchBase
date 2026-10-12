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
            assert "hash_scheme" not in columns
        engine.dispose()
        command.downgrade(config, "0034_pr2_10_exact_transcript_binding")
    finally:
        with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.execute(text("""SELECT pg_terminate_backend(pid) FROM pg_stat_activity
              WHERE datname=:name AND pid<>pg_backend_pid()"""), {"name": name})
            conn.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))
        admin.dispose()
