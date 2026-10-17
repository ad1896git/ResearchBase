"""Closed readiness admission and pinned existing error categories."""

# SQL and independent literal hash vectors preserve contract spelling.
# ruff: noqa: E501

from dataclasses import FrozenInstanceError, fields
from typing import Any, cast
from uuid import uuid4

import pytest

from researchbase.api.errors import _STATUS
from researchbase.application.decision import (
    GetPrepareSubmissionDecisionQuery,
    RecordPrepareSubmissionDecisionCommand,
)
from researchbase.cli.errors import CLI_EXIT_CODES
from researchbase.domain.decision import DecisionBasisReference, validate_readiness_review_count
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


def args() -> dict[str, Any]:
    return dict(
        id=uuid4(), project_id=uuid4(), manuscript_version_id=uuid4(), question="Q", rationale="R"
    )


@pytest.mark.parametrize("field", ["id", "project_id", "manuscript_version_id"])
@pytest.mark.parametrize("bad", [None, True, 3, "00000000-0000-0000-0000-000000000001"])
def test_exact_uuid(field, bad):
    with pytest.raises(ResearchBaseError) as exc:
        cast(Any, RecordPrepareSubmissionDecisionCommand)(**(args() | {field: bad}))
    assert exc.value.code == ErrorCode.VALIDATION_ERROR


@pytest.mark.parametrize("field", ["question", "rationale"])
@pytest.mark.parametrize("bad", ["", " \t\n", "\ud800", "x\x00", "x" * 16001, None, 17, True])
def test_text_denial(field, bad):
    with pytest.raises(ResearchBaseError) as exc:
        cast(Any, RecordPrepareSubmissionDecisionCommand)(**(args() | {field: bad}))
    assert exc.value.code == ErrorCode.VALIDATION_ERROR


@pytest.mark.parametrize("size", [1, 16000])
def test_normalization_and_bounds(size):
    result = cast(Any, RecordPrepareSubmissionDecisionCommand)(
        **(args() | dict(question="é" * size, rationale="  e\u0301  "))
    )
    assert len(result.question) == size and result.rationale == "  é  "
    with pytest.raises(FrozenInstanceError):
        result.question = "changed"  # type: ignore[misc]
    assert not hasattr(result, "__dict__")


@pytest.mark.parametrize(
    "field,bad",
    [
        ("decision_type", "REVISION_RESPONSE"),
        ("decision_type", "READY_FOR_SUBMISSION"),
        ("decision", "REJECT"),
        ("decision", None),
    ],
)
def test_closed_literals(field, bad):
    with pytest.raises(ResearchBaseError):
        cast(Any, RecordPrepareSubmissionDecisionCommand)(**(args() | {field: bad}))


@pytest.mark.parametrize(
    "extra",
    [
        "actor",
        "decided_at",
        "basis",
        "supersedes_decision_id",
        "hash",
        "publication_id",
        "review_ids",
    ],
)
def test_extra_fields(extra):
    with pytest.raises(TypeError):
        cast(Any, RecordPrepareSubmissionDecisionCommand)(**(args() | {extra: None}))


def test_query_and_bool_ordinal():
    with pytest.raises(ResearchBaseError):
        GetPrepareSubmissionDecisionQuery("bad", uuid4())  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        DecisionBasisReference("ManuscriptVersion", uuid4(), "a" * 64, True)
    assert {f.name for f in fields(GetPrepareSubmissionDecisionQuery)} == {"project_id", "id"}


@pytest.mark.parametrize("count", [0, -1, 10001, True, 1.0])
def test_complete_set_ceiling(count):
    with pytest.raises(ValueError):
        validate_readiness_review_count(count)


@pytest.mark.parametrize("count", [1, 10000])
def test_no_truncation(count):
    validate_readiness_review_count(count)


@pytest.mark.parametrize(
    "name,http,cli",
    [
        ("AUTHENTICATION_REQUIRED", 401, 3),
        ("FORBIDDEN", 403, 3),
        ("VALIDATION_ERROR", 422, 2),
        ("NOT_FOUND", 404, 3),
        ("CONFLICT_OF_INTEREST", 403, 3),
        ("FROZEN_REFERENCE_REQUIRED", 409, 5),
        ("DECISION_BASIS_INVALID", 409, 4),
        ("INVALID_STATE_TRANSITION", 409, 4),
        ("APPROVAL_PURPOSE_TARGET_COMMAND_INVALID", 409, 4),
        ("APPROVAL_GATE_FAILED", 409, 4),
        ("APPROVAL_TARGET_STALE", 409, 4),
        ("REJECTION_RECONSIDERATION_REQUIRED", 409, 4),
        ("GRANT_INVALID", 409, 4),
        ("GRANT_STALE", 409, 4),
        ("IDEMPOTENCY_CONFLICT", 409, 4),
        ("IMMUTABLE_RECORD", 409, 4),
        ("REFERENTIAL_INTEGRITY_ERROR", 409, 5),
        ("PROVENANCE_CLOSURE_VIOLATION", 409, 5),
        ("CONCURRENT_MODIFICATION", 409, 4),
    ],
)
def test_pinned_error_mapping(name, http, cli):
    assert _STATUS[ErrorCode(name)] == http
    assert CLI_EXIT_CODES[ErrorCode(name)] == cli


@pytest.mark.parametrize(
    "state,code",
    [
        ("P17F1", ErrorCode.IMMUTABLE_RECORD),
        ("P17F2", ErrorCode.PROVENANCE_CLOSURE_VIOLATION),
        ("P17F3", ErrorCode.IDEMPOTENCY_CONFLICT),
        ("40001", ErrorCode.CONCURRENT_MODIFICATION),
        ("40P01", ErrorCode.CONCURRENT_MODIFICATION),
        ("55P03", ErrorCode.INVALID_STATE_TRANSITION),
        ("57014", ErrorCode.INVALID_STATE_TRANSITION),
        ("XX000", ErrorCode.INVALID_STATE_TRANSITION),
        ("23503", ErrorCode.REFERENTIAL_INTEGRITY_ERROR),
    ],
)
def test_sqlstate_mapping_and_no_driver_disclosure(state, code):
    from types import SimpleNamespace

    from sqlalchemy.exc import DBAPIError

    from researchbase.persistence.uow import _decision_database_error

    error = _decision_database_error(
        DBAPIError(None, None, cast(Any, SimpleNamespace(sqlstate=state, diag=None)))
    )
    assert error.code == code and state not in error.message
