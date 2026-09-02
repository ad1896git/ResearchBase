"""CLI invocation metadata mapped to the caller-neutral Application context."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from researchbase import __version__
from researchbase.foundation.execution_context import ExecutionContext
from researchbase.foundation.ids import new_uuid7

from .errors import CliTransportError


class CliServices(Protocol):
    @property
    def application(self) -> Any: ...

    @property
    def provenance(self) -> Any: ...

    @property
    def governance(self) -> Any: ...

    @property
    def governance_queries(self) -> Any: ...


@dataclass(frozen=True, slots=True)
class CliRuntime:
    """Immutable state for exactly one CLI invocation."""

    services: CliServices
    request_id: UUID
    actor_id: UUID | None
    correlation_id: UUID | None
    causation_id: UUID | None
    client_name: str
    client_version: str


def parse_uuid_option(value: str | None, option: str, request_id: UUID) -> UUID | None:
    if value is None:
        return None
    try:
        return UUID(value)
    except (AttributeError, TypeError, ValueError) as exc:
        raise CliTransportError(
            f"{option} must be a valid UUID",
            request_id=request_id,
            details={"option": option},
        ) from exc


def create_runtime(
    services: CliServices,
    actor_id: str | None,
    request_id: str | None,
    correlation_id: str | None,
    causation_id: str | None,
    client_name: str | None,
    client_version: str | None,
) -> CliRuntime:
    if request_id is None:
        effective_request_id = new_uuid7()
    else:
        try:
            effective_request_id = UUID(request_id)
        except (AttributeError, TypeError, ValueError) as exc:
            generated_request_id = new_uuid7()
            raise CliTransportError(
                "--request-id must be a valid UUID",
                request_id=generated_request_id,
                details={"option": "--request-id"},
            ) from exc
    return CliRuntime(
        services=services,
        request_id=effective_request_id,
        actor_id=parse_uuid_option(actor_id, "--actor-id", effective_request_id),
        correlation_id=parse_uuid_option(correlation_id, "--correlation-id", effective_request_id),
        causation_id=parse_uuid_option(causation_id, "--causation-id", effective_request_id),
        client_name=client_name or "researchbase-cli",
        client_version=client_version or __version__,
    )


def execution_context(runtime: CliRuntime) -> ExecutionContext:
    if runtime.actor_id is None:
        raise CliTransportError(
            "--actor-id is required for this command",
            request_id=runtime.request_id,
            details={"option": "--actor-id"},
        )
    return ExecutionContext(
        actor_id=runtime.actor_id,
        request_id=runtime.request_id,
        correlation_id=runtime.correlation_id,
        causation_id=runtime.causation_id,
        client_type="cli",
        client_name=runtime.client_name,
        client_version=runtime.client_version,
    )
