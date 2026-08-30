"""Independent PR-12 support-set canonicalization and hashing oracle."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence

_SEMANTIC_FIELDS = {
    "source_type",
    "source_id",
    "relation_type",
    "qualification",
}


def independent_support_set_hash(rows: Sequence[Mapping[str, str | None]]) -> str:
    """Hash literal semantic rows without using ResearchBase production helpers."""
    semantic_rows: list[dict[str, str | None]] = []
    for row in rows:
        if set(row) != _SEMANTIC_FIELDS:
            raise ValueError("support-set oracle rows must contain exactly the semantic fields")
        source_type = row["source_type"]
        source_id = row["source_id"]
        relation_type = row["relation_type"]
        qualification = row["qualification"]
        if not isinstance(source_type, str):
            raise TypeError("source_type must be a string")
        if not isinstance(source_id, str):
            raise TypeError("source_id must be a string")
        if not isinstance(relation_type, str):
            raise TypeError("relation_type must be a string")
        if qualification is not None and not isinstance(qualification, str):
            raise TypeError("qualification must be null or a string")
        semantic_rows.append(
            {
                "source_type": source_type,
                "source_id": source_id,
                "relation_type": relation_type,
                "qualification": qualification,
            }
        )

    semantic_rows.sort(
        key=lambda row: (
            row["source_type"],
            row["source_id"],
            row["relation_type"],
            row["qualification"] is not None,
            row["qualification"] or "",
        )
    )
    canonical_bytes = json.dumps(
        semantic_rows,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical_bytes).hexdigest()
