"""Caller-neutral execution metadata for application boundaries."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

ClientType = Literal["human_ui", "cli", "agent", "service", "test"]


class ExecutionContext(BaseModel):
    """Observability and policy context shared by human, CLI, agent, service, and test callers."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    actor_id: UUID
    request_id: UUID
    correlation_id: UUID | None = None
    causation_id: UUID | None = None
    client_type: ClientType
    client_name: str | None = None
    client_version: str | None = None
