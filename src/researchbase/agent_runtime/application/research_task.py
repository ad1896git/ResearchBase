"""Synchronous planning commands; Human and Agent callers share this boundary."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, NoReturn

from researchbase.agent_runtime.application.contracts import (
    AddStepArguments,
    CancelArguments,
    CommandResult,
    CreatePlanArguments,
    CreateTaskArguments,
    InputRead,
    InputType,
    PlanEdge,
    PlanNode,
    ProgressCounts,
    StepEventRead,
    StepRead,
    TaskCommand,
    TaskEventRead,
    TaskGraphRead,
    TaskInput,
    TaskProgressRead,
    TaskRead,
)
from researchbase.agent_runtime.domain.research_task import (
    COMMAND_EVENTS,
    EXECUTION_COMMANDS,
    invalid,
    require_transition,
)
from researchbase.agent_runtime.domain.task_graph import validate_graph
from researchbase.agent_runtime.ports.task_repository import TaskUowFactory, UncertainTaskCommit
from researchbase.application.manuscript_freeze import ManuscriptFreezeService
from researchbase.application.saved_provenance import saved_seal
from researchbase.application.source_version import _material_from_row
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.ids import new_uuid7

_READERS = frozenset({"OWNER", "RESEARCHER", "REVIEWER", "APPROVER", "VIEWER"})
_WRITERS = frozenset({"OWNER", "RESEARCHER"})
_INPUT_COLUMNS = {
    "RESEARCH_QUESTION_VERSION": "research_question_version_id",
    "HYPOTHESIS_VERSION": "hypothesis_version_id",
    "CLAIM_VERSION": "claim_version_id",
    "SOURCE_VERSION": "source_version_id",
    "ARTIFACT_VERSION": "artifact_version_id",
    "MANUSCRIPT_VERSION": "manuscript_version_id",
}


def fail(code, message) -> NoReturn:
    raise ResearchBaseError(code, message)


class ResearchTaskService:
    def __init__(self, factory: TaskUowFactory, credentials: Any, artifact_store: Any = None):
        self._factory = factory
        self._credentials = credentials
        self._verifier = ManuscriptFreezeService(factory, credentials, artifact_store)  # type: ignore[arg-type]

    @staticmethod
    def _principal(principal):
        if not isinstance(principal, VerifiedPrincipal):
            fail(ErrorCode.AUTHENTICATION_REQUIRED, "trusted verified principal required")

    def _authorize(self, repo, principal, project, *, write=False):
        rows = repo.authority(principal, project)
        active = repo.project_active(project)
        at = repo.at()  # Advancing database time after the final blocking wait.
        try:
            live = principal.verified_at <= at and self._credentials.is_valid(principal, at)
        except Exception:
            live = False
        roles = _WRITERS if write else _READERS
        if live and (not write or active):
            for row in rows:
                if (
                    row["retired_at"] is None
                    and row["binding_status"] == "ACTIVE"
                    and row["membership_status"] == "ACTIVE"
                    and row["role"] in roles
                    and row["effective_from"] <= at
                    and (row["effective_until"] is None or at < row["effective_until"])
                    and row["bound_at"] <= at
                    and (row["revoked_at"] is None or at < row["revoked_at"])
                ):
                    return at
        fail(ErrorCode.FORBIDDEN, "current project entitlement unavailable")

    @staticmethod
    def _scoped(repo, project, identity):
        row = repo.task(identity)
        if row is None:
            fail(ErrorCode.NOT_FOUND, "task not found")
        if row["project_id"] != project:
            fail(ErrorCode.FORBIDDEN, "task scope unavailable")
        return row

    def _resolve(self, uow: Any, project, ref: TaskInput, saved=None):
        row = uow.research_tasks.input_version(ref.type, ref.id, project)
        if row is None:
            fail(ErrorCode.NOT_FOUND, "exact input version unavailable")
        if not row["scoped"]:
            fail(ErrorCode.FORBIDDEN, "input scope unavailable")
        if (
            row["status"] not in {"FROZEN", "SUPERSEDED"}
            or row["frozen_at"] is None
            or row["content_hash"] is None
        ):
            fail(ErrorCode.VERSION_NOT_FROZEN, "historically frozen input required")
        scheme = (
            row.get("hash_scheme") if ref.type in {"SOURCE_VERSION", "MANUSCRIPT_VERSION"} else None
        )
        if scheme not in (
            {"sha256-cjson-v1"} if ref.type in {"SOURCE_VERSION", "MANUSCRIPT_VERSION"} else {None}
        ):
            fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "owning hash scheme contradiction")
        warnings = ()
        try:
            # Frozen inputs are retained canonical history. Verify owning material
            # and snapshot validity without ArtifactStore/network I/O under locks.
            with saved_seal():
                if ref.type in {"RESEARCH_QUESTION_VERSION", "HYPOTHESIS_VERSION", "CLAIM_VERSION"}:
                    owner = {
                        "RESEARCH_QUESTION_VERSION": uow.research_questions,
                        "HYPOTHESIS_VERSION": uow.hypotheses,
                        "CLAIM_VERSION": uow.claims,
                    }[ref.type]
                    version = owner.get_version(ref.id)
                    if version is None or version.content_hash != row["content_hash"]:
                        raise ValueError("owning hash mismatch")
                    if ref.type == "CLAIM_VERSION":
                        _, state = self._verifier._claim(uow, project, ref.id)
                        warnings = () if state == "VALID" else (state,)
                elif ref.type == "SOURCE_VERSION":
                    material = _material_from_row(uow.source_version, row)
                    if material.digest() != row["content_hash"]:
                        raise ValueError("source hash mismatch")
                    warnings = ("SOURCE_RETRACTED",) if row["version_kind"] == "RETRACTED" else ()
                elif ref.type == "ARTIFACT_VERSION":
                    _, state = self._verifier._artifact(uow, project, ref.id)
                    warnings = () if state == "VALID" else (state,)
                else:
                    parent = uow.publication.publication(row["publication_id"], project)
                    view = self._verifier.verify_in_uow(
                        uow, project, parent, row, require_current=False
                    )
                    warnings = () if view.current_validity == "VALID" else (view.current_validity,)
        except (ValueError, TypeError, KeyError):
            fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "owning input material contradiction")
        if saved is not None and (
            saved["content_hash"] != row["content_hash"] or saved["hash_scheme"] != scheme
        ):
            fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved exact input contradiction")
        return InputRead(ref.type, ref.id, row["content_hash"], scheme, warnings)

    @staticmethod
    def _reference(row):
        bindings = [
            (kind, row[col]) for kind, col in _INPUT_COLUMNS.items() if row[col] is not None
        ]
        if len(bindings) != 1:
            fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved typed input contradiction")
        return TaskInput(InputType(bindings[0][0]), bindings[0][1])

    def _saved_inputs(self, uow, project, rows):
        return tuple(
            sorted(
                (self._resolve(uow, project, self._reference(row), row) for row in rows),
                key=lambda r: (r.type, str(r.id)),
            )
        )

    def _insert_inputs(self, repo, task, bindings, step=None):
        for ref in bindings:
            row = {
                "id": new_uuid7(),
                "research_task_id": task,
                **dict.fromkeys(_INPUT_COLUMNS.values()),
                _INPUT_COLUMNS[ref.type]: ref.id,
                "content_hash": ref.content_hash,
                "hash_scheme": ref.hash_scheme,
            }
            if step is not None:
                row["step_id"] = step
            repo.insert(
                "research_task_step_inputs" if step is not None else "research_task_inputs", row
            )

    def execute(self, principal: VerifiedPrincipal, command: TaskCommand) -> CommandResult:
        self._principal(principal)
        for attempt in range(3):
            try:
                return self._execute_once(principal, command)
            except UncertainTaskCommit:
                saved = self.replay(principal, command)
                if saved is not None:
                    return saved
                raise
            except ResearchBaseError as exc:
                if not exc.details or not exc.details.get("retryable_pr301") or attempt == 2:
                    raise
        raise AssertionError("unreachable")

    def _execute_once(self, principal, command):
        digest = command.request_hash(principal.actor_id)
        with self._factory() as uow:
            uow.begin_research_task()
            repo = uow.research_tasks
            repo.lock_write(
                command.project_id, principal.actor_id, command.command_id, command.task_id
            )
            self._authorize(repo, principal, command.project_id)
            # Reserved execution has a stable denial even when planning is sealed/terminal.
            if command.command_name in EXECUTION_COMMANDS:
                self._scoped(repo, command.project_id, command.task_id)
                require_transition(command.command_name, "CREATED", False)
            receipt = repo.receipt(command.project_id, principal.actor_id, command.command_id)
            if receipt is not None:
                if receipt["request_hash"] != digest:
                    fail(
                        ErrorCode.IDEMPOTENCY_CONFLICT,
                        "command material differs from saved request",
                    )
                return repo.result(receipt, replayed=True)
            task = repo.task(command.task_id)
            if task is not None and task["project_id"] != command.project_id:
                fail(ErrorCode.FORBIDDEN, "task scope unavailable")
            at = self._authorize(repo, principal, command.project_id, write=True)
            name = command.command_name
            args = command.arguments
            steps = repo.steps(command.task_id) if task else []
            edges = tuple(PlanEdge(**r) for r in repo.edges(command.task_id)) if task else ()
            old_nodes = tuple(
                PlanNode(
                    r["id"],
                    r["step_type"],
                    r["ordinal"],
                    r["parent_step_id"],
                    r["agent_role"],
                    r["capability_id"],
                )
                for r in steps
            )
            new_nodes = ()
            new_edges = ()
            task_inputs = ()
            if name == "create_research_task":
                if task is not None:
                    fail(ErrorCode.CONCURRENT_MODIFICATION, "task identity occupied")
                assert isinstance(args, CreateTaskArguments)
                task_inputs = tuple(
                    self._resolve(uow, command.project_id, ref) for ref in args.inputs
                )
                revision = 1
                prior = None
                status = "CREATED"
            else:
                if task is None:
                    fail(ErrorCode.NOT_FOUND, "task not found")
                if command.expected_row_version != task["row_version"]:
                    fail(ErrorCode.CONCURRENT_MODIFICATION, "stale task revision")
                require_transition(name, task["status"], task["plan_sealed_at"] is not None)
                revision = task["row_version"] + 1
                prior = task["status"]
                status = "CANCELLED" if name == "cancel_research_task" else "PLANNING"
                if isinstance(args, CreatePlanArguments):
                    new_nodes = args.nodes
                    new_edges = args.edges
                elif isinstance(args, AddStepArguments):
                    if args.node.parent_step_id is not None and args.node.parent_step_id not in {
                        n.step_id for n in old_nodes
                    }:
                        invalid("add-step parent must already exist")
                    if any(
                        identity not in {n.step_id for n in old_nodes}
                        for identity in args.predecessor_ids
                    ):
                        invalid("add-step predecessors must already exist")
                    new_nodes = (args.node,)
                    new_edges = tuple(
                        PlanEdge(identity, args.node.step_id) for identity in args.predecessor_ids
                    )
                elif isinstance(args, PlanEdge):
                    new_edges = (args,)
            existing_inputs = (
                repo.inputs(command.task_id) + repo.inputs(command.task_id, step=True)
                if task
                else []
            )
            validate_graph(
                old_nodes + new_nodes,
                edges + new_edges,
                len(existing_inputs) + len(task_inputs) + sum(len(n.inputs) for n in new_nodes),
            )
            resolved = {
                node.step_id: tuple(
                    self._resolve(uow, command.project_id, ref) for ref in node.inputs
                )
                for node in new_nodes
            }
            if name == "seal_task_plan":
                self._saved_inputs(uow, command.project_id, existing_inputs)
            # No blocking operation follows authorization; all protected writes begin here.
            if name == "create_research_task":
                assert isinstance(args, CreateTaskArguments)
                row = {
                    "id": command.task_id,
                    "project_id": command.project_id,
                    "requested_by": principal.actor_id,
                    **{key: value for key, value in asdict(args).items() if key != "inputs"},
                    "status": status,
                    "created_at": at,
                    "started_at": None,
                    "finished_at": None,
                    "plan_sealed_at": None,
                    "current_step_id": None,
                    "row_version": revision,
                }
                repo.insert("research_tasks", row)
                self._insert_inputs(repo, command.task_id, task_inputs)
            else:
                values = {"status": status, "row_version": revision}
                if name == "seal_task_plan":
                    values["plan_sealed_at"] = at
                if name == "cancel_research_task":
                    values["finished_at"] = at
                repo.update_task(command.task_id, values)
            for node in new_nodes:
                repo.insert(
                    "research_task_steps",
                    {
                        "id": node.step_id,
                        "research_task_id": command.task_id,
                        "step_type": node.step_type,
                        "ordinal": node.ordinal,
                        "parent_step_id": node.parent_step_id,
                        "agent_role": node.agent_role,
                        "capability_id": node.capability_id,
                        "status": "PENDING",
                        "started_at": None,
                        "finished_at": None,
                        "retry_count": 0,
                        "failure_code": None,
                        "row_version": 1,
                    },
                )
            for node in new_nodes:
                self._insert_inputs(repo, command.task_id, resolved[node.step_id], node.step_id)
            for edge in new_edges:
                repo.insert(
                    "research_task_step_dependencies",
                    {"research_task_id": command.task_id, **asdict(edge)},
                )
            if name == "cancel_research_task":
                repo.cancel_steps(command.task_id, at)
            receipt = {
                "id": new_uuid7(),
                "project_id": command.project_id,
                "actor_id": principal.actor_id,
                "command_id": command.command_id,
                "command_name": name,
                "research_task_id": command.task_id,
                "request_hash": digest,
                "hash_scheme": "sha256-cjson-v1",
                "material_version": 1,
                "resulting_row_version": revision,
                "completed_at": at,
            }
            repo.insert("research_task_command_receipts", receipt)
            reason = args.reason if isinstance(args, CancelArguments) else None
            event = {
                "id": new_uuid7(),
                "research_task_id": command.task_id,
                "actor_id": principal.actor_id,
                "command_id": command.command_id,
                "event_type": COMMAND_EVENTS[name],
                "sequence": revision,
                "task_row_version": revision,
                "prior_status": prior,
                "new_status": status,
                "reason": reason,
                "occurred_at": at,
            }
            repo.insert("research_task_events", event)
            child_events = []
            for child in (
                steps if name == "cancel_research_task" else [asdict(n) for n in new_nodes]
            ):
                cancel = name == "cancel_research_task"
                child_events.append(
                    {
                        **event,
                        "id": new_uuid7(),
                        "step_id": child["id"] if cancel else child["step_id"],
                        "event_type": "CANCELLED" if cancel else "PLANNED",
                        "sequence": 2 if cancel else 1,
                        "step_row_version": 2 if cancel else 1,
                        "prior_status": "PENDING" if cancel else None,
                        "new_status": "CANCELLED" if cancel else "PENDING",
                    }
                )
            for child_event in child_events:
                repo.insert("research_task_step_events", child_event)
            repo.insert(
                "research_task_receipt_events",
                {
                    "receipt_id": receipt["id"],
                    "research_task_id": command.task_id,
                    "event_id": event["id"],
                },
            )
            for child_event in child_events:
                repo.insert(
                    "research_task_receipt_step_events",
                    {
                        "receipt_id": receipt["id"],
                        "research_task_id": command.task_id,
                        "step_event_id": child_event["id"],
                    },
                )
            repo.force_constraints()
            result = repo.result(receipt, replayed=False)
            uow.commit()
            return result

    def _graph(self, uow, project, task):
        repo = uow.research_tasks
        row = self._scoped(repo, project, task)
        task_read = TaskRead(**row, inputs=self._saved_inputs(uow, project, repo.inputs(task)))
        inputs = repo.inputs(task, step=True)
        nodes = tuple(
            StepRead(
                **r,
                inputs=self._saved_inputs(
                    uow, project, [b for b in inputs if b["step_id"] == r["id"]]
                ),
            )
            for r in repo.steps(task)
        )
        return TaskGraphRead(
            task_read,
            nodes,
            tuple(PlanEdge(**r) for r in repo.edges(task)),
            tuple(TaskEventRead(**r) for r in repo.events(task)),
            tuple(StepEventRead(**r) for r in repo.events(task, step=True)),
        )

    def get_task_graph(self, principal, project_id, task_id) -> TaskGraphRead:
        self._principal(principal)
        with self._factory() as uow:
            uow.begin_formal_read()
            self._authorize(uow.research_tasks, principal, project_id)
            return self._graph(uow, project_id, task_id)

    def get_research_task(self, principal, project_id, task_id) -> TaskRead:
        return self.get_task_graph(principal, project_id, task_id).task

    def get_task_progress(self, principal, project_id, task_id) -> TaskProgressRead:
        graph = self.get_task_graph(principal, project_id, task_id)
        return TaskProgressRead(
            graph.task.id,
            graph.task.row_version,
            graph.task.status,
            len(graph.nodes),
            ProgressCounts(
                PENDING=sum(n.status == "PENDING" for n in graph.nodes),
                CANCELLED=sum(n.status == "CANCELLED" for n in graph.nodes),
            ),
        )

    def replay(self, principal, command: TaskCommand) -> CommandResult | None:
        """Explicit receipt reconciliation after an uncertain commit; never writes."""
        self._principal(principal)
        with self._factory() as uow:
            uow.begin_formal_read()
            repo = uow.research_tasks
            self._authorize(repo, principal, command.project_id)
            receipt = repo.receipt(command.project_id, principal.actor_id, command.command_id)
            if receipt is None:
                return None
            if receipt["request_hash"] != command.request_hash(principal.actor_id):
                fail(ErrorCode.IDEMPOTENCY_CONFLICT, "command material differs from saved request")
            return repo.result(receipt, replayed=True)

    def _named(self, name, principal, command):
        if command.command_name != name:
            invalid("command name does not match the requested operation")
        return self.execute(principal, command)

    def create_research_task(self, principal, command):
        return self._named("create_research_task", principal, command)

    def create_task_plan(self, principal, command):
        return self._named("create_task_plan", principal, command)

    def add_task_step(self, principal, command):
        return self._named("add_task_step", principal, command)

    def add_task_step_dependency(self, principal, command):
        return self._named("add_task_step_dependency", principal, command)

    def seal_task_plan(self, principal, command):
        return self._named("seal_task_plan", principal, command)

    def cancel_research_task(self, principal, command):
        return self._named("cancel_research_task", principal, command)

    def start_research_task(self, principal, command):
        return self._named("start_research_task", principal, command)

    def pause_research_task(self, principal, command):
        return self._named("pause_research_task", principal, command)

    def resume_research_task(self, principal, command):
        return self._named("resume_research_task", principal, command)

    def start_task_step(self, principal, command):
        return self._named("start_task_step", principal, command)

    def finish_task_step(self, principal, command):
        return self._named("finish_task_step", principal, command)

    def fail_task_step(self, principal, command):
        return self._named("fail_task_step", principal, command)
