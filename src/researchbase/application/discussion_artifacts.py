"""Deterministic derived candidates from trusted, closed discussion snapshots.

The caller must obtain the snapshot and reference sets through authorized
Application reads. This module neither authenticates turns nor promotes them.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from researchbase.foundation.canonical_json import canonical_json_bytes
from researchbase.foundation.hashing import ContentHash, sha256_bytes
from researchbase.foundation.time import format_utc, to_utc

_ROLES = frozenset(
    {
        "human",
        "moderator",
        "literature_expert",
        "method_expert",
        "statistician",
        "domain_critic",
        "other",
    }
)


@dataclass(frozen=True, slots=True)
class DiscussionTurnSnapshot:
    id: UUID
    session_id: UUID
    ordinal: int
    actor_id: UUID
    role: str
    utterance: str
    cited_source_version_ids: tuple[UUID, ...]
    cited_claim_version_ids: tuple[UUID, ...]
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ClosedDiscussionSnapshot:
    session_id: UUID
    project_id: UUID
    topic: str
    status: str
    created_by: UUID
    created_at: datetime
    closed_at: datetime
    source_version_ids: tuple[UUID, ...]
    claim_version_ids: tuple[UUID, ...]
    turns: tuple[DiscussionTurnSnapshot, ...]
    research_question_version_ids: tuple[UUID, ...] = ()


@dataclass(frozen=True, slots=True)
class DerivedDiscussionArtifactCandidate:
    artifact_type: str
    session_id: UUID
    project_id: UUID
    media_type: str
    content: bytes
    content_hash: ContentHash


def _uuid(value: object, name: str) -> None:
    if type(value) is not UUID:
        raise ValueError(f"{name} must be a UUID")


def _refs(values: object, name: str) -> tuple[UUID, ...]:
    if not isinstance(values, tuple) or any(type(value) is not UUID for value in values):
        raise ValueError(f"{name} must be a tuple of UUIDs")
    if len(set(values)) != len(values):
        raise ValueError(f"{name} must be unique")
    return values


def _validate(snapshot: ClosedDiscussionSnapshot) -> None:
    for name in ("session_id", "project_id", "created_by"):
        _uuid(getattr(snapshot, name), name)
    if snapshot.status != "CLOSED":
        raise ValueError("discussion must be closed")
    if (
        not isinstance(snapshot.topic, str)
        or not snapshot.topic.strip()
        or len(snapshot.topic) > 255
    ):
        raise ValueError("topic must be bounded nonblank text")
    started, closed = to_utc(snapshot.created_at), to_utc(snapshot.closed_at)
    if closed < started:
        raise ValueError("close time precedes creation")
    sources = set(_refs(snapshot.source_version_ids, "source references"))
    claims = set(_refs(snapshot.claim_version_ids, "claim references"))
    _refs(snapshot.research_question_version_ids, "research question references")
    if not isinstance(snapshot.turns, tuple) or not snapshot.turns:
        raise ValueError("closed discussion requires turns")
    seen_turns: set[UUID] = set()
    previous_time = started
    for expected_ordinal, turn in enumerate(snapshot.turns, 1):
        if not isinstance(turn, DiscussionTurnSnapshot):
            raise ValueError("turn must be a DiscussionTurnSnapshot")
        for name in ("id", "session_id", "actor_id"):
            _uuid(getattr(turn, name), f"turn {name}")
        if turn.id in seen_turns:
            raise ValueError("turn identity must be unique")
        seen_turns.add(turn.id)
        if turn.session_id != snapshot.session_id:
            raise ValueError("turn belongs to another session")
        if type(turn.ordinal) is not int or turn.ordinal != expected_ordinal:
            raise ValueError("turn ordinal must be contiguous")
        if turn.role not in _ROLES:
            raise ValueError("turn role is invalid")
        if (
            not isinstance(turn.utterance, str)
            or not turn.utterance.strip()
            or len(turn.utterance) > 16_000
        ):
            raise ValueError("utterance must be bounded nonblank text")
        if not set(_refs(turn.cited_source_version_ids, "source citation")).issubset(sources):
            raise ValueError("source citation is outside discussion input refs")
        if not set(_refs(turn.cited_claim_version_ids, "claim citation")).issubset(claims):
            raise ValueError("claim citation is outside discussion input refs")
        at = to_utc(turn.created_at)
        if not previous_time <= at <= closed:
            raise ValueError("turn time is outside ordered session boundary")
        previous_time = at


def _candidate(
    snapshot: ClosedDiscussionSnapshot, artifact_type: str, payload: dict[str, object]
) -> DerivedDiscussionArtifactCandidate:
    content = canonical_json_bytes(payload)
    return DerivedDiscussionArtifactCandidate(
        artifact_type,
        snapshot.session_id,
        snapshot.project_id,
        "application/json",
        content,
        sha256_bytes(content),
    )


def build_discussion_artifact_candidates(
    snapshot: ClosedDiscussionSnapshot,
) -> tuple[DerivedDiscussionArtifactCandidate, DerivedDiscussionArtifactCandidate]:
    """Render exact-byte transcript and mechanical citation graph candidates."""
    _validate(snapshot)
    common: dict[str, object] = {
        "session_id": str(snapshot.session_id),
        "project_id": str(snapshot.project_id),
        "topic": snapshot.topic,
    }
    transcript = _candidate(
        snapshot,
        "discussion_transcript",
        common
        | {
            "artifact_role": "discussion_transcript",
            "created_by": str(snapshot.created_by),
            "created_at": format_utc(snapshot.created_at),
            "closed_at": format_utc(snapshot.closed_at),
            "input_source_version_ids": [str(value) for value in snapshot.source_version_ids],
            "input_claim_version_ids": [str(value) for value in snapshot.claim_version_ids],
            "input_research_question_version_ids": [
                str(value) for value in snapshot.research_question_version_ids
            ],
            "turns": [
                {
                    "id": str(turn.id),
                    "ordinal": turn.ordinal,
                    "actor_id": str(turn.actor_id),
                    "role": turn.role,
                    "utterance": turn.utterance,
                    "cited_source_version_ids": [
                        str(value) for value in turn.cited_source_version_ids
                    ],
                    "cited_claim_version_ids": [
                        str(value) for value in turn.cited_claim_version_ids
                    ],
                    "created_at": format_utc(turn.created_at),
                }
                for turn in snapshot.turns
            ],
        },
    )
    edges = [
        {"turn_id": str(turn.id), "kind": kind, "version_id": str(value)}
        for turn in snapshot.turns
        for kind, values in (
            ("cites_source_version", turn.cited_source_version_ids),
            ("cites_claim_version", turn.cited_claim_version_ids),
        )
        for value in values
    ]
    concept_map = _candidate(
        snapshot,
        "concept_map",
        common
        | {
            "artifact_role": "concept_map",
            "derived_only": True,
            "edges": edges,
        },
    )
    return transcript, concept_map
