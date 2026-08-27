"""Minimal identity domain objects owned by PR-02."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from researchbase.foundation.enums import BaseStrEnum
from researchbase.foundation.ids import ActorId
from researchbase.foundation.time import to_utc


class ActorType(BaseStrEnum):
    HUMAN = "human"
    AGENT = "agent"
    SERVICE = "service"


@dataclass(frozen=True, slots=True)
class Actor:
    id: ActorId
    actor_type: ActorType
    display_name: str
    created_at: datetime
    external_key: str | None = None
    retired_at: datetime | None = None
    row_version: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID):
            raise TypeError("id must be UUID-compatible")
        object.__setattr__(self, "actor_type", ActorType(self.actor_type))
        if not self.display_name.strip():
            raise ValueError("display_name must not be blank")
        object.__setattr__(self, "created_at", to_utc(self.created_at))
        if self.retired_at is not None:
            object.__setattr__(self, "retired_at", to_utc(self.retired_at))
        if self.row_version < 1:
            raise ValueError("row_version must be positive")
