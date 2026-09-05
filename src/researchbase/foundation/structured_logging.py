"""Small JSON event writer for the Phase 1 command boundary."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from time import monotonic
from typing import Any

logger = logging.getLogger("researchbase.commands")
_application_env = "development"
_operation_context: ContextVar[dict[str, Any] | None] = ContextVar(
    "researchbase_operation_context", default=None
)
_SENSITIVE_KEY = re.compile(r"(?:database_url|password|passwd|token|credential)", re.IGNORECASE)
_SENSITIVE_TEXT = re.compile(
    r"(?i)(postgres(?:ql)?(?:\+[^:/\s]+)?://[^:\s/]+:)[^@\s]+@"
    r"|(password|passwd|token|credentials?)\s*[:=]\s*[^\s,;}]+"
)


def configure_logging(log_level: str, application_env: str) -> None:
    """Apply the frozen runtime logging settings without owning transactions."""

    global _application_env
    _application_env = application_env
    logger.setLevel(getattr(logging, log_level.upper()))


@contextmanager
def operation_context(
    *, command_name: str, context: Any = None, project_id: Any = None, target_id: Any = None
) -> Iterator[None]:
    values = {
        "command_name": command_name,
        "request_id": getattr(context, "request_id", None),
        "correlation_id": getattr(context, "correlation_id", None),
        "actor_id": getattr(context, "actor_id", None),
        "project_id": project_id,
        "target_id": target_id,
    }
    token = _operation_context.set(values)
    try:
        yield
    finally:
        _operation_context.reset(token)


def _identifier(value: Any) -> str | None:
    return str(value) if value is not None else None


def _redact_value(key: str, value: Any) -> Any:
    if _SENSITIVE_KEY.search(key):
        return "[REDACTED]"
    if isinstance(value, Mapping):
        return {
            str(item_key): _redact_value(str(item_key), item_value)
            for item_key, item_value in value.items()
        }
    if isinstance(value, list | tuple):
        return [_redact_value(key, item) for item in value]
    if isinstance(value, str):
        return _SENSITIVE_TEXT.sub(
            lambda match: "[REDACTED]" if match.group(1) else f"{match.group(2)}=[REDACTED]",
            value,
        )
    return value


def emit_application_event(
    *,
    command_name: str,
    request_id: Any,
    correlation_id: Any,
    actor_id: Any,
    project_id: Any,
    target_id: Any,
    result: str,
    error_code: Any,
    duration_ms: float,
    rollback: bool,
) -> None:
    """Emit the transport-neutral Application/UoW event contract."""

    level = "ERROR" if result == "failure" else "INFO"
    payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        "level": level,
        "request_id": _identifier(request_id),
        "correlation_id": _identifier(correlation_id),
        "command_name": command_name,
        "actor_id": _identifier(actor_id),
        "project_id": _identifier(project_id),
        "target_id": _identifier(target_id),
        "result": result,
        "error_code": str(error_code) if error_code is not None else None,
        "duration_ms": round(duration_ms, 3),
        "rollback": rollback,
        "application_env": _application_env,
    }
    logger.log(
        logging.ERROR if level == "ERROR" else logging.INFO, json.dumps(payload, sort_keys=True)
    )


def emit_uow_rollback(error_code: Any = None) -> None:
    """Record rollback context from the current Application command."""

    context = _operation_context.get() or {}
    emit_application_event(
        command_name=str(context.get("command_name", "unknown")),
        request_id=context.get("request_id"),
        correlation_id=context.get("correlation_id"),
        actor_id=context.get("actor_id"),
        project_id=context.get("project_id"),
        target_id=context.get("target_id"),
        result="failure",
        error_code=error_code,
        duration_ms=0,
        rollback=True,
    )


def emit_event(event: str, fields: Mapping[str, Any]) -> None:
    context = _operation_context.get() or {}
    duration = fields.get("duration")
    duration_ms = fields.get("duration_ms")
    if duration_ms is None and isinstance(duration, int | float):
        duration_ms = round(duration * 1000, 3)
    safe_fields = {str(key): _redact_value(str(key), value) for key, value in fields.items()}
    payload = {
        "event": event,
        "timestamp": datetime.now(UTC).isoformat(),
        "level": "ERROR" if fields.get("result") == "failure" else "INFO",
        "request_id": _identifier(fields.get("request_id", context.get("request_id"))),
        "correlation_id": _identifier(fields.get("correlation_id", context.get("correlation_id"))),
        "command_name": fields.get("command", context.get("command_name", "unknown")),
        "actor_id": _identifier(fields.get("actor_id", context.get("actor_id"))),
        "project_id": _identifier(fields.get("project_id", context.get("project_id"))),
        "target_id": _identifier(fields.get("target_id", context.get("target_id"))),
        "result": fields.get("result"),
        "error_code": fields.get("error_code", fields.get("semantic_error")),
        "duration_ms": duration_ms,
        "rollback": fields.get("rollback", False),
        "application_env": _application_env,
        **safe_fields,
    }
    logger.info(json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")))


def elapsed(start: float) -> float:
    return round(monotonic() - start, 6)
