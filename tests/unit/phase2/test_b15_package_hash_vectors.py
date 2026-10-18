"""Independent literal R2 preimages, identity-only consent and occurrences."""

import hashlib
import json
from uuid import UUID

from researchbase.domain.authorship import ExactReference
from researchbase.domain.prepared_submission import (
    ManifestItemReadback,
    consent_material,
    manifest_material,
    project_occurrences,
)
from researchbase.foundation.canonical_json import canonical_json_bytes
from researchbase.foundation.hashing import sha256_canonical_json


def ref(kind, number, digest):
    return ExactReference(kind, UUID(int=number), digest * 64)


def test_literal_consent_preimage():
    material = consent_material(UUID(int=1), UUID(int=2), ref("ArtifactVersion", 3, "a"))
    expected = {
        "type": "AuthorConsent",
        "material_version": 1,
        "prepared_submission": {"type": "PreparedSubmissionVersion", "id": str(UUID(int=1))},
        "actor": {"type": "ActorIdentity", "id": str(UUID(int=2))},
        "consent_state": "GRANTED",
        "consent_scope": "PREPARED_PACKAGE",
        "evidence_artifact": {
            "type": "ArtifactVersion",
            "id": str(UUID(int=3)),
            "content_hash": "a" * 64,
        },
        "prior_consent": None,
    }
    preimage = json.dumps(
        expected, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    assert canonical_json_bytes(material) == preimage
    assert str(sha256_canonical_json(material)) == hashlib.sha256(preimage).hexdigest()
    assert "captured_at" not in material and "content_hash" not in material["prepared_submission"]


def test_manifest_vector_and_lexical_occurrences():
    artifact = ref("ArtifactVersion", 3, "a")
    projected = project_occurrences(
        [
            ("FIGURE", "é", 0, artifact),
            ("FIGURE", "Z", 1, artifact),
            ("FIGURE", "Z", 0, artifact),
            ("CITATION", "A", 0, ref("SourceVersion", 4, "b")),
        ],
        1,
    )
    assert [p[0:2] for p in projected] == [
        ("CITATION", 0),
        ("FIGURE", 0),
        ("FIGURE", 1),
        ("FIGURE", 2),
    ]
    items = tuple(ManifestItemReadback(UUID(int=10 + i), *p) for i, p in enumerate(projected))
    manuscript, snapshot = ref("ManuscriptVersion", 5, "c"), ref("AuthorshipSnapshot", 6, "d")
    payload = manifest_material(manuscript, snapshot, items)
    expected = {
        "type": "PreparedSubmissionVersionManifest",
        "material_version": 1,
        "manuscript_version": {
            "type": "ManuscriptVersion",
            "id": str(UUID(int=5)),
            "content_hash": "c" * 64,
        },
        "authorship_snapshot": {
            "type": "AuthorshipSnapshot",
            "id": str(UUID(int=6)),
            "content_hash": "d" * 64,
        },
        "items": [
            {
                "category": p[0],
                "ordinal": p[1],
                "target": {
                    "type": p[2].type,
                    "id": str(p[2].id),
                    "content_hash": p[2].content_hash,
                },
            }
            for p in projected
        ],
    }
    assert payload == expected
    assert (
        str(sha256_canonical_json(payload))
        == hashlib.sha256(
            json.dumps(expected, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
    )
    changed_ids = tuple(
        ManifestItemReadback(UUID(int=100 + i), item.category, item.ordinal, item.target)
        for i, item in enumerate(items)
    )
    assert manifest_material(manuscript, snapshot, changed_ids) == payload
