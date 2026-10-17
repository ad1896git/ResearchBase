"""Read-only HG1-01 Runner verification against the durable four-M2 deployment."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from researchbase.host_config import load_host_settings
from researchbase.runner import request as runner_request


@pytest.fixture
def local_deployments(tmp_path, monkeypatch):
    """Own four disposable databases and onboard real installations for this host."""
    root = tmp_path.resolve()
    base_url = make_url(os.environ["DATABASE_URL"])
    admin = create_engine(os.environ["RB_TEST_ADMIN_URL"])
    created = []
    evidence = {}
    try:
        with admin.connect() as connection:
            socket_dir, port = connection.execute(
                text("SELECT current_setting('unix_socket_directories'), current_setting('port')")
            ).one()
        monkeypatch.setenv("RB_HOST_DURABLE_ROOT", str(root))
        monkeypatch.setenv("RB_HOST_OWNER_UID", str(os.geteuid()))
        monkeypatch.setenv("RB_HOST_DATABASE_USER", base_url.username)
        monkeypatch.setenv("RB_HOST_SOCKET_DIR", socket_dir.split(",")[0].strip())
        monkeypatch.setenv("RB_HOST_DATABASE_PORT", port)
        monkeypatch.setenv("RB_HOST_TRUST_ROOT", str(root / "absent-policy"))
        monkeypatch.setenv("RB_HOST_RUNNER_SOCKET_DIR", str(Path("/tmp").resolve()))
        for tag in ("final", "live", "live2", "live3"):
            name = f"researchbase_t8_{uuid4().hex}"
            with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
                connection.execute(text(f'CREATE DATABASE "{name}"'))
            created.append(name)
            monkeypatch.setenv(f"RB_HOST_M2_{tag.upper()}_DATABASE", name)
            host = load_host_settings()
            url = base_url.set(
                username=host.database_user,
                password=None,
                host=None,
                port=None,
                database=name,
                query={"host": host.socket_dir, "port": host.database_port},
            ).render_as_string(hide_password=False)
            config = Config("alembic.ini")
            config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
            monkeypatch.setenv("DATABASE_URL", url)
            command.upgrade(config, "head")
            env = dict(
                os.environ,
                DATABASE_URL=url,
                RESEARCHBASE_LOCAL_ROOT=str(root / f"rb-m2-{tag}-installation"),
                ARTIFACT_STORE_ROOT=str(root / f"rb-m2-{tag}-artifacts"),
            )

            def cli(*args, env=env):
                result = subprocess.run(
                    [sys.executable, "-m", "researchbase.cli.main", "local", *args, "--json"],
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                assert result.returncode == 0, result.stderr
                return json.loads(result.stdout.splitlines()[-1])

            cli("init")
            bootstrap = cli(
                "bootstrap",
                "--display-name",
                "Local runner test",
                "--project-name",
                "Runner verification",
            )
            identity = cli("whoami")
            evidence[tag] = {
                "projects_read": [bootstrap["project_id"]],
                "deployment_id": identity["deployment_id"],
            }
        yield root, evidence
    finally:
        for name in created:
            with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
                connection.execute(
                    text(
                        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                        "WHERE datname = :name AND pid <> pg_backend_pid()"
                    ),
                    {"name": name},
                )
                connection.execute(text(f'DROP DATABASE "{name}"'))
        admin.dispose()


def test_four_durable_deployments_authenticate_and_clean_up(request):
    if os.environ.get("HG1_RUN_LOCAL") == "1":
        root, evidence = request.getfixturevalue("local_deployments")
    elif os.environ.get("HG1_RUN_LIVE") != "1":
        pytest.skip("set HG1_RUN_LIVE=1 for the authorized read-only M2 check")
    else:
        root = load_host_settings().durable_root
        evidence = json.loads(
            (root / "migration-evidence/postcutover-cli-verification.json").read_text()
        )
    host = load_host_settings()
    source = Path(__file__).resolve().parents[3] / "src"
    for tag, db in zip(("final", "live", "live2", "live3"), host.m2_databases, strict=True):
        project_id = evidence[tag]["projects_read"][0]
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(source),
            "DATABASE_URL": (
                make_url("postgresql+psycopg://")
                .set(
                    username=host.database_user,
                    database=db,
                    query={"host": host.socket_dir, "port": host.database_port},
                )
                .render_as_string(hide_password=False)
            ),
            "RESEARCHBASE_LOCAL_ROOT": str(root / f"rb-m2-{tag}-installation"),
            "ARTIFACT_STORE_ROOT": str(root / f"rb-m2-{tag}-artifacts"),
            "PGOPTIONS": "-c TimeZone=UTC",
        }
        process = subprocess.Popen(
            [sys.executable, "-m", "researchbase.runner", "--max-requests", "2"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert process.stdout is not None
        path = Path(process.stdout.readline().strip())
        try:
            assert path.is_socket()
            who = runner_request(path, {"v": 1, "op": "whoami"})
            project = runner_request(path, {"v": 1, "op": "project.get", "project_id": project_id})
            _, errors = process.communicate(timeout=15)
            assert process.returncode == 0, errors
            assert who["ok"] is True
            assert who["result"]["deployment_id"] == evidence[tag]["deployment_id"]
            assert project["ok"] is True
            assert project["result"]["id"] == project_id
            assert not path.exists()
            assert not path.parent.exists()
        finally:
            if process.poll() is None:
                process.terminate()
                process.communicate(timeout=5)
