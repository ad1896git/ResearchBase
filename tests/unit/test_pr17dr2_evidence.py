from __future__ import annotations

import shlex

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


def test_unfiltered_pytest_counts_are_exact() -> None:
    result = pr17dr_evidence._validated_pytest_counts(
        "721 passed, 2 skipped",
        "723 tests collected",
        '<testsuite tests="723" failures="0" errors="0" skipped="2"/>',
    )

    assert result == {
        "total_discovered": 723,
        "collected": 723,
        "passed": 721,
        "failed": 0,
        "skipped": 2,
        "xfailed": 0,
        "xpassed": 0,
        "error": 0,
        "deselected": 0,
    }


def test_marker_filtered_quiet_pytest_counts_are_exact() -> None:
    result = pr17dr_evidence._validated_pytest_counts(
        "...ss...\nSKIPPED [1] tests/a.py:1: opt-in",
        "332/723 tests collected (391 deselected)",
        '<testsuite tests="332" failures="0" errors="0" skipped="2"/>',
    )

    assert result == {
        "total_discovered": 723,
        "collected": 332,
        "passed": 330,
        "failed": 0,
        "skipped": 2,
        "xfailed": 0,
        "xpassed": 0,
        "error": 0,
        "deselected": 391,
    }


def test_failure_and_error_counts_are_not_success() -> None:
    result = pr17dr_evidence._validated_pytest_counts(
        "1 passed, 1 failed, 1 error",
        "3 tests collected",
        '<testsuite tests="3" failures="1" errors="1" skipped="0"/>',
    )

    assert result is not None
    assert result["passed"] == 1
    assert result["failed"] == 1
    assert result["error"] == 1
    assert not pr17dr_evidence._all_required_checks_pass(
        {"failure": {"verdict": "FAIL", "skips": []}}
    )


def test_xfail_and_xpass_are_not_counted_as_ordinary_outcomes() -> None:
    result = pr17dr_evidence._validated_pytest_counts(
        "2 passed, 1 skipped, 1 xfailed, 1 xpassed",
        "5 tests collected",
        '<testsuite tests="5" failures="0" errors="0" skipped="2"/>',
    )

    assert result is not None
    assert result["passed"] == 2
    assert result["skipped"] == 1
    assert result["xfailed"] == 1
    assert result["xpassed"] == 1


def test_incomplete_or_inconsistent_pytest_counts_are_not_verified() -> None:
    assert (
        pr17dr_evidence._validated_pytest_counts(
            "...ss...", "10 tests collected", None
        )
        is None
    )
    assert (
        pr17dr_evidence._validated_pytest_counts(
            "8 passed", "10 tests collected", '<testsuite tests="9"/>'
        )
        is None
    )


def test_stored_command_drift_is_rejected_structurally() -> None:
    valid = {}
    for command_id, command in pr17dr_evidence.VERIFICATION_COMMANDS:
        tokens = pr17dr_evidence._authoritative_command_tokens(command_id, command)
        valid[command_id] = {
            "command": shlex.join(tokens),
            "command_tokens": tokens,
            "command_fingerprint": pr17dr_evidence._command_fingerprint(tokens),
        }
    assert pr17dr_evidence._stored_command_mismatches(valid) == []

    for replacement in (
        "tests/integration/not_the_target.py",
        "not-integration",
        "pytest",
    ):
        drifted = {
            key: {**value, "command_tokens": [*value["command_tokens"]]}
            for key, value in valid.items()
        }
        tokens = drifted["postgresql_integration"]["command_tokens"]
        if replacement.endswith(".py"):
            tokens.append(replacement)
        elif replacement == "pytest":
            tokens.insert(tokens.index("pytest") + 1, replacement)
        else:
            tokens[tokens.index("integration")] = replacement
        assert pr17dr_evidence._stored_command_mismatches(drifted) == [
            "postgresql_integration"
        ]


def test_command_fingerprint_is_bound_to_normalized_tokens() -> None:
    tokens = ["uv", "run", "pytest", "-m", "integration"]

    assert pr17dr_evidence._command_fingerprint(tokens) == pr17dr_evidence._command_fingerprint(
        shlex.split(shlex.join(tokens))
    )
    assert pr17dr_evidence._command_fingerprint(tokens) != pr17dr_evidence._command_fingerprint(
        [*tokens, "tests/integration/test_pr17dr_catalog.py"]
    )


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
