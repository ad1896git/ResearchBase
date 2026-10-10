"""Observe an unselected full pytest run for the PR2-04 host acceptance checks."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest


class SuiteProbe:
    def __init__(self, config: pytest.Config, output: Path):
        self.config, self.output = config, output
        self.root = Path(config.rootpath).resolve()
        self.head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.root, text=True).strip()
        if self.head != os.environ["RB_EXECUTION_HEAD"] or output.exists():
            raise pytest.UsageError("suite probe requires exact candidate and a fresh output path")
        self.started = datetime.now(UTC).isoformat()
        self.nodes: list[str] = []
        self.phases: dict[str, dict[str, str]] = {}
        self.warning_categories: list[str] = []
        self.collection_errors: list[str] = []
        self.clean = not subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=no"], cwd=self.root, text=True
        )

    def pytest_collection_finish(self, session):
        self.nodes = [item.nodeid for item in session.items]

    def pytest_collectreport(self, report):
        if report.failed:
            self.collection_errors.append(report.nodeid)

    def pytest_runtest_logreport(self, report):
        phase = self.phases.setdefault(report.nodeid, {})
        if report.when in phase:
            raise pytest.UsageError("full-suite probe prohibits hidden reruns")
        phase[report.when] = "skipped" if hasattr(report, "wasxfail") else report.outcome

    def pytest_warning_recorded(self, warning_message):
        self.warning_categories.append(warning_message.category.__name__)

    @pytest.hookimpl(trylast=True)
    def pytest_sessionfinish(self, session, exitstatus):
        payload = {
            "schema_version": "pr204-full-suite-observation-v1",
            "execution_head": self.head,
            "run_id": os.environ["PR204_HOST_RUN_ID"],
            "started_at_utc": self.started,
            "finished_at_utc": datetime.now(UTC).isoformat(),
            "tracked_worktree_clean": self.clean,
            "invocation": list(self.config.invocation_params.args),
            "exit_code": int(exitstatus),
            "collected": self.nodes,
            "phases": self.phases,
            "warning_categories": self.warning_categories,
            "collection_errors": self.collection_errors,
            "deselected": len(self.config.pluginmanager.get_plugin("terminalreporter").stats.get("deselected", [])),
        }
        self.output.parent.mkdir(parents=True, exist_ok=True)
        self.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def pytest_configure(config: pytest.Config):
    path = os.environ.get("PR204_FULL_SUITE_RECORD")
    if path:
        config.pluginmanager.register(SuiteProbe(config, Path(path)), "pr204-full-suite-probe")
