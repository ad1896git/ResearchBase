"""Closed B10 admission bounds and unchanged literal R2 builders."""

from dataclasses import FrozenInstanceError, replace
from typing import Any, cast
from uuid import UUID

import pytest

from researchbase.application.decision import RecordRejectionReconsiderationCommand
from researchbase.domain.decision import (
    DecisionBasisReference,
    conclusion_material_changed,
    decision_basis_material,
    decision_content_material,
    reconsideration_question,
    reconsideration_text,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import sha256_canonical_json


def command(**changes):
    return replace(
        RecordRejectionReconsiderationCommand(
            UUID(int=1),
            UUID(int=2),
            UUID(int=3),
            "INTERNAL_SCIENTIFIC_RELEASE",
            "CORRECTED_REVIEW",
            (UUID(int=4),),
            (UUID(int=5),),
            "Evidence correction",
            corrected_review_ids=(UUID(int=6),),
        ),
        **changes,
    )


def test_closed_immutable_normalized_command():
    result = command(rationale="Cafe\u0301\n")
    assert result.rationale == "Café\n"
    assert not hasattr(result, "__dict__")
    with pytest.raises(FrozenInstanceError):
        cast(Any, result).rationale = "changed"
    with pytest.raises(TypeError):
        cast(Any, RecordRejectionReconsiderationCommand)(actor_id=UUID(int=1))


@pytest.mark.parametrize(
    "changes",
    [
        {"id": True},
        {"project_id": str(UUID(int=2))},
        {"decision": "PROCEED"},
        {"approval_purpose": "READY_FOR_SUBMISSION"},
        {"fresh_review_ids": []},
        {"fresh_review_ids": ()},
        {"rejected_approval_decision_ids": ()},
        {"corrected_review_ids": ()},
        {"revision_action_ids": (UUID(int=7),)},
        {"fresh_review_ids": (UUID(int=5), UUID(int=5))},
        {"rationale": " "},
        {"rationale": "\x00"},
        {"rationale": "\ud800"},
        {"rationale": "a" * 16385},
        {"rationale": True},
        {"decision": "REVISED_TARGET"},
    ],
)
def test_invalid_closed_material(changes):
    with pytest.raises(ResearchBaseError) as denied:
        command(**changes)
    assert denied.value.code is ErrorCode.VALIDATION_ERROR


@pytest.mark.parametrize(
    "field",
    [
        "rejected_approval_decision_ids",
        "fresh_review_ids",
        "corrected_review_ids",
        "revision_action_ids",
    ],
)
def test_collection_boundary(field):
    changes: dict[str, Any] = {field: tuple(UUID(int=i) for i in range(100, 200))}
    if field == "revision_action_ids":
        changes.update(decision="REVISED_TARGET", corrected_review_ids=())
    assert len(getattr(command(**changes), field)) == 100
    changes[field] += (UUID(int=200),)
    with pytest.raises(ResearchBaseError):
        command(**changes)


def test_text_exact_boundary_preserves_meaningful_whitespace():
    assert len(command(rationale="a" * 16384).rationale) == 16384
    assert reconsideration_text("  explanation\n") == "  explanation\n"


@pytest.mark.parametrize(
    "field", ["id", "support_set_hash", "version_number", "scientific_conclusion_id"]
)
def test_identity_and_support_alone_do_not_admit_revision(field):
    old = dict(
        statement="Café result",
        scope={"population": "all people"},
        confidence="MODERATE",
        limitation_summary=None,
    )
    new = {**old, field: "different"}
    assert not conclusion_material_changed(old, new)
    assert not conclusion_material_changed(old, {**new, "statement": "Cafe\u0301  result\n"})
    assert conclusion_material_changed(old, {**new, "statement": "Different scientific result"})


def test_literal_question_basis_and_hash():
    refs = tuple(
        DecisionBasisReference(kind, UUID(int=i), "a" * 64, n)
        for n, (kind, i) in enumerate(
            [
                ("ApprovalDecision", 4),
                ("InternalReviewRecord", 5),
                ("InternalReviewRecord", 6),
                ("ScientificConclusionVersion", 3),
            ]
        )
    )
    basis = decision_basis_material(refs)
    digest = str(sha256_canonical_json(basis))
    material = decision_content_material(
        UUID(int=2),
        "RECONSIDER_REJECTION",
        reconsideration_question("INTERNAL_SCIENTIFIC_RELEASE"),
        "CORRECTED_REVIEW",
        "Evidence correction",
        UUID(int=7),
        digest,
    )
    assert material["question"] == "Reconsider rejection for INTERNAL_SCIENTIFIC_RELEASE"
    assert material["decision"] == "CORRECTED_REVIEW"
    assert material["supersedes_decision_id"] is None
    assert (
        str(sha256_canonical_json(material))
        == "cb3f6cdd6913a9c35330aca341c8a41de74a9385dce0fd5a2de430cd732fcee9"
    )


@pytest.mark.parametrize(
    "value",
    [str(UUID(int=1)), f"{UUID(int=1)} {UUID(int=2)}", "Approve", "ACCEPT", "Recommend reject"],
)
def test_uuid_or_recommendation_only_is_not_an_explanation(value):
    from researchbase.domain.decision import correction_explanation

    assert not correction_explanation(value)


@pytest.mark.parametrize(
    "message,attempts",
    [
        ("decision transaction rejected", 3),
        ("database wait timed out", 1),
    ],
)
def test_retry_only_known_whole_transaction_conflict(monkeypatch, message, attempts):
    from researchbase.application.decision import DecisionService

    service = DecisionService(cast(Any, lambda: None), None, None)
    calls = []
    monkeypatch.setattr(service, "_reconsideration_read", lambda *args: None)

    def fail(*args):
        calls.append(1)
        raise ResearchBaseError(ErrorCode.CONCURRENT_MODIFICATION, message)

    monkeypatch.setattr(service, "_record_reconsideration_once", fail)
    from researchbase.domain.phase2_identity import VerifiedPrincipal

    # Reuse a real closed verified-principal fixture shape; no credential is consulted here.
    principal = object.__new__(VerifiedPrincipal)
    with pytest.raises(ResearchBaseError):
        service.record_rejection_reconsideration(command(), principal)
    assert len(calls) == attempts
