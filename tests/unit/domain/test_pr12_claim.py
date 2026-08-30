from __future__ import annotations

import ast
import hashlib
import inspect
import json
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from tests.contracts.version_contract import VersionFixture, assert_version_contract
from tests.oracles import pr12_support_set_oracle as support_set_oracle

from researchbase.domain.claim import (
    Claim,
    ClaimId,
    ClaimVersion,
    ClaimVersionId,
    EvidenceRelation,
    EvidenceRelationId,
    EvidenceRelationType,
    calculate_support_set_hash,
)
from researchbase.domain.measurement import MeasurementId
from researchbase.domain.organization import ProjectId
from researchbase.domain.statistical_result import StatisticalResultId
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import ContentHash
from researchbase.foundation.ids import ActorId
from researchbase.foundation.time import FixedClock
from researchbase.foundation.versioning import VersionStatus

NOW = datetime(2026, 8, 30, tzinfo=UTC)
CLAIM_ID = UUID("00000000-0000-0000-0000-000000000001")
VERSION_ID = UUID("00000000-0000-0000-0000-000000000002")
PROJECT_ID = UUID("00000000-0000-0000-0000-000000000003")
ACTOR_ID = UUID("00000000-0000-0000-0000-000000000004")
MEASUREMENT_ID = UUID("00000000-0000-0000-0000-000000000005")
STATISTICAL_RESULT_ID = UUID("00000000-0000-0000-0000-000000000006")


def independent_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def claim_version(**changes: object) -> ClaimVersion:
    version_id = cast(UUID, changes.get("id", VERSION_ID))
    claim_id = cast(UUID, changes.get("claim_id", CLAIM_ID))
    status = cast(VersionStatus, changes.get("status", VersionStatus.DRAFT))
    statement = cast(str, changes.get("statement", "The treatment improves the outcome"))
    scope = changes.get("scope", {"population": "adult"})
    qualification = cast(str | None, changes.get("qualification"))
    support_set_hash = cast(ContentHash | None, changes.get("support_set_hash"))
    content_hash = cast(ContentHash | None, changes.get("content_hash"))
    frozen_at = cast(datetime | None, changes.get("frozen_at"))
    hash_scheme = cast(str | None, changes.get("hash_scheme"))
    return ClaimVersion(
        id=ClaimVersionId(version_id),
        claim_id=ClaimId(claim_id),
        version_number=1,
        status=status,
        statement=statement,
        scope=scope,
        qualification=qualification,
        support_set_hash=support_set_hash,
        content_hash=content_hash,
        created_by=ActorId(ACTOR_ID),
        created_at=NOW,
        frozen_at=frozen_at,
        hash_scheme=hash_scheme,
    )


def relation(
    *,
    relation_type: EvidenceRelationType = EvidenceRelationType.SUPPORTS,
    qualification: str | None = None,
    relation_id: UUID | None = None,
) -> EvidenceRelation:
    relation_id = relation_id or UUID("00000000-0000-0000-0000-000000000010")
    return EvidenceRelation(
        id=EvidenceRelationId(relation_id),
        claim_version_id=ClaimVersionId(VERSION_ID),
        measurement_id=MeasurementId(MEASUREMENT_ID),
        statistical_result_id=None,
        relation_type=relation_type,
        qualification=qualification,
        created_by=ActorId(ACTOR_ID),
        created_at=NOW,
    )


def test_claim_version_freeze_uses_support_set_in_material_hash() -> None:
    frozen = claim_version().freeze(
        support_set_hash=calculate_support_set_hash([relation()]),
        clock=FixedClock(NOW),
    )
    expected_material = {
        "statement": "The treatment improves the outcome",
        "scope": {"population": "adult"},
        "qualification": None,
        "support_set_hash": str(frozen.support_set_hash),
    }

    assert frozen.status is VersionStatus.FROZEN
    assert frozen.content_hash == ContentHash(independent_sha256(expected_material))
    assert frozen.hash_scheme == "sha256-cjson-v1"
    assert frozen.frozen_at == NOW


def test_support_set_hash_is_independent_of_relation_metadata_and_order() -> None:
    first = relation(relation_id=UUID("00000000-0000-0000-0000-000000000010"))
    second = relation(
        relation_type=EvidenceRelationType.QUALIFIES,
        qualification="under the stated scope",
        relation_id=UUID("00000000-0000-0000-0000-000000000011"),
    )
    changed_metadata = replace(
        second, created_by=ActorId(UUID("00000000-0000-0000-0000-000000000012"))
    )

    assert calculate_support_set_hash([first, second]) == calculate_support_set_hash(
        [changed_metadata, first]
    )


