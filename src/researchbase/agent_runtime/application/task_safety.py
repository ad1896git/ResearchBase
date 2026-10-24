"""Atomic safety bookkeeping. Resource admission is confined to a trusted local fake."""

from __future__ import annotations

from dataclasses import asdict, fields
from datetime import timedelta
from decimal import Decimal
from typing import Any, cast

from researchbase.agent_runtime.application.research_task import ResearchTaskService, fail
from researchbase.agent_runtime.application.safety_contracts import (
    EVENTS,
    BindPoliciesArguments,
    BudgetSpec,
    EvaluateTerminationArguments,
    RequestCheckpointArguments,
    ReserveBudgetArguments,
    RespondCheckpointArguments,
    SafetyCommand,
    SettleBudgetArguments,
    TerminationSpec,
    material_value,
    policy_hash,
)
from researchbase.agent_runtime.domain.research_task import invalid
from researchbase.agent_runtime.domain.task_safety import (
    ADDITIVE,
    ResourceVector,
    settlement,
    streaks,
)
from researchbase.agent_runtime.ports.task_repository import UncertainTaskCommit
from researchbase.agent_runtime.ports.task_safety_repository import FakeConsumerCapability
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.ids import new_uuid7


def spec(kind, row):
    return kind(**{f.name: row[f.name] for f in fields(kind)})


def balances(reservations, usage) -> tuple[dict[str, Any], dict[str, Any]]:
    final = {u["reservation_id"]: u for u in usage if u["is_final"]}
    consumed = {k: 0 for k in ADDITIVE}
    reserved = {k: 0 for k in ADDITIVE}
    for r in reservations:
        target = consumed if r["id"] in final else reserved
        source = final.get(r["id"], r)
        for k in ADDITIVE:
            target[k] += source[k]
    return consumed, reserved


def causes(budget, term, reservations, usage, at, *, human=False, policy=False):
    consumed, reserved = balances(reservations, usage)
    budget_stop = False
    if budget:
        budget_stop = any(
            budget["max_" + k] > 0 and consumed[k] + reserved[k] >= budget["max_" + k]
            for k in ADDITIVE
        )
        if reservations:
            budget_stop |= at >= min(r["created_at"] for r in reservations) + timedelta(
                seconds=budget["max_wall_time_seconds"]
            )
    return dict(
        stop_human=human,
        stop_policy=policy,
        stop_budget=budget_stop,
        stop_repeated_failure=bool(
            term
            and any(
                u["is_final"] and u["failure_streak"] >= term["repeated_failure_threshold"]
                for u in usage
            )
        ),
        stop_no_improvement=bool(
            term
            and any(
                u["is_final"]
                and u["no_improvement_streak"] >= term["max_no_improvement_iterations"]
                for u in usage
            )
        ),
        stop_success=False,
    )


def gates(policy, checkpoints, at, step=None, resources=None):
    required = set(policy["required_types"]) | {"plan_review"}
    if resources and resources.code_iterations:
        required.add("code_risk")
    if resources and resources.experiment_runs:
        required.add("experiment_approval")
    latest = {}
    for c in sorted(checkpoints, key=lambda c: (c["created_at"], c["id"])):
        if c["step_id"] == step:
            latest[c["checkpoint_type"]] = c
    from researchbase.agent_runtime.application.safety_contracts import GateRead

    result = []
    for kind in sorted(required):
        row = latest.get(kind)
        status = (
            ("EXPIRED" if row["status"] == "PENDING" and at >= row["expires_at"] else row["status"])
            if row
            else None
        )
        result.append(
            GateRead(
                step,
                kind,
                row["id"] if row else None,
                status,
                status == "APPROVED",
                "Approved." if status == "APPROVED" else "Checkpoint required.",
            )
        )
    return tuple(result)


def reservation_gauges(repo, task, rows, step):
    """Derive gauges from durable task steps and outstanding reservations."""
    steps = {s["id"]: s for s in repo.steps(task["id"])}
    depth = 0
    if step is not None:
        if step not in steps:
            fail(ErrorCode.REFERENTIAL_INTEGRITY_ERROR, "same-task step required")
        node = steps[step]
        while node["parent_step_id"] is not None:
            depth += 1
            node = steps[node["parent_step_id"]]
    final = {u["reservation_id"] for u in rows["budget_usage_records"] if u["is_final"]}
    occupancy = 1 + sum(r["id"] not in final for r in rows["budget_reservations"])
    return depth, occupancy


