"""Shared version lifecycle and explicit-material freeze semantics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from researchbase.foundation.enums import BaseStrEnum
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import (
    CANONICAL_JSON_HASH_SCHEME,
    ContentHash,
    sha256_canonical_json,
)
from researchbase.foundation.time import Clock, to_utc


class VersionStatus(BaseStrEnum):
    """The shared lifecycle for owning-domain version identities."""

    DRAFT = "DRAFT"
    FROZEN = "FROZEN"
    SUPERSEDED = "SUPERSEDED"
    ABANDONED = "ABANDONED"


@dataclass(frozen=True, slots=True)
class FrozenVersionState:
    """Immutable result of freezing explicitly supplied material."""

    status: VersionStatus
    content_hash: ContentHash
    hash_scheme: str
    frozen_at: datetime

    def __post_init__(self) -> None:
        if self.status is not VersionStatus.FROZEN:
            raise ValueError("frozen version state must have FROZEN status")
        if not self.hash_scheme:
            raise ValueError("hash_scheme must not be blank")
        object.__setattr__(self, "frozen_at", to_utc(self.frozen_at))


def can_transition(current: VersionStatus | str, target: VersionStatus | str) -> bool:
    """Return whether exactly one shared lifecycle transition is allowed."""
    current_status = _coerce_status(current)
    target_status = _coerce_status(target)
    if current_status is None or target_status is None:
        return False

    return (
        current_status is VersionStatus.DRAFT
        and target_status in {VersionStatus.FROZEN, VersionStatus.ABANDONED}
    ) or (current_status is VersionStatus.FROZEN and target_status is VersionStatus.SUPERSEDED)


def require_transition(current: VersionStatus | str, target: VersionStatus | str) -> None:
    """Require an allowed transition or raise the stable domain error."""
    if not can_transition(current, target):
        raise ResearchBaseError(
            ErrorCode.INVALID_STATE_TRANSITION,
            f"version transition {current!s} -> {target!s} is not allowed",
            details={"current_status": str(current), "target_status": str(target)},
        )


def freeze_material(
    current: VersionStatus | str, material: object, clock: Clock
) -> FrozenVersionState:
    """Freeze explicitly supplied material using the accepted canonical hash contract.

    The caller owns validation and material-field selection. This helper never reflects over
    an owning object and therefore cannot accidentally include identity or operational fields.
    """
    require_transition(current, VersionStatus.FROZEN)
    try:
        content_hash = sha256_canonical_json(material)
    except (TypeError, ValueError) as exc:
        raise ResearchBaseError(
            ErrorCode.VALIDATION_ERROR,
            "version material is not valid canonical JSON",
            details={"field": "material"},
        ) from exc
    return FrozenVersionState(
        status=VersionStatus.FROZEN,
        content_hash=content_hash,
        hash_scheme=CANONICAL_JSON_HASH_SCHEME,
        frozen_at=to_utc(clock.now()),
    )


def _coerce_status(value: VersionStatus | str) -> VersionStatus | None:
    if isinstance(value, VersionStatus):
        return value
    if isinstance(value, str):
        try:
            return VersionStatus(value)
        except ValueError:
            return None
    return None
