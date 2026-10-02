from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

import pytest

from researchbase.domain.measurement import Measurement, MeasurementId
from researchbase.domain.metric import MetricDefinitionVersionId
from researchbase.domain.run import RunId
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.ids import ActorId

NOW = datetime(2026, 8, 28, 2, 0, tzinfo=UTC)
BASE_RUN_ID = RunId(UUID("00000000-0000-4000-8000-000000000001"))
BASE_METRIC_ID = MetricDefinitionVersionId(UUID("00000000-0000-4000-8000-000000000002"))
BASE_MEASUREMENT_ID = MeasurementId(UUID("00000000-0000-4000-8000-000000000003"))
BASE_ACTOR_ID = ActorId(UUID("00000000-0000-4000-8000-000000000004"))


def independent_canonical_json_sha256(value: object) -> str:
    """Test-owned canonical-json-v1 oracle; do not import production hash code."""
    canonical_bytes = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical_bytes).hexdigest()


def _material(
    *,
    run_id: Any,
    metric_definition_version_id: Any,
    numeric_value: float | None,
    structured_value: object | None,
    unit: str | None,
    evaluation_scope: object | None,
) -> dict[str, object | None]:
    return {
        "run_id": str(run_id),
        "metric_definition_version_id": str(metric_definition_version_id),
        "numeric_value": numeric_value,
        "structured_value": structured_value,
        "unit": unit,
        "evaluation_scope": evaluation_scope,
    }


def _measurement(**overrides: object) -> Measurement:
    values: dict[str, object] = {
        "id": BASE_MEASUREMENT_ID,
        "run_id": BASE_RUN_ID,
        "metric_definition_version_id": BASE_METRIC_ID,
        "numeric_value": 0.875,
        "structured_value": None,
        "unit": "m",
        "evaluation_scope": {"split": "test"},
        "created_by": BASE_ACTOR_ID,
        "created_at": NOW,
    }
    values.update(overrides)
    material = _material(
        run_id=values["run_id"],
        metric_definition_version_id=values["metric_definition_version_id"],
        numeric_value=values["numeric_value"],  # type: ignore[arg-type]
        structured_value=values["structured_value"],
        unit=values["unit"],  # type: ignore[arg-type]
        evaluation_scope=values["evaluation_scope"],
    )
    try:
        values["content_hash"] = independent_canonical_json_sha256(material)
    except (TypeError, ValueError):
        values["content_hash"] = "0" * 64
    return Measurement(**cast(dict[str, Any], values))


def test_measurement_hash_material_is_exact_and_metadata_independent() -> None:
    measurement = _measurement()
    expected = measurement.material_payload()

    assert measurement.content_hash == independent_canonical_json_sha256(expected)

    changed_metadata = replace(
        measurement, id=MeasurementId(uuid4()), created_by=ActorId(uuid4()), created_at=NOW
    )
    assert changed_metadata.content_hash == measurement.content_hash


@pytest.mark.parametrize(
    ("numeric_value", "structured_value"),
    [(None, None), (1.0, {"value": 1.0})],
)
def test_measurement_requires_exactly_one_value_representation(
    numeric_value: float | None, structured_value: object | None
) -> None:
    with pytest.raises(ResearchBaseError) as exc_info:
        _measurement(numeric_value=numeric_value, structured_value=structured_value)
    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_measurement_rejects_non_finite_numeric_values(value: float) -> None:
    with pytest.raises(ResearchBaseError) as exc_info:
        _measurement(numeric_value=value)
    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR


def test_measurement_rejects_unrepresentable_numeric_values() -> None:
    with pytest.raises(ResearchBaseError) as exc_info:
        _measurement(numeric_value=10**400)
    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR


@pytest.mark.parametrize("field", ["structured_value", "evaluation_scope"])
def test_measurement_rejects_non_canonical_json(field: str) -> None:
    with pytest.raises(ResearchBaseError) as exc_info:
        _measurement(**{field: {"bad": {1, 2}}})
    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR


