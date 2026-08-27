"""Framework-neutral Run provenance closure validation for PR-09."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from researchbase.application.ports import UnitOfWork
from researchbase.domain.run import Run, RunId, RunStatus
from researchbase.foundation.errors import ErrorCode
from researchbase.foundation.versioning import VersionStatus


@dataclass(frozen=True, slots=True)
class ClosureViolation:
    code: str
    object_type: str
    object_id: UUID
    path: list[str]
    message: str


@dataclass(frozen=True, slots=True)
class ClosureReport:
    complete: bool
    visited_count: int
    violations: list[ClosureViolation]


class ProvenanceClosureValidator:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def validate_run(self, run_id: UUID) -> ClosureReport:
        with self._uow_factory() as uow:
            return self.validate_run_in_uow(uow, RunId(run_id))

    def validate_run_in_uow(self, uow: UnitOfWork, run_id: RunId) -> ClosureReport:
        violations: list[ClosureViolation] = []
        visited: set[tuple[str, UUID]] = set()
        run = uow.runs.get(run_id)
        if run is None:
            return ClosureReport(
                complete=False,
                visited_count=0,
                violations=[
                    ClosureViolation(
                        ErrorCode.NOT_FOUND.value,
                        "Run",
                        UUID(str(run_id)),
                        ["run"],
                        "run was not found",
                    )
                ],
            )
        visited.add(("Run", UUID(str(run.id))))
        self._check_run_state(run, violations)

        spec = uow.experiment_specs.get_version(run.experiment_spec_version_id)
        if spec is None:
            violations.append(
                ClosureViolation(
                    ErrorCode.NOT_FOUND.value,
                    "ExperimentSpecVersion",
                    UUID(str(run.experiment_spec_version_id)),
                    ["run", "experiment_spec_version"],
                    "experiment spec version was not found",
                )
            )
        else:
            visited.add(("ExperimentSpecVersion", UUID(str(spec.id))))
            if spec.status not in {VersionStatus.FROZEN, VersionStatus.SUPERSEDED}:
                violations.append(
                    ClosureViolation(
                        ErrorCode.VERSION_NOT_FROZEN.value,
                        "ExperimentSpecVersion",
                        UUID(str(spec.id)),
                        ["run", "experiment_spec_version"],
                        "experiment spec version is not frozen",
                    )
                )

        for item in uow.runs.list_dataset_inputs(run.id):
            snapshot = uow.dataset_snapshots.get(item.dataset_snapshot_id)
            if snapshot is None:
                violations.append(
                    ClosureViolation(
                        ErrorCode.NOT_FOUND.value,
                        "DatasetSnapshot",
                        UUID(str(item.dataset_snapshot_id)),
                        ["run", "dataset_inputs", item.role.value],
                        "dataset snapshot was not found",
                    )
                )
            else:
                visited.add(("DatasetSnapshot", UUID(str(snapshot.id))))

        for item in uow.runs.list_artifact_inputs(run.id):
            version = uow.artifact_versions.get(item.artifact_version_id)
            if version is None:
                violations.append(
                    ClosureViolation(
                        ErrorCode.NOT_FOUND.value,
                        "ArtifactVersion",
                        UUID(str(item.artifact_version_id)),
                        ["run", "artifact_inputs", item.role.value],
                        "artifact version was not found",
                    )
                )
            else:
                visited.add(("ArtifactVersion", UUID(str(version.id))))
                if version.status not in {VersionStatus.FROZEN, VersionStatus.SUPERSEDED}:
                    violations.append(
                        ClosureViolation(
                            ErrorCode.VERSION_NOT_FROZEN.value,
                            "ArtifactVersion",
                            UUID(str(version.id)),
                            ["run", "artifact_inputs", item.role.value],
                            "artifact version is not frozen",
                        )
                    )

        violations.sort(
            key=lambda item: (
                tuple(item.path),
                item.object_type,
                str(item.object_id),
                item.code,
            )
        )
        return ClosureReport(
            complete=not violations,
            visited_count=len(visited),
            violations=violations,
        )

    @staticmethod
    def _check_run_state(run: Run, violations: list[ClosureViolation]) -> None:
        if run.status is not RunStatus.PLANNED and run.inputs_sealed_at is None:
            violations.append(
                ClosureViolation(
                    ErrorCode.VALIDATION_ERROR.value,
                    "Run",
                    UUID(str(run.id)),
                    ["run", "inputs_sealed_at"],
                    "running and terminal runs must have sealed inputs",
                )
            )