def reservation_values(repo, task, rows, budget, term, policy, args, at, *, ignored_event=None):
    """Shared PR3-04 admission calculation; caller owns every persistence effect."""
    flags = causes(budget, term, rows["budget_reservations"], rows["budget_usage_records"], at)
    if any(
        any(e.get(k, False) for k in flags)
        for e in repo.events(task["id"])
        if ignored_event is None or e["id"] != ignored_event
    ) or any(flags.values()):
        fail(ErrorCode.INVALID_STATE_TRANSITION, "task stopped")
    if any(r["operation_id"] == args.operation_id for r in rows["budget_reservations"]):
        invalid("operation already reserved")
    if task["autonomy_level"] in ("A2", "A3"):
        fail(
            ErrorCode.INVALID_STATE_TRANSITION,
            "owning scientific execution prerequisites unavailable",
        )
    if any(
        not g.satisfied
        for g in gates(policy, rows["human_checkpoints"], at, args.step_id, args.resources)
    ):
        fail(ErrorCode.INVALID_STATE_TRANSITION, "checkpoint required")
    if (
        any(
            getattr(args.resources, k) > 0
            for k in ("code_iterations", "experiment_runs", "tree_nodes")
        )
        and term["score_metric_version_id"] is None
    ):
        fail(ErrorCode.INVALID_STATE_TRANSITION, "comparable evaluator required")
    depth, occupancy = reservation_gauges(repo, task, rows, args.step_id)
    if args.observed_depth != depth or args.observed_parallel_branches != occupancy:
        invalid("gauge assertion differs from durable state")
    if depth > budget["max_tree_depth"] or occupancy > budget["max_parallel_branches"]:
        fail(ErrorCode.INVALID_STATE_TRANSITION, "budget gauge exceeded")
    consumed, reserved = balances(rows["budget_reservations"], rows["budget_usage_records"])
    if any(
        consumed[k] + reserved[k] + getattr(args.resources, k) > budget["max_" + k]
        for k in ADDITIVE
    ):
        fail(ErrorCode.INVALID_STATE_TRANSITION, "budget exceeded")
    origin = min((r["created_at"] for r in rows["budget_reservations"]), default=at)
    deadline = at + timedelta(seconds=args.deadline_seconds)
    if at >= origin + timedelta(
        seconds=budget["max_wall_time_seconds"]
    ) or deadline > origin + timedelta(seconds=budget["max_wall_time_seconds"]):
        fail(ErrorCode.INVALID_STATE_TRANSITION, "wall budget exceeded")
    return {
        "budget_id": budget["id"],
        "step_id": args.step_id,
        "operation_id": args.operation_id,
        **asdict(args.resources),
        "observed_depth": depth,
        "observed_parallel_branches": occupancy,
        "deadline": deadline,
    }


def settlement_values(repo, task, rows, term, args):
    """Shared settlement validation and streak calculation; no persistence effects."""
    reservation = next(
        (r for r in rows["budget_reservations"] if r["id"] == args.reservation_id), None
    )
    if not reservation:
        fail(ErrorCode.NOT_FOUND, "reservation unavailable")
    if any(
        u["reservation_id"] == args.reservation_id and u["is_final"]
        for u in rows["budget_usage_records"]
    ):
        fail(ErrorCode.INVALID_STATE_TRANSITION, "reservation already final")
    if (
        args.outcome == "SUCCEEDED"
        and args.score is None
        and any(reservation[k] > 0 for k in ("code_iterations", "experiment_runs", "tree_nodes"))
    ):
        fail(ErrorCode.INVALID_STATE_TRANSITION, "comparable iteration score required")
    settlement(spec(ResourceVector, reservation), args.measured, args.outcome)
    if args.score is not None and (
        args.evaluator_version != term["evaluator_version"] or args.outcome != "SUCCEEDED"
    ):
        invalid("incomparable evaluator observation")
    receipts = {r["id"]: r["resulting_row_version"] for r in repo.receipt_history(task["id"])}
    reservation_steps = {r["id"]: r["step_id"] for r in rows["budget_reservations"]}
    history = [
        (u["outcome"], u["score"])
        for u in sorted(rows["budget_usage_records"], key=lambda u: receipts[u["receipt_id"]])
        if u["is_final"] and reservation_steps[u["reservation_id"]] == reservation["step_id"]
    ]
    fs, ns = streaks(history, args.outcome, args.score, term["score_direction"])
    return {
        "reservation_id": reservation["id"],
        **asdict(args.measured),
        "outcome": args.outcome,
        "is_final": args.outcome != "UNKNOWN",
        "failure_streak": fs,
        "no_improvement_streak": ns,
        "score": args.score,
        "evaluator_version": args.evaluator_version,
    }


