"""Reports cannot launder unavailable, fake, skipped or failed checks into exit PASS."""

import ast
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
            link = link.split("#")[0]
            if link == "pr2_20_verification.md":
                continue  # Filled by the separate verifier, not fabricated by the renderer.
            if link:
                assert (path.parent / link).resolve().is_file() or (
                    r.ROOT / "docs/phase2" / link
                ).resolve().is_file()
            else:
                assert path.is_file()
    rows = r.exit_rows()
    assert len(rows) == 19
    assert all(
        row.status == ("DEFERRED" if row.criterion == "PaperQA2 Adapter" else "BLOCKED")
        for row in rows
    )
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


def test_b28_deferral_is_owner_disposition_and_never_fake_acceptance(tmp_path, monkeypatch):
    item = r.exit_rows()[5]
    assert item.criterion == "PaperQA2 Adapter" and item.status == "DEFERRED"
    assert item.disposition_refs == (r.B28_DISPOSITION,)
    assert r.verified_acceptance(item, r.ROOT)
    assert not r.verified_acceptance(item, tmp_path)
    inventory = r.adapter_inventory()
    record = tmp_path / r.B28_DISPOSITION
    record.parent.mkdir(parents=True)
    record.write_bytes((r.ROOT / r.B28_DISPOSITION).read_bytes())
    monkeypatch.setattr(r, "adapter_inventory", lambda root: inventory)
    lock = tmp_path / "uv.lock"
    lock.write_text("package = []")
    assert r.verified_acceptance(item, tmp_path)
    for package in ("paper-qa", "paperqa"):
        lock.write_text(f'[[package]]\nname = "{package}"\nversion = "test"\n')
        assert not r.verified_acceptance(item, tmp_path)
    lock.write_text("package = []")
    for changes in (
        {"mode": "TEST_ONLY", "status": "BLOCKED"},
        {"package_version": "1", "status": "BLOCKED"},
    ):
        altered = tuple(
            replace(entry, **changes) if entry.adapter_id == "paperqa2" else entry
            for entry in inventory
        )
        monkeypatch.setattr(r, "adapter_inventory", lambda root, altered=altered: altered)
        assert not r.verified_acceptance(item, tmp_path)


def test_b28_deferral_does_not_block_verified_other_rows_or_hide_major_findings(monkeypatch):
    rows = r.exit_rows()
    # Other rows' existing owning-acceptance verifier is independently covered above.
    real = r.verified_acceptance
    accepted = tuple(
        row
        if row.criterion == "PaperQA2 Adapter"
        else replace(
            row,
            status="PASS",
            reason=None,
            passed=1,
            test_nodes=("test::node",),
        )
        for row in rows
    )
    monkeypatch.setattr(
        r,
        "verified_acceptance",
        lambda row, root: real(row, root) if row.status == "DEFERRED" else True,
    )
    assert r.validate_exit(accepted, ()) == "PASS"
    assert r.validate_exit(accepted, ("P1 MAJOR: unresolved",)) == "BLOCKED"
    assert r.validate_exit(rows, ()) == "BLOCKED"


def test_s4_inventory_covers_eighteen_active_rows_and_landed_inputs():
    from scripts.pr2_20_verify import OWNING, POSTGRES

    assert len(r.EXIT_FILES) == 19
    for criterion, paths in r.EXIT_FILES.items():
        assert bool(paths) == (criterion != "PaperQA2 Adapter")
        assert bool(r.EXIT_NODES[criterion]) == bool(paths)
        assert set(paths) <= set(OWNING + POSTGRES)
        for node in r.EXIT_NODES[criterion]:
            path, method = node.split("::")
            assert any(
                isinstance(n, ast.FunctionDef) and n.name == method
                for n in ast.parse(Path(path).read_text()).body
            )
    selected = " ".join(OWNING + POSTGRES)
    for owner in ("test_b02_", "test_b03_", "test_m1_", "test_pr2_20_novelty.py"):
        assert owner in selected
    assert set(r.ARCHITECTURE_NODES.values()) <= set(r.EXIT_NODES[r.EXIT_CRITERIA[17]])


def test_s4_junit_retains_parameter_cases_and_setup_teardown_errors(tmp_path):
    from scripts.pr2_20_verify import cases_from_xml, counts_from_xml

    xml = tmp_path / "junit.xml"
    xml.write_text(
        '<testsuites><testsuite tests="5" failures="1" errors="1" skipped="1">'
        '<testcase classname="tests.example" name="test_case[pass]"/>'
        '<testcase classname="tests.example" name="test_case[fail]"><failure/></testcase>'
        '<testcase classname="tests.example" name="test_case[skip]"><skipped/></testcase>'
        '<testcase classname="tests.example" name="test_case[error]"><error/></testcase>'
        '<testcase classname="tests.example" name="test_other"/>'
        "</testsuite></testsuites>"
    )
    assert counts_from_xml(xml) == dict(passed=2, failed=1, errors=1, skipped=1)
    cases = cases_from_xml(xml)
    assert [case["status"] for case in cases] == ["PASS", "FAIL", "SKIPPED", "ERROR", "PASS"]
    assert cases[0]["node"] == "tests/example.py::test_case[pass]"


