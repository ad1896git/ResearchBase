"""Durable P1-FCR4 valid-digest and canonicalization invariance corpus."""

from __future__ import annotations

from tests.integration.test_p1_fcr4_ownership_matrix import CASES, nested_json, plain
from tests.oracles.p1_fcr4_digest_corpus import (
    GENERIC_VECTORS,
    build_report,
    independent_bytes,
    independent_digest,
    structured_materials,
)

from researchbase.foundation.frozen_json import freeze_json, thaw_json

# Captured by executing this corpus against exact phase1-final-v3
# (3ebedad1f204bbb2e974572e6a1a00c89fd00503), not reconstructed by POST code.
V3_STRUCTURED_DIGESTS = {
    "ResearchQuestionVersion": "4d6dcc81038e078b79f8d7e8da9cc6de4c665bf3f48533fef16a286127623d2f",
    "HypothesisVersion": "52a37243a2fa7d0f0e7e1989b7bd647d9521fdf2dca2c3e7dadedff8e1379ba8",
    "ExperimentSpecVersion": "76e28685f4516504b1f41add7a033265c781477cc3beb9e3bf874f4cf9c11792",
    "DatasetSnapshot": "38daf1f496708bcbcfd62de62c452d4ee5c723b881078dfadc94dde8fcc6d288",
    "MetricDefinitionVersion": "be24582a77a1c066c57891f9dc1186d95583788310f649a9ee46ff049aea7e7e",
    "Measurement": "880de12963b6028fd48d32f21f88b493544656a4d0548b9b2b8e312e0ee65511",
    "StatisticalResult": "42bef55d6f5aeadc6d61fd5cd727b6efcf896d3a61dd21186bf5fe6fd82df2ce",
    "ClaimVersion": "fe63e19b8bbc4c3a0c3f27b92ff56bb76e5a2c8d40ed4b7bec64cff1e22e36b9",
    "ImpactAssessment": "6ea0d42fa5060c006cdabe63343aa884d0f1b04dbce6fdf5021d07d7effc4e73",
    "CorrectionRecord": "e20ffa6f5787fa2144fabc332d2d066a6d0522b7f970c0b15a05ab1739f4f240",
}


def test_exact_v3_structured_digest_corpus_is_unchanged() -> None:
    report = build_report()
    assert set(report["structured"]) == set(V3_STRUCTURED_DIGESTS)
    assert len(report["structured"]) == 10
    assert {
        name: vector["digest"] for name, vector in report["structured"].items()
    } == V3_STRUCTURED_DIGESTS


def test_structured_and_generic_payloads_match_independent_oracle_exactly() -> None:
    report = build_report()
    for family in ("structured", "generic"):
        for vector in report[family].values():
            assert vector["canonical_hex"] == vector["oracle_canonical_hex"]
            assert vector["digest"] == vector["oracle_digest"]


def test_canonical_json_order_unicode_and_float_contract_is_unchanged() -> None:
    report = build_report()["generic"]
    assert report["key-order-a"]["canonical_hex"] == report["key-order-b"]["canonical_hex"]
    assert report["key-order-a"]["digest"] == report["key-order-b"]["digest"]
    assert report["ordered-array"]["canonical_hex"] != report["reversed-array"]["canonical_hex"]
    assert report["ordered-array"]["digest"] != report["reversed-array"]["digest"]
    assert (
        report["unicode-composed"]["canonical_hex"] != report["unicode-decomposed"]["canonical_hex"]
    )
    assert independent_bytes(GENERIC_VECTORS["finite-floats"]) == (
        b'{"negative_zero":-0.0,"positive":1.25}'
    )


def test_special_hash_families_retain_distinct_v3_semantics() -> None:
    report = build_report()
    artifact = report["artifact"]
    assert artifact["production_digest"] == artifact["oracle_digest"]
    assert artifact["metadata_a_digest"] == artifact["metadata_b_digest"]
    assert report["support_set"]["production_digest"] == report["support_set"]["oracle_digest"]
    assert report["bindings"]["structured_measurement"] == V3_STRUCTURED_DIGESTS["Measurement"]
    assert report["bindings"]["raw_artifact"] == artifact["oracle_digest"]
    assert report["bindings"]["hashless_run"] is None
    assert report["manifest"]["snapshot_digest"] == V3_STRUCTURED_DIGESTS["DatasetSnapshot"]


def test_frozen_json_and_thaw_roundtrip_do_not_change_payload_or_digest() -> None:
    for material in structured_materials().values():
        frozen = freeze_json(material)
        thawed = thaw_json(frozen)
        assert thawed == material
        assert independent_bytes(thawed) == independent_bytes(material)
        assert independent_digest(thawed) == independent_digest(material)


def test_dto_to_domain_snapshots_preserve_exact_json_digest() -> None:
    for case in CASES:
        source = nested_json()
        expected = independent_digest(source)
        dto = case.dto_factory(source)
        domain = case.domain_factory(getattr(dto, case.field))
        assert independent_digest(plain(getattr(dto, case.field))) == expected
        assert independent_digest(plain(getattr(domain, case.field))) == expected
