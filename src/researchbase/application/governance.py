"""PR-14 governance commands and closed target resolver registry."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from researchbase.application.config import application_dto_dataclass
from researchbase.application.ports import GovernanceRepository, UnitOfWork
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
    calculate_correction_record_hash,
    calculate_impact_assessment_hash,
)
from researchbase.domain.organization import ProjectId
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.execution_context import ExecutionContext
from researchbase.foundation.ids import ActorId, new_typed_id
from researchbase.foundation.time import Clock


class TargetResolver(Protocol):
    target_type: GovernanceTargetType

    def resolve(
        self, repository: GovernanceRepository, target_id: UUID
    ) -> ResolvedGovernanceTarget | None: ...

    def resolve_many(
        self, repository: GovernanceRepository, target_ids: set[UUID]
    ) -> list[ResolvedGovernanceTarget]: ...


@dataclass(frozen=True, slots=True)
class _MethodResolver:
    target_type: GovernanceTargetType
    method: Callable[[GovernanceRepository, UUID], ResolvedGovernanceTarget | None]
    batch_method: Callable[[GovernanceRepository, set[UUID]], list[ResolvedGovernanceTarget]]

    def resolve(
        self, repository: GovernanceRepository, target_id: UUID
    ) -> ResolvedGovernanceTarget | None:
        return self.method(repository, target_id)

    def resolve_many(
        self, repository: GovernanceRepository, target_ids: set[UUID]
    ) -> list[ResolvedGovernanceTarget]:
        return self.batch_method(repository, target_ids)


class TargetResolverRegistry:
    def __init__(self) -> None:
        pairs: tuple[
            tuple[
                GovernanceTargetType,
                Callable[[GovernanceRepository, UUID], ResolvedGovernanceTarget | None],
                Callable[[GovernanceRepository, set[UUID]], list[ResolvedGovernanceTarget]],
            ],
            ...,
        ] = (
            (
                GovernanceTargetType.EXPERIMENT_SPEC_VERSION,
                lambda repository, target_id: repository.resolve_experiment_spec_version(target_id),
                lambda repository, target_ids: repository.resolve_experiment_spec_versions(
                    target_ids
                ),
            ),
            (
                GovernanceTargetType.DATASET_SNAPSHOT,
                lambda repository, target_id: repository.resolve_dataset_snapshot(target_id),
                lambda repository, target_ids: repository.resolve_dataset_snapshots(target_ids),
            ),
            (
                GovernanceTargetType.ARTIFACT_VERSION,
                lambda repository, target_id: repository.resolve_artifact_version(target_id),
                lambda repository, target_ids: repository.resolve_artifact_versions(target_ids),
            ),
            (
                GovernanceTargetType.RUN,
                lambda repository, target_id: repository.resolve_run(target_id),
                lambda repository, target_ids: repository.resolve_runs(target_ids),
            ),
            (
                GovernanceTargetType.METRIC_DEFINITION_VERSION,
                lambda repository, target_id: repository.resolve_metric_definition_version(
                    target_id
                ),
                lambda repository, target_ids: repository.resolve_metric_definition_versions(
                    target_ids
                ),
            ),
            (
                GovernanceTargetType.MEASUREMENT,
                lambda repository, target_id: repository.resolve_measurement(target_id),
                lambda repository, target_ids: repository.resolve_measurements(target_ids),
            ),
            (
                GovernanceTargetType.STATISTICAL_RESULT,
                lambda repository, target_id: repository.resolve_statistical_result(target_id),
                lambda repository, target_ids: repository.resolve_statistical_results(target_ids),
            ),
            (
                GovernanceTargetType.CLAIM_VERSION,
                lambda repository, target_id: repository.resolve_claim_version(target_id),
                lambda repository, target_ids: repository.resolve_claim_versions(target_ids),
            ),
        )
        self._resolvers = {
            kind: _MethodResolver(kind, method, batch_method)
            for kind, method, batch_method in pairs
        }

    @staticmethod
    def normalize_type(target_type: GovernanceTargetType | str) -> GovernanceTargetType:
        try:
            return GovernanceTargetType(target_type)
        except ValueError as exc:
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR, "unsupported governance target type"
            ) from exc

    @property
    def supported_types(self) -> frozenset[GovernanceTargetType]:
        return frozenset(self._resolvers)

    def resolve(
        self,
        repository: GovernanceRepository,
        requested_project_id: ProjectId,
        target_type: GovernanceTargetType | str,
        target_id: UUID,
    ) -> ResolvedGovernanceTarget:
        kind = self.normalize_type(target_type)
        resolved = self._resolvers[kind].resolve(repository, target_id)
        if not isinstance(resolved, ResolvedGovernanceTarget):
            raise ResearchBaseError(ErrorCode.NOT_FOUND, f"{kind.value} target not found")
        if resolved.project_id != requested_project_id:
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR,
                "governance target belongs to another project",
            )
        return resolved

    def resolve_many(
        self,
        repository: GovernanceRepository,
        requested_project_id: ProjectId,
        targets: Iterable[tuple[GovernanceTargetType | str, UUID]],
    ) -> dict[tuple[GovernanceTargetType, UUID], ResolvedGovernanceTarget]:
        grouped: dict[GovernanceTargetType, set[UUID]] = {}
        for target_type, target_id in targets:
            kind = self.normalize_type(target_type)
            grouped.setdefault(kind, set()).add(target_id)

        resolved: dict[tuple[GovernanceTargetType, UUID], ResolvedGovernanceTarget] = {}
        for kind in sorted(grouped, key=lambda item: item.value):
            items = self._resolvers[kind].resolve_many(repository, grouped[kind])
            by_id = {item.target_id: item for item in items}
            for target_id in sorted(grouped[kind], key=str):
                item = by_id.get(target_id)
                if item is None:
                    raise ResearchBaseError(ErrorCode.NOT_FOUND, f"{kind.value} target not found")
                if item.project_id != requested_project_id:
                    raise ResearchBaseError(
                        ErrorCode.VALIDATION_ERROR,
                        "governance target belongs to another project",
                    )
                resolved[(kind, target_id)] = item
        return resolved


@application_dto_dataclass
class CreateAuditFindingCommand:
    project_id: UUID
    finding_type: str
    severity: AuditFindingSeverity | str
    title: str
    description: str
    target_type: GovernanceTargetType | str
    target_id: UUID
    context: ExecutionContext


@application_dto_dataclass
class TransitionAuditFindingCommand:
    finding_id: UUID
    status: AuditFindingStatus | str
    expected_row_version: int
    context: ExecutionContext


@application_dto_dataclass
class ProposedImpactTarget:
    target_type: GovernanceTargetType | str
    target_id: UUID
    impact_kind: ImpactKind | str


@application_dto_dataclass
class CreateImpactAssessmentCommand:
    project_id: UUID
    audit_finding_id: UUID | None
    assessment_payload: object
    conclusion: ImpactAssessmentConclusion | str
    targets: tuple[ProposedImpactTarget, ...]
    context: ExecutionContext


@application_dto_dataclass
class CreateCorrectionRecordCommand:
    project_id: UUID
    target_type: GovernanceTargetType | str
    target_id: UUID
    correction_type: CorrectionType | str
    corrected_assertion: object
    reason: str
    context: ExecutionContext


class GovernanceService:
    def __init__(self, uow_factory: Callable[[], UnitOfWork], clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self.target_resolvers = TargetResolverRegistry()

    def create_audit_finding(self, command: CreateAuditFindingCommand) -> AuditFinding:
        project_id, actor_id = ProjectId(command.project_id), ActorId(command.context.actor_id)
        with self._uow_factory() as uow:
            self._require_context(uow, project_id, actor_id)
            target = self.target_resolvers.resolve(
                uow.governance, project_id, command.target_type, command.target_id
            )
            finding = AuditFinding(
                new_typed_id(AuditFindingId),
                project_id,
                command.finding_type,
                AuditFindingSeverity(command.severity),
                command.title,
                command.description,
                target.target_type,
                target.target_id,
                target.content_hash,
                AuditFindingStatus.OPEN,
                actor_id,
                self._clock.now(),
                1,
            )
            uow.governance.add_audit_finding(finding)
            uow.commit()
            return finding

    def transition_audit_finding(self, command: TransitionAuditFindingCommand) -> AuditFinding:
        actor_id = ActorId(command.context.actor_id)
        with self._uow_factory() as uow:
            finding = uow.governance.get_audit_finding(command.finding_id)
            if not isinstance(finding, AuditFinding):
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "audit finding not found")
            self._require_context(uow, finding.project_id, actor_id)
            if finding.row_version != command.expected_row_version:
                raise ResearchBaseError(
                    ErrorCode.CONCURRENT_MODIFICATION,
                    "stale audit finding row_version",
                )
            changed = finding.transition_to(AuditFindingStatus(command.status))
            uow.governance.transition_audit_finding(changed, command.expected_row_version)
            uow.commit()
            return changed

    def create_impact_assessment(self, command: CreateImpactAssessmentCommand) -> ImpactAssessment:
        project_id, actor_id = ProjectId(command.project_id), ActorId(command.context.actor_id)
        with self._uow_factory() as uow:
            self._require_context(uow, project_id, actor_id)
            finding_id = (
                AuditFindingId(command.audit_finding_id) if command.audit_finding_id else None
            )
            assessment_id = new_typed_id(ImpactAssessmentId)
            normalized = tuple(
                (
                    self.target_resolvers.normalize_type(proposed.target_type),
                    proposed.target_id,
                    ImpactKind(proposed.impact_kind),
                )
                for proposed in command.targets
            )
            identities = {(target_type, target_id) for target_type, target_id, _ in normalized}
            if len(identities) != len(normalized):
                raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, "duplicate impact target")
            resolved_targets = self.target_resolvers.resolve_many(
                uow.governance,
                project_id,
                ((target_type, target_id) for target_type, target_id, _ in normalized),
            )
            if finding_id is not None:
                finding = uow.governance.get_audit_finding(finding_id)
                if not isinstance(finding, AuditFinding):
                    raise ResearchBaseError(ErrorCode.NOT_FOUND, "audit finding not found")
                if finding.project_id != project_id:
                    raise ResearchBaseError(
                        ErrorCode.VALIDATION_ERROR,
                        "audit finding belongs to another project",
                    )
            targets = tuple(
                sorted(
                    (
                        ImpactTarget(
                            assessment_id,
                            resolved_targets[(target_type, target_id)].target_type,
                            target_id,
                            resolved_targets[(target_type, target_id)].content_hash,
                            impact_kind,
                        )
                        for target_type, target_id, impact_kind in normalized
                    ),
                    key=lambda target: (
                        target.target_type.value,
                        str(target.target_id),
                        target.impact_kind.value,
                    ),
                )
            )
            conclusion = ImpactAssessmentConclusion(command.conclusion)
            content_hash = calculate_impact_assessment_hash(
                project_id=project_id,
                audit_finding_id=finding_id,
                assessment_payload=command.assessment_payload,
                conclusion=conclusion,
                targets=targets,
            )
            assessment = ImpactAssessment(
                assessment_id,
                project_id,
                finding_id,
                command.assessment_payload,
                conclusion,
                actor_id,
                self._clock.now(),
                content_hash,
                targets,
            )
            uow.governance.add_impact_assessment(assessment)
            uow.commit()
            return assessment

    def create_correction_record(self, command: CreateCorrectionRecordCommand) -> CorrectionRecord:
        project_id, actor_id = ProjectId(command.project_id), ActorId(command.context.actor_id)
        with self._uow_factory() as uow:
            self._require_context(uow, project_id, actor_id)
            target = self.target_resolvers.resolve(
                uow.governance, project_id, command.target_type, command.target_id
            )
            correction_type = CorrectionType(command.correction_type)
            content_hash = calculate_correction_record_hash(
                project_id=project_id,
                target_type=target.target_type,
                target_id=target.target_id,
                target_content_hash=target.content_hash,
                correction_type=correction_type,
                corrected_assertion=command.corrected_assertion,
                reason=command.reason,
            )
            correction = CorrectionRecord(
                new_typed_id(CorrectionRecordId),
                project_id,
                target.target_type,
                target.target_id,
                target.content_hash,
                correction_type,
                command.corrected_assertion,
                command.reason,
                actor_id,
                self._clock.now(),
                content_hash,
            )
            uow.governance.add_correction_record(correction)
            uow.commit()
            return correction

    @staticmethod
    def _require_context(uow: UnitOfWork, project_id: ProjectId, actor_id: ActorId) -> None:
        if uow.projects.get(project_id) is None:
            raise ResearchBaseError(ErrorCode.NOT_FOUND, "project not found")
        if uow.actors.get(actor_id) is None:
            raise ResearchBaseError(ErrorCode.NOT_FOUND, "actor not found")