@pytest.mark.parametrize("outcome", ["PASS", "SKIPPED", "FAIL", "ERROR", "MISSING"])
def test_s4_collector_loader_real_files_subject_and_log_integrity(tmp_path, monkeypatch, outcome):
    """Synthetic run fixtures stay temporary and never become repository acceptance."""
    import json
    import shutil

    from scripts.pr2_20_verify import collect_acceptance

    identity = r.subject()
    monkeypatch.setattr(r, "subject", lambda root=r.ROOT: identity)
    # Copy sources into the test root: path validation must not escape via symlinks.
    sources = {
        *[path for paths in r.EXIT_FILES.values() for path in paths],
        r.B31_CONTRACT,
        r.AQ_S3,
        r.LINUX_DISPOSITION,
        "docs/proposals/PR2-20_Hardening_Plan_DRAFT.md",
    }
    for source in sources:
        target = tmp_path / source
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(r.ROOT / source, target)
    directory = tmp_path / "pr_evidence/pr2-20" / identity[2]
    directory.mkdir(parents=True)
    log = directory / "test-only-run.txt"
    log.write_text("TEST FIXTURE ONLY: synthetic assertions")
    cases = [
        dict(node=node + "[fixture]", status="PASS")
        for paths in r.EXIT_NODES.values()
        for node in paths
    ]
    # Each shared node appears once in the actual deduplicated command.
    cases = list({case["node"]: case for case in cases}.values())
    first = r.EXIT_NODES[r.EXIT_CRITERIA[0]][0]
    if outcome == "MISSING":
        cases = [case for case in cases if case["node"].split("[")[0] != first]
    elif outcome != "PASS":
        cases.append(dict(node=first + "[other-parameter]", status=outcome))
    result = dict(
        label="owning-acceptance",
        command="TEST FIXTURE ONLY",
        exit_code=1 if outcome in {"FAIL", "ERROR"} else 0,
        files=list({path for paths in r.EXIT_FILES.values() for path in paths}),
        cases=cases,
        logs=[log.relative_to(tmp_path).as_posix()],
    )
    collect_acceptance([result], directory, tmp_path)
    assert len(list(directory.glob("owning-*.json"))) == 18
    rows = r.exit_rows(tmp_path, acceptance_directory=directory)
    assert rows[0].status == ("PASS" if outcome == "PASS" else "BLOCKED")
    for index, gap in ((4, "AQ-S3-08"), (16, "Linux")):
        expected = "BLOCKED" if outcome in {"FAIL", "ERROR"} else "DEFERRED"
        assert rows[index].status == expected
        if expected == "DEFERRED":
            assert gap in (rows[index].reason or "")
            assert r.verified_acceptance(rows[index], tmp_path)
    assert r.validate_exit(rows, (), tmp_path) == "BLOCKED"
    if outcome == "PASS":
        assert r.verified_acceptance(rows[0], tmp_path)
        for index in (4, 16):
            item = rows[index]
            disposition = tmp_path / r.EXIT_DEFERRALS[item.criterion]
            body = disposition.read_bytes()
            disposition.unlink()
            assert not r.verified_acceptance(item, tmp_path)
            assert r.exit_rows(tmp_path, acceptance_directory=directory)[index].status == "BLOCKED"
            disposition.write_bytes(body)
            wrong = r.B28_DISPOSITION
            with pytest.raises(ValueError):
                replace(item, disposition_refs=(wrong,))
            for changes in (
                {"failed": 1},
                {"errors": 1},
                {"skipped": 1},
                {"passed": 0},
                {"test_nodes": ()},
                {"exit_codes": (1,)},
                {"evidence_refs": ()},
            ):
                assert not r.verified_acceptance(replace(item, **changes), tmp_path)
        # Even a correctly signed owner gap cannot mask a failed owning case.
        for index in (4, 16):
            own = directory / f"owning-{index + 1:02d}.json"
            payload = json.loads(own.read_bytes())
            payload["cases"][0]["status"] = "FAIL"
            own.write_bytes(canonical_bytes(payload))
            assert not r.verified_acceptance(rows[index], tmp_path)
            assert r.exit_rows(tmp_path, acceptance_directory=directory)[index].status == "BLOCKED"
        # Missing/tampered logs invalidate a previously passing record.
        log.write_text("changed")
        assert not r.verified_acceptance(rows[0], tmp_path)
        assert r.exit_rows(tmp_path, acceptance_directory=directory)[0].status == "BLOCKED"
        payload = json.loads((directory / "owning-01.json").read_bytes())
        payload["row"]["dirty_diff_sha256"] = "b" * 64
        (directory / "owning-01.json").write_bytes(canonical_bytes(payload))
        assert r.exit_rows(tmp_path, acceptance_directory=directory)[0].status == "BLOCKED"
    (directory / "owning-01.json").unlink()
    assert r.exit_rows(tmp_path, acceptance_directory=directory)[0].status == "BLOCKED"


