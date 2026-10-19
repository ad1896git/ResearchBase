"""Independent literal complete new-shape bytes and digests."""

import hashlib
import json
from copy import deepcopy
from typing import Any
from uuid import UUID

import pytest

from researchbase.domain.novelty import (
    ClosenessCriteria,
    HashRef,
    NoveltyOutcome,
    ProbeDisposition,
    ProbeInput,
    ScreeningBasis,
    ScreeningDisposition,
    ScreeningResult,
    versioned_novelty_material,
)
from researchbase.foundation.canonical_json import canonical_json_bytes
from researchbase.foundation.hashing import sha256_canonical_json


@pytest.mark.parametrize(
    "outcome", [NoveltyOutcome.INCONCLUSIVE, NoveltyOutcome.NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE]
)
@pytest.mark.parametrize("empty", [False, True])
@pytest.mark.parametrize("predecessor", [False, True])
def test_literal_bytes(outcome, empty, predecessor):
    def ident(kind, n):
        return {"type": kind, "id": str(UUID(int=n))}

    def ref(kind, n):
        return dict(ident(kind, n), content_hash="a" * 64)

    def r(kind, n):
        return HashRef(kind, UUID(int=n), "a" * 64)

    literal: dict[str, Any] = dict(
        type="NoveltyAssessment",
        material_version=2,
        claim_version=ref("ClaimVersion", 1),
        search_coverage=ref("SearchCoverage", 2),
        assessment=outcome.value,
        limitations="Bounded",
        supersedes_assessment=ref("NoveltyAssessment", 3) if predecessor else None,
        assessed_by=ident("ActorIdentity", 4),
        scope_statement="Selected é",
        closeness_criteria={"statements": ["Method", "Result"]},
        prior_art_basis=[],
        screening_basis={
            "probes": [
                {
                    "search_execution": ident("LiteratureSearchExecution", 5),
                    "query_index": 0,
                    "disposition": "NO_HITS" if empty else "SCREENED",
                    "rationale": "Retained é",
                }
            ],
            "results": []
            if empty
            else [
                {
                    "search_result_record": ident("SearchResultRecord", 6),
                    "disposition": "NOT_CLOSE",
                    "criteria_ordinals": [0, 1],
                    "rationale": "Different",
                    "prior_art_relation": ref("PriorArtRelation", 7),
                    "search_result_resolution": ref("SearchResultResolution", 8),
                }
            ],
        },
    )
    basis = ScreeningBasis(
        (
            ProbeInput(
                UUID(int=5),
                0,
                ProbeDisposition.NO_HITS if empty else ProbeDisposition.SCREENED,
                "Retained e\u0301",
            ),
        ),
        ()
        if empty
        else (
            ScreeningResult(
                UUID(int=6),
                ScreeningDisposition.NOT_CLOSE,
                (0, 1),
                "Different",
                r("PriorArtRelation", 7),
                r("SearchResultResolution", 8),
            ),
        ),
    )
    actual = versioned_novelty_material(
        2,
        r("ClaimVersion", 1),
        r("SearchCoverage", 2),
        outcome,
        "Bounded",
        r("NoveltyAssessment", 3) if predecessor else None,
        UUID(int=4),
        scope_statement="Selected e\u0301",
        closeness_criteria=ClosenessCriteria(("Method", "Result")),
        screening_basis=basis,
    )
    expected = json.dumps(
        literal, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    pinned = (
        (
            "7a0c193c3320c76a6fe6b300da03769fa5475a9f5b6242d7a0a6d9a252e4afd5",
            "1a44f10ddd2fb7321f4ff03813bfbe59d0be3235c38c9b4cd81ee8ee81039de8",
            "cf1d0610a5d2cac26b33eb3eeda358cee4a59f642135281326fb70bdd19c25a1",
            "f616bd68555f8583e63cc2a0968f65332a38d902db367b116106164ab53ec770",
        ),
        (
            "fe165a3ccfb5e93edec039d03394ab737286fb8c6f7dc404e14ac5d9db01dbc2",
            "c8eaecc9f5aa878e7d7d18cd2d28001790ed78c41fae0a1d48f7f663fe5e21b5",
            "d00bb5edda518b94df906783708280c791b5c48d37eeac786715f637967fcf69",
            "6026c2312ec7bdf09889518667283ee96dd7367229d3ce345c4d85ccc5c5958d",
        ),
    )
    assert (
        hashlib.sha256(expected).hexdigest()
        == pinned[int(outcome is NoveltyOutcome.NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE)][
            int(empty) * 2 + int(predecessor)
        ]
    )
    changed_reference = deepcopy(literal)
    changed_reference["search_coverage"]["content_hash"] = "b" * 64
    assert sha256_canonical_json(changed_reference) != sha256_canonical_json(actual)
    if not empty:
        changed_reference = deepcopy(literal)
        changed_reference["screening_basis"]["results"][0]["search_result_resolution"]["id"] = str(
            UUID(int=9)
        )
        assert sha256_canonical_json(changed_reference) != sha256_canonical_json(actual)
    assert actual == literal
    assert canonical_json_bytes(actual) == expected
    assert str(sha256_canonical_json(actual)) == hashlib.sha256(expected).hexdigest()
    changed = dict(actual, closeness_criteria={"statements": ["Result", "Method"]})
    assert sha256_canonical_json(changed) != sha256_canonical_json(actual)


def test_multirow_canonical_order():
    from dataclasses import replace

    def ref(kind, n):
        return HashRef(kind, UUID(int=n), "a" * 64)

    probes = (
        ProbeInput(UUID(int=3), 1, ProbeDisposition.SCREENED, "Later query"),
        ProbeInput(UUID(int=2), 0, ProbeDisposition.NO_HITS, "Empty query"),
        ProbeInput(UUID(int=3), 0, ProbeDisposition.SCREENED, "Earlier query"),
    )
    result = ScreeningResult(
        UUID(int=6),
        ScreeningDisposition.NOT_CLOSE,
        (1, 0),
        "Different",
        ref("PriorArtRelation", 7),
        ref("SearchResultResolution", 8),
    )
    results = (replace(result, search_result_record_id=UUID(int=9)), result)
    basis = ScreeningBasis(probes, results)
    material = basis.material()
    assert [(p["search_execution"]["id"], p["query_index"]) for p in material["probes"]] == [
        (str(UUID(int=2)), 0),
        (str(UUID(int=3)), 0),
        (str(UUID(int=3)), 1),
    ]
    assert [r["search_result_record"]["id"] for r in material["results"]] == [
        str(UUID(int=6)),
        str(UUID(int=9)),
    ]
    assert all(r["criteria_ordinals"] == [0, 1] for r in material["results"])
    reordered = ScreeningBasis(tuple(reversed(probes)), tuple(reversed(results)))
    assert canonical_json_bytes(material) == canonical_json_bytes(reordered.material())
