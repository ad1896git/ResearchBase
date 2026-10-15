"""Literal R3 manuscript vectors and material sensitivity."""

from dataclasses import replace
from typing import Any, cast
from uuid import UUID

import pytest

from researchbase.domain.manuscript import (
    ManuscriptPlacement,
    ManuscriptReference,
    manuscript_content_material,
    manuscript_placement_material,
)
from researchbase.foundation.canonical_json import canonical_json_bytes
from researchbase.foundation.hashing import sha256_canonical_json

SOURCE = ManuscriptReference("SourceVersion", UUID(int=1), "d" * 64)
DOCUMENT = ManuscriptReference("ArtifactVersion", UUID(int=0x24), "e" * 64)
CITATION = ManuscriptPlacement(SOURCE, "INTRO", "PARAGRAPH", "p1", "BACKGROUND", 0)


def test_literal_r3_vectors():
    placements = manuscript_placement_material((CITATION,))
    assert len(canonical_json_bytes(placements)) == 411
    placement_hash = str(sha256_canonical_json(placements))
    assert placement_hash == "4dd9c22356a328ec182d0a4f2330f55ffe5b60b6ca65d48eee63ced773bddf95"
    manuscript = manuscript_content_material(
        UUID(int=4), DOCUMENT, "Café recall", None, "INITIAL", placement_hash
    )
    assert len(canonical_json_bytes(manuscript)) == 439
    assert (
        sha256_canonical_json(manuscript)
        == "2e910c3b0c9242184a0d4daf7fda5bd5f17defb41feb7e53fa46be1ff83830dc"
    )
    assert set(manuscript) == {
        "type",
        "material_version",
        "publication_id",
        "document_artifact",
        "title",
        "abstract",
        "semantic_change_class",
        "placement_set_hash",
    }


@pytest.mark.parametrize(
    "change",
    [
        {"section_id": "METHOD"},
        {"locator_kind": "SPAN"},
        {"locator_value": "p2"},
        {"annotation": "METHOD"},
        {"target": replace(SOURCE, id=UUID(int=2))},
        {"target": replace(SOURCE, content_hash="c" * 64)},
    ],
)
def test_each_placement_field_changes_hash(change):
    assert sha256_canonical_json(
        manuscript_placement_material((replace(CITATION, **change),))
    ) != sha256_canonical_json(manuscript_placement_material((CITATION,)))


def test_order_empty_arrays_and_repeated_targets():
    second = replace(CITATION, ordinal=1, locator_value="p2")
    assert manuscript_placement_material((second, CITATION)) == manuscript_placement_material(
        (CITATION, second)
    )
    assert (
        len(cast(list, manuscript_placement_material((second, CITATION))["citation_placements"]))
        == 2
    )
    empty = manuscript_placement_material(())
    assert all(
        empty[key] == []
        for key in ("claim_placements", "citation_placements", "artifact_placements")
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("publication_id", UUID(int=2)),
        ("title", "Café recall "),
        ("abstract", "Abstract"),
        ("semantic_change_class", "EDITORIAL"),
        ("placement_set_hash", "b" * 64),
        ("document_artifact", replace(DOCUMENT, id=UUID(int=2))),
    ],
)
def test_each_manuscript_field_changes_hash(field, value):
    args: dict[str, Any] = dict(
        publication_id=UUID(int=4),
        document_artifact=DOCUMENT,
        title="Café recall",
        abstract=None,
        semantic_change_class="INITIAL",
        placement_set_hash="a" * 64,
    )
    base = manuscript_content_material(**args)
    args[field] = value
    assert sha256_canonical_json(manuscript_content_material(**args)) != sha256_canonical_json(base)
