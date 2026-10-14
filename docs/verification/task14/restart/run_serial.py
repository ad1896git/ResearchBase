"""Run the complete suite on disposable PostgreSQL 18 and preserve exact output."""

import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    admin_url = os.environ["RB_TEST_ADMIN_URL"]
    database = "researchbase_task14_restart_" + uuid4().hex
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
    invocation = [
        sys.executable,
        "-m",
        "pytest",
        "-o",
        "addopts=",
        "-q",
        "-ra",
        "-p",
        "no:cacheprovider",
        f"--junitxml={OUT / 'full-final.xml'}",
        "tests",
    ]
    (OUT / "full-environment.json").write_text(
        json.dumps(
            {
                "server_version": version,
                "database": database,
                "command": invocation,
                "HG1_RUN_LOCAL": env.get("HG1_RUN_LOCAL"),
                "DATABASE_URL": env["DATABASE_URL"],
                "RB_TEST_ADMIN_URL": admin_url,
            },
            indent=2,
        )
        + "\n"
    )
    try:
        with (OUT / "full-migration.log").open("w") as stream:
            migration = subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                env=env,
                cwd=ROOT,
                stdout=stream,
                stderr=subprocess.STDOUT,
                check=False,
            )
        if migration.returncode:
            return migration.returncode
        with (OUT / "full-final.log").open("w") as stream:
            result = subprocess.run(
                invocation, env=env, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, check=False
            )
        (OUT / "full-exit.json").write_text(json.dumps({"exit_code": result.returncode}) + "\n")
        return result.returncode
    finally:
        with admin.connect() as conn:
            conn.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname=:name AND pid<>pg_backend_pid()"
                ),
                {"name": database},
            )
            conn.execute(text(f"DROP DATABASE {quoted}"))
            assert not conn.execute(
                text("SELECT EXISTS(SELECT 1 FROM pg_database WHERE datname=:name)"),
                {"name": database},
            ).scalar_one()
        admin.dispose()
        (OUT / "full-cleanup.json").write_text(
            json.dumps({"database": database, "dropped": True}) + "\n"
        )


if __name__ == "__main__":
    raise SystemExit(main())
