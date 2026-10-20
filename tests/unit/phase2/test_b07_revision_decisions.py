"""Closed B07 policy, literal Decision material and bounded retries."""

from dataclasses import asdict, replace
from typing import Any, cast
from uuid import UUID, uuid4

import pytest

from researchbase.application.decision import DecisionService, RecordRevisionDecisionCommand
from researchbase.application.revision_action import RecordConcernReReviewCommand
from researchbase.domain.decision import (
    DecisionBasisReference,
    decision_basis_material,
    decision_content_material,
    validate_revision_choice,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


def command(**changes):
    return replace(
        RecordRevisionDecisionCommand(uuid4(), uuid4(), uuid4(), "Q", "R", "REQUIRE_CHANGE"),
        **changes,
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("id", "00000000-0000-0000-0000-000000000001"),
        ("project_id", None),
        ("review_issue_id", 1),
        ("question", " "),
        ("rationale", "\ud800"),
        ("question", "x" * 16001),
        ("rationale", "x" * 16001),
        ("decision", "PROCEED"),
        ("decision_type", "INTERNAL_SCIENTIFIC_RELEASE"),
        ("decision", "require_change"),
    ],
)
def test_closed_material_denies(field, value):
    with pytest.raises(ResearchBaseError) as caught:
        command(**{field: value})
    assert caught.value.code == ErrorCode.VALIDATION_ERROR


def test_text_nfc_boundaries_and_unknown_actor():
    c = command(question=" Cafe\u0301 ", rationale="x" * 16000)
    assert c.question == " Café " and len(c.rationale) == 16000
    with pytest.raises(TypeError):
        cast(Any, RecordRevisionDecisionCommand)(**asdict(c), decided_by=uuid4())


@pytest.mark.parametrize("choice", ["REQUIRE_CHANGE", "ACCEPT_NO_CHANGE"])
@pytest.mark.parametrize(
    "action",
    [
        "NEW_EXPERIMENT",
        "ANALYSIS_CHANGE",
        "CLAIM_CHANGE",
        "CONCLUSION_CHANGE",
        "SOURCE_CHANGE",
        "NO_CHANGE",
        "MANUSCRIPT_CHANGE",
    ],
)
def test_finite_choice_matrix(choice, action):
    allowed = (choice == "ACCEPT_NO_CHANGE" and action == "NO_CHANGE") or (
        choice == "REQUIRE_CHANGE" and action != "NO_CHANGE"
    )
    if allowed:
        validate_revision_choice("REVISION_RESPONSE", choice, action)
    else:
        with pytest.raises(ValueError):
            validate_revision_choice("REVISION_RESPONSE", choice, action)


def test_r2_literal_decision_and_sorted_ordinals():
    ids = [UUID(int=i) for i in range(1, 5)]
    h = "a" * 64
    basis = (
        DecisionBasisReference("InternalReviewRecord", ids[1], h, 1),
        DecisionBasisReference("ClaimVersion", ids[0], h, 0),
    )
    assert decision_basis_material(basis) == {
        "type": "DecisionRecordBasisSet",
        "material_version": 1,
        "basis": [
            {
                "target": {"type": "ClaimVersion", "id": str(ids[0]), "content_hash": h},
                "ordinal": 0,
            },
            {
                "target": {"type": "InternalReviewRecord", "id": str(ids[1]), "content_hash": h},
                "ordinal": 1,
            },
        ],
    }
    assert decision_content_material(
        ids[2], "REVISION_RESPONSE", "Q", "ACCEPT_NO_CHANGE", "R", ids[3], h
    ) == {
        "type": "DecisionRecord",
        "material_version": 1,
        "project_id": str(ids[2]),
        "decision_type": "REVISION_RESPONSE",
        "question": "Q",
        "decision": "ACCEPT_NO_CHANGE",
        "rationale": "R",
        "decided_by": {"type": "ActorIdentity", "id": str(ids[3])},
        "supersedes_decision_id": None,
        "basis_set_hash": h,
    }
    with pytest.raises(ValueError):
        decision_basis_material(tuple(replace(r, ordinal=1 - r.ordinal) for r in basis))


def test_trusted_principal_and_closed_link():
    with pytest.raises(ResearchBaseError) as caught:
        DecisionService(cast(Any, lambda: None), None, None).record_revision_decision(
            None, command()
        )
    assert caught.value.code == ErrorCode.AUTHENTICATION_REQUIRED
    with pytest.raises(ResearchBaseError):
        RecordConcernReReviewCommand(uuid4(), uuid4(), cast(Any, "bad"))


@pytest.mark.parametrize(
    "code", [ErrorCode.CONCURRENT_MODIFICATION, ErrorCode.INVALID_STATE_TRANSITION]
)
@pytest.mark.parametrize("method", ["decision", "link"])
def test_only_concurrency_category_retries_three_fresh_attempts(monkeypatch, code, method):
    from unittest.mock import Mock

    from researchbase.application.revision_action import RevisionActionService
    from researchbase.domain.phase2_identity import VerifiedPrincipal

    principal = Mock(spec=VerifiedPrincipal)
    if method == "decision":
        service = DecisionService(cast(Any, lambda: None), None, None)
        once = "_record_revision_once"
        invoke = service.record_revision_decision
        cmd = command()
    else:
        service = RevisionActionService(cast(Any, lambda: None), None, None)
        once = "_record_correspondence_once"
        invoke = service.record_concern_re_review
        cmd = RecordConcernReReviewCommand(uuid4(), uuid4(), uuid4())
    call = Mock(side_effect=ResearchBaseError(code, "sanitized"))
    monkeypatch.setattr(service, once, call)
    with pytest.raises(ResearchBaseError) as caught:
        invoke(principal, cmd)
    assert caught.value.code == code
    assert call.call_count == (3 if code == ErrorCode.CONCURRENT_MODIFICATION else 1)


def test_composite_collision_rolls_back_then_reloads_outside_serialization_retry(monkeypatch):
    from unittest.mock import Mock

    from researchbase.application.revision_action import RevisionActionService
    from researchbase.domain.phase2_identity import VerifiedPrincipal

    service = RevisionActionService(cast(Any, lambda: None), None, None)
    saved = object()
    once = Mock(
        side_effect=[
            ResearchBaseError(ErrorCode.IDEMPOTENCY_CONFLICT, "reload concern correspondence"),
            saved,
        ]
    )
    monkeypatch.setattr(service, "_record_correspondence_once", once)
    assert (
        service.record_concern_re_review(
            Mock(spec=VerifiedPrincipal), RecordConcernReReviewCommand(uuid4(), uuid4(), uuid4())
        )
        is saved
    )
    assert once.call_count == 2
