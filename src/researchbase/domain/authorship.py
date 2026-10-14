"""Pure S1 authorship validation and literal R2 hash material."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from researchbase.domain.scientific_conclusion import _digest, _uuid

ContributionRole = Literal[
    "CONCEPTUALIZATION", "INVESTIGATION", "ANALYSIS", "SOFTWARE", "WRITING", "REVIEW"
]
ROLES = frozenset(
    {"CONCEPTUALIZATION", "INVESTIGATION", "ANALYSIS", "SOFTWARE", "WRITING", "REVIEW"}
)


def contribution_text(value: str) -> str:
    if type(value) is not str or any(ord(c) == 0 or 0xD800 <= ord(c) <= 0xDFFF for c in value):
        raise ValueError("valid Unicode contribution statement required")
    value = unicodedata.normalize("NFC", value)
    if not 1 <= len(value) <= 10000 or not value.strip():
        raise ValueError("nonblank contribution statement must contain 1..10000 characters")
    return value


def uuid_tuple(value: tuple[UUID, ...], minimum: int, maximum: int) -> tuple[UUID, ...]:
    if type(value) is not tuple or not minimum <= len(value) <= maximum:
        raise ValueError("bounded UUID tuple required")
    for identity in value:
        _uuid(identity, "record identity")
    if len(set(value)) != len(value):
        raise ValueError("duplicate identities forbidden")
    return value


def authorship_sets(authors, corresponding, groups):
    uuid_tuple(authors, 1, 100)
    uuid_tuple(corresponding, 1, 100)
    if type(groups) is not tuple or len(groups) > 50:
        raise ValueError("bounded equal group tuple required")
    if not set(corresponding) <= set(authors):
        raise ValueError("corresponding authors must be authors")
    seen = set()
    normalized = []
    for group in groups:
        uuid_tuple(group, 2, 100)
        if not set(group) <= set(authors) or seen.intersection(group):
            raise ValueError("equal groups must be disjoint author subsets")
        seen.update(group)
        normalized.append(tuple(sorted(group, key=str)))
    return tuple(sorted(corresponding, key=str)), tuple(
        sorted(normalized, key=lambda g: tuple(map(str, g)))
    )


@dataclass(frozen=True, slots=True)
class ExactReference:
    type: Literal[
        "ContributionRecord",
        "AuthorshipSnapshot",
        "ArtifactVersion",
        "SourceVersion",
        "ClaimVersion",
        "ScientificConclusionVersion",
        "AuthorConsent",
        "ManuscriptVersion",
    ]
    id: UUID
    content_hash: str

    def __post_init__(self):
        if self.type not in {
            "ContributionRecord",
            "AuthorshipSnapshot",
            "ArtifactVersion",
            "SourceVersion",
            "ClaimVersion",
            "ScientificConclusionVersion",
            "AuthorConsent",
            "ManuscriptVersion",
        }:
            raise ValueError("unsupported exact reference")
        _uuid(self.id, "exact reference")
        _digest(self.content_hash, "exact hash")


@dataclass(frozen=True, slots=True)
class AuthorshipAuthor:
    actor_id: UUID
    ordinal: int

    def __post_init__(self):
        _uuid(self.actor_id, "author")
        if type(self.ordinal) is not int or not 1 <= self.ordinal <= 100:
            raise ValueError("author ordinal must be 1..100")


@dataclass(frozen=True, slots=True)
class OrderedContribution:
    contribution_record: ExactReference
    ordinal: int

    def __post_init__(self):
        if (
            type(self.contribution_record) is not ExactReference
            or self.contribution_record.type != "ContributionRecord"
        ):
            raise ValueError("exact contribution required")
        if type(self.ordinal) is not int or not 0 <= self.ordinal <= 999:
            raise ValueError("contribution ordinal must be 0..999")


def contribution_material(
    publication_id: UUID, actor_id: UUID, role: ContributionRole, statement: str, recorded_by: UUID
) -> dict[str, object]:
    for identity in (publication_id, actor_id, recorded_by):
        _uuid(identity, "identity")
    if type(role) is not str or role not in ROLES:
        raise ValueError("unsupported contribution role")
    return {
        "type": "ContributionRecord",
        "material_version": 1,
        "publication": {"type": "Publication", "id": str(publication_id)},
        "actor": {"type": "ActorIdentity", "id": str(actor_id)},
        "contribution_role": role,
        "contribution_statement": contribution_text(statement),
        "recorded_by": {"type": "ActorIdentity", "id": str(recorded_by)},
    }


def validate_coverage(authors, actor_types, publication_id, contributions):
    if any(actor_types.get(identity) != "HUMAN" for identity in authors):
        raise ValueError("only HUMAN authors permitted")
    if any(row["publication_id"] != publication_id for row in contributions):
        raise ValueError("same publication contributions required")
    if not set(authors) <= {row["actor_id"] for row in contributions}:
        raise ValueError("each author requires their own contribution")


def authorship_material(
    publication_id: UUID,
    authors: tuple[AuthorshipAuthor, ...],
    corresponding: tuple[UUID, ...],
    groups: tuple[tuple[UUID, ...], ...],
    contributions: tuple[OrderedContribution, ...],
) -> dict[str, object]:
    _uuid(publication_id, "publication")
    if type(authors) is not tuple or any(type(a) is not AuthorshipAuthor for a in authors):
        raise ValueError("typed author tuple required")
    if [a.ordinal for a in authors] != list(range(1, len(authors) + 1)):
        raise ValueError("contiguous authored order required")
    corresponding, groups = authorship_sets(
        tuple(a.actor_id for a in authors), corresponding, groups
    )
    if type(contributions) is not tuple or any(
        type(c) is not OrderedContribution for c in contributions
    ):
        raise ValueError("typed contribution tuple required")
    uuid_tuple(tuple(c.contribution_record.id for c in contributions), 1, 1000)
    if [c.ordinal for c in contributions] != list(range(len(contributions))):
        raise ValueError("contiguous contribution order required")
    return {
        "type": "AuthorshipSnapshot",
        "material_version": 1,
        "publication_id": str(publication_id),
        "authors": [
            {"actor": {"type": "ActorIdentity", "id": str(a.actor_id)}, "ordinal": a.ordinal}
            for a in authors
        ],
        "corresponding_authors": [{"type": "ActorIdentity", "id": str(a)} for a in corresponding],
        "equal_contribution_groups": [
            [{"type": "ActorIdentity", "id": str(a)} for a in g] for g in groups
        ],
        "contribution_records": [
            {
                "contribution_record": {
                    "type": "ContributionRecord",
                    "id": str(c.contribution_record.id),
                    "content_hash": c.contribution_record.content_hash,
                },
                "ordinal": c.ordinal,
            }
            for c in contributions
        ],
    }