@pytest.mark.parametrize(
    ("source_type", "source_id"),
    [
        ("measurement", str(MEASUREMENT_ID)),
        ("statistical_result", str(STATISTICAL_RESULT_ID)),
    ],
)
def test_evidence_relation_semantic_row_has_exact_source_shape(
    source_type: str, source_id: str
) -> None:
    edge = relation()
    if source_type == "statistical_result":
        edge = replace(
            edge,
            measurement_id=None,
            statistical_result_id=StatisticalResultId(STATISTICAL_RESULT_ID),
        )

    assert edge.semantic_row() == {
        "source_type": source_type,
        "source_id": source_id,
        "relation_type": "supports",
        "qualification": None,
    }


def test_evidence_relation_requires_measurement_xor_statistical_result() -> None:
    with pytest.raises(ResearchBaseError) as both_missing:
        replace(relation(), measurement_id=None)
    assert both_missing.value.code is ErrorCode.VALIDATION_ERROR

    with pytest.raises(ResearchBaseError) as both_present:
        replace(relation(), statistical_result_id=StatisticalResultId(STATISTICAL_RESULT_ID))
    assert both_present.value.code is ErrorCode.VALIDATION_ERROR


def test_evidence_relation_type_is_closed() -> None:
    with pytest.raises(ValueError):
        relation(relation_type="boundary-condition")  # type: ignore[arg-type]


def test_claim_version_lifecycle_and_immutability() -> None:
    frozen = claim_version().freeze(
        support_set_hash=calculate_support_set_hash([]), clock=FixedClock(NOW)
    )
    superseded = frozen.transition_to(VersionStatus.SUPERSEDED)

    assert superseded.status is VersionStatus.SUPERSEDED
    with pytest.raises(ResearchBaseError) as edit_error:
        frozen.edit_material(statement="changed", scope=frozen.scope, qualification=None)
    assert edit_error.value.code is ErrorCode.IMMUTABLE_RECORD
    with pytest.raises(ResearchBaseError):
        superseded.transition_to(VersionStatus.DRAFT)
    with pytest.raises(FrozenInstanceError):
        frozen.statement = "changed"  # type: ignore[misc]


def test_empty_evidence_set_is_a_deterministic_frozen_boundary() -> None:
    first = claim_version().freeze(
        support_set_hash=calculate_support_set_hash([]), clock=FixedClock(NOW)
    )
    second = claim_version().freeze(
        support_set_hash=calculate_support_set_hash([]), clock=FixedClock(NOW)
    )

    assert first.support_set_hash == second.support_set_hash
    assert first.support_set_hash == ContentHash(independent_sha256([]))


def test_claim_identity_validates_uuid_and_positive_row_version() -> None:
    claim = Claim(
        id=ClaimId(CLAIM_ID),
        project_id=ProjectId(PROJECT_ID),
        created_by=ActorId(ACTOR_ID),
        created_at=NOW,
    )
    assert claim.current_version_id is None
    with pytest.raises(ValueError):
        Claim(
            id=ClaimId(CLAIM_ID),
            project_id=ProjectId(PROJECT_ID),
            created_by=ActorId(ACTOR_ID),
            created_at=NOW,
            row_version=0,
        )


class ClaimVersionContractAdapter(VersionFixture):
    def __init__(self, material: object) -> None:
        title = str(cast(dict[str, object], material)["title"])
        self.version = claim_version(id=uuid4(), claim_id=uuid4(), statement=title)
        self._metadata = {"id": self.version.id, "created_at": self.version.created_at}

    @property
    def status(self) -> VersionStatus:
        return self.version.status

    @property
    def content_hash(self) -> ContentHash | None:
        return self.version.content_hash

    @property
    def hash_scheme(self) -> str | None:
        return self.version.hash_scheme

    @property
    def frozen_at(self) -> datetime | None:
        return self.version.frozen_at

    @property
    def non_material_metadata(self) -> object:
        return self._metadata

    def edit_material(self, material: object) -> None:
        values = cast(dict[str, Any], material)
        self.version = self.version.edit_material(
            statement=str(values["title"]),
            scope=self.version.scope,
            qualification=self.version.qualification,
        )

    def freeze(self, clock: object) -> None:
        self.version = self.version.freeze(
            support_set_hash=calculate_support_set_hash([]), clock=cast(Any, clock)
        )

    def transition_to(self, target: VersionStatus) -> None:
        self.version = self.version.transition_to(target)


def test_claim_version_is_directly_wired_to_shared_pr03_contract() -> None:
    assert_version_contract(ClaimVersionContractAdapter)


