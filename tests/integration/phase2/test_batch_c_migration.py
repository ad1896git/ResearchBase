"""Real PostgreSQL empty upgrade/downgrade of the integrated linear history."""

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

pytestmark = pytest.mark.integration


def test_batch_c_empty_database_roundtrip(phase2_database_url):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    engine = create_engine(phase2_database_url)
    try:
        command.upgrade(config, "head")
        with engine.connect() as conn:
            assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
                "0069_b13_stale_gate_denials"
            )
        command.downgrade(config, "base")
        with engine.connect() as conn:
            assert conn.execute(text("SELECT count(*) FROM alembic_version")).scalar_one() == 0
        command.upgrade(config, "head")
    finally:
        engine.dispose()


def test_batch_c_downgrade_restores_exact_b11_schema(phase2_database_url, tmp_path):
    """Compare complete pg_dump schemas before/after the B09/B10 round trip."""
    import hashlib
    import re
    import shutil
    import subprocess

    from sqlalchemy.engine import make_url

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    executable = shutil.which("pg_dump")
    assert executable is not None, "pg_dump is required for full-schema downgrade comparison"
    database_url = make_url(phase2_database_url).set(drivername="postgresql")

    def schema():
        result = subprocess.run(
            [
                executable,
                "--schema-only",
                "--no-owner",
                "--no-privileges",
                "--dbname",
                database_url.render_as_string(hide_password=False),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        # PostgreSQL 18 generates a random psql restrict key for each dump.
        dump = re.sub(r"^\\(?:un)?restrict .*\n", "", result.stdout, flags=re.MULTILINE)
        # Frozen B09 restores pr216_event_insert with different indentation and
        # splits this existing statement onto two lines. Compare all schema DDL
        # after only these known presentation differences, preserving literals.
        dump = dump.replace("END IF; RETURN NEW;", "END IF;\nRETURN NEW;")
        return "\n".join(line.strip() for line in dump.splitlines() if line.strip())

    command.upgrade(config, "0054_b11_ready_for_submission")
    before = schema()
    command.upgrade(config, "0056_b10_reconsideration")
    command.downgrade(config, "0054_b11_ready_for_submission")
    after = schema()
    (tmp_path / "before.sql").write_text(before)
    (tmp_path / "after.sql").write_text(after)
    print("Schema comparison artifacts:", tmp_path)
    assert after == before
    print("B11 schema before/after SHA256:", hashlib.sha256(before.encode()).hexdigest())
    command.upgrade(config, "0056_b10_reconsideration")
