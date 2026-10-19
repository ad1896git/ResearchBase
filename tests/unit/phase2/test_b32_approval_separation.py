"""Independent three-purpose policy, request material and transport contracts."""

from dataclasses import replace
from datetime import UTC, datetime
from itertools import product
from typing import Any, cast
from uuid import UUID

import pytest

from researchbase.api.errors import _STATUS
from researchbase.application.approval import (
    DecideApprovalCommand,
    RecordInternalScientificReleaseCommand,
    RequestApprovalCommand,
)
from researchbase.application.prepared_submission import FreezePreparedSubmissionCommand
from researchbase.application.publication import TransitionPublicationReadyCommand
from researchbase.cli.errors import CLI_EXIT_CODES
from researchbase.domain.approval import (
    RECEIPT_COMMANDS,
    TUPLES,
    PreparedSubmissionFreezeResult,
    PublicationReadyResult,
    ScientificReleaseResult,
    approval_tuple,
    consumption_request_material,
    decode_consumption_result,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import sha256_canonical_json

# These expectations are literals from architectures 17/18, never production-derived.
ROWS = (
    (
        "INTERNAL_SCIENTIFIC_RELEASE",
        "ScientificConclusionVersion",
        "record_internal_scientific_release",
        "RECORD_INTERNAL_SCIENTIFIC_RELEASE",
        "scientific_conclusion_version_id",
        ScientificReleaseResult,
    ),
    (
        "READY_FOR_SUBMISSION",
        "ManuscriptVersion",
        "transition_publication_ready",
        "TRANSITION_PUBLICATION_READY",
        "publication_id",
        PublicationReadyResult,
    ),
    (
        "PREPARE_SUBMISSION",
        "ManuscriptVersion",
        "freeze_prepared_submission",
        "FREEZE_PREPARED_SUBMISSION",
        "prepared_submission_version_id",
        PreparedSubmissionFreezeResult,
    ),
)


def test_complete_finite_policy():
    assert TUPLES == {row[0]: (row[1], row[2]) for row in ROWS}
    assert RECEIPT_COMMANDS == {row[0]: row[3] for row in ROWS}


@pytest.mark.parametrize("row", ROWS)
def test_exact_policy_and_saved_result(row):
    purpose, target, capability, receipt, key, result_class = row
    conclusion = UUID(int=7) if target == "ScientificConclusionVersion" else None
    manuscript = UUID(int=7) if target == "ManuscriptVersion" else None
    assert approval_tuple(purpose, conclusion, manuscript) == (target, capability)
    saved = {"command": receipt, key: str(UUID(int=7)), "consumption_id": str(UUID(int=8))}
    assert decode_consumption_result(1, saved) == result_class(UUID(int=7), UUID(int=8))


@pytest.mark.parametrize("row,other", list(product(ROWS, repeat=2)))
def test_receipt_result_cross_product(row, other):
    saved = {"command": row[3], other[4]: str(UUID(int=7)), "consumption_id": str(UUID(int=8))}
    if row == other:
        assert isinstance(decode_consumption_result(1, saved), row[5])
    else:
        with pytest.raises(ValueError):
            decode_consumption_result(1, saved)


@pytest.mark.parametrize("row", ROWS)
def test_wrong_target_and_case_are_denied(row):
    purpose, target = row[:2]
    wrong_conclusion = UUID(int=7) if target == "ManuscriptVersion" else None
    wrong_manuscript = UUID(int=7) if target == "ScientificConclusionVersion" else None
    with pytest.raises(ResearchBaseError) as caught:
        RequestApprovalCommand(
            UUID(int=1),
            UUID(int=2),
            wrong_conclusion,
            UUID(int=3),
            (UUID(int=4),),
            purpose,
            manuscript_version_id=wrong_manuscript,
        )
    assert caught.value.code == ErrorCode.APPROVAL_PURPOSE_TARGET_COMMAND_INVALID
    for altered in (purpose.lower(), purpose + " ", row[2], row[3]):
        with pytest.raises(ValueError):
            approval_tuple(
                altered,
                UUID(int=7) if target == "ScientificConclusionVersion" else None,
                UUID(int=7) if target == "ManuscriptVersion" else None,
            )


def material(row, **changes):
    values: dict[str, Any] = dict(
        project_id=UUID(int=0x10),
        actor_id=UUID(int=0x11),
        grant_id=UUID(int=0x25),
        command=row[3],
        target_type=row[1],
        target_id=UUID(int=7),
        target_hash="b" * 64,
        result_id=UUID(int=7) if row[0] == "INTERNAL_SCIENTIFIC_RELEASE" else UUID(int=4),
        expected_package_manifest_hash="c" * 64 if row[0] == "PREPARE_SUBMISSION" else None,
        checked_review_ids=(UUID(int=0x13), UUID(int=0x12)),
    )
    values.update(changes)
    return consumption_request_material(**values)


@pytest.mark.parametrize("row", ROWS)
def test_literal_r3_preimage(row):
    expected = {
        "type": "ApprovalGrantConsumptionRequest",
        "material_version": 1,
        "command": row[3],
        "project_id": str(UUID(int=0x10)),
        "actor_id": str(UUID(int=0x11)),
        "grant_id": str(UUID(int=0x25)),
        "target": {"type": row[1], "id": str(UUID(int=7)), "content_hash": "b" * 64},
        "result_id": str(UUID(int=7 if row[0] == "INTERNAL_SCIENTIFIC_RELEASE" else 4)),
        "expected_package_manifest_hash": "c" * 64 if row[0] == "PREPARE_SUBMISSION" else None,
        "checked_review_ids": [str(UUID(int=0x12)), str(UUID(int=0x13))],
    }
    assert material(row) == expected
    assert material(row, checked_review_ids=(UUID(int=0x12), UUID(int=0x13))) == expected
    if row[0] == "READY_FOR_SUBMISSION":
        assert str(sha256_canonical_json(expected)) == (
            "c08f141629ea381ea71ddc9ad1f44ceb952fa1d6cbcc3e0847263a53cbaddf3b"
        )
        assert str(sha256_canonical_json(material(row, grant_id=UUID(int=0x26)))) == (
            "b65aa64fa7ae49e3842d78d78295d445b741f7dde09d2472d0949802983f7b2b"
        )


@pytest.mark.parametrize("row", ROWS)
@pytest.mark.parametrize(
    "change",
    [
        {"command": "freeze_prepared_submission"},
        {"command": "SEND_SUBMISSION"},
        {"project_id": True},
        {"actor_id": 1},
        {"grant_id": str(UUID(int=1))},
        {"target_hash": "B" * 64},
        {"target_hash": "g" * 64},
        {"target_type": "ClaimVersion"},
        {"checked_review_ids": ()},
        {"checked_review_ids": [UUID(int=1)]},
        {"checked_review_ids": (True,)},
        {"checked_review_ids": (UUID(int=1),) * 2},
        {"checked_review_ids": tuple(UUID(int=i) for i in range(101))},
    ],
)
def test_material_rejects_coercion_and_noncanonical_values(row, change):
    with pytest.raises(ValueError):
        material(row, **change)


def commands():
    common = (UUID(int=1), UUID(int=2), UUID(int=3), UUID(int=4))
    return (
        RecordInternalScientificReleaseCommand(*common, (UUID(int=5),)),
        TransitionPublicationReadyCommand(*common, (UUID(int=5),)),
        FreezePreparedSubmissionCommand(*common, "a" * 64, (UUID(int=5),)),
    )


@pytest.mark.parametrize("index", range(3))
@pytest.mark.parametrize("count", [0, 1, 100, 101])
def test_effect_review_bounds(index, count):
    reviews = tuple(UUID(int=i) for i in reversed(range(count)))
    if count in (1, 100):
        assert replace(commands()[index], checked_review_ids=reviews).checked_review_ids == tuple(
            sorted(reviews, key=str)
        )
    else:
        with pytest.raises(ResearchBaseError) as caught:
            replace(commands()[index], checked_review_ids=reviews)
        assert caught.value.code == ErrorCode.VALIDATION_ERROR


@pytest.mark.parametrize("index", range(3))
@pytest.mark.parametrize(
    "change",
    [
        {"command_key": True},
        {"project_id": 1},
        {"grant_id": str(UUID(int=1))},
        {"result_id": None},
        {"checked_review_ids": [UUID(int=1)]},
        {"checked_review_ids": (UUID(int=1),) * 2},
        {"checked_review_ids": (True,)},
    ],
)
def test_all_effects_use_strict_inputs(index, change):
    with pytest.raises(ResearchBaseError) as caught:
        replace(commands()[index], **change)
    assert caught.value.code == ErrorCode.VALIDATION_ERROR


@pytest.mark.parametrize("digest", [None, True, "A" * 64, "g" * 64, "a" * 63, "a" * 65])
def test_package_manifest_is_strict_hex(digest):
    with pytest.raises(ResearchBaseError):
        replace(commands()[2], expected_package_manifest_hash=cast(Any, digest))
    with pytest.raises(ValueError):
        material(ROWS[2], expected_package_manifest_hash=digest)


@pytest.mark.parametrize("flag", [0, 1, None, "true"])
def test_consent_condition_is_strict_bool(flag):
    with pytest.raises(ResearchBaseError) as caught:
        DecideApprovalCommand(
            UUID(int=1),
            UUID(int=2),
            UUID(int=3),
            "APPROVE_WITH_CONDITIONS",
            "Independent",
            datetime(2026, 10, 20, tzinfo=UTC),
            cast(Any, flag),
        )
    assert caught.value.code == ErrorCode.VALIDATION_ERROR


@pytest.mark.parametrize("row", ROWS)
@pytest.mark.parametrize("version", [True, False, 0, 2, "1"])
def test_decoder_version_is_strict(row, version):
    saved = {"command": row[3], row[4]: str(UUID(int=7)), "consumption_id": str(UUID(int=8))}
    with pytest.raises(ValueError):
        decode_consumption_result(cast(Any, version), saved)


@pytest.mark.parametrize("row", ROWS)
@pytest.mark.parametrize("change", ["extra", "lowercase", "uuid", "compact", "unknown"])
def test_decoder_is_closed(row, change):
    identity = UUID("abcdefab-1234-4567-89ab-abcdefabcdef")
    saved = {"command": row[3], row[4]: str(identity), "consumption_id": str(UUID(int=8))}
    if change == "extra":
        saved["sent"] = True
    elif change == "lowercase":
        saved["command"] = row[3].lower()
    elif change == "uuid":
        saved[row[4]] = str(identity).upper()
    elif change == "compact":
        saved[row[4]] = identity.hex
    else:
        saved["command"] = "SEND_SUBMISSION"
    with pytest.raises(ValueError):
        decode_consumption_result(1, saved)


@pytest.mark.parametrize(
    "name,http,cli",
    [
        ("VALIDATION_ERROR", 422, 2),
        ("NOT_FOUND", 404, 3),
        ("AUTHENTICATION_REQUIRED", 401, 3),
        ("FORBIDDEN", 403, 3),
        ("CONFLICT_OF_INTEREST", 403, 3),
        ("APPROVAL_PURPOSE_TARGET_COMMAND_INVALID", 409, 4),
        ("APPROVAL_GATE_FAILED", 409, 4),
        ("DECISION_BASIS_INVALID", 409, 4),
        ("APPROVAL_TARGET_STALE", 409, 4),
        ("REJECTION_RECONSIDERATION_REQUIRED", 409, 4),
        ("GRANT_INVALID", 409, 4),
        ("GRANT_STALE", 409, 4),
        ("IDEMPOTENCY_CONFLICT", 409, 4),
        ("CONCURRENT_MODIFICATION", 409, 4),
        ("INVALID_STATE_TRANSITION", 409, 4),
        ("VERSION_NOT_FROZEN", 409, 4),
        ("IMMUTABLE_RECORD", 409, 4),
        ("FROZEN_REFERENCE_REQUIRED", 409, 5),
        ("PROVENANCE_CLOSURE_VIOLATION", 409, 5),
        ("REFERENTIAL_INTEGRITY_ERROR", 409, 5),
    ],
)
def test_transport_mapping(name, http, cli):
    assert _STATUS[ErrorCode(name)] == http
    assert CLI_EXIT_CODES[ErrorCode(name)] == cli


def test_unexpected_error_uses_sanitized_existing_fallback():
    import asyncio

    from fastapi import FastAPI
    from starlette.requests import Request

    from researchbase.api.errors import install_error_handlers
    from researchbase.cli.errors import INTERNAL_ERROR_EXIT_CODE

    app = FastAPI()
    install_error_handlers(app)
    request = Request({"type": "http", "headers": []})
    request.state.request_id = UUID(int=1)
    handler = app.exception_handlers[Exception]
    response = asyncio.run(cast(Any, handler)(request, RuntimeError("PRIVATE_CREDENTIAL")))
    assert response.status_code == 500
    assert b'"code":"INTERNAL_ERROR"' in response.body
    assert b"PRIVATE_CREDENTIAL" not in response.body
    assert INTERNAL_ERROR_EXIT_CODE == 1
