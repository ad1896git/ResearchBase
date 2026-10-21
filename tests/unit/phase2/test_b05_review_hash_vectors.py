"""Literal R2 review digest and preserved Claim/Conclusion material."""

from typing import Any
from uuid import UUID

import pytest

from researchbase.application.internal_review import InternalReviewService
from researchbase.domain.internal_review import _RECOMMENDATIONS, _TYPES, review_material
from researchbase.foundation.hashing import sha256_canonical_json


def values() -> list[Any]:
    return [
        UUID(int=16),
        "ManuscriptVersion",
        UUID(int=7),
        "b" * 64,
        UUID(int=17),
        "SCIENTIFIC",
        "ACCEPT",
        "Ready.",
    ]


def test_literal_manuscript_review_vector():
    assert (
        InternalReviewService._hash(*values())
        == "f974d3fad6625fe231671f5f485cc7a6ef8dc7926beba71259813fb75d3de704"
    )
    material = review_material(*values())
    assert not {"issues", "created_at", "status"} & material.keys()


@pytest.mark.parametrize(
    "index,value",
    [
        (0, UUID(int=20)),
        (1, "ClaimVersion"),
        (2, UUID(int=8)),
        (3, "a" * 64),
        (4, UUID(int=18)),
        (5, "EDITORIAL"),
        (6, "REJECT"),
        (7, "Different."),
    ],
)
def test_every_material_field_changes_hash(index, value):
    args = values()
    original = InternalReviewService._hash(*args)
    args[index] = value
    assert InternalReviewService._hash(*args) != original


@pytest.mark.parametrize("kind", ["ClaimVersion", "ScientificConclusionVersion"])
def test_accepted_legacy_payload_unchanged(kind):
    args = values()
    args[1] = kind
    expected = {
        "type": "InternalReviewRecord",
        "material_version": 1,
        "project_id": str(args[0]),
        "target": {"type": kind, "id": str(args[2]), "content_hash": args[3]},
        "reviewer_actor_id": str(args[4]),
        "review_type": "SCIENTIFIC",
        "recommendation": "ACCEPT",
        "summary": "Ready.",
    }
    assert InternalReviewService._hash(*args) == str(sha256_canonical_json(expected))


@pytest.mark.parametrize("review_type", sorted(_TYPES))
@pytest.mark.parametrize("recommendation", sorted(_RECOMMENDATIONS))
def test_no_favorable_hash_filter(review_type, recommendation):
    args = values()
    args[5:7] = [review_type, recommendation]
    assert len(InternalReviewService._hash(*args)) == 64
