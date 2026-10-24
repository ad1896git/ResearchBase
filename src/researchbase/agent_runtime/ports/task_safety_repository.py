"""Safety port and the nonserializable capability of the in-process fake consumer."""

from collections.abc import Callable
from typing import Any, Protocol
from uuid import UUID

from researchbase.agent_runtime.application.safety_contracts import SafetyCommandResult
from researchbase.agent_runtime.ports.task_repository import TaskRepository


class TaskSafetyRepository(TaskRepository, Protocol):
    def lock_write(
        self,
        project: UUID,
        actor: UUID,
        command: UUID,
        task: UUID,
        *,
        after_wait: Callable[[], Any] | None = None,
    ) -> None: ...
    def lock_prefix(
        self,
        project: UUID,
        actor: UUID,
        command: UUID,
        task: UUID,
        *,
        after_wait: Callable[[], Any] | None = None,
    ) -> None: ...
    def lock_task_rows(
        self, task: UUID, *, after_wait: Callable[[], Any] | None = None
    ) -> None: ...
    def lock_safety(self, task: UUID, *, after_wait: Callable[[], Any] | None = None) -> None: ...
    def rows(self, table: str, task: UUID, *, lock: bool = False) -> list[dict[str, Any]]: ...
    def respond(self, identity: UUID, values: dict[str, Any]) -> None: ...
    def safety_result(self, receipt: dict[str, Any], *, replayed: bool) -> SafetyCommandResult: ...
    def scope_reference(
        self, kind: str, identity: UUID, project: UUID
    ) -> dict[str, Any] | None: ...
    def snapshot_at(self) -> Any: ...
    def identity_occupied(self, identity: UUID) -> bool: ...
    def receipt_history(self, task: UUID) -> list[dict[str, Any]]: ...


class FakeConsumerCapability:
    """Object identity is injected at composition; public request material cannot carry it."""

    __slots__ = ()
