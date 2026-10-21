"""Reconcile reviewer JUnit results without counting skips as passes.

The prior HG1_RUN_LOCAL=1 run is retained as distinct historical evidence.
"""

import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "docs/verification/task14"
REVIEW = EVIDENCE / "review"
EXPECTED_SKIP = (
    "tests.integration.phase2.test_hg1_runner_live",
    "test_four_durable_deployments_authenticate_and_clean_up",
)
CHECK = (
    "uv run pyright && uv run ruff format --check . && uv run ruff check . && "
    "DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase "
    "RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres "
    "uv run pytest -o addopts='' -q -rfE -p no:cacheprovider"
)


def key(node: str) -> tuple[str, str]:
    path, selection = node.split("::", 1)
    head, bracket, parameters = selection.partition("[")
    names = head.split("::")
    return (
        ".".join([path[:-3].replace("/", "."), *names[:-1]]),
        names[-1] + bracket + parameters,
    )


def main() -> int:
    env = dict(os.environ)
    assert env.get("HG1_RUN_LOCAL") != "1" and env.get("HG1_RUN_LIVE") != "1"
    exit_code = json.loads((REVIEW / "check-exit.json").read_text())["exit_code"]
    assert exit_code == 0
    env.pop("PYTEST_ADDOPTS", None)
    collected = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-o",
            "addopts=",
            "-q",
            "--collect-only",
            "-p",
            "no:cacheprovider",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    nodes = [
        line for line in collected.stdout.splitlines() if line.startswith("tests/") and "::" in line
    ]
    assert len(nodes) == len(set(nodes))
    expected = {key(node) for node in nodes}
    assert len(expected) == len(nodes)
    (REVIEW / "collection.txt").write_text(collected.stdout + collected.stderr)
    cases = {}
    skips = []
    source = REVIEW / "full.xml"
    for case in ET.parse(source).iter("testcase"):
        identity = (case.attrib["classname"], case.attrib["name"])
        assert identity not in cases, identity
        status = "passed"
        for tag in ("failure", "error", "skipped"):
            child = case.find(tag)
            if child is not None:
                status = tag
                if tag == "skipped":
                    skips.append(
                        {
                            "classname": identity[0],
                            "name": identity[1],
                            "reason": child.get("message"),
                            "detail": child.text,
                            "counted_as_pass": False,
                        }
                    )
        cases[identity] = status
    assert set(cases) == expected, {
        "missing": sorted(expected - set(cases)),
        "extra": sorted(set(cases) - expected),
    }
    totals = {
        "passed": list(cases.values()).count("passed"),
        "failures": list(cases.values()).count("failure"),
        "errors": list(cases.values()).count("error"),
        "skipped": list(cases.values()).count("skipped"),
    }
    report = {
        "command": CHECK,
        "command_exit_code": exit_code,
        "verdict": "COMMAND_PASS_WITH_DOCUMENTED_SKIP",
        "method": "reviewer serial command; each collected identity has exactly one JUnit result",
        "collected": len(nodes),
        "unique_results": len(cases),
        "unique_verified": totals["passed"],
        "totals": totals,
        "skipped_tests": skips,
        "HG1_RUN_LOCAL": env.get("HG1_RUN_LOCAL"),
        "HG1_RUN_LIVE": env.get("HG1_RUN_LIVE"),
        "result_path": str(source.relative_to(ROOT)),
        "result_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "historical_local_run": {
            "path": "docs/verification/task14/review/prior-local-coverage.json",
            "HG1_RUN_LOCAL": "1",
            "totals": json.loads((REVIEW / "prior-local-coverage.json").read_text())["totals"],
            "not_the_reviewer_command": True,
        },
    }
    (EVIDENCE / "full-coverage.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(totals, sort_keys=True))
    assert totals["failures"] == totals["errors"] == 0
    assert {identity for identity, status in cases.items() if status == "skipped"} == {
        EXPECTED_SKIP
    }
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
