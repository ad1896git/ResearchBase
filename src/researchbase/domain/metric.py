"""Metric definition identity and immutable version semantics for PR-08."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from typing import NewType
from uuid import UUID

from researchbase.domain.organization import ProjectId
from researchbase.foundation.canonical_json import canonical_json_bytes
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.frozen_json import freeze_json, thaw_json
from researchbase.foundation.hashing import ContentHash
from researchbase.foundation.ids import ActorId
from researchbase.foundation.time import Clock, to_utc
from researchbase.foundation.versioning import (
    VersionStatus,
    freeze_material,
    require_transition,
    validate_version_hash,
)

MetricDefinitionId = NewType("MetricDefinitionId", UUID)
MetricDefinitionVersionId = NewType("MetricDefinitionVersionId", UUID)


@dataclass(frozen=True, slots=True)
class MetricDefinition:
    id: MetricDefinitionId
    project_id: ProjectId | None
    name: str
    created_by: ActorId
    created_at: datetime
    current_version_id: MetricDefinitionVersionId | None = None
    row_version: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID):
            raise TypeError("metric definition id must be UUID-compatible")
        if self.project_id is not None and not isinstance(self.project_id, UUID):
            raise TypeError("project id must be UUID-compatible")
        if not isinstance(self.created_by, UUID):
            raise TypeError("created_by must be UUID-compatible")
        if self.current_version_id is not None and not isinstance(self.current_version_id, UUID):
            raise TypeError("current version id must be UUID-compatible")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name must not be blank")
        object.__setattr__(self, "id", MetricDefinitionId(self.id))
        if self.project_id is not None:
            object.__setattr__(self, "project_id", ProjectId(self.project_id))
        object.__setattr__(self, "created_by", ActorId(self.created_by))
        if self.current_version_id is not None:
            object.__setattr__(
                self,
                "current_version_id",
                MetricDefinitionVersionId(self.current_version_id),
            )
        object.__setattr__(self, "created_at", to_utc(self.created_at))
        if self.row_version < 1:
            raise ValueError("row_version must be positive")


@dataclass(frozen=True, slots=True)
class MetricDefinitionVersion:
    id: MetricDefinitionVersionId
    metric_definition_id: MetricDefinitionId
    version_number: int
    status: VersionStatus
    definition: object
    unit: str | None
    aggregation: str | None
    created_by: ActorId
    created_at: datetime
    content_hash: ContentHash | None = None
    hash_scheme: str | None = None
    frozen_at: datetime | None = None
    row_version: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID) or not isinstance(self.metric_definition_id, UUID):
            raise TypeError("metric definition version IDs must be UUID-compatible")
        if not isinstance(self.created_by, UUID):
            raise TypeError("created_by must be UUID-compatible")
        object.__setattr__(self, "id", MetricDefinitionVersionId(self.id))
        object.__setattr__(
            self, "metric_definition_id", MetricDefinitionId(self.metric_definition_id)
        )
        object.__setattr__(self, "created_by", ActorId(self.created_by))
        object.__setattr__(self, "status", VersionStatus(self.status))
        if self.version_number < 1:
            raise ValueError("version_number must be positive")
        object.__setattr__(self, "created_at", to_utc(self.created_at))
        if self.frozen_at is not None:
            object.__setattr__(self, "frozen_at", to_utc(self.frozen_at))
        self._validate_optional_text(self.unit, "unit")
        self._validate_optional_text(self.aggregation, "aggregation")
        try:
            frozen_definition = freeze_json(self.definition)
        except (TypeError, ValueError) as exc:
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR,
                "metric definition material is not valid canonical JSON",
                {"field": "definition"},
            ) from exc
        object.__setattr__(self, "definition", frozen_definition)
        object.__setattr__(
            self,
            "content_hash",
            validate_version_hash(
                self.status,
                self.material_payload(),
                self.content_hash,
                self.hash_scheme,
                self.frozen_at,
            ),
        )
        if self.row_version < 1:
            raise ValueError("row_version must be positive")
        self.validate_material()

    @staticmethod
    def _validate_optional_text(value: str | None, field: str) -> None:
        if value is not None and (not isinstance(value, str) or len(value) > 64):
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR,
                f"{field} must be a string of at most 64 characters",
                {"field": field},
            )

    def material_payload(self) -> dict[str, object | None]:
        return {
            "definition": thaw_json(self.definition),
            "unit": self.unit,
            "aggregation": self.aggregation,
        }

    def validate_material(self) -> None:
        if self.definition is None:
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR,
                "definition must not be null",
                {"field": "definition"},
            )
        try:
            canonical_json_bytes(self.material_payload())
        except (TypeError, ValueError) as exc:
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR,
                "metric definition material is not valid canonical JSON",
                {"field": "definition"},
            ) from exc

    def edit_material(
        self, *, definition: object, unit: str | None, aggregation: str | None
    ) -> MetricDefinitionVersion:
        if self.status is not VersionStatus.DRAFT:
            raise ResearchBaseError(ErrorCode.IMMUTABLE_RECORD, "version material is immutable")
        candidate = replace(self, definition=definition, unit=unit, aggregation=aggregation)
        candidate.validate_material()
        return candidate

    def freeze(self, clock: Clock) -> MetricDefinitionVersion:
        self.validate_material()
        result = freeze_material(self.status, self.material_payload(), clock)
        return replace(
            self,
            status=result.status,
            content_hash=result.content_hash,
            hash_scheme=result.hash_scheme,
            frozen_at=result.frozen_at,
        )

    def transition_to(self, target: VersionStatus) -> MetricDefinitionVersion:
        require_transition(self.status, target)
        return replace(self, status=target)
