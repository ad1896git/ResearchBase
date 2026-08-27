"""Typed UUID helpers and a standard-library UUIDv7 generator."""

from __future__ import annotations

import secrets
import time
from collections.abc import Callable
from typing import NewType
from uuid import UUID

ActorId = NewType("ActorId", UUID)
CanonicalId = NewType("CanonicalId", UUID)


def new_uuid7() -> UUID:
    """Return a UUIDv7 using the Unix epoch millisecond timestamp and random bits."""
    timestamp_ms = time.time_ns() // 1_000_000
    if timestamp_ms < 0 or timestamp_ms >= 1 << 48:
        raise OverflowError("current time cannot be represented by UUIDv7")

    random_bits = secrets.randbits(74)
    random_a = random_bits >> 62
    random_b = random_bits & ((1 << 62) - 1)
    value = (timestamp_ms << 80) | (0x7 << 76) | (random_a << 64) | (0b10 << 62) | random_b
    return UUID(int=value)


def parse_uuid(value: UUID | str) -> UUID:
    """Parse a UUID value explicitly and reject invalid input with a clear error."""
    if isinstance(value, UUID):
        return value
    try:
        return UUID(value)
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError("value is not a valid UUID") from exc


def uuid_text(value: UUID) -> str:
    """Return canonical lower-case UUID text."""
    return str(value)


def parse_typed_id[TypedId](value: UUID | str, id_type: Callable[[UUID], TypedId]) -> TypedId:
    """Parse a UUID and explicitly wrap it with a typed-ID constructor."""
    return id_type(parse_uuid(value))


def new_typed_id[TypedId](id_type: Callable[[UUID], TypedId]) -> TypedId:
    """Generate a UUIDv7 and explicitly wrap it with a typed-ID constructor."""
    return id_type(new_uuid7())
