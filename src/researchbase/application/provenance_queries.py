"""Explicit, read-only provenance query DTOs and service for PR-13."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from researchbase.application.closure import ClosureReport, ProvenanceClosureValidator
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
    """Dedicated read boundary over one coherent UoW per query call."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory
        self._validator = ProvenanceClosureValidator(uow_factory)

    def get_run_provenance(self, run_id: UUID) -> RunProvenanceDTO:
        with self._uow_factory() as uow:
            run = self._require_run(uow, run_id)
            return self._run_provenance(uow, run)

    def trace_run_to_inputs(self, run_id: UUID) -> RunInputsDTO:
        with self._uow_factory() as uow:
            run = self._require_run(uow, run_id)
            provenance = self._run_provenance(uow, run)
            return RunInputsDTO(
                run_id=provenance.run_id,
                project_id=provenance.project_id,
                experiment_spec_version_id=provenance.experiment_spec_version_id,
                experiment_spec_content_hash=provenance.experiment_spec_content_hash,
                dataset_inputs=provenance.dataset_inputs,
                artifact_inputs=provenance.artifact_inputs,
                closure=provenance.closure,
            )

    def get_claim_closure_report(self, claim_version_id: UUID) -> ClosureReportDTO:
        with self._uow_factory() as uow:
            self._require_claim_version(uow, claim_version_id)
            report = self._validator.validate_claim_version_in_uow(
                uow, ClaimVersionId(claim_version_id)
            )
            return _closure_dto(report)

    def trace_claim_to_runs(self, claim_version_id: UUID) -> ClaimToRunsTraceDTO:
        with self._uow_factory() as uow:
            version = self._require_claim_version(uow, claim_version_id)
            claim = uow.claims.get(version.claim_id)
            if claim is None:
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "claim was not found")

            closure = self._validator.validate_claim_version_in_uow(uow, version.id)
            paths: list[ClaimEvidencePathDTO] = []
            runs: dict[str, Run] = {}
            relations = sorted(uow.claims.list_evidence(version.id), key=_relation_key)
            for relation in relations:
                if relation.measurement_id is not None:
                    measurement = uow.measurements.get(relation.measurement_id)
                    if measurement is not None:
                        self._append_path(paths, runs, uow, version.id, relation, measurement)
                    continue
                if relation.statistical_result_id is None:
                    continue
                for edge in uow.statistical_results.list_inputs(relation.statistical_result_id):
                    measurement = uow.measurements.get(edge.measurement_id)
                    if measurement is not None:
                        self._append_path(
                            paths,
                            runs,
                            uow,
                            version.id,
                            relation,
                            measurement,
                            input_role=edge.input_role,
                            input_ordinal=edge.ordinal,
                        )

            paths.sort(key=_path_key)
            run_dtos = tuple(self._run_provenance(uow, runs[run_id]) for run_id in sorted(runs))
            return ClaimToRunsTraceDTO(
                claim_version_id=str(version.id),
                project_id=str(claim.project_id),
                runs=run_dtos,
                paths=tuple(paths),
                closure=_closure_dto(closure),
            )

    def _append_path(
        self,
        paths: list[ClaimEvidencePathDTO],
        runs: dict[str, Run],
        uow: UnitOfWork,
        claim_version_id: ClaimVersionId,
        relation: EvidenceRelation,
        measurement: Measurement,
        *,
        input_role: str | None = None,
        input_ordinal: int | None = None,
    ) -> None:
        run = uow.runs.get(measurement.run_id)
        if run is None:
            return
        run_id = str(run.id)
        runs[run_id] = run
        paths.append(
            ClaimEvidencePathDTO(
                claim_version_id=str(claim_version_id),
                evidence_relation_id=str(relation.id),
                source_type=relation.source_type,
                source_id=str(relation.source_id),
                relation_type=relation.relation_type.value,
                qualification=relation.qualification,
                statistical_result_input_role=input_role,
                statistical_result_input_ordinal=input_ordinal,
                measurement_id=str(measurement.id),
                metric_definition_version_id=str(measurement.metric_definition_version_id),
                run_id=run_id,
            )
        )

    def _run_provenance(self, uow: UnitOfWork, run: Run) -> RunProvenanceDTO:
        spec = uow.experiment_specs.get_version(run.experiment_spec_version_id)
        spec_hash = str(spec.content_hash) if spec is not None and spec.content_hash else None
        datasets = []
        for edge in uow.runs.list_dataset_inputs(run.id):
            snapshot = uow.dataset_snapshots.get(edge.dataset_snapshot_id)
            datasets.append(
                RunInputDTO(
                    target_id=str(edge.dataset_snapshot_id),
                    role=edge.role.value,
                    ordinal=edge.ordinal,
                    content_hash=str(snapshot.content_hash) if snapshot is not None else None,
                )
            )
        artifacts = []
        for edge in uow.runs.list_artifact_inputs(run.id):
            version = uow.artifact_versions.get(edge.artifact_version_id)
            artifacts.append(
                RunInputDTO(
                    target_id=str(edge.artifact_version_id),
                    role=edge.role.value,
                    ordinal=edge.ordinal,
                    content_hash=str(version.content_hash) if version is not None else None,
                )
            )
        measurements = tuple(
            MeasurementRefDTO(
                measurement_id=str(item.id),
                metric_definition_version_id=str(item.metric_definition_version_id),
                content_hash=str(item.content_hash),
            )
            for item in uow.measurements.list_by_run(run.id)
        )
        return RunProvenanceDTO(
            run_id=str(run.id),
            project_id=str(run.project_id),
            run_type=run.run_type,
            status=run.status.value,
            inputs_sealed_at=run.inputs_sealed_at,
            started_at=run.started_at,
            finished_at=run.finished_at,
            experiment_spec_version_id=str(run.experiment_spec_version_id),
            experiment_spec_content_hash=spec_hash,
            dataset_inputs=tuple(sorted(datasets, key=_input_key)),
            artifact_inputs=tuple(sorted(artifacts, key=_input_key)),
            measurements=measurements,
            closure=_closure_dto(self._validator.validate_run_in_uow(uow, run.id)),
        )

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
        complete=report.complete,
        visited_count=report.visited_count,
        violations=tuple(
            ClosureViolationDTO(
                code=item.code,
                object_type=item.object_type,
                object_id=str(item.object_id),
                path=tuple(item.path),
                message=item.message,
            )
            for item in report.violations
        ),
    )


def _relation_key(relation: EvidenceRelation) -> tuple[object, ...]:
    return (
        relation.source_type,
        str(relation.source_id),
        relation.relation_type.value,
        relation.qualification is not None,
        relation.qualification or "",
        str(relation.id),
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
