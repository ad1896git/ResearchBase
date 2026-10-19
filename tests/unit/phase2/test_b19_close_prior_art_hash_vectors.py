"""Independent literal v2 payload, using no production builder for the oracle."""

import hashlib
import json
from typing import Any
from uuid import UUID

import pytest

from researchbase.domain.novelty import (
    ClosenessCriteria,
    HashRef,
    NoveltyOutcome,
    versioned_novelty_material,
)
from researchbase.foundation.hashing import sha256_canonical_json


def test_literal_v2_and_mixed_predecessor():
    def ref(kind, i, digest="a" * 64):
        return {"type": kind, "id": str(UUID(int=i)), "content_hash": digest}

    def r(kind, i):
        return HashRef(kind, UUID(int=i), "a" * 64)

    literal = {
        "type": "NoveltyAssessment",
        "material_version": 2,
        "claim_version": ref("ClaimVersion", 1),
        "search_coverage": ref("SearchCoverage", 2),
        "assessment": "CLOSE_PRIOR_ART_FOUND",
        "limitations": "Limited",
        "supersedes_assessment": ref("NoveltyAssessment", 3),
        "assessed_by": {"type": "ActorIdentity", "id": str(UUID(int=4))},
        "scope_statement": "Selected é",
        "closeness_criteria": {"statements": ["method", "result"]},
        "prior_art_basis": [
            {
                "prior_art_relation": ref("PriorArtRelation", i),
                "search_result_resolution": ref("SearchResultResolution", 7),
            }
            for i in (5, 6)
        ],
    }
    args = (
        r("ClaimVersion", 1),
        r("SearchCoverage", 2),
        NoveltyOutcome.CLOSE_PRIOR_ART_FOUND,
        "Limited",
        r("NoveltyAssessment", 3),
        UUID(int=4),
    )
    kwargs: dict[str, Any] = dict(
        scope_statement="Selected e\u0301",
        closeness_criteria=ClosenessCriteria(("method", "result")),
        prior_art_basis=tuple(
            (r("PriorArtRelation", i), r("SearchResultResolution", 7)) for i in (6, 5)
        ),
    )
    actual = versioned_novelty_material(2, *args, **kwargs)
    expected = hashlib.sha256(
        json.dumps(literal, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()
    assert actual == literal
    assert str(sha256_canonical_json(actual)) == expected
    assert actual == versioned_novelty_material(
        2, *args, **(kwargs | {"prior_art_basis": tuple(reversed(kwargs["prior_art_basis"]))})
    )
    for change in (
        dict(scope_statement="Other"),
        dict(closeness_criteria=ClosenessCriteria(("result", "method"))),
        dict(prior_art_basis=((r("PriorArtRelation", 5), r("SearchResultResolution", 8)),)),
    ):
        assert (
            str(sha256_canonical_json(versioned_novelty_material(2, *args, **(kwargs | change))))
            != expected
        )
    assert "current_validity" not in actual
    for version in (0, 3, True, "2"):
        with pytest.raises(ValueError):
            versioned_novelty_material(version, *args, **kwargs)


def test_relation_and_transitive_evidence_digest_are_material():
    from researchbase.domain.novelty import PriorArtKind, prior_art_material

    def ref(kind, i, digest="a" * 64):
        return HashRef(kind, UUID(int=i), digest)

    def assessment(evidence_digest):
        comparison = prior_art_material(
            ref("ClaimVersion", 1),
            ref("SourceVersion", 2),
            PriorArtKind.IDENTICAL,
            "Compared",
            (ref("LiteratureEvidence", 3, evidence_digest),),
            UUID(int=4),
        )
        relation_hash = str(sha256_canonical_json(comparison))
        return versioned_novelty_material(
            2,
            ref("ClaimVersion", 1),
            ref("SearchCoverage", 5),
            NoveltyOutcome.CLOSE_PRIOR_ART_FOUND,
            "Bounded",
            None,
            UUID(int=4),
            scope_statement="Selected",
            closeness_criteria=ClosenessCriteria(("Same",)),
            prior_art_basis=(
                (ref("PriorArtRelation", 6, relation_hash), ref("SearchResultResolution", 7)),
            ),
        )

    assert sha256_canonical_json(assessment("a" * 64)) != sha256_canonical_json(
        assessment("b" * 64)
    )
