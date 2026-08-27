from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from tests.contracts.version_contract import assert_version_contract

from researchbase.foundation.canonical_json import canonical_json_text
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import (
    CANONICAL_JSON_HASH_SCHEME,
    RAW_BYTES_HASH_SCHEME,
)
from researchbase.foundation.time import FixedClock
from researchbase.foundation.versioning import (
    VersionStatus,
    can_transition,
    freeze_material,
    require_transition,
)


class MappingVersion:
    def __init__(self, material: object) -> None:
        self.material = material
        self.status = VersionStatus.DRAFT
        self.content_hash = None
        self.hash_scheme = None
        self.frozen_at = None

    def edit_material(self, material: object) -> None:
        if self.status is not VersionStatus.DRAFT:
            raise ResearchBaseError(ErrorCode.IMMUTABLE_RECORD, "version material is immutable")
        self.material = material

    def freeze(self, clock: FixedClock) -> None:
        result = freeze_material(self.status, self.material, clock)
        self.status = result.status
        self.content_hash = result.content_hash
        self.hash_scheme = result.hash_scheme
        self.frozen_at = result.frozen_at

    def supersede(self) -> None:
        require_transition(self.status, VersionStatus.SUPERSEDED)
        self.status = VersionStatus.SUPERSEDED

    def abandon(self) -> None:
        require_transition(self.status, VersionStatus.ABANDONED)
        self.status = VersionStatus.ABANDONED

    def reactivate(self) -> None:
        require_transition(self.status, VersionStatus.DRAFT)
        self.status = VersionStatus.DRAFT


@dataclass
class SequenceVersion:
    document: object
    status: VersionStatus = VersionStatus.DRAFT
    content_hash: object = None
    hash_scheme: str | None = None
    frozen_at: datetime | None = None

    def edit_material(self, material: object) -> None:
        if self.status is not VersionStatus.DRAFT:
            raise ResearchBaseError(ErrorCode.IMMUTABLE_RECORD, "version material is immutable")
        self.document = material

    def freeze(self, clock: FixedClock) -> None:
        result = freeze_material(self.status, self.document, clock)
        self.status = result.status
        self.content_hash = result.content_hash
        self.hash_scheme = result.hash_scheme
        self.frozen_at = result.frozen_at

    def supersede(self) -> None:
        require_transition(self.status, VersionStatus.SUPERSEDED)
        self.status = VersionStatus.SUPERSEDED

    def abandon(self) -> None:
        require_transition(self.status, VersionStatus.ABANDONED)
        self.status = VersionStatus.ABANDONED

    def reactivate(self) -> None:
        require_transition(self.status, VersionStatus.DRAFT)
        self.status = VersionStatus.DRAFT


def test_version_status_has_exact_string_values() -> None:
    assert [(status.name, status.value) for status in VersionStatus] == [
        ("DRAFT", "DRAFT"),
        ("FROZEN", "FROZEN"),
        ("SUPERSEDED", "SUPERSEDED"),
        ("ABANDONED", "ABANDONED"),
    ]


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (VersionStatus.DRAFT, VersionStatus.FROZEN),
        (VersionStatus.DRAFT, VersionStatus.ABANDONED),
        (VersionStatus.FROZEN, VersionStatus.SUPERSEDED),
    ],
)
def test_allowed_transitions_are_publicly_accepted(
    current: VersionStatus, target: VersionStatus
) -> None:
    assert can_transition(current, target)
    require_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (VersionStatus.FROZEN, VersionStatus.DRAFT),
        (VersionStatus.SUPERSEDED, VersionStatus.FROZEN),
        (VersionStatus.SUPERSEDED, VersionStatus.DRAFT),
        (VersionStatus.ABANDONED, VersionStatus.DRAFT),
        (VersionStatus.ABANDONED, VersionStatus.FROZEN),
        (VersionStatus.DRAFT, VersionStatus.DRAFT),
        (VersionStatus.FROZEN, VersionStatus.FROZEN),
        (VersionStatus.SUPERSEDED, VersionStatus.SUPERSEDED),
        (VersionStatus.ABANDONED, VersionStatus.ABANDONED),
    ],
)
def test_forbidden_and_same_state_transitions_raise_stable_error(
    current: VersionStatus, target: VersionStatus
) -> None:
    assert not can_transition(current, target)
    with pytest.raises(ResearchBaseError) as error:
        require_transition(current, target)
    assert error.value.code is ErrorCode.INVALID_STATE_TRANSITION


