"""Pure immutable review material and bounded assessment vocabulary."""

import unicodedata
from uuid import UUID

from researchbase.domain.scientific_conclusion import _digest, _uuid

_TYPES = frozenset(
    {"SCIENTIFIC", "STATISTICAL", "LITERATURE", "REPRODUCIBILITY", "EDITORIAL", "COMPREHENSIVE"}
)
_RECOMMENDATIONS = frozenset({"ACCEPT", "MINOR_REVISION", "MAJOR_REVISION", "REJECT", "UNCERTAIN"})
_SEVERITIES = frozenset({"INFO", "MINOR", "MAJOR", "BLOCKING"})
_ISSUE_TYPES = frozenset(
    {
        "UNSUPPORTED_CLAIM",
        "CITATION",
        "STATISTICAL",
        "METHODOLOGICAL",
        "REPRODUCIBILITY",
        "OVERCLAIM",
        "CONTRADICTION",
        "NOVELTY",
        "WRITING",
        "OTHER",
    }
)


def _text(value: str, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be text")
    result = unicodedata.normalize("NFC", value)
    if not result.strip() or len(result) > 16000:
        raise ValueError(f"{label} must be nonblank and bounded")
    try:
        result.encode("utf-8", "strict")
    except UnicodeError:
        raise ValueError(f"{label} contains invalid Unicode") from None
    return result


def review_material(
    project: UUID,
    target_kind: str,
    target_id: UUID,
    digest: str,
    actor: UUID,
    review_type: str,
    recommendation: str,
    summary: str,
) -> dict:
    for value in (project, target_id, actor):
        _uuid(value, "review reference")
    _digest(digest, "target hash")
    if target_kind not in {"ClaimVersion", "ScientificConclusionVersion", "ManuscriptVersion"}:
        raise ValueError("unsupported review target")
    if type(review_type) is not str or review_type not in _TYPES:
        raise ValueError("invalid review type")
    if type(recommendation) is not str or recommendation not in _RECOMMENDATIONS:
        raise ValueError("invalid review recommendation")
    return {
        "type": "InternalReviewRecord",
        "material_version": 1,
        "project_id": str(project),
        "target": {"type": target_kind, "id": str(target_id), "content_hash": digest},
        "reviewer_actor_id": str(actor),
        "review_type": review_type,
        "recommendation": recommendation,
        "summary": _text(summary, "review summary"),
    }


_DISPOSITIONS = frozenset({"ADDRESSED", "DISMISSED"})
_CHANGED_ACTIONS = frozenset(
    {"NEW_EXPERIMENT", "ANALYSIS_CHANGE", "CLAIM_CHANGE", "CONCLUSION_CHANGE", "SOURCE_CHANGE"}
)


def disposition_policy(
    disposition: str,
    severity: str,
    role: str,
    *,
    opener: bool,
    action_type: str,
    decision: str | None,
) -> bool:
    """Finite authority/basis policy; scientific closure is checked separately."""
    if (
        type(disposition) is not str
        or disposition not in _DISPOSITIONS
        or type(severity) is not str
        or severity not in _SEVERITIES
    ):
        return False
    if disposition == "DISMISSED":
        return role == "OWNER" and action_type == "NO_CHANGE" and decision == "ACCEPT_NO_CHANGE"
    return (
        (role == "OWNER" or (opener and role == "REVIEWER"))
        and action_type in _CHANGED_ACTIONS
        and (decision == "REQUIRE_CHANGE" or (decision is None and severity != "BLOCKING"))
    )
