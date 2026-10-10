from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from scripts.pr2_04_verification_matrix import _load_results, _requirements

ROOT = Path(__file__).parents[3]
MATRIX = ROOT / "execution/phase2/PR2-04_Acceptance_Matrix_v1.0.md"
HOST_REVIEW = ROOT / "scripts/researchbase_host_pr2_04_verification.sh"


def test_matrix_parser_preserves_all_65_contract_rows() -> None:
    rows = _requirements(MATRIX)

    assert len(rows) == 65
    assert rows[0]["requirement"] == "PR204-DOM-01"
    assert rows[-1]["requirement"] == "PR204-EVID-02"
    assert all(
        row["invariant"] and row["evidence_type"] and row["expected_category"]
        for row in rows
    )
    bindings = json.loads((ROOT / "scripts/pr2_04_requirement_bindings.json").read_text())
    assert set(bindings["requirements"]) == {row["requirement"] for row in rows}


def test_matrix_evidence_index_requires_candidate_bound_artifacts(tmp_path: Path) -> None:
    head = "a" * 40
    artifact = tmp_path / "trace.json"
    artifact.write_text(json.dumps({"execution_head": head}))
    junit = tmp_path / "tests.xml"
    junit.write_text(
        '<testsuite><testcase classname="tests.unit.test_domain" name="test_transition" />'
        "</testsuite>"
    )
    evidence = {
        "execution_head": head,
        "rows": [
            {
                "requirement": "PR204-DOM-01",
                "result": "PASS",
                "node_ids": ["tests/unit/test_domain.py::test_transition"],
                "evidence": [
                    {
                        "path": "trace.json",
                        "candidate_head": head,
                        "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                    },
                    {
                        "path": "tests.xml",
                        "candidate_head": head,
                        "sha256": hashlib.sha256(junit.read_bytes()).hexdigest(),
                    },
                ],
            }
        ],
    }
    evidence_file = tmp_path / "index.json"
    evidence_file.write_text(json.dumps(evidence))

    with pytest.raises(ValueError, match="validated producer"):
        _load_results(evidence_file, tmp_path, head)

    evidence["execution_head"] = "b" * 40
    evidence_file.write_text(json.dumps(evidence))
    with pytest.raises(ValueError, match="current candidate HEAD"):
        _load_results(evidence_file, tmp_path, head)


def test_matrix_pass_cannot_omit_evidence_or_exact_node_ids(tmp_path: Path) -> None:
    head = "a" * 40
    evidence_file = tmp_path / "index.json"
    evidence_file.write_text(
        json.dumps(
            {
                "execution_head": head,
                "rows": [{"requirement": "PR204-DOM-01", "result": "PASS"}],
            }
        )
    )

    with pytest.raises(ValueError, match="PASS requires evidence artifacts and exact node IDs"):
        _load_results(evidence_file, tmp_path, head)


def test_host_review_dry_run_binds_frozen_contract_and_required_gates() -> None:
    completed = subprocess.run(
        ["bash", str(HOST_REVIEW), "--dry-run"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "FROZEN_CONTRACT_SHA=ea216c9babea322808b3885f563d276b571575ab" in completed.stdout
    assert "EXPECTED_MIGRATION=0024_literature_search_execution" in completed.stdout
    assert "matrix_65" in completed.stdout
