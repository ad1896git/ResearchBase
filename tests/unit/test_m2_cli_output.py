from decimal import Decimal

from researchbase.cli.output import to_jsonable


def test_provider_decimal_score_is_lossless_json_string():
    assert to_jsonable({"provider_score": Decimal("1.234567890123456789")}) == {
        "provider_score": "1.234567890123456789"
    }


def test_observation_hash_normalizes_equivalent_database_timezones():
    from datetime import UTC, datetime, timedelta, timezone

    from researchbase.application.metadata_observation import _hash

    instant = datetime(2026, 10, 10, tzinfo=UTC)
    assert _hash({"observed_at": instant}) == _hash(
        {"observed_at": instant.astimezone(timezone(timedelta(hours=8)))}
    )
