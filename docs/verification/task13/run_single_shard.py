"""Reverify one entire unchanged partition after a compatibility-test correction."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "docs/verification/task13/final-run"


def main() -> int:
    os.chdir(ROOT)
    index = int(sys.argv[1])
    assert index in range(1, 5)
    partition = json.loads((OUT / "full-sharded/partition.json").read_text())
    group = partition["groups"][index]
    assert all(node.startswith("tests/integration/phase2/") for node in group)
    admin_url = os.environ["RB_TEST_ADMIN_URL"]
    database = "researchbase_task13_shard_test_" + uuid4().hex
    admin = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    quoted = admin.dialect.identifier_preparer.quote(database)
    with admin.connect() as conn:
        assert int(conn.execute(text("SHOW server_version_num")).scalar_one()) // 10000 == 18
        conn.execute(text(f"CREATE DATABASE {quoted}"))
    env = dict(os.environ)
    env["DATABASE_URL"] = (
        make_url(admin_url).set(database=database).render_as_string(hide_password=False)
    )
    stem = f"repaired-shard-{index}"
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
        f"--junitxml={OUT / (stem + '.xml')}",
        *group,
    ]
    (OUT / (stem + "-command.json")).write_text(json.dumps(invocation, indent=2) + "\n")
    try:
        with (OUT / (stem + "-migration.log")).open("w") as output:
            bootstrap = subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                env=env,
                stdout=output,
                stderr=subprocess.STDOUT,
                check=False,
            )
        assert bootstrap.returncode == 0
        with (OUT / (stem + ".log")).open("w") as output:
            result = subprocess.run(
                invocation, env=env, stdout=output, stderr=subprocess.STDOUT, check=False
            )
        suite = ET.parse(OUT / (stem + ".xml")).find("testsuite")
        assert suite is not None
        assert int(suite.get("tests", "0")) == len(group)
        (OUT / (stem + "-exit.json")).write_text(
            json.dumps({"exit_code": result.returncode}) + "\n"
        )
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
        (OUT / (stem + "-cleanup.json")).write_text(
            json.dumps({"database": database, "dropped": True}) + "\n"
        )


if __name__ == "__main__":
    raise SystemExit(main())
