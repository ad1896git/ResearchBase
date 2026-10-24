"""Bounded operational memory values; no scientific facts or authority live here."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from types import UnionType
from typing import (
    Any,
    Literal,
    NoReturn,
    TypeAliasType,
    Union,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)
from unicodedata import normalize
from uuid import UUID

from researchbase.foundation.canonical_json import canonical_json_bytes
from researchbase.foundation.errors import ErrorCode, ResearchBaseError

MAX_MANIFEST_BYTES = 1_048_576
MAX_SOURCES = 256
MAX_NOTE_CHARACTERS = 8192
type Digest = str
type TrustLevel = Literal["UNVERIFIED", "SOURCE_VERIFIED", "UNUSABLE"]
type ValidityStatus = Literal["UNASSESSED", "UNKNOWN", "VALID", "STALE", "INVALID"]
type Note = str


def memory_error() -> NoReturn:
    raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, "unusable task memory")


def closed_value(kind: Any, value: Any, *, decode: bool = False) -> Any:
    """Validate the exact declared immutable graph; decode only explicit closed formats.

    Any is used for runtime annotation inspection, never as an admitted field type.
    Frozen dataclasses from owning Application projections are checked recursively too.
    """
    if isinstance(kind, TypeAliasType):
        result = closed_value(kind.__value__, value, decode=decode)
        if kind is Digest:
            digest(result)
        return result
    origin = get_origin(kind)
    if origin in (UnionType, Union):
        for option in get_args(kind):
            try:
                return closed_value(option, value, decode=decode)
            except (ValueError, TypeError):
                pass
        raise ValueError("closed union value required")
    if origin is Literal:
        for option in get_args(kind):
            candidate = value
            if decode and isinstance(option, Enum) and type(value) is str:
                candidate = type(option)(value)
            if type(candidate) is type(option) and candidate == option:
                return candidate
        raise ValueError("exact literal required")
    if origin is tuple:
        if type(value) is not tuple and not (decode and type(value) is list):
            raise ValueError("immutable typed tuple required")
        return tuple(closed_value(get_args(kind)[0], v, decode=decode) for v in value)
    if kind is UUID and decode and type(value) is str:
        parsed = UUID(value)
        if str(parsed) != value:
            raise ValueError("canonical UUID required")
        return parsed
    if isinstance(kind, type) and issubclass(kind, Enum):
        if decode and type(value) is str:
            return kind(value)
        if type(value) is not kind:
            raise ValueError("exact enum required")
        return value
    if is_dataclass(kind) and isinstance(kind, type):
        if not vars(kind)["__dataclass_params__"].frozen:
            raise ValueError("frozen dataclass required")
        hints = get_type_hints(kind)
        if decode:
            if type(value) is not dict or set(value) - {f.name for f in fields(kind)}:
                raise ValueError("closed object required")
            return cast(Any, kind)(
                **{name: closed_value(hints[name], v, decode=True) for name, v in value.items()}
            )
        if type(value) is not kind:
            raise ValueError("exact declared dataclass required")
        for field in fields(kind):
            closed_value(hints[field.name], getattr(value, field.name))
        return value
    if kind not in (str, bytes, bool, int, UUID, date, datetime, Decimal, type(None)):
        raise ValueError("unsupported closed field type")
    if type(value) is not kind:
        raise ValueError("exact declared scalar required")
    if kind is datetime and value.utcoffset() is None:
        raise ValueError("aware timestamp required")
    if kind is Decimal and not value.is_finite():
        raise ValueError("finite decimal required")
    if kind is str:
        value.encode("utf-8", "strict")
    return value


class ClosedReadValue:
    """Stdlib dataclass boundary: exact fields, immutable tuples and strict member types."""

    __slots__ = ()

    def __post_init__(self) -> None:
        for name, kind in get_type_hints(type(self)).items():
            closed_value(kind, getattr(self, name))


def digest(value: str) -> None:
    if re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError("canonical SHA-256 digest required")


def nonnegative(value: int) -> None:
    if value < 0:
        raise ValueError("nonnegative integer required")


def positive(value: int) -> None:
    if value < 1:
        raise ValueError("positive integer required")


def memory_material(value: object) -> object:
    """Plain canonical JSON value for the closed memory format, without normalization."""
    if isinstance(value, tuple):
        return [memory_material(v) for v in value]
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: memory_material(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, Enum):
        return value.value
    if type(value) is UUID:
        return str(value)
    if value is None or type(value) in (str, int, bool):
        return value
    raise ValueError("unsupported manifest value")


@dataclass(frozen=True, slots=True, kw_only=True)
class MemoryNotes(ClosedReadValue):
    plan_notes: tuple[Note, ...] = ()
    candidate_notes: tuple[Note, ...] = ()
    tool_summaries: tuple[Note, ...] = ()

    def __post_init__(self) -> None:
        ClosedReadValue.__post_init__(self)
        for notes in (self.plan_notes, self.candidate_notes, self.tool_summaries):
            for note in notes:
                if normalize("NFC", note) != note or len(note) > MAX_NOTE_CHARACTERS:
                    raise ValueError("bounded NFC note required")


@dataclass(frozen=True, slots=True, kw_only=True)
class MemoryFormat(ClosedReadValue):
    """Application specializes this envelope with the delivered six-family source refs."""

    format_version: Literal[1] = 1
    project_scope: UUID
    task_id: UUID
    step_id: UUID | None
    created_by: UUID
    trust_level: TrustLevel
    validity_status: ValidityStatus
    notes: MemoryNotes


def canonical_manifest_object(raw: bytes) -> object:
    """Check original encoding, duplicate keys and finite JSON before typed decoding.

    Application first authorizes the exact version and verifies its bytes/size/SHA-256.
    This function has no ArtifactStore access and never normalizes or repairs bytes.
    """

    def pairs(items: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result

    try:
        if type(raw) is not bytes or len(raw) > MAX_MANIFEST_BYTES:
            raise ValueError("manifest bound exceeded")
        value = json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=pairs)
        if canonical_json_bytes(value) != raw:
            raise ValueError("canonical encoding required")
        return value
    except (ValueError, TypeError, UnicodeError, RecursionError):
        memory_error()
