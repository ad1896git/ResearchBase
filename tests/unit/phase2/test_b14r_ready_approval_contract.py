"""READY reuses closed immutable approval DTOs and existing transport errors."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone
from typing import Any, cast
from uuid import UUID, uuid4

import pytest

from researchbase.api.errors import _STATUS
from researchbase.application.approval import DecideApprovalCommand, RequestApprovalCommand
from researchbase.cli.errors import CLI_EXIT_CODES
from researchbase.domain.approval import approval_tuple
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


def request(**changes):
    return cast(Any, RequestApprovalCommand)(
        **(
            dict(
                id=uuid4(),
                project_id=uuid4(),
                scientific_conclusion_version_id=None,
                manuscript_version_id=uuid4(),
                basis_decision_id=uuid4(),
                review_ids=(uuid4(),),
                approval_purpose="READY_FOR_SUBMISSION",
            )
            | changes
        )
    )


def decision(**changes):
    return cast(Any, DecideApprovalCommand)(
        **(
            dict(
                id=uuid4(),
                project_id=uuid4(),
                approval_request_id=uuid4(),
                decision="APPROVE",
                rationale="Permission",
            )
            | changes
        )
    )


def test_existing_closed_types_defaults_tuple_and_sorted_set():
    ids = (UUID(int=2), UUID(int=1))
    cmd = request(review_ids=ids)
    assert cmd.review_ids == tuple(reversed(ids))
    assert cmd.prior_rejected_request_id is cmd.reconsideration_decision_id is None
    assert approval_tuple(cmd.approval_purpose, None, cmd.manuscript_version_id) == (
        "ManuscriptVersion",
        "transition_publication_ready",
    )
    assert decision().requires_current_author_consent is False
    with pytest.raises(FrozenInstanceError):
        cast(Any, cmd).id = uuid4()
    with pytest.raises(TypeError):
        request(actor_id=uuid4())


@pytest.mark.parametrize(
    "field", ["id", "project_id", "manuscript_version_id", "basis_decision_id"]
)
@pytest.mark.parametrize("value", ["00000000-0000-0000-0000-000000000001", 1, True])
def test_strict_uuids(field, value):
    with pytest.raises(ResearchBaseError) as error:
        request(**{field: value})
    assert error.value.code == ErrorCode.VALIDATION_ERROR


@pytest.mark.parametrize("reviews", [(), [uuid4()], ("bad",), (UUID(int=1), UUID(int=1))])
def test_closed_distinct_reviews(reviews):
    with pytest.raises(ResearchBaseError):
        request(review_ids=reviews)


@pytest.mark.parametrize("size", [100, 101])
def test_replay_material_is_preserved_without_truncation(size):
    cmd = request(review_ids=tuple(uuid4() for _ in range(size)))
    assert len(cmd.review_ids) == size
    # Admission, rather than historical DTO construction, owns the 100-review ceiling.


@pytest.mark.parametrize("size", [16384, 16385])
def test_replay_text_is_preserved_without_truncation(size):
    assert len(decision(rationale="x" * size).rationale) == size


@pytest.mark.parametrize("text", ["", "  ", "\x00", "\ud800", b"text"])
def test_invalid_text(text):
    with pytest.raises(ResearchBaseError) as error:
        decision(rationale=text)
    assert error.value.code == ErrorCode.VALIDATION_ERROR


def test_nfc_whitespace_and_utc_normalization():
    assert decision(rationale=" Cafe\u0301 ").rationale == " Café "
    expiry = datetime(2026, 10, 19, tzinfo=timezone(timedelta(hours=2)))
    cmd = decision(decision="APPROVE_WITH_CONDITIONS", valid_until=expiry)
    assert cmd.valid_until == expiry.astimezone(UTC)
    assert cmd.valid_until is not None and cmd.valid_until.tzinfo == UTC


@pytest.mark.parametrize(
    "outcome", ["APPROVE", "APPROVE_WITH_CONDITIONS", "REJECT", "PROCEED", "approve"]
)
@pytest.mark.parametrize(
    "expiry", [None, datetime(2026, 10, 19), datetime(2026, 10, 19, tzinfo=UTC)]
)
def test_outcome_expiry_closed_policy(outcome, expiry):
    valid = (
        outcome in {"APPROVE", "REJECT"}
        and expiry is None
        or (
            outcome == "APPROVE_WITH_CONDITIONS"
            and expiry is not None
            and expiry.tzinfo is not None
        )
    )
    if valid:
        assert decision(decision=outcome, valid_until=expiry).decision == outcome
    else:
        with pytest.raises(ResearchBaseError):
            decision(decision=outcome, valid_until=expiry)


@pytest.mark.parametrize(
    "change",
    [
        dict(prior_rejected_request_id=uuid4()),
        dict(reconsideration_decision_id=uuid4()),
        dict(prior_rejected_request_id="bad", reconsideration_decision_id="bad"),
    ],
)
def test_successor_pair_is_strict(change):
    with pytest.raises(ResearchBaseError) as error:
        request(**change)
    assert error.value.code == ErrorCode.VALIDATION_ERROR


@pytest.mark.parametrize("purpose", ["READY", "ready_for_submission", "", 1])
def test_closed_purpose(purpose):
    with pytest.raises(ResearchBaseError):
        request(approval_purpose=purpose)


@pytest.mark.parametrize(
    "name,http,cli",
    [
        ("VALIDATION_ERROR", 422, 2),
        ("AUTHENTICATION_REQUIRED", 401, 3),
        ("FORBIDDEN", 403, 3),
        ("NOT_FOUND", 404, 3),
        ("CONFLICT_OF_INTEREST", 403, 3),
        ("APPROVAL_PURPOSE_TARGET_COMMAND_INVALID", 409, 4),
        ("DECISION_BASIS_INVALID", 409, 4),
        ("APPROVAL_GATE_FAILED", 409, 4),
        ("APPROVAL_TARGET_STALE", 409, 4),
        ("REJECTION_RECONSIDERATION_REQUIRED", 409, 4),
        ("IDEMPOTENCY_CONFLICT", 409, 4),
        ("IMMUTABLE_RECORD", 409, 4),
        ("CONCURRENT_MODIFICATION", 409, 4),
        ("FROZEN_REFERENCE_REQUIRED", 409, 5),
        ("PROVENANCE_CLOSURE_VIOLATION", 409, 5),
        ("REFERENTIAL_INTEGRITY_ERROR", 409, 5),
        ("GRANT_INVALID", 409, 4),
        ("GRANT_STALE", 409, 4),
    ],
)
def test_every_pinned_transport_mapping(name, http, cli):
    code = ErrorCode(name)
    assert _STATUS[code] == http and CLI_EXIT_CODES[code] == cli


@pytest.mark.parametrize(
    "state,code",
    [
        ("P04M3", ErrorCode.PROVENANCE_CLOSURE_VIOLATION),
        ("P14P1", ErrorCode.PROVENANCE_CLOSURE_VIOLATION),
        ("P14I1", ErrorCode.IMMUTABLE_RECORD),
        ("P14A1", ErrorCode.FORBIDDEN),
    ],
)
def test_nested_entry_and_structure_sql_errors_are_normalized(state, code):
    from sqlalchemy.exc import DBAPIError

    from researchbase.persistence.uow import _approval_database_error

    class DriverError(Exception):
        sqlstate = state

    error = _approval_database_error(
        DBAPIError(None, None, DriverError("protected diagnostics"), False)
    )
    assert error.code == code
    assert "protected diagnostics" not in error.message
