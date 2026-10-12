"""Literal R2 ScientificConclusion vectors and fail-closed material rules."""

from __future__ import annotations

from uuid import UUID

import pytest

from researchbase.domain.scientific_conclusion import (
    ClaimConclusionInput,
    LiteratureConclusionInput,
    conclusion_content_material,
    conclusion_support_material,
)
from researchbase.foundation.canonical_json import canonical_json_bytes
from researchbase.foundation.hashing import sha256_canonical_json

CLAIM = UUID("00000000-0000-0000-0000-000000000002")
CONCLUSION = UUID("00000000-0000-0000-0000-000000000003")
EVIDENCE = UUID("00000000-0000-0000-0000-000000000016")
SNAPSHOT = UUID("00000000-0000-0000-0000-000000000017")
A = "a" * 64
F = "f" * 64
C = "c" * 64
SUPPORT_HASH = "24b43b7434ebcc6e8ba349d4f9313277c4eefd3832adeaca16882365d94f7953"
CONTENT_HASH = "eba7398741d3591ca30451a64536ffbb6d8b6039d9a459453e9af34f9e5f631f"


def claim_input(ordinal: int = 0, snapshot: UUID | None = None) -> ClaimConclusionInput:
    return ClaimConclusionInput(CLAIM, A, "SUPPORTS", ordinal, snapshot, C if snapshot else None)


def test_r2_support_golden_vector_exact_bytes_and_digest() -> None:
    material = conclusion_support_material((claim_input(),), ())
    expected = (
        b'{"claim_inputs":[{"claim_version":{"content_hash":"'
        + A.encode()
        + b'","id":"00000000-0000-0000-0000-000000000002","type":"ClaimVersion"},'
        b'"literature_support_snapshot":null,"ordinal":0,"relation_type":"SUPPORTS"}],'
        b'"literature_inputs":[],"material_version":1,"type":"ScientificConclusionVersionSupportSet"}'
    )
    assert canonical_json_bytes(material) == expected
    assert str(sha256_canonical_json(material)) == SUPPORT_HASH


def test_r2_content_golden_vector_exact_bytes_and_digest() -> None:
    material = conclusion_content_material(
        CONCLUSION,
        "Evidence supports the effect.",
        {"population": "Adults", "conditions": None, "time_window": None, "applicability": None},
        "MODERATE",
        None,
        SUPPORT_HASH,
    )
    expected = (
        b'{"confidence":"MODERATE","limitation_summary":null,"material_version":1,'
        b'"scientific_conclusion_id":"00000000-0000-0000-0000-000000000003",'
        b'"scope":{"applicability":null,"conditions":null,"population":"Adults",'
        b'"time_window":null},"statement":"Evidence supports the effect.",'
        b'"support_set_hash":"24b43b7434ebcc6e8ba349d4f9313277c4eefd3832adeaca16882365d94f7953",'
        b'"type":"ScientificConclusionVersion"}'
    )
    assert canonical_json_bytes(material) == expected
    assert str(sha256_canonical_json(material)) == CONTENT_HASH


def test_r2_accepts_claim_only_or_literature_only_but_rejects_empty() -> None:
    assert conclusion_support_material((claim_input(),), ())["literature_inputs"] == []
    literature = LiteratureConclusionInput(EVIDENCE, F, "CONTRADICTS", 0)
    assert conclusion_support_material((), (literature,))["claim_inputs"] == []
    with pytest.raises(ValueError, match="at least one"):
        conclusion_support_material((), ())


def test_r2_order_is_ordinal_not_insertion_order_and_gaps_reject() -> None:
    second = ClaimConclusionInput(UUID(int=4), "b" * 64, "QUALIFIES", 1)
    assert conclusion_support_material((second, claim_input()), ()) == (
        conclusion_support_material((claim_input(), second), ())
    )
    with pytest.raises(ValueError, match="contiguous"):
        conclusion_support_material((claim_input(1),), ())
    with pytest.raises(ValueError, match="duplicate"):
        conclusion_support_material((claim_input(), claim_input(1)), ())


def test_r2_snapshot_is_typed_hashed_reference_and_hash_sensitive() -> None:
    material = conclusion_support_material((claim_input(snapshot=SNAPSHOT),), ())
    assert material["claim_inputs"][0]["literature_support_snapshot"] == {
        "type": "LiteratureSupportSnapshot", "id": str(SNAPSHOT), "content_hash": C
    }
    assert str(sha256_canonical_json(material)) != SUPPORT_HASH
    with pytest.raises(ValueError, match="snapshot"):
        ClaimConclusionInput(CLAIM, A, "SUPPORTS", 0, SNAPSHOT, None)


def test_r2_scope_exact_keys_uppercase_enum_and_nfc() -> None:
    scope = {"population": "Cafe\u0301", "conditions": None,
             "time_window": None, "applicability": None}
    normalized = conclusion_content_material(CONCLUSION, "Cafe\u0301", scope,
                                              "MODERATE", None, SUPPORT_HASH)
    assert normalized["statement"] == "Caf\u00e9"
    assert normalized["scope"]["population"] == "Caf\u00e9"
    with pytest.raises(ValueError, match="scope"):
        conclusion_content_material(CONCLUSION, "x", {"population": "Adults"},
                                    "MODERATE", None, SUPPORT_HASH)
    with pytest.raises(ValueError, match="confidence"):
        conclusion_content_material(CONCLUSION, "x", scope, "moderate", None, SUPPORT_HASH)
