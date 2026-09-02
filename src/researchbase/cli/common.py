"""Shared transport parsing and one-handler invocation boundary."""

# pyright: reportCallIssue=false

from __future__ import annotations

import base64
import binascii
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import TypeVar
from uuid import UUID

import typer

from researchbase.foundation.errors import ResearchBaseError

from .context import CliRuntime
from .errors import CliTransportError, cli_exit_code
from .output import emit_error, emit_success

T = TypeVar("T")


def parse_json_value(value: str | None, option: str, request_id: UUID) -> object | None:
    if value is None:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise CliTransportError(
            f"{option} must contain valid JSON",
            request_id=request_id,
            details={"option": option},
        ) from exc


def read_json_file(path: str | None, option: str, request_id: UUID) -> object | None:
    if path is None:
        return None
    try:
        content = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise CliTransportError(
            f"{option} could not be read as UTF-8 JSON",
            request_id=request_id,
            details={"option": option},
        ) from exc
    return parse_json_value(content, option, request_id)


def payload(
    json_input: str | None,
    json_file: str | None,
    request_id: UUID,
) -> dict[str, object]:
    if json_input is not None and json_file is not None:
        raise CliTransportError(
            "use only one of --json-input and --json-file",
            request_id=request_id,
            details={"options": ["--json-input", "--json-file"]},
        )
    source = parse_json_value(json_input, "--json-input", request_id)
    if source is None:
        source = read_json_file(json_file, "--json-file", request_id)
    if source is None:
        return {}
    if not isinstance(source, dict):
        raise CliTransportError(
            "JSON input must be an object",
            request_id=request_id,
            details={"option": "--json-input/--json-file"},
        )
    return dict(source)


def merged_payload(
    json_input: str | None,
    json_file: str | None,
    request_id: UUID,
    **values: object,
) -> dict[str, object]:
    result = payload(json_input, json_file, request_id)
    result.update({key: value for key, value in values.items() if value is not None})
    return result


def option_int(value: str | None, name: str, request_id: UUID) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise CliTransportError(
            f"{name} must be an integer",
            request_id=request_id,
            details={"option": name},
        ) from exc
    return parsed


def option_float(value: str | None, name: str, request_id: UUID) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise CliTransportError(
            f"{name} must be a number",
            request_id=request_id,
            details={"option": name},
        ) from exc


def option_json(value: str | None, name: str, request_id: UUID) -> object | None:
    return parse_json_value(value, name, request_id)


def option_uuid(value: str | None, name: str, request_id: UUID) -> str | None:
    if value is None:
        return None
    try:
        return str(UUID(value))
    except (AttributeError, TypeError, ValueError) as exc:
        raise CliTransportError(
            f"{name} must be a valid UUID",
            request_id=request_id,
            details={"option": name},
        ) from exc


def option_base64(value: str | None, name: str, request_id: UUID) -> bytes | None:
    if value is None:
        return None
    try:
        return base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise CliTransportError(
            f"{name} must be valid base64",
            request_id=request_id,
            details={"option": name},
        ) from exc


def required(data: Mapping[str, object], name: str, request_id: UUID) -> object:
    value = data.get(name)
    if value is None or (isinstance(value, str) and not value.strip()):
        raise CliTransportError(
            f"{name} is required",
            request_id=request_id,
            details={"field": name},
        )
    return value


def text_value(data: Mapping[str, object], name: str, request_id: UUID) -> str:
    value = required(data, name, request_id)
    if not isinstance(value, str):
        raise CliTransportError(
            f"{name} must be a string",
            request_id=request_id,
            details={"field": name},
        )
    return value


def optional_text(data: Mapping[str, object], name: str, request_id: UUID) -> str | None:
    value = data.get(name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise CliTransportError(
            f"{name} must be a string",
            request_id=request_id,
            details={"field": name},
        )
    return value


def uuid_value(data: Mapping[str, object], name: str, request_id: UUID) -> UUID:
    value = text_value(data, name, request_id)
    try:
        return UUID(value)
    except (AttributeError, TypeError, ValueError) as exc:
        raise CliTransportError(
            f"{name} must be a valid UUID",
            request_id=request_id,
            details={"field": name},
        ) from exc


def optional_uuid(data: Mapping[str, object], name: str, request_id: UUID) -> UUID | None:
    value = data.get(name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise CliTransportError(
            f"{name} must be a valid UUID",
            request_id=request_id,
            details={"field": name},
        )
    try:
        return UUID(value)
    except (AttributeError, TypeError, ValueError) as exc:
        raise CliTransportError(
            f"{name} must be a valid UUID",
            request_id=request_id,
            details={"field": name},
        ) from exc


def int_value(
    data: Mapping[str, object], name: str, request_id: UUID, *, minimum: int | None = None
) -> int:
    value = required(data, name, request_id)
    if isinstance(value, bool) or not isinstance(value, int):
        raise CliTransportError(
            f"{name} must be an integer",
            request_id=request_id,
            details={"field": name},
        )
    if minimum is not None and value < minimum:
        raise CliTransportError(
            f"{name} must be at least {minimum}",
            request_id=request_id,
            details={"field": name},
        )
    return value


def float_or_none(data: Mapping[str, object], name: str, request_id: UUID) -> float | None:
    value = data.get(name)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, float | int):
        raise CliTransportError(
            f"{name} must be a number",
            request_id=request_id,
            details={"field": name},
        )
    return float(value)


def enum_value[T](data: Mapping[str, object], name: str, enum_type: type[T], request_id: UUID) -> T:
    value = text_value(data, name, request_id)
    try:
        return enum_type(value)
    except ValueError as exc:
        choices = [str(item.value) for item in enum_type]  # type: ignore[union-attr]
        raise CliTransportError(
            f"{name} must be one of: {', '.join(choices)}",
            request_id=request_id,
            details={"field": name, "choices": choices},
        ) from exc


def list_of_objects(
    data: Mapping[str, object], name: str, request_id: UUID
) -> list[dict[str, object]]:
    value = required(data, name, request_id)
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise CliTransportError(
            f"{name} must be a JSON array of objects",
            request_id=request_id,
            details={"field": name},
        )
    return [dict(item) for item in value]


def invoke(
    runtime: CliRuntime,
    json_mode: bool,
    operation: Callable[[], object],
) -> None:
    try:
        result = operation()
        emit_success(result, json_mode)
    except (CliTransportError, ResearchBaseError) as exc:
        emit_error(exc, runtime.request_id, json_mode)
        raise typer.Exit(code=cli_exit_code(exc)) from None
    except Exception:
        emit_error(RuntimeError("unexpected internal error"), runtime.request_id, json_mode)
        raise typer.Exit(code=70) from None
