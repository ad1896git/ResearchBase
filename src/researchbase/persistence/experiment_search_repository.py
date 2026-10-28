"""S2 storage only, in the caller's existing transaction and snapshot.

No admission decisions, transaction ownership, Run-link writer, or D1 activation.
Fresh callbacks belong to Application; they can inspect own-effect progress and
committed replay separately without recursively entering any locking helper.
"""

from collections.abc import Mapping
from datetime import datetime
from typing import Any, cast, get_type_hints
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from researchbase.agent_runtime.ports.gateway_repository import StoredTaskEvent
from researchbase.agent_runtime.ports.search_repository import (
    FreshSearchValidation,
    SearchCallerKind,
    SearchStorageStage,
    StoredExperimentSpecReference,
    StoredHypothesisReference,
    StoredSearchEvent,
    StoredSearchNode,
    StoredSearchNodeRun,
    StoredSearchReceipt,
    StoredSearchRun,
    StoredSearchSession,
    StoredSearchWriteRows,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.time import to_utc
from researchbase.persistence.research_task_repository import SHARE_SQL
from researchbase.persistence.task_safety_repository import (
    SAFETY_TABLES,
    SqlAlchemyTaskSafetyRepository,
)

COMMITTED_RECEIPT_SQL = """
SELECT * FROM research_task_command_receipts
WHERE project_id=:project AND actor_id=:actor AND command_id=:command
AND xmin<>pg_current_xact_id()::xid
"""
HYPOTHESIS_SQL = """
SELECT v.id,v.hypothesis_id,o.project_id,v.status,v.frozen_at,v.content_hash
FROM hypothesis_versions v JOIN hypotheses o ON o.id=v.hypothesis_id WHERE v.id=:id
"""
EXPERIMENT_SPEC_SQL = """
SELECT v.id,v.experiment_spec_id,o.project_id,v.status,v.frozen_at,v.content_hash
FROM experiment_spec_versions v JOIN experiment_specs o ON o.id=v.experiment_spec_id
WHERE v.id=:id
"""
INSERT_COLUMNS = {
    "experiment_search_sessions": frozenset(get_type_hints(StoredSearchSession)),
    "experiment_search_nodes": frozenset(get_type_hints(StoredSearchNode)),
    "experiment_search_events": frozenset(get_type_hints(StoredSearchEvent)),
    "research_task_command_receipts": frozenset(get_type_hints(StoredSearchReceipt)),
    "research_task_events": frozenset(get_type_hints(StoredTaskEvent)),
    "research_task_receipt_events": frozenset({"receipt_id", "research_task_id", "event_id"}),
}


class SqlAlchemyExperimentSearchRepository:
    def __init__(self, session: Session):
        self._session = session
        self._tasks = SqlAlchemyTaskSafetyRepository(session)
        self._after_stage: FreshSearchValidation | None = None
        self._notifying = False
        self._started = False

    def _many(self, sql: str, params: Mapping[str, Any]) -> list[dict[str, Any]]:
        return [
            {
                key: to_utc(value) if isinstance(value, datetime) else value
                for key, value in row.items()
            }
            for row in self._session.execute(text(sql), params).mappings()
        ]

    def _notify(self, stage: SearchStorageStage) -> None:
        if self._after_stage is None or self._notifying:
            raise RuntimeError("search write requires a nonrecursive Application callback")
        self._notifying = True
        try:
            self._after_stage(stage)
        except BaseException:
            # A denied/replayed attempt cannot resume writes if its caller catches
            # the control signal. The owning UoW will roll the attempt back.
            self._after_stage = None
            raise
        finally:
            self._notifying = False

    def _writing(self) -> None:
        if self._after_stage is None or self._notifying:
            raise RuntimeError("search write requires the lock sequence and Application callback")

    def lock_write(
        self,
        project: UUID,
        actor: UUID,
        command: UUID,
        task: UUID,
        *,
        caller_kind: SearchCallerKind,
        after_stage: FreshSearchValidation,
        hypothesis_versions: tuple[UUID, ...] = (),
        experiment_spec_versions: tuple[UUID, ...] = (),
    ) -> StoredSearchWriteRows:
        """Use the authenticated caller kind supplied by Application, never a trust flag.

        Each step row is locked separately so a fresh check follows every possible
        row wait, rather than only the last wait of a multirow FOR UPDATE.
        """
        if self._started or self._notifying:
            raise RuntimeError("search lock sequence may run only once per UoW")
        if caller_kind not in ("HUMAN", "AGENT"):
            raise ValueError("unsupported caller kind")
        if not callable(after_stage):
            raise TypeError("Application validation callback required")
        if self._session.autoflush:
            raise RuntimeError("configure the command UoW before taking search locks")
        self._started = True
        self._after_stage = after_stage
        self._session.execute(text(SHARE_SQL))
        self._notify(SearchStorageStage("share"))
        self._session.execute(text("SELECT rb_phase2_lock_project(:id)"), {"id": project})
        self._notify(SearchStorageStage("project", "projects", project))
        keys = [
            ("command_key", f"pr301:command:{project}:{actor}:{command}"),
            ("task_key", f"pr301:task:{task}"),
        ]
        if caller_kind == "AGENT":
            keys.append(("actor_key", f"pr302:actor:{actor}"))
        for operation, key in keys:
            self._session.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"), {"key": key}
            )
            self._notify(SearchStorageStage(cast(Any, operation)))
        self._many("SELECT id FROM research_tasks WHERE id=:id FOR UPDATE", {"id": task})
        self._notify(SearchStorageStage("task_row", "research_tasks", task))
        step_ids = self._many(
            "SELECT id FROM research_task_steps WHERE research_task_id=:id ORDER BY id",
            {"id": task},
        )
        self._notify(SearchStorageStage("read", "research_task_steps"))
        for step in step_ids:
            self._many(
                "SELECT id FROM research_task_steps WHERE research_task_id=:task "
                "AND id=:id FOR UPDATE",
                {"task": task, "id": step["id"]},
            )
            self._notify(SearchStorageStage("step_row", "research_task_steps", step["id"]))
        self.edges(task)
        self._notify(SearchStorageStage("read", "research_task_step_dependencies"))
        self.inputs(task)
        self._notify(SearchStorageStage("read", "research_task_inputs"))
        self.inputs(task, step=True)
        self._notify(SearchStorageStage("read", "research_task_step_inputs"))
        for table in SAFETY_TABLES:
            self.rows(table, task)
            self._notify(SearchStorageStage("read", table))
        retained = {}
        for table in (
            "experiment_search_events",
            "experiment_search_nodes",
            "experiment_search_sessions",
        ):
            retained[table] = self._many(
                f"SELECT * FROM {table} WHERE research_task_id=:id ORDER BY id", {"id": task}
            )
            self._notify(SearchStorageStage("read", table))
        sessions = cast(list[StoredSearchSession], retained["experiment_search_sessions"])
        nodes = cast(list[StoredSearchNode], retained["experiment_search_nodes"])
        hypothesis_ids = set(hypothesis_versions)
        spec_ids = set(experiment_spec_versions)
        for session in sessions:
            if session["root_hypothesis_version_id"] is not None:
                hypothesis_ids.add(session["root_hypothesis_version_id"])
            if session["root_experiment_spec_version_id"] is not None:
                spec_ids.add(session["root_experiment_spec_version_id"])
        for node in nodes:
            if node["hypothesis_version_id"] is not None:
                hypothesis_ids.add(node["hypothesis_version_id"])
            if node["experiment_spec_version_id"] is not None:
                spec_ids.add(node["experiment_spec_version_id"])
        hypotheses, specs = [], []
        for identity in sorted(hypothesis_ids):
            ref = self.hypothesis_version(identity)
            self._notify(SearchStorageStage("read", "hypothesis_versions", identity))
            if ref is not None:
                hypotheses.append(ref)
        for identity in sorted(spec_ids):
            spec = self.experiment_spec_version(identity)
            self._notify(SearchStorageStage("read", "experiment_spec_versions", identity))
            if spec is not None:
                specs.append(spec)
        return StoredSearchWriteRows(
            tuple(cast(list[StoredSearchEvent], retained["experiment_search_events"])),
            tuple(nodes),
            tuple(sessions),
            tuple(hypotheses),
            tuple(specs),
        )

    def committed_receipt(self, project, actor, command) -> StoredSearchReceipt | None:
        rows = self._many(
            COMMITTED_RECEIPT_SQL,
            {
                "project": project,
                "actor": actor,
                "command": command,
            },
        )
        return cast(StoredSearchReceipt, rows[0]) if rows else None

    def sessions(self, project, task) -> list[StoredSearchSession]:
        return cast(
            list[StoredSearchSession],
            self._many(
                "SELECT * FROM experiment_search_sessions WHERE project_id=:project "
                "AND research_task_id=:task ORDER BY id",
                {"project": project, "task": task},
            ),
        )

    def nodes(self, task, session) -> list[StoredSearchNode]:
        return cast(
            list[StoredSearchNode],
            self._many(
                "SELECT * FROM experiment_search_nodes WHERE research_task_id=:task "
                "AND search_session_id=:session ORDER BY depth,id",
                {"task": task, "session": session},
            ),
        )

    def search_events(self, task, session) -> list[StoredSearchEvent]:
        return cast(
            list[StoredSearchEvent],
            self._many(
                "SELECT * FROM experiment_search_events WHERE research_task_id=:task "
                "AND search_session_id=:session ORDER BY sequence,id",
                {"task": task, "session": session},
            ),
        )

    def node_runs(self, project, task, session) -> list[StoredSearchNodeRun]:
        return cast(
            list[StoredSearchNodeRun],
            self._many(
                "SELECT * FROM experiment_search_node_runs WHERE project_id=:project "
                "AND research_task_id=:task AND search_session_id=:session ORDER BY id",
                {"project": project, "task": task, "session": session},
            ),
        )

    def run(self, project, identity) -> StoredSearchRun | None:
        rows = self._many(
            "SELECT id,project_id,experiment_spec_version_id,status,inputs_sealed_at,"
            "created_at,finished_at FROM runs WHERE project_id=:project AND id=:id",
            {"project": project, "id": identity},
        )
        return cast(StoredSearchRun, rows[0]) if rows else None

    def hypothesis_version(self, identity) -> StoredHypothesisReference | None:
        rows = self._many(HYPOTHESIS_SQL, {"id": identity})
        return cast(StoredHypothesisReference, rows[0]) if rows else None

    def experiment_spec_version(self, identity) -> StoredExperimentSpecReference | None:
        rows = self._many(EXPERIMENT_SPEC_SQL, {"id": identity})
        return cast(StoredExperimentSpecReference, rows[0]) if rows else None

    def task(self, identity):
        return self._tasks.task(identity)

    def steps(self, task):
        return self._tasks.steps(task)

    def edges(self, task):
        return self._tasks.edges(task)

    def inputs(self, task, *, step=False):
        return self._tasks.inputs(task, step=step)

    def events(self, task, *, step=False):
        return self._tasks.events(task, step=step)

    def rows(self, table, task):
        return self._tasks.rows(table, task)

    def scope_reference(self, kind, identity, project):
        return self._tasks.scope_reference(kind, identity, project)

    def receipt_history(self, task):
        return self._tasks.receipt_history(task)

    def authority(self, principal, project):
        return self._tasks.authority(principal, project)

    def project_active(self, project):
        return self._tasks.project_active(project)

    def at(self):
        return self._tasks.at()

    def snapshot_at(self):
        return self._tasks.snapshot_at()

    def insert(self, table: str, row: dict[str, Any]) -> None:
        allowed = INSERT_COLUMNS.get(table)
        if allowed is None or not row or not set(row) <= allowed:
            raise ValueError("unsupported search storage insert")
        self._writing()
        self._session.execute(
            text(
                f"INSERT INTO {table} ({','.join(row)}) VALUES ({','.join(':' + k for k in row)})"
            ),
            row,
        )
        self._notify(SearchStorageStage("insert", table, row.get("id")))

    def update_task(self, identity: UUID, expected_revision: int) -> None:
        self._writing()
        result = cast(
            CursorResult,
            self._session.execute(
                text(
                    "UPDATE research_tasks SET row_version=row_version+1 "
                    "WHERE id=:id AND row_version=:expected"
                ),
                {"id": identity, "expected": expected_revision},
            ),
        )
        if result.rowcount != 1:
            raise ResearchBaseError(ErrorCode.CONCURRENT_MODIFICATION, "task revision changed")
        self._notify(SearchStorageStage("update", "research_tasks", identity))

    def flush(self) -> None:
        self._writing()
        self._session.flush()
        self._notify(SearchStorageStage("flush"))

    def force_constraints(self) -> None:
        self._writing()
        self._session.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        self._notify(SearchStorageStage("constraints"))

    def before_commit(self) -> None:
        """Called by the owning UoW immediately before its single commit."""
        self.flush()
        self.force_constraints()
        self._notify(SearchStorageStage("final"))
