from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest

from scripts.pr2_04_evidence import finalize_run, validate_run
from scripts.pr2_04_pytest_evidence import FactRecorder

HEAD = "a" * 40
RUN = "unit-synthetic-run"
NODE = "tests/integration/phase2/test_example.py::test_example"
REQ = "PR204-DOM-01"


def _run(root: Path, *, phase: str = "passed", traced: bool = True) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    trace = root / "trace.json"
    trace.write_text(
        json.dumps(
            {
                "schema_version": "pr204-observed-facts-v1",
                "execution_head": HEAD,
                "run_id": RUN,
                "node_id": NODE,
                "requirements": [REQ],
                "facts": {"durable_count": 1},
            }
        )
    )
    entry = {
        "node_id": NODE,
        "requirements": [REQ],
        "phases": {"setup": "passed", "call": phase, "teardown": "passed"},
        "trace": {"path": "trace.json", "sha256": hashlib.sha256(trace.read_bytes()).hexdigest()}
        if traced
        else None,
    }
    ledger = root / "ledger.json"
    ledger.write_text(json.dumps({"execution_head": HEAD, "run_id": RUN, "tests": [entry]}))
    xml = root / "tests.xml"
    failure = '<failure message="failed" />' if phase == "failed" else ""
    xml.write_text(
        '<testsuite><testcase classname="tests.integration.phase2.test_example" '
        f'name="test_example">{failure}</testcase></testsuite>'
    )
    manifest = root / "run.json"
    bindings = root / "bindings.json"
    bindings.write_text(json.dumps({"requirements": {REQ: [NODE]}}))
    finalize_run(ledger, xml, manifest, root, HEAD, RUN, {REQ}, bindings)
    return manifest


def test_marked_executed_passing_test_requires_bound_trace(tmp_path: Path) -> None:
    manifest = _run(tmp_path)
    rows = validate_run(manifest, tmp_path, HEAD, RUN, {REQ})
    assert rows[REQ]["result"] == "PASS"
    assert rows[REQ]["node_ids"] == [NODE]


def test_partial_requirement_without_complete_expected_node_binding_is_not_run(
    tmp_path: Path,
) -> None:
    manifest = _run(tmp_path)
    payload = json.loads(manifest.read_text())
    payload["bindings"] = None
    manifest.write_text(json.dumps(payload))
    assert validate_run(manifest, tmp_path, HEAD, RUN, {REQ})[REQ]["result"] == "NOT_RUN"


def test_fully_bound_requirement_cannot_pass_before_its_pg_node_executes(tmp_path: Path) -> None:
    manifest = _run(tmp_path)
    bindings = tmp_path / "bindings.json"
    bindings.write_text(json.dumps({
        "requirements": {REQ: [NODE, NODE + "_postgresql"]},
        "coverage_gaps": {REQ: []},
    }))
    finalize_run(tmp_path / "ledger.json", tmp_path / "tests.xml", manifest,
                 tmp_path, HEAD, RUN, {REQ}, bindings)
    row = validate_run(manifest, tmp_path, HEAD, RUN, {REQ})[REQ]
    assert row["result"] == "NOT_RUN"
    assert row["node_ids"] == [NODE]
    assert row["expected_node_ids"] == [NODE, NODE + "_postgresql"]


def test_matching_partial_node_set_with_open_contract_gaps_cannot_pass(tmp_path: Path) -> None:
    manifest = _run(tmp_path)
    bindings = tmp_path / "bindings.json"
    bindings.write_text(json.dumps({
        "requirements": {REQ: [NODE]},
        "coverage_gaps": {REQ: ["PostgreSQL transition guards not yet exercised"]},
    }))
    finalize_run(tmp_path / "ledger.json", tmp_path / "tests.xml", manifest,
                 tmp_path, HEAD, RUN, {REQ}, bindings)
    row = validate_run(manifest, tmp_path, HEAD, RUN, {REQ})[REQ]
    assert row["result"] == "NOT_RUN"
    assert row["coverage_gaps"] == ["PostgreSQL transition guards not yet exercised"]


def test_unknown_requirement_in_coverage_gap_register_is_rejected(tmp_path: Path) -> None:
    manifest = _run(tmp_path)
    bindings = tmp_path / "bindings.json"
    bindings.write_text(json.dumps({
        "requirements": {REQ: [NODE]},
        "coverage_gaps": {"PR204-UNKNOWN-ID": ["uncovered"]},
    }))
    with pytest.raises(ValueError, match="unknown requirement"):
        finalize_run(tmp_path / "ledger.json", tmp_path / "tests.xml", manifest,
                     tmp_path, HEAD, RUN, {REQ}, bindings)


