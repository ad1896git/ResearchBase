from __future__ import annotations

from uuid import RFC_4122, UUID

import pytest

import researchbase.foundation.ids as ids
from researchbase.foundation.ids import ActorId, new_typed_id, new_uuid7, parse_typed_id, parse_uuid


def test_uuid7_has_uuid_type_version_and_rfc_variant() -> None:
    value = new_uuid7()

    assert isinstance(value, UUID)
    assert value.version == 7
    assert value.variant == RFC_4122


def test_uuid7_repeated_generation_does_not_collide() -> None:
    values = {new_uuid7() for _ in range(1_000)}

    assert len(values) == 1_000


def test_uuid7_places_timestamp_and_random_bits_in_the_standard_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    timestamp_ms = 1_700_000_000_123
    random_a = 0xABC
    random_b = 0x123456789ABCDEF
    random_bits = (random_a << 62) | random_b
    monkeypatch.setattr(ids.time, "time_ns", lambda: timestamp_ms * 1_000_000)
    monkeypatch.setattr(ids.secrets, "randbits", lambda bits: random_bits)

    value = new_uuid7()

    assert value.int >> 80 == timestamp_ms
    assert (value.int >> 76) & 0xF == 7
    assert (value.int >> 62) & 0x3 == 0b10
    assert (value.int >> 64) & 0xFFF == random_a
    assert value.int & ((1 << 62) - 1) == random_b


def test_uuid7_timestamp_is_close_to_current_wall_clock() -> None:
    before_ms = ids.time.time_ns() // 1_000_000
    value = new_uuid7()
    after_ms = ids.time.time_ns() // 1_000_000

    timestamp_ms = value.int >> 80
    assert before_ms <= timestamp_ms <= after_ms


def test_typed_id_parses_uuid_and_serializes_canonically() -> None:
    source = "550E8400-E29B-41D4-A716-446655440000"

    value = parse_typed_id(source, ActorId)

    assert isinstance(value, UUID)
    assert str(value) == "550e8400-e29b-41d4-a716-446655440000"
    assert str(new_typed_id(ActorId))


def test_parse_uuid_rejects_invalid_input() -> None:
    with pytest.raises(ValueError, match="valid UUID"):
        parse_uuid("not-a-uuid")
