# ruff: noqa: E501
"""PR3-01 SQL adapter; the literal first SHARE precedes all scoped lock waits."""

from sqlalchemy import text
from sqlalchemy.orm import Session

from researchbase.agent_runtime.application.contracts import CommandResult
from researchbase.persistence.literature_search_plan_repository import (
    SqlAlchemyLiteratureSearchPlanRepository,
)
from researchbase.persistence.research_task_queries import input_version

SHARE_TABLES = (
    "actor_subject_bindings",
    "actors",
    "artifact_versions",
    "artifacts",
    "claim_versions",
    "claims",
    "hypothesis_versions",
    "hypotheses",
    "literature_source_project_links",
    "literature_sources",
    "manuscript_versions",
    "project_memberships",
    "project_role_assignments",
    "projects",
    "publications",
    "research_question_versions",
    "research_questions",
    "source_versions",
)
SHARE_SQL = "LOCK TABLE " + ", ".join(SHARE_TABLES) + " IN SHARE MODE"
TABLES = frozenset(
    {
        "research_tasks",
        "research_task_steps",
        "research_task_step_dependencies",
        "research_task_inputs",
        "research_task_step_inputs",
        "research_task_command_receipts",
        "research_task_events",
        "research_task_step_events",
        "research_task_receipt_events",
        "research_task_receipt_step_events",
    }
)


class SqlAlchemyResearchTaskRepository:
    def __init__(self, session: Session):
        self._session = session
        self._authority = SqlAlchemyLiteratureSearchPlanRepository(session, protected_reads=True)

    def _many(self, sql, params):
        return [dict(r) for r in self._session.execute(text(sql), params).mappings()]

    def lock_write(self, project, actor, command, task):
        self._session.execute(text(SHARE_SQL))
        self._session.execute(text("SELECT rb_phase2_lock_project(:id)"), {"id": project})
        for key in (f"pr301:command:{project}:{actor}:{command}", f"pr301:task:{task}"):
            self._session.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"), {"key": key}
            )
        self._many("SELECT id FROM research_tasks WHERE id=:id FOR UPDATE", {"id": task})
        self._many(
            "SELECT id FROM research_task_steps WHERE research_task_id=:id ORDER BY id FOR UPDATE",
            {"id": task},
        )
        # Fixed table/primary-key read order after every blocking wait.
        self.edges(task)
        self.inputs(task)
        self.inputs(task, step=True)

    def task(self, identity):
        rows = self._many("SELECT * FROM research_tasks WHERE id=:id", {"id": identity})
        return rows[0] if rows else None

    def steps(self, task):
        return self._many(
            "SELECT * FROM research_task_steps WHERE research_task_id=:id ORDER BY ordinal,id",
            {"id": task},
        )

    def edges(self, task):
        return self._many(
            "SELECT predecessor_id,dependent_id FROM research_task_step_dependencies WHERE research_task_id=:id ORDER BY predecessor_id,dependent_id",
            {"id": task},
        )

    def inputs(self, task, *, step=False):
        table = "research_task_step_inputs" if step else "research_task_inputs"
        return self._many(
            f"SELECT * FROM {table} WHERE research_task_id=:id ORDER BY id", {"id": task}
        )

    def events(self, task, *, step=False):
        table = "research_task_step_events" if step else "research_task_events"
        order = "step_id,sequence" if step else "sequence"
        return self._many(
            f"SELECT * FROM {table} WHERE research_task_id=:id ORDER BY {order}", {"id": task}
        )

    def receipt(self, project, actor, command):
        rows = self._many(
            "SELECT * FROM research_task_command_receipts WHERE project_id=:project AND actor_id=:actor AND command_id=:command",
            {"project": project, "actor": actor, "command": command},
        )
        return rows[0] if rows else None

    def result(self, receipt, *, replayed):
        task_events = self._many(
            "SELECT e.id FROM research_task_receipt_events l JOIN research_task_events e ON e.id=l.event_id WHERE l.receipt_id=:id ORDER BY e.sequence",
            {"id": receipt["id"]},
        )
        step_events = self._many(
            "SELECT e.id FROM research_task_receipt_step_events l JOIN research_task_step_events e ON e.id=l.step_event_id WHERE l.receipt_id=:id ORDER BY e.step_id,e.sequence",
            {"id": receipt["id"]},
        )
        return CommandResult(
            receipt["research_task_id"],
            receipt["resulting_row_version"],
            tuple(r["id"] for r in task_events),
            tuple(r["id"] for r in step_events),
            replayed,
        )

    def insert(self, table, row):
        if table not in TABLES:
            raise ValueError("unknown planning table")
        self._session.execute(
            text(
                f"INSERT INTO {table} ({','.join(row)}) VALUES ({','.join(':' + k for k in row)})"
            ),
            row,
        )

    def update_task(self, identity, values):
        self._session.execute(
            text(
                "UPDATE research_tasks SET "
                + ",".join(k + "=:" + k for k in values)
                + " WHERE id=:id"
            ),
            {**values, "id": identity},
        )

    def cancel_steps(self, task, at):
        self._session.execute(
            text(
                "UPDATE research_task_steps SET status='CANCELLED',finished_at=:at,row_version=row_version+1 WHERE research_task_id=:id AND status='PENDING'"
            ),
            {"id": task, "at": at},
        )

    def authority(self, principal, project):
        return self._authority.authorize(principal, project)

    def at(self):
        return self._authority.at()

    def project_active(self, project):
        return self._authority.project_active(project)

    def input_version(self, kind, identity, project):
        return input_version(self._session, kind, identity, project)

    def force_constraints(self):
        self._session.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
