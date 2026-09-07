from __future__ import annotations

import shlex

import pytest
from scripts.pr18_evidence import (
    AUTHORITATIVE_COMMANDS,
    PR18EvidenceError,
    assess_evidence_readiness,
    authoritative_command_tokens,
    build_evidence_artifact,
    command_fingerprint,
    parse_pytest_counts,
    validate_command_entries,
    validate_current_command_registry,
    validate_evidence_artifact,
    validate_stored_command_registry,
)


def _entry(tokens: list[str]) -> dict[str, object]:
    return {
        "command": " ".join(tokens),
        "command_tokens": tokens,
        "command_fingerprint": command_fingerprint(tokens),
        "return_code": 0,
        "counts": {
            "total_discovered": 1,
            "selected": 1,
            "deselected": 0,
            "passed": 1,
            "failed": 0,
            "skipped": 0,
            "xfailed": 0,
            "xpassed": 0,
            "errors": 0,
            "return_code": 0,
        },
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
        "schema_version": "pr18r-evidence-v1",
        "protocol": "non-self-referential-v1",
        "implementation_subject": "abc123",
        "evidence_binding": {"mode": "separate-evidence-only-commit", "parent": "abc123"},
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
        commands=commands,
        metadata={"full_pytest": {"passed": 1}},
    )

    assert artifact["protocol"] == "non-self-referential-v1"
    assert "evidence_head" not in artifact
    assert artifact["command_consistency"] == {
        "stored": 1,
        "current": 1,
        "exact_token_matches": 1,
        "stale_result_reuse": False,
    }


def test_pytest_counts_reconcile_junit_and_collection_semantics() -> None:
    junit = """<testsuites><testsuite tests='5' failures='1' errors='0' skipped='2'>
      <testcase classname='x' name='pass'/>
      <testcase classname='x' name='fail'><failure/></testcase>
      <testcase classname='x' name='skip'><skipped/></testcase>
      <testcase classname='x' name='xfail'><skipped type='pytest.xfail'/></testcase>
      <testcase classname='x' name='xpass'/>
    </testsuite></testsuites>"""
    counts = parse_pytest_counts(
        output="1 failed, 1 skipped, 1 xfailed, 1 xpassed, 1 passed",
        collection_output="5/6 tests collected (1 deselected)",
        junit_xml=junit,
        return_code=1,
    )

    assert counts == {
        "total_discovered": 6,
        "selected": 5,
        "deselected": 1,
        "passed": 1,
        "failed": 1,
        "skipped": 1,
        "xfailed": 1,
        "xpassed": 1,
        "errors": 0,
        "return_code": 1,
    }


def test_pytest_count_parser_fails_closed_on_missing_machine_results() -> None:
    with pytest.raises(PR18EvidenceError):
        parse_pytest_counts(
            output="1 passed",
            collection_output="1 test collected",
            junit_xml=None,
            return_code=0,
        )


def test_pytest_count_parser_ignores_collection_text_inside_test_identifiers() -> None:
    counts = parse_pytest_counts(
        output="1 passed",
        collection_output=(
            "tests/unit/test_parser.py::test_case[1 test collected]\n1 test collected in 0.01s"
        ),
        junit_xml=(
            "<testsuite tests='1' failures='0' errors='0' skipped='0'><testcase/></testsuite>"
        ),
        return_code=0,
    )

    assert counts["selected"] == 1


@pytest.mark.parametrize(
    ("collection_output", "junit_xml"),
    [
        ("", "<testsuite tests='1' failures='0' errors='0' skipped='0'><testcase/></testsuite>"),
        (
            "1/2 tests collected (1 deselected)\n2/3 tests collected (1 deselected)",
            "<testsuite tests='1' failures='0' errors='0' skipped='0'><testcase/></testsuite>",
        ),
        (
            "1 test collected",
            "<testsuite failures='0' errors='0' skipped='0'></testsuite>",
        ),
        (
            "1 test collected",
            "<testsuite tests='2' failures='0' errors='0' skipped='0'><testcase/></testsuite>",
        ),
        (
            "1 test collected",
            "<testsuite tests='1' failures='bad' errors='0' skipped='0'><testcase/></testsuite>",
        ),
    ],
)
def test_pytest_count_parser_is_not_verified_for_missing_or_ambiguous_data(
    collection_output: str, junit_xml: str
) -> None:
    with pytest.raises(PR18EvidenceError):
        parse_pytest_counts(
            output="1 passed",
            collection_output=collection_output,
            junit_xml=junit_xml,
            return_code=0,
        )


def test_missing_count_data_blocks_readiness_as_not_verified() -> None:
    entry = _entry(["uv", "run", "pytest", "-q", "tests/unit"])
    del entry["counts"]["selected"]  # type: ignore[index]

    assert assess_evidence_readiness({"commands": {"focused": entry}}) == "NOT_VERIFIED"


@pytest.mark.parametrize(
    "field_value",
    [None, "1", -1, True],
)
def test_command_validation_rejects_malformed_pytest_count_values(field_value: object) -> None:
    entry = _entry(["uv", "run", "pytest", "-q", "tests/unit"])
    entry["counts"]["passed"] = field_value  # type: ignore[index]

    with pytest.raises(PR18EvidenceError):
        validate_command_entries({"focused": entry})


def test_authoritative_registry_has_no_absolute_or_credential_tokens() -> None:
    assert len(AUTHORITATIVE_COMMANDS) == 19
    assert validate_current_command_registry() == 19
    assert all(
        "DATABASE_URL=" not in token for _, command in AUTHORITATIVE_COMMANDS for token in command
    )


def test_authoritative_focused_command_includes_explain_topology_contracts() -> None:
    focused = dict(AUTHORITATIVE_COMMANDS)["pr18_focused_and_evidence_tool"]

    assert "tests/unit/test_pr18_explain_contract.py" in focused


def test_stored_commands_are_bound_to_the_current_registry() -> None:
    entries: dict[str, dict[str, object]] = {}
    for command_id, _command in AUTHORITATIVE_COMMANDS:
        tokens = authoritative_command_tokens(command_id)
        if "pytest" in tokens:
            counts = {
                key: 0
                for key in (
                    "total_discovered",
                    "selected",
                    "deselected",
                    "passed",
                    "failed",
                    "skipped",
                    "xfailed",
                    "xpassed",
                    "errors",
                    "return_code",
                )
            }
        else:
            counts = {"status": "PASS", "return_code": 0}
        entries[command_id] = {
            "command": shlex.join(tokens),
            "command_tokens": tokens,
            "command_fingerprint": command_fingerprint(tokens),
            "return_code": 0,
            "counts": counts,
        }
    validate_stored_command_registry(entries)
    entries["architecture"]["command_tokens"] = ["uv", "run", "pytest", "-q", "tests/other"]
    with pytest.raises(PR18EvidenceError):
        validate_stored_command_registry(entries)


def test_evidence_rejects_legacy_self_referential_head() -> None:
    commands = {"focused": _entry(["uv", "run", "pytest", "-q", "tests/unit"])}
    artifact = build_evidence_artifact(implementation_subject="abc123", commands=commands)
    artifact["evidence_head"] = "abc123"
    with pytest.raises(PR18EvidenceError):
        validate_evidence_artifact(artifact, implementation_subject="abc123")