def test_s4_generated_narratives_known_gaps_and_owner_decisions(tmp_path, monkeypatch):
    identity, inventory, migrations = r.subject(), r.adapter_inventory(), r.migration_inventory()
    monkeypatch.setattr(r, "subject", lambda root=r.ROOT: identity)
    monkeypatch.setattr(r, "adapter_inventory", lambda root=r.ROOT: inventory)
    monkeypatch.setattr(r, "migration_inventory", lambda root=r.ROOT: migrations)
    r.write_reports(tmp_path)
    docs = tmp_path / "docs/phase2"
    for name in ("literature_trace_demo.md", "publication_trace_demo.md"):
        text = (docs / name).read_text()
        assert "READY" in text and "FROZEN PreparedSubmissionVersion" in text
    report = (docs / "phase2_exit_report.md").read_text()
    for token in (
        "AQ-S3-08",
        r.AQ_S3,
        r.LINUX_DISPOSITION,
        "first slices delivered",
        "NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE",
        "B23",
        "MANUSCRIPT_CHANGE",
    ):
        assert token in report
    assert "remain Phase 2 exit non-goals" not in report
    assert r.NOVELTY_DELIVERY in report
    assert r.NOVELTY_NON_GOALS in report
    for token in (
        "0070_b20_screening_basis",
        "0071_b23_novelty_review",
        "B20_Screening_Negative_Probe_Contract_DRAFT.md",
        "B23_Novelty_Review_Revision_Contract_DRAFT.md",
        "phase2_exit_review_2026-10-20.md",
        "12,523 passed, 66 skipped, 0 failed",
    ):
        assert token in report
    assert "Attach independent review and loop full-suite evidence" not in report
    inventory_text = (docs / "reference_system_inventory.md").read_text()
    for token in ("idna>=3.10,<4", "BSD-3-Clause", "IDNA/UTS-46", "transitive", "anyio"):
        assert token in inventory_text
    final = report.split("Owner decisions needed")[-1]
    for row in r.exit_rows(tmp_path):
        if row.status == "BLOCKED":
            assert row.criterion in final
    assert "Phase 2 is accepted" not in report


@pytest.fixture(scope="module")
def baseline_exit_rows():
    return r.exit_rows()


@pytest.mark.parametrize("index", [n for n in range(19) if n not in {4, 5, 16}])
@pytest.mark.parametrize("disposition", list(r.EXIT_DEFERRALS.values()))
def test_no_other_row_can_use_an_owner_gap_deferral(baseline_exit_rows, index, disposition):
    with pytest.raises(ValueError):
        replace(baseline_exit_rows[index], status="DEFERRED", disposition_refs=(disposition,))


@pytest.mark.parametrize(
    "criterion,wrong",
    [
        (criterion, wrong)
        for criterion, disposition in r.EXIT_DEFERRALS.items()
        for wrong in r.EXIT_DEFERRALS.values()
        if wrong != disposition
    ],
)
def test_each_deferral_requires_its_own_cited_file(baseline_exit_rows, criterion, wrong):
    item = baseline_exit_rows[r.EXIT_CRITERIA.index(criterion)]
    with pytest.raises(ValueError):
        replace(item, status="DEFERRED", disposition_refs=(wrong,))


def test_exit_verification_records_delivered_novelty_slices_and_director_evidence(
    tmp_path, monkeypatch
):
    from scripts import pr2_20_verify as verifier

    monkeypatch.setattr(verifier, "ROOT", tmp_path)
    monkeypatch.setattr(verifier, "exit_rows", lambda **kwargs: ())
    docs = tmp_path / "docs/phase2"
    docs.mkdir(parents=True)
    verifier.write_verification(r.context(), tmp_path, [], "BLOCKED")
    report = (docs / "pr2_20_verification.md").read_text()
    assert (
        "B20 NO_CLOSE_PRIOR_ART, B23 and MANUSCRIPT_CHANGE are Phase 2 exit non-goals" not in report
    )
    assert r.NOVELTY_DELIVERY in report
    assert r.NOVELTY_NON_GOALS in report
    assert r.EXIT_REVIEW_EVIDENCE in report