class TaskSafetyService(ResearchTaskService):
    def __init__(self, factory, credentials, artifact_store=None, *, consumer_capability=None):
        super().__init__(factory, credentials, artifact_store)
        if consumer_capability is not None and not isinstance(
            consumer_capability, FakeConsumerCapability
        ):
            raise TypeError("in-process capability required")
        self._consumer_capability = consumer_capability

    def _trusted(self, capability):
        return self._consumer_capability is not None and capability is self._consumer_capability

    def _owner(self, repo, principal, project):
        at = self._authorize(repo, principal, project, write=True)
        if not any(
            r["actor_type"] == "HUMAN"
            and r["role"] == "OWNER"
            and r["effective_from"] <= at
            and (r["effective_until"] is None or at < r["effective_until"])
            for r in repo.authority(principal, project)
        ):
            fail(ErrorCode.FORBIDDEN, "current Human OWNER required")
        return at

    def execute(self, principal, command: SafetyCommand, *, consumer_capability=None):
        self._principal(principal)
        if not isinstance(command, SafetyCommand):
            invalid("typed safety command required")
        for attempt in range(3):
            try:
                return self._execute_safety(principal, command, consumer_capability)
            except UncertainTaskCommit:
                saved = self.replay_safety(principal, command)
                if saved is not None:
                    return saved
                raise
            except ResearchBaseError as exc:
                if not exc.details or not exc.details.get("retryable_pr301") or attempt == 2:
                    raise
        raise AssertionError("unreachable")

    def _execute_safety(self, principal, command, capability):
        digest = command.request_hash(principal.actor_id)
        trusted = self._trusted(capability)
        with self._factory() as uow:
            uow.begin_research_task()
            repo = uow.task_safety
            repo.lock_write(
                command.project_id,
                principal.actor_id,
                command.command_id,
                command.task_id,
                after_wait=lambda: self._authorize(repo, principal, command.project_id),
            )
            repo.lock_safety(
                command.task_id,
                after_wait=lambda: self._authorize(repo, principal, command.project_id),
            )
            self._authorize(repo, principal, command.project_id)
            # Consumer admission cannot be granted by public actor or request fields.
            args = command.arguments
            if isinstance(args, ReserveBudgetArguments | SettleBudgetArguments) and not trusted:
                fail(ErrorCode.FORBIDDEN, "trusted in-process consumer required")
            if (
                isinstance(args, EvaluateTerminationArguments)
                and args.policy_violation
                and not trusted
            ):
                fail(ErrorCode.FORBIDDEN, "trusted policy observation required")
            receipt = repo.receipt(command.project_id, principal.actor_id, command.command_id)
            if receipt:
                if receipt["request_hash"] != digest:
                    fail(
                        ErrorCode.IDEMPOTENCY_CONFLICT,
                        "command material differs from saved request",
                    )
                return repo.safety_result(receipt, replayed=True)
            task = self._scoped(repo, command.project_id, command.task_id)
            at = (
                self._authorize(repo, principal, command.project_id, write=True)
                if trusted
                else self._owner(repo, principal, command.project_id)
            )
            if (
                isinstance(args, BindPoliciesArguments | RespondCheckpointArguments)
                or isinstance(args, EvaluateTerminationArguments)
                and args.human_stop
            ):
                at = self._owner(repo, principal, command.project_id)
            if task["row_version"] != command.expected_row_version:
                fail(ErrorCode.CONCURRENT_MODIFICATION, "stale task revision")
            if task["status"] == "CANCELLED" and not isinstance(
                args, SettleBudgetArguments | EvaluateTerminationArguments
            ):
                fail(ErrorCode.INVALID_STATE_TRANSITION, "cancelled task")
            rows = {
                table: repo.rows(table, task["id"])
                for table in (
                    "execution_budgets",
                    "termination_policies",
                    "checkpoint_policies",
                    "checkpoint_policy_dataset_scopes",
                    "checkpoint_policy_metric_scopes",
                    "budget_reservations",
                    "budget_usage_records",
                    "human_checkpoints",
                )
            }

            def active(table, key):
                return next((r for r in rows[table] if r["id"] == task[key]), None)

            budget = active("execution_budgets", "budget_policy_id")
            term = active("termination_policies", "termination_policy_id")
            policy = active("checkpoint_policies", "checkpoint_policy_id")
            if not isinstance(
                args, BindPoliciesArguments | EvaluateTerminationArguments
            ) and not all((budget, term, policy)):
                fail(ErrorCode.INVALID_STATE_TRANSITION, "complete policy bundle required")
            # Revalidate owning scientific inputs in the same locked transaction.
            self._saved_inputs(
                uow,
                command.project_id,
                repo.inputs(task["id"]) + repo.inputs(task["id"], step=True),
            )
            pending = []
            updates = []
            bindings = {}
            flags = causes(
                budget, term, rows["budget_reservations"], rows["budget_usage_records"], at
            )
            base = {"research_task_id": task["id"], "created_at": at, "receipt_id": new_uuid7()}

            def add(table, row):
                if repo.identity_occupied(row["id"]):
                    fail(ErrorCode.CONCURRENT_MODIFICATION, "result identity occupied")
                item = {**base, **row}
                pending.append((table, item))
                rows[table].append(item)
                return item

            def budget_row(identity, content):
                return add(
                    "execution_budgets",
                    {
                        "id": identity,
                        **asdict(content),
                        "content_hash": policy_hash("ExecutionBudgetPolicy", content),
                        "hash_scheme": "sha256-cjson-v1",
                    },
                )

            def occupied(identity):
                if any(r["id"] == identity for values in rows.values() for r in values):
                    fail(ErrorCode.CONCURRENT_MODIFICATION, "proposed identity occupied")

            if isinstance(args, BindPoliciesArguments):
                if any(
                    task[k] is not None
                    for k in ("budget_policy_id", "termination_policy_id", "checkpoint_policy_id")
                ):
                    fail(ErrorCode.IMMUTABLE_RECORD, "policies already bound")
                for identity in (
                    args.budget_id,
                    args.termination_policy_id,
                    args.checkpoint_policy_id,
                ):
                    occupied(identity)
                if task["autonomy_level"] > args.checkpoint.maximum_autonomy:
                    fail(ErrorCode.INVALID_STATE_TRANSITION, "autonomy ceiling exceeded")
                budget_row(args.budget_id, args.budget)
                add(
                    "termination_policies",
                    {
                        "id": args.termination_policy_id,
                        **asdict(args.termination),
                        "content_hash": policy_hash("TerminationPolicy", args.termination),
                        "hash_scheme": "sha256-cjson-v1",
                    },
                )
                content = material_value(args.checkpoint)
                scopes = []
                for kind, member, table, col, hash_member in (
                    (
                        "dataset",
                        "allowed_dataset_snapshot_ids",
                        "checkpoint_policy_dataset_scopes",
                        "dataset_snapshot_id",
                        "allowed_dataset_snapshots",
                    ),
                    (
                        "metric",
                        "allowed_metric_version_ids",
                        "checkpoint_policy_metric_scopes",
                        "metric_definition_version_id",
                        "allowed_metric_versions",
                    ),
                ):
                    content.pop(member)
                    content[hash_member] = []
                    for identity in getattr(args.checkpoint, member):
                        ref = repo.scope_reference(kind, identity, command.project_id)
                        if not ref:
                            fail(ErrorCode.NOT_FOUND, "exact scope reference unavailable")
                        if not ref["scoped"]:
                            fail(ErrorCode.FORBIDDEN, "scope reference unavailable")
                        if not ref["frozen"]:
                            fail(ErrorCode.VERSION_NOT_FROZEN, "frozen scope reference required")
                        content[hash_member].append(
                            {"id": str(identity), "content_hash": ref["content_hash"]}
                        )
                        scopes.append(
                            (
                                table,
                                {
                                    "id": new_uuid7(),
                                    "checkpoint_policy_id": args.checkpoint_policy_id,
                                    col: identity,
                                    "content_hash": ref["content_hash"],
                                },
                            )
                        )
                if args.termination.score_metric_version_id:
                    ref = repo.scope_reference(
                        "metric", args.termination.score_metric_version_id, command.project_id
                    )
                    if not ref or not ref["scoped"]:
                        fail(ErrorCode.FORBIDDEN, "metric scope unavailable")
                    if not ref["frozen"]:
                        fail(ErrorCode.VERSION_NOT_FROZEN, "frozen score metric required")
                stored = {
                    k: v
                    for k, v in asdict(args.checkpoint).items()
                    if k not in ("allowed_dataset_snapshot_ids", "allowed_metric_version_ids")
                }
                add(
                    "checkpoint_policies",
                    {
                        "id": args.checkpoint_policy_id,
                        **stored,
                        "content_hash": policy_hash("CheckpointPolicy", content),
                        "hash_scheme": "sha256-cjson-v1",
                    },
                )
                for table, row in scopes:
                    add(table, row)
                bindings = {
                    "budget_policy_id": args.budget_id,
                    "termination_policy_id": args.termination_policy_id,
                    "checkpoint_policy_id": args.checkpoint_policy_id,
                }
            elif isinstance(args, ReserveBudgetArguments):
                assert budget and term and policy
                values = reservation_values(repo, task, rows, budget, term, policy, args, at)
                add("budget_reservations", {"id": new_uuid7(), **values})
                flags = causes(
                    budget, term, rows["budget_reservations"], rows["budget_usage_records"], at
                )
            elif isinstance(args, SettleBudgetArguments):
                assert term
                values = settlement_values(repo, task, rows, term, args)
                add("budget_usage_records", {"id": new_uuid7(), **values, "settled_at": at})
                flags = causes(
                    budget, term, rows["budget_reservations"], rows["budget_usage_records"], at
                )
            elif isinstance(args, RequestCheckpointArguments):
                assert policy
                occupied(args.checkpoint_id)
                if args.step_id is not None and args.step_id not in {
                    s["id"] for s in repo.steps(task["id"])
                }:
                    fail(ErrorCode.REFERENTIAL_INTEGRITY_ERROR, "same-task step required")
                if any(
                    c["status"] == "PENDING"
                    and c["step_id"] == args.step_id
                    and c["checkpoint_type"] == args.checkpoint_type
                    for c in rows["human_checkpoints"]
                ):
                    fail(ErrorCode.INVALID_STATE_TRANSITION, "pending checkpoint already exists")
                if args.proposed_budget is not None:
                    occupied(args.proposed_budget_id)
                    budget_row(args.proposed_budget_id, args.proposed_budget)
                add(
                    "human_checkpoints",
                    {
                        "id": args.checkpoint_id,
                        "step_id": args.step_id,
                        "checkpoint_type": args.checkpoint_type,
                        "status": "PENDING",
                        "reason": args.reason,
                        "requested_at": at,
                        "expires_at": at + timedelta(seconds=policy["timeout_seconds"]),
                        "responded_at": None,
                        "responded_by": None,
                        "response_reason": None,
                        "row_version": 1,
                        "response_receipt_id": None,
                        "proposed_budget_id": args.proposed_budget_id,
                    },
                )
            elif isinstance(args, RespondCheckpointArguments):
                checkpoint = next(
                    (c for c in rows["human_checkpoints"] if c["id"] == args.checkpoint_id), None
                )
                if not checkpoint:
                    fail(ErrorCode.NOT_FOUND, "checkpoint unavailable")
                if checkpoint["status"] != "PENDING":
                    fail(ErrorCode.INVALID_STATE_TRANSITION, "checkpoint already answered")
                if checkpoint["row_version"] != args.expected_checkpoint_row_version:
                    fail(ErrorCode.CONCURRENT_MODIFICATION, "stale checkpoint revision")
                at = self._owner(repo, principal, command.project_id)
                base["created_at"] = at
                if checkpoint["status"] != "PENDING" or at >= checkpoint["expires_at"]:
                    fail(ErrorCode.INVALID_STATE_TRANSITION, "checkpoint response blocked")
                updates.append(
                    (
                        checkpoint["id"],
                        {
                            "status": args.response,
                            "row_version": 2,
                            "responded_at": at,
                            "responded_by": principal.actor_id,
                            "response_reason": args.reason,
                            "response_receipt_id": base["receipt_id"],
                        },
                    )
                )
            elif isinstance(args, EvaluateTerminationArguments):
                flags = causes(
                    budget,
                    term,
                    rows["budget_reservations"],
                    rows["budget_usage_records"],
                    at,
                    human=args.human_stop,
                    policy=args.policy_violation,
                )
                for checkpoint in rows["human_checkpoints"]:
                    if checkpoint["status"] == "PENDING" and at >= checkpoint["expires_at"]:
                        updates.append(
                            (
                                checkpoint["id"],
                                {
                                    "status": "EXPIRED",
                                    "row_version": 2,
                                    "responded_at": at,
                                    "responded_by": None,
                                    "response_reason": "Checkpoint expired.",
                                    "response_receipt_id": base["receipt_id"],
                                },
                            )
                        )
            revision = task["row_version"] + 1
            repo.update_task(task["id"], {"row_version": revision, **bindings})
            receipt = {
                "id": base["receipt_id"],
                "project_id": command.project_id,
                "actor_id": principal.actor_id,
                "command_id": command.command_id,
                "command_name": command.command_name,
                "research_task_id": task["id"],
                "request_hash": digest,
                "hash_scheme": "sha256-cjson-v1",
                "material_version": 1,
                "resulting_row_version": revision,
                "completed_at": at,
            }
            repo.insert("research_task_command_receipts", receipt)
            for table, row in pending:
                # psycopg adapts lists as PostgreSQL arrays; tuples denote records.
                repo.insert(
                    table, {k: list(v) if isinstance(v, tuple) else v for k, v in row.items()}
                )
            for identity, values in updates:
                repo.respond(identity, values)
            event = {
                "id": new_uuid7(),
                "research_task_id": task["id"],
                "actor_id": principal.actor_id,
                "command_id": command.command_id,
                "event_type": EVENTS[command.command_name],
                "sequence": revision,
                "task_row_version": revision,
                "prior_status": task["status"],
                "new_status": task["status"],
                "reason": args.reason,
                "occurred_at": at,
            }
            if isinstance(
                args, ReserveBudgetArguments | SettleBudgetArguments | EvaluateTerminationArguments
            ):
                event.update(flags)
            repo.insert("research_task_events", event)
            repo.insert(
                "research_task_receipt_events",
                {
                    "receipt_id": receipt["id"],
                    "research_task_id": task["id"],
                    "event_id": event["id"],
                },
            )
            repo.force_constraints()
            result = repo.safety_result(receipt, replayed=False)
            uow.commit()
            return result

    def bind_task_policies(self, principal, command):
        return self._named("bind_task_policies", principal, command)

    def reserve_task_budget(self, principal, command):
        return self._named("reserve_task_budget", principal, command)

    def settle_task_budget(self, principal, command):
        return self._named("settle_task_budget", principal, command)

    def evaluate_task_termination(self, principal, command):
        return self._named("evaluate_task_termination", principal, command)

    def request_human_checkpoint(self, principal, command):
        return self._named("request_human_checkpoint", principal, command)

    def respond_human_checkpoint(self, principal, command):
        return self._named("respond_human_checkpoint", principal, command)

    def replay_safety(self, principal, command):
        self._principal(principal)
        with self._factory() as uow:
            uow.begin_formal_read()
            repo = uow.task_safety
            self._authorize(repo, principal, command.project_id)
            receipt = repo.receipt(command.project_id, principal.actor_id, command.command_id)
            if receipt is None:
                return None
            if receipt["request_hash"] != command.request_hash(principal.actor_id):
                fail(ErrorCode.IDEMPOTENCY_CONFLICT, "command material differs from saved request")
            return repo.safety_result(receipt, replayed=True)

    def get_task_safety(self, principal, project_id, task_id):
        from researchbase.agent_runtime.application.safety_contracts import TaskSafetyRead

        return cast(
            TaskSafetyRead, self._read_safety(principal, project_id, task_id, history=False)
        )

    def get_task_checkpoint_history(self, principal, project_id, task_id):
        from researchbase.agent_runtime.application.safety_contracts import CheckpointHistoryRead

        return cast(
            CheckpointHistoryRead, self._read_safety(principal, project_id, task_id, history=True)
        )

    def _read_safety(self, principal, project, task, *, history):
        self._principal(principal)
        with self._factory() as uow:
            uow.begin_formal_read()
            repo = uow.task_safety
            at = repo.snapshot_at()
            self._authorize(repo, principal, project, at=at)
            row = self._scoped(repo, project, task)
            return safety_projection(repo, row, at, history=history)


