from __future__ import annotations

import pytest
from scripts.pr18_evidence import (
    PR18EvidenceError,
    build_evidence_artifact,
    command_fingerprint,
    validate_command_entries,
    validate_evidence_artifact,
)


def _entry(tokens: list[str]) -> dict[str, object]:
    return {
        "command": " ".join(tokens),
        "command_tokens": tokens,
        "command_fingerprint": command_fingerprint(tokens),
        "return_code": 0,
        "counts": {"total_discovered": 1, "passed": 1, "failed": 0, "skipped": 0},
    }


def test_command_validation_accepts_exact_tokens_and_fingerprints() -> None:
    entries = {"focused": _entry(["uv", "run", "pytest", "-q", "tests/unit"])}

    assert validate_command_entries(entries) == {"stored": 1, "valid": 1}


@pytest.mark.parametrize(
    "mutation",
    [
        lambda item: item.update(command="uv run pytest -q tests/other"),
        lambda item: item.update(command_fingerprint="bad"),
        lambda item: item.update(command_tokens=["/tmp/secret", "run"]),
        lambda item: item.update(command_tokens=["uv", "run", "--password=secret"]),
    ],
)
def test_command_validation_fails_closed_for_drift_paths(mutation: object) -> None:
    item = _entry(["uv", "run", "pytest", "-q", "tests/unit"])
    mutation(item)  # type: ignore[operator]

    with pytest.raises(PR18EvidenceError):
        validate_command_entries({"focused": item})


def test_evidence_validation_requires_current_subject_and_exact_command_accounting() -> None:
    commands = {"focused": _entry(["uv", "run", "pytest", "-q", "tests/unit"])}
    artifact = {
        "schema_version": "pr18-evidence-v1",
        "implementation_subject": "abc123",
        "evidence_head": "def456",
        "audits": {
            "absolute_paths": [],
            "credential_leakage": [],
            "reproducible": True,
        },
        "command_consistency": {
            "stored": 1,
            "current": 1,
            "exact_token_matches": 1,
            "stale_result_reuse": False,
        },
        "commands": commands,
    }

    assert validate_evidence_artifact(artifact, implementation_subject="abc123") is None

    artifact["command_consistency"] = {
        "stored": 1,
        "current": 0,
        "exact_token_matches": 0,
        "stale_result_reuse": True,
    }
    with pytest.raises(PR18EvidenceError):
        validate_evidence_artifact(artifact, implementation_subject="abc123")


def test_generator_builds_the_same_fail_closed_shape_it_validates() -> None:
    commands = {"focused": _entry(["uv", "run", "pytest", "-q", "tests/unit"])}

    artifact = build_evidence_artifact(
        implementation_subject="abc123",
        evidence_head="def456",
        commands=commands,
        metadata={"full_pytest": {"passed": 1}},
    )

    assert artifact["command_consistency"] == {
        "stored": 1,
        "current": 1,
        "exact_token_matches": 1,
        "stale_result_reuse": False,
    }
