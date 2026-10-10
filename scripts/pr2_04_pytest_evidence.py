"""Test-only observation recorder; acceptance is decided by the evidence validator."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from scripts.pr2_04_verification_matrix import _requirements

OBSERVATIONS: pytest.StashKey[list[dict[str, Any]]] = pytest.StashKey()


def _fact_json(value: Any) -> str:
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, UUID | Decimal):
        return str(value)
    raise TypeError("observations must be JSON values or typed database scalars")


class FactRecorder:
    def __init__(self, observations: list[dict[str, Any]]) -> None:
        self._observations = observations

    def record(self, **facts: Any) -> None:
        if not facts:
            raise ValueError("an observation must contain facts")
        if set(facts) & {
            "requirement_acceptance",
            "requirement_result",
            "acceptance",
            "acceptance_status",
            "requirement_status",
        }:
            raise ValueError("the factual recorder cannot declare requirement acceptance")
        # JSON roundtrip captures values at observation time; caller-owned objects cannot mutate it.
        self._observations.append(
            json.loads(json.dumps(facts, allow_nan=False, default=_fact_json))
        )


@pytest.fixture
def pr204_trace(request: pytest.FixtureRequest) -> FactRecorder:
    observations: list[dict[str, Any]] = []
    request.node.stash[OBSERVATIONS] = observations
    return FactRecorder(observations)


class EvidencePlugin:
    def __init__(self, config: pytest.Config) -> None:
        source_root = Path(__file__).resolve().parents[1]
        self.known_ids = {
            row["requirement"]
            for row in _requirements(
                source_root / "execution/phase2/PR2-04_Acceptance_Matrix_v1.0.md"
            )
        }
        self.root = Path(config.rootpath).resolve()
        self.items: dict[str, pytest.Item] = {}
        self.tests: dict[str, dict[str, Any]] = {}
        values = [
            os.environ.get(name)
            for name in ("PR204_EVIDENCE_DIR", "PR204_RUN_ID", "PR204_CANDIDATE_HEAD")
        ]
        self.output: Path | None = None
        self.run_id = values[1]
        self.head = values[2]
        if any(values):
            if not all(values):
                raise pytest.UsageError(
                    "PR2-04 evidence requires directory, run ID and candidate SHA"
                )
            actual_head = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=source_root, text=True
            ).strip()
            if actual_head != self.head:
                raise pytest.UsageError("PR2-04 evidence candidate differs from checkout HEAD")
            self.output = Path(str(values[0])).resolve()
            if self.root not in self.output.parents:
                raise pytest.UsageError("PR2-04 evidence directory must be within pytest root")
            if (self.output / "pytest_ledger.json").exists():
                raise pytest.UsageError("PR2-04 evidence run directory cannot be reused")

    def pytest_collection_modifyitems(self, items: list[pytest.Item]) -> None:
        for item in items:
            requirements = [
                requirement
                for marker in item.iter_markers("pr204_requirements")
                for requirement in marker.args
            ]
            if not requirements:
                continue
            if (
                any(not isinstance(req, str) for req in requirements)
                or set(requirements) - self.known_ids
                or len(set(requirements)) != len(requirements)
            ):
                raise pytest.UsageError(
                    f"unknown or duplicate PR2-04 requirement marker: {item.nodeid}"
                )
            self.items[item.nodeid] = item
            self.tests[item.nodeid] = {
                "node_id": item.nodeid,
                "requirements": sorted(requirements),
                "phases": {},
                "trace": None,
            }

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        if report.nodeid in self.tests:
            phases = self.tests[report.nodeid]["phases"]
            if report.when in phases:
                raise pytest.UsageError("PR2-04 evidence prohibits hidden test reruns")
            phases[report.when] = "skipped" if hasattr(report, "wasxfail") else report.outcome

    def pytest_sessionfinish(self) -> None:
        if self.output is None:
            return
        self.output.mkdir(parents=True, exist_ok=True)
        trace_dir = self.output / "traces"
        trace_dir.mkdir(exist_ok=True)
        for node, test in self.tests.items():
            observations = self.items[node].stash.get(OBSERVATIONS, [])
            if not observations:
                continue
            name = hashlib.sha256(node.encode()).hexdigest() + ".json"
            path = trace_dir / name
            if path.exists():
                raise pytest.UsageError("PR2-04 trace path already exists in this run")
            payload = {
                "schema_version": "pr204-observed-facts-v1",
                "run_id": self.run_id,
                "execution_head": self.head,
                "node_id": node,
                "requirements": test["requirements"],
                "facts": {"observations": observations},
            }
            path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
            test["trace"] = {
                "path": str(path.relative_to(self.root)),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        ledger = {
            "schema_version": "pr204-pytest-ledger-v1",
            "run_id": self.run_id,
            "execution_head": self.head,
            "tests": list(self.tests.values()),
        }
        (self.output / "pytest_ledger.json").write_text(
            json.dumps(ledger, indent=2, sort_keys=True) + "\n"
        )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "pr204_requirements(*ids): explicit PR2-04 evidence bindings"
    )
    config.pluginmanager.register(EvidencePlugin(config), "pr204-factual-evidence")
