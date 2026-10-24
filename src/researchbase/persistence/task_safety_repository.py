"""Typed safety SQL adapter; all mutations use the existing task lock namespace."""

# ruff: noqa: E501
from datetime import datetime

from sqlalchemy import text

from researchbase.agent_runtime.application.safety_contracts import SafetyCommandResult
from researchbase.foundation.time import to_utc
from researchbase.persistence.research_task_repository import (
    SHARE_SQL,
    SqlAlchemyResearchTaskRepository,
)
from researchbase.persistence.task_safety_queries import snapshot_time

SAFETY_TABLES = (
    "budget_reservations",
    "budget_usage_records",
    "checkpoint_policies",
    "checkpoint_policy_dataset_scopes",
    "checkpoint_policy_metric_scopes",
    "execution_budgets",
    "human_checkpoints",
    "termination_policies",
)
RESULT_TABLES = (
    "execution_budgets",
    "termination_policies",
    "checkpoint_policies",
    "checkpoint_policy_dataset_scopes",
    "checkpoint_policy_metric_scopes",
    "budget_reservations",
    "budget_usage_records",
    "human_checkpoints",
)


class SqlAlchemyTaskSafetyRepository(SqlAlchemyResearchTaskRepository):
    def _many(self, sql, params):
        return [
            {
                key: to_utc(value) if isinstance(value, datetime) else value
                for key, value in row.items()
            }
            for row in super()._many(sql, params)
        ]

    def at(self):
        return to_utc(super().at())

    def lock_write(self, project, actor, command, task, *, after_wait=None):
        self.lock_prefix(project, actor, command, task, after_wait=after_wait)
        self.lock_task_rows(task, after_wait=after_wait)

    def lock_prefix(self, project, actor, command, task, *, after_wait=None):
        def fresh():
            if after_wait is not None:
                after_wait()

        self._session.execute(text(SHARE_SQL))
        fresh()
        self._session.execute(text("SELECT rb_phase2_lock_project(:id)"), {"id": project})
        fresh()
        for key in (f"pr301:command:{project}:{actor}:{command}", f"pr301:task:{task}"):
            self._session.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"), {"key": key}
            )
            fresh()

    def lock_task_rows(self, task, *, after_wait=None):
        def fresh():
            if after_wait is not None:
                after_wait()

        self._many("SELECT id FROM research_tasks WHERE id=:id FOR UPDATE", {"id": task})
        fresh()
        self._many(
            "SELECT id FROM research_task_steps WHERE research_task_id=:id ORDER BY id FOR UPDATE",
            {"id": task},
        )
        fresh()
        self.edges(task)
        self.inputs(task)
        self.inputs(task, step=True)

    def lock_safety(self, task, *, after_wait=None):
        for table in SAFETY_TABLES:
            self.rows(table, task, lock=table == "human_checkpoints")
            if table == "human_checkpoints" and after_wait is not None:
                after_wait()

    def rows(self, table, task, *, lock=False):
        if table not in SAFETY_TABLES:
            raise ValueError("unknown safety table")
        return self._many(
            f"SELECT * FROM {table} WHERE research_task_id=:id ORDER BY id"
            + (" FOR UPDATE" if lock else ""),
            {"id": task},
        )

    def insert(self, table, row):
        if table not in SAFETY_TABLES:
            return super().insert(table, row)
        self._session.execute(
            text(
                f"INSERT INTO {table} ({','.join(row)}) VALUES ({','.join(':' + k for k in row)})"
            ),
            row,
        )

    def respond(self, identity, values):
        self._session.execute(
            text(
                "UPDATE human_checkpoints SET "
                + ",".join(k + "=:" + k for k in values)
                + " WHERE id=:id"
            ),
            {**values, "id": identity},
        )

    def safety_result(self, receipt, *, replayed):
        ids = []
        for table in RESULT_TABLES:
            ids.append(
                tuple(
                    r["id"]
                    for r in self._many(
                        f"SELECT id FROM {table} WHERE receipt_id=:id ORDER BY id",
                        {"id": receipt["id"]},
                    )
                )
            )
        ids.append(
            tuple(
                r["id"]
                for r in self._many(
                    "SELECT id FROM human_checkpoints WHERE response_receipt_id=:id ORDER BY id",
                    {"id": receipt["id"]},
                )
            )
        )
        return SafetyCommandResult(self.result(receipt, replayed=replayed), *ids)

    def scope_reference(self, kind, identity, project):
        if kind == "dataset":
            sql = "SELECT v.content_hash,d.project_id=:project AS scoped,true AS frozen FROM dataset_snapshots v JOIN datasets d ON d.id=v.dataset_id WHERE v.id=:id"
        elif kind == "metric":
            sql = "SELECT v.content_hash,(d.project_id=:project OR d.project_id IS NULL) AS scoped,(v.status IN ('FROZEN','SUPERSEDED') AND v.frozen_at IS NOT NULL AND v.content_hash IS NOT NULL) AS frozen FROM metric_definition_versions v JOIN metric_definitions d ON d.id=v.metric_definition_id WHERE v.id=:id"
        else:
            raise ValueError("unknown scope kind")
        rows = self._many(sql, {"id": identity, "project": project})
        return rows[0] if rows else None

    def snapshot_at(self):
        return to_utc(snapshot_time(self._session))

    def receipt_history(self, task):
        return self._many(
            "SELECT id,resulting_row_version FROM research_task_command_receipts WHERE research_task_id=:id ORDER BY resulting_row_version",
            {"id": task},
        )

    def identity_occupied(self, identity):
        return bool(
            self._many(
                "SELECT id FROM ("
                + " UNION ALL ".join(f"SELECT id FROM {t} WHERE id=:id" for t in SAFETY_TABLES)
                + ") occupied LIMIT 1",
                {"id": identity},
            )
        )
