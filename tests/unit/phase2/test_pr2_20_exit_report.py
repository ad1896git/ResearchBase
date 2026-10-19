"""Reports cannot launder unavailable, fake, skipped or failed checks into exit PASS."""

import re
from dataclasses import replace
from pathlib import Path

import pytest

from tests.contracts import pr2_20_reports as r
from tests.contracts.pr2_20_evidence import (
    canonical_bytes,
    digest_bytes,
    subject_digest,
    write_chunks,
)


def test_all_six_reports_nineteen_literal_rows_thirteen_architecture_mappings(
    tmp_path, monkeypatch
):
    identity = r.subject()
    inventory = r.adapter_inventory()
    migrations = r.migration_inventory()
    monkeypatch.setattr(r, "subject", lambda root=r.ROOT: identity)
    monkeypatch.setattr(r, "adapter_inventory", lambda root=r.ROOT: inventory)
    monkeypatch.setattr(r, "migration_inventory", lambda root=r.ROOT: migrations)
    directory = r.write_reports(tmp_path)
    docs = tmp_path / "docs/phase2"
    assert {path.name for path in docs.iterdir()} == set(r.REPORT_NAMES)
    assert len(list(directory.glob("*.json"))) == 27
    text = (docs / "phase2_exit_report.md").read_text()
    assert all(criterion in text for criterion in r.EXIT_CRITERIA)
    assert all(node in text for node in r.ARCHITECTURE_NODES)
    assert "STOP; wait for explicit Phase 3 GO" in text and "**Exit BLOCKED" in text
    assert "skipped" in text and identity[0] in text and identity[1] in text
    # Links to generated machine records must resolve locally.
    for path in docs.iterdir():
        for link in re.findall(r"\]\(([^)]+)\)", path.read_text()):
            if link == "pr2_20_verification.md":
                continue  # Filled by the separate verifier, not fabricated by the renderer.
            assert (path.parent / link).resolve().is_file(), (path, link)
    rows = r.exit_rows()
    assert len(rows) == 19 and all(row.status == "BLOCKED" for row in rows)
    assert r.validate_exit(rows, ()) == "BLOCKED"
    assert r.validate_exit(rows, ("P1 MAJOR: destination protection",)) == "BLOCKED"
    with pytest.raises(ValueError):
        r.validate_exit(rows[:-1], ())
    with pytest.raises(ValueError):
        r.validate_exit((replace(rows[0], dirty_diff_sha256="b" * 64), *rows[1:]), ())


def test_false_pass_nonzero_exit_missing_node_fake_optional_and_missing_logs(tmp_path):
    item = r.exit_rows()[0]
    with pytest.raises(ValueError):
        replace(
            item,
            status="PASS",
            passed=1,
            failed=0,
            errors=0,
            skipped=0,
            test_nodes=("fake",),
            commands=("false",),
            exit_codes=(1,),
        )
    item = replace(
        item,
        status="PASS",
        reason=None,
        passed=1,
        failed=0,
        errors=0,
        skipped=0,
        test_nodes=("tests/example.py::test_case",),
        commands=("uv run pytest tests/example.py",),
        exit_codes=(0,),
        owning_prs=("PR2-01",),
        contract_refs=("contract.md",),
        acceptance_revision="a" * 40,
    )
    prefix = (
        "pr_evidence/pr2-20/" + subject_digest(item.subject_revision, item.dirty_diff_sha256) + "/"
    )
    root = tmp_path
    (root / "tests").mkdir()
    (root / "tests/example.py").write_text("def test_case():\n    assert True\n")
    (root / "contract.md").write_text("Approved contract fixture")
    evidence = root / prefix
    evidence.mkdir(parents=True)
    (evidence / "owner.md").write_text("TEST ONLY disposition fixture")
    (evidence / "run.txt").write_text("1 passed")
    item = replace(
        item,
        evidence_refs=(prefix + "result.json", prefix + "run.txt"),
        disposition_refs=(prefix + "owner.md",),
    )
    payload = dict(
        scope="OWNING_ACCEPTANCE",
        subject_revision=item.subject_revision,
        dirty_diff_sha256=item.dirty_diff_sha256,
        acceptance_revision=item.acceptance_revision,
        mode="ENABLED",
        optional=False,
        commands=list(item.commands),
        exit_codes=[0],
        nodes={item.test_nodes[0]: "PASS"},
        counts=dict(passed=1, failed=0, errors=0, skipped=0),
        logs=[prefix + "run.txt"],
    )
    result = evidence / "result.json"
    result.write_bytes(canonical_bytes(payload))
    assert r.verified_acceptance(item, root)
    for change in (
        {"scope": "FOCUSED"},
        {"mode": "TEST_ONLY"},
        {"optional": True},
        {"nodes": {item.test_nodes[0]: "SKIPPED"}},
        {"logs": []},
        {"exit_codes": [1]},
        {"dirty_diff_sha256": "b" * 64},
    ):
        result.write_bytes(canonical_bytes({**payload, **change}))
        assert not r.verified_acceptance(item, root)
    result.write_bytes(canonical_bytes(payload))
    (evidence / "run.txt").unlink()
    assert not r.verified_acceptance(item, root)
    assert not r.verified_acceptance(replace(item, test_nodes=("does/not/exist.py::fake",)), root)


