"""Experiment specification identity and immutable version semantics for PR-05."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from typing import NewType, Self
from uuid import UUID

from researchbase.domain.organization import ProjectId
from researchbase.domain.research import HypothesisId
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import ContentHash
from researchbase.foundation.ids import ActorId
from researchbase.foundation.time import Clock, to_utc
from researchbase.foundation.versioning import VersionStatus, freeze_material, require_transition

ExperimentSpecId = NewType("ExperimentSpecId", UUID)
ExperimentSpecVersionId = NewType("ExperimentSpecVersionId", UUID)


@dataclass(frozen=True, slots=True)
class ExperimentSpec:
    id: ExperimentSpecId
    project_id: ProjectId
    hypothesis_id: HypothesisId | None
    created_by: ActorId
    created_at: datetime
    current_version_id: ExperimentSpecVersionId | None = None
    row_version: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID) or not isinstance(self.project_id, UUID):
            raise TypeError("experiment spec IDs must be UUID-compatible")
        if self.hypothesis_id is not None and not isinstance(self.hypothesis_id, UUID):
            raise TypeError("hypothesis id must be UUID-compatible")
        if not isinstance(self.created_by, UUID):
            raise TypeError("created_by must be UUID-compatible")
        if self.current_version_id is not None and not isinstance(self.current_version_id, UUID):
            raise TypeError("current version id must be UUID-compatible")
        object.__setattr__(self, "id", ExperimentSpecId(self.id))
        object.__setattr__(self, "project_id", ProjectId(self.project_id))
        if self.hypothesis_id is not None:
            object.__setattr__(self, "hypothesis_id", HypothesisId(self.hypothesis_id))
        object.__setattr__(self, "created_by", ActorId(self.created_by))
        if self.current_version_id is not None:
            object.__setattr__(
                self, "current_version_id", ExperimentSpecVersionId(self.current_version_id)
            )
        object.__setattr__(self, "created_at", to_utc(self.created_at))
        _validate_row_version(self.row_version)


@dataclass(frozen=True, slots=True)
class ExperimentSpecVersion:
    id: ExperimentSpecVersionId
    experiment_spec_id: ExperimentSpecId
    version_number: int
    status: VersionStatus
    title: str
    objective: str
    protocol: object
    planned_metrics: object | None
    seed_policy: object | None
    analysis_plan: object | None
    created_by: ActorId
    created_at: datetime
    content_hash: ContentHash | None = None
    hash_scheme: str | None = None
    frozen_at: datetime | None = None
    row_version: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID) or not isinstance(self.experiment_spec_id, UUID):
            raise TypeError("experiment spec version IDs must be UUID-compatible")
        if not isinstance(self.created_by, UUID):
            raise TypeError("created_by must be UUID-compatible")
        object.__setattr__(self, "id", ExperimentSpecVersionId(self.id))
        object.__setattr__(self, "experiment_spec_id", ExperimentSpecId(self.experiment_spec_id))
        object.__setattr__(self, "created_by", ActorId(self.created_by))
        object.__setattr__(self, "status", VersionStatus(self.status))
        _validate_version_number(self.version_number)
        _validate_text(self.title, "title")
        _validate_text(self.objective, "objective")
        _validate_protocol(self.protocol)
        object.__setattr__(self, "created_at", to_utc(self.created_at))
        if self.frozen_at is not None:
            object.__setattr__(self, "frozen_at", to_utc(self.frozen_at))
        if self.content_hash is not None and not isinstance(self.content_hash, ContentHash):
            object.__setattr__(self, "content_hash", ContentHash(self.content_hash))
        if self.status in {VersionStatus.FROZEN, VersionStatus.SUPERSEDED} and (
            self.content_hash is None or self.hash_scheme is None or self.frozen_at is None
        ):
            raise ValueError("frozen versions require content_hash, hash_scheme, and frozen_at")
        _validate_row_version(self.row_version)

    def material_payload(self) -> dict[str, object | None]:
        """Return the frozen specification material, excluding identity/operational metadata."""
        return {
            "title": self.title,
            "objective": self.objective,
            "protocol": self.protocol,
            "planned_metrics": self.planned_metrics,
            "seed_policy": self.seed_policy,
            "analysis_plan": self.analysis_plan,
        }

    def edit_material(
        self,
        *,
        title: str,
        objective: str,
        protocol: object,
        planned_metrics: object | None,
        seed_policy: object | None,
        analysis_plan: object | None,
    ) -> Self:
        if self.status is not VersionStatus.DRAFT:
            raise ResearchBaseError(ErrorCode.IMMUTABLE_RECORD, "version material is immutable")
        return replace(
            self,
            title=title,
            objective=objective,
            protocol=protocol,
            planned_metrics=planned_metrics,
            seed_policy=seed_policy,
            analysis_plan=analysis_plan,
        )

    def freeze(self, clock: Clock) -> Self:
        result = freeze_material(self.status, self.material_payload(), clock)
        return replace(
            self,
            status=result.status,
            content_hash=result.content_hash,
            hash_scheme=result.hash_scheme,
            frozen_at=result.frozen_at,
        )

    def transition_to(self, target: VersionStatus) -> Self:
        require_transition(self.status, target)
        return replace(self, status=target)


def _validate_text(value: str, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must not be blank")


def _validate_protocol(value: object) -> None:
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValueError("protocol must not be empty")
    if isinstance(value, dict | list | tuple | set) and not value:
        raise ValueError("protocol must not be empty")


def _validate_version_number(value: int) -> None:
    if value < 1:
        raise ValueError("version_number must be positive")


def _validate_row_version(value: int) -> None:
    if value < 1:
        raise ValueError("row_version must be positive")
