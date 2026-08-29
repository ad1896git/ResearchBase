"""Immutable StatisticalResult records and their exact Measurement inputs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import NewType
from uuid import UUID

from researchbase.domain.measurement import MeasurementId
from researchbase.domain.organization import ProjectId
from researchbase.foundation.canonical_json import canonical_json_bytes
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import ContentHash, sha256_canonical_json
from researchbase.foundation.ids import ActorId
from researchbase.foundation.time import to_utc

StatisticalResultId = NewType("StatisticalResultId", UUID)


@dataclass(frozen=True, slots=True)
class StatisticalResult:
    """An immutable statistical result bound to a project's Measurements."""

    id: StatisticalResultId
    project_id: ProjectId
    analysis_type: str
    result_payload: object
    analysis_definition: object
    content_hash: ContentHash
    created_by: ActorId
    created_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID):
            raise TypeError("statistical result id must be UUID-compatible")
        if not isinstance(self.project_id, UUID):
            raise TypeError("project id must be UUID-compatible")
        if not isinstance(self.created_by, UUID):
            raise TypeError("created_by must be UUID-compatible")
        if not isinstance(self.analysis_type, str) or not self.analysis_type.strip():
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR,
                "analysis_type must be a non-blank string of at most 64 characters",
                {"field": "analysis_type"},
            )
        if len(self.analysis_type) > 64:
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR,
                "analysis_type must be a non-blank string of at most 64 characters",
                {"field": "analysis_type"},
            )

        object.__setattr__(self, "id", StatisticalResultId(self.id))
        object.__setattr__(self, "project_id", ProjectId(self.project_id))
        object.__setattr__(self, "created_by", ActorId(self.created_by))
        object.__setattr__(self, "created_at", to_utc(self.created_at))
        try:
            canonical_json_bytes(self.result_payload)
            canonical_json_bytes(self.analysis_definition)
        except (TypeError, ValueError) as exc:
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR,
                "statistical result material is not valid canonical JSON",
                {"field": "material"},
            ) from exc
        try:
            content_hash = ContentHash(self.content_hash)
        except (TypeError, ValueError) as exc:
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR,
                "content_hash must be a valid SHA-256 hex digest",
                {"field": "content_hash"},
            ) from exc
        object.__setattr__(self, "content_hash", content_hash)
        if content_hash != sha256_canonical_json(self.material_payload()):
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR,
                "content_hash does not match statistical result material",
                {"field": "content_hash"},
            )

    def material_payload(self) -> dict[str, object]:
        """Return the exact AD-PR11-001 content-hash material."""
        return {
            "analysis_type": self.analysis_type,
            "result_payload": self.result_payload,
            "analysis_definition": self.analysis_definition,
        }


@dataclass(frozen=True, slots=True)
class StatisticalResultInput:
    """An immutable edge from a StatisticalResult to one Measurement."""

    statistical_result_id: StatisticalResultId
    measurement_id: MeasurementId
    input_role: str = "input"
    ordinal: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.statistical_result_id, UUID):
            raise TypeError("statistical result id must be UUID-compatible")
        if not isinstance(self.measurement_id, UUID):
            raise TypeError("measurement id must be UUID-compatible")
        if not isinstance(self.input_role, str) or not self.input_role or len(self.input_role) > 32:
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR,
                "input_role must be a non-blank string of at most 32 characters",
                {"field": "input_role"},
            )
        if isinstance(self.ordinal, bool) or not isinstance(self.ordinal, int) or self.ordinal < 0:
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR,
                "ordinal must be a non-negative integer",
                {"field": "ordinal"},
            )
        object.__setattr__(
            self, "statistical_result_id", StatisticalResultId(self.statistical_result_id)
        )
        object.__setattr__(self, "measurement_id", MeasurementId(self.measurement_id))
