from __future__ import annotations

# Keyword-material mutation dictionaries intentionally exercise heterogeneous fields.
# pyright: reportArgumentType=false
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from tests.oracles.pr14_governance_hash_oracle import (
    correction_record_hash,
    impact_assessment_hash,
)

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
    calculate_correction_record_hash,
    calculate_impact_assessment_hash,
)
from researchbase.domain.organization import ProjectId
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import ContentHash
from researchbase.foundation.ids import ActorId

NOW = datetime(2026, 8, 30, tzinfo=UTC)
PROJECT_ID = UUID("00000000-0000-0000-0000-000000000101")
ACTOR_ID = UUID("00000000-0000-0000-0000-000000000102")
TARGET_ID = UUID("00000000-0000-0000-0000-000000000103")
FINDING_ID = UUID("00000000-0000-0000-0000-000000000104")
ASSESSMENT_ID = UUID("00000000-0000-0000-0000-000000000105")
CORRECTION_ID = UUID("00000000-0000-0000-0000-000000000106")
TARGET_HASH = ContentHash("a" * 64)


def impact_target(**changes: object) -> ImpactTarget:
    values: dict[str, object] = {
        "impact_assessment_id": ImpactAssessmentId(ASSESSMENT_ID),
        "target_type": GovernanceTargetType.ARTIFACT_VERSION,
        "target_id": TARGET_ID,
        "target_content_hash": TARGET_HASH,
        "impact_kind": ImpactKind.DIRECT,
    }
    values.update(changes)
    return ImpactTarget(**values)  # type: ignore[arg-type]


def test_governance_enums_are_exactly_closed() -> None:
    assert {item.value for item in GovernanceTargetType} == {
        "experiment_spec_version",
        "dataset_snapshot",
        "artifact_version",
        "run",
        "metric_definition_version",
        "measurement",
        "statistical_result",
        "claim_version",
    }
    assert {item.value for item in AuditFindingSeverity} == {
        "info",
        "minor",
        "major",
        "critical",
    }
    assert {item.value for item in AuditFindingStatus} == {
        "open",
        "confirmed",
        "dismissed",
        "resolved",
    }
    assert {item.value for item in ImpactAssessmentConclusion} == {
        "no_impact",
        "stale",
        "invalid",
        "requires_review",
        "unknown",
    }
    assert {item.value for item in ImpactKind} == {
        "direct",
        "downstream",
        "stale",
        "invalid",
        "requires_review",
    }
    assert {item.value for item in CorrectionType} == {
        "factual",
        "metadata",
        "computational",
        "attribution",
        "other",
    }


def test_audit_finding_lifecycle_is_controlled_and_material_is_frozen() -> None:
    finding = AuditFinding(
        id=AuditFindingId(FINDING_ID),
        project_id=ProjectId(PROJECT_ID),
        finding_type="code_bug",
        severity=AuditFindingSeverity.CRITICAL,
        title="Code bug",
        description="The exact artifact contains an arithmetic defect.",
        target_type=GovernanceTargetType.ARTIFACT_VERSION,
        target_id=TARGET_ID,
        target_content_hash=TARGET_HASH,
        status=AuditFindingStatus.OPEN,
        created_by=ActorId(ACTOR_ID),
        created_at=NOW,
    )

    confirmed = finding.transition_to(AuditFindingStatus.CONFIRMED)
    resolved = confirmed.transition_to(AuditFindingStatus.RESOLVED)
    assert confirmed.row_version == 2
    assert resolved.row_version == 3
    with pytest.raises(ResearchBaseError) as terminal:
        resolved.transition_to(AuditFindingStatus.OPEN)
    assert terminal.value.code is ErrorCode.INVALID_STATE_TRANSITION
    with pytest.raises(FrozenInstanceError):
        finding.title = "rewritten"  # type: ignore[misc]


