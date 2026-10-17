"""Independently literal R2 JSON: readiness adds no hash fields/version."""

# SQL and independent literal hash vectors preserve contract spelling.
# ruff: noqa: E501

import hashlib
import json
from uuid import UUID

from researchbase.domain.decision import (
    DecisionBasisReference,
    decision_basis_material,
    decision_content_material,
)
from researchbase.foundation.hashing import sha256_canonical_json


def test_literal_basis_and_content_vectors():
    review = "00000000-0000-0000-0000-000000000001"
    target = "00000000-0000-0000-0000-000000000002"
    project = "00000000-0000-0000-0000-000000000003"
    actor = "00000000-0000-0000-0000-000000000004"
    literal = (
        '{"basis":[{"ordinal":0,"target":{"content_hash":"'
        + ("a" * 64)
        + '","id":"'
        + review
        + '","type":"InternalReviewRecord"}},{"ordinal":1,"target":{"content_hash":"'
        + ("b" * 64)
        + '","id":"'
        + target
        + '","type":"ManuscriptVersion"}}],"material_version":1,"type":"DecisionRecordBasisSet"}'
    )
    expected = hashlib.sha256(literal.encode()).hexdigest()
    refs = (
        DecisionBasisReference("ManuscriptVersion", UUID(target), "b" * 64, 1),
        DecisionBasisReference("InternalReviewRecord", UUID(review), "a" * 64, 0),
    )
    material = decision_basis_material(refs)
    assert material == json.loads(literal)
    assert str(sha256_canonical_json(material)) == expected
    content = (
        '{"basis_set_hash":"'
        + expected
        + '","decided_by":{"id":"'
        + actor
        + '","type":"ActorIdentity"},"decision":"PROCEED","decision_type":"READY_FOR_SUBMISSION","material_version":1,"project_id":"'
        + project
        + '","question":"Ready?","rationale":"Judgment","supersedes_decision_id":null,"type":"DecisionRecord"}'
    )
    actual = decision_content_material(
        UUID(project),
        "READY_FOR_SUBMISSION",
        "Ready?",
        "PROCEED",
        "Judgment",
        UUID(actor),
        expected,
    )
    assert actual == json.loads(content)
    assert str(sha256_canonical_json(actual)) == hashlib.sha256(content.encode()).hexdigest()
    for changed in (dict(actual, rationale="Other"), dict(actual, basis_set_hash="c" * 64)):
        assert sha256_canonical_json(changed) != sha256_canonical_json(actual)


def test_multiple_adverse_review_hashes_keep_uuid_order():
    refs = tuple(
        DecisionBasisReference("InternalReviewRecord", UUID(int=i), str(i) * 64, i - 1)
        for i in (1, 2, 3)
    ) + (DecisionBasisReference("ManuscriptVersion", UUID(int=4), "a" * 64, 3),)
    expected = {
        "type": "DecisionRecordBasisSet",
        "material_version": 1,
        "basis": [
            {
                "target": {
                    "type": "InternalReviewRecord",
                    "id": f"00000000-0000-0000-0000-{i:012d}",
                    "content_hash": str(i) * 64,
                },
                "ordinal": i - 1,
            }
            for i in (1, 2, 3)
        ]
        + [
            {
                "target": {
                    "type": "ManuscriptVersion",
                    "id": "00000000-0000-0000-0000-000000000004",
                    "content_hash": "a" * 64,
                },
                "ordinal": 3,
            }
        ],
    }
    assert decision_basis_material(tuple(reversed(refs))) == expected
    digest = hashlib.sha256(
        json.dumps(expected, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert str(sha256_canonical_json(decision_basis_material(refs))) == digest