@pytest.mark.parametrize(
    "phase,traced,expected",
    [
        ("failed", True, "FAIL"),
        ("failed", False, "NOT_RUN"),
        ("passed", False, "NOT_RUN"),
        ("skipped", True, "NOT_RUN"),
    ],
)
def test_nonpassing_or_untraced_test_never_passes(
    tmp_path: Path, phase: str, traced: bool, expected: str
) -> None:
    manifest = _run(tmp_path, phase=phase, traced=traced)
    assert validate_run(manifest, tmp_path, HEAD, RUN, {REQ})[REQ]["result"] == expected


def test_failed_partial_coverage_is_fail_not_pass_or_hidden_not_run(tmp_path: Path) -> None:
    manifest = _run(tmp_path, phase="failed")
    bindings = tmp_path / "bindings.json"
    bindings.write_text(json.dumps({"requirements": {REQ: [NODE]},
                                    "coverage_gaps": {REQ: ["PG cases missing"]}}))
    finalize_run(tmp_path / "ledger.json", tmp_path / "tests.xml", manifest,
                 tmp_path, HEAD, RUN, {REQ}, bindings)
    assert validate_run(manifest, tmp_path, HEAD, RUN, {REQ})[REQ]["result"] == "FAIL"


def test_unmarked_requirement_retains_gap_and_not_run_without_trace(tmp_path: Path) -> None:
    manifest = _run(tmp_path)
    other = "PR204-DOM-02"
    bindings = tmp_path / "bindings.json"
    bindings.write_text(json.dumps({
        "requirements": {REQ: [NODE], other: []},
        "coverage_gaps": {other: ["Complete seals not exercised"]},
    }))
    finalize_run(tmp_path / "ledger.json", tmp_path / "tests.xml", manifest,
                 tmp_path, HEAD, RUN, {REQ, other}, bindings)
    row = validate_run(manifest, tmp_path, HEAD, RUN, {REQ, other})[other]
    assert row["result"] == "NOT_RUN"
    assert row["node_ids"] == [] and row["evidence"] == []
    assert row["coverage_gaps"] == ["Complete seals not exercised"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("execution_head", "b" * 40),
        ("run_id", "older-run"),
        ("node_id", NODE + "[other]"),
        ("requirements", ["PR204-UNKNOWN-ID"]),
    ],
)
def test_trace_binding_mismatch_is_rejected(tmp_path: Path, field: str, value: object) -> None:
    manifest = _run(tmp_path)
    trace = tmp_path / "trace.json"
    payload = json.loads(trace.read_text())
    payload[field] = value
    trace.write_text(json.dumps(payload))
    # Recompute the digest to prove binding validation is independent of file integrity.
    run = json.loads(manifest.read_text())
    run["tests"][0]["trace"]["sha256"] = hashlib.sha256(trace.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(run))
    with pytest.raises(ValueError, match="binding|unknown"):
        validate_run(manifest, tmp_path, HEAD, RUN, {REQ})


def test_corrupted_trace_digest_is_rejected(tmp_path: Path) -> None:
    manifest = _run(tmp_path)
    (tmp_path / "trace.json").write_text("{}")
    with pytest.raises(ValueError, match="digest"):
        validate_run(manifest, tmp_path, HEAD, RUN, {REQ})


def test_unknown_marker_is_rejected(tmp_path: Path) -> None:
    manifest = _run(tmp_path)
    payload = json.loads(manifest.read_text())
    payload["tests"][0]["requirements"] = ["PR204-NOT-A-REQUIREMENT"]
    manifest.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="unknown"):
        validate_run(manifest, tmp_path, HEAD, RUN, {REQ})


def test_run_reuse_and_junit_corruption_are_rejected(tmp_path: Path) -> None:
    manifest = _run(tmp_path)
    with pytest.raises(ValueError, match="binding"):
        validate_run(manifest, tmp_path, HEAD, "another-run", {REQ})
    (tmp_path / "tests.xml").write_text("<testsuite />")
    with pytest.raises(ValueError, match="digest"):
        validate_run(manifest, tmp_path, HEAD, RUN, {REQ})


def test_marker_without_exact_executed_junit_node_is_not_run(tmp_path: Path) -> None:
    manifest = _run(tmp_path)
    xml = tmp_path / "tests.xml"
    xml.write_text("<testsuite />")
    payload = json.loads(manifest.read_text())
    payload["junit"]["sha256"] = hashlib.sha256(xml.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(payload))
    assert validate_run(manifest, tmp_path, HEAD, RUN, {REQ})[REQ]["result"] == "NOT_RUN"


def test_fixture_records_a_snapshot_of_observed_values_only() -> None:
    observations = []
    recorder = FactRecorder(observations)
    durable = {"count": 1}
    recorder.record(durable=durable)
    durable["count"] = 2
    assert observations == [{"durable": {"count": 1}}]
    with pytest.raises(ValueError):
        recorder.record(nonfinite=float("nan"))
    with pytest.raises(ValueError, match="acceptance"):
        recorder.record(requirement_acceptance="PASS")