def safety_projection(repo, task, at, *, history):
    from researchbase.agent_runtime.application.safety_contracts import (
        BudgetPolicyRead,
        CheckpointHistoryRead,
        CheckpointPolicyRead,
        CheckpointRead,
        DatasetScopeRead,
        MetricScopeRead,
        TaskSafetyRead,
        TerminationPolicyRead,
    )
    from researchbase.agent_runtime.domain.research_task import UNMET_PREREQUISITES
    from researchbase.agent_runtime.domain.task_safety import StopCause

    rows = {
        table: repo.rows(table, task["id"])
        for table in (
            "execution_budgets",
            "termination_policies",
            "checkpoint_policies",
            "checkpoint_policy_dataset_scopes",
            "checkpoint_policy_metric_scopes",
            "budget_reservations",
            "budget_usage_records",
            "human_checkpoints",
        )
    }
    verify_saved_policies(repo, task["project_id"], rows)
    budgets = {r["id"]: BudgetPolicyRead(**r) for r in rows["execution_budgets"]}
    checkpoints = tuple(
        CheckpointRead(
            **r,
            effective_status="EXPIRED"
            if r["status"] == "PENDING" and at >= r["expires_at"]
            else r["status"],
            proposed_budget=budgets.get(r["proposed_budget_id"]),
        )
        for r in sorted(rows["human_checkpoints"], key=lambda r: (r["created_at"], r["id"]))
    )
    if history:
        return CheckpointHistoryRead(task["id"], task["row_version"], checkpoints)
    budget = budgets.get(task["budget_policy_id"])
    term = next(
        (
            TerminationPolicyRead(**r)
            for r in rows["termination_policies"]
            if r["id"] == task["termination_policy_id"]
        ),
        None,
    )
    raw_policy = next(
        (r for r in rows["checkpoint_policies"] if r["id"] == task["checkpoint_policy_id"]), None
    )
    policy = None
    if raw_policy:
        ds = tuple(
            DatasetScopeRead(**r)
            for r in rows["checkpoint_policy_dataset_scopes"]
            if r["checkpoint_policy_id"] == raw_policy["id"]
        )
        ms = tuple(
            MetricScopeRead(**r)
            for r in rows["checkpoint_policy_metric_scopes"]
            if r["checkpoint_policy_id"] == raw_policy["id"]
        )
        policy = CheckpointPolicyRead(
            **raw_policy,
            allowed_dataset_snapshot_ids=tuple(r.dataset_snapshot_id for r in ds),
            allowed_metric_version_ids=tuple(r.metric_definition_version_id for r in ms),
            dataset_scope=ds,
            metric_scope=ms,
        )
    consumed, reserved = balances(rows["budget_reservations"], rows["budget_usage_records"])
    elapsed = Decimal(0)
    if rows["budget_reservations"]:
        elapsed = Decimal(
            str((at - min(r["created_at"] for r in rows["budget_reservations"])).total_seconds())
        )
    final = {u["reservation_id"] for u in rows["budget_usage_records"] if u["is_final"]}
    pending = [r for r in rows["budget_reservations"] if r["id"] not in final]
    outstanding = max(
        (max(0, int((r["deadline"] - at).total_seconds())) for r in pending), default=0
    )
    remaining: dict[str, Any] = {
        k: max(0, getattr(budget, "max_" + k) - consumed[k] - reserved[k]) if budget else 0
        for k in ADDITIVE
    }
    stop_fields = (
        "stop_human",
        "stop_policy",
        "stop_budget",
        "stop_repeated_failure",
        "stop_no_improvement",
        "stop_success",
    )
    flags = causes(
        asdict(budget) if budget else None,
        asdict(term) if term else None,
        rows["budget_reservations"],
        rows["budget_usage_records"],
        at,
    )
    for e in repo.events(task["id"]):
        for k in stop_fields:
            flags[k] |= e[k]
    stops = tuple(str(c) for c, k in zip(StopCause, stop_fields, strict=True) if flags[k])
    return TaskSafetyRead(
        task["id"],
        task["row_version"],
        task["budget_policy_id"],
        task["termination_policy_id"],
        task["checkpoint_policy_id"],
        budget,
        term,
        policy,
        ResourceVector(wall_time_seconds=int(elapsed), **consumed),
        ResourceVector(wall_time_seconds=outstanding, **reserved),
        ResourceVector(
            wall_time_seconds=max(0, budget.max_wall_time_seconds - int(elapsed)) if budget else 0,
            **remaining,
        ),
        elapsed,
        max((r["observed_depth"] for r in rows["budget_reservations"]), default=0),
        len(pending),
        stops,
        stops[0] if stops else None,
        gates(raw_policy, rows["human_checkpoints"], at) if raw_policy else (),
        UNMET_PREREQUISITES[1:] if budget else UNMET_PREREQUISITES,
    )


