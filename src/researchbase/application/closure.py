"""Framework-neutral Run provenance closure validation for PR-09."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import UUID

from researchbase.application.ports import UnitOfWork
from researchbase.domain.claim import ClaimVersionId, calculate_support_set_hash
from researchbase.domain.measurement import Measurement
from researchbase.domain.run import Run, RunId, RunStatus
from researchbase.domain.statistical_result import StatisticalResult
from researchbase.foundation.errors import ErrorCode
from researchbase.foundation.hashing import sha256_canonical_json
from researchbase.foundation.versioning import VersionStatus


class BatchLookupState(Enum):
    FOUND = "found"
    MISSING = "missing"
    NEVER_REQUESTED = "never_requested"


@dataclass(frozen=True, slots=True)
class BatchLookup[T]:
    """Explicit membership for one bounded request-local batch."""

    values: dict[UUID, T] = field(default_factory=dict)
    requested_ids: frozenset[UUID] = frozenset()

    def __post_init__(self) -> None:
        if not self.values.keys() <= self.requested_ids:
            raise ValueError("values must be a subset of requested_ids")

    @property
    def missing_ids(self) -> frozenset[UUID]:
        return self.requested_ids - self.values.keys()

    def resolve(self, key: object) -> tuple[BatchLookupState, T | None]:
        normalized = UUID(str(key))
        if normalized not in self.requested_ids:
            return BatchLookupState.NEVER_REQUESTED, None
        value = self.values.get(normalized)
        if value is None:
            return BatchLookupState.MISSING, None
        return BatchLookupState.FOUND, value


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


@dataclass(slots=True)
class ClosureEvaluationContext:
    """Request-local typed read cache shared by one trace transaction."""

    measurements: BatchLookup[Any] = field(default_factory=lambda: BatchLookup[Any]())
    statistical_results: BatchLookup[Any] = field(default_factory=lambda: BatchLookup[Any]())
    statistical_inputs: BatchLookup[list[Any]] = field(
        default_factory=lambda: BatchLookup[list[Any]]()
    )
    runs: BatchLookup[Run] = field(default_factory=lambda: BatchLookup[Run]())
    metric_versions: BatchLookup[Any] = field(default_factory=lambda: BatchLookup[Any]())
    spec_versions: BatchLookup[Any] = field(default_factory=lambda: BatchLookup[Any]())
    dataset_inputs: BatchLookup[list[Any]] = field(default_factory=lambda: BatchLookup[list[Any]]())
    artifact_inputs: BatchLookup[list[Any]] = field(
        default_factory=lambda: BatchLookup[list[Any]]()
    )
    dataset_snapshots: BatchLookup[Any] = field(default_factory=lambda: BatchLookup[Any]())
    artifact_versions: BatchLookup[Any] = field(default_factory=lambda: BatchLookup[Any]())
    spec_owners: BatchLookup[Any] = field(default_factory=lambda: BatchLookup[Any]())
    dataset_owners: BatchLookup[Any] = field(default_factory=lambda: BatchLookup[Any]())
    artifact_owners: BatchLookup[Any] = field(default_factory=lambda: BatchLookup[Any]())
    metric_owners: BatchLookup[Any] = field(default_factory=lambda: BatchLookup[Any]())
    run_reports: dict[UUID, ClosureReport] = field(default_factory=dict)


def _context_incomplete(
    object_type: str,
    object_id: object,
    path: list[str],
) -> ClosureViolation:
    return ClosureViolation(
        "PROVENANCE_CONTEXT_INCOMPLETE",
        object_type,
        UUID(str(object_id)),
        path,
        f"{object_type} was referenced but never requested by the closure batch",
    )


class ProvenanceClosureValidator:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def validate_run(self, run_id: UUID) -> ClosureReport:
        with self._uow_factory() as uow:
            uow.begin_formal_read()
            return self.validate_run_in_uow(uow, RunId(run_id))

    def validate_claim_version(self, claim_version_id: UUID) -> ClosureReport:
        with self._uow_factory() as uow:
            uow.begin_formal_read()
            return self.validate_claim_version_in_uow(uow, ClaimVersionId(claim_version_id))

    def validate_claim_version_in_uow(
        self,
        uow: UnitOfWork,
        claim_version_id: ClaimVersionId,
        context: ClosureEvaluationContext | None = None,
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
                if context is None:
                    measurement = uow.measurements.get(relation.measurement_id)
                else:
                    state, measurement = context.measurements.resolve(relation.measurement_id)
                    if state is BatchLookupState.NEVER_REQUESTED:
                        violations.append(
                            _context_incomplete(
                                "Measurement",
                                relation.measurement_id,
                                [*relation_path, "measurement"],
                            )
                        )
                        continue
                self._validate_measurement_source(
                    uow,
                    measurement,
                    relation.measurement_id,
                    claim_project_id,
                    relation_path,
                    visited,
                    violations,
                    context,
                )
            elif relation.statistical_result_id is not None:
                if context is None:
                    result = uow.statistical_results.get(relation.statistical_result_id)
                else:
                    state, result = context.statistical_results.resolve(
                        relation.statistical_result_id
                    )
                    if state is BatchLookupState.NEVER_REQUESTED:
                        violations.append(
                            _context_incomplete(
                                "StatisticalResult",
                                relation.statistical_result_id,
                                [*relation_path, "statistical_result"],
                            )
                        )
                        continue
                self._validate_statistical_result_source(
                    uow,
                    result,
                    relation.statistical_result_id,
                    claim_project_id,
                    relation_path,
                    visited,
                    violations,
                    context,
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
        context: ClosureEvaluationContext | None = None,
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
        run_context_incomplete = False
        if context is None:
            run = uow.runs.get(measurement.run_id)
        else:
            state, run = context.runs.resolve(measurement.run_id)
            if state is BatchLookupState.NEVER_REQUESTED:
                violations.append(
                    _context_incomplete("Run", measurement.run_id, [*path, "measurement", "run"])
                )
                run = None
                run_context_incomplete = True
        if run is None:
            if not run_context_incomplete:
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
            self._record_run_closure(uow, run, path, visited, violations, context)

        metric_context_incomplete = False
        if context is None:
            metric = uow.metric_definition_versions.get(measurement.metric_definition_version_id)
        else:
            state, metric = context.metric_versions.resolve(
                measurement.metric_definition_version_id
            )
            if state is BatchLookupState.NEVER_REQUESTED:
                violations.append(
                    _context_incomplete(
                        "MetricDefinitionVersion",
                        measurement.metric_definition_version_id,
                        [*path, "measurement", "metric_definition_version"],
                    )
                )
                metric = None
                metric_context_incomplete = True
        if metric is None:
            if not metric_context_incomplete:
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
            self._owner(
                uow.metric_definitions,
                context.metric_owners if context else None,
                metric.metric_definition_id,
                "MetricDefinition",
                claim_project_id,
                [*path, "measurement", "metric_definition_version", "owner"],
                violations,
            )
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
        context: ClosureEvaluationContext | None = None,
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
        if context is None:
            inputs = uow.statistical_results.list_inputs(result.id)
        else:
            state, inputs = context.statistical_inputs.resolve(result.id)
            if state is BatchLookupState.NEVER_REQUESTED:
                violations.append(
                    _context_incomplete(
                        "StatisticalResultInput",
                        result.id,
                        [*path, "statistical_result", "inputs"],
                    )
                )
                return
            inputs = inputs or []
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
            if context is None:
                measurement = uow.measurements.get(input_edge.measurement_id)
            else:
                state, measurement = context.measurements.resolve(input_edge.measurement_id)
                if state is BatchLookupState.NEVER_REQUESTED:
                    violations.append(
                        _context_incomplete(
                            "Measurement",
                            input_edge.measurement_id,
                            [
                                *path,
                                "statistical_result",
                                "inputs",
                                str(input_edge.measurement_id),
                                "measurement",
                            ],
                        )
                    )
                    continue
            self._validate_measurement_source(
                uow,
                measurement,
                input_edge.measurement_id,
                result.project_id,
                [*path, "statistical_result", "inputs", str(input_edge.measurement_id)],
                visited,
                violations,
                context,
            )

    def _record_run_closure(
        self,
        uow: UnitOfWork,
        run: Run,
        path: list[str],
        visited: set[tuple[str, UUID]],
        violations: list[ClosureViolation],
        context: ClosureEvaluationContext | None = None,
    ) -> None:
        visited.add(("Run", UUID(str(run.id))))
        run_uuid = UUID(str(run.id))
        report = context.run_reports.get(run_uuid) if context is not None else None
        if report is None:
            report = self.validate_run_in_uow(uow, run.id, context)
            if context is not None:
                context.run_reports[run_uuid] = report
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
        if context is None:
            spec = uow.experiment_specs.get_version(run.experiment_spec_version_id)
        else:
            state, spec = context.spec_versions.resolve(run.experiment_spec_version_id)
            if state is BatchLookupState.NEVER_REQUESTED:
                violations.append(
                    _context_incomplete(
                        "ExperimentSpecVersion",
                        run.experiment_spec_version_id,
                        [*prefix, "run", "experiment_spec_version"],
                    )
                )
        if spec is not None:
            visited.add(("ExperimentSpecVersion", UUID(str(spec.id))))
        if context is None:
            dataset_inputs = uow.runs.list_dataset_inputs(run.id)
        else:
            state, dataset_inputs = context.dataset_inputs.resolve(run.id)
            if state is BatchLookupState.NEVER_REQUESTED:
                violations.append(
                    _context_incomplete(
                        "RunDatasetInput", run.id, [*prefix, "run", "dataset_inputs"]
                    )
                )
                dataset_inputs = []
            else:
                dataset_inputs = dataset_inputs or []
        for item in dataset_inputs:
            if context is None:
                snapshot = uow.dataset_snapshots.get(item.dataset_snapshot_id)
            else:
                state, snapshot = context.dataset_snapshots.resolve(item.dataset_snapshot_id)
                if state is BatchLookupState.NEVER_REQUESTED:
                    violations.append(
                        _context_incomplete(
                            "DatasetSnapshot",
                            item.dataset_snapshot_id,
                            [*prefix, "run", "dataset_inputs", item.role.value],
                        )
                    )
                    continue
            if snapshot is not None:
                visited.add(("DatasetSnapshot", UUID(str(snapshot.id))))
        if context is None:
            artifact_inputs = uow.runs.list_artifact_inputs(run.id)
        else:
            state, artifact_inputs = context.artifact_inputs.resolve(run.id)
            if state is BatchLookupState.NEVER_REQUESTED:
                violations.append(
                    _context_incomplete(
                        "RunArtifactInput", run.id, [*prefix, "run", "artifact_inputs"]
                    )
                )
                artifact_inputs = []
            else:
                artifact_inputs = artifact_inputs or []
        for item in artifact_inputs:
            if context is None:
                artifact = uow.artifact_versions.get(item.artifact_version_id)
            else:
                state, artifact = context.artifact_versions.resolve(item.artifact_version_id)
                if state is BatchLookupState.NEVER_REQUESTED:
                    violations.append(
                        _context_incomplete(
                            "ArtifactVersion",
                            item.artifact_version_id,
                            [*prefix, "run", "artifact_inputs", item.role.value],
                        )
                    )
                    continue
            if artifact is not None:
                visited.add(("ArtifactVersion", UUID(str(artifact.id))))

    def validate_run_in_uow(
        self, uow: UnitOfWork, run_id: RunId, context: ClosureEvaluationContext | None = None
    ) -> ClosureReport:
        violations: list[ClosureViolation] = []
        visited: set[tuple[str, UUID]] = set()
        if context is None:
            run = uow.runs.get(run_id)
        else:
            state, run = context.runs.resolve(run_id)
            if state is BatchLookupState.NEVER_REQUESTED:
                return ClosureReport(
                    complete=False,
                    visited_count=0,
                    violations=[_context_incomplete("Run", run_id, ["run"])],
                )
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

        spec_context_incomplete = False
        if context is None:
            spec = uow.experiment_specs.get_version(run.experiment_spec_version_id)
        else:
            state, spec = context.spec_versions.resolve(run.experiment_spec_version_id)
            if state is BatchLookupState.NEVER_REQUESTED:
                violations.append(
                    _context_incomplete(
                        "ExperimentSpecVersion",
                        run.experiment_spec_version_id,
                        ["run", "experiment_spec_version"],
                    )
                )
                spec_context_incomplete = True
        if spec is None:
            if not spec_context_incomplete:
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
            self._owner(
                uow.experiment_specs,
                context.spec_owners if context else None,
                spec.experiment_spec_id,
                "ExperimentSpec",
                run.project_id,
                ["run", "experiment_spec_version", "owner"],
                violations,
            )
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

        if context is None:
            dataset_inputs = uow.runs.list_dataset_inputs(run.id)
        else:
            state, dataset_inputs = context.dataset_inputs.resolve(run.id)
            if state is BatchLookupState.NEVER_REQUESTED:
                violations.append(
                    _context_incomplete("RunDatasetInput", run.id, ["run", "dataset_inputs"])
                )
                dataset_inputs = []
            else:
                dataset_inputs = dataset_inputs or []
        for item in dataset_inputs:
            if context is None:
                snapshot = uow.dataset_snapshots.get(item.dataset_snapshot_id)
            else:
                state, snapshot = context.dataset_snapshots.resolve(item.dataset_snapshot_id)
                if state is BatchLookupState.NEVER_REQUESTED:
                    violations.append(
                        _context_incomplete(
                            "DatasetSnapshot",
                            item.dataset_snapshot_id,
                            ["run", "dataset_inputs", item.role.value],
                        )
                    )
                    continue
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
                self._owner(
                    uow.datasets,
                    context.dataset_owners if context else None,
                    snapshot.dataset_id,
                    "Dataset",
                    run.project_id,
                    ["run", "dataset_inputs", item.role.value, "owner"],
                    violations,
                )

        if context is None:
            artifact_inputs = uow.runs.list_artifact_inputs(run.id)
        else:
            state, artifact_inputs = context.artifact_inputs.resolve(run.id)
            if state is BatchLookupState.NEVER_REQUESTED:
                violations.append(
                    _context_incomplete("RunArtifactInput", run.id, ["run", "artifact_inputs"])
                )
                artifact_inputs = []
            else:
                artifact_inputs = artifact_inputs or []
        for item in artifact_inputs:
            if context is None:
                version = uow.artifact_versions.get(item.artifact_version_id)
            else:
                state, version = context.artifact_versions.resolve(item.artifact_version_id)
                if state is BatchLookupState.NEVER_REQUESTED:
                    violations.append(
                        _context_incomplete(
                            "ArtifactVersion",
                            item.artifact_version_id,
                            ["run", "artifact_inputs", item.role.value],
                        )
                    )
                    continue
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
                self._owner(
                    uow.artifacts,
                    context.artifact_owners if context else None,
                    version.artifact_id,
                    "Artifact",
                    run.project_id,
                    ["run", "artifact_inputs", item.role.value, "owner"],
                    violations,
                )
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
    def _owner(
        repository: Any,
        batch: BatchLookup[Any] | None,
        identity: Any,
        kind: str,
        project: Any,
        path: list[str],
        violations: list[ClosureViolation],
    ) -> None:
        if batch is None:
            owner = repository.get(identity)
        else:
            state, owner = batch.resolve(identity)
            if state is BatchLookupState.NEVER_REQUESTED:
                violations.append(_context_incomplete(kind, identity, path))
                return
        if owner is None:
            violations.append(
                ClosureViolation(
                    ErrorCode.NOT_FOUND.value,
                    kind,
                    UUID(str(identity)),
                    path,
                    "required owning identity was not found",
                )
            )
        elif (
            project is not None
            and owner.project_id != project
            and not (
                kind in {"Dataset", "Artifact", "MetricDefinition"} and owner.project_id is None
            )
        ):
            violations.append(
                ClosureViolation(
                    ErrorCode.REFERENTIAL_INTEGRITY_ERROR.value,
                    kind,
                    UUID(str(identity)),
                    path,
                    "required owning identity belongs to a different project",
                )
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
