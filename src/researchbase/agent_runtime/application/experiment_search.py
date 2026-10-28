"""Bounded planning session creation through one Application transaction.

Composition supplies the existing trusted, bounded, no-I/O CredentialVerifier.
This service does not adapt disk/network credential providers or activate nodes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from inspect import iscoroutine, iscoroutinefunction
from typing import Any, cast

from researchbase.agent_runtime.application.research_task import TaskContextAdmission, fail
from researchbase.agent_runtime.application.search_contracts import (
    CreateSearchArguments,
    SearchCommand,
    SearchCommandResult,
)
from researchbase.agent_runtime.application.task_safety import (
    balances,
    causes,
    gates,
    verify_saved_policies,
)
from researchbase.agent_runtime.domain.experiment_search import ExactReference
from researchbase.agent_runtime.domain.research_task import invalid
from researchbase.agent_runtime.domain.task_safety import ADDITIVE
from researchbase.agent_runtime.ports.search_repository import (
    SearchCallerKind,
    SearchStorageStage,
    SearchUowFactory,
)
from researchbase.agent_runtime.ports.task_repository import UncertainTaskCommit
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.ids import new_uuid7

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
_FLAGS = (
    "stop_human",
    "stop_policy",
    "stop_budget",
    "stop_repeated_failure",
    "stop_no_improvement",
    "stop_success",
)
_REASON = "Search session created."
_MESSAGES = {
    ErrorCode.VALIDATION_ERROR: "Search request invalid.",
    ErrorCode.AUTHENTICATION_REQUIRED: "Authentication required.",
    ErrorCode.FORBIDDEN: "Search access denied.",
    ErrorCode.NOT_FOUND: "Search target not found.",
    ErrorCode.IDEMPOTENCY_CONFLICT: "Search command conflicts.",
    ErrorCode.CONCURRENT_MODIFICATION: "Task revision changed.",
    ErrorCode.INVALID_STATE_TRANSITION: "Search state unavailable.",
    ErrorCode.REFERENTIAL_INTEGRITY_ERROR: "Search reference invalid.",
    ErrorCode.FROZEN_REFERENCE_REQUIRED: "Frozen reference required.",
    ErrorCode.VERSION_NOT_FROZEN: "Search version not frozen.",
    ErrorCode.PROVENANCE_CLOSURE_VIOLATION: "Search provenance invalid.",
    ErrorCode.IMMUTABLE_RECORD: "Search history is immutable.",
}


class _Credentials:
    """Fail closed for unsupported results; trust/no-I/O is a composition contract."""

    def __init__(self, verifier):
        self.verifier = verifier

    def is_valid(self, principal, at):
        method = getattr(self.verifier, "is_valid", None)
        if not callable(method) or iscoroutinefunction(method):
            return False
        result = method(principal, at)
        if iscoroutine(result):
            result.close()
        return type(result) is bool and result


class _SavedReplay(Exception):
    def __init__(self, result: SearchCommandResult):
        self.result = result


@dataclass
class _Progress:
    """Completed own effects, advanced by storage notification before validation."""

    task_updated: bool = False
    inserted: set[str] = field(default_factory=set)
    planned: dict[str, dict[str, Any]] = field(default_factory=dict)

    def observe(self, stage: SearchStorageStage):
        if stage.operation == "update":
            if self.task_updated or stage.table != "research_tasks":
                raise RuntimeError("unexpected search update")
            self.task_updated = True
        elif stage.operation == "insert":
            row = self.planned.get(stage.table or "")
            if row is None or stage.table in self.inserted or row.get("id") != stage.identity:
                raise RuntimeError("unexpected search insert")
            self.inserted.add(cast(str, stage.table))


class ExperimentSearchService(TaskContextAdmission):
    def __init__(self, factory: SearchUowFactory, credentials=None):
        super().__init__(_Credentials(credentials))
        self._factory = factory

    def create_search_session(self, principal, command: SearchCommand) -> SearchCommandResult:
        try:
            return self._create(principal, command)
        except ResearchBaseError as exc:
            raise ResearchBaseError(exc.code, _MESSAGES[exc.code]) from None

    def _create(self, principal, command: SearchCommand) -> SearchCommandResult:
        self._command(principal, command, "create_search_session")
        # Generated identities remain stable through all bounded transient attempts.
        ids = tuple(new_uuid7() for _ in range(3))
        for attempt in range(3):
            try:
                return self._create_once(principal, command, ids)
            except _SavedReplay as saved:
                return saved.result
            except UncertainTaskCommit:
                saved = self.replay(principal, command)
                if saved is not None:
                    return saved
                raise
            except ResearchBaseError as exc:
                if attempt == 2 or not (exc.details or {}).get("retryable_pr301"):
                    raise
        raise AssertionError("unreachable")

    def append_search_node(self, principal, command: SearchCommand):
        try:
            self._command(principal, command, "append_search_node")
        except ResearchBaseError as exc:
            raise ResearchBaseError(exc.code, _MESSAGES[exc.code]) from None
        # No UoW, producer, evaluator, reservation or protected effect is admitted.
        fail(ErrorCode.INVALID_STATE_TRANSITION, "Search state unavailable.")

    def execute(self, principal, command: SearchCommand):
        if not isinstance(command, SearchCommand):
            invalid("typed search command required")
        if command.command_name == "create_search_session":
            return self.create_search_session(principal, command)
        return self.append_search_node(principal, command)

    def _command(self, principal, command, name):
        self._principal(principal)
        if not isinstance(command, SearchCommand) or command.command_name != name:
            invalid("matching typed search command required")

    @staticmethod
    def _saved(uow, receipt, command, digest):
        if receipt is None:
            return None
        if receipt["request_hash"] != digest:
            fail(ErrorCode.IDEMPOTENCY_CONFLICT, "command material differs from saved request")
        if (
            receipt["command_name"] != command.command_name
            or receipt["research_task_id"] != command.task_id
            or receipt["result_search_session_id"] != command.arguments.session_id
            or receipt["result_search_node_id"] is not None
            or receipt["result_search_event_id"] is None
        ):
            fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved search result contradiction")
        return SearchCommandResult(
            uow.research_tasks.result(receipt, replayed=True),
            receipt["result_search_session_id"],
            None,
            receipt["result_search_event_id"],
        )

    def replay(self, principal, command: SearchCommand) -> SearchCommandResult | None:
        """Uncertain-commit reconciliation only; no fresh mutation or CAS."""
        self._command(principal, command, "create_search_session")
        with self._factory() as uow:
            uow.begin_formal_read()
            repo = uow.experiment_search
            self._authorize(repo, principal, command.project_id)
            receipt = repo.committed_receipt(
                command.project_id, principal.actor_id, command.command_id
            )
            return self._saved(uow, receipt, command, command.request_hash(principal.actor_id))

    @staticmethod
    def _reference(uow, project, identity, *, hypothesis):
        if identity is None:
            return None
        repo = uow.experiment_search
        row = (
            repo.hypothesis_version(identity)
            if hypothesis
            else repo.experiment_spec_version(identity)
        )
        if row is None:
            fail(ErrorCode.NOT_FOUND, "exact search reference unavailable")
        if row["project_id"] != project:
            fail(ErrorCode.FORBIDDEN, "search reference scope unavailable")
        if (
            row["status"] not in {"FROZEN", "SUPERSEDED"}
            or row["frozen_at"] is None
            or row["content_hash"] is None
        ):
            fail(ErrorCode.VERSION_NOT_FROZEN, "historically frozen search reference required")
        try:
            # Owning constructors verify canonical material, without Artifact I/O.
            owner = uow.hypotheses if hypothesis else uow.experiment_specs
            version = owner.get_version(identity)
            if version is None or version.content_hash != row["content_hash"]:
                raise ValueError("owning hash mismatch")
            ExactReference(identity, row["content_hash"])
        except (ValueError, TypeError, KeyError):
            fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "owning search hash contradiction")
        return row["content_hash"]

    @staticmethod
    def _admission(repo, task, at):
        rows = {table: repo.rows(table, task["id"]) for table in SAFETY_TABLES}
        verify_saved_policies(repo, task["project_id"], rows)
        bundle = [
            next((r for r in rows[table] if r["id"] == task[key]), None)
            for table, key in (
                ("execution_budgets", "budget_policy_id"),
                ("termination_policies", "termination_policy_id"),
                ("checkpoint_policies", "checkpoint_policy_id"),
            )
        ]
        if any(row is None for row in bundle):
            fail(ErrorCode.INVALID_STATE_TRANSITION, "complete search policy bundle required")
        budget, term, policy = (cast(dict[str, Any], row) for row in bundle)
        if task["autonomy_level"] > policy["maximum_autonomy"]:
            fail(ErrorCode.INVALID_STATE_TRANSITION, "search autonomy exceeds policy")
        reservations, usage = rows["budget_reservations"], rows["budget_usage_records"]
        flags = causes(budget, term, reservations, usage, at)
        consumed, reserved = balances(reservations, usage)
        if (
            any(flags.values())
            or any(any(e.get(k, False) for k in _FLAGS) for e in repo.events(task["id"]))
            or any(consumed[k] + reserved[k] > budget["max_" + k] for k in ADDITIVE)
        ):
            fail(ErrorCode.INVALID_STATE_TRANSITION, "task stopped")
        if any(not gate.satisfied for gate in gates(policy, rows["human_checkpoints"], at)):
            fail(ErrorCode.INVALID_STATE_TRANSITION, "checkpoint required")
        return budget["id"]

    def _create_once(self, principal, command, ids):
        args = command.arguments
        assert isinstance(args, CreateSearchArguments)
        digest = command.request_hash(principal.actor_id)
        receipt_id, search_event_id, task_event_id = ids
        progress = _Progress()
        caller_kind: SearchCallerKind | None = None
        pinned_task = None
        pinned_hashes = None
        with self._factory() as uow:
            uow.begin_experiment_search()
            repo = uow.experiment_search

            def validate(stage):
                nonlocal caller_kind, pinned_task, pinned_hashes
                progress.observe(stage)
                # This order applies even while our own effect set is incomplete.
                self._authorize(repo, principal, command.project_id)
                receipt = repo.committed_receipt(
                    command.project_id, principal.actor_id, command.command_id
                )
                saved = self._saved(uow, receipt, command, digest)
                if saved is not None:
                    raise _SavedReplay(saved)
                at = self._authorize(repo, principal, command.project_id, write=True)
                kinds = {r["actor_type"] for r in repo.authority(principal, command.project_id)}
                if len(kinds) != 1 or not kinds <= {"HUMAN", "AGENT"}:
                    fail(ErrorCode.FORBIDDEN, "supported verified caller required")
                kind = cast(SearchCallerKind, next(iter(kinds)))
                if caller_kind is not None and caller_kind != kind:
                    fail(ErrorCode.FORBIDDEN, "caller kind changed")
                caller_kind = kind
                task = repo.task(command.task_id)
                if task is None:
                    fail(ErrorCode.NOT_FOUND, "task not found")
                if task["project_id"] != command.project_id:
                    fail(ErrorCode.FORBIDDEN, "task scope unavailable")
                expected = command.expected_row_version + int(progress.task_updated)
                if task["row_version"] != expected:
                    fail(ErrorCode.CONCURRENT_MODIFICATION, "stale task revision")
                if task["status"] not in {"CREATED", "PLANNING"}:
                    fail(ErrorCode.INVALID_STATE_TRANSITION, "nonterminal search task required")
                material = {k: v for k, v in task.items() if k != "row_version"}
                if pinned_task is not None and material != pinned_task:
                    fail(ErrorCode.CONCURRENT_MODIFICATION, "task binding changed")
                pinned_task = material
                self._admission(repo, task, at)
                hashes = (
                    self._reference(
                        uow, command.project_id, args.root_hypothesis_version_id, hypothesis=True
                    ),
                    self._reference(
                        uow,
                        command.project_id,
                        args.root_experiment_spec_version_id,
                        hypothesis=False,
                    ),
                )
                if pinned_hashes is not None and pinned_hashes != hashes:
                    fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "search reference hash changed")
                pinned_hashes = hashes
                self._own_effects(uow, command, progress, receipt_id, principal.actor_id)

            def kind_source() -> SearchCallerKind:
                assert caller_kind is not None
                return caller_kind

            repo.lock_write(
                command.project_id,
                principal.actor_id,
                command.command_id,
                command.task_id,
                caller_kind=kind_source,
                after_stage=validate,
                hypothesis_versions=(args.root_hypothesis_version_id,)
                if args.root_hypothesis_version_id is not None
                else (),
                experiment_spec_versions=(args.root_experiment_spec_version_id,)
                if args.root_experiment_spec_version_id is not None
                else (),
            )
            assert pinned_task is not None and pinned_hashes is not None
            at = repo.snapshot_at()  # DDL0082 uses transaction_timestamp(), not clock time.
            revision = command.expected_row_version + 1
            receipt = dict(
                id=receipt_id,
                project_id=command.project_id,
                actor_id=principal.actor_id,
                command_id=command.command_id,
                command_name=command.command_name,
                research_task_id=command.task_id,
                request_hash=digest,
                hash_scheme="sha256-cjson-v1",
                material_version=1,
                resulting_row_version=revision,
                completed_at=at,
                result_search_session_id=args.session_id,
                result_search_node_id=None,
                result_search_event_id=search_event_id,
            )
            progress.planned = {
                "research_task_command_receipts": receipt,
                "experiment_search_sessions": dict(
                    id=args.session_id,
                    project_id=command.project_id,
                    research_task_id=command.task_id,
                    budget_id=pinned_task["budget_policy_id"],
                    root_hypothesis_version_id=args.root_hypothesis_version_id,
                    root_hypothesis_content_hash=pinned_hashes[0],
                    root_experiment_spec_version_id=args.root_experiment_spec_version_id,
                    root_experiment_spec_content_hash=pinned_hashes[1],
                    created_by=principal.actor_id,
                    created_at=at,
                    receipt_id=receipt_id,
                ),
                "experiment_search_events": dict(
                    id=search_event_id,
                    research_task_id=command.task_id,
                    search_session_id=args.session_id,
                    node_id=None,
                    sequence=1,
                    event_type="SESSION_CREATED",
                    reason=_REASON,
                    actor_id=principal.actor_id,
                    occurred_at=at,
                    receipt_id=receipt_id,
                ),
                "research_task_events": dict(
                    id=task_event_id,
                    research_task_id=command.task_id,
                    actor_id=principal.actor_id,
                    command_id=command.command_id,
                    event_type="SEARCH_SESSION_CREATED",
                    sequence=revision,
                    task_row_version=revision,
                    prior_status=pinned_task["status"],
                    new_status=pinned_task["status"],
                    reason=_REASON,
                    occurred_at=at,
                    **dict.fromkeys(_FLAGS, False),
                ),
                "research_task_receipt_events": dict(
                    receipt_id=receipt_id, research_task_id=command.task_id, event_id=task_event_id
                ),
            }
            validate(SearchStorageStage("read"))
            repo.update_task(command.task_id, command.expected_row_version)
            for table, row in progress.planned.items():
                repo.insert(table, row)
            repo.flush()
            repo.force_constraints()
            result = SearchCommandResult(
                uow.research_tasks.result(receipt, replayed=False),
                args.session_id,
                None,
                search_event_id,
            )
            # The accepted UoW repeats flush/constraints/final validation immediately
            # before its single commit, still inside this rollback-owning context.
            uow.commit()
            return result

    @staticmethod
    def _own_effects(uow, command, progress, receipt_id, actor_id):
        repo = uow.experiment_search
        session = command.arguments.session_id
        rows = {
            "experiment_search_sessions": [
                r for r in repo.sessions(command.project_id, command.task_id) if r["id"] == session
            ],
            "experiment_search_events": repo.search_events(command.task_id, session),
            "research_task_events": [
                r
                for r in repo.events(command.task_id)
                if r["command_id"] == command.command_id and r["actor_id"] == actor_id
            ],
        }
        for table, observed in rows.items():
            wanted = [progress.planned[table]] if table in progress.inserted else []
            if table == "experiment_search_sessions" and observed and not wanted:
                fail(ErrorCode.VALIDATION_ERROR, "search session identity occupied")
            if len(observed) != len(wanted) or any(
                any(row.get(k) != v for k, v in expected.items())
                for row, expected in zip(observed, wanted, strict=True)
            ):
                fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "search effect set contradiction")
        if repo.nodes(command.task_id, session):
            fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "unexpected node effects")
        own_receipts = [r for r in repo.receipt_history(command.task_id) if r["id"] == receipt_id]
        if len(own_receipts) != int("research_task_command_receipts" in progress.inserted):
            fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "search receipt progress contradiction")
        if "research_task_receipt_events" in progress.inserted:
            result = uow.research_tasks.result(
                progress.planned["research_task_command_receipts"], replayed=False
            )
            if result.task_event_ids != (progress.planned["research_task_events"]["id"],) or (
                result.step_event_ids != ()
            ):
                fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "search receipt effects contradiction")