def test_support_set_oracle_imports_only_standard_library() -> None:
    tree = ast.parse(inspect.getsource(support_set_oracle))
    imported_roots = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_roots.update(
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module is not None
        and node.module != "__future__"
    )

    assert imported_roots == {"collections", "hashlib", "json"}


def test_support_set_hash_matches_an_independent_mixed_evidence_oracle() -> None:
    measurement_edge = relation(relation_id=UUID("00000000-0000-0000-0000-000000000010"))
    measurement_qualified_edge = replace(
        relation(
            relation_type=EvidenceRelationType.QUALIFIES,
            qualification="under the stated scope",
            relation_id=UUID("00000000-0000-0000-0000-000000000011"),
        ),
        measurement_id=MeasurementId(MEASUREMENT_ID),
    )
    statistical_edge = replace(
        relation(
            relation_type=EvidenceRelationType.CONTEXT,
            qualification="secondary analysis",
            relation_id=UUID("00000000-0000-0000-0000-000000000012"),
        ),
        measurement_id=None,
        statistical_result_id=StatisticalResultId(STATISTICAL_RESULT_ID),
    )
    expected_rows = [
        {
            "source_type": "measurement",
            "source_id": str(MEASUREMENT_ID),
            "relation_type": "supports",
            "qualification": None,
        },
        {
            "source_type": "measurement",
            "source_id": str(MEASUREMENT_ID),
            "relation_type": "qualifies",
            "qualification": "under the stated scope",
        },
        {
            "source_type": "statistical_result",
            "source_id": str(STATISTICAL_RESULT_ID),
            "relation_type": "context",
            "qualification": "secondary analysis",
        },
    ]
    relations = [measurement_edge, measurement_qualified_edge, statistical_edge]

    assert str(
        calculate_support_set_hash([statistical_edge, measurement_edge, measurement_qualified_edge])
    ) == support_set_oracle.independent_support_set_hash(expected_rows)
    assert (
        str(calculate_support_set_hash(relations))
        == str(calculate_support_set_hash(list(reversed(relations))))
        == support_set_oracle.independent_support_set_hash(list(reversed(expected_rows)))
    )


@pytest.mark.parametrize("source_type", ["measurement", "statistical_result"])
def test_support_set_hash_oracle_covers_each_single_source_type(source_type: str) -> None:
    edge = relation()
    source_id = MEASUREMENT_ID
    if source_type == "statistical_result":
        source_id = STATISTICAL_RESULT_ID
        edge = replace(
            edge,
            measurement_id=None,
            statistical_result_id=StatisticalResultId(source_id),
        )
    expected_rows = [
        {
            "source_type": source_type,
            "source_id": str(source_id),
            "relation_type": "supports",
            "qualification": None,
        }
    ]

    assert str(calculate_support_set_hash([edge])) == (
        support_set_oracle.independent_support_set_hash(expected_rows)
    )


def test_support_set_hash_independent_oracle_covers_empty_and_null_ordering() -> None:
    expected_rows = [
        {
            "source_type": "measurement",
            "source_id": str(MEASUREMENT_ID),
            "relation_type": "supports",
            "qualification": None,
        },
        {
            "source_type": "measurement",
            "source_id": str(MEASUREMENT_ID),
            "relation_type": "supports",
            "qualification": "qualified",
        },
    ]
    null_relation = relation(relation_id=UUID("00000000-0000-0000-0000-000000000013"))
    qualified_relation = replace(
        relation(
            qualification="qualified",
            relation_id=UUID("00000000-0000-0000-0000-000000000014"),
        ),
        measurement_id=MeasurementId(MEASUREMENT_ID),
    )

    assert str(calculate_support_set_hash([])) == (
        support_set_oracle.independent_support_set_hash([])
    )
    assert str(calculate_support_set_hash([qualified_relation, null_relation])) == (
        support_set_oracle.independent_support_set_hash(expected_rows)
    )


@pytest.mark.parametrize(
    "field",
    ["source_type", "source_id", "relation_type", "qualification"],
)
def test_support_set_hash_changes_for_each_single_semantic_field(field: str) -> None:
    baseline = relation()
    baseline_rows = [
        {
            "source_type": "measurement",
            "source_id": str(MEASUREMENT_ID),
            "relation_type": "supports",
            "qualification": None,
        }
    ]
    changed_rows = [dict(baseline_rows[0])]
    if field == "source_type":
        changed = replace(
            baseline,
            measurement_id=None,
            statistical_result_id=StatisticalResultId(MEASUREMENT_ID),
        )
        changed_rows[0]["source_type"] = "statistical_result"
    elif field == "source_id":
        changed = replace(
            baseline,
            measurement_id=MeasurementId(UUID("00000000-0000-0000-0000-000000000099")),
        )
        changed_rows[0]["source_id"] = "00000000-0000-0000-0000-000000000099"
    elif field == "relation_type":
        changed = replace(baseline, relation_type=EvidenceRelationType.CONTRADICTS)
        changed_rows[0]["relation_type"] = "contradicts"
    else:
        changed = replace(baseline, qualification="different qualification")
        changed_rows[0]["qualification"] = "different qualification"

    baseline_expected = support_set_oracle.independent_support_set_hash(baseline_rows)
    changed_expected = support_set_oracle.independent_support_set_hash(changed_rows)
    assert str(calculate_support_set_hash([baseline])) == baseline_expected
    assert str(calculate_support_set_hash([changed])) == changed_expected
    assert baseline_expected != changed_expected


