"""Typed, deterministic SourceVersion material and lifecycle values."""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from researchbase.foundation.frozen_json import freeze_json, thaw_json
from researchbase.foundation.hashing import ContentHash, sha256_canonical_json


class SourceVersionKind(StrEnum):
    SUBMITTED = "SUBMITTED"
    PREPRINT = "PREPRINT"
    REVISED_PREPRINT = "REVISED_PREPRINT"
    ACCEPTED = "ACCEPTED"
    PUBLISHED = "PUBLISHED"
    CORRECTED = "CORRECTED"
    RETRACTED = "RETRACTED"
    WEB_SNAPSHOT = "WEB_SNAPSHOT"
    OTHER = "OTHER"


class SourceVersionStatus(StrEnum):
    DRAFT = "DRAFT"
    FROZEN = "FROZEN"
    SUPERSEDED = "SUPERSEDED"
    ABANDONED = "ABANDONED"


@dataclass(frozen=True, slots=True)
class FrozenSourceReference:
    id: UUID
    content_hash: str

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID):
            raise TypeError("reference id must be a UUID")
        object.__setattr__(self, "content_hash", ContentHash(self.content_hash))


@dataclass(frozen=True, slots=True)
class SourceVersionMaterial:
    literature_source_id: UUID
    version_kind: SourceVersionKind
    predecessor_source_version: FrozenSourceReference | None
    correction_basis_artifact: FrozenSourceReference | None
    title: str
    abstract: str | None
    authors: tuple[Mapping[str, str | None], ...]
    publication_date: date | None
    venue: str | None
    external_version_label: str | None
    fulltext_artifact: FrozenSourceReference | None
    metadata: Mapping[str, str | None] | None

    def __post_init__(self) -> None:
        if not isinstance(self.literature_source_id, UUID):
            raise TypeError("literature_source_id must be a UUID")
        object.__setattr__(self, "version_kind", SourceVersionKind(self.version_kind))
        object.__setattr__(self, "title", _nfc_text(self.title, "title", allow_blank=False))
        for field_name in ("abstract", "venue", "external_version_label"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(self, field_name, _nfc_text(value, field_name))
        if self.publication_date is not None and not isinstance(self.publication_date, date):
            raise TypeError("publication_date must be a date or null")
        if isinstance(self.publication_date, datetime):
            raise TypeError("publication_date must not be a datetime")
        if self.version_kind in {SourceVersionKind.CORRECTED, SourceVersionKind.RETRACTED} and (
            self.predecessor_source_version is None or self.correction_basis_artifact is None
        ):
            raise ValueError("corrected and retracted versions require predecessor and basis")
        normalized_authors: list[dict[str, str | None]] = []
        for author in self.authors:
            if not isinstance(author, Mapping) or set(author) != {"name", "orcid"}:
                raise ValueError("author entries must contain exactly name and orcid")
            name_value = author["name"]
            if not isinstance(name_value, str):
                raise ValueError("author name must be text")
            name = _nfc_text(name_value, "author name", allow_blank=False)
            orcid = author["orcid"]
            if orcid is not None:
                orcid = _nfc_text(orcid, "author orcid")
            normalized_authors.append({"name": name, "orcid": orcid})
        object.__setattr__(self, "authors", freeze_json(normalized_authors))
        if self.metadata is not None:
            allowed = {
                "journal_identifier",
                "volume",
                "issue",
                "pages",
                "license_label",
                "public_repository_label",
            }
            if not isinstance(self.metadata, Mapping) or set(self.metadata) != allowed:
                raise ValueError("metadata must contain exactly the six registered fields")
            normalized_metadata: dict[str, str | None] = {}
            for key in sorted(allowed):
                value = self.metadata[key]
                if value is None:
                    normalized_metadata[key] = None
                elif isinstance(value, str):
                    normalized_metadata[key] = _nfc_text(value, key)
                else:
                    raise ValueError("metadata values must be strings or null")
            object.__setattr__(self, "metadata", freeze_json(normalized_metadata))

    def payload(self) -> dict[str, Any]:
        return {
            "type": "SourceVersion",
            "material_version": 1,
            "literature_source_id": str(self.literature_source_id),
            "version_kind": self.version_kind.value,
            "predecessor_source_version": _reference_payload(
                "SourceVersion", self.predecessor_source_version
            ),
            "correction_basis_artifact": _reference_payload(
                "ArtifactVersion", self.correction_basis_artifact
            ),
            "title": self.title,
            "abstract": self.abstract,
            "authors": thaw_json(self.authors),
            "publication_date": (
                self.publication_date.isoformat() if self.publication_date is not None else None
            ),
            "venue": self.venue,
            "external_version_label": self.external_version_label,
            "fulltext_artifact": _reference_payload("ArtifactVersion", self.fulltext_artifact),
            "metadata": thaw_json(self.metadata) if self.metadata is not None else None,
        }

    def digest(self) -> str:
        return str(sha256_canonical_json(self.payload()))


def _reference_payload(
    type_name: str, reference: FrozenSourceReference | None
) -> dict[str, str] | None:
    if reference is None:
        return None
    return {"type": type_name, "id": str(reference.id), "content_hash": reference.content_hash}


def _nfc_text(value: str, field_name: str, *, allow_blank: bool = True) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be text")
    normalized = unicodedata.normalize("NFC", value)
    if not allow_blank and not normalized.strip():
        raise ValueError(f"{field_name} must not be blank")
    if any(unicodedata.category(char) in {"Cc", "Cs"} for char in normalized):
        raise ValueError(f"{field_name} cannot contain controls or surrogates")
    return normalized