def test_recorder_serializes_observed_typed_database_values_without_orm_objects() -> None:
    observations = []
    FactRecorder(observations).record(
        at=datetime(2026, 1, 1, tzinfo=UTC), id=UUID(int=1), score=Decimal("0.75")
    )
    assert observations == [
        {"at": "2026-01-01T00:00:00+00:00", "id": str(UUID(int=1)), "score": "0.75"}
    ]


@pytest.mark.parametrize("traced", [True, False])
def test_real_pytest_plugin_records_markers_phases_and_facts(tmp_path: Path, traced: bool) -> None:
    root = Path(__file__).resolve().parents[3]
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    sample = tmp_path / "test_fixture.py"
    sample.write_text(
        "import pytest\n@pytest.mark.pr204_requirements('PR204-DOM-01')\n"
        "def test_observation(pr204_trace):\n"
        + ("    pr204_trace.record(durable_count=1)\n" if traced else "    assert 1 == 1\n")
    )
    output = tmp_path / "evidence"
    env = dict(
        os.environ,
        PR204_EVIDENCE_DIR=str(output),
        PR204_RUN_ID=RUN,
        PR204_CANDIDATE_HEAD=head,
        PYTHONPATH=str(root),
    )
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-p",
        "scripts.pr2_04_pytest_evidence",
        "--rootdir",
        str(tmp_path),
        "--junitxml",
        str(tmp_path / "tests.xml"),
        str(sample),
        "-q",
    ]
    completed = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    manifest = tmp_path / "run.json"
    bindings = tmp_path / "bindings.json"
    bindings.write_text(json.dumps({"requirements": {REQ: ["test_fixture.py::test_observation"]}}))
    finalize_run(
        output / "pytest_ledger.json",
        tmp_path / "tests.xml",
        manifest,
        tmp_path,
        head,
        RUN,
        {REQ},
        bindings,
    )
    rows = validate_run(manifest, tmp_path, head, RUN, {REQ})
    assert rows[REQ]["result"] == ("PASS" if traced else "NOT_RUN")
    repeated = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True)
    assert repeated.returncode != 0
    assert "cannot be reused" in repeated.stderr


def test_xpass_cannot_generate_acceptance_pass(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[3]
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    sample = tmp_path / "test_fixture.py"
    sample.write_text(
        "import pytest\n@pytest.mark.xfail\n"
        "@pytest.mark.pr204_requirements('PR204-DOM-01')\n"
        "def test_observation(pr204_trace):\n    pr204_trace.record(durable_count=1)\n"
    )
    output = tmp_path / "evidence"
    env = dict(
        os.environ,
        PR204_EVIDENCE_DIR=str(output),
        PR204_RUN_ID=RUN,
        PR204_CANDIDATE_HEAD=head,
        PYTHONPATH=str(root),
    )
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-p",
            "scripts.pr2_04_pytest_evidence",
            "--rootdir",
            str(tmp_path),
            "--junitxml",
            str(tmp_path / "tests.xml"),
            str(sample),
            "-q",
        ],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    bindings = tmp_path / "bindings.json"
    bindings.write_text(json.dumps({"requirements": {REQ: ["test_fixture.py::test_observation"]}}))
    manifest = tmp_path / "run.json"
    finalize_run(
        output / "pytest_ledger.json",
        tmp_path / "tests.xml",
        manifest,
        tmp_path,
        head,
        RUN,
        {REQ},
        bindings,
    )
    assert validate_run(manifest, tmp_path, head, RUN, {REQ})[REQ]["result"] == "NOT_RUN"


def test_compatibility_pass_requires_identical_validated_producer_rows(tmp_path: Path) -> None:
    from scripts.pr2_04_verification_matrix import _load_results

    manifest = _run(tmp_path)
    rows = validate_run(manifest, tmp_path, HEAD, RUN, {REQ})
    compatibility = tmp_path / "acceptance_results.json"
    compatibility.write_text(json.dumps({"execution_head": HEAD, "run_id": RUN,
                                        "rows": list(rows.values())}))
    assert _load_results(compatibility, tmp_path, HEAD, rows, RUN)[REQ]["result"] == "PASS"
    with pytest.raises(ValueError, match="run binding"):
        _load_results(compatibility, tmp_path, HEAD, rows, "other-run")


def test_manual_pass_cannot_upgrade_failed_producer_test(tmp_path: Path) -> None:
    from scripts.pr2_04_verification_matrix import _load_results

    manifest = _run(tmp_path, phase="failed")
    rows = validate_run(manifest, tmp_path, HEAD, RUN, {REQ})
    manual = dict(rows[REQ], result="PASS")
    compatibility = tmp_path / "acceptance_results.json"
    compatibility.write_text(json.dumps({"execution_head": HEAD, "run_id": RUN, "rows": [manual]}))
    with pytest.raises(ValueError):
        _load_results(compatibility, tmp_path, HEAD, rows, RUN)
