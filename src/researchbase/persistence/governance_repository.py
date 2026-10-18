"""Explicit persistence adapter for the closed PR-14 governance surface."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from researchbase.domain.governance import (
    AuditFinding,
    AuditFindingId,
    AuditFindingSeverity,
    AuditFindingStatus,
    CorrectionRecord,
    CorrectionRecordId,
    CorrectionType,
    GovernanceTargetType,
    ImpactAssessment,
    ImpactAssessmentConclusion,
    ImpactAssessmentId,
    ImpactKind,
    ImpactTarget,
    ResolvedGovernanceTarget,
)
from researchbase.domain.organization import ProjectId
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.frozen_json import thaw_json
from researchbase.foundation.hashing import ContentHash
from researchbase.foundation.ids import ActorId
from researchbase.persistence.models import (
    ArtifactModel,
    ArtifactVersionModel,
    AuditFindingModel,
    ClaimModel,
    ClaimVersionModel,
    CorrectionRecordModel,
    DatasetModel,
    DatasetSnapshotModel,
    EvidenceRelationModel,
    ExperimentSpecModel,
    ExperimentSpecVersionModel,
    ImpactAssessmentModel,
    ImpactTargetModel,
    MeasurementModel,
    MetricDefinitionModel,
    MetricDefinitionVersionModel,
    RunArtifactInputModel,
    RunDatasetInputModel,
    RunModel,
    StatisticalResultInputModel,
    StatisticalResultModel,
)
from researchbase.persistence.repositories import (
    _claim_version_from_model,
    _dataset_snapshot_from_model,
    _experiment_spec_version_from_model,
    _measurement_from_model,
    _metric_definition_version_from_model,
    _statistical_result_from_row,
    _verified_persisted,
)


@_verified_persisted("AuditFinding")
def _audit_finding_from_model(model: AuditFindingModel) -> AuditFinding:
    return AuditFinding(
        AuditFindingId(model.id),
        ProjectId(model.project_id),
        model.finding_type,
        AuditFindingSeverity(model.severity),
        model.title,
        model.description,
        GovernanceTargetType(model.target_type),
        model.target_id,
        ContentHash(model.target_content_hash) if model.target_content_hash else None,
        AuditFindingStatus(model.status),
        ActorId(model.created_by),
        model.created_at,
        model.row_version,
    )


@_verified_persisted("ImpactTarget")
def _impact_target_from_model(model: ImpactTargetModel) -> ImpactTarget:
    return ImpactTarget(
        ImpactAssessmentId(model.impact_assessment_id),
        GovernanceTargetType(model.target_type),
        model.target_id,
        ContentHash(model.target_content_hash) if model.target_content_hash else None,
        ImpactKind(model.impact_kind),
    )


@_verified_persisted("ImpactAssessment")
def _impact_assessment_from_models(
    model: ImpactAssessmentModel, targets: tuple[ImpactTarget, ...]
) -> ImpactAssessment:
    return ImpactAssessment(
        ImpactAssessmentId(model.id),
        ProjectId(model.project_id),
        AuditFindingId(model.audit_finding_id) if model.audit_finding_id else None,
        model.assessment_payload,
        ImpactAssessmentConclusion(model.conclusion),
        ActorId(model.created_by),
        model.created_at,
        ContentHash(model.content_hash),
        targets,
    )


@_verified_persisted("CorrectionRecord")
def _correction_record_from_model(model: CorrectionRecordModel) -> CorrectionRecord:
    return CorrectionRecord(
        CorrectionRecordId(model.id),
        ProjectId(model.project_id),
        GovernanceTargetType(model.target_type),
        model.target_id,
        ContentHash(model.target_content_hash) if model.target_content_hash else None,
        CorrectionType(model.correction_type),
        model.corrected_assertion,
        model.reason,
        ActorId(model.created_by),
        model.created_at,
        ContentHash(model.content_hash),
    )


class SqlAlchemyGovernanceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._verified_targets: dict[
            tuple[GovernanceTargetType, UUID], ResolvedGovernanceTarget
        ] = {}

    def _verify_target_binding(
        self,
        project_id: ProjectId,
        target_type: GovernanceTargetType,
        target_id: UUID,
        stored_hash: ContentHash | None,
    ) -> None:
        loaders = {
            GovernanceTargetType.EXPERIMENT_SPEC_VERSION: self.resolve_experiment_spec_version,
            GovernanceTargetType.DATASET_SNAPSHOT: self.resolve_dataset_snapshot,
            GovernanceTargetType.ARTIFACT_VERSION: self.resolve_artifact_version,
            GovernanceTargetType.RUN: self.resolve_run,
            GovernanceTargetType.METRIC_DEFINITION_VERSION: self.resolve_metric_definition_version,
            GovernanceTargetType.MEASUREMENT: self.resolve_measurement,
            GovernanceTargetType.STATISTICAL_RESULT: self.resolve_statistical_result,
            GovernanceTargetType.CLAIM_VERSION: self.resolve_claim_version,
        }
        resolved = self._verified_targets.get((target_type, target_id))
        if resolved is None:
            resolved = loaders[target_type](target_id)
        if (
            resolved is None
            or resolved.project_id != project_id
            or resolved.content_hash != stored_hash
        ):
            raise ResearchBaseError(
                ErrorCode.REFERENTIAL_INTEGRITY_ERROR,
                "persisted governance target binding failed integrity verification",
                {
                    "object_type": target_type.value,
                    "object_id": str(target_id),
                    "hash_category": "target_hash_binding",
                },
            )

    def resolve_experiment_spec_version(self, target_id: UUID) -> ResolvedGovernanceTarget | None:
        row = self._session.execute(
            select(ExperimentSpecModel.project_id, ExperimentSpecVersionModel)
            .join(
                ExperimentSpecVersionModel,
                ExperimentSpecVersionModel.experiment_spec_id == ExperimentSpecModel.id,
            )
            .where(ExperimentSpecVersionModel.id == target_id)
        ).one_or_none()
        return self._resolved(GovernanceTargetType.EXPERIMENT_SPEC_VERSION, target_id, row)

    def resolve_experiment_spec_versions(
        self, target_ids: set[UUID]
    ) -> list[ResolvedGovernanceTarget]:
        if not target_ids:
            return []
        rows = self._session.execute(
            select(
                ExperimentSpecVersionModel.id,
                ExperimentSpecModel.project_id,
                ExperimentSpecVersionModel,
            )
            .join(
                ExperimentSpecVersionModel,
                ExperimentSpecVersionModel.experiment_spec_id == ExperimentSpecModel.id,
            )
            .where(ExperimentSpecVersionModel.id.in_(target_ids))
        ).all()
        return self._resolved_many(GovernanceTargetType.EXPERIMENT_SPEC_VERSION, rows)

    def resolve_dataset_snapshot(self, target_id: UUID) -> ResolvedGovernanceTarget | None:
        row = self._session.execute(
            select(DatasetModel.project_id, DatasetSnapshotModel)
            .join(DatasetSnapshotModel, DatasetSnapshotModel.dataset_id == DatasetModel.id)
            .where(DatasetSnapshotModel.id == target_id)
        ).one_or_none()
        return self._resolved(GovernanceTargetType.DATASET_SNAPSHOT, target_id, row)

    def resolve_dataset_snapshots(self, target_ids: set[UUID]) -> list[ResolvedGovernanceTarget]:
        if not target_ids:
            return []
        rows = self._session.execute(
            select(
                DatasetSnapshotModel.id,
                DatasetModel.project_id,
                DatasetSnapshotModel,
            )
            .join(DatasetSnapshotModel, DatasetSnapshotModel.dataset_id == DatasetModel.id)
            .where(DatasetSnapshotModel.id.in_(target_ids))
        ).all()
        return self._resolved_many(GovernanceTargetType.DATASET_SNAPSHOT, rows)

    def resolve_artifact_version(self, target_id: UUID) -> ResolvedGovernanceTarget | None:
        row = self._session.execute(
            select(ArtifactModel.project_id, ArtifactVersionModel.content_hash)
            .join(ArtifactVersionModel, ArtifactVersionModel.artifact_id == ArtifactModel.id)
            .where(ArtifactVersionModel.id == target_id)
        ).one_or_none()
        return self._resolved(GovernanceTargetType.ARTIFACT_VERSION, target_id, row)

    def resolve_artifact_versions(self, target_ids: set[UUID]) -> list[ResolvedGovernanceTarget]:
        if not target_ids:
            return []
        rows = self._session.execute(
            select(
                ArtifactVersionModel.id,
                ArtifactModel.project_id,
                ArtifactVersionModel.content_hash,
            )
            .join(ArtifactVersionModel, ArtifactVersionModel.artifact_id == ArtifactModel.id)
            .where(ArtifactVersionModel.id.in_(target_ids))
        ).all()
        return self._resolved_many(GovernanceTargetType.ARTIFACT_VERSION, rows)

    def resolve_run(self, target_id: UUID) -> ResolvedGovernanceTarget | None:
        row = self._session.execute(
            select(RunModel.project_id).where(RunModel.id == target_id)
        ).one_or_none()
        return self._resolved(GovernanceTargetType.RUN, target_id, row)

    def resolve_runs(self, target_ids: set[UUID]) -> list[ResolvedGovernanceTarget]:
        if not target_ids:
            return []
        rows = self._session.execute(
            select(RunModel.id, RunModel.project_id).where(RunModel.id.in_(target_ids))
        ).all()
        return self._resolved_many(GovernanceTargetType.RUN, rows)

    def resolve_metric_definition_version(self, target_id: UUID) -> ResolvedGovernanceTarget | None:
        row = self._session.execute(
            select(
                MetricDefinitionModel.project_id,
                MetricDefinitionVersionModel,
            )
            .join(
                MetricDefinitionVersionModel,
                MetricDefinitionVersionModel.metric_definition_id == MetricDefinitionModel.id,
            )
            .where(MetricDefinitionVersionModel.id == target_id)
        ).one_or_none()
        return self._resolved(GovernanceTargetType.METRIC_DEFINITION_VERSION, target_id, row)

    def resolve_metric_definition_versions(
        self, target_ids: set[UUID]
    ) -> list[ResolvedGovernanceTarget]:
        if not target_ids:
            return []
        rows = self._session.execute(
            select(
                MetricDefinitionVersionModel.id,
                MetricDefinitionModel.project_id,
                MetricDefinitionVersionModel,
            )
            .join(
                MetricDefinitionVersionModel,
                MetricDefinitionVersionModel.metric_definition_id == MetricDefinitionModel.id,
            )
            .where(MetricDefinitionVersionModel.id.in_(target_ids))
        ).all()
        return self._resolved_many(GovernanceTargetType.METRIC_DEFINITION_VERSION, rows)

    def resolve_measurement(self, target_id: UUID) -> ResolvedGovernanceTarget | None:
        row = self._session.execute(
            select(RunModel.project_id, MeasurementModel)
            .join(MeasurementModel, MeasurementModel.run_id == RunModel.id)
            .where(MeasurementModel.id == target_id)
        ).one_or_none()
        return self._resolved(GovernanceTargetType.MEASUREMENT, target_id, row)

    def resolve_measurements(self, target_ids: set[UUID]) -> list[ResolvedGovernanceTarget]:
        if not target_ids:
            return []
        rows = self._session.execute(
            select(MeasurementModel.id, RunModel.project_id, MeasurementModel)
            .join(MeasurementModel, MeasurementModel.run_id == RunModel.id)
            .where(MeasurementModel.id.in_(target_ids))
        ).all()
        return self._resolved_many(GovernanceTargetType.MEASUREMENT, rows)

    def resolve_statistical_result(self, target_id: UUID) -> ResolvedGovernanceTarget | None:
        row = self._session.execute(
            select(StatisticalResultModel.project_id, StatisticalResultModel).where(
                StatisticalResultModel.id == target_id
            )
        ).one_or_none()
        return self._resolved(GovernanceTargetType.STATISTICAL_RESULT, target_id, row)

    def resolve_statistical_results(self, target_ids: set[UUID]) -> list[ResolvedGovernanceTarget]:
        if not target_ids:
            return []
        rows = self._session.execute(
            select(
                StatisticalResultModel.id,
                StatisticalResultModel.project_id,
                StatisticalResultModel,
            ).where(StatisticalResultModel.id.in_(target_ids))
        ).all()
        return self._resolved_many(GovernanceTargetType.STATISTICAL_RESULT, rows)

    def resolve_claim_version(self, target_id: UUID) -> ResolvedGovernanceTarget | None:
        row = self._session.execute(
            select(ClaimModel.project_id, ClaimVersionModel)
            .join(ClaimVersionModel, ClaimVersionModel.claim_id == ClaimModel.id)
            .where(ClaimVersionModel.id == target_id)
        ).one_or_none()
        return self._resolved(GovernanceTargetType.CLAIM_VERSION, target_id, row)

    def resolve_claim_versions(self, target_ids: set[UUID]) -> list[ResolvedGovernanceTarget]:
        if not target_ids:
            return []
        rows = self._session.execute(
            select(ClaimVersionModel.id, ClaimModel.project_id, ClaimVersionModel)
            .join(ClaimVersionModel, ClaimVersionModel.claim_id == ClaimModel.id)
            .where(ClaimVersionModel.id.in_(target_ids))
        ).all()
        return self._resolved_many(GovernanceTargetType.CLAIM_VERSION, rows)

    def _resolved(
        self, target_type: GovernanceTargetType, target_id: UUID, row: object
    ) -> ResolvedGovernanceTarget | None:
        if row is None:
            return None
        project_id, *hash_value = row  # type: ignore[misc]
        if project_id is None:
            return None
        hash_source = hash_value[0] if hash_value else None
        content_hash = self_hash = hash_source
        if isinstance(hash_source, ExperimentSpecVersionModel):
            self_hash = _experiment_spec_version_from_model(hash_source).content_hash
        elif isinstance(hash_source, DatasetSnapshotModel):
            self_hash = _dataset_snapshot_from_model(hash_source).content_hash
        elif isinstance(hash_source, MetricDefinitionVersionModel):
            self_hash = _metric_definition_version_from_model(hash_source).content_hash
        elif isinstance(hash_source, MeasurementModel):
            self_hash = _measurement_from_model(hash_source).content_hash
        elif isinstance(hash_source, StatisticalResultModel):
            self_hash = _statistical_result_from_row(
                {
                    "id": hash_source.id,
                    "project_id": hash_source.project_id,
                    "analysis_type": hash_source.analysis_type,
                    "result_payload": hash_source.result_payload,
                    "analysis_definition": hash_source.analysis_definition,
                    "content_hash": hash_source.content_hash,
                    "created_by": hash_source.created_by,
                    "created_at": hash_source.created_at,
                }
            ).content_hash
        elif isinstance(hash_source, ClaimVersionModel):
            self_hash = _claim_version_from_model(hash_source).content_hash
        content_hash = self_hash
        resolved = ResolvedGovernanceTarget(
            target_type,
            target_id,
            ProjectId(project_id),
            ContentHash(content_hash) if content_hash is not None else None,
        )
        self._verified_targets[(target_type, target_id)] = resolved
        return resolved

    def _resolved_many(
        self, target_type: GovernanceTargetType, rows: Sequence[object]
    ) -> list[ResolvedGovernanceTarget]:
        resolved: list[ResolvedGovernanceTarget] = []
        for row in rows:
            values = tuple(cast(Any, row))
            item = self._resolved(target_type, values[0], values[1:])
            if item is not None:
                resolved.append(item)
        return resolved

    def add_audit_finding(self, finding: AuditFinding) -> None:
        self._session.add(
            AuditFindingModel(
                id=finding.id,
                project_id=finding.project_id,
                finding_type=finding.finding_type,
                severity=finding.severity.value,
                title=finding.title,
                description=finding.description,
                target_type=finding.target_type.value,
                target_id=finding.target_id,
                target_content_hash=finding.target_content_hash,
                status=finding.status.value,
                created_by=finding.created_by,
                created_at=finding.created_at,
                row_version=finding.row_version,
            )
        )
        self._session.flush()

    def finding_header(self, project_id: UUID, finding_id: UUID) -> UUID | None:
        """Scope the root before hydrating any saved target or payload."""
        return self._session.scalar(
            select(AuditFindingModel.id).where(
                AuditFindingModel.id == finding_id, AuditFindingModel.project_id == project_id
            )
        )

    def finding_assessments(
        self, project_id: UUID, finding_id: UUID
    ) -> tuple[ImpactAssessment, ...]:
        # Inventory the complete linked set and target count before domain hydration.
        # Every SELECT is ceiling+1 bounded by the caller's prepared B25 Session.
        ids = self._session.scalars(
            select(ImpactAssessmentModel.id)
            .where(ImpactAssessmentModel.audit_finding_id == finding_id)
            .order_by(ImpactAssessmentModel.created_at, ImpactAssessmentModel.id)
            .limit(10001)
        ).all()
        targets = self._session.execute(
            select(ImpactTargetModel.impact_assessment_id, ImpactTargetModel.target_id)
            .join(
                ImpactAssessmentModel,
                ImpactAssessmentModel.id == ImpactTargetModel.impact_assessment_id,
            )
            .where(ImpactAssessmentModel.audit_finding_id == finding_id)
            .limit(10001)
        ).all()
        if len(ids) > 10000 or len(targets) > 10000:
            raise ResearchBaseError(
                ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                "complete Finding assessment set exceeds fixed ceiling",
            )
        result = []
        for identity in ids:
            item = self.get_impact_assessment(identity)
            if item is None or item.project_id != project_id or item.audit_finding_id != finding_id:
                raise ResearchBaseError(
                    ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                    "incomplete or foreign saved Finding assessment",
                )
            result.append(item)
        return tuple(sorted(result, key=lambda item: (item.created_at, str(item.id))))

    def get_audit_finding(self, finding_id: UUID) -> AuditFinding | None:
        model = self._session.get(AuditFindingModel, finding_id)
        if model is None:
            return None
        finding = _audit_finding_from_model(model)
        self._verify_target_binding(
            finding.project_id,
            finding.target_type,
            finding.target_id,
            finding.target_content_hash,
        )
        return finding

    def list_audit_findings(
        self, project_id: UUID, target_type: str | None = None, target_id: UUID | None = None
    ) -> list[AuditFinding]:
        statement = select(AuditFindingModel.id).where(AuditFindingModel.project_id == project_id)
        if target_type is not None and target_id is not None:
            statement = statement.where(
                AuditFindingModel.target_type == target_type,
                AuditFindingModel.target_id == target_id,
            )
        ids = self._session.scalars(
            statement.order_by(AuditFindingModel.created_at, AuditFindingModel.id)
        ).all()
        return [item for item in (self.get_audit_finding(value) for value in ids) if item]

    def transition_audit_finding(self, finding: AuditFinding, expected_row_version: int) -> None:
        result = self._session.execute(
            update(AuditFindingModel)
            .where(
                AuditFindingModel.id == finding.id,
                AuditFindingModel.row_version == expected_row_version,
            )
            .values(status=finding.status.value, row_version=finding.row_version)
        )
        if cast(Any, result).rowcount != 1:
            raise ResearchBaseError(
                ErrorCode.CONCURRENT_MODIFICATION,
                "stale audit finding row_version",
            )
        self._session.flush()

    def add_impact_assessment(self, assessment: ImpactAssessment) -> None:
        self._session.add(
            ImpactAssessmentModel(
                id=assessment.id,
                project_id=assessment.project_id,
                audit_finding_id=assessment.audit_finding_id,
                assessment_payload=thaw_json(assessment.assessment_payload),
                conclusion=assessment.conclusion.value,
                created_by=assessment.created_by,
                created_at=assessment.created_at,
                content_hash=assessment.content_hash,
            )
        )
        self._session.flush()
        for target in assessment.targets:
            self._session.add(
                ImpactTargetModel(
                    impact_assessment_id=target.impact_assessment_id,
                    target_type=target.target_type.value,
                    target_id=target.target_id,
                    target_content_hash=target.target_content_hash,
                    impact_kind=target.impact_kind.value,
                )
            )
        self._session.flush()

    def get_impact_assessment(self, assessment_id: UUID) -> ImpactAssessment | None:
        model = self._session.get(ImpactAssessmentModel, assessment_id)
        if model is None:
            return None
        target_models = self._session.scalars(
            select(ImpactTargetModel)
            .where(ImpactTargetModel.impact_assessment_id == assessment_id)
            .order_by(ImpactTargetModel.target_type, ImpactTargetModel.target_id)
        ).all()
        targets = tuple(
            sorted(
                (_impact_target_from_model(item) for item in target_models),
                key=lambda item: (item.target_type.value, str(item.target_id)),
            )
        )
        assessment = _impact_assessment_from_models(model, targets)
        for target in targets:
            self._verify_target_binding(
                assessment.project_id,
                target.target_type,
                target.target_id,
                target.target_content_hash,
            )
        return assessment

    def list_impact_assessments(self, finding_id: UUID) -> list[ImpactAssessment]:
        ids = self._session.scalars(
            select(ImpactAssessmentModel.id)
            .where(ImpactAssessmentModel.audit_finding_id == finding_id)
            .order_by(ImpactAssessmentModel.created_at, ImpactAssessmentModel.id)
        ).all()
        return [item for item in (self.get_impact_assessment(value) for value in ids) if item]

    def add_correction_record(self, correction: CorrectionRecord) -> None:
        self._session.add(
            CorrectionRecordModel(
                id=correction.id,
                project_id=correction.project_id,
                target_type=correction.target_type.value,
                target_id=correction.target_id,
                target_content_hash=correction.target_content_hash,
                correction_type=correction.correction_type.value,
                corrected_assertion=thaw_json(correction.corrected_assertion),
                reason=correction.reason,
                created_by=correction.created_by,
                created_at=correction.created_at,
                content_hash=correction.content_hash,
            )
        )
        self._session.flush()

    def get_correction_record(self, correction_id: UUID) -> CorrectionRecord | None:
        model = self._session.get(CorrectionRecordModel, correction_id)
        if model is None:
            return None
        correction = _correction_record_from_model(model)
        self._verify_target_binding(
            correction.project_id,
            correction.target_type,
            correction.target_id,
            correction.target_content_hash,
        )
        return correction

    def list_correction_records(
        self, project_id: UUID, target_type: str, target_id: UUID
    ) -> list[CorrectionRecord]:
        ids = self._session.scalars(
            select(CorrectionRecordModel.id)
            .where(
                CorrectionRecordModel.project_id == project_id,
                CorrectionRecordModel.target_type == target_type,
                CorrectionRecordModel.target_id == target_id,
            )
            .order_by(CorrectionRecordModel.created_at, CorrectionRecordModel.id)
        ).all()
        return [item for item in (self.get_correction_record(value) for value in ids) if item]

    def downstream_impact_rows(
        self, project_id: UUID, target_type: str, target_id: UUID
    ) -> list[tuple[object, ...]]:
        """Return exact dependency paths with a fixed, bounded set of staged reads."""
        run_paths: list[tuple[UUID, ...]] = []
        if target_type == GovernanceTargetType.ARTIFACT_VERSION.value:
            run_paths = [
                (row.run_id,)
                for row in self._session.execute(
                    select(RunArtifactInputModel.run_id)
                    .join(RunModel, RunModel.id == RunArtifactInputModel.run_id)
                    .where(
                        RunArtifactInputModel.artifact_version_id == target_id,
                        RunModel.project_id == project_id,
                    )
                )
            ]
        elif target_type == GovernanceTargetType.DATASET_SNAPSHOT.value:
            run_paths = [
                (row.run_id,)
                for row in self._session.execute(
                    select(RunDatasetInputModel.run_id)
                    .join(RunModel, RunModel.id == RunDatasetInputModel.run_id)
                    .where(
                        RunDatasetInputModel.dataset_snapshot_id == target_id,
                        RunModel.project_id == project_id,
                    )
                )
            ]
        elif target_type == GovernanceTargetType.RUN.value:
            exists = self._session.scalar(
                select(RunModel.id).where(
                    RunModel.id == target_id, RunModel.project_id == project_id
                )
            )
            run_paths = [(target_id,)] if exists else []

        paths: list[tuple[object, ...]] = []
        if target_type in {
            GovernanceTargetType.ARTIFACT_VERSION.value,
            GovernanceTargetType.DATASET_SNAPSHOT.value,
        }:
            paths.extend(
                (GovernanceTargetType.RUN.value, run_id, run_id, None, None, None, None, None, None)
                for run_id in sorted({row[0] for row in run_paths}, key=str)
            )

        measurement_prefixes: list[tuple[UUID | None, UUID]] = []
        if target_type == GovernanceTargetType.MEASUREMENT.value:
            row = self._session.execute(
                select(MeasurementModel.id)
                .join(RunModel, RunModel.id == MeasurementModel.run_id)
                .where(MeasurementModel.id == target_id, RunModel.project_id == project_id)
            ).one_or_none()
            if row:
                measurement_prefixes.append((None, target_id))
        elif run_paths:
            run_ids = {row[0] for row in run_paths}
            for row in self._session.execute(
                select(
                    MeasurementModel.run_id,
                    MeasurementModel.id,
                    MeasurementModel,
                ).where(MeasurementModel.run_id.in_(run_ids))
            ):
                measurement_prefixes.append((row.run_id, row.id))
                paths.append(
                    (
                        GovernanceTargetType.MEASUREMENT.value,
                        row.id,
                        row.run_id,
                        None,
                        None,
                        _measurement_from_model(row.MeasurementModel).content_hash,
                        None,
                        None,
                        None,
                    )
                )

        measurement_ids = {row[1] for row in measurement_prefixes}
        stat_prefixes: list[tuple[UUID | None, UUID | None, UUID, str | None, int | None]] = []
        if target_type == GovernanceTargetType.STATISTICAL_RESULT.value:
            exists = self._session.scalar(
                select(StatisticalResultModel.id).where(
                    StatisticalResultModel.id == target_id,
                    StatisticalResultModel.project_id == project_id,
                )
            )
            if exists:
                stat_prefixes.append((None, None, target_id, None, None))
        elif measurement_ids:
            for row in self._session.execute(
                select(
                    MeasurementModel.run_id,
                    StatisticalResultInputModel.measurement_id,
                    StatisticalResultInputModel.statistical_result_id,
                    StatisticalResultModel,
                    StatisticalResultInputModel.input_role,
                    StatisticalResultInputModel.ordinal,
                )
                .join(
                    MeasurementModel,
                    MeasurementModel.id == StatisticalResultInputModel.measurement_id,
                )
                .join(
                    StatisticalResultModel,
                    StatisticalResultModel.id == StatisticalResultInputModel.statistical_result_id,
                )
                .where(
                    StatisticalResultInputModel.measurement_id.in_(measurement_ids),
                    StatisticalResultModel.project_id == project_id,
                )
            ):
                stat_prefixes.append(
                    (
                        row.run_id,
                        row.measurement_id,
                        row.statistical_result_id,
                        row.input_role,
                        row.ordinal,
                    )
                )
                paths.append(
                    (
                        "statistical_result",
                        row.statistical_result_id,
                        row.run_id,
                        row.measurement_id,
                        None,
                        _statistical_result_from_row(
                            {
                                "id": row.StatisticalResultModel.id,
                                "project_id": row.StatisticalResultModel.project_id,
                                "analysis_type": row.StatisticalResultModel.analysis_type,
                                "result_payload": row.StatisticalResultModel.result_payload,
                                "analysis_definition": (
                                    row.StatisticalResultModel.analysis_definition
                                ),
                                "content_hash": row.StatisticalResultModel.content_hash,
                                "created_by": row.StatisticalResultModel.created_by,
                                "created_at": row.StatisticalResultModel.created_at,
                            }
                        ).content_hash,
                        None,
                        row.input_role,
                        row.ordinal,
                    )
                )

        if measurement_ids:
            for row in self._session.execute(
                select(
                    EvidenceRelationModel.id,
                    EvidenceRelationModel.measurement_id,
                    EvidenceRelationModel.claim_version_id,
                    ClaimVersionModel,
                )
                .join(
                    ClaimVersionModel,
                    ClaimVersionModel.id == EvidenceRelationModel.claim_version_id,
                )
                .join(ClaimModel, ClaimModel.id == ClaimVersionModel.claim_id)
                .where(
                    EvidenceRelationModel.measurement_id.in_(measurement_ids),
                    ClaimModel.project_id == project_id,
                )
            ):
                run_id = next((r for r, m in measurement_prefixes if m == row.measurement_id), None)
                paths.append(
                    (
                        "claim_version",
                        row.claim_version_id,
                        run_id,
                        row.measurement_id,
                        None,
                        _claim_version_from_model(row.ClaimVersionModel).content_hash,
                        row.id,
                        None,
                        None,
                    )
                )

        stat_ids = {row[2] for row in stat_prefixes}
        if stat_ids:
            for row in self._session.execute(
                select(
                    EvidenceRelationModel.id,
                    EvidenceRelationModel.statistical_result_id,
                    EvidenceRelationModel.claim_version_id,
                    ClaimVersionModel,
                )
                .join(
                    ClaimVersionModel,
                    ClaimVersionModel.id == EvidenceRelationModel.claim_version_id,
                )
                .join(ClaimModel, ClaimModel.id == ClaimVersionModel.claim_id)
                .where(
                    EvidenceRelationModel.statistical_result_id.in_(stat_ids),
                    ClaimModel.project_id == project_id,
                )
            ):
                prefixes = [p for p in stat_prefixes if p[2] == row.statistical_result_id]
                for run_id, measurement_id, stat_id, input_role, ordinal in prefixes:
                    paths.append(
                        (
                            "claim_version",
                            row.claim_version_id,
                            run_id,
                            measurement_id,
                            stat_id,
                            _claim_version_from_model(row.ClaimVersionModel).content_hash,
                            row.id,
                            input_role,
                            ordinal,
                        )
                    )
        return sorted(set(paths), key=lambda row: tuple("" if v is None else str(v) for v in row))

    def validity_rows(
        self, project_id: UUID, target_type: str, target_id: UUID
    ) -> list[tuple[object, ...]]:
        rows = self._session.execute(
            select(
                ImpactAssessmentModel.id,
                ImpactAssessmentModel.conclusion,
                AuditFindingModel.id,
                AuditFindingModel.status,
            )
            .join(
                ImpactTargetModel,
                ImpactTargetModel.impact_assessment_id == ImpactAssessmentModel.id,
            )
            .outerjoin(
                AuditFindingModel,
                AuditFindingModel.id == ImpactAssessmentModel.audit_finding_id,
            )
            .where(
                ImpactAssessmentModel.project_id == project_id,
                ImpactTargetModel.target_type == target_type,
                ImpactTargetModel.target_id == target_id,
            )
        ).all()
        corrections = self._session.execute(
            select(CorrectionRecordModel.id).where(
                CorrectionRecordModel.project_id == project_id,
                CorrectionRecordModel.target_type == target_type,
                CorrectionRecordModel.target_id == target_id,
            )
        ).all()
        return [tuple(row) for row in rows] + [
            (None, None, None, None, row.id) for row in corrections
        ]
