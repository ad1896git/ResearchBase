"""Reusable assertions for owning-domain version implementations."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol

from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import ContentHash
from researchbase.foundation.time import Clock
from researchbase.foundation.versioning import VersionStatus

ALLOWED_TRANSITIONS = (
    (VersionStatus.DRAFT, VersionStatus.FROZEN),
    (VersionStatus.DRAFT, VersionStatus.ABANDONED),
    (VersionStatus.FROZEN, VersionStatus.SUPERSEDED),
)

FORBIDDEN_TRANSITIONS = (
    (VersionStatus.DRAFT, VersionStatus.DRAFT),
    (VersionStatus.DRAFT, VersionStatus.SUPERSEDED),
    (VersionStatus.FROZEN, VersionStatus.DRAFT),
    (VersionStatus.FROZEN, VersionStatus.FROZEN),
    (VersionStatus.FROZEN, VersionStatus.ABANDONED),
    (VersionStatus.SUPERSEDED, VersionStatus.DRAFT),
    (VersionStatus.SUPERSEDED, VersionStatus.FROZEN),
    (VersionStatus.SUPERSEDED, VersionStatus.SUPERSEDED),
    (VersionStatus.SUPERSEDED, VersionStatus.ABANDONED),
    (VersionStatus.ABANDONED, VersionStatus.DRAFT),
    (VersionStatus.ABANDONED, VersionStatus.FROZEN),
    (VersionStatus.ABANDONED, VersionStatus.SUPERSEDED),
    (VersionStatus.ABANDONED, VersionStatus.ABANDONED),
)


class VersionFixture(Protocol):
    status: VersionStatus
    content_hash: ContentHash | None
    hash_scheme: str | None
    frozen_at: datetime | None

    @property
    def non_material_metadata(self) -> object: ...

    def edit_material(self, material: object) -> None: ...

    def freeze(self, clock: Clock) -> None: ...

    def transition_to(self, target: VersionStatus) -> None: ...


def assert_version_contract(make_fixture: Callable[[object], VersionFixture]) -> None:
    """Run the independent lifecycle and immutability assertions for one fixture factory."""
    frozen_at = datetime(2026, 8, 27, 4, 0, tzinfo=UTC)

    for current, target in ALLOWED_TRANSITIONS:
        fixture = _fixture_at(make_fixture, current, frozen_at)
        _apply_transition(fixture, target, frozen_at)
        assert fixture.status is target

    for current, target in FORBIDDEN_TRANSITIONS:
        fixture = _fixture_at(make_fixture, current, frozen_at)
        _expect_error(
            lambda fixture=fixture, target=target: _apply_transition(
                fixture, target, frozen_at
            ),
            ErrorCode.INVALID_STATE_TRANSITION,
        )
        assert fixture.status is current

    draft = make_fixture({"title": "draft"})
    assert draft.status is VersionStatus.DRAFT
    draft.edit_material({"title": "edited"})
    draft.freeze(_FixedContractClock(frozen_at))
    assert draft.status is VersionStatus.FROZEN
    assert draft.content_hash is not None
    assert draft.hash_scheme == "sha256-cjson-v1"
    assert draft.frozen_at == frozen_at
    assert draft.frozen_at is not None and draft.frozen_at.utcoffset() is not None
    assert draft.frozen_at.tzinfo == UTC
    _expect_error(
        lambda: draft.edit_material({"title": "changed after freeze"}),
        ErrorCode.IMMUTABLE_RECORD,
    )

    superseded = _fixture_at(make_fixture, VersionStatus.SUPERSEDED, frozen_at)
    _expect_error(
        lambda: superseded.edit_material({"title": "changed after supersede"}),
        ErrorCode.IMMUTABLE_RECORD,
    )

    abandoned = _fixture_at(make_fixture, VersionStatus.ABANDONED, frozen_at)
    _expect_error(
        lambda: abandoned.transition_to(VersionStatus.DRAFT),
        ErrorCode.INVALID_STATE_TRANSITION,
    )
    _expect_error(
        lambda: abandoned.transition_to(VersionStatus.FROZEN),
        ErrorCode.INVALID_STATE_TRANSITION,
    )
    _expect_error(
        lambda: abandoned.transition_to(VersionStatus.SUPERSEDED),
        ErrorCode.INVALID_STATE_TRANSITION,
    )
    _expect_error(
        lambda: abandoned.freeze(_FixedContractClock(frozen_at)),
        ErrorCode.INVALID_STATE_TRANSITION,
    )
    _expect_error(
        lambda: abandoned.edit_material({"title": "resurrected"}),
        ErrorCode.IMMUTABLE_RECORD,
    )

    left = make_fixture({"title": "same material"})
    right = make_fixture({"title": "same material"})
    assert left.non_material_metadata != right.non_material_metadata
    left.freeze(_FixedContractClock(frozen_at))
    right.freeze(_FixedContractClock(frozen_at))
    assert left.content_hash == right.content_hash

    changed = make_fixture({"title": "changed material"})
    changed.freeze(_FixedContractClock(frozen_at))
    assert changed.content_hash != left.content_hash


def _fixture_at(
    make_fixture: Callable[[object], VersionFixture],
    status: VersionStatus,
    frozen_at: datetime,
) -> VersionFixture:
    fixture = make_fixture({"title": status.value})
    if status is VersionStatus.FROZEN:
        fixture.freeze(_FixedContractClock(frozen_at))
    elif status is VersionStatus.SUPERSEDED:
        fixture.freeze(_FixedContractClock(frozen_at))
        fixture.transition_to(VersionStatus.SUPERSEDED)
    elif status is VersionStatus.ABANDONED:
        fixture.transition_to(VersionStatus.ABANDONED)
    assert fixture.status is status
    return fixture


def _expect_error(action: Callable[[], object], code: ErrorCode) -> None:
    try:
        action()
    except ResearchBaseError as error:
        assert error.code is code
    else:
        raise AssertionError(f"expected ResearchBaseError with code {code}")


def _apply_transition(
    fixture: VersionFixture, target: VersionStatus, frozen_at: datetime
) -> None:
    if target is VersionStatus.FROZEN:
        fixture.freeze(_FixedContractClock(frozen_at))
    else:
        fixture.transition_to(target)


class _FixedContractClock:
    def __init__(self, value: datetime) -> None:
        self._value = value

    def now(self) -> datetime:
        return self._value
