"""Literal R2 ScientificConclusion canonical material, independent of persistence."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, cast
from uuid import UUID

_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_RELATIONS = frozenset({"SUPPORTS", "CONTRADICTS", "QUALIFIES"})
_CONFIDENCE = frozenset({"STRONG", "MODERATE", "WEAK", "INCONCLUSIVE", "MIXED"})
_SCOPE_KEYS = frozenset({"population", "conditions", "time_window", "applicability"})


def _uuid(value: UUID, label: str) -> UUID:
    if type(value) is not UUID:
        raise ValueError(f"{label} must be UUID")
    return value


def _digest(value: str, label: str) -> str:
    if not isinstance(value, str) or _DIGEST.fullmatch(value) is None:
        raise ValueError(f"{label} must be lowercase SHA-256")
    return value


def _text(value: str, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be text")
    result = unicodedata.normalize("NFC", value)
    try:
        result.encode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise ValueError(f"{label} has invalid Unicode") from exc
    if not result.strip():
        raise ValueError(f"{label} must be nonblank")
    return result


def _relation(value: str) -> str:
    if value not in _RELATIONS:
        raise ValueError("conclusion relation must be SUPPORTS, CONTRADICTS or QUALIFIES")
    return value


def _ordinal(value: int) -> int:
    if type(value) is not int or value < 0:
        raise ValueError("ordinal must be a nonnegative integer")
    return value


def _ref(kind: str, identity: UUID, digest: str) -> dict[str, str]:
    return {"type": kind, "id": str(identity), "content_hash": digest}


@dataclass(frozen=True, slots=True)
class ClaimConclusionInput:
    claim_version_id: UUID
    claim_content_hash: str
    relation_type: str
    ordinal: int
    literature_support_snapshot_id: UUID | None = None
    literature_support_snapshot_content_hash: str | None = None

    def __post_init__(self) -> None:
        _uuid(self.claim_version_id, "claim version")
        _digest(self.claim_content_hash, "claim content hash")
        _relation(self.relation_type)
        _ordinal(self.ordinal)
        if (self.literature_support_snapshot_id is None) != (
            self.literature_support_snapshot_content_hash is None
        ):
            raise ValueError("snapshot ID and digest must both be present or absent")
        if self.literature_support_snapshot_id is not None:
            _uuid(self.literature_support_snapshot_id, "snapshot")
            assert self.literature_support_snapshot_content_hash is not None
            _digest(self.literature_support_snapshot_content_hash, "snapshot content hash")


@dataclass(frozen=True, slots=True)
class LiteratureConclusionInput:
    literature_evidence_id: UUID
    literature_evidence_content_hash: str
    relation_type: str
    ordinal: int

    def __post_init__(self) -> None:
        _uuid(self.literature_evidence_id, "literature evidence")
        _digest(self.literature_evidence_content_hash, "literature content hash")
        _relation(self.relation_type)
        _ordinal(self.ordinal)


def _sorted_unique(rows: tuple[Any, ...], kind: str) -> tuple[Any, ...]:
    ordered = tuple(sorted(rows, key=lambda row: (row.ordinal, str(
        row.claim_version_id if kind == "claim" else row.literature_evidence_id
    ))))
    if [row.ordinal for row in ordered] != list(range(len(ordered))):
        raise ValueError(f"{kind} ordinals must be contiguous from zero")
    identities = [
        (row.claim_version_id if kind == "claim" else row.literature_evidence_id,
         row.relation_type)
        for row in ordered
    ]
    if len(set(identities)) != len(identities):
        raise ValueError(f"duplicate {kind} target/relation")
    return ordered


def conclusion_support_material(
    claims: tuple[ClaimConclusionInput, ...],
    literature: tuple[LiteratureConclusionInput, ...],
) -> dict[str, object]:
    """Build the complete literal R2 support-set payload with exact refs."""
    if not isinstance(claims, tuple) or not all(
        isinstance(x, ClaimConclusionInput) for x in claims
    ):
        raise ValueError("claim inputs must be typed tuple")
    if not isinstance(literature, tuple) or not all(
        isinstance(x, LiteratureConclusionInput) for x in literature
    ):
        raise ValueError("literature inputs must be typed tuple")
    if not claims and not literature:
        raise ValueError("at least one conclusion input required")
    claims = _sorted_unique(claims, "claim")
    literature = _sorted_unique(literature, "literature")
    return {
        "type": "ScientificConclusionVersionSupportSet",
        "material_version": 1,
        "claim_inputs": [
            {
                "claim_version": _ref("ClaimVersion", x.claim_version_id, x.claim_content_hash),
                "literature_support_snapshot": (
                    _ref(
                        "LiteratureSupportSnapshot",
                        x.literature_support_snapshot_id,
                        cast(str, x.literature_support_snapshot_content_hash),
                    )
                    if x.literature_support_snapshot_id is not None
                    else None
                ),
                "relation_type": x.relation_type,
                "ordinal": x.ordinal,
            }
            for x in claims
        ],
        "literature_inputs": [
            {
                "literature_evidence": _ref(
                    "LiteratureEvidence", x.literature_evidence_id,
                    x.literature_evidence_content_hash,
                ),
                "relation_type": x.relation_type,
                "ordinal": x.ordinal,
            }
            for x in literature
        ],
    }


def conclusion_content_material(
    scientific_conclusion_id: UUID,
    statement: str,
    scope: dict[str, str | None],
    confidence: str,
    limitation_summary: str | None,
    support_set_hash: str,
) -> dict[str, object]:
    """Build the complete literal R2 conclusion own-content payload."""
    _uuid(scientific_conclusion_id, "scientific conclusion")
    if not isinstance(scope, dict) or frozenset(scope) != _SCOPE_KEYS:
        raise ValueError("scope must contain exactly four R2 keys")
    normalized_scope = {
        key: _text(value, f"scope {key}") if value is not None else None
        for key, value in scope.items()
    }
    if confidence not in _CONFIDENCE:
        raise ValueError("confidence must be an uppercase R2 value")
    return {
        "type": "ScientificConclusionVersion",
        "material_version": 1,
        "scientific_conclusion_id": str(scientific_conclusion_id),
        "statement": _text(statement, "statement"),
        "scope": normalized_scope,
        "confidence": confidence,
        "limitation_summary": (
            _text(limitation_summary, "limitation summary")
            if limitation_summary is not None else None
        ),
        "support_set_hash": _digest(support_set_hash, "support set hash"),
    }
