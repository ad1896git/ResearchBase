"""Read-only PR-14 downstream-impact and validity projections."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, cast
from uuid import UUID

from researchbase.application.governance import TargetResolverRegistry
from researchbase.application.ports import UnitOfWork
from researchbase.domain.governance import (
    AuditFinding,
    CorrectionRecord,
    GovernanceTargetType,
    ImpactAssessment,
)
from researchbase.domain.organization import ProjectId


@dataclass(frozen=True, slots=True)
class DownstreamImpactPath:
    target_type: GovernanceTargetType
    target_id: UUID
    run_id: UUID | None
    measurement_id: UUID | None
    statistical_result_id: UUID | None
    target_content_hash: str | None = None
    evidence_relation_id: UUID | None = None
    statistical_input_role: str | None = None
    statistical_input_ordinal: int | None = None


@dataclass(frozen=True, slots=True)
class DownstreamImpactTarget:
    target_type: GovernanceTargetType
    target_id: UUID
    target_content_hash: str | None
    paths: tuple[DownstreamImpactPath, ...]


class ValidityState(StrEnum):
    NOT_ASSESSED = "not_assessed"
    UNAFFECTED = "unaffected"
    STALE = "stale"
    INVALID = "invalid"
    REQUIRES_REVIEW = "requires_review"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ValidityProjection:
    target_type: GovernanceTargetType
    target_id: UUID
    state: ValidityState
    finding_ids: tuple[UUID, ...]
    assessment_ids: tuple[UUID, ...]
    correction_ids: tuple[UUID, ...]


class GovernanceQueryService:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory
        self._resolvers = TargetResolverRegistry()

    def get_audit_finding(self, finding_id: UUID) -> AuditFinding | None:
        with self._uow_factory() as uow:
            return uow.governance.get_audit_finding(finding_id)

    def list_audit_findings(
        self,
        project_id: UUID,
        target_type: GovernanceTargetType | str | None = None,
        target_id: UUID | None = None,
    ) -> tuple[AuditFinding, ...]:
        kind = GovernanceTargetType(target_type).value if target_type is not None else None
        with self._uow_factory() as uow:
            return tuple(uow.governance.list_audit_findings(project_id, kind, target_id))

    def get_impact_assessment(self, assessment_id: UUID) -> ImpactAssessment | None:
        with self._uow_factory() as uow:
            return uow.governance.get_impact_assessment(assessment_id)

    def list_impact_assessments(self, finding_id: UUID) -> tuple[ImpactAssessment, ...]:
        with self._uow_factory() as uow:
            return tuple(uow.governance.list_impact_assessments(finding_id))

    def get_correction_record(self, correction_id: UUID) -> CorrectionRecord | None:
        with self._uow_factory() as uow:
            return uow.governance.get_correction_record(correction_id)

    def list_correction_records(
        self, project_id: UUID, target_type: GovernanceTargetType | str, target_id: UUID
    ) -> tuple[CorrectionRecord, ...]:
        kind = GovernanceTargetType(target_type)
        with self._uow_factory() as uow:
            self._resolvers.resolve(uow.governance, ProjectId(project_id), kind, target_id)
            return tuple(uow.governance.list_correction_records(project_id, kind.value, target_id))

    def downstream_impact(
        self, project_id: UUID, target_type: GovernanceTargetType | str, target_id: UUID
    ) -> tuple[DownstreamImpactTarget, ...]:
        project = ProjectId(project_id)
        kind = GovernanceTargetType(target_type)
        with self._uow_factory() as uow:
            self._resolvers.resolve(uow.governance, project, kind, target_id)
            rows = uow.governance.downstream_impact_rows(project_id, kind.value, target_id)
        grouped: dict[
            tuple[GovernanceTargetType, UUID], tuple[str | None, list[DownstreamImpactPath]]
        ] = {}
        for raw_row in rows:
            row = cast(Sequence[Any], raw_row)
            result_type = GovernanceTargetType(str(row[0]))
            result_id = row[1]
            content_hash = str(row[5]) if len(row) > 5 and row[5] is not None else None
            path = DownstreamImpactPath(
                result_type,
                result_id,
                row[2],
                row[3],
                row[4],
                content_hash,
                row[6],
                row[7],
                row[8],
            )
            key = (result_type, result_id)
            expected_hash, paths = grouped.setdefault(key, (content_hash, []))
            if expected_hash != content_hash:
                raise ValueError("inconsistent downstream target content hash")
            paths.append(path)
        return tuple(
            DownstreamImpactTarget(key[0], key[1], content_hash, tuple(paths))
            for key, (content_hash, paths) in sorted(
                grouped.items(), key=lambda item: (item[0][0].value, str(item[0][1]))
            )
        )

    def validity_projection(
        self, project_id: UUID, target_type: GovernanceTargetType | str, target_id: UUID
    ) -> ValidityProjection:
        project = ProjectId(project_id)
        kind = GovernanceTargetType(target_type)
        with self._uow_factory() as uow:
            self._resolvers.resolve(uow.governance, project, kind, target_id)
            rows = uow.governance.validity_rows(project_id, kind.value, target_id)
        active: list[tuple[UUID, str, UUID | None]] = []
        corrections: set[UUID] = set()
        for raw_row in rows:
            row = cast(Sequence[Any], raw_row)
            if len(row) == 5:
                corrections.add(row[4])
            elif row[3] != "dismissed":
                active.append((row[0], row[1], row[2]))
        if not active:
            state = ValidityState.NOT_ASSESSED
        else:
            mapping = {
                "no_impact": ValidityState.UNAFFECTED,
                "stale": ValidityState.STALE,
                "invalid": ValidityState.INVALID,
                "requires_review": ValidityState.REQUIRES_REVIEW,
                "unknown": ValidityState.UNKNOWN,
            }
            precedence = {
                ValidityState.UNAFFECTED: 1,
                ValidityState.UNKNOWN: 2,
                ValidityState.REQUIRES_REVIEW: 3,
                ValidityState.STALE: 4,
                ValidityState.INVALID: 5,
            }
            state = max((mapping[row[1]] for row in active), key=precedence.__getitem__)
        return ValidityProjection(
            kind,
            target_id,
            state,
            tuple(sorted({row[2] for row in active if row[2] is not None}, key=str)),
            tuple(sorted({row[0] for row in active}, key=str)),
            tuple(sorted(corrections, key=str)),
        )
