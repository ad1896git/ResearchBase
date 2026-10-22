"""Closed immutable invocation values and pure lifecycle predicates."""

from __future__ import annotations

import re
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime
from decimal import Decimal
from types import UnionType
from typing import Any, cast, get_args, get_origin, get_type_hints
from unicodedata import normalize
from uuid import UUID

from researchbase.agent_runtime.domain.agent_version import digest_value
from researchbase.agent_runtime.domain.research_task import exact_uuid, invalid
from researchbase.foundation.canonical_json import canonical_json_bytes
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import sha256_canonical_json
from researchbase.foundation.time import to_utc

TERMINAL = ("SUCCEEDED", "FAILED", "UNKNOWN_OUTCOME", "CANCELLED")
FINAL = ("SUCCEEDED", "FAILED", "CANCELLED")
FAMILIES = (
    "RESEARCH_QUESTION_VERSION",
    "HYPOTHESIS_VERSION",
    "CLAIM_VERSION",
    "SOURCE_VERSION",
    "ARTIFACT_VERSION",
    "MANUSCRIPT_VERSION",
)
SCHEMA = {
    "additionalProperties": False,
    "properties": {
        "message": {"maxLength": 1024, "type": "string"},
        "outcome": {"enum": list(TERMINAL)},
    },
    "required": ["message", "outcome"],
    "type": "object",
}
SCHEMA_HASH = str(sha256_canonical_json(SCHEMA))


def pin(value, limit=512):
    value = nfc(value)
    if not value or value != value.strip() or len(value) > limit:
        invalid("bounded exact pin required")
    if any(
        p.lower() in {"latest", "current", "main", "master", "head"}
        for p in re.split(r"[/@:#?=&\s]+", value)
    ) or re.search(r"[\s*?\[\]{}()^$|+\\]", value):
        invalid("aliases and patterns are forbidden")
    return value


def nfc(value):
    if type(value) is not str:
        invalid("text required")
    value = normalize("NFC", value)
    try:
        value.encode("utf-8")
    except UnicodeError:
        invalid("UTF-8 text required")
    return value


def bounded_text(value, limit=8192, *, byte_limit=False, blank=False):
    value = nfc(value)
    size = len(value.encode("utf-8")) if byte_limit else len(value)
    if size > limit or (not blank and not value.strip()):
        invalid("text admission limit exceeded")
    return value


def typed(kind: Any, value: Any, *, decode=False) -> Any:
    """Decode only the declared closed value graph; trusted objects have no decoder."""
    if decode and getattr(kind, "__trusted_context__", False):
        invalid("trusted context has no public decoder")
    origin = get_origin(kind)
    if origin is UnionType:
        for option in get_args(kind):
            try:
                return typed(option, value, decode=decode)
            except ResearchBaseError:
                pass
        invalid("closed union value required")
    if kind is type(None):
        if value is not None:
            invalid("NULL required")
        return None
    if origin is tuple:
        if type(value) is not tuple and not (decode and type(value) is list):
            invalid("typed tuple required")
        return tuple(typed(get_args(kind)[0], v, decode=decode) for v in value)
    if kind is UUID:
        if decode and type(value) is str:
            try:
                value = UUID(value)
            except ValueError:
                invalid("UUID required")
        exact_uuid(value)
        return value
    if kind is datetime:
        if decode and type(value) is str:
            try:
                value = datetime.fromisoformat(value)
            except ValueError:
                invalid("aware timestamp required")
        if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
            invalid("aware timestamp required")
        return to_utc(value)
    if kind is Decimal:
        from researchbase.agent_runtime.domain.task_safety import decimal_value

        return decimal_value(value)
    if is_dataclass(kind) and decode:
        if type(value) is not dict:
            invalid("closed object required")
        known = {f.name for f in fields(kind)}
        if set(value) - known:
            invalid("unknown nested fields")
        hints = get_type_hints(kind)
        try:
            return cast(Any, kind)(**{k: typed(hints[k], v, decode=True) for k, v in value.items()})
        except TypeError:
            invalid("missing required fields")
    if type(value) is not kind:
        invalid("exact declared type required")
    return nfc(value) if kind is str else value


class ClosedValue:
    __slots__ = ()

    def __post_init__(self):
        for name, kind in get_type_hints(type(self)).items():
            object.__setattr__(self, name, typed(kind, getattr(self, name)))


def material(value) -> Any:
    if getattr(type(value), "__trusted_context__", False):
        invalid("trusted context is not command material")
    if is_dataclass(value):
        return {f.name: material(getattr(value, f.name)) for f in fields(value)}
    if type(value) is tuple:
        return [material(v) for v in value]
    if type(value) is UUID:
        return str(value)
    if isinstance(value, Decimal):
        return format(value, ".6f")
    if isinstance(value, datetime):
        return value.isoformat()
    return value


@dataclass(frozen=True, slots=True)
class FakeParameters(ClosedValue):
    message: str
    outcome: str

    def __post_init__(self):
        ClosedValue.__post_init__(self)
        bounded_text(self.message, 1024, blank=True)
        if self.outcome not in TERMINAL:
            invalid("terminal outcome required")

    def canonical_bytes(self):
        return canonical_json_bytes(material(self))

    def digest(self):
        return str(sha256_canonical_json(material(self)))


@dataclass(frozen=True, slots=True)
class GatewayRef(ClosedValue):
    family: str
    version_id: UUID
    content_hash: str
    hash_scheme: str | None

    def __post_init__(self):
        ClosedValue.__post_init__(self)
        if self.family not in FAMILIES:
            invalid("closed reference family required")
        digest_value(self.content_hash)
        expected = (
            "sha256-cjson-v1" if self.family in ("SOURCE_VERSION", "MANUSCRIPT_VERSION") else None
        )
        if self.hash_scheme != expected:
            invalid("owning reference hash scheme required")


def refs(values, *, output=False):
    if type(values) is not tuple or any(type(v) is not GatewayRef for v in values):
        invalid("closed reference tuple required")
    keys = [(v.family, str(v.version_id)) for v in values]
    if len(values) > 256 or len(set(keys)) != len(keys):
        invalid("duplicate references or admission limit exceeded")
    if output and any(v.family != "ARTIFACT_VERSION" for v in values):
        invalid("outputs must be candidate artifacts")
    return tuple(sorted(values, key=lambda v: (v.family, str(v.version_id))))


def require_transition(prior, action, outcome=None, *, no_dispatch=False, reconciled=False):
    if prior == "REQUESTED" and action == "START" and outcome is None:
        return "RUNNING"
    if prior == "REQUESTED" and action == "FINISH" and outcome == "CANCELLED" and no_dispatch:
        return "CANCELLED"
    if prior == "RUNNING" and action == "FINISH" and outcome in TERMINAL:
        return outcome
    if prior == "UNKNOWN_OUTCOME" and action == "RECONCILE" and outcome in FINAL and not reconciled:
        return "UNKNOWN_OUTCOME"
    raise ResearchBaseError(ErrorCode.INVALID_STATE_TRANSITION, "invalid invocation transition")


def retry_eligible(status, reconciled_outcome=None):
    return status == "FAILED" or (status == "UNKNOWN_OUTCOME" and reconciled_outcome in FINAL)


def validate_combined_refs(inputs: tuple[GatewayRef, ...], outputs: tuple[GatewayRef, ...]):
    refs(inputs)
    refs(outputs, output=True)
    if len(inputs) + len(outputs) > 256:
        invalid("combined persisted reference admission limit exceeded")
