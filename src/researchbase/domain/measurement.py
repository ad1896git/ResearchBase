"""Immutable Measurement scientific records for PR-10."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import NewType
from uuid import UUID

from researchbase.domain.metric import MetricDefinitionVersionId
from researchbase.domain.run import RunId
from researchbase.foundation.canonical_json import canonical_json_bytes
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.frozen_json import freeze_json, thaw_json
from researchbase.foundation.hashing import ContentHash, sha256_canonical_json
from researchbase.foundation.ids import ActorId
from researchbase.foundation.time import to_utc

MeasurementId = NewType("MeasurementId", UUID)


@dataclass(frozen=True, slots=True)
class Measurement:
    """A single immutable scientific measurement bound to exact provenance."""

    id: MeasurementId
    run_id: RunId
    metric_definition_version_id: MetricDefinitionVersionId
    numeric_value: float | None
    structured_value: object | None
    unit: str | None
    evaluation_scope: object | None
    content_hash: ContentHash
    created_by: ActorId
    created_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID):
            raise TypeError("measurement id must be UUID-compatible")
        if not isinstance(self.run_id, UUID):
            raise TypeError("run id must be UUID-compatible")
        if not isinstance(self.metric_definition_version_id, UUID):
            raise TypeError("metric definition version id must be UUID-compatible")
        if not isinstance(self.created_by, UUID):
            raise TypeError("created_by must be UUID-compatible")

        object.__setattr__(self, "id", MeasurementId(self.id))
        object.__setattr__(self, "run_id", RunId(self.run_id))
        object.__setattr__(
            self,
            "metric_definition_version_id",
            MetricDefinitionVersionId(self.metric_definition_version_id),
        )
        object.__setattr__(self, "created_by", ActorId(self.created_by))
        object.__setattr__(self, "created_at", to_utc(self.created_at))

        for field in ("structured_value", "evaluation_scope"):
            value = getattr(self, field)
            if value is None:
                continue
            try:
                frozen_value = freeze_json(value)
            except (TypeError, ValueError) as exc:
                raise ResearchBaseError(
                    ErrorCode.VALIDATION_ERROR,
                    f"{field} is not valid canonical JSON",
                    {"field": field},
                ) from exc
            object.__setattr__(self, field, frozen_value)

        self._validate_value_representation()
        self._validate_unit()
        self._validate_json_fields()
        try:
            content_hash = ContentHash(self.content_hash)
        except (TypeError, ValueError) as exc:
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR,
                "content_hash must be a valid SHA-256 hex digest",
                {"field": "content_hash"},
            ) from exc
        object.__setattr__(self, "content_hash", content_hash)
        expected = sha256_canonical_json(self.material_payload())
        if content_hash != expected:
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR,
                "content_hash does not match measurement material",
                {"field": "content_hash"},
            )

    def _validate_value_representation(self) -> None:
        if (self.numeric_value is None) == (self.structured_value is None):
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR,
                "exactly one of numeric_value and structured_value is required",
                {"field": "value"},
            )
        if self.numeric_value is not None:
            if isinstance(self.numeric_value, bool) or not isinstance(
                self.numeric_value, int | float
            ):
                raise ResearchBaseError(
                    ErrorCode.VALIDATION_ERROR,
                    "numeric_value must be a number",
                    {"field": "numeric_value"},
                )
            try:
                numeric_value = float(self.numeric_value)
            except OverflowError as exc:
                raise ResearchBaseError(
                    ErrorCode.VALIDATION_ERROR,
                    "numeric_value is not representable as DOUBLE PRECISION",
                    {"field": "numeric_value"},
                ) from exc
            if not math.isfinite(numeric_value):
                raise ResearchBaseError(
                    ErrorCode.VALIDATION_ERROR,
                    "numeric_value must be finite",
                    {"field": "numeric_value"},
                )
            object.__setattr__(self, "numeric_value", numeric_value)
        elif not isinstance(thaw_json(self.structured_value), dict | list):
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR,
                "structured_value must be a JSON object or array",
                {"field": "structured_value"},
            )

    def _validate_unit(self) -> None:
        if self.unit is not None and (not isinstance(self.unit, str) or len(self.unit) > 64):
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR,
                "unit must be a string of at most 64 characters",
                {"field": "unit"},
            )

    def _validate_json_fields(self) -> None:
        try:
            canonical_json_bytes(
                thaw_json(self.structured_value) if self.structured_value is not None else None
            )
            if self.evaluation_scope is not None:
                if not isinstance(thaw_json(self.evaluation_scope), dict):
                    raise TypeError("evaluation_scope must be a JSON object")
                canonical_json_bytes(thaw_json(self.evaluation_scope))
        except (TypeError, ValueError) as exc:
            field = "structured_value" if self.structured_value is not None else "evaluation_scope"
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR,
                f"{field} is not valid canonical JSON",
                {"field": field},
            ) from exc

    def material_payload(self) -> dict[str, object | None]:
        """Return the exact AD-PR10-001 hash material, in semantic form."""
        return {
            "run_id": str(self.run_id),
            "metric_definition_version_id": str(self.metric_definition_version_id),
            "numeric_value": self.numeric_value,
            "structured_value": (
                thaw_json(self.structured_value) if self.structured_value is not None else None
            ),
            "unit": self.unit,
            "evaluation_scope": (
                thaw_json(self.evaluation_scope) if self.evaluation_scope is not None else None
            ),
        }
