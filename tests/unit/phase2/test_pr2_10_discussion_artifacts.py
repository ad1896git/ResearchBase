"""Offline, test-only discussion snapshots; no canonical or human records."""

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import uuid4

import pytest

from researchbase.application.discussion_artifacts import (
    ClosedDiscussionSnapshot,
    DiscussionTurnSnapshot,
    build_discussion_artifact_candidates,
)


def _snapshot():
    session_id, project_id = uuid4(), uuid4()
    source_id, claim_id = uuid4(), uuid4()
    created = datetime(2026, 1, 1, tzinfo=UTC)
    turns = (
        DiscussionTurnSnapshot(
            uuid4(), session_id, 1, uuid4(), "moderator", "What does the source show?",
            (source_id,), (), created,
        ),
        DiscussionTurnSnapshot(
            uuid4(), session_id, 2, uuid4(), "domain_critic", "Claim needs checking.",
            (), (claim_id,), created + timedelta(minutes=1),
        ),
    )
    return ClosedDiscussionSnapshot(
        session_id, project_id, "Test-only topic", "CLOSED", uuid4(), created,
        created + timedelta(minutes=2), (source_id,), (claim_id,), turns,
    )


def test_exact_deterministic_transcript_and_mechanical_concept_map():
    snapshot = replace(_snapshot(), research_question_version_ids=(uuid4(),))
    first = build_discussion_artifact_candidates(snapshot)
    assert first == build_discussion_artifact_candidates(snapshot)
    assert [item.artifact_type for item in first] == [
        "discussion_transcript", "concept_map"
    ]
    for item in first:
        assert item.media_type == "application/json"
        assert item.content_hash == sha256(item.content).hexdigest()
        assert item.session_id == snapshot.session_id
        assert item.project_id == snapshot.project_id
    transcript = json.loads(first[0].content)
    graph = json.loads(first[1].content)
    assert [turn["ordinal"] for turn in transcript["turns"]] == [1, 2]
    assert transcript["turns"][0]["utterance"] == "What does the source show?"
    assert transcript["turns"][1]["actor_id"] == str(snapshot.turns[1].actor_id)
    assert transcript["turns"][0]["cited_source_version_ids"] == [
        str(snapshot.source_version_ids[0])
    ]
    assert transcript["input_research_question_version_ids"] == [
        str(snapshot.research_question_version_ids[0])
    ]
    assert graph["derived_only"] is True
    assert graph["edges"] == [
        {"turn_id": str(snapshot.turns[0].id), "kind": "cites_source_version",
         "version_id": str(snapshot.source_version_ids[0])},
        {"turn_id": str(snapshot.turns[1].id), "kind": "cites_claim_version",
         "version_id": str(snapshot.claim_version_ids[0])},
    ]
    assert "decision" not in graph
    assert "promoted" not in graph


@pytest.mark.parametrize("change", ["OPEN", "ARCHIVED"])
def test_only_closed_sessions_can_yield_candidates(change):
    with pytest.raises(ValueError, match="closed"):
        build_discussion_artifact_candidates(replace(_snapshot(), status=change))


@pytest.mark.parametrize("ordinal", [0, 1, 3])
def test_out_of_order_or_duplicate_turns_fail_closed(ordinal):
    snapshot = _snapshot()
    turns = (snapshot.turns[0], replace(snapshot.turns[1], ordinal=ordinal))
    with pytest.raises(ValueError, match="ordinal"):
        build_discussion_artifact_candidates(replace(snapshot, turns=turns))


def test_cross_session_and_unknown_citation_fail_closed():
    snapshot = _snapshot()
    for altered in (
        replace(snapshot.turns[0], session_id=uuid4()),
        replace(snapshot.turns[0], cited_source_version_ids=(uuid4(),)),
        replace(snapshot.turns[0], cited_claim_version_ids=(uuid4(),)),
    ):
        with pytest.raises(ValueError, match="session|citation"):
            build_discussion_artifact_candidates(
                replace(snapshot, turns=(altered, snapshot.turns[1]))
            )


def test_turns_must_precede_close_and_have_unique_identity():
    snapshot = _snapshot()
    for altered in (
        replace(snapshot.turns[1], created_at=snapshot.closed_at + timedelta(seconds=1)),
        replace(snapshot.turns[1], id=snapshot.turns[0].id),
    ):
        with pytest.raises(ValueError, match="time|unique"):
            build_discussion_artifact_candidates(
                replace(snapshot, turns=(snapshot.turns[0], altered))
            )


def test_invalid_role_reference_shape_and_naive_time_fail_closed():
    snapshot = _snapshot()
    for altered in (
        replace(snapshot.turns[0], role="decision"),
        replace(snapshot.turns[0], cited_source_version_ids=[snapshot.source_version_ids[0]]),
        replace(snapshot.turns[0], created_at=datetime(2026, 1, 1)),
    ):
        with pytest.raises((ValueError, TypeError)):
            build_discussion_artifact_candidates(
                replace(snapshot, turns=(altered, snapshot.turns[1]))
            )


def test_empty_and_duplicate_input_references_fail_closed():
    snapshot = _snapshot()
    for changed in (
        replace(snapshot, turns=()),
        replace(snapshot, source_version_ids=snapshot.source_version_ids * 2),
        replace(snapshot, research_question_version_ids=(uuid4(),) * 2),
    ):
        with pytest.raises(ValueError):
            build_discussion_artifact_candidates(changed)
