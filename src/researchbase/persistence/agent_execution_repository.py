# ruff: noqa: E501
"""Intent SQL adapter: exact prefix, explicit parent locks and historical reads."""

from datetime import datetime
from typing import Any, cast

from sqlalchemy import text

from researchbase.agent_runtime.application.execution_contracts import (
    AgentExecutionDTO,
    AgentExecutionEventDTO,
)
from researchbase.agent_runtime.domain.agent_execution import ExecutionInput
from researchbase.foundation.time import to_utc
from researchbase.persistence.agent_version_repository import SqlAlchemyAgentRepository
from researchbase.persistence.research_task_repository import SqlAlchemyResearchTaskRepository

INTENT_SHARE_SQL = "LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_membership_events, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions, strategy_candidate_captures, strategy_candidate_sources, strategy_hypothesis_admissions, strategy_question_admissions IN SHARE MODE"


class SqlAlchemyExecutionRepository(SqlAlchemyAgentRepository):
    def __init__(self, session):
        super().__init__(session)
        self._tasks = SqlAlchemyResearchTaskRepository(session)

    def lock_write(self, command, after_wait):
        self._session.execute(text(INTENT_SHARE_SQL))
        after_wait()
        self.one("SELECT rb_phase2_lock_project(:id)", id=command.project_id)
        after_wait()
        self.advisory(
            f"pr302:command:{command.project_id}:{command.caller.actor_id}:{command.command_id}"
        )
        after_wait()
        args = command.arguments
        version = self.version(args.agent_version_id)
        actor = version["actor_id"] if version else None
        if actor is not None:
            self.advisory(f"pr302:actor:{actor}")
            after_wait()
        for key in (
            f"pr301:task:{args.research_task_id}",
            f"pr302:version:{args.agent_version_id}",
            f"pr302:execution:{args.execution_id}",
        ):
            self.advisory(key)
            after_wait()
        for identity in sorted({command.caller.actor_id, actor} - {None}, key=str):
            self.many("SELECT id FROM actors WHERE id=:id FOR UPDATE", id=identity)
            after_wait()
        self.many("SELECT id FROM research_tasks WHERE id=:id FOR UPDATE", id=args.research_task_id)
        after_wait()
        # Lock individually so every possible row wait is followed by fresh authority.
        for step in sorted(self.steps(args.research_task_id), key=lambda s: str(s["id"])):
            self.many("SELECT id FROM research_task_steps WHERE id=:id FOR UPDATE", id=step["id"])
            after_wait()
        self.many(
            "SELECT agent_version_id FROM agent_availability WHERE agent_version_id=:id FOR UPDATE",
            id=args.agent_version_id,
        )
        after_wait()
        self.many(
            "SELECT id FROM agent_execution_instances WHERE id=:id FOR UPDATE", id=args.execution_id
        )
        after_wait()

    def execution(self, identity):
        return self.one("SELECT * FROM agent_execution_instances WHERE id=:id", id=identity)

    def task(self, identity):
        return self._tasks.task(identity)

    def steps(self, identity):
        return self._tasks.steps(identity)

    def input_version(self, kind, identity, project):
        return self._tasks.input_version(kind, identity, project)

    def inputs(self, task, step):
        values = []
        for selected in (False, True):
            for row in self._tasks.inputs(task, step=selected):
                if selected and row["step_id"] != step:
                    continue
                for kind in (
                    "RESEARCH_QUESTION_VERSION",
                    "HYPOTHESIS_VERSION",
                    "CLAIM_VERSION",
                    "SOURCE_VERSION",
                    "ARTIFACT_VERSION",
                    "MANUSCRIPT_VERSION",
                ):
                    identity = row[kind.lower() + "_id"]
                    if identity is not None:
                        values.append(
                            ExecutionInput(
                                "STEP" if selected else "TASK",
                                row["step_id"] if selected else task,
                                kind,
                                identity,
                                row["content_hash"],
                                row["hash_scheme"],
                            )
                        )
        return tuple(values)

    def insert(self, table, row):
        if table not in {
            "agent_execution_instances",
            "agent_execution_events",
            "agent_command_receipts",
        }:
            raise ValueError("unknown intent table")
        result = dict(
            self._session.execute(
                text(
                    f"INSERT INTO {table} ({','.join(row)}) VALUES ({','.join(':' + k for k in row)}) RETURNING *"
                ),
                row,
            )
            .mappings()
            .one()
        )
        return {k: to_utc(v) if isinstance(v, datetime) else v for k, v in result.items()}

    def dto(self, row):
        events = self.many(
            "SELECT * FROM agent_execution_events WHERE execution_id=:id ORDER BY sequence",
            id=row["id"],
        )
        return AgentExecutionDTO(
            **row, events=tuple(AgentExecutionEventDTO(**cast(dict[str, Any], e)) for e in events)
        )

    def page(self, query):
        rows = self.many(
            "SELECT * FROM agent_execution_instances WHERE project_id=:project AND research_task_id=:task AND (CAST(:after AS uuid) IS NULL OR id>CAST(:after AS uuid)) ORDER BY id LIMIT :limit",
            project=query.project_id,
            task=query.research_task_id,
            after=query.after_id,
            limit=query.limit,
        )
        return tuple(self.dto(row) for row in rows)
