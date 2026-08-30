"""PR-14 governance commands and closed target resolver registry."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

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

    def resolve(self, repository: GovernanceRepository, target_id: UUID) -> object | None: ...


@dataclass(frozen=True, slots=True)
class _MethodResolver:
    target_type: GovernanceTargetType
    method: Callable[[GovernanceRepository, UUID], object | None]

    def resolve(self, repository: GovernanceRepository, target_id: UUID) -> object | None:
        return self.method(repository, target_id)


class TargetResolverRegistry:
    def __init__(self) -> None:
        pairs: tuple[
            tuple[
                GovernanceTargetType,
                Callable[[GovernanceRepository, UUID], object | None],
            ],
            ...,
        ] = (
            (
                GovernanceTargetType.EXPERIMENT_SPEC_VERSION,
                lambda repository, target_id: repository.resolve_experiment_spec_version(target_id),
            ),
            (
                GovernanceTargetType.DATASET_SNAPSHOT,
                lambda repository, target_id: repository.resolve_dataset_snapshot(target_id),
            ),
            (
                GovernanceTargetType.ARTIFACT_VERSION,
                lambda repository, target_id: repository.resolve_artifact_version(target_id),
            ),
            (
                GovernanceTargetType.RUN,
                lambda repository, target_id: repository.resolve_run(target_id),
            ),
            (
                GovernanceTargetType.METRIC_DEFINITION_VERSION,
                lambda repository, target_id: repository.resolve_metric_definition_version(
                    target_id
                ),
            ),
            (
                GovernanceTargetType.MEASUREMENT,
                lambda repository, target_id: repository.resolve_measurement(target_id),
            ),
            (
                GovernanceTargetType.STATISTICAL_RESULT,
                lambda repository, target_id: repository.resolve_statistical_result(target_id),
            ),
            (
                GovernanceTargetType.CLAIM_VERSION,
                lambda repository, target_id: repository.resolve_claim_version(target_id),
            ),
        )
        self._resolvers = {kind: _MethodResolver(kind, method) for kind, method in pairs}

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
        try:
            kind = GovernanceTargetType(target_type)
        except ValueError as exc:
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR, "unsupported governance target type"
            ) from exc
        resolved = self._resolvers[kind].resolve(repository, target_id)
        if not isinstance(resolved, ResolvedGovernanceTarget):
            raise ResearchBaseError(ErrorCode.NOT_FOUND, f"{kind.value} target not found")
        if resolved.project_id != requested_project_id:
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR,
                "governance target belongs to another project",
            )
        return resolved


@dataclass(frozen=True, slots=True)
class CreateAuditFindingCommand:
    project_id: UUID
    finding_type: str
    severity: AuditFindingSeverity | str
    title: str
    description: str
    target_type: GovernanceTargetType | str
    target_id: UUID
    context: ExecutionContext


@dataclass(frozen=True, slots=True)
class TransitionAuditFindingCommand:
    finding_id: UUID
    status: AuditFindingStatus | str
    expected_row_version: int
    context: ExecutionContext


@dataclass(frozen=True, slots=True)
class ProposedImpactTarget:
    target_type: GovernanceTargetType | str
    target_id: UUID
    impact_kind: ImpactKind | str


@dataclass(frozen=True, slots=True)
class CreateImpactAssessmentCommand:
    project_id: UUID
    audit_finding_id: UUID | None
    assessment_payload: object
    conclusion: ImpactAssessmentConclusion | str
    targets: tuple[ProposedImpactTarget, ...]
    context: ExecutionContext


@dataclass(frozen=True, slots=True)
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
            if finding_id is not None:
                finding = uow.governance.get_audit_finding(finding_id)
                if not isinstance(finding, AuditFinding):
                    raise ResearchBaseError(ErrorCode.NOT_FOUND, "audit finding not found")
                if finding.project_id != project_id:
                    raise ResearchBaseError(
                        ErrorCode.VALIDATION_ERROR,
                        "audit finding belongs to another project",
                    )
            assessment_id = new_typed_id(ImpactAssessmentId)
            targets = tuple(
                ImpactTarget(
                    assessment_id,
                    resolved.target_type,
                    resolved.target_id,
                    resolved.content_hash,
                    ImpactKind(proposed.impact_kind),
                )
                for proposed in command.targets
                for resolved in (
                    self.target_resolvers.resolve(
                        uow.governance, project_id, proposed.target_type, proposed.target_id
                    ),
                )
            )
            identities = {(target.target_type, target.target_id) for target in targets}
            if len(identities) != len(targets):
                raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, "duplicate impact target")
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
