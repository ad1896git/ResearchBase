#!/usr/bin/env python3
"""Emit a candidate-bound PR2-04 requirement matrix without inventing PASS evidence."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

RESULTS = {"PASS", "FAIL", "BLOCKED", "NOT_RUN"}


def _requirements(source: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in source.read_text().splitlines():
        if not line.startswith("| PR204-"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 4:
            raise ValueError(f"malformed acceptance row: {line}")
        requirement, invariant, evidence_type, category = cells
        rows.append(
            {
                "requirement": requirement,
                "invariant": invariant,
                "evidence_type": evidence_type,
                "expected_category": category,
            }
        )
    ids = [row["requirement"] for row in rows]
    if len(ids) != 65 or len(set(ids)) != 65:
        raise ValueError(f"expected 65 unique requirements, found {len(ids)}")
    return rows


def _load_results(
    path: Path, root: Path, head: str,
    validated_rows: dict[str, dict[str, Any]] | None = None,
    run_id: str | None = None,
) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text())
    if payload.get("execution_head") != head:
        raise ValueError("evidence index is not bound to the current candidate HEAD")
    if run_id is not None and payload.get("run_id") != run_id:
        raise ValueError("compatibility index run binding mismatch")
    known_ids = {row["requirement"] for row in _requirements(
        Path(__file__).resolve().parents[1]
        / "execution/phase2/PR2-04_Acceptance_Matrix_v1.0.md")}
    result: dict[str, dict[str, Any]] = {}
    for row in payload.get("rows", []):
        requirement = row.get("requirement")
        status = row.get("result")
        if not isinstance(requirement, str) or status not in RESULTS:
            raise ValueError("evidence rows require a requirement ID and valid result")
        if requirement not in known_ids:
            raise ValueError(f"unknown requirement ID: {requirement}")
        if requirement in result:
            raise ValueError(f"duplicate evidence row: {requirement}")
        evidence = row.get("evidence", [])
        node_ids = row.get("node_ids", [])
        if status == "PASS" and (not evidence or not node_ids):
            raise ValueError(f"PASS requires evidence artifacts and exact node IDs: {requirement}")
        observed: list[ET.Element] = []
        for item in evidence:
            relative = Path(item.get("path", ""))
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError(f"evidence path must stay within the repository: {relative}")
            artifact = (root / relative).resolve()
            if not artifact.is_file() or root.resolve() not in artifact.parents:
                raise ValueError(f"evidence artifact is missing or outside repository: {relative}")
            if item.get("candidate_head") != head:
                raise ValueError(f"stale evidence artifact binding: {relative}")
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            if item.get("sha256") != digest:
                raise ValueError(f"evidence artifact digest mismatch: {relative}")
            if artifact.suffix == ".xml":
                observed.extend(ET.parse(artifact).getroot().iter("testcase"))
        if status == "PASS" and any(not isinstance(node, str) or not node for node in node_ids):
            raise ValueError(f"PASS node IDs must be exact nonblank strings: {requirement}")
        if status == "PASS":
            if not observed:
                raise ValueError(f"PASS requires candidate-bound JUnit evidence: {requirement}")
            for node_id in node_ids:
                file_name, separator, test_name = node_id.partition("::")
                if not separator:
                    raise ValueError(f"invalid exact pytest node ID: {node_id}")
                module_name = file_name.removesuffix(".py").replace("/", ".")
                matches = [
                    case
                    for case in observed
                    if case.get("classname") == module_name and case.get("name") == test_name
                ]
                if not matches or any(
                    case.find("failure") is not None
                    or case.find("error") is not None
                    or case.find("skipped") is not None
                    for case in matches
                ):
                    raise ValueError(f"required JUnit node is missing or not passing: {node_id}")
            trusted = (validated_rows or {}).get(requirement)
            if trusted is None or trusted["result"] != "PASS":
                raise ValueError("automated PASS requires a validated producer run")
            if node_ids != trusted["node_ids"] or evidence != trusted["evidence"]:
                raise ValueError("compatibility PASS differs from validated producer observations")
        trusted = (validated_rows or {}).get(requirement)
        if trusted is not None and status != trusted["result"]:
            raise ValueError("compatibility status differs from validated producer result")
        result[requirement] = row
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--head", default=None)
    parser.add_argument("--results", type=Path, default=None)
    parser.add_argument("--run-manifest", type=Path, default=None)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    source = root / "execution/phase2/PR2-04_Acceptance_Matrix_v1.0.md"
    current_head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    head = args.head or current_head
    if head != current_head:
        raise SystemExit("matrix HEAD must equal the checked-out candidate HEAD")
    try:
        requirements = _requirements(source)
        indexed = {}
        if args.run_manifest is not None:
            from scripts.pr2_04_evidence import validate_run

            if not args.run_id:
                raise ValueError("automated evidence requires the current host run ID")
            indexed = validate_run(args.run_manifest, root, head, args.run_id,
                                   {row["requirement"] for row in requirements})
        if args.results:
            indexed.update(_load_results(args.results, root, head, indexed, args.run_id))
    except (ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(str(exc)) from exc
    known_ids = {row["requirement"] for row in requirements}
    unexpected = set(indexed).difference(known_ids)
    if unexpected:
        raise SystemExit(f"evidence index contains unknown requirements: {sorted(unexpected)}")
    rows = []
    for requirement in requirements:
        evidence_row = indexed.get(requirement["requirement"], {})
        rows.append(
            {
                **requirement,
                "result": evidence_row.get("result", "NOT_RUN"),
                "node_ids": evidence_row.get("node_ids", []),
                "expected_node_ids": evidence_row.get("expected_node_ids", []),
                "coverage_gaps": evidence_row.get("coverage_gaps", []),
                "evidence": evidence_row.get("evidence", []),
                "reason": evidence_row.get("reason"),
            }
        )
    counts = {status: sum(row["result"] == status for row in rows) for status in RESULTS}
    result = {
        "schema_version": "pr2-04-verification-matrix-v1",
        "execution_head": head,
        "run_id": args.run_id,
        "required": 65,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "counts": counts,
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
