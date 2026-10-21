"""Literal frozen R2/R3 literature evidence and support hash material.

This quotation slice uses R3 QUOTATION/MODERATE values and the approved RULE
extraction method for deterministic span selection; HUMAN remains hash-compatible.
Verification state never changes the evidence's content hash.
"""

from __future__ import annotations

from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import sha256_canonical_json

RELATIONS = frozenset(
    {"SUPPORTS", "CONTRADICTS", "QUALIFIES", "MOTIVATES", "PRIOR_ART", "CONTEXTUALIZES"}
)
TRANSITIONS = {
    "UNREVIEWED": {"VERIFIED", "DISPUTED", "REJECTED"},
    "VERIFIED": {"DISPUTED"},
    "DISPUTED": {"VERIFIED", "REJECTED"},
    "REJECTED": set(),
}


def ref(kind, row):
    return {"type": kind, "id": str(row["id"]), "content_hash": row["content_hash"]}


def evidence_material(row, source):
    return {
        "type": "LiteratureEvidence",
        "material_version": 1,
        "project_id": str(row["project_id"]),
        "source_version": ref("SourceVersion", source),
        **{
            key: row[key]
            for key in (
                "evidence_type",
                "locator",
                "extracted_statement",
                "normalized_assertion",
                "extraction_method",
                "confidence",
            )
        },
    }


def support_material(inputs):
    seen = set()
    ordinals = set()
    for item in inputs:
        relation = item["relation_type"]
        evidence = item["literature_evidence"]
        key = (evidence.get("id"), relation)
        ordinal = item["ordinal"]
        if (
            relation not in RELATIONS
            or key in seen
            or type(ordinal) is not int
            or ordinal < 0
            or ordinal in ordinals
        ):
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR, "invalid/duplicate literature relation"
            )
        seen.add(key)
        ordinals.add(ordinal)
    return {
        "type": "LiteratureSupportSnapshotSupportSet",
        "material_version": 1,
        "literature_inputs": sorted(
            inputs, key=lambda x: (x["ordinal"], x["literature_evidence"]["id"])
        ),
    }


def snapshot_material(row, target, previous):
    return {
        "type": "LiteratureSupportSnapshot",
        "material_version": 1,
        "project_id": str(row["project_id"]),
        "target": target,
        "snapshot_number": row["snapshot_number"],
        "previous_snapshot": ref("LiteratureSupportSnapshot", previous) if previous else None,
        "literature_support_set_hash": row["literature_support_set_hash"],
    }


def digest(payload):
    return str(sha256_canonical_json(payload))