@pytest.mark.parametrize("field", ["id", "created_by", "created_at"])
def test_support_set_hash_ignores_each_single_metadata_field(field: str) -> None:
    baseline = relation()
    if field == "id":
        changed = replace(
            baseline, id=EvidenceRelationId(UUID("00000000-0000-0000-0000-000000000099"))
        )
    elif field == "created_by":
        changed = replace(
            baseline, created_by=ActorId(UUID("00000000-0000-0000-0000-000000000099"))
        )
    else:
        changed = replace(baseline, created_at=NOW + timedelta(seconds=1))

    expected = support_set_oracle.independent_support_set_hash(
        [
            {
                "source_type": "measurement",
                "source_id": str(MEASUREMENT_ID),
                "relation_type": "supports",
                "qualification": None,
            }
        ]
    )
    assert str(calculate_support_set_hash([baseline])) == expected
    assert str(calculate_support_set_hash([changed])) == expected


def test_claim_hash_has_exact_material_and_canonical_key_order_stability() -> None:
    support_hash = calculate_support_set_hash([])
    left = claim_version(scope={"population": "adult", "region": "EU"}).freeze(
        support_set_hash=support_hash, clock=FixedClock(NOW)
    )
    right = claim_version(scope={"region": "EU", "population": "adult"}).freeze(
        support_set_hash=support_hash, clock=FixedClock(NOW)
    )
    expected = {
        "statement": "The treatment improves the outcome",
        "scope": {"population": "adult", "region": "EU"},
        "qualification": None,
        "support_set_hash": str(support_hash),
    }

    assert left.content_hash == right.content_hash
    assert str(left.content_hash) == independent_sha256(expected)


@pytest.mark.parametrize("field", ["statement", "scope", "qualification", "support_set_hash"])
def test_claim_hash_changes_for_each_single_material_field(field: str) -> None:
    support_hash = calculate_support_set_hash([])
    baseline = claim_version(qualification="baseline").freeze(
        support_set_hash=support_hash, clock=FixedClock(NOW)
    )
    if field == "statement":
        candidate = claim_version(statement="A different treatment").freeze(
            support_set_hash=support_hash, clock=FixedClock(NOW)
        )
    elif field == "scope":
        candidate = claim_version(scope={"population": "child"}, qualification="baseline").freeze(
            support_set_hash=support_hash, clock=FixedClock(NOW)
        )
    elif field == "qualification":
        candidate = claim_version(qualification="different").freeze(
            support_set_hash=support_hash, clock=FixedClock(NOW)
        )
    else:
        candidate = claim_version(qualification="baseline").freeze(
            support_set_hash=ContentHash("f" * 64), clock=FixedClock(NOW)
        )

    assert baseline.content_hash != candidate.content_hash


@pytest.mark.parametrize(
    "field", ["id", "claim_id", "version_number", "created_by", "created_at", "row_version"]
)
def test_claim_hash_ignores_each_single_excluded_metadata_field(field: str) -> None:
    support_hash = calculate_support_set_hash([])
    baseline = claim_version().freeze(support_set_hash=support_hash, clock=FixedClock(NOW))
    if field == "id":
        draft = claim_version(id=UUID("00000000-0000-0000-0000-000000000099"))
    elif field == "claim_id":
        draft = claim_version(claim_id=UUID("00000000-0000-0000-0000-000000000099"))
    elif field == "version_number":
        draft = replace(claim_version(), version_number=2)
    elif field == "created_by":
        draft = replace(
            claim_version(), created_by=ActorId(UUID("00000000-0000-0000-0000-000000000099"))
        )
    elif field == "created_at":
        draft = replace(claim_version(), created_at=NOW + timedelta(seconds=1))
    else:
        draft = replace(claim_version(), row_version=2)

    candidate = draft.freeze(support_set_hash=support_hash, clock=FixedClock(NOW))
    assert baseline.content_hash == candidate.content_hash
