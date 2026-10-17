"""Collect the entire suite and run each node once, isolating shared Phase 1 DB tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "docs/verification/task12/full-sharded"
COMMON = [sys.executable, "-m", "pytest", "-o", "addopts=", "-q", "-ra", "-p", "no:cacheprovider"]


def main() -> int:
    os.chdir(ROOT)
    assert os.environ.get("DATABASE_URL") and os.environ.get("RB_TEST_ADMIN_URL")
    assert os.environ.get("HG1_RUN_LOCAL") == "1"
    OUT.mkdir(exist_ok=True)
    collection = subprocess.run(
        [*COMMON, "--collect-only"], text=True, capture_output=True, check=True
    )
    (OUT / "collection.log").write_text(collection.stdout + collection.stderr)
    nodes = [
        line
        for line in collection.stdout.splitlines()
        if line.startswith("tests/") and "::" in line
    ]
    assert nodes and len(nodes) == len(set(nodes))
    previous = ET.parse(ROOT / "docs/verification/task12/full-pytest-serial.xml")
    timings = {
        f"{case.attrib['classname'].replace('.', '/')}.py::{case.attrib['name']}": float(
            case.get("time", "1")
        )
        for case in previous.findall(".//testcase")
    }
    # Only Phase 2 tests use per-test disposable databases throughout their subtree.
    # All other tests run serially in one worker, preserving their shared DB discipline.
    groups: list[list[str]] = [[] for _ in range(5)]
    for node in nodes:
        if not node.startswith("tests/integration/phase2/"):
            groups[0].append(node)
    loads = [0.0] * 4
    phase2 = [node for node in nodes if node.startswith("tests/integration/phase2/")]
    for node in sorted(phase2, key=lambda item: timings.get(item, 1.0), reverse=True):
        index = min(range(4), key=lambda index: loads[index])
        groups[index + 1].append(node)
        loads[index] += timings.get(node, 1.0)
    # Keep normal collection order within every worker after balancing the partition.
    order = {node: index for index, node in enumerate(nodes)}
    for group in groups:
        group.sort(key=order.__getitem__)
    selected = [node for group in groups for node in group]
    assert len(selected) == len(nodes) and set(selected) == set(nodes)
    (OUT / "partition.json").write_text(
        json.dumps({"collected": len(nodes), "groups": groups}, indent=2) + "\n"
    )

    def run(index: int) -> dict:
        group = groups[index]
        targets = ["tests", "--ignore=tests/integration/phase2"] if index == 0 else group
        command = [*COMMON, f"--junitxml={OUT / f'shard-{index}.xml'}", *targets]
        with (OUT / f"shard-{index}.log").open("w") as output:
            result = subprocess.run(command, stdout=output, stderr=subprocess.STDOUT, check=False)
        (OUT / f"shard-{index}-exit.json").write_text(
            json.dumps({"exit_code": result.returncode}) + "\n"
        )
        suite = ET.parse(OUT / f"shard-{index}.xml").find("testsuite")
        assert suite is not None
        cases = suite.findall("testcase")
        assert len(cases) == len(group)
        expected = set()
        for node in group:
            path, selection = node.split("::", 1)
            head, bracket, parameters = selection.partition("[")
            names = head.split("::")
            classname = ".".join([path[:-3].replace("/", "."), *names[:-1]])
            expected.add((classname, names[-1] + bracket + parameters))
        assert {(case.get("classname"), case.get("name")) for case in cases} == expected
        counts = {
            key: int(suite.get(key, "0")) for key in ("tests", "failures", "errors", "skipped")
        }
        summary = {"worker": index, "exit_code": result.returncode, "counts": counts}
        print(json.dumps(summary), flush=True)
        return summary

    print(f"Collected {len(nodes)} nodes; worker counts: {[len(g) for g in groups]}", flush=True)
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(run, range(5)))
    totals = {
        key: sum(result["counts"][key] for result in results)
        for key in ("tests", "failures", "errors", "skipped")
    }
    totals["passed"] = totals["tests"] - totals["failures"] - totals["errors"] - totals["skipped"]
    assert totals["tests"] == len(nodes)
    report = {"collected": len(nodes), "workers": results, "totals": totals}
    (OUT / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report), flush=True)
    return int(any(result["exit_code"] != 0 for result in results))


if __name__ == "__main__":
    raise SystemExit(main())
