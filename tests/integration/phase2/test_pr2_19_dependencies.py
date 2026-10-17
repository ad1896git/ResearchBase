"""Full gate blockers are operational inventory, never skipped acceptance tests."""

from pathlib import Path

# Frozen first-slice inventory, regardless of later code presence in this checkout.
BLOCKED_ROWS = {
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
        "PR2-18 novelty",
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
BLOCKED_ARCHITECTURE = ("test_approval_does_not_override_invalid_fact",)


def full_gate_report():
    return {
        "status": "BLOCKED",
        "blocked_rows": BLOCKED_ROWS,
        "blocked_row_count": len(BLOCKED_ROWS),
        "blocked_contract_count": len({item for row in BLOCKED_ROWS.values() for item in row}),
        "blocked_architecture": BLOCKED_ARCHITECTURE,
        "reserved_modules": RESERVED_MODULES,
    }


def require_full_gate(report):
    if report["blocked_rows"] or report["blocked_architecture"]:
        raise ValueError("PR2-19 full gate BLOCKED: mandatory prerequisites remain")


def test_all_blocked_matrix_rows_and_contracts_are_inventoried():
    import pytest

    plan = Path("docs/proposals/PR2-19_E2E_Failure_Injection_Plan_DRAFT.md").read_text()
    matrix = plan.split("### Runnable matrix and named fixtures")[1].split(
        "Create fixture wrappers"
    )[0]
    actual = {line.split("|")[1].strip() for line in matrix.splitlines() if "| BLOCKED BY " in line}
    assert set(BLOCKED_ROWS) == actual
    missing_table = plan.split("### Not in this slice")[1].split("## 15.")[0]
    contracts = {
        line.split("|")[1].strip()
        for line in missing_table.splitlines()
        if line.startswith("| ")
        and not line.startswith("| Missing contract")
        and not line.startswith("| ---")
    }
    assert contracts == {item for row in BLOCKED_ROWS.values() for item in row}
    assert all(not (Path(__file__).parent / name).exists() for name in RESERVED_MODULES)
    with pytest.raises(ValueError, match="BLOCKED"):
        require_full_gate(full_gate_report())
