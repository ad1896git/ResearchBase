"""Full gate blockers are operational inventory, never skipped acceptance tests."""

from pathlib import Path

# Frozen first-slice inventory, regardless of later code presence in this checkout.
HISTORICAL_BLOCKED_ROWS = {
    "G1": ("Search-result resolution admission",),
    "G2": ("Strategy candidate promotion",),
    "G4": ("Discussion candidate promotion",),
    "G5": ("Manuscript freeze",),
    "G6": (
        "Completed RevisionAction",
        "Issue disposition",
        "Revision-purpose Decision",
        "Concern carry-forward",
        "Manuscript review",
        "Basic Approval",
    ),
    "G7": (
        "Manuscript READY transition",
        "READY_FOR_SUBMISSION Decision purpose",
        "PREPARE_SUBMISSION Decision purpose",
        "PR2-17 preparation",
    ),
    "F1": (
        "Manuscript validity/audit projection",
        "Automatic finding/impact propagation",
        "Basic Approval",
    ),
    "F2b": ("Defensive unresolved-FK read",),
    "F5": ("Basic Approval", "Manuscript READY transition", "Manuscript review"),
    "F5b": ("Basic Approval",),
    "F5c": ("Basic Approval", "Reconsideration"),
    "F6": ("Completed RevisionAction", "Revision-purpose Decision"),
    "F7": ("Basic Approval",),
    "F9": ("Grant consumption",),
}
RESERVED_MODULES = ("test_pr2_19_revision.py", "test_pr2_19_grant_consumption.py")
HISTORICAL_BLOCKED_ARCHITECTURE = ("test_approval_does_not_override_invalid_fact",)


# Informational owner-availability inventory only; True means commands exist,
# NEVER that an E2E test ran or passed. Acceptance comes only from pytest evidence.
# B30 Start here step 2 and §§11.1/12.3 authorize this reconciliation.
# (row, subcase, owning Application contract, owner_available, remaining blocker)
SUBCASES = (
    ("G1", "resolution-evidence-conclusion", "search_result_resolution", True, None),
    ("G2", "native-candidate", "native_research_strategy", True, None),
    (
        "G2",
        "candidate-admission",
        "strategy_candidate_promotion",
        True,
        None,
    ),
    ("G4", "discussion-close-bind", "discussion_artifacts", True, None),
    ("G4", "discussion-admission", "discussion_hypothesis", True, None),
    (
        "G2",
        "s3-contract-reconciliation",
        "B30-S3/B02",
        False,
        "AQ-S3-08: bound AGENT fixture requires owning Application admission path",
    ),
    ("G5", "initial-frozen-closure", "manuscript_freeze", True, None),
    ("G6", "claim-conclusion-cycle", "revision_action/internal_review/approval", True, None),
    ("G6", "manuscript-cycle", "revision_action", False, "MANUSCRIPT_CHANGE denied"),
    ("G7", "novelty-inconclusive", "novelty", True, None),
    (
        "G7",
        "lock-free-completed-command-replay",
        "novelty",
        False,
        "Owner decision pending: authorize production snapshot replay or defer §7 requirement",
    ),
    (
        "G7",
        "readiness-package-consent",
        "publication/package",
        True,
        None,
    ),
    ("G7", "strong-novelty", "novelty", False, "Exact screening/comparison basis absent"),
    ("G7", "authorship-lock-free-read", "authorship", True, None),
    ("F1", "current-lineage-and-audit", "source_version/manuscript_validity", True, None),
    (
        "F1",
        "ready-package-downstream-projection",
        "publication/prepared_submission",
        True,
        None,
    ),
    (
        "F1",
        "automatic-finding-impact-propagation",
        "automatic propagation",
        False,
        "No automatic finding/impact propagation owner",
    ),
    ("F2b", "saved-formal-dependencies", "saved_provenance", True, None),
    ("F5", "approval-blockers", "approval", True, None),
    ("F5", "ready-consumption", "publication", True, None),
    ("F5b", "bounded-approval-denial", "approval", True, None),
    ("F5c", "release-reconsideration", "decision/approval", True, None),
    ("F5c", "manuscript-reconsideration", "decision", False, "B10 release-only scope"),
    ("F6", "six-action-types", "revision_action", True, None),
    ("F6", "manuscript-result", "revision_action", False, "Seventh action type deferred"),
    ("F7", "approval-command-atomicity", "approval", True, None),
    ("F9", "internal-release", "approval/scientific_conclusion", True, None),
    ("F9", "ready-package-consumption", "package", True, None),
    ("F9", "credential-grant-expiry", "approval/credential", True, None),
    (
        "F9",
        "scheduled-role-expiry",
        "identity",
        False,
        "BLOCKED: no owning Application command to schedule role expiry (AQ-S2-02)",
    ),
)
BLOCKED_ROWS = {
    row: tuple(blocker for r, _, _, _, blocker in SUBCASES if r == row and blocker)
    for row in HISTORICAL_BLOCKED_ROWS
    if any(r == row and blocker for r, _, _, _, blocker in SUBCASES)
}
# The behavioral obligation now has real B09/B13 tests in architecture boundaries.
BLOCKED_ARCHITECTURE = ()


