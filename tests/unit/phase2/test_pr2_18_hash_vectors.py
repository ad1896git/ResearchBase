"""Independent literal R2 JSON bytes; production builders are never the oracle."""

import hashlib
import json
from uuid import UUID

from researchbase.domain.novelty import (
    HashRef,
    NoveltyOutcome,
    PriorArtKind,
    coverage_material,
    novelty_material,
    prior_art_material,
)
from researchbase.foundation.hashing import sha256_canonical_json


def _oracle(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def test_literal_vectors():
    a = UUID(int=1)
    b = UUID(int=2)
    actor = UUID(int=3)

    def r(kind, identity):
        return {"type": kind, "id": str(identity), "content_hash": "a" * 64}

    plan = HashRef("LiteratureSearchPlanVersion", a, "a" * 64)
    claim = HashRef("ClaimVersion", a, "a" * 64)
    source = HashRef("SourceVersion", b, "a" * 64)
    evidence = (
        HashRef("LiteratureEvidence", b, "a" * 64),
        HashRef("LiteratureEvidence", a, "a" * 64),
    )
    literal = {
        "type": "SearchCoverage",
        "material_version": 1,
        "search_plan_version": r("LiteratureSearchPlanVersion", a),
        "search_execution": [
            {"type": "LiteratureSearchExecution", "id": str(a)},
            {"type": "LiteratureSearchExecution", "id": str(b)},
        ],
        "providers": ["a", "é"],
        "query_count": 2,
        "result_count": 3,
        "resolved_source_count": 1,
        "time_scope": None,
        "coverage_limitations": "é limits",
    }
    actual = coverage_material(plan, (b, a), ("é", "a"), 2, 3, 1, None, "e\u0301 limits")
    assert actual == literal
    assert str(sha256_canonical_json(actual)) == _oracle(literal)
    literal = {
        "type": "PriorArtRelation",
        "material_version": 1,
        "claim_version": r("ClaimVersion", a),
        "source_version": r("SourceVersion", b),
        "relation": "UNCLEAR",
        "rationale": "Uncertain",
        "literature_evidence": [r("LiteratureEvidence", a), r("LiteratureEvidence", b)],
        "assessed_by": {"type": "ActorIdentity", "id": str(actor)},
    }
    actual = prior_art_material(claim, source, PriorArtKind.UNCLEAR, "Uncertain", evidence, actor)
    assert actual == literal
    assert str(sha256_canonical_json(actual)) == _oracle(literal)
    assert actual == prior_art_material(
        claim, source, PriorArtKind.UNCLEAR, "Uncertain", tuple(reversed(evidence)), actor
    )
    literal = {
        "type": "NoveltyAssessment",
        "material_version": 1,
        "claim_version": r("ClaimVersion", a),
        "search_coverage": r("SearchCoverage", b),
        "assessment": "INCONCLUSIVE",
        "limitations": "Limited",
        "supersedes_assessment": None,
        "assessed_by": {"type": "ActorIdentity", "id": str(actor)},
    }
    actual = novelty_material(
        claim,
        HashRef("SearchCoverage", b, "a" * 64),
        NoveltyOutcome.INCONCLUSIVE,
        "Limited",
        None,
        actor,
    )
    assert actual == literal
    assert str(sha256_canonical_json(actual)) == _oracle(literal)
    changed = novelty_material(
        claim,
        HashRef("SearchCoverage", b, "a" * 64),
        NoveltyOutcome.INCONCLUSIVE,
        "Changed",
        None,
        actor,
    )
    assert _oracle(changed) != _oracle(literal)
