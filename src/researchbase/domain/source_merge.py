"""Typed source-merge governance values and deterministic proposal basis hashing."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from researchbase.foundation.hashing import sha256_canonical_json


@dataclass(frozen=True, slots=True)
class SourceMergeBasis:
    source_a_id: UUID
    source_b_id: UUID
    canonical_survivor_id: UUID
    affected_project_ids: tuple[UUID, ...]
    effective_project_links: tuple[dict[str, str], ...]
    identifier_state: tuple[dict[str, Any], ...]
    source_version_state: tuple[dict[str, Any], ...]
    rationale: str
    evidence_artifacts: tuple[dict[str, str], ...]

    def payload(self) -> dict[str, Any]:
        a, b = sorted((self.source_a_id, self.source_b_id), key=str)
        if a == b or self.canonical_survivor_id not in (a, b):
            raise ValueError("source pair and canonical survivor are invalid")
        rationale = unicodedata.normalize("NFC", self.rationale)
        if not rationale.strip():
            raise ValueError("rationale must not be blank")
        projects = sorted({str(value) for value in self.affected_project_ids})
        links = sorted(
            (dict(row) for row in self.effective_project_links),
            key=lambda row: (row["source_id"], row["project_id"], row["link_id"]),
        )
        identifiers = sorted(
            (dict(row) for row in self.identifier_state),
            key=lambda row: (
                row["identifier_type"],
                row["normalized_value"],
                row["identifier_id"],
            ),
        )
        versions = sorted(
            (dict(row) for row in self.source_version_state),
            key=lambda row: row["source_id"],
        )
        if len(versions) != 2 or {row["source_id"] for row in versions} != {str(a), str(b)}:
            raise ValueError("basis must contain exactly one version state per source")
        artifacts = sorted(
            (dict(row) for row in self.evidence_artifacts),
            key=lambda row: (row["id"], row["content_hash"]),
        )
        if len({(row["id"], row["content_hash"]) for row in artifacts}) != len(artifacts):
            raise ValueError("duplicate evidence artifact")
        return {
            "type": "SourceMergeProposalBasis",
            "material_version": 1,
            "source_a": {"type": "LiteratureSource", "id": str(a)},
            "source_b": {"type": "LiteratureSource", "id": str(b)},
            "canonical_survivor": {
                "type": "LiteratureSource",
                "id": str(self.canonical_survivor_id),
            },
            "affected_project_ids": projects,
            "effective_project_links": links,
            "identifier_state": identifiers,
            "source_version_state": versions,
            "rationale": rationale,
            "evidence_artifacts": artifacts,
        }

    def digest(self) -> str:
        return str(sha256_canonical_json(self.payload()))
