from __future__ import annotations

import json
import shlex
from pathlib import Path

import pytest
from scripts import pr17dr_evidence


def _stored_artifact() -> dict[str, object]:
    commands = {}
    for command_id, command in pr17dr_evidence.VERIFICATION_COMMANDS:
        tokens = pr17dr_evidence._authoritative_command_tokens(command_id, command)
        commands[command_id] = {
            "command": shlex.join(tokens),
            "command_tokens": tokens,
            "command_fingerprint": pr17dr_evidence._command_fingerprint(tokens),
        }
    return {"commands": commands}


def _run_main_until_database(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, artifact: dict[str, object] | None
) -> tuple[Path, bytes | None, list[str]]:
    output_dir = tmp_path / "evidence"
    artifact_path = output_dir / "implementation_verification.json"
    original = None
    if artifact is not None:
        output_dir.mkdir()
        original = (json.dumps(artifact, sort_keys=True) + "\n").encode()
        artifact_path.write_bytes(original)
    events: list[str] = []

    def stop_at_database(_url: str) -> object:
        events.append("database")
        raise RuntimeError("reached database")

    monkeypatch.setattr(pr17dr_evidence, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(pr17dr_evidence, "OUTPUT_DIR", Path("evidence"))
    monkeypatch.setattr(pr17dr_evidence, "create_database_engine", stop_at_database)
    monkeypatch.setenv("DATABASE_URL", "postgresql://redacted")
    monkeypatch.setenv(pr17dr_evidence.IMPLEMENTATION_SUBJECT_ENV, "subject")
    monkeypatch.setattr(pr17dr_evidence, "_subject_head", lambda: "subject")

    return artifact_path, original, events


def test_authoritative_main_audits_matching_stored_commands_before_database(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    artifact_path, original, events = _run_main_until_database(
        monkeypatch, tmp_path, _stored_artifact()
    )

    with pytest.raises(RuntimeError, match="reached database"):
        pr17dr_evidence.main()

    assert events == ["database"]
    assert artifact_path.read_bytes() == original


@pytest.mark.parametrize(
    "drift",
    [
        "executable",
        "argument",
        "missing",
        "extra",
        "malformed_commands",
        "malformed_entry",
        "missing_tokens",
    ],
)
def test_authoritative_main_rejects_stored_command_drift_before_database_or_write(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, drift: str
) -> None:
    artifact = _stored_artifact()
    commands = artifact["commands"]
    assert isinstance(commands, dict)
    if drift == "executable":
        commands["postgresql_integration"]["command_tokens"][2] = "not-pytest"
    elif drift == "argument":
        commands["postgresql_integration"]["command_tokens"][6] = "not-integration"
    elif drift == "missing":
        del commands["postgresql_integration"]
    elif drift == "extra":
        commands["extra"] = commands["ruff"]
    elif drift == "malformed_commands":
        artifact["commands"] = []
    elif drift == "malformed_entry":
        commands["postgresql_integration"] = []
    else:
        del commands["postgresql_integration"]["command_tokens"]
    artifact_path, original, events = _run_main_until_database(monkeypatch, tmp_path, artifact)

    with pytest.raises(RuntimeError, match="stored command evidence"):
        pr17dr_evidence.main()

    assert events == []
    assert artifact_path.read_bytes() == original


def test_authoritative_main_explicitly_allows_first_generation_before_database(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    artifact_path, _, events = _run_main_until_database(monkeypatch, tmp_path, None)

    with pytest.raises(RuntimeError, match="reached database"):
        pr17dr_evidence.main()

    assert events == ["database"]
    assert not artifact_path.exists()


def test_authoritative_main_rejects_duplicate_json_keys_before_database(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    artifact_path, _, events = _run_main_until_database(monkeypatch, tmp_path, None)
    artifact_path.parent.mkdir()
    commands = json.dumps(_stored_artifact()["commands"], sort_keys=True)
    original = f'{{"commands": [], "commands": {commands}}}\n'.encode()
    artifact_path.write_bytes(original)

    with pytest.raises(RuntimeError, match="stored command evidence"):
        pr17dr_evidence.main()

    assert events == []
    assert artifact_path.read_bytes() == original


def test_authoritative_main_rejects_dangling_artifact_symlink_before_database(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    artifact_path, _, events = _run_main_until_database(monkeypatch, tmp_path, None)
    artifact_path.parent.mkdir()
    target = tmp_path / "missing-artifact"
    artifact_path.symlink_to(target)

    with pytest.raises(RuntimeError, match="stored command evidence"):
        pr17dr_evidence.main()

    assert events == []
    assert artifact_path.is_symlink()
    assert artifact_path.readlink() == target


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
    assert pr17dr_evidence._validated_pytest_counts("...ss...", "10 tests collected", None) is None
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
        assert pr17dr_evidence._stored_command_mismatches(drifted) == ["postgresql_integration"]


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
