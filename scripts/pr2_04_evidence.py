"""Validate test-produced PR2-04 observations and exact executed test results."""

from __future__ import annotations

import argparse
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


def _artifact(path: Path, root: Path) -> dict[str, str]:
    resolved = path.resolve()
    if not resolved.is_file() or root.resolve() not in resolved.parents:
        raise ValueError("evidence artifact must be a file inside the run repository")
    return {
        "path": str(resolved.relative_to(root.resolve())),
        "sha256": hashlib.sha256(resolved.read_bytes()).hexdigest(),
    }


def _read_artifact(item: dict[str, Any], root: Path) -> Path:
    relative = Path(item.get("path", ""))
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("evidence path must remain within the repository")
    path = root / relative
    actual = _artifact(path, root)
    if actual["sha256"] != item.get("sha256"):
        raise ValueError(f"evidence digest mismatch: {relative}")
    return path


def _binding(payload: dict[str, Any], head: str, run_id: str) -> None:
    if payload.get("execution_head") != head or payload.get("run_id") != run_id:
        raise ValueError("evidence candidate/run binding mismatch")


def finalize_run(
    ledger: Path,
    junit: Path,
    output: Path,
    root: Path,
    head: str,
    run_id: str,
    known_ids: set[str],
    bindings: Path | None = None,
) -> None:
    payload = json.loads(ledger.read_text())
    _binding(payload, head, run_id)
    manifest = {
        "schema_version": "pr204-test-run-v1",
        "execution_head": head,
        "run_id": run_id,
        "tests": payload["tests"],
        "ledger": _artifact(ledger, root),
        "junit": _artifact(junit, root),
        "bindings": _artifact(bindings, root) if bindings else None,
    }
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    validate_run(output, root, head, run_id, known_ids)


def validate_run(
    manifest_path: Path,
    root: Path,
    head: str,
    run_id: str,
    known_ids: set[str],
) -> dict[str, dict[str, Any]]:
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("schema_version") != "pr204-test-run-v1":
        raise ValueError("unsupported evidence run schema")
    _binding(manifest, head, run_id)
    ledger = json.loads(_read_artifact(manifest["ledger"], root).read_text())
    _binding(ledger, head, run_id)
    junit_path = _read_artifact(manifest["junit"], root)
    expected_nodes = {}
    coverage_gaps: dict[str, list[str]] = {}
    if manifest.get("bindings") is not None:
        binding_register = json.loads(_read_artifact(manifest["bindings"], root).read_text())
        expected_nodes = binding_register["requirements"]
        coverage_gaps = binding_register.get("coverage_gaps", {})
        if not isinstance(coverage_gaps, dict):
            raise ValueError("invalid coverage gap register")
        if (set(expected_nodes) | set(coverage_gaps)) - known_ids:
            raise ValueError("unknown requirement in expected-node bindings")
        for gaps in coverage_gaps.values():
            if not isinstance(gaps, list) or any(
                not isinstance(gap, str) or not gap.strip() for gap in gaps
            ):
                raise ValueError("invalid coverage gap declaration")
        for nodes in expected_nodes.values():
            if (
                not isinstance(nodes, list)
                or any(not isinstance(node, str) or "::" not in node for node in nodes)
                or len(set(nodes)) != len(nodes)
            ):
                raise ValueError("invalid exact expected-node binding")
    cases = list(ET.parse(junit_path).getroot().iter("testcase"))
    grouped: dict[str, list[tuple[dict[str, Any], str]]] = {}
    seen: set[str] = set()
    for test in manifest["tests"]:
        node = test.get("node_id")
        requirements = test.get("requirements", [])
        if not isinstance(node, str) or "::" not in node or node in seen:
            raise ValueError("invalid or duplicate exact test node binding")
        seen.add(node)
        if not requirements or len(set(requirements)) != len(requirements):
            raise ValueError("test requires unique explicit requirement markers")
        if set(requirements) - known_ids:
            raise ValueError("unknown requirement marker")
        if test not in ledger["tests"]:
            raise ValueError("test marker/trace binding differs from producer ledger")
        phases = test.get("phases", {})
        if set(phases) - {"setup", "call", "teardown"} or any(
            value not in {"passed", "failed", "skipped"} for value in phases.values()
        ):
            raise ValueError("invalid pytest phase result")
        file_name, _, test_name = node.partition("::")
        module = file_name.removesuffix(".py").replace("/", ".")
        matches = [
            case
            for case in cases
            if case.get("classname") == module and case.get("name") == test_name
        ]
        failed = "failed" in phases.values() or any(
            case.find("failure") is not None or case.find("error") is not None for case in matches
        )
        status = "NOT_RUN"
        trace_item = test.get("trace")
        if trace_item is not None:
            trace = json.loads(_read_artifact(trace_item, root).read_text())
            _binding(trace, head, run_id)
            if (
                trace.get("schema_version") != "pr204-observed-facts-v1"
                or trace.get("node_id") != node
                or trace.get("requirements") != requirements
            ):
                raise ValueError("trace node/marker binding mismatch")
            if not isinstance(trace.get("facts"), dict) or not trace["facts"]:
                raise ValueError("trace must contain observed facts")
            if failed and "call" in phases:
                status = "FAIL"
            if (
                not failed
                and phases == {"setup": "passed", "call": "passed", "teardown": "passed"}
                and len(matches) == 1
                and matches[0].find("skipped") is None
            ):
                status = "PASS"
        for requirement in requirements:
            grouped.setdefault(requirement, []).append((test, status))
    if manifest["tests"] != ledger["tests"]:
        raise ValueError("run test collection binding differs from producer ledger")
    rows = {}
    for requirement in sorted(known_ids):
        tests = grouped.get(requirement, [])
        statuses = [status for _, status in tests]
        complete = (
            not coverage_gaps.get(requirement)
            and bool(expected_nodes.get(requirement))
            and (set(expected_nodes[requirement]) == {test["node_id"] for test, _ in tests})
        )
        status = (
            "FAIL"
            if "FAIL" in statuses
            else "PASS"
            if complete and set(statuses) == {"PASS"}
            else "NOT_RUN"
        )
        evidence = [dict(manifest["junit"], candidate_head=head, run_id=run_id)] if tests else []
        evidence.extend(
            dict(test["trace"], candidate_head=head, run_id=run_id)
            for test, _ in tests
            if test.get("trace") is not None
        )
        rows[requirement] = {
            "requirement": requirement,
            "result": status,
            "expected_node_ids": expected_nodes.get(requirement, []),
            "coverage_gaps": coverage_gaps.get(requirement, []),
            "node_ids": [test["node_id"] for test, _ in tests],
            "evidence": evidence,
        }
    return rows


def main() -> int:
    from scripts.pr2_04_verification_matrix import _requirements

    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--junit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--acceptance-output", type=Path, default=None)
    parser.add_argument("--bindings", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    known_ids = {
        row["requirement"]
        for row in _requirements(root / "execution/phase2/PR2-04_Acceptance_Matrix_v1.0.md")
    }
    finalize_run(
        args.ledger, args.junit, args.output, root, args.head, args.run_id, known_ids, args.bindings
    )
    if args.acceptance_output:
        rows = validate_run(args.output, root, args.head, args.run_id, known_ids)
        args.acceptance_output.write_text(
            json.dumps(
                {
                    "execution_head": args.head,
                    "run_id": args.run_id,
                    "run_manifest": _artifact(args.output, root),
                    "rows": list(rows.values()),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
