from __future__ import annotations

from uuid import RFC_4122, UUID

import pytest

from researchbase.foundation.ids import ActorId, new_typed_id, new_uuid7, parse_typed_id, parse_uuid


def test_uuid7_has_uuid_type_version_and_rfc_variant() -> None:
    value = new_uuid7()

    assert isinstance(value, UUID)
    assert value.version == 7
    assert value.variant == RFC_4122


def test_uuid7_repeated_generation_does_not_collide() -> None:
    values = {new_uuid7() for _ in range(1_000)}

    assert len(values) == 1_000


def test_typed_id_parses_uuid_and_serializes_canonically() -> None:
    source = "550E8400-E29B-41D4-A716-446655440000"

    value = parse_typed_id(source, ActorId)

    assert isinstance(value, UUID)
    assert str(value) == "550e8400-e29b-41d4-a716-446655440000"
    assert str(new_typed_id(ActorId))


def test_parse_uuid_rejects_invalid_input() -> None:
    with pytest.raises(ValueError, match="valid UUID"):
        parse_uuid("not-a-uuid")
