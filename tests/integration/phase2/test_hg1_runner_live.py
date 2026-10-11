"""Read-only HG1-01 Runner verification against the durable four-M2 deployment."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from researchbase.runner import request


def test_four_durable_deployments_authenticate_and_clean_up():
    if os.environ.get("HG1_RUN_LIVE") != "1":
        pytest.skip("set HG1_RUN_LIVE=1 for the authorized read-only M2 check")
    root = Path("/Users/onephone/ResearchBaseData")
    evidence = json.loads(
        (root / "migration-evidence/postcutover-cli-verification.json").read_text()
    )
    source = Path(__file__).resolve().parents[3] / "src"
    for tag in ("final", "live", "live2", "live3"):
        db = f"researchbase_m2_{tag}"
        project_id = evidence[tag]["projects_read"][0]
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(source),
            "DATABASE_URL": (
                f"postgresql+psycopg://onephone@/{db}?host=%2Fprivate%2Ftmp&port=55440"
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
            who = request(path, {"v": 1, "op": "whoami"})
            project = request(path, {"v": 1, "op": "project.get", "project_id": project_id})
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
