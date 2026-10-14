"""Literal approval hash and finite closed DTO policy."""

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID, uuid4

import pytest

from researchbase.api.errors import _STATUS
from researchbase.application.approval import DecideApprovalCommand, RequestApprovalCommand
from researchbase.cli.errors import CLI_EXIT_CODES
from researchbase.domain.approval import approval_decision_material
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import sha256_canonical_json


def test_literal_r2_approval_golden_vector():
    material = approval_decision_material(
        UUID(int=0x14),
        UUID(int=7),
        "b" * 64,
        "APPROVE",
        None,
        False,
        "Gate passed.",
        UUID(int=0x15),
        target_type="ManuscriptVersion",
    )
    assert str(sha256_canonical_json(material)) == (
        "d5de0062b526e4555429d13482cf6521f39bd7ce8b72544b604f66c8fb0229de"
    )
    assert "decided_at" not in material and "status" not in material


@pytest.mark.parametrize(
    "purpose",
    [
        "READY_FOR_SUBMISSION",
        "PREPARE_SUBMISSION",
        "",
        "INTERNAL",
        "record_internal_scientific_release",
    ],
)
def test_unavailable_purpose_denies(purpose):
    with pytest.raises(ResearchBaseError) as denied:
        RequestApprovalCommand(uuid4(), uuid4(), uuid4(), uuid4(), (uuid4(),), purpose)
    assert denied.value.code is ErrorCode.APPROVAL_PURPOSE_TARGET_COMMAND_INVALID


@pytest.mark.parametrize("reviews", [(), (uuid4(), uuid4()), [uuid4()], ("bad",)])
def test_closed_review_set(reviews):
    if type(reviews) is tuple and len(reviews) == 2:
        reviews = (reviews[0], reviews[0])
    with pytest.raises(ResearchBaseError):
        RequestApprovalCommand(uuid4(), uuid4(), uuid4(), uuid4(), reviews)


def test_normalization_and_immutability():
    ids = (uuid4(), uuid4())
    command = RequestApprovalCommand(uuid4(), uuid4(), uuid4(), uuid4(), ids)
    assert command == replace(command, review_ids=tuple(reversed(ids)))
    decision = DecideApprovalCommand(
        uuid4(), command.project_id, command.id, "APPROVE", "Cafe\u0301"
    )
    assert decision.rationale == "Café"
    with pytest.raises(FrozenInstanceError):
        cast(Any, command).id = uuid4()
    with pytest.raises(TypeError):
        cast(Any, RequestApprovalCommand)(uuid4(), uuid4(), uuid4(), uuid4(), ids, bypass=True)


@pytest.mark.parametrize("outcome", ["APPROVE", "REJECT", "APPROVE_WITH_CONDITIONS"])
@pytest.mark.parametrize("expiry", [None, datetime.now(UTC) + timedelta(days=1)])
@pytest.mark.parametrize("consent", [False, True, 1])
def test_finite_conditions(outcome, expiry, consent):
    accepted = (
        type(consent) is bool
        and not consent
        and ((outcome == "APPROVE_WITH_CONDITIONS") == (expiry is not None))
    )
    args = (uuid4(), uuid4(), uuid4(), outcome, "TEST ONLY rationale", expiry, consent)
    if accepted:
        assert DecideApprovalCommand(*args).decision == outcome
    else:
        with pytest.raises(ResearchBaseError):
            DecideApprovalCommand(*args)


@pytest.mark.parametrize("expiry", [datetime(2026, 1, 1), "tomorrow", 1])
def test_bad_timestamps(expiry):
    with pytest.raises(ResearchBaseError):
        DecideApprovalCommand(
            uuid4(), uuid4(), uuid4(), "APPROVE_WITH_CONDITIONS", "reason", expiry
        )


@pytest.mark.parametrize(
    "code",
    [
        ErrorCode.APPROVAL_PURPOSE_TARGET_COMMAND_INVALID,
        ErrorCode.APPROVAL_GATE_FAILED,
        ErrorCode.DECISION_BASIS_INVALID,
        ErrorCode.APPROVAL_TARGET_STALE,
        ErrorCode.REJECTION_RECONSIDERATION_REQUIRED,
        ErrorCode.GRANT_INVALID,
        ErrorCode.GRANT_STALE,
    ],
)
def test_error_mappings(code):
    assert _STATUS[code] == 409 and CLI_EXIT_CODES[code] == 4