def test_subject_includes_authored_phase2_docs_but_excludes_only_generated_files(
    tmp_path, monkeypatch
):
    def output(command, cwd):
        if command[1] == "rev-parse":
            return b"a" * 40
        if command[1] == "diff":
            assert ":!docs/phase2" not in command
            assert ":!docs/phase2/phase2_exit_report.md" in command
            return b"authored diff"
        return b"docs/phase2/owning_contract.md\0docs/phase2/phase2_exit_report.md\0"

    monkeypatch.setattr(r.subprocess, "check_output", output)
    (tmp_path / "docs/phase2").mkdir(parents=True)
    contract = tmp_path / "docs/phase2/owning_contract.md"
    report = tmp_path / "docs/phase2/phase2_exit_report.md"
    contract.write_text("first")
    report.write_text("generated")
    first = r.subject(tmp_path)
    report.write_text("regenerated")
    assert r.subject(tmp_path) == first
    contract.write_text("second")
    assert r.subject(tmp_path) != first
    assert first[2] == subject_digest(first[0], first[1])
    assert digest_bytes(b"first") != digest_bytes(b"second")


@pytest.mark.parametrize(
    "unsafe",
    [
        {"password": "private"},
        {"Authorization": "Bearer secret"},
        {"nested": [{"url": "https://user:pass@example.org?q=restricted"}]},
        {"text": "e\u0301"},
        {"text": "\ud800"},
        {"raw": [float("nan")]},
        {"query": "proprietary research"},
        {"text": "api_key=sensitive"},
    ],
)
def test_raw_evidence_rejects_secret_nfc_utf8_and_numeric_bypasses(tmp_path, unsafe):
    with pytest.raises((ValueError, UnicodeError)):
        write_chunks(tmp_path, "samples-secret-0", [unsafe])
    assert not list(tmp_path.iterdir())


def test_literal_criteria_and_architecture_names_match_approved_plan():
    plan = Path("docs/proposals/PR2-20_Hardening_Plan_DRAFT.md").read_text()
    table = plan.split("The exit report must retain")[1].split("PR2-18 Novelty")[0]
    criteria = tuple(
        line.split("|")[1].strip()
        for line in table.splitlines()
        if line.startswith("| ") and not line.startswith(("| ---", "| Literal"))
    )
    assert criteria == r.EXIT_CRITERIA
    architecture = plan.split("### 9.1")[1].split("### 9.2")[0]
    assert set(re.findall(r"`(test_[a-z_]+)`", architecture)) == set(r.ARCHITECTURE_NODES)


def test_exact_non_nfc_catalog_sql_is_encoded_without_rewriting_history():
    from tests.integration.phase2.pr2_20_support import encode_catalog_text

    raw = "CHECK (objective ~ 'e\u0301')"
    encoded = encode_catalog_text(raw)
    assert bytes.fromhex(encoded["utf8_hex"]).decode("utf-8") == raw
    assert encoded["sha256"] == digest_bytes(raw.encode())


@pytest.mark.parametrize("source", ["FAIL", "BLOCKED", "NOT RUN", "DEFERRED"])
def test_h2_compaction_success_does_not_close_source_or_exit(source, monkeypatch):
    identity = r.subject()
    monkeypatch.setattr(r, "subject", lambda root=r.ROOT: identity)
    from tests.contracts.pr2_20_evidence import CompactionEvidence
    from tests.unit.phase2.test_pr2_20_evidence import record

    item = record(
        CompactionEvidence,
        status="PASS",
        original_path="old.txt",
        retained_path="kept.txt",
        retained_revision="a" * 40,
        summary="Byte recovery only",
    )
    assert r.compaction_status(item, source) == source
    assert r.validate_exit(r.exit_rows(), ()) == "BLOCKED"
