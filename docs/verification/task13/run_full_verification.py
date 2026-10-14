"""Run the entire suite against a newly created, then deleted PostgreSQL database."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(os.environ.get("RB_TASK13_RUN_DIR", ROOT / "docs/verification/task13"))


def main() -> int:
    os.chdir(ROOT)
    OUT.mkdir(parents=True, exist_ok=True)
    admin_url = os.environ["RB_TEST_ADMIN_URL"]
    database = "researchbase_task13_test_" + uuid4().hex
    admin = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    quoted = admin.dialect.identifier_preparer.quote(database)
    with admin.connect() as conn:
        version = conn.execute(text("SELECT version()")).scalar_one()
        assert int(conn.execute(text("SHOW server_version_num")).scalar_one()) // 10000 == 18
        conn.execute(text(f"CREATE DATABASE {quoted}"))
    env = dict(os.environ)
    env["DATABASE_URL"] = (
        make_url(admin_url).set(database=database).render_as_string(hide_password=False)
    )
    env["RB_TASK13_FULL_OUT"] = str(OUT / "full-sharded")
    invocation = [sys.executable, str(ROOT / "docs/verification/task13/run_full_sharded.py")]
    (OUT / "postgres-environment.json").write_text(
        json.dumps(
            {
                "server_version": version,
                "database": database,
                "command": invocation,
                "HG1_RUN_LOCAL": env.get("HG1_RUN_LOCAL"),
            },
            indent=2,
        )
        + "\n"
    )
    try:
        with (OUT / "initial-migration.log").open("w") as output:
            migration = subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                env=env,
                stdout=output,
                stderr=subprocess.STDOUT,
                check=False,
            )
        if migration.returncode:
            return migration.returncode
        result = subprocess.run(invocation, env=env, check=False)
        return result.returncode
    finally:
        with admin.connect() as conn:
            conn.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname=:database AND pid<>pg_backend_pid()"
                ),
                {"database": database},
            )
            conn.execute(text(f"DROP DATABASE {quoted}"))
            assert not conn.execute(
                text("SELECT EXISTS(SELECT 1 FROM pg_database WHERE datname=:name)"),
                {"name": database},
            ).scalar_one()
        admin.dispose()
        (OUT / "shared-database-cleanup.json").write_text(
            json.dumps({"database": database, "dropped": True}) + "\n"
        )


if __name__ == "__main__":
    raise SystemExit(main())
