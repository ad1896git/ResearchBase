from __future__ import annotations

import unicodedata
from dataclasses import replace
from datetime import date
from uuid import UUID

import pytest

from researchbase.domain.literature_search_plan import (
    FrozenResearchQuestionReference,
    LiteratureSearchPlanMaterial,
    LiteratureSearchStrategy,
    LiteratureSourceScope,
    canonical_language_identifier,
)

PLAN_ID = UUID("00000000-0000-0000-0000-000000000001")
RQ_ID = UUID("00000000-0000-0000-0000-000000000002")
RQ_VERSION_ID = UUID("00000000-0000-0000-0000-000000000003")
RQ_HASH = "a" * 64


def material(language_scope: tuple[str, ...] | None) -> LiteratureSearchPlanMaterial:
    return LiteratureSearchPlanMaterial(
        plan_id=PLAN_ID,
        research_question_refs=(
            FrozenResearchQuestionReference(
                research_question_id=RQ_ID,
                version_id=RQ_VERSION_ID,
                content_hash=RQ_HASH,
            ),
        ),
        objective="Find evidence about language normalization",
        source_scope=LiteratureSourceScope.BIBLIOGRAPHIC,
        inclusion_criteria=None,
        exclusion_criteria=None,
        time_range=None,
        language_scope=language_scope,
        search_strategy=LiteratureSearchStrategy.KEYWORD,
        planned_providers=("provider-a",),
        stopping_rule=None,
    )


def test_language_identifier_trims_and_normalizes_to_nfc_without_case_folding() -> None:
    decomposed = "e\u0301n"
    assert canonical_language_identifier(" en ") == "en"
    assert canonical_language_identifier(decomposed) == unicodedata.normalize("NFC", decomposed)
    assert canonical_language_identifier("EN") == "EN"
    assert canonical_language_identifier("EN") != canonical_language_identifier("en")


@pytest.mark.parametrize("raw", ["", "   ", "\u2003\t"])
def test_language_identifier_rejects_blank_canonical_values(raw: str) -> None:
    with pytest.raises(ValueError, match="blank"):
        canonical_language_identifier(raw)


def test_draft_material_allows_null_language_but_never_hashes_it() -> None:
    draft = material(None)
    with pytest.raises(ValueError, match="language_scope"):
        draft.digest()


def test_empty_language_set_is_valid_frozen_hash_material() -> None:
    value = material(())
    assert value.payload()["language_scope"] == []
    assert value.digest()


def test_language_set_canonicalization_is_order_independent_and_case_sensitive() -> None:
    left = material(("fr", " en ", "EN"))
    right = material(("EN", "en", "fr"))
    assert left.payload()["language_scope"] == ["EN", "en", "fr"]
    assert left.digest() == right.digest()
    assert material(("en",)).digest() != material(("EN",)).digest()


def test_nfc_equivalent_language_sets_have_equal_hashes() -> None:
    composed = material(("é",))
    decomposed = material(("e\u0301",))
    assert composed.payload()["language_scope"] == ["é"]
    assert composed.digest() == decomposed.digest()


def test_material_rejects_duplicate_question_identity_even_for_different_versions() -> None:
    first = FrozenResearchQuestionReference(RQ_ID, RQ_VERSION_ID, RQ_HASH)
    second = FrozenResearchQuestionReference(
        RQ_ID,
        UUID("00000000-0000-0000-0000-000000000004"),
        "b" * 64,
    )
    with pytest.raises(ValueError, match="duplicate ResearchQuestion"):
        LiteratureSearchPlanMaterial(
            plan_id=PLAN_ID,
            research_question_refs=(first, second),
            objective="Find evidence",
            source_scope=LiteratureSourceScope.BIBLIOGRAPHIC,
            inclusion_criteria=None,
            exclusion_criteria=None,
            time_range=None,
            language_scope=(),
            search_strategy=LiteratureSearchStrategy.KEYWORD,
            planned_providers=("provider-a",),
            stopping_rule=None,
        )


def test_question_reference_set_order_does_not_change_digest() -> None:
    other = FrozenResearchQuestionReference(
        UUID("00000000-0000-0000-0000-000000000005"),
        UUID("00000000-0000-0000-0000-000000000006"),
        "b" * 64,
    )
    base = material(())
    left = replace(base, research_question_refs=(*base.research_question_refs, other))
    right = replace(base, research_question_refs=(other, *base.research_question_refs))
    assert left.digest() == right.digest()


def test_payload_has_contract_15_keys_and_literal_empty_language_array() -> None:
    payload = material(()).payload()
    assert set(payload) == {
        "type",
        "material_version",
        "plan_id",
        "research_question_refs",
        "objective",
        "source_scope",
        "inclusion_criteria",
        "exclusion_criteria",
        "time_range",
        "language_scope",
        "search_strategy",
        "planned_providers",
        "stopping_rule",
    }
    assert payload["language_scope"] == []
    assert payload["research_question_refs"] == [
        {
            "type": "ResearchQuestionVersion",
            "id": str(RQ_VERSION_ID),
            "content_hash": RQ_HASH,
        }
    ]


def test_named_structured_values_are_closed_and_canonicalized() -> None:
    value = replace(
        material(()),
        inclusion_criteria={"statements": ["e\u0301ligible"]},
        time_range={"from": date(2020, 1, 1), "through": None},
        stopping_rule={"rule": "Stop after saturation"},
    )
    assert value.payload()["inclusion_criteria"] == {"statements": ["éligible"]}
    assert value.payload()["time_range"] == {"from": "2020-01-01", "through": None}
    assert value.payload()["stopping_rule"] == {"rule": "Stop after saturation"}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("inclusion_criteria", {"statements": ["  "]}),
        ("inclusion_criteria", {"statements": [], "extra": []}),
        ("time_range", {"from": None, "through": None}),
        ("time_range", {"from": date(2025, 1, 1), "through": date(2024, 1, 1)}),
        ("stopping_rule", {"rule": "  "}),
        ("stopping_rule", {"rule": "stop", "extra": "x"}),
    ],
)
def test_invalid_closed_structured_material_is_rejected(field: str, value: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        replace(material(()), **{field: value})


def test_normalized_duplicate_language_identifiers_are_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate canonical language"):
        material(("en", " en "))


def test_material_changes_change_digest() -> None:
    assert (
        material(()).digest() != replace(material(()), objective="A different objective").digest()
    )
