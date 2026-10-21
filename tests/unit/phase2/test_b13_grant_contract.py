"""Literal R3 vectors, closed command types and pure terminal precedence."""

from dataclasses import FrozenInstanceError, fields, replace
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID, uuid4

import pytest

from researchbase.api.errors import _STATUS
from researchbase.application.approval import (
    EvaluateApprovalGrantCommand,
    RecordInternalScientificReleaseCommand,
    RevokeApprovalGrantCommand,
)
from researchbase.cli.errors import CLI_EXIT_CODES
from researchbase.domain.approval import (
    consumption_request_material,
    decode_consumption_result,
    evaluate_grant,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import sha256_canonical_json


def material(**kwargs):
    values: dict[str, Any] = dict(
        project_id=UUID(int=0x10),
        actor_id=UUID(int=0x11),
        grant_id=UUID(int=0x25),
        command="TRANSITION_PUBLICATION_READY",
        target_type="ManuscriptVersion",
        target_id=UUID(int=7),
        target_hash="b" * 64,
        result_id=UUID(int=4),
        expected_package_manifest_hash=None,
        checked_review_ids=(UUID(int=0x13), UUID(int=0x12)),
    )
    values.update(kwargs)
    return consumption_request_material(**values)


def test_independent_r3_golden_vectors():
    first = material()
    assert (
        str(sha256_canonical_json(first))
        == "c08f141629ea381ea71ddc9ad1f44ceb952fa1d6cbcc3e0847263a53cbaddf3b"
    )
    assert material(checked_review_ids=(UUID(int=0x12), UUID(int=0x13))) == first
    assert (
        str(sha256_canonical_json(material(grant_id=UUID(int=0x26))))
        == "b65aa64fa7ae49e3842d78d78295d445b741f7dde09d2472d0949802983f7b2b"
    )
    assert set(first) == {
        "type",
        "material_version",
        "command",
        "project_id",
        "actor_id",
        "grant_id",
        "target",
        "result_id",
        "expected_package_manifest_hash",
        "checked_review_ids",
    }
    assert first["expected_package_manifest_hash"] is None


@pytest.mark.parametrize(
    "changes",
    [
        {"project_id": 1},
        {"actor_id": True},
        {"checked_review_ids": ()},
        {"checked_review_ids": (UUID(int=1),) * 2},
        {"checked_review_ids": [UUID(int=1)]},
        {"checked_review_ids": tuple(UUID(int=i) for i in range(101))},
        {"expected_package_manifest_hash": "a" * 64},
        {"target_hash": "B" * 64},
        {"command": "record_internal_scientific_release"},
        {"target_type": "ClaimVersion"},
    ],
)
def test_literal_rejects_coercion_missing_or_extra_semantics(changes):
    with pytest.raises(ValueError):
        material(**changes)


def test_all_three_literal_tuples_and_limits():
    material(checked_review_ids=tuple(UUID(int=i) for i in range(100)))
    material(command="FREEZE_PREPARED_SUBMISSION", expected_package_manifest_hash="c" * 64)
    material(
        command="RECORD_INTERNAL_SCIENTIFIC_RELEASE",
        target_type="ScientificConclusionVersion",
        result_id=UUID(int=7),
    )
    with pytest.raises(ValueError):
        material(command="FREEZE_PREPARED_SUBMISSION")
    with pytest.raises(ValueError):
        material(
            command="RECORD_INTERNAL_SCIENTIFIC_RELEASE", target_type="ScientificConclusionVersion"
        )


@pytest.mark.parametrize(
    "status,at_delta,issuer,dependency,expected",
    [
        ("ACTIVE", 0, True, True, ("EXPIRED", "GRANT_INVALID")),
        ("ACTIVE", -1, False, True, ("STALE", "GRANT_STALE")),
        ("ACTIVE", -1, False, False, ("STALE", "GRANT_STALE")),
        ("ACTIVE", -1, True, False, (None, "APPROVAL_GATE_FAILED")),
        ("CONSUMED", -1, False, False, (None, "GRANT_INVALID")),
        ("REVOKED", 1, False, True, (None, "GRANT_INVALID")),
        ("EXPIRED", 1, True, True, (None, "GRANT_INVALID")),
        ("STALE", 1, True, True, (None, "GRANT_STALE")),
    ],
)
def test_terminal_precedence(status, at_delta, issuer, dependency, expected):
    until = datetime(2026, 10, 17, tzinfo=UTC)
    result = evaluate_grant(
        uuid4(),
        status,
        until,
        until + timedelta(seconds=at_delta),
        issuer_active=issuer,
        dependency_available=dependency,
    )
    assert (result.proposed_terminal_status, result.unusable_code) == expected
    assert not result.usable
    with pytest.raises(FrozenInstanceError):
        cast(Any, result).usable = True


def test_evaluator_reasons_are_complete_and_sorted_corruption_never_stales():
    now = datetime.now(UTC)
    result = evaluate_grant(
        uuid4(),
        "ACTIVE",
        now + timedelta(hours=1),
        now,
        issuer_active=True,
        reason_codes=("APPROVAL_TARGET_STALE", "APPROVAL_GATE_FAILED"),
    )
    assert result.reason_codes == ("APPROVAL_GATE_FAILED", "APPROVAL_TARGET_STALE", "GRANT_STALE")
    with pytest.raises(ValueError):
        evaluate_grant(
            uuid4(),
            "ACTIVE",
            now,
            now,
            issuer_active=True,
            reason_codes=("PROVENANCE_CLOSURE_VIOLATION",),
        )


def test_closed_input_fields_and_reason_unicode_bounds():
    ids = [uuid4() for _ in range(4)]
    cmd = RecordInternalScientificReleaseCommand(ids[0], ids[1], ids[2], ids[3], (uuid4(),))
    assert not {"actor_id", "at", "status", "effective_at"} & {f.name for f in fields(cmd)}
    with pytest.raises(ResearchBaseError):
        replace(cmd, result_id=cast(Any, True))
    assert RevokeApprovalGrantCommand(ids[0], ids[1], "e\u0301").reason == "é"
    RevokeApprovalGrantCommand(ids[0], ids[1], "é" * 16384)
    for text in ("", " ", "\ud800", "a" * 16385, "\x00"):
        with pytest.raises(ResearchBaseError):
            RevokeApprovalGrantCommand(ids[0], ids[1], text)
    assert {f.name for f in fields(EvaluateApprovalGrantCommand)} == {"project_id", "grant_id"}


@pytest.mark.parametrize("version", [True, 0, 2, "1"])
def test_saved_result_version_is_strict(version):
    with pytest.raises(ValueError):
        decode_consumption_result(cast(Any, version), {})


def test_saved_result_is_closed_and_frozen():
    value = {
        "command": "RECORD_INTERNAL_SCIENTIFIC_RELEASE",
        "scientific_conclusion_version_id": str(uuid4()),
        "consumption_id": str(uuid4()),
    }
    result = decode_consumption_result(1, value)
    with pytest.raises(FrozenInstanceError):
        cast(Any, result).consumption_id = uuid4()
    with pytest.raises(ValueError):
        decode_consumption_result(1, value | {"current_validity": "VALID"})


@pytest.mark.parametrize(
    "name,http,cli",
    [
        ("VALIDATION_ERROR", 422, 2),
        ("AUTHENTICATION_REQUIRED", 401, 3),
        ("FORBIDDEN", 403, 3),
        ("CONFLICT_OF_INTEREST", 403, 3),
        ("NOT_FOUND", 404, 3),
        ("APPROVAL_PURPOSE_TARGET_COMMAND_INVALID", 409, 4),
        ("DECISION_BASIS_INVALID", 409, 4),
        ("APPROVAL_GATE_FAILED", 409, 4),
        ("APPROVAL_TARGET_STALE", 409, 4),
        ("REJECTION_RECONSIDERATION_REQUIRED", 409, 4),
        ("GRANT_INVALID", 409, 4),
        ("GRANT_STALE", 409, 4),
        ("IDEMPOTENCY_CONFLICT", 409, 4),
        ("CONCURRENT_MODIFICATION", 409, 4),
        ("IMMUTABLE_RECORD", 409, 4),
        ("PROVENANCE_CLOSURE_VIOLATION", 409, 5),
        ("REFERENTIAL_INTEGRITY_ERROR", 409, 5),
    ],
)
def test_pinned_error_pairs(name, http, cli):
    code = ErrorCode(name)
    assert _STATUS[code] == http and CLI_EXIT_CODES[code] == cli