def test_unknown_statuses_are_not_transitions() -> None:
    assert not can_transition("UNKNOWN", VersionStatus.FROZEN)  # type: ignore[arg-type]
    with pytest.raises(ResearchBaseError) as error:
        require_transition("UNKNOWN", VersionStatus.FROZEN)  # type: ignore[arg-type]
    assert error.value.code is ErrorCode.INVALID_STATE_TRANSITION


def test_freeze_uses_explicit_material_and_fixed_utc_clock() -> None:
    material = {"b": [2, 3], "a": "value"}
    frozen_at = datetime(2026, 8, 27, 12, 0, tzinfo=UTC)

    result = freeze_material(VersionStatus.DRAFT, material, FixedClock(frozen_at))

    assert result.status is VersionStatus.FROZEN
    assert result.content_hash is not None
    assert result.hash_scheme == CANONICAL_JSON_HASH_SCHEME
    assert result.frozen_at == frozen_at
    assert result.frozen_at.tzinfo == UTC
    assert canonical_json_text(material) == '{"a":"value","b":[2,3]}'


def test_freeze_rejects_non_draft_and_invalid_material() -> None:
    clock = FixedClock(datetime(2026, 8, 27, 4, 0, tzinfo=UTC))
    with pytest.raises(ResearchBaseError) as frozen_error:
        freeze_material(VersionStatus.FROZEN, {"value": 1}, clock)
    assert frozen_error.value.code is ErrorCode.INVALID_STATE_TRANSITION

    with pytest.raises(TypeError, match="supported JSON subset"):
        freeze_material(VersionStatus.DRAFT, {"value": object()}, clock)


def test_same_material_has_same_hash_and_key_order_does_not_matter() -> None:
    clock = FixedClock(datetime(2026, 8, 27, 4, 0, tzinfo=UTC))
    left = freeze_material(VersionStatus.DRAFT, {"a": 1, "b": 2}, clock)
    right = freeze_material(VersionStatus.DRAFT, {"b": 2, "a": 1}, clock)

    assert left.content_hash == right.content_hash
    assert left.hash_scheme == right.hash_scheme == "sha256-cjson-v1"


def test_material_hash_excludes_non_material_fields_by_construction() -> None:
    clock = FixedClock(datetime(2026, 8, 27, 4, 0, tzinfo=UTC))
    first = {
        "title": "same",
        "id": uuid4(),
        "created_at": "2026-08-27T04:00:00Z",
        "row_version": 1,
    }
    second = {
        "title": "same",
        "id": uuid4(),
        "created_at": "2027-01-01T00:00:00Z",
        "row_version": 99,
    }

    first_result = freeze_material(VersionStatus.DRAFT, {"title": first["title"]}, clock)
    second_result = freeze_material(VersionStatus.DRAFT, {"title": second["title"]}, clock)

    assert first_result.content_hash == second_result.content_hash


@pytest.mark.parametrize(
    ("left", "right"),
    [
        (1, 1.0),
        (-0.0, 0.0),
        ("é", "e\u0301"),
    ],
)
def test_frozen_canonical_policy_does_not_add_semantic_normalization(
    left: object, right: object
) -> None:
    clock = FixedClock(datetime(2026, 8, 27, 4, 0, tzinfo=UTC))

    assert freeze_material(VersionStatus.DRAFT, {"value": left}, clock).content_hash != (
        freeze_material(VersionStatus.DRAFT, {"value": right}, clock).content_hash
    )


def test_hash_scheme_identifiers_remain_machine_readable() -> None:
    assert CANONICAL_JSON_HASH_SCHEME == "sha256-cjson-v1"
    assert RAW_BYTES_HASH_SCHEME == "sha256-bytes-v1"


@pytest.mark.parametrize(
    "factory",
    [lambda material: MappingVersion(material), lambda material: SequenceVersion(material)],
)
def test_reusable_contract_supports_two_lightweight_fixture_shapes(factory: object) -> None:
    assert_version_contract(factory)  # type: ignore[arg-type]
