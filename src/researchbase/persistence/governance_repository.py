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


class SqlAlchemyGovernanceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def resolve_experiment_spec_version(self, target_id: UUID) -> ResolvedGovernanceTarget | None:
        row = self._session.execute(
            select(ExperimentSpecModel.project_id, ExperimentSpecVersionModel.content_hash)
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
                ExperimentSpecVersionModel.content_hash,
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
            select(DatasetModel.project_id, DatasetSnapshotModel.content_hash)
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
                DatasetSnapshotModel.content_hash,
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
                MetricDefinitionVersionModel.content_hash,
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
                MetricDefinitionVersionModel.content_hash,
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
            select(RunModel.project_id, MeasurementModel.content_hash)
            .join(MeasurementModel, MeasurementModel.run_id == RunModel.id)
            .where(MeasurementModel.id == target_id)
        ).one_or_none()
        return self._resolved(GovernanceTargetType.MEASUREMENT, target_id, row)

    def resolve_measurements(self, target_ids: set[UUID]) -> list[ResolvedGovernanceTarget]:
        if not target_ids:
            return []
        rows = self._session.execute(
            select(MeasurementModel.id, RunModel.project_id, MeasurementModel.content_hash)
            .join(MeasurementModel, MeasurementModel.run_id == RunModel.id)
            .where(MeasurementModel.id.in_(target_ids))
        ).all()
        return self._resolved_many(GovernanceTargetType.MEASUREMENT, rows)

    def resolve_statistical_result(self, target_id: UUID) -> ResolvedGovernanceTarget | None:
        row = self._session.execute(
            select(StatisticalResultModel.project_id, StatisticalResultModel.content_hash).where(
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
                StatisticalResultModel.content_hash,
            ).where(StatisticalResultModel.id.in_(target_ids))
        ).all()
        return self._resolved_many(GovernanceTargetType.STATISTICAL_RESULT, rows)

    def resolve_claim_version(self, target_id: UUID) -> ResolvedGovernanceTarget | None:
        row = self._session.execute(
            select(ClaimModel.project_id, ClaimVersionModel.content_hash)
            .join(ClaimVersionModel, ClaimVersionModel.claim_id == ClaimModel.id)
            .where(ClaimVersionModel.id == target_id)
        ).one_or_none()
        return self._resolved(GovernanceTargetType.CLAIM_VERSION, target_id, row)

    def resolve_claim_versions(self, target_ids: set[UUID]) -> list[ResolvedGovernanceTarget]:
        if not target_ids:
            return []
        rows = self._session.execute(
            select(ClaimVersionModel.id, ClaimModel.project_id, ClaimVersionModel.content_hash)
            .join(ClaimVersionModel, ClaimVersionModel.claim_id == ClaimModel.id)
            .where(ClaimVersionModel.id.in_(target_ids))
        ).all()
        return self._resolved_many(GovernanceTargetType.CLAIM_VERSION, rows)

    @staticmethod
    def _resolved(
        target_type: GovernanceTargetType, target_id: UUID, row: object
    ) -> ResolvedGovernanceTarget | None:
        if row is None:
            return None
        project_id, *hash_value = row  # type: ignore[misc]
        if project_id is None:
            return None
        content_hash = hash_value[0] if hash_value else None
        return ResolvedGovernanceTarget(
            target_type,
            target_id,
            ProjectId(project_id),
            ContentHash(content_hash) if content_hash is not None else None,
        )

    @classmethod
    def _resolved_many(
        cls, target_type: GovernanceTargetType, rows: Sequence[object]
    ) -> list[ResolvedGovernanceTarget]:
        resolved: list[ResolvedGovernanceTarget] = []
        for row in rows:
            values = tuple(cast(Any, row))
            item = cls._resolved(target_type, values[0], values[1:])
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

    def get_audit_finding(self, finding_id: UUID) -> AuditFinding | None:
        model = self._session.get(AuditFindingModel, finding_id)
        if model is None:
            return None
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
                assessment_payload=assessment.assessment_payload,
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
            ImpactTarget(
                ImpactAssessmentId(item.impact_assessment_id),
                GovernanceTargetType(item.target_type),
                item.target_id,
                ContentHash(item.target_content_hash) if item.target_content_hash else None,
                ImpactKind(item.impact_kind),
            )
            for item in target_models
        )
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
                corrected_assertion=correction.corrected_assertion,
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
                    MeasurementModel.content_hash,
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
                        row.content_hash,
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
                    StatisticalResultModel.content_hash,
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
                        row.content_hash,
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
                    ClaimVersionModel.content_hash,
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
                        row.content_hash,
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
                    ClaimVersionModel.content_hash,
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
                            row.content_hash,
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
