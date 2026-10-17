"""Literal R2 DecisionRecord material; no policy or persistence ownership."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from researchbase.domain.scientific_conclusion import _digest, _text, _uuid

_BASIS_TYPES = frozenset(
    {
        "ClaimVersion",
        "ScientificConclusionVersion",
        "ManuscriptVersion",
        "InternalReviewRecord",
        "ApprovalDecision",
        "RevisionAction",
    }
)


@dataclass(frozen=True, slots=True)
class DecisionBasisReference:
    type: str
    id: UUID
    content_hash: str
    ordinal: int

    def __post_init__(self) -> None:
        if self.type not in _BASIS_TYPES:
            raise ValueError("unsupported typed decision basis")
        _uuid(self.id, "basis ID")
        _digest(self.content_hash, "basis hash")
        if type(self.ordinal) is not int or self.ordinal < 0:
            raise ValueError("basis ordinal must be nonnegative integer")


def decision_basis_material(basis: tuple[DecisionBasisReference, ...]) -> dict[str, object]:
    if (
        not isinstance(basis, tuple)
        or not basis
        or any(not isinstance(row, DecisionBasisReference) for row in basis)
    ):
        raise ValueError("nonempty typed basis tuple required")
    ordered = sorted(basis, key=lambda row: (row.type, str(row.id), row.content_hash))
    if [row.ordinal for row in ordered] != list(range(len(ordered))):
        raise ValueError("canonical basis ordinals required")
    if len({(row.type, row.id) for row in ordered}) != len(ordered):
        raise ValueError("duplicate basis target")
    return {
        "type": "DecisionRecordBasisSet",
        "material_version": 1,
        "basis": [
            {
                "target": {"type": row.type, "id": str(row.id), "content_hash": row.content_hash},
                "ordinal": row.ordinal,
            }
            for row in ordered
        ],
    }


def decision_content_material(
    project_id: UUID,
    decision_type: str,
    question: str,
    decision: str,
    rationale: str,
    decided_by: UUID,
    basis_set_hash: str,
) -> dict[str, object]:
    _uuid(project_id, "project")
    _uuid(decided_by, "deciding actor")
    return {
        "type": "DecisionRecord",
        "material_version": 1,
        "project_id": str(project_id),
        "decision_type": _text(decision_type, "purpose"),
        "question": _text(question, "question"),
        "decision": _text(decision, "decision"),
        "rationale": _text(rationale, "rationale"),
        "decided_by": {"type": "ActorIdentity", "id": str(decided_by)},
        "supersedes_decision_id": None,
        "basis_set_hash": _digest(basis_set_hash, "basis hash"),
    }


RevisionChoice = Literal["REQUIRE_CHANGE", "ACCEPT_NO_CHANGE"]
RevisionPurpose = Literal["REVISION_RESPONSE"]

REVISION_CHOICES = frozenset({"REQUIRE_CHANGE", "ACCEPT_NO_CHANGE"})


def revision_decision_text(value: str, name: str) -> str:
    normalized = _text(value, name)
    if len(normalized) > 16_000:
        raise ValueError(f"{name} exceeds 16000 characters")
    return normalized


def validate_revision_choice(purpose: str, choice: str, action: str | None = None) -> None:
    if purpose != "REVISION_RESPONSE" or choice not in REVISION_CHOICES:
        raise ValueError("revision response Decision required")
    if action is not None and (
        (choice == "ACCEPT_NO_CHANGE" and action != "NO_CHANGE")
        or (
            choice == "REQUIRE_CHANGE"
            and action
            not in {
                "NEW_EXPERIMENT",
                "ANALYSIS_CHANGE",
                "CLAIM_CHANGE",
                "CONCLUSION_CHANGE",
                "SOURCE_CHANGE",
            }
        )
    ):
        raise ValueError("Decision choice and completed action disagree")


ReadinessPurpose = Literal["READY_FOR_SUBMISSION"]
ReadinessChoice = Literal["PROCEED"]


def validate_readiness_choice(purpose: str, choice: str) -> None:
    if (
        type(purpose) is not str
        or type(choice) is not str
        or purpose != "READY_FOR_SUBMISSION"
        or choice != "PROCEED"
    ):
        raise ValueError("READY_FOR_SUBMISSION/PROCEED required")


def readiness_text(value: str, name: str) -> str:
    return revision_decision_text(value, name)


def validate_readiness_review_count(count: int) -> None:
    if type(count) is not int or not 1 <= count <= 10_000:
        raise ValueError("complete set of 1..10000 manuscript reviews required")
