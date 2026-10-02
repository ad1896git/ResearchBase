"""PR-14 governance records, lifecycles, and deterministic material hashes."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from typing import NewType, Self
from uuid import UUID

from researchbase.domain.organization import ProjectId
from researchbase.foundation.canonical_json import canonical_json_bytes
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.frozen_json import freeze_json, thaw_json
from researchbase.foundation.hashing import ContentHash, sha256_canonical_json
from researchbase.foundation.ids import ActorId
from researchbase.foundation.time import to_utc

AuditFindingId = NewType("AuditFindingId", UUID)
ImpactAssessmentId = NewType("ImpactAssessmentId", UUID)
CorrectionRecordId = NewType("CorrectionRecordId", UUID)


class GovernanceTargetType(StrEnum):
    EXPERIMENT_SPEC_VERSION = "experiment_spec_version"
    DATASET_SNAPSHOT = "dataset_snapshot"
    ARTIFACT_VERSION = "artifact_version"
    RUN = "run"
    METRIC_DEFINITION_VERSION = "metric_definition_version"
    MEASUREMENT = "measurement"
    STATISTICAL_RESULT = "statistical_result"
    CLAIM_VERSION = "claim_version"


class AuditFindingSeverity(StrEnum):
    INFO = "info"
    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"


class AuditFindingStatus(StrEnum):
    OPEN = "open"
    CONFIRMED = "confirmed"
    DISMISSED = "dismissed"
    RESOLVED = "resolved"


class ImpactAssessmentConclusion(StrEnum):
    NO_IMPACT = "no_impact"
    STALE = "stale"
    INVALID = "invalid"
    REQUIRES_REVIEW = "requires_review"
    UNKNOWN = "unknown"


class ImpactKind(StrEnum):
    DIRECT = "direct"
    DOWNSTREAM = "downstream"
    STALE = "stale"
    INVALID = "invalid"
    REQUIRES_REVIEW = "requires_review"


class CorrectionType(StrEnum):
    FACTUAL = "factual"
    METADATA = "metadata"
    COMPUTATIONAL = "computational"
    ATTRIBUTION = "attribution"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class ResolvedGovernanceTarget:
    target_type: GovernanceTargetType
    target_id: UUID
    project_id: ProjectId
    content_hash: ContentHash | None
    version_identity: UUID | None = None


@dataclass(frozen=True, slots=True)
class AuditFinding:
    id: AuditFindingId
    project_id: ProjectId
    finding_type: str
    severity: AuditFindingSeverity
    title: str
    description: str
    target_type: GovernanceTargetType
    target_id: UUID
    target_content_hash: ContentHash | None
    status: AuditFindingStatus
    created_by: ActorId
    created_at: datetime
    row_version: int = 1

    def __post_init__(self) -> None:
        _require_uuid(self.id, "finding id")
        _require_uuid(self.project_id, "project id")
        _require_uuid(self.target_id, "target id")
        _require_uuid(self.created_by, "created_by")
        object.__setattr__(self, "id", AuditFindingId(self.id))
        object.__setattr__(self, "project_id", ProjectId(self.project_id))
        object.__setattr__(self, "created_by", ActorId(self.created_by))
        object.__setattr__(self, "severity", AuditFindingSeverity(self.severity))
        object.__setattr__(self, "status", AuditFindingStatus(self.status))
        object.__setattr__(self, "target_type", GovernanceTargetType(self.target_type))
        object.__setattr__(self, "created_at", to_utc(self.created_at))
        if self.target_content_hash is not None:
            object.__setattr__(self, "target_content_hash", ContentHash(self.target_content_hash))
        _require_text(self.finding_type, "finding_type", 64)
        _require_text(self.title, "title", 255)
        _require_text(self.description, "description")
        if isinstance(self.row_version, bool) or self.row_version < 1:
            raise ValueError("row_version must be positive")

    def transition_to(self, target: AuditFindingStatus) -> Self:
        target = AuditFindingStatus(target)
        allowed = {
            AuditFindingStatus.OPEN: {
                AuditFindingStatus.CONFIRMED,
                AuditFindingStatus.DISMISSED,
            },
            AuditFindingStatus.CONFIRMED: {
                AuditFindingStatus.RESOLVED,
                AuditFindingStatus.DISMISSED,
            },
            AuditFindingStatus.DISMISSED: set(),
            AuditFindingStatus.RESOLVED: set(),
        }
        if target not in allowed[self.status]:
            raise ResearchBaseError(
                ErrorCode.INVALID_STATE_TRANSITION,
                f"cannot transition audit finding from {self.status.value} to {target.value}",
            )
        return replace(self, status=target, row_version=self.row_version + 1)


@dataclass(frozen=True, slots=True)
class ImpactTarget:
    impact_assessment_id: ImpactAssessmentId
    target_type: GovernanceTargetType
    target_id: UUID
    target_content_hash: ContentHash | None
    impact_kind: ImpactKind

    def __post_init__(self) -> None:
        _require_uuid(self.impact_assessment_id, "impact assessment id")
        _require_uuid(self.target_id, "target id")
        object.__setattr__(
            self, "impact_assessment_id", ImpactAssessmentId(self.impact_assessment_id)
        )
        object.__setattr__(self, "target_type", GovernanceTargetType(self.target_type))
        object.__setattr__(self, "impact_kind", ImpactKind(self.impact_kind))
        if self.target_content_hash is not None:
            object.__setattr__(self, "target_content_hash", ContentHash(self.target_content_hash))

    def semantic_row(self) -> dict[str, str | None]:
        return {
            "target_type": self.target_type.value,
            "target_id": str(self.target_id),
            "target_content_hash": (
                str(self.target_content_hash) if self.target_content_hash is not None else None
            ),
            "impact_kind": self.impact_kind.value,
        }


@dataclass(frozen=True, slots=True)
class ImpactAssessment:
    id: ImpactAssessmentId
    project_id: ProjectId
    audit_finding_id: AuditFindingId | None
    assessment_payload: object
    conclusion: ImpactAssessmentConclusion
    created_by: ActorId
    created_at: datetime
    content_hash: ContentHash
    targets: tuple[ImpactTarget, ...]

    def __post_init__(self) -> None:
        _require_uuid(self.id, "impact assessment id")
        _require_uuid(self.project_id, "project id")
        _require_uuid(self.created_by, "created_by")
        if self.audit_finding_id is not None:
            _require_uuid(self.audit_finding_id, "audit finding id")
            object.__setattr__(self, "audit_finding_id", AuditFindingId(self.audit_finding_id))
        object.__setattr__(self, "id", ImpactAssessmentId(self.id))
        object.__setattr__(self, "project_id", ProjectId(self.project_id))
        object.__setattr__(self, "created_by", ActorId(self.created_by))
        object.__setattr__(self, "conclusion", ImpactAssessmentConclusion(self.conclusion))
        object.__setattr__(self, "created_at", to_utc(self.created_at))
        object.__setattr__(self, "content_hash", ContentHash(self.content_hash))
        object.__setattr__(self, "targets", tuple(self.targets))
        object.__setattr__(self, "assessment_payload", freeze_json(self.assessment_payload))
        _validate_json(thaw_json(self.assessment_payload), "assessment_payload")
        expected = calculate_impact_assessment_hash(
            project_id=self.project_id,
            audit_finding_id=self.audit_finding_id,
            assessment_payload=thaw_json(self.assessment_payload),
            conclusion=self.conclusion,
            targets=self.targets,
        )
        if self.content_hash != expected:
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR,
                "content_hash does not match impact assessment material",
                {"field": "content_hash"},
            )


@dataclass(frozen=True, slots=True)
class CorrectionRecord:
    id: CorrectionRecordId
    project_id: ProjectId
    target_type: GovernanceTargetType
    target_id: UUID
    target_content_hash: ContentHash | None
    correction_type: CorrectionType
    corrected_assertion: object
    reason: str
    created_by: ActorId
    created_at: datetime
    content_hash: ContentHash

    def __post_init__(self) -> None:
        _require_uuid(self.id, "correction id")
        _require_uuid(self.project_id, "project id")
        _require_uuid(self.target_id, "target id")
        _require_uuid(self.created_by, "created_by")
        object.__setattr__(self, "id", CorrectionRecordId(self.id))
        object.__setattr__(self, "project_id", ProjectId(self.project_id))
        object.__setattr__(self, "target_type", GovernanceTargetType(self.target_type))
        object.__setattr__(self, "correction_type", CorrectionType(self.correction_type))
        object.__setattr__(self, "created_by", ActorId(self.created_by))
        object.__setattr__(self, "created_at", to_utc(self.created_at))
        object.__setattr__(self, "content_hash", ContentHash(self.content_hash))
        if self.target_content_hash is not None:
            object.__setattr__(self, "target_content_hash", ContentHash(self.target_content_hash))
        _require_text(self.reason, "reason")
        object.__setattr__(self, "corrected_assertion", freeze_json(self.corrected_assertion))
        _validate_json(thaw_json(self.corrected_assertion), "corrected_assertion")
        expected = calculate_correction_record_hash(
            project_id=self.project_id,
            target_type=self.target_type,
            target_id=self.target_id,
            target_content_hash=self.target_content_hash,
            correction_type=self.correction_type,
            corrected_assertion=thaw_json(self.corrected_assertion),
            reason=self.reason,
        )
        if self.content_hash != expected:
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR,
                "content_hash does not match correction record material",
                {"field": "content_hash"},
            )


def calculate_impact_assessment_hash(
    *,
    project_id: ProjectId,
    audit_finding_id: AuditFindingId | None,
    assessment_payload: object,
    conclusion: ImpactAssessmentConclusion,
    targets: tuple[ImpactTarget, ...],
) -> ContentHash:
    assessment_payload = _plain_json(assessment_payload, "assessment_payload")
    rows = [target.semantic_row() for target in targets]
    rows.sort(
        key=lambda row: (
            row["target_type"] or "",
            row["target_id"] or "",
            row["target_content_hash"] is not None,
            row["target_content_hash"] or "",
            row["impact_kind"] or "",
        )
    )
    return sha256_canonical_json(
        {
            "project_id": str(project_id),
            "audit_finding_id": (str(audit_finding_id) if audit_finding_id is not None else None),
            "assessment_payload": assessment_payload,
            "conclusion": ImpactAssessmentConclusion(conclusion).value,
            "impact_targets": rows,
        }
    )


def calculate_correction_record_hash(
    *,
    project_id: ProjectId,
    target_type: GovernanceTargetType,
    target_id: UUID,
    target_content_hash: ContentHash | None,
    correction_type: CorrectionType,
    corrected_assertion: object,
    reason: str,
) -> ContentHash:
    corrected_assertion = _plain_json(corrected_assertion, "corrected_assertion")
    return sha256_canonical_json(
        {
            "project_id": str(project_id),
            "target_type": GovernanceTargetType(target_type).value,
            "target_id": str(target_id),
            "target_content_hash": (
                str(target_content_hash) if target_content_hash is not None else None
            ),
            "correction_type": CorrectionType(correction_type).value,
            "corrected_assertion": corrected_assertion,
            "reason": reason,
        }
    )


def _validate_json(value: object, field: str) -> None:
    try:
        canonical_json_bytes(value)
    except (TypeError, ValueError) as exc:
        raise ResearchBaseError(
            ErrorCode.VALIDATION_ERROR,
            f"{field} is not valid canonical JSON",
            {"field": field},
        ) from exc


def _plain_json(value: object, field: str) -> object:
    try:
        plain = thaw_json(value)
    except (TypeError, ValueError) as exc:
        raise ResearchBaseError(
            ErrorCode.VALIDATION_ERROR,
            f"{field} is not valid canonical JSON",
            {"field": field},
        ) from exc
    _validate_json(plain, field)
    return plain


def _require_uuid(value: object, field: str) -> None:
    if not isinstance(value, UUID):
        raise TypeError(f"{field} must be UUID-compatible")


def _require_text(value: object, field: str, maximum: int | None = None) -> None:
    if (
        not isinstance(value, str)
        or not value.strip()
        or (maximum is not None and len(value) > maximum)
    ):
        suffix = f" of at most {maximum} characters" if maximum is not None else ""
        raise ResearchBaseError(
            ErrorCode.VALIDATION_ERROR,
            f"{field} must be non-blank text{suffix}",
            {"field": field},
        )
