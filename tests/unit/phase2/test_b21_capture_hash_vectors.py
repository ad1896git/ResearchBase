"""Independent complete literal v2 bytes; v1 remains byte-identical."""

import hashlib
import json
from dataclasses import replace
from uuid import UUID

from researchbase.domain.novelty import CapturedResolution, CapturedResult, coverage_material
from researchbase.foundation.canonical_json import canonical_json_text
from researchbase.foundation.hashing import sha256_canonical_json
from tests.unit.phase2.test_b21_capture_contract import build

BASE = {
    "type": "SearchCoverage",
    "material_version": 2,
    "search_plan_version": {
        "type": "LiteratureSearchPlanVersion",
        "id": "00000000-0000-0000-0000-000000000001",
        "content_hash": "a" * 64,
    },
    "search_execution": [
        {"type": "LiteratureSearchExecution", "id": "00000000-0000-0000-0000-000000000002"}
    ],
    "providers": [],
    "query_count": 0,
    "result_count": 0,
    "resolved_source_count": 0,
    "time_scope": None,
    "coverage_limitations": "é",
    "captured_unresolved_result_count": 0,
    "captured_results": [],
}


def oracle(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def test_empty_literal_bytes_and_legacy():
    literal = oracle(BASE)
    assert canonical_json_text(build()) == literal
    assert str(sha256_canonical_json(build())) == hashlib.sha256(literal.encode()).hexdigest()
    v1 = {
        k: v
        for k, v in BASE.items()
        if k not in {"captured_results", "captured_unresolved_result_count"}
    }
    v1["material_version"] = 1
    from researchbase.domain.novelty import HashRef

    actual = coverage_material(
        HashRef("LiteratureSearchPlanVersion", UUID(int=1), "a" * 64),
        (UUID(int=2),),
        (),
        0,
        0,
        0,
        None,
        "é",
    )
    assert canonical_json_text(actual) == oracle(v1)
    assert str(sha256_canonical_json(actual)) == hashlib.sha256(oracle(v1).encode()).hexdigest()


def test_full_literal_children_sorted_and_bound():
    r = CapturedResolution(UUID(int=6), "b" * 64, UUID(int=8), UUID(int=9))
    results = (
        CapturedResult(UUID(int=4), (r, replace(r, id=UUID(int=5)))),
        CapturedResult(UUID(int=3), ()),
    )
    literal = dict(
        BASE,
        result_count=2,
        resolved_source_count=1,
        captured_unresolved_result_count=1,
        captured_results=[
            {
                "search_result_record": {
                    "type": "SearchResultRecord",
                    "id": "00000000-0000-0000-0000-000000000003",
                },
                "resolutions": [],
            },
            {
                "search_result_record": {
                    "type": "SearchResultRecord",
                    "id": "00000000-0000-0000-0000-000000000004",
                },
                "resolutions": [
                    {
                        "type": "SearchResultResolution",
                        "id": "00000000-0000-0000-0000-000000000005",
                        "content_hash": "b" * 64,
                    },
                    {
                        "type": "SearchResultResolution",
                        "id": "00000000-0000-0000-0000-000000000006",
                        "content_hash": "b" * 64,
                    },
                ],
            },
        ],
    )
    actual = build(results, resolved_source_count=1, captured_unresolved_result_count=1)
    assert canonical_json_text(actual) == oracle(literal)
    assert (
        str(sha256_canonical_json(actual)) == hashlib.sha256(oracle(literal).encode()).hexdigest()
    )
    assert actual == build(
        tuple(reversed(results)), resolved_source_count=1, captured_unresolved_result_count=1
    )
    for changed in (replace(r, content_hash="c" * 64), replace(r, id=UUID(int=7))):
        other = (replace(results[0], resolutions=(changed,)), results[1])
        assert actual != build(other, resolved_source_count=1, captured_unresolved_result_count=1)
