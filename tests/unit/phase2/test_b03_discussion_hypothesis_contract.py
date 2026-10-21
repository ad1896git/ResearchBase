"""Closed, normalized manual extraction and independently serialized hash vectors."""

import hashlib
import json
from dataclasses import FrozenInstanceError, replace
from typing import Any
from uuid import UUID, uuid4

import pytest

from researchbase.application.discussion_hypothesis import (
    DiscussionHypothesisCandidate,
    PromoteDiscussionHypothesisCommand,
    discussion_hypothesis_candidate_hash,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


def candidate(**changes):
    values: dict[str, Any] = dict(
        turn_id=UUID(int=3),
        transcript_artifact_version_id=UUID(int=4),
        research_question_version_id=UUID(int=5),
        statement="  Café Ω\n",
        expected_direction=None,
        rationale=None,
    )
    return DiscussionHypothesisCandidate(**(values | changes))


@pytest.mark.parametrize(
    "field,limit", [("statement", 16000), ("expected_direction", 64), ("rationale", 16000)]
)
@pytest.mark.parametrize("value", ["", " \t\n", "a\x00b", "\ud800", 1, True, b"text"])
def test_invalid_text(field, limit, value):
    with pytest.raises(ResearchBaseError) as exc:
        candidate(**{field: value})
    assert exc.value.code is ErrorCode.VALIDATION_ERROR


@pytest.mark.parametrize(
    "field,limit", [("statement", 16000), ("expected_direction", 64), ("rationale", 16000)]
)
def test_bounds_after_nfc(field, limit):
    assert len(getattr(candidate(**{field: "e\u0301" * limit}), field)) == limit
    with pytest.raises(ResearchBaseError):
        candidate(**{field: "x" * (limit + 1)})


@pytest.mark.parametrize(
    "field",
    ["status", "actor_id", "admitted_at", "candidate_hash", "hypothesis_id", "success_criteria"],
)
def test_forbidden_candidate_assertions(field):
    with pytest.raises(ResearchBaseError):
        candidate(**{field: "assertion"})


@pytest.mark.parametrize(
    "field", ["turn_id", "transcript_artifact_version_id", "research_question_version_id"]
)
@pytest.mark.parametrize("value", [True, 1, None, "00000000-0000-0000-0000-000000000001"])
def test_exact_uuid_fields(field, value):
    with pytest.raises(ResearchBaseError):
        candidate(**{field: value})


def test_literal_hash_vector_and_normalized_identity():
    c = candidate(statement="  Cafe\u0301 Ω\n")
    material = {
        "schema": "discussion_hypothesis_candidate_v1",
        "project_id": "00000000-0000-0000-0000-000000000001",
        "session_id": "00000000-0000-0000-0000-000000000002",
        "turn_id": "00000000-0000-0000-0000-000000000003",
        "transcript_artifact_version_id": "00000000-0000-0000-0000-000000000004",
        "research_question_version_id": "00000000-0000-0000-0000-000000000005",
        "statement": "  Café Ω\n",
        "expected_direction": None,
        "success_criteria": None,
        "rationale": None,
    }
    expected = hashlib.sha256(
        json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert str(discussion_hypothesis_candidate_hash(UUID(int=1), UUID(int=2), c)) == expected
    assert c == candidate()
    assert (
        discussion_hypothesis_candidate_hash(UUID(int=1), UUID(int=2), replace(c, rationale="why"))
        != expected
    )
    with pytest.raises((FrozenInstanceError, ResearchBaseError, ValueError)):
        c.statement = "changed"


def test_closed_command_and_uuid_boundaries():
    c = candidate()
    command = PromoteDiscussionHypothesisCommand(uuid4(), uuid4(), uuid4(), c)
    assert command.candidate is c
    for field in ("project_id", "session_id", "request_id"):
        with pytest.raises(ResearchBaseError):
            replace(command, **{field: str(uuid4())})
    with pytest.raises(ResearchBaseError):
        PromoteDiscussionHypothesisCommand(uuid4(), uuid4(), uuid4(), c, status="FROZEN")  # type: ignore[call-arg]


@pytest.mark.parametrize(
    "state,constraint,expected",
    [
        ("P17D1", None, ErrorCode.IMMUTABLE_RECORD),
        ("P17D3", None, ErrorCode.PROVENANCE_CLOSURE_VIOLATION),
        ("40001", None, ErrorCode.CONCURRENT_MODIFICATION),
        ("40P01", None, ErrorCode.CONCURRENT_MODIFICATION),
        ("55P03", None, ErrorCode.CONCURRENT_MODIFICATION),
        ("23505", "uq_b03_candidate", ErrorCode.DUPLICATE_CONTENT),
        (
            "23505",
            "discussion_command_receipts_deployment_id_project_id_actor_id_key",
            ErrorCode.CONCURRENT_MODIFICATION,
        ),
        ("23503", "fk_b03_turn", ErrorCode.REFERENTIAL_INTEGRITY_ERROR),
        ("23514", "ck_b03_statement", ErrorCode.VALIDATION_ERROR),
    ],
)
def test_pinned_database_error_categories(state, constraint, expected):
    from types import SimpleNamespace

    from sqlalchemy.exc import DBAPIError
    from sqlalchemy.orm import Session

    from researchbase.persistence.uow import SqlAlchemyUnitOfWork

    class DriverError(Exception):
        sqlstate = state
        diag = SimpleNamespace(constraint_name=constraint)

    error = DBAPIError(None, None, DriverError())
    uow = SqlAlchemyUnitOfWork(Session)
    uow._b03_error_normalization = True
    assert uow._command_database_error(error).code is expected
    unknown = DBAPIError(None, None, RuntimeError("unexpected defect"))
    with pytest.raises(DBAPIError):
        uow._command_database_error(unknown)
