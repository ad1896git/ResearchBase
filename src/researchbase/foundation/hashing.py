"""Explicit SHA-256 primitives for raw and canonical structured content."""

from __future__ import annotations

import hashlib
import re

from researchbase.foundation.canonical_json import canonical_json_bytes

RAW_BYTES_HASH_SCHEME = "sha256-bytes-v1"
CANONICAL_JSON_HASH_SCHEME = "sha256-cjson-v1"


class ContentHash(str):
    """Validated lower-case SHA-256 digest text."""

    def __new__(cls, value: str) -> ContentHash:
        if not isinstance(value, str):
            raise TypeError("content hash must be text")
        normalized = value.lower()
        if re.fullmatch(r"[0-9a-f]{64}", normalized) is None:
            raise ValueError("content hash must be a 64-character SHA-256 hex digest")
        return str.__new__(cls, normalized)


def sha256_bytes(data: bytes) -> ContentHash:
    """Hash raw bytes with the sha256-bytes-v1 scheme."""
    if not isinstance(data, bytes):
        raise TypeError("sha256_bytes requires bytes")
    return ContentHash(hashlib.sha256(data).hexdigest())


def sha256_canonical_json(value: object) -> ContentHash:
    """Hash canonical-json-v1 UTF-8 bytes with the sha256-cjson-v1 scheme."""
    return sha256_bytes(canonical_json_bytes(value))
