"""Repeat the complete shared-database shard after migrating a fresh PostgreSQL DB."""

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
OUT = ROOT / "docs/verification/task13"


def main() -> int:
    os.chdir(ROOT)
    admin_url = os.environ["RB_TEST_ADMIN_URL"]
    database = "researchbase_task13_shared_test_" + uuid4().hex
    admin = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    quoted = admin.dialect.identifier_preparer.quote(database)
    with admin.connect() as conn:
        assert int(conn.execute(text("SHOW server_version_num")).scalar_one()) // 10000 == 18
        conn.execute(text(f"CREATE DATABASE {quoted}"))
    env = dict(os.environ)
    env["DATABASE_URL"] = (
        make_url(admin_url).set(database=database).render_as_string(hide_password=False)
    )
    commands = [
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        [
            sys.executable,
            "-m",
            "pytest",
            "-o",
            "addopts=",
            "-q",
            "-ra",
            "-p",
            "no:cacheprovider",
            f"--junitxml={OUT / 'shared-final.xml'}",
            "tests",
            "--ignore=tests/integration/phase2",
        ],
    ]
    (OUT / "shared-commands.json").write_text(
        json.dumps({"database": database, "commands": commands}, indent=2) + "\n"
    )
    try:
        for invocation, log in zip(
            commands, ("shared-migration.log", "shared-final.log"), strict=True
        ):
            with (OUT / log).open("w") as output:
                result = subprocess.run(
                    invocation, env=env, stdout=output, stderr=subprocess.STDOUT, check=False
                )
            if result.returncode:
                return result.returncode
        return 0
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
        (OUT / "shared-retry-cleanup.json").write_text(
            json.dumps({"database": database, "dropped": True}) + "\n"
        )


if __name__ == "__main__":
    raise SystemExit(main())
