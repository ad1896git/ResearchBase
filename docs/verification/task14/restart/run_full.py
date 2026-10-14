"""Run every collected test once, with serial Phase 1 and four isolated Phase 2 shards."""

import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent / "full"


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + "\n")


def key(node):
    path, selection = node.split("::", 1)
    head, bracket, parameters = selection.partition("[")
    names = head.split("::")
    return (
        ".".join([path[:-3].replace("/", "."), *names[:-1]]),
        names[-1] + bracket + parameters,
    )


def run_group(index, group, env):
    args = ["tests", "--ignore=tests/integration/phase2"] if index == 0 else group
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-o",
        "addopts=",
        "-q",
        "-ra",
        "-p",
        "no:cacheprovider",
        f"--junitxml={OUT / f'shard-{index}.xml'}",
        *args,
    ]
    save(f"shard-{index}-command.json", command)
    with (OUT / f"shard-{index}.log").open("w") as stream:
        child = subprocess.Popen(
            command, env=env, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT
        )
        save(f"shard-{index}-process.json", {"pid": child.pid})
        code = child.wait()
    save(f"shard-{index}-exit.json", {"exit_code": code})
    return code


def main():
    OUT.mkdir(exist_ok=True)
    admin_url = os.environ["RB_TEST_ADMIN_URL"]
    admin = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    database = "researchbase_task14_full_" + uuid4().hex
    quoted = admin.dialect.identifier_preparer.quote(database)
    with admin.connect() as conn:
        version = conn.execute(text("SELECT version()")).scalar_one()
        assert int(conn.execute(text("SHOW server_version_num")).scalar_one()) // 10000 == 18
        conn.execute(text(f"CREATE DATABASE {quoted}"))
    env = dict(os.environ)
    env.pop("PYTEST_ADDOPTS", None)
    env["DATABASE_URL"] = (
        make_url(admin_url).set(database=database).render_as_string(hide_password=False)
    )
    save(
        "environment.json",
        {
            "server_version": version,
            "DATABASE_URL": env["DATABASE_URL"],
            "RB_TEST_ADMIN_URL": admin_url,
            "HG1_RUN_LOCAL": env.get("HG1_RUN_LOCAL"),
            "HG1_RUN_LIVE": env.get("HG1_RUN_LIVE"),
        },
    )
    try:
        with (OUT / "migration.log").open("w") as stream:
            migration = subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                env=env,
                cwd=ROOT,
                stdout=stream,
                stderr=subprocess.STDOUT,
            )
        assert migration.returncode == 0
        collection_command = [
            sys.executable,
            "-m",
            "pytest",
            "-o",
            "addopts=",
            "-q",
            "--collect-only",
            "-p",
            "no:cacheprovider",
        ]
        save("collection-command.json", collection_command)
        collected = subprocess.run(
            collection_command, env=env, cwd=ROOT, text=True, capture_output=True, check=True
        )
        (OUT / "collection.log").write_text(collected.stdout + collected.stderr)
        nodes = [
            line
            for line in collected.stdout.splitlines()
            if line.startswith("tests/") and "::" in line
        ]
        assert len(nodes) == len(set(nodes))
        phase2 = [n for n in nodes if n.startswith("tests/integration/phase2/")]
        groups = [[n for n in nodes if n not in set(phase2)], *[phase2[i::4] for i in range(4)]]
        save("partition.json", {"collected": len(nodes), "groups": groups})
        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = [pool.submit(run_group, i, group, env) for i, group in enumerate(groups)]
            exits = [future.result() for future in futures]
        cases = {}
        for index in range(len(groups)):
            for case in ET.parse(OUT / f"shard-{index}.xml").iter("testcase"):
                identity = (case.attrib["classname"], case.attrib["name"])
                assert identity not in cases, identity
                status = next(
                    (tag for tag in ("failure", "error", "skipped") if case.find(tag) is not None),
                    "passed",
                )
                cases[identity] = status
        expected = {key(node) for node in nodes}
        assert len(expected) == len(nodes)
        assert set(cases) == expected, {
            "missing": sorted(expected - set(cases)),
            "extra": sorted(set(cases) - expected),
        }
        totals = {
            status: list(cases.values()).count(status)
            for status in ("passed", "failure", "error", "skipped")
        }
        report = {
            "collected": len(nodes),
            "unique_results": len(cases),
            "totals": totals,
            "exits": exits,
            "coverage": "Every collected test has exactly one JUnit result",
        }
        save("summary.json", report)
        print(json.dumps(report), flush=True)
        return int(any(exits) or totals["failure"] or totals["error"])
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
        save("cleanup.json", {"database": database, "dropped": True})


if __name__ == "__main__":
    raise SystemExit(main())