def verify_saved_policies(repo, project, rows):
    """Reconstruct policy digests and exact scope references inside the read snapshot."""
    for table, kind, envelope in (
        ("execution_budgets", BudgetSpec, "ExecutionBudgetPolicy"),
        ("termination_policies", TerminationSpec, "TerminationPolicy"),
    ):
        for row in rows[table]:
            if policy_hash(envelope, spec(kind, row)) != row["content_hash"]:
                fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved policy material contradiction")
    for row in rows["termination_policies"]:
        if row["score_metric_version_id"] is not None:
            ref = repo.scope_reference("metric", row["score_metric_version_id"], project)
            if not ref or not ref["scoped"] or not ref["frozen"]:
                fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved score metric contradiction")
    for row in rows["checkpoint_policies"]:
        content = {
            k: v
            for k, v in row.items()
            if k
            not in (
                "id",
                "research_task_id",
                "created_at",
                "receipt_id",
                "content_hash",
                "hash_scheme",
            )
        }
        for kind, table, col, member in (
            (
                "dataset",
                "checkpoint_policy_dataset_scopes",
                "dataset_snapshot_id",
                "allowed_dataset_snapshots",
            ),
            (
                "metric",
                "checkpoint_policy_metric_scopes",
                "metric_definition_version_id",
                "allowed_metric_versions",
            ),
        ):
            refs = []
            for scope in rows[table]:
                if scope["checkpoint_policy_id"] != row["id"]:
                    continue
                ref = repo.scope_reference(kind, scope[col], project)
                if (
                    not ref
                    or not ref["scoped"]
                    or not ref["frozen"]
                    or ref["content_hash"] != scope["content_hash"]
                ):
                    fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved exact scope contradiction")
                refs.append({"id": str(scope[col]), "content_hash": scope["content_hash"]})
            content[member] = sorted(refs, key=lambda r: r["id"])
        if policy_hash("CheckpointPolicy", content) != row["content_hash"]:
            fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved checkpoint policy contradiction")
