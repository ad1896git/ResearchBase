from enum import StrEnum

import pytest

from researchbase.domain.claim import EvidenceRelationType
from researchbase.domain.governance import (
    AuditFindingSeverity,
    AuditFindingStatus,
    CorrectionType,
    GovernanceTargetType,
    ImpactAssessmentConclusion,
    ImpactKind,
)
from researchbase.domain.identity import ActorType
from researchbase.domain.organization import LifecycleStatus
from researchbase.persistence.enum_codec import (
    PersistedCanonicalEnum,
    decode_persisted_enum,
    encode_persisted_enum,
)
from researchbase.persistence.models import (
    ActorModel,
    AuditFindingModel,
    CorrectionRecordModel,
    EvidenceRelationModel,
    ImpactAssessmentModel,
    ImpactTargetModel,
    ProjectModel,
)


@pytest.mark.parametrize(
    ("enum_type", "member", "persisted"),
    [
        (ActorType, ActorType.HUMAN, "HUMAN"),
        (LifecycleStatus, LifecycleStatus.ACTIVE, "ACTIVE"),
        (
            GovernanceTargetType,
            GovernanceTargetType.EXPERIMENT_SPEC_VERSION,
            "EXPERIMENT_SPEC_VERSION",
        ),
    ],
)
def test_encode_uses_uppercase_member_name_without_changing_enum_value(
    enum_type: type[StrEnum], member: StrEnum, persisted: str
) -> None:
    assert encode_persisted_enum(enum_type, member) == persisted
    assert member.value != persisted


def test_decode_uses_only_explicit_canonical_database_lexemes() -> None:
    assert decode_persisted_enum(ActorType, "HUMAN") is ActorType.HUMAN
    assert (
        decode_persisted_enum(GovernanceTargetType, "EXPERIMENT_SPEC_VERSION")
        is GovernanceTargetType.EXPERIMENT_SPEC_VERSION
    )


@pytest.mark.parametrize("persisted", ["human", "UNKNOWN", "experiment_spec_version"])
def test_decode_rejects_unknown_and_legacy_database_lexemes(persisted: str) -> None:
    with pytest.raises(ValueError):
        decode_persisted_enum(ActorType, persisted)


def test_encode_accepts_the_enum_semantic_value_explicitly() -> None:
    assert encode_persisted_enum(ActorType, "human") == "HUMAN"


def test_encode_rejects_values_that_are_not_members_of_the_declared_enum() -> None:
    with pytest.raises(ValueError):
        encode_persisted_enum(ActorType, "not-an-actor")


@pytest.mark.parametrize(
    ("model", "column", "enum_type"),
    [
        (ActorModel, "actor_type", ActorType),
        (ProjectModel, "lifecycle_status", LifecycleStatus),
        (EvidenceRelationModel, "relation_type", EvidenceRelationType),
        (AuditFindingModel, "severity", AuditFindingSeverity),
        (AuditFindingModel, "target_type", GovernanceTargetType),
        (AuditFindingModel, "status", AuditFindingStatus),
        (ImpactAssessmentModel, "conclusion", ImpactAssessmentConclusion),
        (ImpactTargetModel, "target_type", GovernanceTargetType),
        (ImpactTargetModel, "impact_kind", ImpactKind),
        (CorrectionRecordModel, "target_type", GovernanceTargetType),
        (CorrectionRecordModel, "correction_type", CorrectionType),
    ],
)
def test_approved_persisted_columns_use_explicit_codec(
    model: type, column: str, enum_type: type
) -> None:
    column_type = getattr(model, column).property.columns[0].type
    assert isinstance(column_type, PersistedCanonicalEnum)
    assert column_type.enum_type is enum_type
