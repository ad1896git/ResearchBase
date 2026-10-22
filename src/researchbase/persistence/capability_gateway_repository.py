"""Inert stored-row adapter and composed PR3-03 locks in the caller's transaction."""

from collections.abc import Callable
from typing import Any, cast
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import CursorResult

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
        invocation_id: UUID | None = None,
        after_wait: Callable[[], object] | None = None,
    ) -> None:
        self.lock_prefix(project, actor, command, task, after_wait=after_wait)
        if invocation_id is not None:
            target = self.invocation(project, task, invocation_id)
            agent_version = target["agent_version_id"] if target else None
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

    def committed_receipt(self, project, actor, command):
        rows = self._many(
            COMMITTED_RECEIPT_SQL,
            {
                "project": project,
                "actor": actor,
                "command": command,
            },
        )
        return rows[0] if rows else None

    def policy_version_occupied(self, project, version):
        return bool(self._many(POLICY_VERSION_SQL, {"project": project, "version": version}))

    def gateway_identity_occupied(self, table, identity):
        if table not in ("agent_tool_policies", "capability_invocations"):
            raise ValueError("unknown gateway identity")
        return bool(self._many(IDENTITY_SQL.format(table=table), {"id": identity}))

    def task_invocations(self, project, task):
        return self._many(TASK_INVOCATIONS_SQL, {"project": project, "task": task})

    def invocation_page(self, project, task, limit, after_at, after_id):
        from researchbase.persistence.capability_gateway_queries import invocation_page

        return invocation_page(self._session, project, task, limit, after_at, after_id)

    def agent_version(self, identity):
        return self._agents.version(identity)

    def agent_availability(self, identity):
        return self._agents.availability(identity)

    def live_agent(self, actor, project):
        return self._agents.live_agent(actor, project)

    def artifact_pin(self, project, identity):
        rows = self._many(ARTIFACT_PIN_SQL, {"project": project, "id": identity})
        return rows[0] if rows else None

    def insert(self, table, row):
        if table not in GATEWAY_WRITES:
            return super().insert(table, row)
        # Names originate only in the closed table/column whitelist, never submitted SQL.
        if not set(row) <= GATEWAY_WRITES[table]:
            raise ValueError("unknown gateway column")
        sql = INSERT_SQL.format(
            table=table,
            columns=",\n".join(row),
            parameters=",\n".join(":" + key for key in row),
        )
        self._session.execute(text(sql), row)

    def update_invocation(self, identity, expected_revision, values):
        allowed = {
            "status",
            "row_version",
            "started_at",
            "start_receipt_id",
            "finished_at",
            "finish_receipt_id",
            "usage_record_id",
            "trace_artifact_version_id",
            "trace_content_hash",
            "result_summary",
            "error_code",
        }
        if not values or not set(values) <= allowed:
            raise ValueError("unknown invocation mutation")
        from researchbase.foundation.errors import ErrorCode, ResearchBaseError

        result = self._session.execute(
            text(
                UPDATE_INVOCATION_SQL.format(
                    assignments=",\n".join(f"{key}=:{key}" for key in values)
                )
            ),
            {"identity": identity, "expected_revision": expected_revision, **values},
        )
        if cast(CursorResult[Any], result).rowcount != 1:
            raise ResearchBaseError(ErrorCode.CONCURRENT_MODIFICATION, "stale invocation revision")

    def gateway_result(self, receipt, *, replayed):
        from researchbase.agent_runtime.application.gateway_contracts import GatewayCommandResult

        rows = self._many(SAVED_EVENT_SQL, {"id": receipt["result_capability_event_id"]})
        event: Any = rows[0] if rows else None
        return GatewayCommandResult(
            receipt["id"],
            receipt["project_id"],
            receipt["research_task_id"],
            receipt["actor_id"],
            receipt["command_id"],
            receipt["command_name"],
            receipt["result_tool_policy_id"],
            receipt["result_capability_invocation_id"],
            receipt["result_capability_event_id"],
            event["reservation_id"] if event else None,
            event["usage_record_id"] if event else None,
            receipt["resulting_row_version"],
            receipt["resulting_invocation_revision"],
            receipt["completed_at"],
            replayed,
        )


COMMITTED_RECEIPT_SQL = """
SELECT * FROM research_task_command_receipts
WHERE project_id=:project AND actor_id=:actor AND command_id=:command
  AND xmin <> pg_current_xact_id()::xid
"""
POLICY_VERSION_SQL = """
SELECT id FROM agent_tool_policies WHERE project_id=:project AND version=:version
"""
IDENTITY_SQL = """
SELECT id FROM {table} WHERE id=:id
"""
TASK_INVOCATIONS_SQL = """
SELECT * FROM capability_invocations
WHERE project_id=:project AND research_task_id=:task ORDER BY id
"""
ARTIFACT_PIN_SQL = """
SELECT v.*, a.project_id, a.project_id=:project AS scoped
FROM artifact_versions v JOIN artifacts a ON a.id=v.artifact_id WHERE v.id=:id
"""
INSERT_SQL = """
INSERT INTO {table} (
{columns}
) VALUES (
{parameters}
)
"""
SAVED_EVENT_SQL = """
SELECT reservation_id,usage_record_id FROM capability_invocation_events WHERE id=:id
"""
# Closed stored-row vocabulary is the write whitelist; no later lifecycle mutation is exposed.
GATEWAY_WRITES = {
    "agent_tool_policies": frozenset(StoredToolPolicy.__annotations__),
    "agent_tool_policy_permissions": frozenset(StoredPermission.__annotations__),
    "capability_invocations": frozenset(StoredInvocation.__annotations__),
    "capability_invocation_refs": frozenset(StoredInvocationRef.__annotations__),
    "capability_invocation_events": frozenset(StoredInvocationEvent.__annotations__),
}

UPDATE_INVOCATION_SQL = """
UPDATE capability_invocations SET
{assignments}
WHERE id=:identity AND row_version=:expected_revision
"""
