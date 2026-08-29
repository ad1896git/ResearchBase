"""Framework-neutral Run provenance closure validation for PR-09."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from researchbase.application.ports import UnitOfWork
from researchbase.domain.claim import ClaimVersionId, calculate_support_set_hash
from researchbase.domain.measurement import Measurement
from researchbase.domain.run import Run, RunId, RunStatus
from researchbase.domain.statistical_result import StatisticalResult
from researchbase.foundation.errors import ErrorCode
from researchbase.foundation.hashing import sha256_canonical_json
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

    def validate_claim_version(self, claim_version_id: UUID) -> ClosureReport:
        with self._uow_factory() as uow:
            return self.validate_claim_version_in_uow(uow, ClaimVersionId(claim_version_id))

    def validate_claim_version_in_uow(
        self, uow: UnitOfWork, claim_version_id: ClaimVersionId
    ) -> ClosureReport:
        violations: list[ClosureViolation] = []
        visited: set[tuple[str, UUID]] = set()
        claim_version = uow.claims.get_version(claim_version_id)
        if claim_version is None:
            return ClosureReport(
                complete=False,
                visited_count=0,
                violations=[
                    ClosureViolation(
                        ErrorCode.NOT_FOUND.value,
                        "ClaimVersion",
                        UUID(str(claim_version_id)),
                        ["claim_version"],
                        "claim version was not found",
                    )
                ],
            )

        claim_version_uuid = UUID(str(claim_version.id))
        visited.add(("ClaimVersion", claim_version_uuid))
        claim = uow.claims.get(claim_version.claim_id)
        if claim is None:
            violations.append(
                ClosureViolation(
                    ErrorCode.NOT_FOUND.value,
                    "Claim",
                    UUID(str(claim_version.claim_id)),
                    ["claim_version", "claim"],
                    "claim was not found",
                )
            )
            claim_project_id = None
        else:
            visited.add(("Claim", UUID(str(claim.id))))
            claim_project_id = claim.project_id

        if claim_version.status not in {VersionStatus.FROZEN, VersionStatus.SUPERSEDED}:
            violations.append(
                ClosureViolation(
                    ErrorCode.VERSION_NOT_FROZEN.value,
                    "ClaimVersion",
                    claim_version_uuid,
                    ["claim_version", "status"],
                    "claim version is not finalized",
                )
            )

        relations = uow.claims.list_evidence(claim_version.id)
        expected_support_hash = calculate_support_set_hash(relations)
        if claim_version.support_set_hash != expected_support_hash:
            violations.append(
                ClosureViolation(
                    "SUPPORT_SET_HASH_MISMATCH",
                    "ClaimVersion",
                    claim_version_uuid,
                    ["claim_version", "support_set_hash"],
                    "support_set_hash does not match persisted evidence semantics",
                )
            )
        expected_content_hash = sha256_canonical_json(claim_version.material_payload())
        if claim_version.content_hash != expected_content_hash:
            violations.append(
                ClosureViolation(
                    "CONTENT_HASH_MISMATCH",
                    "ClaimVersion",
                    claim_version_uuid,
                    ["claim_version", "content_hash"],
                    "content_hash does not match claim material",
                )
            )

        for relation in relations:
            relation_uuid = UUID(str(relation.id))
            visited.add(("EvidenceRelation", relation_uuid))
            relation_path = ["claim_version", "evidence", str(relation.id)]
            if relation.measurement_id is not None:
                measurement = uow.measurements.get(relation.measurement_id)
                self._validate_measurement_source(
                    uow,
                    measurement,
                    relation.measurement_id,
                    claim_project_id,
                    relation_path,
                    visited,
                    violations,
                )
            elif relation.statistical_result_id is not None:
                result = uow.statistical_results.get(relation.statistical_result_id)
                self._validate_statistical_result_source(
                    uow,
                    result,
                    relation.statistical_result_id,
                    claim_project_id,
                    relation_path,
                    visited,
                    violations,
                )

        violations.sort(
            key=lambda item: (
                tuple(item.path),
                item.object_type,
                str(item.object_id),
                item.code,
                item.message,
            )
        )
        return ClosureReport(
            complete=not violations,
            visited_count=len(visited),
            violations=violations,
        )

    def _validate_measurement_source(
        self,
        uow: UnitOfWork,
        measurement: Measurement | None,
        measurement_id: UUID | None,
        claim_project_id: object | None,
        path: list[str],
        visited: set[tuple[str, UUID]],
        violations: list[ClosureViolation],
    ) -> None:
        if measurement is None:
            violations.append(
                ClosureViolation(
                    ErrorCode.NOT_FOUND.value,
                    "Measurement",
                    UUID(str(measurement_id)),
                    [*path, "measurement"],
                    "measurement was not found",
                )
            )
            return
        measurement_uuid = UUID(str(measurement.id))
        visited.add(("Measurement", measurement_uuid))
        run = uow.runs.get(measurement.run_id)
        if run is None:
            violations.append(
                ClosureViolation(
                    ErrorCode.NOT_FOUND.value,
                    "Run",
                    UUID(str(measurement.run_id)),
                    [*path, "measurement", "run"],
                    "measurement run was not found",
                )
            )
        else:
            if claim_project_id is not None and run.project_id != claim_project_id:
                violations.append(
                    ClosureViolation(
                        ErrorCode.REFERENTIAL_INTEGRITY_ERROR.value,
                        "Run",
                        UUID(str(run.id)),
                        [*path, "measurement", "run", "project_id"],
                        "measurement run belongs to a different project",
                    )
                )
            self._record_run_closure(uow, run, path, visited, violations)

        metric = uow.metric_definition_versions.get(measurement.metric_definition_version_id)
        if metric is None:
            violations.append(
                ClosureViolation(
                    ErrorCode.NOT_FOUND.value,
                    "MetricDefinitionVersion",
                    UUID(str(measurement.metric_definition_version_id)),
                    [*path, "measurement", "metric_definition_version"],
                    "metric definition version was not found",
                )
            )
        else:
            metric_uuid = UUID(str(metric.id))
            visited.add(("MetricDefinitionVersion", metric_uuid))
            if metric.status not in {VersionStatus.FROZEN, VersionStatus.SUPERSEDED}:
                violations.append(
                    ClosureViolation(
                        ErrorCode.VERSION_NOT_FROZEN.value,
                        "MetricDefinitionVersion",
                        metric_uuid,
                        [*path, "measurement", "metric_definition_version", "status"],
                        "metric definition version is not finalized",
                    )
                )

    def _validate_statistical_result_source(
        self,
        uow: UnitOfWork,
        result: StatisticalResult | None,
        statistical_result_id: UUID | None,
        claim_project_id: object | None,
        path: list[str],
        visited: set[tuple[str, UUID]],
        violations: list[ClosureViolation],
    ) -> None:
        if result is None:
            violations.append(
                ClosureViolation(
                    ErrorCode.NOT_FOUND.value,
                    "StatisticalResult",
                    UUID(str(statistical_result_id)),
                    [*path, "statistical_result"],
                    "statistical result was not found",
                )
            )
            return
        result_uuid = UUID(str(result.id))
        visited.add(("StatisticalResult", result_uuid))
        if claim_project_id is not None and result.project_id != claim_project_id:
            violations.append(
                ClosureViolation(
                    ErrorCode.REFERENTIAL_INTEGRITY_ERROR.value,
                    "StatisticalResult",
                    result_uuid,
                    [*path, "statistical_result", "project_id"],
                    "statistical result belongs to a different project",
                )
            )
        inputs = uow.statistical_results.list_inputs(result.id)
        if not inputs:
            violations.append(
                ClosureViolation(
                    "STATISTICAL_RESULT_INPUT_MISSING",
                    "StatisticalResult",
                    result_uuid,
                    [*path, "statistical_result", "inputs"],
                    "statistical result has no measurement inputs",
                )
            )
        for input_edge in inputs:
            visited.add(("StatisticalResultInput", UUID(str(input_edge.measurement_id))))
            measurement = uow.measurements.get(input_edge.measurement_id)
            self._validate_measurement_source(
                uow,
                measurement,
                input_edge.measurement_id,
                result.project_id,
                [*path, "statistical_result", "inputs", str(input_edge.measurement_id)],
                visited,
                violations,
            )

    def _record_run_closure(
        self,
        uow: UnitOfWork,
        run: Run,
        path: list[str],
        visited: set[tuple[str, UUID]],
        violations: list[ClosureViolation],
    ) -> None:
        visited.add(("Run", UUID(str(run.id))))
        report = self.validate_run_in_uow(uow, run.id)
        prefix = [*path, "measurement", "run"]
        for violation in report.violations:
            violations.append(
                ClosureViolation(
                    violation.code,
                    violation.object_type,
                    violation.object_id,
                    [*prefix, *violation.path],
                    violation.message,
                )
            )
        spec = uow.experiment_specs.get_version(run.experiment_spec_version_id)
        if spec is not None:
            visited.add(("ExperimentSpecVersion", UUID(str(spec.id))))
        for item in uow.runs.list_dataset_inputs(run.id):
            snapshot = uow.dataset_snapshots.get(item.dataset_snapshot_id)
            if snapshot is not None:
                visited.add(("DatasetSnapshot", UUID(str(snapshot.id))))
        for item in uow.runs.list_artifact_inputs(run.id):
            artifact = uow.artifact_versions.get(item.artifact_version_id)
            if artifact is not None:
                visited.add(("ArtifactVersion", UUID(str(artifact.id))))

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
