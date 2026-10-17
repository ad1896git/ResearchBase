"""Finite Basic Approval material; approval authorizes without executing effects."""

from datetime import datetime
from uuid import UUID

from researchbase.domain.scientific_conclusion import _digest, _text, _uuid
from researchbase.foundation.time import to_utc

PURPOSE = "INTERNAL_SCIENTIFIC_RELEASE"
ALLOWED_COMMAND = "record_internal_scientific_release"
TUPLES = {
    PURPOSE: ("ScientificConclusionVersion", ALLOWED_COMMAND),
    "READY_FOR_SUBMISSION": ("ManuscriptVersion", "transition_publication_ready"),
    "PREPARE_SUBMISSION": ("ManuscriptVersion", "freeze_prepared_submission"),
}


def approval_tuple(purpose: str, conclusion: UUID | None, manuscript: UUID | None):
    if (
        type(purpose) is not str
        or (conclusion is None) == (manuscript is None)
        or any(x is not None and type(x) is not UUID for x in (conclusion, manuscript))
    ):
        raise ValueError("exact typed target XOR required")
    target_type = "ScientificConclusionVersion" if conclusion is not None else "ManuscriptVersion"
    if purpose not in TUPLES or TUPLES[purpose][0] != target_type:
        raise ValueError("unlisted approval tuple")
    return TUPLES[purpose]


OUTCOMES = frozenset({"APPROVE", "APPROVE_WITH_CONDITIONS", "REJECT"})


def approval_decision_material(
    request_id: UUID,
    target_id: UUID,
    target_hash: str,
    decision: str,
    valid_until: datetime | None,
    requires_current_author_consent: bool,
    rationale: str,
    decided_by: UUID,
    *,
    target_type: str = "ScientificConclusionVersion",
) -> dict[str, object]:
    for value in (request_id, target_id, decided_by):
        _uuid(value, "exact identity")
    if (
        decision not in OUTCOMES
        or target_type not in {"ScientificConclusionVersion", "ManuscriptVersion"}
        or type(requires_current_author_consent) is not bool
    ):
        raise ValueError("typed approval material required")
    return {
        "type": "ApprovalDecision",
        "material_version": 1,
        "approval_request_id": str(request_id),
        "target": {
            "type": target_type,
            "id": str(target_id),
            "content_hash": _digest(target_hash, "target hash"),
        },
        "decision": decision,
        "valid_until": None
        if valid_until is None
        else to_utc(valid_until).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "requires_current_author_consent": requires_current_author_consent,
        "rationale": _text(rationale, "rationale"),
        "decided_by": {"type": "ActorIdentity", "id": str(decided_by)},
    }
