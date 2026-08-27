from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from tests.contracts.version_contract import VersionFixture, assert_version_contract

from researchbase.domain.metric import (
    MetricDefinition,
    MetricDefinitionId,
    MetricDefinitionVersion,
    MetricDefinitionVersionId,
)
from researchbase.foundation.canonical_json import canonical_json_bytes
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import sha256_canonical_json
from researchbase.foundation.ids import ActorId
from researchbase.foundation.time import FixedClock
from researchbase.foundation.versioning import VersionStatus

FIXED_TIME = datetime(2026, 8, 27, 4, 0, tzinfo=UTC)
FROZEN_TIME = datetime(2026, 8, 27, 5, 0, tzinfo=UTC)


def _version(**overrides: object) -> MetricDefinitionVersion:
    values: dict[str, Any] = {
        "id": MetricDefinitionVersionId(uuid4()),
        "metric_definition_id": MetricDefinitionId(uuid4()),
        "version_number": 1,
        "status": VersionStatus.DRAFT,
        "definition": {"kind": "mean", "field": "score"},
        "unit": "m",
        "aggregation": "mean",
        "created_by": ActorId(uuid4()),
        "created_at": FIXED_TIME,
    }
    values.update(overrides)
    return MetricDefinitionVersion(**values)


class MetricVersionContractAdapter(VersionFixture):
    def __init__(self, value: MetricDefinitionVersion, title: str = "baseline") -> None:
        self.value = value
        self.title = title

    @property
    def status(self) -> VersionStatus:
        return self.value.status

    @property
    def content_hash(self) -> str | None:
        return str(self.value.content_hash) if self.value.content_hash else None

    @property
    def hash_scheme(self) -> str | None:
        return self.value.hash_scheme

    @property
    def frozen_at(self) -> datetime | None:
        return self.value.frozen_at

    @property
    def non_material_metadata(self) -> dict[str, object]:
        return {
            "id": self.value.id,
            "metric_definition_id": self.value.metric_definition_id,
            "version_number": self.value.version_number,
            "created_by": self.value.created_by,
            "created_at": self.value.created_at,
            "row_version": self.value.row_version,
        }

    def edit_material(self, material: object) -> MetricVersionContractAdapter:
        if isinstance(material, dict) and "title" in material:
            self.title = str(material["title"])
            self.value = self.value.edit_material(
                definition={"kind": "mean", "field": "score", "title": self.title},
                unit=self.value.unit,
                aggregation=self.value.aggregation,
            )
        return self

    def freeze(self, clock: object) -> MetricVersionContractAdapter:
        self.value = self.value.freeze(clock)  # type: ignore[arg-type]
        return self

    def transition_to(self, target: VersionStatus) -> MetricVersionContractAdapter:
        self.value = self.value.transition_to(target)
        return self


def test_metric_version_is_directly_wired_to_shared_pr03_contract() -> None:
    assert_version_contract(
        lambda material=None: MetricVersionContractAdapter(
            _version(definition={"kind": "mean", "field": "score", "title": str(material)})
        )
    )


def test_material_payload_is_exact_and_hash_is_black_box_reproducible() -> None:
    version = _version()
    expected_payload = {
        "definition": {"kind": "mean", "field": "score"},
        "unit": "m",
        "aggregation": "mean",
    }
    assert version.material_payload() == expected_payload
    frozen = version.freeze(FixedClock(FROZEN_TIME))
    assert sha256_canonical_json(expected_payload) == str(frozen.content_hash)
    assert canonical_json_bytes(expected_payload)


@pytest.mark.parametrize("field", ["definition", "unit", "aggregation"])
def test_each_material_field_changes_the_hash(field: str) -> None:
    baseline = _version().freeze(FixedClock(FROZEN_TIME))
    changed = {
        "definition": {"kind": "sum", "field": "score"},
        "unit": "cm",
        "aggregation": "sum",
    }[field]
    candidate = replace(_version(), **{field: changed}).freeze(FixedClock(FROZEN_TIME))
    assert baseline.content_hash != candidate.content_hash


@pytest.mark.parametrize("value", [None, object(), {"bad": {1, 2}}])
def test_invalid_definition_is_stable_validation_error(value: object) -> None:
    with pytest.raises(ResearchBaseError) as exc_info:
        _version(definition=value).validate_material()
    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR


@pytest.mark.parametrize("field", ["unit", "aggregation"])
def test_optional_text_fields_are_bounded(field: str) -> None:
    with pytest.raises(ResearchBaseError, match="64"):
        _version(**{field: "x" * 65})


def test_identity_supports_nullable_project_and_no_pointer() -> None:
    identity = MetricDefinition(
        id=MetricDefinitionId(uuid4()),
        project_id=None,
        name="Score",
        created_by=ActorId(uuid4()),
        created_at=FIXED_TIME,
    )
    assert identity.current_version_id is None
    assert identity.row_version == 1
