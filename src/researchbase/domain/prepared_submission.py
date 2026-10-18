"""Pure S2 occurrence projection and literal R2 package/consent material."""

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from researchbase.domain.authorship import ExactReference, contribution_text
from researchbase.domain.scientific_conclusion import _uuid

PackageStatus = Literal["PREPARED", "WITHDRAWN"]
ConsentState = Literal["GRANTED"]
ConsentScope = Literal["PREPARED_PACKAGE"]
Category = Literal["FIGURE", "TABLE", "CITATION", "CLAIM", "CONCLUSION", "AUTHOR_CONSENT"]
Validity = Literal["NOT_FROZEN", "STALE", "INVALID"]
ValidityReason = Literal[
    "NOT_FROZEN",
    "CONSENT_MISSING",
    "UPSTREAM_INVALID",
    "UPSTREAM_STALE",
    "PACKAGE_WITHDRAWN",
    "DEPENDENCY_UNAVAILABLE",
]
TARGET_TYPES = {
    "FIGURE": "ArtifactVersion",
    "TABLE": "ArtifactVersion",
    "CITATION": "SourceVersion",
    "CLAIM": "ClaimVersion",
    "CONCLUSION": "ScientificConclusionVersion",
    "AUTHOR_CONSENT": "AuthorConsent",
}
withdrawal_reason = contribution_text


@dataclass(frozen=True, slots=True)
class ManifestItemReadback:
    id: UUID
    category: Category
    ordinal: int
    target: ExactReference

    def __post_init__(self):
        _uuid(self.id, "manifest identity")
        if type(self.category) is not str or self.category not in TARGET_TYPES:
            raise ValueError("closed category required")
        if type(self.ordinal) is not int or not 0 <= self.ordinal <= 9999:
            raise ValueError("manifest ordinal must be 0..9999")
        if (
            type(self.target) is not ExactReference
            or self.target.type != TARGET_TYPES[self.category]
        ):
            raise ValueError("category requires exact target type")


def project_occurrences(placements, author_count: int):
    """Input tuples: category, section_id, placement ordinal, exact target.

    UTF-8 byte order is PostgreSQL COLLATE C for the admitted Unicode text.
    IDs are allocated by the Application; occurrences are never deduplicated.
    """
    if type(author_count) is not int or not 1 <= author_count <= 100:
        raise ValueError("S1 author count required")
    if len(placements) + author_count > 10000:
        raise ValueError("manifest must reserve author consent capacity")
    result = []
    for category in sorted(TARGET_TYPES):
        rows = [p for p in placements if p[0] == category]
        if category == "AUTHOR_CONSENT" and rows:
            raise ValueError("consent occurrences are transient")
        for ordinal, (_, _section, _, target) in enumerate(
            sorted(rows, key=lambda p: (p[1].encode("utf-8"), p[2]))
        ):
            if type(target) is not ExactReference or target.type != TARGET_TYPES[category]:
                raise ValueError("wrong occurrence target")
            result.append((category, ordinal, target))
    if len(result) != len(placements):
        raise ValueError("unsupported placement category")
    return tuple(result)


def reference_material(ref: ExactReference):
    if type(ref) is not ExactReference:
        raise ValueError("typed exact reference required")
    return {"type": ref.type, "id": str(ref.id), "content_hash": ref.content_hash}


def consent_material(package_id: UUID, actor_id: UUID, evidence: ExactReference):
    _uuid(package_id, "package")
    _uuid(actor_id, "author")
    if type(evidence) is not ExactReference or evidence.type != "ArtifactVersion":
        raise ValueError("exact evidence required")
    return {
        "type": "AuthorConsent",
        "material_version": 1,
        "prepared_submission": {"type": "PreparedSubmissionVersion", "id": str(package_id)},
        "actor": {"type": "ActorIdentity", "id": str(actor_id)},
        "consent_state": "GRANTED",
        "consent_scope": "PREPARED_PACKAGE",
        "evidence_artifact": reference_material(evidence),
        "prior_consent": None,
    }


def manifest_material(manuscript: ExactReference, snapshot: ExactReference, items):
    if manuscript.type != "ManuscriptVersion" or snapshot.type != "AuthorshipSnapshot":
        raise ValueError("exact package context required")
    coordinates = [(i.category, i.ordinal) for i in items]
    if len(set(coordinates)) != len(coordinates) or len(items) > 10000:
        raise ValueError("bounded unique manifest coordinates required")
    for category in TARGET_TYPES:
        if sorted(i.ordinal for i in items if i.category == category) != list(
            range(sum(i.category == category for i in items))
        ):
            raise ValueError("gap-free category coordinates required")
    return {
        "type": "PreparedSubmissionVersionManifest",
        "material_version": 1,
        "manuscript_version": reference_material(manuscript),
        "authorship_snapshot": reference_material(snapshot),
        "items": [
            {"category": i.category, "ordinal": i.ordinal, "target": reference_material(i.target)}
            for i in sorted(items, key=lambda i: (i.category, i.ordinal))
        ],
    }
