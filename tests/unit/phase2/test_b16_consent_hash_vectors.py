"""Independent literal R2 material, prior binding and retained evidence vectors."""

import hashlib
import json
from uuid import UUID

import pytest

from researchbase.domain.authorship import ExactReference
from researchbase.domain.prepared_submission import consent_material
from researchbase.foundation.hashing import sha256_canonical_json


def independent(state, prior_hash=None):
    return {
        "type": "AuthorConsent",
        "material_version": 1,
        "prepared_submission": {
            "type": "PreparedSubmissionVersion",
            "id": "00000000-0000-0000-0000-000000000001",
        },
        "actor": {"type": "ActorIdentity", "id": "00000000-0000-0000-0000-000000000002"},
        "consent_state": state,
        "consent_scope": "PREPARED_PACKAGE",
        "evidence_artifact": {
            "type": "ArtifactVersion",
            "id": "00000000-0000-0000-0000-000000000003",
            "content_hash": "a" * 64,
        },
        "prior_consent": {
            "type": "AuthorConsent",
            "id": "00000000-0000-0000-0000-000000000004",
            "content_hash": prior_hash,
        }
        if prior_hash
        else None,
    }


@pytest.mark.parametrize(
    "state,prior_hash", [("GRANTED", None), ("WITHDRAWN", "b" * 64), ("GRANTED", "c" * 64)]
)
def test_literal_independent_vectors(state, prior_hash):
    prior = ExactReference("AuthorConsent", UUID(int=4), prior_hash) if prior_hash else None
    actual = consent_material(
        UUID(int=1),
        UUID(int=2),
        ExactReference("ArtifactVersion", UUID(int=3), "a" * 64),
        state,
        prior,
    )
    literal = independent(state, prior_hash)
    expected = hashlib.sha256(
        json.dumps(literal, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()
    assert actual == literal and str(sha256_canonical_json(actual)) == expected
    assert "captured_at" not in actual and "created_at" not in actual


def test_prior_and_unicode_evidence_are_exact_digest_material():
    material = independent("WITHDRAWN", "b" * 64)
    before = sha256_canonical_json(material)
    material["prior_consent"]["content_hash"] = "c" * 64
    assert sha256_canonical_json(material) != before
    material["evidence_artifact"]["content_hash"] = hashlib.sha256(
        "同意撤回 é".encode()
    ).hexdigest()
    assert sha256_canonical_json(material) != before