def test_measurement_accepts_json_lists_and_scope_objects() -> None:
    measurement = _measurement(
        numeric_value=None,
        structured_value=[{"value": 1}, {"value": 2}],
        evaluation_scope={"fold": 0, "nested": {"split": "test"}},
    )
    assert measurement.structured_value == [{"value": 1}, {"value": 2}]


def test_measurement_rejects_nonfinite_nested_json() -> None:
    with pytest.raises(ResearchBaseError) as exc_info:
        _measurement(numeric_value=None, structured_value={"value": float("nan")})
    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR


def test_measurement_unit_is_bounded_and_record_is_frozen() -> None:
    with pytest.raises(ResearchBaseError) as exc_info:
        _measurement(unit="x" * 65)
    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR

    measurement = _measurement()
    with pytest.raises(FrozenInstanceError):
        measurement.numeric_value = 0.5  # type: ignore[misc]


def test_numeric_and_structured_materials_have_distinct_hashes() -> None:
    numeric = _measurement(numeric_value=1.0, structured_value=None)
    structured = _measurement(numeric_value=None, structured_value={"value": 1.0})
    assert numeric.content_hash != structured.content_hash


def test_structured_and_scope_key_order_does_not_change_hash() -> None:
    left = _measurement(
        structured_value={"a": 1, "b": {"x": True, "y": [1, 2]}},
        numeric_value=None,
        evaluation_scope={"fold": 3, "split": "test"},
    )
    right = _measurement(
        run_id=left.run_id,
        metric_definition_version_id=left.metric_definition_version_id,
        structured_value={"b": {"y": [1, 2], "x": True}, "a": 1},
        numeric_value=None,
        evaluation_scope={"split": "test", "fold": 3},
    )
    assert left.content_hash == right.content_hash


def test_material_field_changes_hash() -> None:
    baseline = _measurement()
    changed = _measurement(
        run_id=baseline.run_id,
        metric_definition_version_id=baseline.metric_definition_version_id,
        unit="cm",
    )
    assert changed.content_hash != baseline.content_hash


def test_each_material_field_changes_hash_independently() -> None:
    baseline = _measurement()

    def with_recomputed_hash(measurement: Measurement, **changes: object) -> Measurement:
        material = measurement.material_payload()
        for field, value in changes.items():
            material[field] = str(value) if field.endswith("_id") else value
        return replace(
            measurement,
            **changes,
            content_hash=independent_canonical_json_sha256(material),
        )

    assert (
        with_recomputed_hash(
            baseline,
            run_id=RunId(UUID("00000000-0000-4000-8000-000000000011")),
        ).content_hash
        != baseline.content_hash
    )
    assert (
        with_recomputed_hash(
            baseline,
            metric_definition_version_id=MetricDefinitionVersionId(
                UUID("00000000-0000-4000-8000-000000000012")
            ),
        ).content_hash
        != baseline.content_hash
    )
    assert with_recomputed_hash(baseline, numeric_value=1.875).content_hash != baseline.content_hash
    assert with_recomputed_hash(baseline, unit="cm").content_hash != baseline.content_hash
    assert (
        with_recomputed_hash(baseline, evaluation_scope={"split": "train"}).content_hash
        != baseline.content_hash
    )

    structured_baseline = _measurement(numeric_value=None, structured_value={"value": 1.0})
    structured_changed = with_recomputed_hash(
        structured_baseline,
        structured_value={"value": 2.0},
    )
    assert structured_changed.content_hash != structured_baseline.content_hash


def test_excluded_metadata_fields_do_not_change_hash_independently() -> None:
    baseline = _measurement()
    assert (
        replace(
            baseline,
            id=MeasurementId(UUID("00000000-0000-4000-8000-000000000021")),
        ).content_hash
        == baseline.content_hash
    )
    assert (
        replace(
            baseline,
            created_by=ActorId(UUID("00000000-0000-4000-8000-000000000022")),
        ).content_hash
        == baseline.content_hash
    )
    assert replace(baseline, created_at=NOW.replace(day=29)).content_hash == baseline.content_hash
