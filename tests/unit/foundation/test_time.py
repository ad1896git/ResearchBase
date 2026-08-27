from datetime import UTC, datetime, timedelta, timezone

import pytest

from researchbase.foundation.time import FixedClock, SystemClock, format_utc, to_utc


def test_system_clock_returns_aware_utc() -> None:
    now = SystemClock().now()

    assert now.tzinfo == UTC
    assert now.utcoffset() == timedelta(0)


def test_fixed_clock_is_deterministic_and_normalizes_to_utc() -> None:
    source = datetime(2026, 8, 27, 12, 0, tzinfo=timezone(timedelta(hours=8)))
    clock = FixedClock(source)

    assert clock.now() == datetime(2026, 8, 27, 4, 0, tzinfo=UTC)
    assert format_utc(clock.now()) == "2026-08-27T04:00:00Z"


def test_naive_datetime_is_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        to_utc(datetime(2026, 8, 27, 4, 0))
