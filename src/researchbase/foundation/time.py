"""UTC time primitives with replaceable clocks."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import NewType, Protocol

Instant = NewType("Instant", datetime)


class Clock(Protocol):
    def now(self) -> datetime:
        """Return an aware UTC datetime."""
        ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class FixedClock:
    def __init__(self, value: datetime) -> None:
        self._value = to_utc(value)

    def now(self) -> datetime:
        return self._value


def to_utc(value: datetime) -> datetime:
    """Reject naive datetimes and normalize aware datetimes to UTC."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")
    return value.astimezone(UTC)


def format_utc(value: datetime) -> str:
    """Format an aware datetime as ISO-8601 UTC text ending in ``Z``."""
    return to_utc(value).isoformat().replace("+00:00", "Z")
