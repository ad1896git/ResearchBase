"""Independent PR-14 governance hash oracles.

This module intentionally does not import ResearchBase production hashing or material builders.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence


def _digest(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def impact_assessment_hash(
    *,
    project_id: str,
    audit_finding_id: str | None,
    assessment_payload: object,
    conclusion: str,
    targets: Sequence[Mapping[str, str | None]],
) -> str:
    rows = [
        {
            "target_type": row["target_type"],
            "target_id": row["target_id"],
            "target_content_hash": row["target_content_hash"],
            "impact_kind": row["impact_kind"],
        }
        for row in targets
    ]
    rows.sort(
        key=lambda row: (
            row["target_type"] or "",
            row["target_id"] or "",
            row["target_content_hash"] is not None,
            row["target_content_hash"] or "",
            row["impact_kind"] or "",
        )
    )
    return _digest(
        {
            "project_id": project_id,
            "audit_finding_id": audit_finding_id,
            "assessment_payload": assessment_payload,
            "conclusion": conclusion,
            "impact_targets": rows,
        }
    )


def correction_record_hash(
    *,
    project_id: str,
    target_type: str,
    target_id: str,
    target_content_hash: str | None,
    correction_type: str,
    corrected_assertion: object,
    reason: str,
) -> str:
    return _digest(
        {
            "project_id": project_id,
            "target_type": target_type,
            "target_id": target_id,
            "target_content_hash": target_content_hash,
            "correction_type": correction_type,
            "corrected_assertion": corrected_assertion,
            "reason": reason,
        }
    )
