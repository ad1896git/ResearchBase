"""Pure admission values and the unchanged M2 resolution hash material."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from researchbase.domain.source_identity import (
    IdentifierType,
    normalize_reason,
    normalize_source_identifier,
    normalize_source_title,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import sha256_canonical_json

RESOLUTION_FIELDS = (
    "id",
    "search_result_record_id",
    "source_id",
    "source_version_id",
    "resolved_by",
    "resolved_at",
    "basis",
    "hash_scheme",
)


def require_uuid(value: object) -> None:
    if not isinstance(value, UUID):
        raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, "UUID value required")


def normalize_basis(value: str) -> str:
    if not isinstance(value, str):
        raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, "basis must be text")
    try:
        result = normalize_reason(value)
    except ResearchBaseError:
        raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, "invalid resolution basis") from None
    if len(result) > 4096:
        raise ResearchBaseError(
            ErrorCode.VALIDATION_ERROR, "resolution basis exceeds 4096 characters"
        )
    return result


def result_doi(url: str | None) -> str:
    if not isinstance(url, str) or not url.startswith("https://doi.org/"):
        raise ResearchBaseError(ErrorCode.IDENTIFIER_INVALID, "exact DOI URL required")
    return normalize_source_identifier(IdentifierType.DOI, url).normalized_value


def titles_match(result: str, version: str) -> bool:
    return normalize_source_title(result) == normalize_source_title(version)


def resolution_hash(row: dict[str, Any]) -> str:
    return str(
        sha256_canonical_json(
            {
                key: value.astimezone(UTC).isoformat()
                if isinstance(value, datetime)
                else str(value)
                if isinstance(value, UUID)
                else value
                for key in RESOLUTION_FIELDS
                for value in (row[key],)
            }
        )
    )
