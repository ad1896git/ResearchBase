"""Verify every final collected node has actual passing XML evidence exactly once."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "docs/verification/task13"
RUN = OUT / "final-run"


def case_key(node: str) -> tuple[str, str]:
    path, selection = node.split("::", 1)
    head, bracket, parameters = selection.partition("[")
    names = head.split("::")
    classname = ".".join([path[:-3].replace("/", "."), *names[:-1]])
    return classname, names[-1] + bracket + parameters


def main() -> None:
    os.chdir(ROOT)
    partition = json.loads((RUN / "full-sharded/partition.json").read_text())
    collection = subprocess.run(
        [sys.executable, "-m", "pytest", "-o", "addopts=", "-q", "--collect-only"],
        text=True,
        capture_output=True,
        check=True,
    )
    (OUT / "final-collection.log").write_text(collection.stdout + collection.stderr)
    collected = [
        line
        for line in collection.stdout.splitlines()
        if line.startswith("tests/") and "::" in line
    ]
    selected = [node for group in partition["groups"] for node in group]
    assert len(selected) == len(set(selected)) == len(collected) == partition["collected"]
    assert set(selected) == set(collected)
    evidence = []
    total = 0
    for index, group in enumerate(partition["groups"]):
        stem = RUN / "repaired-shard-4" if index == 4 else RUN / "full-sharded" / f"shard-{index}"
        assert json.loads(stem.with_name(stem.name + "-exit.json").read_text())["exit_code"] == 0
        suite = ET.parse(stem.with_suffix(".xml")).find("testsuite")
        assert suite is not None
        cases = suite.findall("testcase")
        assert len(cases) == len(group) == int(suite.get("tests", "0"))
        assert {(case.get("classname"), case.get("name")) for case in cases} == {
            case_key(node) for node in group
        }
        assert all(
            case.find("failure") is None
            and case.find("error") is None
            and case.find("skipped") is None
            for case in cases
        )
        assert all(int(suite.get(key, "0")) == 0 for key in ("failures", "errors", "skipped"))
        total += len(cases)
        evidence.append(
            {
                "worker": index,
                "xml": str(stem.with_suffix(".xml").relative_to(ROOT)),
                "passed": len(cases),
                "failed": 0,
                "errors": 0,
                "skipped": 0,
            }
        )
    assert total == len(collected)
    for cleanup in (RUN / "shared-database-cleanup.json", RUN / "repaired-shard-4-cleanup.json"):
        assert json.loads(cleanup.read_text())["dropped"] is True
    report = {
        "status": "PASS",
        "server_version": json.loads((RUN / "postgres-environment.json").read_text())[
            "server_version"
        ],
        "collected": total,
        "passed": total,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "complete_unique_node_coverage": True,
        "evidence": evidence,
        "repair": (
            "Shard 4 was rerun in full after Task 12's table-preservation test was "
            "pinned to its own 0043 revision. The original failed XML and summary "
            "are retained, not relabeled as passing."
        ),
        "disposable_shared_databases_dropped": True,
    }
    (OUT / "full-verified-summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
