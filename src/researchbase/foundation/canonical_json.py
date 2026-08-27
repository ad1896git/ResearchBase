"""Conservative deterministic JSON serialization for material structured content."""

from __future__ import annotations

import json
import math

CANONICAL_JSON_SCHEME = "canonical-json-v1"


def canonical_json_bytes(value: object) -> bytes:
    """Serialize the canonical-json-v1 supported subset as compact UTF-8 bytes.

    Unicode code points are preserved (no normalization is performed); UTF-8 encoding and
    sorted object keys make repeated serialization deterministic. Callers must normalize
    non-JSON-native values before invoking this function. Integer and floating-point values
    remain distinct, including signed zero; this is not an RFC 8785/JCS implementation.
    """
    _validate_supported_value(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def canonical_json_text(value: object) -> str:
    """Return canonical JSON as UTF-8 text."""
    return canonical_json_bytes(value).decode("utf-8")


def _validate_supported_value(value: object) -> None:
    if value is None or isinstance(value, bool | int | str):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("canonical JSON numbers must be finite")
        return
    if isinstance(value, list):
        for item in value:
            _validate_supported_value(item)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(
                    "only the supported JSON subset is accepted: object keys must be strings"
                )
            _validate_supported_value(item)
        return
    raise TypeError("only the supported JSON subset is accepted")
