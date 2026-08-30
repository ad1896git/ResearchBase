"""Explicit, read-only provenance query DTOs and service."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from researchbase.application.closure import (
    ClosureEvaluationContext,
    ClosureReport,
    ProvenanceClosureValidator,
)
from researchbase.application.ports import UnitOfWork
from researchbase.domain.claim import ClaimVersionId, EvidenceRelation
from researchbase.domain.measurement import Measurement
from researchbase.domain.run import Run, RunId
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


@dataclass(frozen=True, slots=True)
class ClosureViolationDTO:
    code: str
    object_type: str
    object_id: str
    path: tuple[str, ...]
    message: str


@dataclass(frozen=True, slots=True)
class ClosureReportDTO:
    complete: bool
    visited_count: int
    violations: tuple[ClosureViolationDTO, ...]


@dataclass(frozen=True, slots=True)
class RunInputDTO:
    target_id: str
    role: str
    ordinal: int
    content_hash: str | None


@dataclass(frozen=True, slots=True)
class MeasurementRefDTO:
    measurement_id: str
    metric_definition_version_id: str
    content_hash: str


@dataclass(frozen=True, slots=True)
class RunInputsDTO:
    run_id: str
    project_id: str
    experiment_spec_version_id: str
    experiment_spec_content_hash: str | None
    dataset_inputs: tuple[RunInputDTO, ...]
    artifact_inputs: tuple[RunInputDTO, ...]
    closure: ClosureReportDTO


@dataclass(frozen=True, slots=True)
class RunProvenanceDTO:
    run_id: str
    project_id: str
    run_type: str
    status: str
    inputs_sealed_at: datetime | None
    started_at: datetime | None
    finished_at: datetime | None
    experiment_spec_version_id: str
    experiment_spec_content_hash: str | None
    dataset_inputs: tuple[RunInputDTO, ...]
    artifact_inputs: tuple[RunInputDTO, ...]
    measurements: tuple[MeasurementRefDTO, ...]
    closure: ClosureReportDTO


@dataclass(frozen=True, slots=True)
class ClaimEvidencePathDTO:
    claim_version_id: str
    evidence_relation_id: str
    source_type: str
    source_id: str
    relation_type: str
    qualification: str | None
    statistical_result_input_role: str | None
    statistical_result_input_ordinal: int | None
    measurement_id: str
    metric_definition_version_id: str
    run_id: str


@dataclass(frozen=True, slots=True)
class ClaimToRunsTraceDTO:
    claim_version_id: str
    project_id: str
    runs: tuple[RunProvenanceDTO, ...]
    paths: tuple[ClaimEvidencePathDTO, ...]
    closure: ClosureReportDTO


class ProvenanceQueryService:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory
        self._validator = ProvenanceClosureValidator(uow_factory)

    def get_run_provenance(self, run_id: UUID) -> RunProvenanceDTO:
        with self._uow_factory() as uow:
            run = self._require_run(uow, run_id)
            return self._run_provenance(uow, run, self._load_run_context(uow, {run.id}))

    def trace_run_to_inputs(self, run_id: UUID) -> RunInputsDTO:
        item = self.get_run_provenance(run_id)
        return RunInputsDTO(
            item.run_id,
            item.project_id,
            item.experiment_spec_version_id,
            item.experiment_spec_content_hash,
            item.dataset_inputs,
            item.artifact_inputs,
            item.closure,
        )

    def get_claim_closure_report(self, claim_version_id: UUID) -> ClosureReportDTO:
        with self._uow_factory() as uow:
            version = self._require_claim_version(uow, claim_version_id)
            relations = uow.claims.list_evidence(version.id)
            context = self._load_claim_context(uow, relations)
            return _closure_dto(
                self._validator.validate_claim_version_in_uow(uow, version.id, context)
            )

    def trace_claim_to_runs(self, claim_version_id: UUID) -> ClaimToRunsTraceDTO:
        with self._uow_factory() as uow:
            version = self._require_claim_version(uow, claim_version_id)
            claim = uow.claims.get(version.claim_id)
            if claim is None:
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "claim was not found")
            relations = sorted(uow.claims.list_evidence(version.id), key=_relation_key)
            context = self._load_claim_context(uow, relations)
            closure = self._validator.validate_claim_version_in_uow(uow, version.id, context)
            paths: list[ClaimEvidencePathDTO] = []
            for relation in relations:
                if relation.measurement_id is not None:
                    measurement = context.measurements.get(UUID(str(relation.measurement_id)))
                    if measurement is not None:
                        self._append_path(paths, version.id, relation, measurement)
                elif relation.statistical_result_id is not None:
                    for edge in context.statistical_inputs.get(
                        UUID(str(relation.statistical_result_id)), []
                    ):
                        measurement = context.measurements.get(UUID(str(edge.measurement_id)))
                        if measurement is not None:
                            self._append_path(
                                paths,
                                version.id,
                                relation,
                                measurement,
                                edge.input_role,
                                edge.ordinal,
                            )
            paths.sort(key=_path_key)
            runs = tuple(
                self._run_provenance(uow, context.runs[key], context)
                for key in sorted(context.runs, key=str)
            )
            return ClaimToRunsTraceDTO(
                str(version.id), str(claim.project_id), runs, tuple(paths), _closure_dto(closure)
            )

    @staticmethod
    def _append_path(
        paths: list[ClaimEvidencePathDTO],
        claim_version_id: ClaimVersionId,
        relation: EvidenceRelation,
        measurement: Measurement,
        input_role: str | None = None,
        input_ordinal: int | None = None,
    ) -> None:
        paths.append(
            ClaimEvidencePathDTO(
                str(claim_version_id),
                str(relation.id),
                relation.source_type,
                str(relation.source_id),
                relation.relation_type.value,
                relation.qualification,
                input_role,
                input_ordinal,
                str(measurement.id),
                str(measurement.metric_definition_version_id),
                str(measurement.run_id),
            )
        )

    def _run_provenance(
        self, uow: UnitOfWork, run: Run, context: ClosureEvaluationContext
    ) -> RunProvenanceDTO:
        spec = context.spec_versions.get(UUID(str(run.experiment_spec_version_id)))
        datasets = tuple(
            sorted(
                (
                    RunInputDTO(
                        str(edge.dataset_snapshot_id),
                        edge.role.value,
                        edge.ordinal,
                        str(
                            context.dataset_snapshots[
                                UUID(str(edge.dataset_snapshot_id))
                            ].content_hash
                        ),
                    )
                    for edge in context.dataset_inputs.get(UUID(str(run.id)), [])
                    if UUID(str(edge.dataset_snapshot_id)) in context.dataset_snapshots
                ),
                key=_input_key,
            )
        )
        artifacts = tuple(
            sorted(
                (
                    RunInputDTO(
                        str(edge.artifact_version_id),
                        edge.role.value,
                        edge.ordinal,
                        str(
                            context.artifact_versions[
                                UUID(str(edge.artifact_version_id))
                            ].content_hash
                        ),
                    )
                    for edge in context.artifact_inputs.get(UUID(str(run.id)), [])
                    if UUID(str(edge.artifact_version_id)) in context.artifact_versions
                ),
                key=_input_key,
            )
        )
        measurements = tuple(
            sorted(
                (
                    MeasurementRefDTO(
                        str(item.id), str(item.metric_definition_version_id), str(item.content_hash)
                    )
                    for item in context.measurements.values()
                    if item.run_id == run.id
                ),
                key=lambda item: item.measurement_id,
            )
        )
        key = UUID(str(run.id))
        if key not in context.run_reports:
            context.run_reports[key] = self._validator.validate_run_in_uow(uow, run.id, context)
        return RunProvenanceDTO(
            str(run.id),
            str(run.project_id),
            run.run_type,
            run.status.value,
            run.inputs_sealed_at,
            run.started_at,
            run.finished_at,
            str(run.experiment_spec_version_id),
            str(spec.content_hash) if spec is not None and spec.content_hash else None,
            datasets,
            artifacts,
            measurements,
            _closure_dto(context.run_reports[key]),
        )

    def _load_claim_context(
        self, uow: UnitOfWork, relations: list[EvidenceRelation]
    ) -> ClosureEvaluationContext:
        result_ids = {
            item.statistical_result_id
            for item in relations
            if item.statistical_result_id is not None
        }
        results = uow.statistical_results.get_many(result_ids)
        inputs = uow.statistical_results.list_inputs_for_results(result_ids)
        measurement_ids = {
            item.measurement_id for item in relations if item.measurement_id is not None
        } | {item.measurement_id for item in inputs}
        measurements = uow.measurements.get_many(measurement_ids)
        context = self._load_run_context(uow, {item.run_id for item in measurements})
        context.measurements.update({UUID(str(item.id)): item for item in measurements})
        context.statistical_results.update({UUID(str(item.id)): item for item in results})
        for item in inputs:
            context.statistical_inputs.setdefault(UUID(str(item.statistical_result_id)), []).append(
                item
            )
        return context

    @staticmethod
    def _load_run_context(uow: UnitOfWork, run_ids: set[RunId]) -> ClosureEvaluationContext:
        runs = uow.runs.get_many(run_ids)
        ids = {item.id for item in runs}
        dataset_inputs = uow.runs.list_dataset_inputs_for_runs(ids)
        artifact_inputs = uow.runs.list_artifact_inputs_for_runs(ids)
        specs = uow.experiment_specs.get_versions(
            {item.experiment_spec_version_id for item in runs}
        )
        snapshots = uow.dataset_snapshots.get_many(
            {item.dataset_snapshot_id for item in dataset_inputs}
        )
        artifacts = uow.artifact_versions.get_many(
            {item.artifact_version_id for item in artifact_inputs}
        )
        measurements = uow.measurements.list_by_runs(ids)
        metrics = uow.metric_definition_versions.get_many(
            {item.metric_definition_version_id for item in measurements}
        )
        context = ClosureEvaluationContext(
            runs={UUID(str(x.id)): x for x in runs},
            measurements={UUID(str(x.id)): x for x in measurements},
            metric_versions={UUID(str(x.id)): x for x in metrics},
            spec_versions={UUID(str(x.id)): x for x in specs},
            dataset_snapshots={UUID(str(x.id)): x for x in snapshots},
            artifact_versions={UUID(str(x.id)): x for x in artifacts},
        )
        for item in dataset_inputs:
            context.dataset_inputs.setdefault(UUID(str(item.run_id)), []).append(item)
        for item in artifact_inputs:
            context.artifact_inputs.setdefault(UUID(str(item.run_id)), []).append(item)
        return context

    @staticmethod
    def _require_run(uow: UnitOfWork, run_id: UUID) -> Run:
        run = uow.runs.get(RunId(run_id))
        if run is None:
            raise ResearchBaseError(ErrorCode.NOT_FOUND, "run was not found")
        return run

    @staticmethod
    def _require_claim_version(uow: UnitOfWork, claim_version_id: UUID):
        version = uow.claims.get_version(ClaimVersionId(claim_version_id))
        if version is None:
            raise ResearchBaseError(ErrorCode.NOT_FOUND, "claim version was not found")
        return version


def _closure_dto(report: ClosureReport) -> ClosureReportDTO:
    return ClosureReportDTO(
        report.complete,
        report.visited_count,
        tuple(
            ClosureViolationDTO(x.code, x.object_type, str(x.object_id), tuple(x.path), x.message)
            for x in report.violations
        ),
    )


def _relation_key(item: EvidenceRelation) -> tuple[object, ...]:
    return (
        item.source_type,
        str(item.source_id),
        item.relation_type.value,
        item.qualification is not None,
        item.qualification or "",
        str(item.id),
    )


def _input_key(item: RunInputDTO) -> tuple[str, int, str]:
    return (item.role, item.ordinal, item.target_id)


def _path_key(item: ClaimEvidencePathDTO) -> tuple[object, ...]:
    return (
        item.run_id,
        item.evidence_relation_id,
        item.source_type,
        item.source_id,
        item.statistical_result_input_ordinal
        if item.statistical_result_input_ordinal is not None
        else -1,
        item.statistical_result_input_role or "",
        item.measurement_id,
        item.relation_type,
        item.qualification is not None,
        item.qualification or "",
    )
