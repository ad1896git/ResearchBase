"""Reusable assertions for owning-domain version implementations."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol

import pytest

from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import ContentHash
from researchbase.foundation.time import Clock
from researchbase.foundation.versioning import VersionStatus


class VersionFixture(Protocol):
    status: VersionStatus
    content_hash: ContentHash | None
    hash_scheme: str | None
    frozen_at: datetime | None

    def edit_material(self, material: object) -> None: ...

    def freeze(self, clock: Clock) -> None: ...

    def supersede(self) -> None: ...

    def abandon(self) -> None: ...

    def reactivate(self) -> None: ...


def assert_version_contract(make_fixture: Callable[[object], VersionFixture]) -> None:
    """Run the shared lifecycle and immutability assertions for one fixture factory."""
    draft = make_fixture({"title": "draft"})
    assert draft.status is VersionStatus.DRAFT
    draft.edit_material({"title": "edited"})

    frozen_at = datetime(2026, 8, 27, 4, 0, tzinfo=UTC)
    draft.freeze(_FixedContractClock(frozen_at))
    assert draft.status is VersionStatus.FROZEN
    assert draft.content_hash is not None
    assert draft.hash_scheme == "sha256-cjson-v1"
    assert draft.frozen_at == frozen_at
    assert draft.frozen_at is not None and draft.frozen_at.utcoffset() is not None
    assert draft.frozen_at.tzinfo == UTC

    with pytest.raises(ResearchBaseError) as frozen_edit:
        draft.edit_material({"title": "changed after freeze"})
    assert frozen_edit.value.code is ErrorCode.IMMUTABLE_RECORD

    draft.supersede()
    with pytest.raises(ResearchBaseError) as superseded_edit:
        draft.edit_material({"title": "changed after supersede"})
    assert superseded_edit.value.code is ErrorCode.IMMUTABLE_RECORD

    abandoned = make_fixture({"title": "abandoned"})
    abandoned.abandon()
    with pytest.raises(ResearchBaseError) as abandoned_reactivate:
        abandoned.reactivate()
    assert abandoned_reactivate.value.code is ErrorCode.INVALID_STATE_TRANSITION
    with pytest.raises(ResearchBaseError) as abandoned_edit:
        abandoned.edit_material({"title": "resurrected"})
    assert abandoned_edit.value.code is ErrorCode.IMMUTABLE_RECORD


class _FixedContractClock:
    def __init__(self, value: datetime) -> None:
        self._value = value

    def now(self) -> datetime:
        return self._value