def test_impact_assessment_hash_matches_independent_oracle_and_ignores_order() -> None:
    second = impact_target(
        target_type=GovernanceTargetType.CLAIM_VERSION,
        target_id=UUID("00000000-0000-0000-0000-000000000107"),
        target_content_hash=ContentHash("b" * 64),
        impact_kind=ImpactKind.STALE,
    )
    targets = (second, impact_target())
    production = calculate_impact_assessment_hash(
        project_id=ProjectId(PROJECT_ID),
        audit_finding_id=AuditFindingId(FINDING_ID),
        assessment_payload={"nested": {"说明": "代码错误"}, "score": 1},
        conclusion=ImpactAssessmentConclusion.STALE,
        targets=targets,
    )
    expected = impact_assessment_hash(
        project_id=str(PROJECT_ID),
        audit_finding_id=str(FINDING_ID),
        assessment_payload={"score": 1, "nested": {"说明": "代码错误"}},
        conclusion="stale",
        targets=[target.semantic_row() for target in reversed(targets)],
    )
    assessment = ImpactAssessment(
        id=ImpactAssessmentId(ASSESSMENT_ID),
        project_id=ProjectId(PROJECT_ID),
        audit_finding_id=AuditFindingId(FINDING_ID),
        assessment_payload={"score": 1, "nested": {"说明": "代码错误"}},
        conclusion=ImpactAssessmentConclusion.STALE,
        created_by=ActorId(ACTOR_ID),
        created_at=NOW,
        content_hash=production,
        targets=targets,
    )

    assert production == ContentHash(expected)
    assert (
        calculate_impact_assessment_hash(
            project_id=assessment.project_id,
            audit_finding_id=assessment.audit_finding_id,
            assessment_payload=assessment.assessment_payload,
            conclusion=assessment.conclusion,
            targets=tuple(reversed(targets)),
        )
        == production
    )
    with pytest.raises(FrozenInstanceError):
        assessment.conclusion = ImpactAssessmentConclusion.INVALID  # type: ignore[misc]


def test_impact_hash_changes_for_each_material_field() -> None:
    base = dict(
        project_id=ProjectId(PROJECT_ID),
        audit_finding_id=AuditFindingId(FINDING_ID),
        assessment_payload={"value": 1},
        conclusion=ImpactAssessmentConclusion.STALE,
        targets=(impact_target(),),
    )
    original = calculate_impact_assessment_hash(**base)
    variants = (
        {**base, "project_id": ProjectId(UUID(int=201))},
        {**base, "audit_finding_id": AuditFindingId(UUID(int=202))},
        {**base, "assessment_payload": {"value": 2}},
        {**base, "conclusion": ImpactAssessmentConclusion.INVALID},
        {**base, "targets": (replace(impact_target(), impact_kind=ImpactKind.INVALID),)},
    )
    assert all(calculate_impact_assessment_hash(**variant) != original for variant in variants)


def test_correction_hash_matches_independent_oracle_and_excludes_metadata() -> None:
    material = dict(
        project_id=ProjectId(PROJECT_ID),
        target_type=GovernanceTargetType.MEASUREMENT,
        target_id=TARGET_ID,
        target_content_hash=None,
        correction_type=CorrectionType.COMPUTATIONAL,
        corrected_assertion={"value": {"μ": 2}, "unit": "ms"},
        reason="Corrected arithmetic",
    )
    production = calculate_correction_record_hash(**material)
    expected = correction_record_hash(
        project_id=str(PROJECT_ID),
        target_type="measurement",
        target_id=str(TARGET_ID),
        target_content_hash=None,
        correction_type="computational",
        corrected_assertion={"unit": "ms", "value": {"μ": 2}},
        reason="Corrected arithmetic",
    )
    first = CorrectionRecord(
        id=CorrectionRecordId(CORRECTION_ID),
        created_by=ActorId(ACTOR_ID),
        created_at=NOW,
        content_hash=production,
        **material,
    )
    second = replace(
        first,
        id=CorrectionRecordId(UUID(int=301)),
        created_by=ActorId(UUID(int=302)),
        created_at=NOW + timedelta(days=1),
    )

    assert production == ContentHash(expected)
    assert first.content_hash == second.content_hash
    with pytest.raises(FrozenInstanceError):
        first.reason = "rewritten"  # type: ignore[misc]


def test_governance_material_rejects_noncanonical_json_and_invalid_hashes() -> None:
    with pytest.raises(ResearchBaseError) as payload_error:
        calculate_impact_assessment_hash(
            project_id=ProjectId(PROJECT_ID),
            audit_finding_id=None,
            assessment_payload={"bad": {1, 2}},
            conclusion=ImpactAssessmentConclusion.UNKNOWN,
            targets=(),
        )
    assert payload_error.value.code is ErrorCode.VALIDATION_ERROR

    with pytest.raises(ResearchBaseError) as hash_error:
        ImpactAssessment(
            id=ImpactAssessmentId(ASSESSMENT_ID),
            project_id=ProjectId(PROJECT_ID),
            audit_finding_id=None,
            assessment_payload={},
            conclusion=ImpactAssessmentConclusion.UNKNOWN,
            created_by=ActorId(ACTOR_ID),
            created_at=NOW,
            content_hash=ContentHash("0" * 64),
            targets=(),
        )
    assert hash_error.value.code is ErrorCode.VALIDATION_ERROR