def full_gate_report():
    return {
        "status": "BLOCKED",
        "availability_is_acceptance": False,
        "subcase_inventory_kind": "INFORMATIONAL_OWNER_AVAILABILITY",
        "blocked_rows": BLOCKED_ROWS,
        "blocked_row_count": len(BLOCKED_ROWS),
        "blocked_contract_count": len({item for row in BLOCKED_ROWS.values() for item in row}),
        "blocked_architecture": BLOCKED_ARCHITECTURE,
        "reserved_modules": RESERVED_MODULES,
    }


def require_full_gate(report):
    if report.get("subcase_inventory_kind") == "INFORMATIONAL_OWNER_AVAILABILITY":
        raise ValueError("PR2-19 full gate BLOCKED: owner availability is not acceptance evidence")
    if (
        BLOCKED_ROWS
        or BLOCKED_ARCHITECTURE
        or report["blocked_rows"]
        or report["blocked_architecture"]
    ):
        raise ValueError("PR2-19 full gate BLOCKED: mandatory prerequisites remain")


def test_all_blocked_matrix_rows_and_contracts_are_inventoried():
    import pytest

    plan = Path("docs/proposals/PR2-19_E2E_Failure_Injection_Plan_DRAFT.md").read_text()
    matrix = plan.split("### Runnable matrix and named fixtures")[1].split(
        "Create fixture wrappers"
    )[0]
    actual = {line.split("|")[1].strip() for line in matrix.splitlines() if "| BLOCKED BY " in line}
    assert set(HISTORICAL_BLOCKED_ROWS) == actual
    missing_table = plan.split("### Not in this slice")[1].split("## 15.")[0]
    contracts = {
        line.split("|")[1].strip()
        for line in missing_table.splitlines()
        if line.startswith("| ")
        and not line.startswith("| Missing contract")
        and not line.startswith("| ---")
    }
    assert contracts == {item for row in HISTORICAL_BLOCKED_ROWS.values() for item in row}
    assert all(not (Path(__file__).parent / name).exists() for name in RESERVED_MODULES)
    with pytest.raises(ValueError, match="BLOCKED"):
        require_full_gate(full_gate_report())


def test_current_subcases_reconcile_b30_without_claiming_full_rows_passed():
    contract = Path("docs/proposals/B30_PR2-19_Remaining_Rows_Contract_DRAFT.md").read_text()
    assert "APPROVED by owner 2026-10-18" in contract
    assert {row for row, *_ in SUBCASES} == set(HISTORICAL_BLOCKED_ROWS)
    assert len({(row, subcase) for row, subcase, *_ in SUBCASES}) == len(SUBCASES)
    for _, _, owner, owner_available, blocker in SUBCASES:
        assert owner and owner_available == (blocker is None)
    assert not {"G1", "G5", "F2b", "F5b", "F7"} & BLOCKED_ROWS.keys()
    assert {"G2", "G6", "G7", "F1", "F5c", "F6", "F9"} == BLOCKED_ROWS.keys()
    assert full_gate_report()["status"] == "BLOCKED"


def test_omitting_blockers_cannot_promote_informational_inventory_to_acceptance(monkeypatch):
    import pytest

    report = full_gate_report()
    assert report["availability_is_acceptance"] is False
    assert report["subcase_inventory_kind"] == "INFORMATIONAL_OWNER_AVAILABILITY"
    report.update(status="PASS", blocked_rows={}, blocked_architecture=())
    import sys

    monkeypatch.setattr(sys.modules[__name__], "BLOCKED_ROWS", {})
    monkeypatch.setattr(sys.modules[__name__], "BLOCKED_ARCHITECTURE", ())
    with pytest.raises(ValueError, match="BLOCKED"):
        require_full_gate(report)
