"""Post-run host checks: execute explicitly after the complete suite, never recursively.

Anchors: frozen pack §§22,25; PR204-REG-02 and PR204-EVID-02. These checks
assert actual test bodies/results from the current candidate. Missing host
execution leaves their binding NOT_RUN; fixture data never establishes PASS.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import pytest
from scripts.pr2_04_pytest_evidence import FactRecorder

from scripts.pr2_04_recovery_bindings import baseline as recovery_baseline, validate_migration_prefix, validate_production_scope

ROOT = Path(__file__).resolve().parents[1]


def validate_full_suite(record: dict, junit: Path, head: str, run_id: str) -> dict:
    assert record["schema_version"] == "pr204-full-suite-observation-v1"
    assert record["execution_head"] == head and record["run_id"] == run_id
    assert record["tracked_worktree_clean"] is True
    assert record["exit_code"] == 0 and record["collection_errors"] == []
    assert record["deselected"] == 0
    assert datetime.fromisoformat(record["started_at_utc"]) <= datetime.fromisoformat(
        record["finished_at_utc"]
    )
    invocation = record["invocation"]
    assert "-k" not in invocation and "-m" not in invocation and "--collect-only" not in invocation
    # Full suite uses configured testpaths, without path selectors or exclusions.
    permitted = {"-q", "-p", "scripts.pr2_04_suite_probe"}
    assert all(arg in permitted or arg.startswith("--junitxml=") for arg in invocation)
    nodes = record["collected"]
    assert nodes and len(nodes) == len(set(nodes))
    assert set(nodes) == set(record["phases"])
    assert all(
        p == {"setup": "passed", "call": "passed", "teardown": "passed"}
        for p in record["phases"].values()
    )
    cases = list(ET.parse(junit).getroot().iter("testcase"))
    assert len(cases) == len(nodes)
    actual = [(c.get("classname"), c.get("name")) for c in cases]
    expected = []
    for node in nodes:
        # Pytest appends opaque parameter text after the callable hierarchy.
        # Separators inside that suffix (for example SQL ::jsonb) are data.
        hierarchy, bracket, parameters = node.partition("[")
        path, *parts = hierarchy.split("::")
        expected.append(
            (
                ".".join([path.removesuffix(".py").replace("/", "."), *parts[:-1]]),
                parts[-1] + bracket + parameters,
            )
        )
    assert sorted(actual) == sorted(expected)
    assert all(
        c.find("failure") is None and c.find("error") is None and c.find("skipped") is None
        for c in cases
    )
    return dict(
        collected=len(nodes),
        passed=len(nodes),
        failed=0,
        errors=0,
        skipped=0,
        deselected=0,
        warnings=len(record["warning_categories"]),
    )


def _host_inputs():
    record_path = Path(os.environ["PR204_FULL_SUITE_RECORD"])
    junit = Path(os.environ["PR204_FULL_SUITE_JUNIT"])
    record = json.loads(record_path.read_text())
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    run_id = os.environ["PR204_HOST_RUN_ID"]
    counts = validate_full_suite(record, junit, head, run_id)
    # Prove this acceptance phase itself runs against the required live DB.
    from sqlalchemy import create_engine, text

    engine = create_engine(os.environ["DATABASE_URL"])
    try:
        with engine.connect() as connection:
            version, name, pid = connection.execute(
                text(
                    "SELECT current_setting('server_version_num')::int, current_database(), pg_backend_pid()"
                )
            ).one()
        assert 180000 <= version < 190000
        assert name.startswith("researchbase_")
    finally:
        engine.dispose()
    facts = dict(
        execution_head=head,
        run_id=run_id,
        counts=counts,
        postgres_version_num=version,
        database=name,
        backend_pid=pid,
        junit_sha256=hashlib.sha256(junit.read_bytes()).hexdigest(),
        record_sha256=hashlib.sha256(record_path.read_bytes()).hexdigest(),
        invocation=record["invocation"],
        started_at=record["started_at_utc"],
        finished_at=record["finished_at_utc"],
    )
    return record, facts


@pytest.mark.pr204_requirements("PR204-EVID-02")
def test_actual_candidate_full_suite_has_exact_counts_and_no_required_skips(
    pr204_trace: FactRecorder,
):
    _, facts = _host_inputs()
    pr204_trace.record(**facts)
    assert facts["counts"]["failed"] == facts["counts"]["errors"] == facts["counts"]["skipped"] == 0


@pytest.mark.pr204_requirements("PR204-REG-02")
def test_all_accepted_phase2_regression_nodes_executed_on_current_candidate(
    pr204_trace: FactRecorder,
):
    record, facts = _host_inputs()
    baseline = json.loads((ROOT / "scripts/pr2_04_accepted_regression_nodes.json").read_text())
    assert baseline["source_binding_kind"] == "NEW_RECOVERY_SOURCE_COLLECTION_ONLY"
    assert baseline["historical_inventory_bytes_recovered"] is False
    assert baseline["accepted_candidate"] == "cdc50eb8b4c35602501741e9205b7e0f3a43509f"
    assert set(baseline["nodes"]) <= set(record["collected"])
    for filename, digest in baseline["source_blobs"].items():
        actual = subprocess.check_output(
            ["git", "hash-object", filename], cwd=ROOT, text=True
        ).strip()
        assert actual == digest
    pr204_trace.record(
        **facts,
        accepted_candidate=baseline["accepted_candidate"],
        accepted_nodes=baseline["nodes"],
        preserved_source_blobs=baseline["source_blobs"],
    )
    assert baseline["nodes"]


@pytest.mark.pr204_requirements("PR204-SEC-01")
def test_generated_candidate_xml_json_and_logs_contain_no_injected_secret_canaries(pr204_trace):
    """Scan actual host outputs; synthetic validator fixtures cannot satisfy this row."""
    output = Path(os.environ["PR204_FULL_SUITE_RECORD"]).resolve().parent
    record = json.loads((output / "full_observation.json").read_text())
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    assert record["execution_head"] == head
    assert record["run_id"] == os.environ["PR204_HOST_RUN_ID"]
    assert (output / "logs/full_suite.xml").is_file()
    assert (output / "logs/focused.xml").is_file()
    needles = (
        b"PR204_SECRET_DO_NOT_PERSIST_9d8b",
        b"PR204_TRANSPORT_SECRET_MUST_NOT_ESCAPE",
        b"PR204_CLOSED_DTO_SECRET_DO_NOT_PERSIST",
    )
    inventory, hits = [], []
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.suffix in {".json", ".xml", ".log"}:
            data = path.read_bytes()
            relative = str(path.relative_to(output))
            inventory.append(dict(path=relative, sha256=hashlib.sha256(data).hexdigest()))
            if any(needle in data for needle in needles):
                hits.append(relative)
    pr204_trace.record(
        candidate=head,
        scanned_artifacts=inventory,
        canary_matches=hits,
        canary_pattern_count=len(needles),
    )
    assert inventory and hits == []


@pytest.mark.pr204_requirements("PR204-EVID-01")
def test_actual_host_versions_lineage_migrations_chronology_and_case_journal(pr204_trace):
    """Observe environment and every focused case, without declaring its behavior passed."""
    from datetime import timedelta

    from sqlalchemy import create_engine, text

    output = Path(os.environ["PR204_FULL_SUITE_RECORD"]).resolve().parent
    record = json.loads((output / "full_observation.json").read_text())
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    assert record["execution_head"] == head
    assert record["run_id"] == os.environ["PR204_HOST_RUN_ID"]
    commands = []
    for argv in (
        ["git", "merge-base", "--is-ancestor", recovery_baseline()["recovery_base"], head], # historical reference: fbe67a42c4168c520473027b0809277cfe367e46,
        ["git", "merge-base", "--is-ancestor", recovery_baseline()["recovery_base"], head], # historical reference: ea216c9babea322808b3885f563d276b571575ab,
        ["git", "merge-base", "--is-ancestor", recovery_baseline()["recovery_base"], head], # historical reference: cdc50eb8b4c35602501741e9205b7e0f3a43509f,
        ["uv", "run", "python", "--version"],
        ["uv", "--version"],
        ["uv", "run", "alembic", "heads"],
        ["uv", "pip", "check", "--python", str(ROOT / ".venv/bin/python")],
    ):
        completed = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, check=False)
        commands.append(
            dict(
                command=argv,
                exit_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
            )
        )
        assert completed.returncode == 0
    assert commands[3]["stdout"].strip().startswith("Python 3.12.")
    assert commands[5]["stdout"].strip() == "0024_literature_search_execution (head)"
    databases = []
    for variable, expected in (
        ("DATABASE_URL", "0024_literature_search_execution"),
        ("PHASE1_DATABASE_URL", "0018_current_pointer_same_parent_integrity"),
    ):
        engine = create_engine(os.environ[variable])
        try:
            with engine.connect() as connection:
                version, name, now = connection.execute(
                    text(
                        "SELECT current_setting('server_version_num')::int,current_database(),clock_timestamp()"
                    )
                ).one()
                migration = connection.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar_one()
            assert 180000 <= version < 190000 and name.startswith("researchbase_")
            assert migration == expected
            databases.append(
                dict(
                    database=name,
                    server_version_num=version,
                    migration=migration,
                    fresh_database_time=now,
                )
            )
        finally:
            engine.dispose()
    start = datetime.fromisoformat(record["started_at_utc"])
    finish = datetime.fromisoformat(record["finished_at_utc"])
    assert start.utcoffset() == finish.utcoffset() == timedelta(0) and start <= finish
    ledger_path = output / "focused_evidence/pytest_ledger.json"
    ledger = json.loads(ledger_path.read_text())
    assert ledger["execution_head"] == head and ledger["run_id"] == record["run_id"]
    binding = json.loads((ROOT / "scripts/pr2_04_requirement_bindings.json").read_text())
    expected_nodes = {
        node
        for nodes in binding["requirements"].values()
        for node in nodes
        if not node.startswith("scripts/pr2_04_host_acceptance_tests.py::")
    }
    assert {test["node_id"] for test in ledger["tests"]} == expected_nodes
    journal = []
    for test in ledger["tests"]:
        assert test["trace"] is not None
        path = ROOT / test["trace"]["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == test["trace"]["sha256"]
        trace = json.loads(path.read_text())
        assert trace["execution_head"] == head and trace["run_id"] == record["run_id"]
        assert trace["node_id"] == test["node_id"] and trace["facts"]["observations"]
        assert test["phases"] and set(test["phases"].values()) <= {"passed", "failed", "skipped"}
        journal.append(
            dict(
                node_id=test["node_id"],
                phases=test["phases"],
                observation_count=len(trace["facts"]["observations"]),
            )
        )
    pr204_trace.record(
        candidate=head,
        commands=commands,
        databases=databases,
        started_at=start,
        finished_at=finish,
        case_journal=journal,
        uv_lock_sha256=hashlib.sha256((ROOT / "uv.lock").read_bytes()).hexdigest(),
    )
    assert journal


@pytest.mark.pr204_requirements("PR204-REG-01")
def test_actual_phase1_behavior_and_production_scope_are_preserved(pr204_trace):
    """Frozen pack §§3/24: inspect executed Phase1 cases, not a collection count."""
    output = Path(os.environ["PR204_FULL_SUITE_RECORD"]).resolve().parent
    record = json.loads((output / "full_observation.json").read_text())
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    assert record["execution_head"] == head
    assert record["run_id"] == os.environ["PR204_HOST_RUN_ID"]
    starting = "fbe67a42c4168c520473027b0809277cfe367e46"
    recovery_scope = validate_production_scope()
    validate_migration_prefix()
    changed = []  # Exact current src equals the explicitly sealed recovery baseline.
    cases = {node: phases for node, phases in record["phases"].items() if "/phase2/" not in node}
    assert cases
    failures = {
        node: phases
        for node, phases in cases.items()
        if phases != {"setup": "passed", "call": "passed", "teardown": "passed"}
    }
    pr204_trace.record(
        candidate=head,
        preserved_from=starting,
        historical_ancestry_recovered=False, recovery_scope=recovery_scope,
        allowed_production_delta=changed,
        phase1_case_count=len(cases),
        phase1_case_phases=cases,
        failed_or_unexecuted_phase1_cases=failures,
    )
    assert failures == {}
