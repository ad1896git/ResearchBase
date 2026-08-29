from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import pytest

from researchbase.domain.measurement import MeasurementId
from researchbase.domain.organization import ProjectId
from researchbase.domain.statistical_result import (
    StatisticalResult,
    StatisticalResultId,
    StatisticalResultInput,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import ContentHash
from researchbase.foundation.ids import ActorId

NOW = datetime(2026, 8, 29, 0, 0, tzinfo=UTC)
RESULT_ID = UUID("00000000-0000-0000-0000-000000000001")
PROJECT_ID = UUID("00000000-0000-0000-0000-000000000002")
ACTOR_ID = UUID("00000000-0000-0000-0000-000000000003")
MEASUREMENT_ID = UUID("00000000-0000-0000-0000-000000000004")


def independent_canonical_json_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def material(
    *,
    analysis_type: str = "t_test",
    result_payload: object = None,
    analysis_definition: object = None,
) -> dict[str, object]:
    return {
        "analysis_type": analysis_type,
        "result_payload": {"p_value": 0.01} if result_payload is None else result_payload,
        "analysis_definition": (
            {"method": "student", "alternative": "two-sided"}
            if analysis_definition is None
            else analysis_definition
        ),
    }


def make_result(
    *,
    result_id: UUID = RESULT_ID,
    project_id: UUID = PROJECT_ID,
    created_by: UUID = ACTOR_ID,
    created_at: datetime = NOW,
    **changes: object,
) -> StatisticalResult:
    payload = material(
        analysis_type=cast(str, changes.get("analysis_type", "t_test")),
        result_payload=changes.get("result_payload"),
        analysis_definition=changes.get("analysis_definition"),
    )
    return StatisticalResult(
        id=StatisticalResultId(result_id),
        project_id=ProjectId(project_id),
        analysis_type=cast(str, payload["analysis_type"]),
        result_payload=payload["result_payload"],
        analysis_definition=payload["analysis_definition"],
        content_hash=ContentHash(independent_canonical_json_sha256(payload)),
        created_by=ActorId(created_by),
        created_at=created_at,
    )


def test_statistical_result_hash_uses_exact_material_fields_with_independent_oracle() -> None:
    result = make_result()

    assert result.material_payload() == material()
    assert result.content_hash == independent_canonical_json_sha256(material())
    assert "id" not in result.material_payload()
    assert "project_id" not in result.material_payload()
    assert "created_by" not in result.material_payload()
    assert "created_at" not in result.material_payload()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("analysis_type", "mann_whitney"),
        ("result_payload", {"p_value": 0.02}),
        ("analysis_definition", {"method": "mann_whitney", "alternative": "greater"}),
    ],
)
def test_each_material_field_changes_hash_independently(field: str, value: object) -> None:
    baseline = make_result()
    if field == "analysis_type":
        changed_material = material(analysis_type=cast(str, value))
        changed = make_result(analysis_type=cast(str, value))
    elif field == "result_payload":
        changed_material = material(result_payload=value)
        changed = make_result(result_payload=value)
    else:
        changed_material = material(analysis_definition=value)
        changed = make_result(analysis_definition=value)

    assert changed_material[field] == value
    assert changed.content_hash == independent_canonical_json_sha256(changed_material)
    assert changed.content_hash != baseline.content_hash


def test_key_order_only_changes_do_not_change_hash() -> None:
    baseline = make_result()
    reordered = make_result(
        result_payload={"p_value": 0.01},
        analysis_definition={"alternative": "two-sided", "method": "student"},
    )

    assert reordered.content_hash == baseline.content_hash


def test_excluded_metadata_changes_do_not_change_hash() -> None:
    baseline = make_result()

    for variant in (
        replace(baseline, id=UUID("00000000-0000-0000-0000-000000000011")),
        replace(baseline, project_id=ProjectId(UUID("00000000-0000-0000-0000-000000000012"))),
        replace(baseline, created_by=ActorId(UUID("00000000-0000-0000-0000-000000000013"))),
        replace(baseline, created_at=datetime(2026, 8, 30, tzinfo=UTC)),
    ):
        assert variant.content_hash == baseline.content_hash


def test_unserializable_material_is_a_stable_validation_error() -> None:
    with pytest.raises(ResearchBaseError) as exc_info:
        StatisticalResult(
            id=StatisticalResultId(RESULT_ID),
            project_id=ProjectId(PROJECT_ID),
            analysis_type="t_test",
            result_payload=object(),
            analysis_definition={"method": "student"},
            content_hash=ContentHash("0" * 64),
            created_by=ActorId(ACTOR_ID),
            created_at=NOW,
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR


@pytest.mark.parametrize("analysis_type", ["", " ", "x" * 65])
def test_analysis_type_has_one_to_64_non_blank_characters(analysis_type: str) -> None:
    with pytest.raises(ResearchBaseError) as exc_info:
        make_result(analysis_type=analysis_type)

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR


def test_statistical_result_and_input_are_immutable_values() -> None:
    result = make_result()
    input_edge = StatisticalResultInput(
        statistical_result_id=result.id,
        measurement_id=MeasurementId(MEASUREMENT_ID),
    )

    with pytest.raises(FrozenInstanceError):
        result.analysis_type = "other"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        input_edge.ordinal = 1  # type: ignore[misc]


@pytest.mark.parametrize("input_role", ["", "x" * 33])
def test_input_role_is_one_to_32_characters(input_role: str) -> None:
    with pytest.raises(ResearchBaseError) as exc_info:
        StatisticalResultInput(
            statistical_result_id=StatisticalResultId(RESULT_ID),
            measurement_id=MeasurementId(MEASUREMENT_ID),
            input_role=input_role,
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR


def test_input_role_length_32_is_accepted() -> None:
    input_edge = StatisticalResultInput(
        statistical_result_id=StatisticalResultId(RESULT_ID),
        measurement_id=MeasurementId(MEASUREMENT_ID),
        input_role="x" * 32,
    )

    assert len(input_edge.input_role) == 32


def test_input_ordinal_must_be_non_negative() -> None:
    with pytest.raises(ResearchBaseError) as exc_info:
        StatisticalResultInput(
            statistical_result_id=StatisticalResultId(RESULT_ID),
            measurement_id=MeasurementId(MEASUREMENT_ID),
            ordinal=-1,
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
