"""Run state and exact provenance input edge value objects for PR-09."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from typing import NewType
from uuid import UUID

from researchbase.domain.artifact import ArtifactVersionId
from researchbase.domain.evidence import DatasetSnapshotId
from researchbase.domain.experiment import ExperimentSpecVersionId
from researchbase.domain.organization import ProjectId
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.ids import ActorId
from researchbase.foundation.time import Clock, to_utc

RunId = NewType("RunId", UUID)


class RunStatus(StrEnum):
    PLANNED = "PLANNED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class DatasetInputRole(StrEnum):
    TRAIN = "train"
    VALIDATION = "validation"
    TEST = "test"
    CALIBRATION = "calibration"
    AUXILIARY = "auxiliary"
    OTHER = "other"


class ArtifactInputRole(StrEnum):
    SOURCE_CODE = "source_code"
    MODEL = "model"
    CHECKPOINT = "checkpoint"
    CONFIGURATION = "configuration"
    ENVIRONMENT_MANIFEST = "environment_manifest"
    SCRIPT = "script"
    DEPENDENCY_LOCK = "dependency_lock"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class Run:
    id: RunId
    project_id: ProjectId
    experiment_spec_version_id: ExperimentSpecVersionId
    run_type: str
    status: RunStatus
    created_by: ActorId
    created_at: datetime
    inputs_sealed_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    exit_code: int | None = None
    failure_reason: str | None = None
    row_version: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID):
            raise TypeError("run id must be UUID-compatible")
        if not isinstance(self.project_id, UUID):
            raise TypeError("project id must be UUID-compatible")
        if not isinstance(self.experiment_spec_version_id, UUID):
            raise TypeError("experiment spec version id must be UUID-compatible")
        if not isinstance(self.created_by, UUID):
            raise TypeError("created_by must be UUID-compatible")
        if (
            not isinstance(self.run_type, str)
            or not self.run_type.strip()
            or len(self.run_type) > 32
        ):
            raise ValueError("run_type must be a non-empty string of at most 32 characters")
        object.__setattr__(self, "id", RunId(self.id))
        object.__setattr__(self, "project_id", ProjectId(self.project_id))
        object.__setattr__(
            self,
            "experiment_spec_version_id",
            ExperimentSpecVersionId(self.experiment_spec_version_id),
        )
        object.__setattr__(self, "status", RunStatus(self.status))
        object.__setattr__(self, "created_by", ActorId(self.created_by))
        object.__setattr__(self, "created_at", to_utc(self.created_at))
        for field in ("inputs_sealed_at", "started_at", "finished_at"):
            value = getattr(self, field)
            if value is not None:
                object.__setattr__(self, field, to_utc(value))
        if self.exit_code is not None and (
            isinstance(self.exit_code, bool) or not isinstance(self.exit_code, int)
        ):
            raise ValueError("exit_code must be an integer or null")
        if self.status is RunStatus.PLANNED and self.inputs_sealed_at is not None:
            raise ValueError("planned runs cannot have sealed inputs")
        if self.status is not RunStatus.PLANNED and self.inputs_sealed_at is None:
            raise ValueError("non-planned runs require sealed inputs")
        if (
            isinstance(self.row_version, bool)
            or not isinstance(self.row_version, int)
            or self.row_version < 1
        ):
            raise ValueError("row_version must be positive")

    def start(self, clock: Clock) -> Run:
        if self.status is not RunStatus.PLANNED:
            raise ResearchBaseError(
                ErrorCode.INVALID_STATE_TRANSITION,
                "only planned runs can start",
            )
        now = to_utc(clock.now())
        return replace(self, status=RunStatus.RUNNING, inputs_sealed_at=now, started_at=now)

    def finish(self, outcome: RunStatus | str, clock: Clock) -> Run:
        if self.status is not RunStatus.RUNNING:
            raise ResearchBaseError(
                ErrorCode.INVALID_STATE_TRANSITION,
                "only running runs can finish",
            )
        try:
            target = RunStatus(outcome)
        except ValueError as exc:
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR,
                "run outcome must be SUCCEEDED, FAILED, or CANCELLED",
                {"field": "outcome"},
            ) from exc
        if target not in {RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED}:
            raise ResearchBaseError(
                ErrorCode.INVALID_STATE_TRANSITION,
                "running runs can only finish to a terminal status",
            )
        return replace(self, status=target, finished_at=to_utc(clock.now()))


@dataclass(frozen=True, slots=True)
class RunDatasetInput:
    run_id: RunId
    dataset_snapshot_id: DatasetSnapshotId
    role: DatasetInputRole
    ordinal: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.run_id, UUID) or not isinstance(self.dataset_snapshot_id, UUID):
            raise TypeError("run dataset input IDs must be UUID-compatible")
        object.__setattr__(self, "run_id", RunId(self.run_id))
        object.__setattr__(self, "dataset_snapshot_id", DatasetSnapshotId(self.dataset_snapshot_id))
        object.__setattr__(self, "role", DatasetInputRole(self.role))
        if isinstance(self.ordinal, bool) or not isinstance(self.ordinal, int) or self.ordinal < 0:
            raise ValueError("ordinal must be a non-negative integer")


@dataclass(frozen=True, slots=True)
class RunArtifactInput:
    run_id: RunId
    artifact_version_id: ArtifactVersionId
    role: ArtifactInputRole
    ordinal: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.run_id, UUID) or not isinstance(self.artifact_version_id, UUID):
            raise TypeError("run artifact input IDs must be UUID-compatible")
        object.__setattr__(self, "run_id", RunId(self.run_id))
        object.__setattr__(self, "artifact_version_id", ArtifactVersionId(self.artifact_version_id))
        object.__setattr__(self, "role", ArtifactInputRole(self.role))
        if isinstance(self.ordinal, bool) or not isinstance(self.ordinal, int) or self.ordinal < 0:
            raise ValueError("ordinal must be a non-negative integer")
