"""Inert stored-row adapter and composed PR3-03 locks in the caller's transaction."""

from collections.abc import Callable
from typing import cast
from uuid import UUID

from sqlalchemy import text

from researchbase.agent_runtime.ports.gateway_repository import (
    StoredGatewayReceipt,
    StoredInvocation,
    StoredInvocationEvent,
    StoredInvocationRef,
    StoredPermission,
    StoredTaskEvent,
    StoredToolPolicy,
)
from researchbase.persistence.agent_version_repository import SqlAlchemyAgentRepository
from researchbase.persistence.task_safety_repository import SqlAlchemyTaskSafetyRepository

ADVISORY_SQL = """
SELECT pg_advisory_xact_lock(hashtextextended(:key,0))
"""
AVAILABILITY_LOCK_SQL = """
SELECT * FROM agent_availability WHERE agent_version_id=:id FOR UPDATE
"""
GATEWAY_LOCK_READS = (
    """
    SELECT * FROM agent_tool_policies WHERE project_id=:project ORDER BY id
    """,
    """
    SELECT * FROM agent_tool_policy_permissions WHERE project_id=:project ORDER BY id
    """,
    """
    SELECT * FROM capability_invocations
    WHERE project_id=:project AND research_task_id=:task ORDER BY id FOR UPDATE
    """,
    """
    SELECT * FROM capability_invocation_refs
    WHERE project_id=:project AND research_task_id=:task ORDER BY id
    """,
    """
    SELECT * FROM capability_invocation_events
    WHERE project_id=:project AND research_task_id=:task ORDER BY id
    """,
)
POLICY_SQL = """
SELECT * FROM agent_tool_policies WHERE project_id=:project AND id=:id
"""
PERMISSIONS_SQL = """
SELECT * FROM agent_tool_policy_permissions WHERE project_id=:project AND policy_id=:id
ORDER BY capability_id,capability_version,operation,adapter_id,adapter_version,
         parameter_schema_hash,effect
"""
INVOCATION_SQL = """
SELECT * FROM capability_invocations
WHERE project_id=:project AND research_task_id=:task AND id=:id
"""
REFS_SQL = """
SELECT * FROM capability_invocation_refs
WHERE project_id=:project AND research_task_id=:task AND invocation_id=:id
ORDER BY direction,
    CASE
        WHEN research_question_version_id IS NOT NULL THEN 'RESEARCH_QUESTION_VERSION'
        WHEN hypothesis_version_id IS NOT NULL THEN 'HYPOTHESIS_VERSION'
        WHEN claim_version_id IS NOT NULL THEN 'CLAIM_VERSION'
        WHEN source_version_id IS NOT NULL THEN 'SOURCE_VERSION'
        WHEN artifact_version_id IS NOT NULL THEN 'ARTIFACT_VERSION'
        WHEN manuscript_version_id IS NOT NULL THEN 'MANUSCRIPT_VERSION'
    END,
    coalesce(research_question_version_id,hypothesis_version_id,claim_version_id,
             source_version_id,artifact_version_id,manuscript_version_id)
"""
EVENTS_SQL = """
SELECT * FROM capability_invocation_events
WHERE project_id=:project AND research_task_id=:task AND invocation_id=:id ORDER BY sequence
"""
RECEIPT_SQL = """
SELECT * FROM research_task_command_receipts
WHERE project_id=:project AND actor_id=:actor AND command_id=:command
"""
TASK_EVENTS_SQL = """
SELECT * FROM research_task_events WHERE research_task_id=:task ORDER BY sequence
"""


class SqlAlchemyGatewayRepository(SqlAlchemyTaskSafetyRepository):
    def __init__(self, session):
        super().__init__(session)
        self._agents = SqlAlchemyAgentRepository(session)

    def lock_gateway(
        self,
        project: UUID,
        actor: UUID,
        command: UUID,
        task: UUID,
        *,
        agent_version: UUID | None = None,
        after_wait: Callable[[], object] | None = None,
    ) -> None:
        self.lock_prefix(project, actor, command, task, after_wait=after_wait)
        if agent_version is not None:
            # Immutable identity lookup is deliberately unlocked; diagnostics follow the keys.
            # Missing versions have no derivable actor key. Keep the version key;
            # Application admission must reject absence before relying on these locks.
            version = self._agents.version(agent_version)
            keys = []
            if version is not None:
                keys.append(f"pr302:actor:{version['actor_id']}")
            keys.append(f"pr302:version:{agent_version}")
            for key in keys:
                self._session.execute(text(ADVISORY_SQL), {"key": key})
                if after_wait is not None:
                    after_wait()
        self.lock_task_rows(task, after_wait=after_wait)
        self.lock_safety(task, after_wait=after_wait)
        if agent_version is not None:
            self._many(AVAILABILITY_LOCK_SQL, {"id": agent_version})
            if after_wait is not None:
                after_wait()
            self._agents.version(agent_version)
        for sql in GATEWAY_LOCK_READS:
            self._many(sql, {"project": project, "task": task})
            if "FOR UPDATE" in sql and after_wait is not None:
                after_wait()

    def policy(self, project: UUID, identity: UUID) -> StoredToolPolicy | None:
        rows = self._many(POLICY_SQL, {"project": project, "id": identity})
        return cast(StoredToolPolicy, rows[0]) if rows else None

    def permissions(self, project: UUID, policy: UUID) -> list[StoredPermission]:
        return cast(
            list[StoredPermission], self._many(PERMISSIONS_SQL, {"project": project, "id": policy})
        )

    def invocation(self, project: UUID, task: UUID, identity: UUID) -> StoredInvocation | None:
        rows = self._many(INVOCATION_SQL, {"project": project, "task": task, "id": identity})
        return cast(StoredInvocation, rows[0]) if rows else None

    def invocation_refs(
        self, project: UUID, task: UUID, invocation: UUID
    ) -> list[StoredInvocationRef]:
        return cast(
            list[StoredInvocationRef],
            self._many(REFS_SQL, {"project": project, "task": task, "id": invocation}),
        )

    def invocation_events(
        self, project: UUID, task: UUID, invocation: UUID
    ) -> list[StoredInvocationEvent]:
        return cast(
            list[StoredInvocationEvent],
            self._many(EVENTS_SQL, {"project": project, "task": task, "id": invocation}),
        )

    def gateway_receipt(
        self, project: UUID, actor: UUID, command: UUID
    ) -> StoredGatewayReceipt | None:
        rows = self._many(RECEIPT_SQL, {"project": project, "actor": actor, "command": command})
        return cast(StoredGatewayReceipt, rows[0]) if rows else None

    def gateway_task_events(self, task: UUID) -> list[StoredTaskEvent]:
        return cast(list[StoredTaskEvent], self._many(TASK_EVENTS_SQL, {"task": task}))
