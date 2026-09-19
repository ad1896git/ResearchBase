"""Explicit database codecs for persisted canonical enum lexemes."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, TypeVar

from sqlalchemy.engine import Dialect
from sqlalchemy.types import String, TypeDecorator

PersistedEnumT = TypeVar("PersistedEnumT", bound=StrEnum)


def encode_persisted_enum[EnumT: StrEnum](enum_type: type[EnumT], value: EnumT | str) -> str:
    """Encode a semantic enum value as its explicit canonical member name."""

    try:
        member = value if isinstance(value, enum_type) else enum_type(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid {enum_type.__name__} value: {value!r}") from exc
    return member.name


def decode_persisted_enum[EnumT: StrEnum](enum_type: type[EnumT], value: str) -> EnumT:
    """Decode only an exact canonical database member name."""

    try:
        return enum_type.__members__[value]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"invalid persisted {enum_type.__name__} lexeme: {value!r}") from exc


class PersistedCanonicalEnum(TypeDecorator[PersistedEnumT]):
    """Store a StrEnum's member name and return its semantic enum member."""

    impl = String
    cache_ok = True

    def __init__(self, enum_type: type[PersistedEnumT], length: int | None = None) -> None:
        self.enum_type = enum_type
        super().__init__(length)

    def process_bind_param(
        self, value: PersistedEnumT | str | None, dialect: Dialect
    ) -> str | None:
        del dialect
        return None if value is None else encode_persisted_enum(self.enum_type, value)

    def process_result_value(self, value: Any, dialect: Dialect) -> PersistedEnumT | None:
        del dialect
        return None if value is None else decode_persisted_enum(self.enum_type, value)
