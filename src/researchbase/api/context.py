"""Request-scoped HTTP metadata to caller-neutral ExecutionContext mapping."""

from typing import Annotated
from uuid import UUID

from fastapi import Header, Request

from researchbase.foundation.execution_context import ExecutionContext


def execution_context(
    request: Request,
    actor_id: Annotated[UUID, Header(alias="X-Actor-ID")],
    correlation_id: Annotated[UUID | None, Header(alias="X-Correlation-ID")] = None,
    causation_id: Annotated[UUID | None, Header(alias="X-Causation-ID")] = None,
    client_name: Annotated[str | None, Header(alias="X-Client-Name")] = None,
    client_version: Annotated[str | None, Header(alias="X-Client-Version")] = None,
) -> ExecutionContext:
    return ExecutionContext(
        actor_id=actor_id,
        request_id=request.state.request_id,
        correlation_id=correlation_id,
        causation_id=causation_id,
        client_type="human_ui",
        client_name=client_name,
        client_version=client_version,
    )
