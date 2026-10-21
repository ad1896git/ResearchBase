"""Literal B04 manuscript material; no persistence or authority semantics."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from uuid import UUID

CHANGES = frozenset({"INITIAL", "EDITORIAL", "SCIENTIFIC_MINOR", "SCIENTIFIC_MATERIAL"})
KINDS = frozenset({"PARAGRAPH", "SPAN", "CAPTION", "ANCHOR"})
STRENGTHS = frozenset({"DESCRIPTIVE", "SUGGESTIVE", "SUPPORTED", "STRONG"})
PURPOSES = frozenset(
    {"BACKGROUND", "METHOD", "COMPARISON", "EVIDENCE", "PRIOR_ART", "DATASET", "OTHER"}
)
ROLES = frozenset({"FIGURE", "TABLE", "OTHER"})


def digest(value: object) -> str:
    if not isinstance(value, str) or re.fullmatch("[0-9a-f]{64}", value) is None:
        raise ValueError("canonical SHA-256 digest required")
    return value


def text_value(value: object, *, bounded: bool = True) -> str:
    if not isinstance(value, str):
        raise ValueError("text required")
    value.encode("utf-8", "strict")
    if (
        not value.strip()
        or (bounded and len(value) > 2000)
        or unicodedata.normalize("NFC", value) != value
    ):
        raise ValueError("nonblank NFC text required")
    return value


@dataclass(frozen=True, slots=True)
class ManuscriptReference:
    type: str
    id: UUID
    content_hash: str

    def __post_init__(self) -> None:
        if (
            self.type
            not in {
                "ClaimVersion",
                "ScientificConclusionVersion",
                "SourceVersion",
                "ArtifactVersion",
            }
            or type(self.id) is not UUID
        ):
            raise ValueError("exact typed reference required")
        digest(self.content_hash)

    def material(self) -> dict[str, str]:
        return {"type": self.type, "id": str(self.id), "content_hash": self.content_hash}


@dataclass(frozen=True, slots=True)
class ManuscriptPlacement:
    target: ManuscriptReference
    section_id: str
    locator_kind: str
    locator_value: str
    annotation: str
    ordinal: int

    def __post_init__(self) -> None:
        text_value(self.section_id)
        text_value(self.locator_value)
        if (
            self.locator_kind not in KINDS
            or type(self.ordinal) is not int
            or not 0 <= self.ordinal <= 2147483647
        ):
            raise ValueError("closed locator and bounded ordinal required")
        allowed = (
            PURPOSES
            if self.target.type == "SourceVersion"
            else ROLES
            if self.target.type == "ArtifactVersion"
            else STRENGTHS
        )
        if self.annotation not in allowed:
            raise ValueError("invalid placement annotation")

    def material(self) -> dict[str, object]:
        ref, annotation = (
            ("source_version", "citation_purpose")
            if self.target.type == "SourceVersion"
            else ("artifact_version", "artifact_role")
            if self.target.type == "ArtifactVersion"
            else ("target", "rhetorical_strength")
        )
        return {
            ref: self.target.material(),
            "section_id": self.section_id,
            "locator": {"kind": self.locator_kind, "value": self.locator_value},
            annotation: self.annotation,
            "ordinal": self.ordinal,
        }


def manuscript_placement_material(placements: tuple[ManuscriptPlacement, ...]) -> dict[str, object]:
    if len(placements) > 10000:
        raise ValueError("at most 10000 placement occurrences")
    groups: dict[str, list[ManuscriptPlacement]] = {
        "claim_placements": [],
        "citation_placements": [],
        "artifact_placements": [],
    }
    for item in placements:
        group = (
            "citation_placements"
            if item.target.type == "SourceVersion"
            else "artifact_placements"
            if item.target.type == "ArtifactVersion"
            else "claim_placements"
        )
        groups[group].append(item)
    result: dict[str, object] = {"type": "ManuscriptVersionPlacementSet", "material_version": 1}
    for name, items in groups.items():
        items.sort(key=lambda p: (p.section_id, p.ordinal))
        ordinals: dict[str, int] = {}
        for item in items:
            if item.ordinal != ordinals.get(item.section_id, 0):
                raise ValueError("duplicate or gapped section ordinal")
            ordinals[item.section_id] = item.ordinal + 1
        result[name] = [item.material() for item in items]
    return result


def manuscript_content_material(
    publication_id: UUID,
    document_artifact: ManuscriptReference,
    title: str,
    abstract: str | None,
    semantic_change_class: str,
    placement_set_hash: str,
) -> dict[str, object]:
    if (
        type(publication_id) is not UUID
        or document_artifact.type != "ArtifactVersion"
        or semantic_change_class not in CHANGES
    ):
        raise ValueError("closed manuscript material required")
    text_value(title)
    if abstract is not None:
        text_value(abstract, bounded=False)
    return {
        "type": "ManuscriptVersion",
        "material_version": 1,
        "publication_id": str(publication_id),
        "document_artifact": document_artifact.material(),
        "title": title,
        "abstract": abstract,
        "semantic_change_class": semantic_change_class,
        "placement_set_hash": digest(placement_set_hash),
    }
