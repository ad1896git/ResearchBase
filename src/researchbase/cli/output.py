"""Deterministic CLI success and error serialization."""

from __future__ import annotations

import base64
import json
from dataclasses import fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

import typer

from researchbase.foundation.errors import ResearchBaseError
from researchbase.foundation.frozen_json import FrozenJSONArray, FrozenJSONObject, thaw_json
from researchbase.foundation.time import format_utc

from .errors import CliTransportError, error_code, error_details


def to_jsonable(value: object) -> object:
    if isinstance(value, FrozenJSONObject | FrozenJSONArray):
        return to_jsonable(thaw_json(value))
    from researchbase.domain.novelty import TimeScope

    if isinstance(value, TimeScope):
        return value.material()
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: to_jsonable(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Enum):
        return to_jsonable(value.value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return format_utc(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("nonfinite CLI decimal")
        return str(value)
    if isinstance(value, bytes):
        return base64.b64encode(value).decode("ascii")
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [to_jsonable(item) for item in value]
    if value is None or isinstance(value, str | int | float | bool):
        return value
    raise TypeError(f"unsupported CLI output value: {type(value).__name__}")


def emit_success(value: object, json_mode: bool) -> None:
    payload = to_jsonable(value)
    if json_mode:
        typer.echo(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        return
    typer.echo(human_text(payload))


def human_text(payload: object) -> str:
    if isinstance(payload, dict):
        return " ".join(f"{key}={human_text(payload[key])}" for key in sorted(payload))
    if isinstance(payload, list):
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if isinstance(payload, str):
        return payload
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def emit_error(error: Exception, request_id: UUID, json_mode: bool) -> None:
    if isinstance(error, CliTransportError | ResearchBaseError):
        code = error_code(error)
        message = error.message
        details: Any = error_details(error)
    else:
        code = "INTERNAL_ERROR"
        message = "unexpected internal error"
        details = None
    if json_mode:
        payload = {
            "error": {
                "code": code,
                "message": message,
                "details": to_jsonable(details),
                "request_id": str(request_id),
            }
        }
        typer.echo(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            err=True,
        )
        return
    typer.echo(f"ERROR [{code}] {message}\nrequest_id={request_id}", err=True)
