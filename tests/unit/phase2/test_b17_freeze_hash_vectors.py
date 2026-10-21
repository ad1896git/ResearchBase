"""Independent literal R2 package vectors and R3 request preimages."""

import hashlib
import json
from typing import Any, cast
from uuid import UUID

from researchbase.domain.approval import consumption_request_material
from researchbase.domain.authorship import ExactReference
from researchbase.domain.prepared_submission import (
    ManifestItemReadback,
    manifest_material,
    package_material,
)
from researchbase.foundation.canonical_json import canonical_json_bytes
from researchbase.foundation.hashing import sha256_canonical_json


def ref(kind, n, letter):
    return ExactReference(kind, UUID(int=n), letter * 64)


def test_published_r2_vectors_remain_exact():
    manuscript, snapshot = ref("ManuscriptVersion", 7, "b"), ref("AuthorshipSnapshot", 8, "c")
    items = (ManifestItemReadback(UUID(int=20), "AUTHOR_CONSENT", 0, ref("AuthorConsent", 9, "d")),)
    manifest = manifest_material(manuscript, snapshot, items)
    digest = str(sha256_canonical_json(manifest))
    assert digest == "1378737bf5d07edff580a8b5e13f53e9f516df69738ec81688c2fff838d40d46"
    material = package_material(UUID(int=4), manuscript, snapshot, cast(Any, digest))
    assert (
        str(sha256_canonical_json(material))
        == "2ffff00e6620ddc0cf68c62fd54e18d8f1eb2099a640828d7f027101e5b2d32d"
    )
    assert set(material) == {
        "type",
        "material_version",
        "publication_id",
        "manuscript_version",
        "authorship_snapshot",
        "package_manifest_hash",
    }


def test_literal_r3_request_has_complete_sorted_set_and_manifest_binding():
    ids = [UUID(int=i) for i in range(1, 8)]
    material = consumption_request_material(
        ids[0],
        ids[1],
        ids[2],
        "FREEZE_PREPARED_SUBMISSION",
        "ManuscriptVersion",
        ids[3],
        "a" * 64,
        ids[4],
        "b" * 64,
        (ids[6], ids[5]),
    )
    expected = {
        "type": "ApprovalGrantConsumptionRequest",
        "material_version": 1,
        "command": "FREEZE_PREPARED_SUBMISSION",
        "project_id": str(ids[0]),
        "actor_id": str(ids[1]),
        "grant_id": str(ids[2]),
        "target": {"type": "ManuscriptVersion", "id": str(ids[3]), "content_hash": "a" * 64},
        "result_id": str(ids[4]),
        "expected_package_manifest_hash": "b" * 64,
        "checked_review_ids": [str(ids[5]), str(ids[6])],
    }
    preimage = json.dumps(
        expected, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    assert canonical_json_bytes(material) == preimage
    assert str(sha256_canonical_json(material)) == hashlib.sha256(preimage).hexdigest()


def test_consent_order_and_repeated_placements_are_material():
    manuscript, snapshot = ref("ManuscriptVersion", 7, "b"), ref("AuthorshipSnapshot", 8, "c")
    items = tuple(
        ManifestItemReadback(UUID(int=20 + i), "FIGURE", i, ref("ArtifactVersion", 9, "d"))
        for i in range(2)
    )
    once = manifest_material(manuscript, snapshot, items[:1])
    twice = manifest_material(manuscript, snapshot, items)
    assert sha256_canonical_json(once) != sha256_canonical_json(twice)
    assert sha256_canonical_json(twice) == sha256_canonical_json(
        manifest_material(manuscript, snapshot, items[::-1])
    )


def test_authored_consent_positions_bind_exact_ids_and_hashes():
    from dataclasses import replace

    manuscript, snapshot = ref("ManuscriptVersion", 7, "b"), ref("AuthorshipSnapshot", 8, "c")
    first = ManifestItemReadback(UUID(int=20), "AUTHOR_CONSENT", 0, ref("AuthorConsent", 9, "d"))
    second = ManifestItemReadback(UUID(int=21), "AUTHOR_CONSENT", 1, ref("AuthorConsent", 10, "e"))
    expected = sha256_canonical_json(manifest_material(manuscript, snapshot, (first, second)))
    # Input enumeration is irrelevant; authored category coordinates are material.
    assert expected == sha256_canonical_json(
        manifest_material(manuscript, snapshot, (second, first))
    )
    swapped = (replace(first, ordinal=1), replace(second, ordinal=0))
    assert expected != sha256_canonical_json(manifest_material(manuscript, snapshot, swapped))
    for altered in (ref("AuthorConsent", 11, "d"), ref("AuthorConsent", 9, "f")):
        assert expected != sha256_canonical_json(
            manifest_material(manuscript, snapshot, (replace(first, target=altered), second))
        )


def test_content_material_rejects_null_or_noncanonical_draft_manifest_hash():
    import pytest

    manuscript, snapshot = ref("ManuscriptVersion", 7, "b"), ref("AuthorshipSnapshot", 8, "c")
    for digest in (None, "A" * 64, "a" * 63, "g" * 64):
        with pytest.raises(ValueError):
            package_material(UUID(int=4), manuscript, snapshot, cast(Any, digest))
