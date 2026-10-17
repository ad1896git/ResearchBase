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
        and (not consent or outcome == "APPROVE_WITH_CONDITIONS")
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


@pytest.mark.parametrize(
    "purpose",
    ["INTERNAL_SCIENTIFIC_RELEASE", "READY_FOR_SUBMISSION", "PREPARE_SUBMISSION", "OTHER"],
)
@pytest.mark.parametrize("kind", ["conclusion", "manuscript"])
def test_b09_finite_tuple_cross_product(purpose, kind):
    from researchbase.domain.approval import TUPLES, approval_tuple

    conclusion = uuid4() if kind == "conclusion" else None
    manuscript = uuid4() if kind == "manuscript" else None
    valid = (purpose == "INTERNAL_SCIENTIFIC_RELEASE" and kind == "conclusion") or (
        purpose in {"READY_FOR_SUBMISSION", "PREPARE_SUBMISSION"} and kind == "manuscript"
    )
    if valid:
        command = RequestApprovalCommand(
            uuid4(),
            uuid4(),
            conclusion,
            uuid4(),
            (uuid4(),),
            purpose,
            manuscript_version_id=manuscript,
        )
        assert approval_tuple(purpose, conclusion, manuscript) == TUPLES[purpose]
        assert command.manuscript_version_id == manuscript
    else:
        with pytest.raises(ResearchBaseError) as denied:
            RequestApprovalCommand(
                uuid4(),
                uuid4(),
                conclusion,
                uuid4(),
                (uuid4(),),
                purpose,
                manuscript_version_id=manuscript,
            )
        assert denied.value.code is ErrorCode.APPROVAL_PURPOSE_TARGET_COMMAND_INVALID


@pytest.mark.parametrize("targets", [(None, None), (uuid4(), uuid4()), (True, None), (None, "bad")])
def test_b09_exact_target_xor(targets):
    with pytest.raises(ResearchBaseError) as denied:
        RequestApprovalCommand(
            uuid4(), uuid4(), targets[0], uuid4(), (uuid4(),), manuscript_version_id=targets[1]
        )
    assert denied.value.code is ErrorCode.VALIDATION_ERROR


@pytest.mark.parametrize("rationale", ["a\x00b", "\ud800", "", "  ", True, 1])
def test_b09_strict_rationale(rationale):
    with pytest.raises(ResearchBaseError) as denied:
        DecideApprovalCommand(uuid4(), uuid4(), uuid4(), "APPROVE", rationale)
    assert denied.value.code is ErrorCode.VALIDATION_ERROR


@pytest.mark.parametrize("count", [100, 101])
def test_b09_historical_size_limits_are_not_constructor_limits(count):
    request = RequestApprovalCommand(
        uuid4(), uuid4(), uuid4(), uuid4(), tuple(uuid4() for _ in range(count))
    )
    assert len(request.review_ids) == count
    for length in (16384, 16385):
        assert (
            len(
                DecideApprovalCommand(
                    uuid4(), request.project_id, request.id, "APPROVE", "x" * length
                ).rationale
            )
            == length
        )


def test_b09_unchanged_literal_conclusion_hash():
    import hashlib

    literal = b'{"approval_request_id":"00000000-0000-0000-0000-000000000014","decided_by":{"id":"00000000-0000-0000-0000-000000000015","type":"ActorIdentity"},"decision":"REJECT","material_version":1,"rationale":"Gate failed.","requires_current_author_consent":false,"target":{"content_hash":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","id":"00000000-0000-0000-0000-000000000007","type":"ScientificConclusionVersion"},"type":"ApprovalDecision","valid_until":null}'  # noqa: E501 — independent literal hash vector
    material = approval_decision_material(
        UUID(int=20), UUID(int=7), "b" * 64, "REJECT", None, False, "Gate failed.", UUID(int=21)
    )
    assert str(sha256_canonical_json(material)) == hashlib.sha256(literal).hexdigest()


@pytest.mark.parametrize(
    "state,attempts", [("40001", 3), ("40P01", 3), ("55P03", 1), ("57014", 1), ("23505", 1)]
)
def test_b09_retry_only_serialization_deadlock(state, attempts, monkeypatch):
    from sqlalchemy.exc import DBAPIError

    from researchbase.application.approval import ApprovalService
    from researchbase.persistence.uow import _approval_database_error

    class DriverError(Exception):
        sqlstate = state
        diag = None

    # Exercise the actual stable driver classifier and service attempt boundary.
    error = _approval_database_error(DBAPIError(None, None, DriverError(), False))
    service = ApprovalService(cast(Any, lambda: None), None, None)
    from researchbase.domain.phase2_identity import VerifiedPrincipal

    calls = []

    def once(*args):
        calls.append(1)
        raise error

    monkeypatch.setattr(service, "_once", once)
    monkeypatch.setattr(service, "_replay", lambda *args: None)
    # Principal instances carry no DB capability; command path authenticates later.
    principal = object.__new__(VerifiedPrincipal)
    command = RequestApprovalCommand(uuid4(), uuid4(), uuid4(), uuid4(), (uuid4(),))
    with pytest.raises(ResearchBaseError):
        service.request_approval(principal, command)
    assert len(calls) == attempts
