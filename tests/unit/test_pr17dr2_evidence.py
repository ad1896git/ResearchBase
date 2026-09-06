from __future__ import annotations

from scripts import pr17dr_evidence


def test_authoritative_verification_commands_are_reproducible() -> None:
    audit = pr17dr_evidence._audit_verification_commands()

    assert audit == {
        "expected": 18,
        "audited": 18,
        "duplicated_executables": [],
        "invalid_executable_sequences": [],
        "missing_targets": [],
        "absolute_paths": [],
        "credential_bearing_tokens": [],
    }


def test_evidence_counts_are_parsed_from_executed_output() -> None:
    result = pr17dr_evidence._summary_counts("7 passed, 2 skipped, 1 deselected")

    assert result == {
        "passed": 7,
        "failed": 0,
        "skipped": 2,
        "deselected": 1,
        "xfailed": 0,
        "xpassed": 0,
    }


def test_unexecuted_or_uncollectable_check_is_not_verified() -> None:
    projection = pr17dr_evidence._invariant_projection({}, "PASS")[0]

    assert projection["verdict"] == "NOT_VERIFIED"
    assert projection["observed"] == {"commands": [], "db_enforced": None}


def test_inherited_skip_is_distinguished_from_current_remediation_skip() -> None:
    details = pr17dr_evidence._skip_details(
        "SKIPPED [1] tests/integration/test_pr11r2_migration.py:204: "
        "PR11R2_MIGRATION_DB_URL is not set"
    )

    assert details == [
        {
            "count": 1,
            "nodeid": "tests/integration/test_pr11r2_migration.py:204",
            "reason": "PR11R2_MIGRATION_DB_URL is not set",
            "classification": "inherited_pr11r2",
        }
    ]


def test_quiet_success_counts_are_reconciled_from_collection_and_skip_report() -> None:
    result = pr17dr_evidence._reconcile_success_counts(
        {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "deselected": 0,
            "xfailed": 0,
            "xpassed": 0,
        },
        "SKIPPED [2] tests/integration/test_pr11r2_migration.py:204: opt-in\n",
        10,
        0,
    )

    assert result["passed"] == 8
    assert result["skipped"] == 2


def test_projection_separates_expected_observed_and_verdict() -> None:
    command = {
        "command": "uv run pytest tests/integration/test_pr17dr_adversarial.py",
        "verdict": "PASS",
        "skips": [],
    }
    projection = pr17dr_evidence._invariant_projection({"adversarial": command}, "PASS")[0]

    assert set(projection) >= {"expected", "observed", "verdict", "source"}
    assert projection["expected"]["db_enforced"] is True
    assert projection["observed"]["commands"] == ["adversarial"]
    assert projection["verdict"] == "PASS"
