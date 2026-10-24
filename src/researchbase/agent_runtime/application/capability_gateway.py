"""PR3-03 Lifecycle commands and append-only settlement. No execution or dispatch."""

from __future__ import annotations

import json
from dataclasses import asdict, fields, replace
from datetime import timedelta
from decimal import Decimal
from itertools import chain
from typing import Any

from researchbase.agent_runtime.application.agent_contracts import (
    AgentAvailabilityDTO,
    AgentVersionDTO,
)
from researchbase.agent_runtime.application.contracts import InputType, TaskInput
from researchbase.agent_runtime.application.gateway_contracts import (
    AgentExecutionContext,
    AgentToolPolicyRead,
    CapabilityEventRead,
    CapabilityInvocationRead,
    CapabilityRequest,
    CapabilityResult,
    FinishInvocationArguments,
    GatewayCommand,
    GatewayRefRead,
    InvocationListCursor,
    RegisterToolPolicyArguments,
    RequestInvocationArguments,
    StartInvocationArguments,
    TaskCapabilityInvocationsRead,
)
from researchbase.agent_runtime.application.research_task import _INPUT_COLUMNS, fail
from researchbase.agent_runtime.application.routing import (
    CapabilityPolicy,
    FrozenArtifactPin,
    RoutingPolicy,
    SkillRegistryLoader,
    SkillRouter,
)
from researchbase.agent_runtime.application.safety_contracts import (
    ReserveBudgetArguments,
    SettleBudgetArguments,
)
from researchbase.agent_runtime.application.task_safety import (
    TaskSafetyService,
    balances,
    causes,
    gates,
    reservation_gauges,
    reservation_values,
    settlement_values,
    verify_saved_policies,
)
from researchbase.agent_runtime.domain.capability_invocation import (
    FakeParameters,
    GatewayRef,
    material,
    typed,
)
from researchbase.agent_runtime.domain.harness_manifest import HarnessManifest
from researchbase.agent_runtime.domain.research_task import invalid
from researchbase.agent_runtime.domain.task_safety import ADDITIVE, ResourceVector, integer
from researchbase.agent_runtime.domain.tool_policy import PermissionSpec, ToolPolicySpec
from researchbase.agent_runtime.ports.task_repository import UncertainTaskCommit
from researchbase.application.governance_queries import (
    GovernanceQueryService,
    ValidityProjection,
    ValidityState,
)
from researchbase.foundation.canonical_json import canonical_json_bytes
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import sha256_bytes
from researchbase.foundation.ids import new_uuid7

FAKE_RESOURCES = ResourceVector(60, 0, 1, 0, 0, 0, 0, Decimal("0.000000"), Decimal("0.125000"))
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


class _InputValidationReads:
    """Per-pass repository view; nothing is retained across fresh() calls."""

    def __init__(self, owner, **overrides):
        self._owner = owner
        self.__dict__.update(overrides)

    def __getattr__(self, name):
        return getattr(self._owner, name)


class _GatewayValiditySnapshot(GovernanceQueryService):
    """Discover the exact owning traversal, then serve one pass's batched facts."""

    def __init__(self, project):
        self.project = project
        self.targets = {}
        self.projections: dict | None = None

    def validity_projection_in_uow(self, uow, project, kind, identity):
        assert project == self.project
        key = (kind, identity)
        self.targets[key] = None
        if self.projections is None:
            # Discovery is never admission evidence. Neutral validity lets the owning
            # verifier enumerate dependencies even when real validity will reject them.
            return ValidityProjection(key[0], identity, ValidityState.NOT_ASSESSED, (), (), ())
        if key not in self.projections:
            fail(
                ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
                "gateway validity target unavailable in discovered snapshot",
            )
        value = self.projections[key]
        if isinstance(value, ResearchBaseError):
            raise value
        return value


class GatewayAccounting:
    def __init__(self, consumer_capability):
        self._consumer = consumer_capability

    def prepare(self, repo, task, args, at, *, receipt_id, capability, event_id=None):
        if self._consumer is None or capability is not self._consumer:
            fail(ErrorCode.FORBIDDEN, "trusted in-process consumer required")
        rows = {table: repo.rows(table, task["id"]) for table in SAFETY_TABLES}
        verify_saved_policies(repo, task["project_id"], rows)
        # Rechecking our uncommitted writes must not count this reservation twice.
        rows["budget_reservations"] = [
            r for r in rows["budget_reservations"] if r["receipt_id"] != receipt_id
        ]
        bundle = []
        for table, key in (
            ("execution_budgets", "budget_policy_id"),
            ("termination_policies", "termination_policy_id"),
            ("checkpoint_policies", "checkpoint_policy_id"),
        ):
            row = next((r for r in rows[table] if r["id"] == task[key]), None)
            if row is None:
                fail(ErrorCode.INVALID_STATE_TRANSITION, "complete policy bundle required")
            bundle.append(row)
        budget, term, policy = bundle
        if budget["pricing_basis"] != "fake-usd-v1":
            fail(ErrorCode.INVALID_STATE_TRANSITION, "fake pricing basis required")
        if task["autonomy_level"] > policy["maximum_autonomy"]:
            fail(ErrorCode.INVALID_STATE_TRANSITION, "autonomy ceiling exceeded")
        depth, occupancy = reservation_gauges(repo, task, rows, args.step_id)
        proposed = ReserveBudgetArguments(
            args.invocation_id,
            args.step_id,
            FAKE_RESOURCES,
            depth,
            occupancy,
            args.deadline_seconds,
            args.reason,
        )
        values = reservation_values(
            repo, task, rows, budget, term, policy, proposed, at, ignored_event=event_id
        )
        return values, rows, budget, term

    def reserve_in_uow(self, repo, task, args, at, *, receipt_id, reservation_id, capability):
        values, rows, budget, term = self.prepare(
            repo, task, args, at, receipt_id=receipt_id, capability=capability
        )
        reservation = {
            "id": reservation_id,
            "research_task_id": task["id"],
            "receipt_id": receipt_id,
            "created_at": at,
            **values,
        }
        repo.insert("budget_reservations", reservation)
        flags = causes(
            budget,
            term,
            [*rows["budget_reservations"], reservation],
            rows["budget_usage_records"],
            at,
        )
        return reservation, flags

    def settle_in_uow(self, repo, task, invocation, args, at, *, receipt_id, usage_id, capability):
        if self._consumer is None or capability is not self._consumer:
            fail(ErrorCode.FORBIDDEN, "trusted observation required")
        rows = {table: repo.rows(table, task["id"]) for table in SAFETY_TABLES}
        verify_saved_policies(repo, task["project_id"], rows)
        term = next(
            r for r in rows["termination_policies"] if r["id"] == task["termination_policy_id"]
        )
        budget = next(r for r in rows["execution_budgets"] if r["id"] == task["budget_policy_id"])
        outcome = "UNKNOWN" if args.outcome == "UNKNOWN_OUTCOME" else args.outcome
        observation = SettleBudgetArguments(
            invocation["reservation_id"], args.measured, outcome, None, None, args.reason
        )
        values = settlement_values(repo, task, rows, term, observation)
        usage = dict(
            id=usage_id,
            research_task_id=task["id"],
            receipt_id=receipt_id,
            settled_at=at,
            created_at=at,
            **values,
        )
        repo.insert("budget_usage_records", usage)
        return usage, causes(
            budget, term, rows["budget_reservations"], [*rows["budget_usage_records"], usage], at
        )


class _SavedReplay(Exception):
    def __init__(self, result):
        self.result = result


def policy_spec(repo, project, identity):
    row = repo.policy(project, identity)
    if row is None:
        fail(ErrorCode.NOT_FOUND, "exact policy unavailable")
    permissions = tuple(
        PermissionSpec(**{f.name: r[f.name] for f in fields(PermissionSpec)})
        for r in repo.permissions(project, identity)
    )
    data: dict[str, Any] = {
        f.name: permissions if f.name == "permissions" else row[f.name]
        for f in fields(ToolPolicySpec)
    }
    value = ToolPolicySpec(**data)
    if value.digest(project) != row["content_hash"]:
        fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved policy contradiction")
    return row, value


def fake_measurement(outcome):
    return (
        FAKE_RESOURCES
        if outcome == "UNKNOWN_OUTCOME"
        else replace(
            FAKE_RESOURCES, wall_time_seconds=0, gpu_hours=Decimal(0), token_cost=Decimal(0)
        )
    )


def task_stopped(repo, task, *, ignored_event=None):
    """Sticky task stop, excluding this command's own newly written event."""
    return task["status"] == "CANCELLED" or any(
        any(
            event[key]
            for key in (
                "stop_human",
                "stop_policy",
                "stop_budget",
                "stop_repeated_failure",
                "stop_no_improvement",
                "stop_success",
            )
        )
        for event in repo.events(task["id"])
        if event["id"] != ignored_event
    )


class CapabilityGatewayService(TaskSafetyService):
    """Shares safety authorization helpers, never enters a public safety command."""

    def __init__(self, factory, credentials, artifact_store=None, *, consumer_capability=None):
        super().__init__(
            factory, credentials, artifact_store, consumer_capability=consumer_capability
        )
        self._store = artifact_store
        self._accounting = GatewayAccounting(consumer_capability)

    def register_agent_tool_policy(self, principal, command: GatewayCommand):
        return self._run(principal, command, "register_agent_tool_policy", None)

    def request_capability_invocation(self, principal, command: GatewayCommand, context=None):
        return self._run(principal, command, "request_capability_invocation", context)

    def start_capability_invocation(self, principal, command: GatewayCommand, context=None):
        return self._run(principal, command, "start_capability_invocation", context)

    def finish_capability_invocation(self, principal, command: GatewayCommand, context=None):
        return self._run(principal, command, "finish_capability_invocation", context)

    def _read_scope(self, uow, principal, project, task=None):
        # All authority and current projections belong to this one formal snapshot.
        uow.begin_formal_read()
        repo = uow.gateway
        self._authorize(repo, principal, project, at=repo.snapshot_at())
        if task is not None:
            self._scoped(repo, project, task)
        return repo

    def get_agent_tool_policy(self, principal, project_id, policy_id):
        """Exact stored policy and canonically ordered permissions in one snapshot."""
        self._principal(principal)
        with self._factory() as uow:
            repo = self._read_scope(uow, principal, project_id)
            row, policy = policy_spec(repo, project_id, policy_id)
            return AgentToolPolicyRead(**row, permissions=policy.permissions)

    def get_capability_invocation(self, principal, project_id, task_id, invocation_id):
        """Availability/effective outcome/usage are projections of this read snapshot."""
        self._principal(principal)
        with self._factory() as uow:
            repo = self._read_scope(uow, principal, project_id, task_id)
            row = repo.invocation(project_id, task_id, invocation_id)
            if row is None:
                fail(ErrorCode.NOT_FOUND, "invocation unavailable")
            return self._invocation_projection(uow, row)

    def list_task_capability_invocations(
        self, principal, project_id, task_id, limit=100, after=None
    ):
        """Keyset page; every nested projection shares the same formal snapshot."""
        self._principal(principal)
        integer(limit, minimum=1, maximum=256)
        if after is not None and type(after) is not InvocationListCursor:
            invalid("closed invocation cursor required")
        with self._factory() as uow:
            repo = self._read_scope(uow, principal, project_id, task_id)
            rows = repo.invocation_page(
                project_id,
                task_id,
                limit,
                after.created_at if after else None,
                after.id if after else None,
            )
            page = rows[:limit]
            cursor = (
                InvocationListCursor(page[-1]["created_at"], page[-1]["id"])
                if len(rows) > limit
                else None
            )
            return TaskCapabilityInvocationsRead(
                task_id, tuple(self._invocation_projection(uow, row) for row in page), cursor
            )

    def _invocation_projection(self, uow, row):
        repo = uow.gateway
        project, task, identity = row["project_id"], row["research_task_id"], row["id"]
        refs = []
        for ref in repo.invocation_refs(project, task, identity):
            family, column = next(
                (family, column)
                for family, column in _INPUT_COLUMNS.items()
                if ref[column] is not None
            )
            owning = self._resolve(uow, project, TaskInput(InputType(family), ref[column]), ref)
            refs.append(
                (
                    ref["direction"],
                    family,
                    ref[column],
                    GatewayRefRead(**ref, validity_warnings=owning.validity_warnings),
                )
            )
        events = tuple(
            CapabilityEventRead(**event)
            for event in sorted(
                repo.invocation_events(project, task, identity), key=lambda event: event["sequence"]
            )
        )
        effective = next(
            (event for event in reversed(events) if event.event_type in ("RECONCILED", "FINISHED")),
            None,
        )
        availability = repo.agent_availability(row["agent_version_id"])
        if availability is None:
            fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved availability unavailable")
        return CapabilityInvocationRead(
            **row,
            refs=tuple(ref[-1] for ref in sorted(refs, key=lambda ref: ref[:3])),
            events=events,
            effective_outcome=(effective.reconciled_outcome or effective.new_status)
            if effective
            else None,
            effective_usage_record_id=effective.usage_record_id if effective else None,
            current_availability=availability["status"],
            execution_enabled=False,
        )

    def invoke(
        self, request: CapabilityRequest, context: AgentExecutionContext
    ) -> CapabilityResult:
        """One fresh committed start authorizes one call; replay never redispatches."""
        if type(request) is not CapabilityRequest:
            invalid("closed capability request required")
        if type(context) is not AgentExecutionContext or not self._trusted(
            context.consumer_capability
        ):
            fail(ErrorCode.FORBIDDEN, "trusted in-process context required")
        principal = context.principal
        requested = GatewayCommand(
            context.project_id,
            context.task_id,
            request.request_command_id,
            request.expected_row_version,
            "request_capability_invocation",
            request.arguments,
        )
        self._context(principal, requested, context)
        saved_request = self.request_capability_invocation(principal, requested, context)
        start = GatewayCommand(
            context.project_id,
            context.task_id,
            request.start_command_id,
            saved_request.resulting_row_version,
            "start_capability_invocation",
            StartInvocationArguments(
                request.arguments.invocation_id,
                saved_request.resulting_invocation_revision,
                "Start finite fake invocation.",
            ),
        )
        saved_start = self.start_capability_invocation(principal, start, context)
        if saved_start.replayed:
            completed = self._saved_completion(request, context, saved_start)
            if completed is not None:
                return completed
            fail(
                ErrorCode.INVALID_STATE_TRANSITION,
                "Prior start unresolved; explicit reconciliation required.",
            )
        # No UoW survives either command call. No injected executable or hidden subcall.
        from researchbase.agent_runtime.application.routing import finite_fake_echo

        summary, error = finite_fake_echo(request.arguments.parameters)
        outcome = request.arguments.parameters.outcome
        measured = fake_measurement(outcome)
        observation = FinishInvocationArguments(
            request.arguments.invocation_id,
            saved_start.resulting_invocation_revision,
            "FINISH",
            outcome,
            measured,
            (),
            None,
            None,
            summary,
            error,
            "Observe finite fake invocation.",
        )
        finish = GatewayCommand(
            context.project_id,
            context.task_id,
            request.finish_command_id,
            saved_start.resulting_row_version,
            "finish_capability_invocation",
            observation,
        )
        saved_finish = self.finish_capability_invocation(
            principal, finish, replace(context, finish_observation=observation)
        )
        # Read the immutable receipt-owned completion, including an uncertain finish commit.
        result = self._saved_completion(request, context, saved_start)
        if result is None or saved_finish.invocation_id != result.invocation_id:
            fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved finish unavailable")
        return result

    def _saved_completion(self, request, context, saved_start):
        with self._factory() as uow:
            repo = self._read_scope(uow, context.principal, context.project_id, context.task_id)
            receipt = repo.gateway_receipt(
                context.project_id, context.principal.actor_id, request.finish_command_id
            )
            if receipt is None:
                return None
            row = repo.invocation(
                context.project_id, context.task_id, request.arguments.invocation_id
            )
            if row is None or (
                receipt["command_name"] != "finish_capability_invocation"
                or receipt["result_capability_invocation_id"] != row["id"]
                or receipt["id"] != row["finish_receipt_id"]
            ):
                fail(ErrorCode.IDEMPOTENCY_CONFLICT, "finish identity belongs to another command")
            event = next(
                (
                    event
                    for event in repo.invocation_events(
                        context.project_id, context.task_id, row["id"]
                    )
                    if event["id"] == receipt["result_capability_event_id"]
                    and event["event_type"] == "FINISHED"
                ),
                None,
            )
            if event is None:
                fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved finish event unavailable")
            usage = next(
                (
                    row
                    for row in repo.rows("budget_usage_records", context.task_id)
                    if row["id"] == event["usage_record_id"]
                ),
                None,
            )
            if usage is None:
                fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "saved finish usage unavailable")
            measured = ResourceVector(**{f.name: usage[f.name] for f in fields(ResourceVector)})
            outputs = tuple(
                GatewayRef(
                    "ARTIFACT_VERSION", ref["artifact_version_id"], ref["content_hash"], None
                )
                for ref in repo.invocation_refs(context.project_id, context.task_id, row["id"])
                if ref["receipt_id"] == receipt["id"] and ref["direction"] == "OUTPUT"
            )
            observation = FinishInvocationArguments(
                row["id"],
                saved_start.resulting_invocation_revision,
                "FINISH",
                event["new_status"],
                measured,
                outputs,
                row["trace_artifact_version_id"],
                row["trace_content_hash"],
                row["result_summary"],
                row["error_code"],
                "Observe finite fake invocation.",
            )
            command = GatewayCommand(
                context.project_id,
                context.task_id,
                request.finish_command_id,
                saved_start.resulting_row_version,
                "finish_capability_invocation",
                observation,
            )
            self._saved(repo, receipt, command.request_hash(context.principal.actor_id))
            return CapabilityResult(
                row["id"],
                event["new_status"],
                outputs,
                row["trace_artifact_version_id"],
                measured,
                row["error_code"],
                row["result_summary"],
            )

    def _context(self, principal, command, context, invocation=None, *, finish=False):
        if (
            type(context) is not AgentExecutionContext
            or not self._trusted(context.consumer_capability)
            or (finish and context.finish_observation is not command.arguments)
        ):
            fail(
                ErrorCode.FORBIDDEN,
                "trusted observation required" if finish else "trusted in-process context required",
            )
        if (
            context.principal != principal
            or context.project_id != command.project_id
            or context.task_id != command.task_id
        ):
            fail(ErrorCode.FORBIDDEN, "trusted context scope disagrees")
        if invocation and any(
            (
                context.agent_version_id != invocation["agent_version_id"],
                context.step_id != invocation["step_id"],
                context.harness_artifact_version_id != invocation["harness_artifact_version_id"],
                context.harness_content_hash != invocation["harness_content_hash"],
            )
        ):
            fail(ErrorCode.FORBIDDEN, "trusted context provenance disagrees")

    @staticmethod
    def _pin(repo, project, identity, digest):
        row = repo.artifact_pin(project, identity)
        if row is None:
            fail(ErrorCode.NOT_FOUND, "exact artifact unavailable")
        if not row["scoped"] or row["project_id"] != project:
            fail(ErrorCode.FORBIDDEN, "artifact scope unavailable")
        if row["status"] not in ("FROZEN", "SUPERSEDED") or row["frozen_at"] is None:
            fail(ErrorCode.VERSION_NOT_FROZEN, "historically frozen artifact required")
        if row["content_hash"] != digest or type(row["byte_size"]) is not int:
            fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "exact artifact pins disagree")
        return row

    def _preflight(self, principal, command):
        """All retained-byte I/O finishes before entering the command/lock transaction."""
        args = command.arguments
        with self._factory() as uow:
            uow.begin_formal_read()
            repo = uow.gateway
            self._authorize(repo, principal, command.project_id)
            if isinstance(args, FinishInvocationArguments):
                return None
            starting = isinstance(args, StartInvocationArguments)
            if starting:
                self._authorize(repo, principal, command.project_id, write=True)
                invocation = repo.invocation(
                    command.project_id, command.task_id, args.invocation_id
                )
                if invocation is None:
                    fail(ErrorCode.NOT_FOUND, "invocation unavailable")
                if self._store is None:
                    fail(ErrorCode.FROZEN_REFERENCE_REQUIRED, "retained bytes unavailable")
                data = self._store.open(invocation["parameters_content_hash"])
                values = {
                    f.name: invocation[f.name]
                    for f in fields(RequestInvocationArguments)
                    if f.name in invocation
                }
                reservation = next(
                    r
                    for r in repo.rows("budget_reservations", command.task_id)
                    if r["id"] == invocation["reservation_id"]
                )
                values.update(
                    invocation_id=invocation["id"],
                    reason=args.reason,
                    deadline_seconds=int(
                        (reservation["deadline"] - reservation["created_at"]).total_seconds()
                    ),
                    parameters=typed(FakeParameters, json.loads(data), decode=True),
                    input_refs=tuple(
                        GatewayRef(family, r[column], r["content_hash"], r["hash_scheme"])
                        for r in repo.invocation_refs(
                            command.project_id, command.task_id, invocation["id"]
                        )
                        if r["direction"] == "INPUT"
                        for family, column in _INPUT_COLUMNS.items()
                        if r[column] is not None
                    ),
                )
                args = RequestInvocationArguments(**values)
            if isinstance(args, RegisterToolPolicyArguments):
                policy = args.policy
            else:
                assert isinstance(args, RequestInvocationArguments)
                _, policy = policy_spec(repo, command.project_id, args.policy_id)
            pins: dict[Any, Any] = {}

            def load(identity, digest):
                row = self._pin(repo, command.project_id, identity, digest)
                if self._store is None:
                    fail(ErrorCode.FROZEN_REFERENCE_REQUIRED, "retained bytes unavailable")
                data = self._store.open(digest)
                if (
                    type(data) is not bytes
                    or len(data) != row["byte_size"]
                    or str(sha256_bytes(data)) != digest
                ):
                    fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "retained bytes disagree")
                pins[identity] = (digest, row["byte_size"])
                return data

            registry = SkillRegistryLoader().load(
                load(policy.registry_artifact_version_id, policy.registry_content_hash)
            )
            for entry in registry.entries:
                load(entry.intake_artifact_version_id, entry.intake_content_hash)
            manifest = None
            if isinstance(args, RequestInvocationArguments):
                raw = load(args.harness_artifact_version_id, args.harness_content_hash)
                manifest = typed(HarnessManifest, json.loads(raw), decode=True)
                if canonical_json_bytes(material(manifest)) != raw:
                    invalid("retained harness must be canonical")
                data = load(args.parameters_artifact_version_id, args.parameters_content_hash)
                args.verify_retained_parameters(data, args.parameters_content_hash, len(data))
            prepared = (policy, registry, manifest, pins)
            return (*prepared, args) if starting else prepared

    def _run(self, principal, command, name, context):
        self._principal(principal)
        if type(command) is not GatewayCommand or command.command_name != name:
            invalid("typed named gateway command required")
        if isinstance(command.arguments, StartInvocationArguments | FinishInvocationArguments):
            self._context(
                principal,
                command,
                context,
                finish=isinstance(command.arguments, FinishInvocationArguments),
            )
        try:
            prepared = self._preflight(principal, command)
            preflight_error = None
        except ResearchBaseError as exc:
            prepared, preflight_error = None, exc
        except (OSError, ValueError, TypeError, KeyError):
            prepared = None
            preflight_error = ResearchBaseError(
                ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "retained material unavailable"
            )
        args = command.arguments
        ids: dict[str, Any] = {
            key: new_uuid7() for key in ("receipt", "reservation", "event", "task_event", "usage")
        }
        ids["permissions"] = tuple(
            new_uuid7()
            for _ in (
                args.policy.permissions if isinstance(args, RegisterToolPolicyArguments) else ()
            )
        )
        ids["refs"] = tuple(
            new_uuid7()
            for _ in (
                args.input_refs
                if isinstance(args, RequestInvocationArguments)
                else args.output_refs
                if isinstance(args, FinishInvocationArguments)
                else ()
            )
        )
        for attempt in range(3):
            try:
                runner = (
                    self._lifecycle_once
                    if isinstance(args, StartInvocationArguments | FinishInvocationArguments)
                    else self._once
                )
                return runner(principal, command, context, ids, prepared, preflight_error)
            except _SavedReplay as saved:
                return saved.result
            except UncertainTaskCommit:
                saved = self.replay_gateway(principal, command)
                if saved is not None:
                    return saved
                raise
            except ResearchBaseError as exc:
                if attempt == 2 or not (exc.details or {}).get("retryable_pr301"):
                    raise
        raise AssertionError("unreachable")

    def replay_gateway(self, principal, command):
        self._principal(principal)
        with self._factory() as uow:
            uow.begin_formal_read()
            repo = uow.gateway
            self._authorize(repo, principal, command.project_id)
            receipt = repo.gateway_receipt(
                command.project_id, principal.actor_id, command.command_id
            )
            return self._saved(repo, receipt, command.request_hash(principal.actor_id))

    @staticmethod
    def _saved(repo, receipt, digest):
        if receipt is None:
            return None
        if receipt["request_hash"] != digest:
            fail(ErrorCode.IDEMPOTENCY_CONFLICT, "command material differs from saved request")
        return repo.gateway_result(receipt, replayed=True)

    def _validate_input_refs(self, uow, project, saved_rows, refs):
        # Preserve saved-input order, then command-input order, including failures.
        bindings = []
        reference_error = None
        for row in saved_rows:
            try:
                bindings.append((self._reference(row), row))
            except ResearchBaseError as exc:
                reference_error = exc
                break
        command_bindings = (
            (
                TaskInput(InputType(ref.family), ref.version_id),
                {"content_hash": ref.content_hash, "hash_scheme": ref.hash_scheme},
            )
            for ref in refs
        )
        keys = [(ref.type, ref.id) for ref, _ in bindings]
        if reference_error is None:
            # Collect raw lookup keys without constructing later bindings before
            # earlier refs have resolved. Unknown families fail at their own turn.
            keys.extend((ref.family, ref.version_id) for ref in refs if ref.family in InputType)
        rows = uow.research_tasks.input_versions(tuple(keys), project) if keys else {}

        def input_version(kind, identity, requested_project):
            assert requested_project == project
            return rows.get((kind, identity))

        overrides: dict[str, Any] = {
            "research_tasks": _InputValidationReads(uow.research_tasks, input_version=input_version)
        }
        if hasattr(uow, "manuscript_freeze"):

            def artifact(identity, requested_project):
                key = ("ARTIFACT_VERSION", identity)
                if requested_project == project and key in rows:
                    row = rows[key]
                    return row if row["scoped"] else None
                return uow.manuscript_freeze.artifact(identity, requested_project)

            overrides["manuscript_freeze"] = _InputValidationReads(
                uow.manuscript_freeze, artifact=artifact
            )
        view = _InputValidationReads(uow, **overrides)
        ordered = chain(bindings, command_bindings if reference_error is None else ())
        collected = []
        binding_error = None
        try:
            collected.extend(ordered)
        except (ValueError, ResearchBaseError) as exc:
            binding_error = exc
        ordered = collected
        # Construct an independent graph through the owning service's public API.
        # Neither discovery nor snapshots survive this validation pass.
        snapshot = _GatewayValiditySnapshot(project)
        verifier = self._verifier.with_governance(snapshot)
        for ref, saved in ordered:
            try:
                self._resolve(view, project, ref, saved, verifier=verifier)
            except ResearchBaseError:
                # Replay the original order with real facts below. A later resolver
                # error must never jump ahead of an earlier owning-material error.
                pass
        snapshot.projections = (
            uow.gateway.input_validity_projections(
                project, tuple(snapshot.targets), defer_errors=True
            )
            if snapshot.targets
            else {}
        )
        for ref, saved in ordered:
            self._resolve(view, project, ref, saved, verifier=verifier)
        if reference_error is not None:
            raise reference_error
        if binding_error is not None:
            raise binding_error

    def _once(self, principal, command, context, ids, prepared, preflight_error):
        args = command.arguments
        request = isinstance(args, RequestInvocationArguments)
        with self._factory() as uow:
            uow.begin_gateway_command()
            repo = uow.gateway
            digest = command.request_hash(principal.actor_id)
            ready = False
            written = False
            at = None

            def fresh():
                self._authorize(repo, principal, command.project_id)
                receipt = repo.committed_receipt(
                    command.project_id, principal.actor_id, command.command_id
                )
                saved = self._saved(repo, receipt, digest)
                if saved is not None:
                    raise _SavedReplay(saved)
                if ready:
                    self._admit(
                        uow,
                        repo,
                        principal,
                        command,
                        context,
                        ids,
                        prepared,
                        written=written,
                        provenance_at=at,
                    )

            repo.lock_gateway(
                command.project_id,
                principal.actor_id,
                command.command_id,
                command.task_id,
                agent_version=args.agent_version_id if request else None,
                after_wait=fresh,
            )
            fresh()
            if preflight_error is not None:
                raise preflight_error
            ready = True
            task, at = self._admit(uow, repo, principal, command, context, ids, prepared)
            # This one advancing DB observation is the provenance time on every new row.
            revision = task["row_version"] + 1
            repo.update_task(task["id"], {"row_version": revision})
            written = True
            fresh()
            pointers = {
                "result_tool_policy_id": args.policy_id,
                "result_capability_invocation_id": args.invocation_id if request else None,
                "result_capability_event_id": ids["event"] if request else None,
            }
            receipt = {
                "id": ids["receipt"],
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
                **pointers,
                "resulting_invocation_revision": 1 if request else None,
            }

            def insert(table, row):
                repo.insert(table, row)
                fresh()

            insert("research_task_command_receipts", receipt)
            flags: Any = dict.fromkeys(
                (
                    "stop_human",
                    "stop_policy",
                    "stop_budget",
                    "stop_repeated_failure",
                    "stop_no_improvement",
                    "stop_success",
                ),
                False,
            )
            if request:
                reservation, flags = self._accounting.reserve_in_uow(
                    repo,
                    task,
                    args,
                    at,
                    receipt_id=ids["receipt"],
                    reservation_id=ids["reservation"],
                    capability=context.consumer_capability,
                )
                fresh()
                invocation = {
                    key: getattr(args, key)
                    for key in (
                        "agent_version_id",
                        "policy_id",
                        "policy_content_hash",
                        "step_id",
                        "capability_id",
                        "capability_version",
                        "operation",
                        "adapter_id",
                        "adapter_version",
                        "parameter_schema_hash",
                        "skill_id",
                        "skill_version",
                        "strategy_id",
                        "strategy_version",
                        "harness_artifact_version_id",
                        "harness_content_hash",
                        "parameters_artifact_version_id",
                        "parameters_content_hash",
                        "requested_parameters_hash",
                        "parameters_byte_size",
                        "retry_parent_id",
                    )
                }
                version = repo.agent_version(args.agent_version_id)
                invocation.update(
                    id=args.invocation_id,
                    project_id=command.project_id,
                    research_task_id=task["id"],
                    agent_actor_id=version["actor_id"],
                    requested_by=principal.actor_id,
                    mode="CONTRACT_FAKE",
                    reservation_id=reservation["id"],
                    usage_record_id=None,
                    trace_artifact_version_id=None,
                    trace_content_hash=None,
                    status="REQUESTED",
                    row_version=1,
                    created_at=at,
                    started_at=None,
                    finished_at=None,
                    request_receipt_id=ids["receipt"],
                    start_receipt_id=None,
                    finish_receipt_id=None,
                    result_summary=None,
                    error_code=None,
                )
                insert("capability_invocations", invocation)
                for identity, ref in zip(ids["refs"], args.input_refs, strict=True):
                    insert(
                        "capability_invocation_refs",
                        {
                            "id": identity,
                            "project_id": command.project_id,
                            "research_task_id": task["id"],
                            "invocation_id": args.invocation_id,
                            "receipt_id": ids["receipt"],
                            "direction": "INPUT",
                            **dict.fromkeys(_INPUT_COLUMNS.values()),
                            _INPUT_COLUMNS[ref.family]: ref.version_id,
                            "content_hash": ref.content_hash,
                            "hash_scheme": ref.hash_scheme,
                        },
                    )
                insert(
                    "capability_invocation_events",
                    {
                        "id": ids["event"],
                        "project_id": command.project_id,
                        "research_task_id": task["id"],
                        "invocation_id": args.invocation_id,
                        "reservation_id": reservation["id"],
                        "receipt_id": ids["receipt"],
                        "sequence": 1,
                        "invocation_row_version": 1,
                        "event_type": "REQUESTED",
                        "prior_status": None,
                        "new_status": "REQUESTED",
                        "reconciled_outcome": None,
                        "usage_record_id": None,
                        "actor_id": principal.actor_id,
                        "occurred_at": at,
                        "reason": args.reason,
                    },
                )
            else:
                policy = asdict(args.policy)
                del policy["permissions"]
                insert(
                    "agent_tool_policies",
                    {
                        "id": args.policy_id,
                        "project_id": command.project_id,
                        "registration_task_id": task["id"],
                        "receipt_id": ids["receipt"],
                        **policy,
                        "content_hash": args.policy.digest(command.project_id),
                        "hash_scheme": "sha256-cjson-v1",
                        "created_by": principal.actor_id,
                        "created_at": at,
                    },
                )
                for identity, permission in zip(
                    ids["permissions"], args.policy.permissions, strict=True
                ):
                    insert(
                        "agent_tool_policy_permissions",
                        {
                            "id": identity,
                            "policy_id": args.policy_id,
                            "project_id": command.project_id,
                            **asdict(permission),
                        },
                    )
            insert(
                "research_task_events",
                {
                    "id": ids["task_event"],
                    "research_task_id": task["id"],
                    "actor_id": principal.actor_id,
                    "command_id": command.command_id,
                    "event_type": "CAPABILITY_REQUESTED" if request else "TOOL_POLICY_REGISTERED",
                    "sequence": revision,
                    "task_row_version": revision,
                    "prior_status": task["status"],
                    "new_status": task["status"],
                    "reason": args.reason,
                    "occurred_at": at,
                    **flags,
                    **pointers,
                },
            )
            insert(
                "research_task_receipt_events",
                {
                    "receipt_id": ids["receipt"],
                    "research_task_id": task["id"],
                    "event_id": ids["task_event"],
                },
            )
            repo.force_constraints()
            fresh()
            result = repo.gateway_result(receipt, replayed=False)
            uow.commit()
            return result

    def _start_admission(self, uow, repo, principal, command, context, invocation, prepared, at):
        task = self._scoped(repo, command.project_id, command.task_id)
        if task["status"] not in ("CREATED", "PLANNING"):
            fail(ErrorCode.INVALID_STATE_TRANSITION, "nonterminal planning task required")
        self._authorize(repo, principal, command.project_id, write=True)
        policy, registry, manifest, pins, request = prepared
        for identity, (digest, size) in pins.items():
            if self._pin(repo, command.project_id, identity, digest)["byte_size"] != size:
                fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "retained size changed")
        row, current = policy_spec(repo, command.project_id, invocation["policy_id"])
        if current != policy:
            fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "preflight policy changed")
        version = repo.agent_version(invocation["agent_version_id"])
        if version is None:
            fail(ErrorCode.NOT_FOUND, "AgentVersion unavailable")
        if not repo.live_agent(version["actor_id"], command.project_id):
            fail(ErrorCode.FORBIDDEN, "live enrolled Agent required")
        availability = repo.agent_availability(invocation["agent_version_id"])
        if availability is None:
            fail(ErrorCode.FORBIDDEN, "active Agent required")
        dto = AgentVersionDTO(
            **version,
            current_availability=AgentAvailabilityDTO(
                **{f.name: availability[f.name] for f in fields(AgentAvailabilityDTO)}
            ),
        )
        rows = {table: repo.rows(table, task["id"]) for table in SAFETY_TABLES}
        verify_saved_policies(repo, command.project_id, rows)
        budget = next(r for r in rows["execution_budgets"] if r["id"] == task["budget_policy_id"])
        term = next(
            r for r in rows["termination_policies"] if r["id"] == task["termination_policy_id"]
        )
        checkpoint = next(
            r for r in rows["checkpoint_policies"] if r["id"] == task["checkpoint_policy_id"]
        )
        reservation = next(
            r for r in rows["budget_reservations"] if r["id"] == invocation["reservation_id"]
        )
        origin = min(r["created_at"] for r in rows["budget_reservations"])
        if at >= reservation["deadline"] or at >= origin + timedelta(
            seconds=budget["max_wall_time_seconds"]
        ):
            fail(ErrorCode.INVALID_STATE_TRANSITION, "reservation or task deadline elapsed")
        if (
            task["autonomy_level"] > checkpoint["maximum_autonomy"]
            or task["autonomy_level"] in ("A2", "A3")
            or any(
                not g.satisfied
                for g in gates(
                    checkpoint, rows["human_checkpoints"], at, invocation["step_id"], FAKE_RESOURCES
                )
            )
        ):
            fail(ErrorCode.INVALID_STATE_TRANSITION, "checkpoint or autonomy blocked")
        consumed, reserved = balances(rows["budget_reservations"], rows["budget_usage_records"])
        if any(consumed[k] + reserved[k] > budget["max_" + k] for k in ADDITIVE):
            fail(ErrorCode.INVALID_STATE_TRANSITION, "budget exceeded")
        depth, occupancy = reservation_gauges(repo, task, rows, invocation["step_id"])
        if depth > budget["max_tree_depth"] or occupancy - 1 > budget["max_parallel_branches"]:
            fail(ErrorCode.INVALID_STATE_TRANSITION, "budget gauge exceeded")
        flags = causes(budget, term, rows["budget_reservations"], rows["budget_usage_records"], at)
        request_events = [
            e
            for e in repo.gateway_task_events(task["id"])
            if e.get("result_capability_invocation_id") == invocation["id"]
            and e["event_type"] == "CAPABILITY_REQUESTED"
            and e.get("result_capability_event_id") is not None
        ]
        own = request_events[0] if len(request_events) == 1 else None
        receipt = (
            repo.gateway_receipt(command.project_id, invocation["requested_by"], own["command_id"])
            if own is not None
            else None
        )
        if not (
            own
            and receipt
            and receipt["id"] == invocation["request_receipt_id"]
            and receipt["command_name"] == "request_capability_invocation"
            and receipt["command_id"] == own["command_id"]
            and receipt["result_capability_event_id"] == own["result_capability_event_id"]
        ):
            own = None
        # Ignore only the first stop, on this request, caused solely by its own capacity.
        without = [r for r in rows["budget_reservations"] if r["id"] != reservation["id"]]
        attributable = (
            own is not None
            and own.get("stop_budget", False)
            and flags["stop_budget"]
            and not any(causes(budget, term, without, rows["budget_usage_records"], at).values())
        )
        for event in repo.events(task["id"]):
            if any(event.get(k, False) for k in flags):
                if not (
                    attributable
                    and own is not None
                    and event["id"] == own["id"]
                    and all(not event.get(k, False) for k in flags if k != "stop_budget")
                ):
                    fail(ErrorCode.INVALID_STATE_TRANSITION, "task stopped")
        if any(v for k, v in flags.items() if k != "stop_budget") or (
            flags["stop_budget"] and not attributable
        ):
            fail(ErrorCode.INVALID_STATE_TRANSITION, "task stopped")
        self._validate_input_refs(
            uow,
            command.project_id,
            repo.inputs(task["id"]) + repo.inputs(task["id"], step=True),
            request.input_refs,
        )
        invocations = repo.task_invocations(command.project_id, task["id"])
        occupied = sum(
            i["status"] in ("REQUESTED", "RUNNING", "UNKNOWN_OUTCOME")
            and not any(
                u["is_final"] and u["reservation_id"] == i["reservation_id"]
                for u in rows["budget_usage_records"]
            )
            for i in invocations
        )
        SkillRouter().select(
            request,
            context,
            dto,
            CapabilityPolicy(
                command.project_id, invocation["policy_id"], row["content_hash"], current
            ),
            registry,
            FrozenArtifactPin(
                policy.registry_artifact_version_id,
                command.project_id,
                policy.registry_content_hash,
                True,
            ),
            tuple(
                FrozenArtifactPin(
                    e.intake_artifact_version_id, command.project_id, e.intake_content_hash, True
                )
                for e in {e.intake_artifact_version_id: e for e in registry.entries}.values()
            ),
            manifest,
            RoutingPolicy(3, True, True, True, len(invocations) - 1, occupied - 1),
            self._consumer_capability,
        )

    def _lifecycle_once(self, principal, command, context, ids, prepared, preflight_error):
        args = command.arguments
        starting = isinstance(args, StartInvocationArguments)
        with self._factory() as uow:
            uow.begin_gateway_command()
            repo = uow.gateway
            ready = written = invocation_written = False
            original = None
            digest = command.request_hash(principal.actor_id)

            def fresh():
                at = self._authorize(repo, principal, command.project_id)
                self._context(principal, command, context, finish=not starting)
                saved = self._saved(
                    repo,
                    repo.committed_receipt(
                        command.project_id, principal.actor_id, command.command_id
                    ),
                    digest,
                )
                if saved is not None:
                    raise _SavedReplay(saved)
                if starting:
                    self._authorize(repo, principal, command.project_id, write=True)
                else:
                    task = self._scoped(repo, command.project_id, command.task_id)
                    stopped = task_stopped(repo, task, ignored_event=ids["task_event"])
                    if not stopped:
                        self._authorize(repo, principal, command.project_id, write=True)
                if not ready:
                    return at
                assert original is not None
                self._context(principal, command, context, original, finish=not starting)
                task = self._scoped(repo, command.project_id, command.task_id)
                if task["row_version"] != command.expected_row_version + int(written):
                    fail(ErrorCode.CONCURRENT_MODIFICATION, "stale task revision")
                current = repo.invocation(command.project_id, command.task_id, args.invocation_id)
                if current is None:
                    fail(ErrorCode.CONCURRENT_MODIFICATION, "invocation unavailable")
                delta = int(invocation_written and not reconcile)
                if current["row_version"] != args.expected_invocation_revision + delta:
                    fail(ErrorCode.CONCURRENT_MODIFICATION, "stale invocation revision")
                if invocation_written and not reconcile:
                    owner = current["start_receipt_id" if starting else "finish_receipt_id"]
                    if owner != ids["receipt"]:
                        fail(ErrorCode.CONCURRENT_MODIFICATION, "invocation changed")
                elif current != original:
                    fail(ErrorCode.CONCURRENT_MODIFICATION, "invocation changed")
                usage = [
                    u
                    for u in repo.rows("budget_usage_records", command.task_id)
                    if u["reservation_id"] == original["reservation_id"]
                    and u["receipt_id"] != ids["receipt"]
                ]
                if any(u["is_final"] for u in usage):
                    fail(ErrorCode.INVALID_STATE_TRANSITION, "reservation already final")
                reservation = next(
                    (
                        r
                        for r in repo.rows("budget_reservations", task["id"])
                        if r["id"] == original["reservation_id"]
                    ),
                    None,
                )
                if reservation is None or (
                    reservation["operation_id"],
                    reservation["step_id"],
                    reservation["budget_id"],
                    reservation["receipt_id"],
                ) != (
                    original["id"],
                    original["step_id"],
                    task["budget_policy_id"],
                    original["request_receipt_id"],
                ):
                    fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "reservation ownership disagrees")
                if starting:
                    self._start_admission(
                        uow, repo, principal, command, context, original, prepared, at
                    )
                else:
                    if task["status"] not in ("CREATED", "PLANNING", "CANCELLED"):
                        fail(ErrorCode.INVALID_STATE_TRANSITION, "task bookkeeping unavailable")
                    for ref in args.output_refs:
                        self._pin(repo, command.project_id, ref.version_id, ref.content_hash)
                    if args.trace_artifact_version_id is not None:
                        self._pin(
                            repo,
                            command.project_id,
                            args.trace_artifact_version_id,
                            args.trace_content_hash,
                        )
                    refs = [
                        r
                        for r in repo.invocation_refs(
                            command.project_id, command.task_id, args.invocation_id
                        )
                        if r["receipt_id"] != ids["receipt"]
                    ]
                    if len(refs) + len(args.output_refs) > 256:
                        invalid("total invocation refs exceeded")
                return at

            repo.lock_gateway(
                command.project_id,
                principal.actor_id,
                command.command_id,
                command.task_id,
                invocation_id=args.invocation_id,
                after_wait=fresh,
            )
            fresh()
            if preflight_error is not None:
                raise preflight_error
            original = repo.invocation(command.project_id, command.task_id, args.invocation_id)
            if original is None:
                fail(ErrorCode.NOT_FOUND, "invocation unavailable")
            original = dict(original)
            reconcile = not starting and args.kind == "RECONCILE"
            ready = True
            at = fresh()
            if starting:
                allowed = original["status"] == "REQUESTED"
            elif reconcile:
                allowed = original["status"] == "UNKNOWN_OUTCOME" and not any(
                    e["event_type"] == "RECONCILED"
                    for e in repo.invocation_events(
                        command.project_id, command.task_id, args.invocation_id
                    )
                )
            else:
                allowed = original["status"] == "RUNNING" or (
                    original["status"] == "REQUESTED" and args.outcome == "CANCELLED"
                )
            if not allowed:
                fail(ErrorCode.INVALID_STATE_TRANSITION, "invocation lifecycle edge denied")
            if not starting:
                expected = fake_measurement(args.outcome)
                if args.measured != expected:
                    invalid("trusted fake measurement disagrees")
            task = self._scoped(repo, command.project_id, command.task_id)
            revision = task["row_version"] + 1
            invocation_revision = original["row_version"] + int(not reconcile)
            event_type = "STARTED" if starting else "RECONCILED" if reconcile else "FINISHED"
            pointers = dict(
                result_tool_policy_id=original["policy_id"],
                result_capability_invocation_id=original["id"],
                result_capability_event_id=ids["event"],
            )
            receipt = dict(
                id=ids["receipt"],
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
                resulting_invocation_revision=invocation_revision,
                **pointers,
            )
            repo.update_task(task["id"], {"row_version": revision})
            written = True
            fresh()

            def insert(table, row):
                repo.insert(table, row)
                fresh()

            insert("research_task_command_receipts", receipt)
            flags = dict.fromkeys(
                (
                    "stop_human",
                    "stop_policy",
                    "stop_budget",
                    "stop_repeated_failure",
                    "stop_no_improvement",
                    "stop_success",
                ),
                False,
            )
            usage = None
            if not starting:
                usage, flags = self._accounting.settle_in_uow(
                    repo,
                    task,
                    original,
                    args,
                    at,
                    receipt_id=ids["receipt"],
                    usage_id=ids["usage"],
                    capability=context.consumer_capability,
                )
                fresh()
            status = "RUNNING" if starting else original["status"] if reconcile else args.outcome
            if not reconcile:
                values = dict(status=status, row_version=invocation_revision)
                if starting:
                    values.update(started_at=at, start_receipt_id=ids["receipt"])
                else:
                    assert usage is not None
                    values.update(
                        finished_at=at,
                        finish_receipt_id=ids["receipt"],
                        usage_record_id=usage["id"],
                        trace_artifact_version_id=args.trace_artifact_version_id,
                        trace_content_hash=args.trace_content_hash,
                        result_summary=args.result_summary,
                        error_code=args.error_code,
                    )
                repo.update_invocation(original["id"], original["row_version"], values)
                invocation_written = True
                fresh()
            insert(
                "capability_invocation_events",
                dict(
                    id=ids["event"],
                    project_id=command.project_id,
                    research_task_id=task["id"],
                    invocation_id=original["id"],
                    reservation_id=original["reservation_id"],
                    receipt_id=ids["receipt"],
                    sequence=4 if reconcile else invocation_revision,
                    invocation_row_version=invocation_revision,
                    event_type=event_type,
                    prior_status=original["status"],
                    new_status=status,
                    reconciled_outcome=(
                        args.outcome
                        if reconcile and isinstance(args, FinishInvocationArguments)
                        else None
                    ),
                    usage_record_id=usage["id"] if usage else None,
                    actor_id=principal.actor_id,
                    occurred_at=at,
                    reason=args.reason,
                ),
            )
            if not starting:
                for identity, ref in zip(ids["refs"], args.output_refs, strict=True):
                    insert(
                        "capability_invocation_refs",
                        dict(
                            id=identity,
                            project_id=command.project_id,
                            research_task_id=task["id"],
                            invocation_id=original["id"],
                            receipt_id=ids["receipt"],
                            direction="OUTPUT",
                            **{
                                **dict.fromkeys(_INPUT_COLUMNS.values()),
                                "artifact_version_id": ref.version_id,
                            },
                            content_hash=ref.content_hash,
                            hash_scheme=ref.hash_scheme,
                        ),
                    )
            insert(
                "research_task_events",
                dict(
                    id=ids["task_event"],
                    research_task_id=task["id"],
                    actor_id=principal.actor_id,
                    command_id=command.command_id,
                    event_type="CAPABILITY_STARTED" if starting else "CAPABILITY_FINISHED",
                    sequence=revision,
                    task_row_version=revision,
                    prior_status=task["status"],
                    new_status=task["status"],
                    reason=args.reason,
                    occurred_at=at,
                    **flags,
                    **pointers,
                ),
            )
            insert(
                "research_task_receipt_events",
                dict(
                    receipt_id=ids["receipt"],
                    research_task_id=task["id"],
                    event_id=ids["task_event"],
                ),
            )
            repo.force_constraints()
            fresh()
            result = repo.gateway_result(receipt, replayed=False)
            uow.commit()
            return result

    def _registration_authority(self, repo, principal, project):
        at = self._authorize(repo, principal, project, write=True)
        if not any(
            r["actor_type"] == "HUMAN"
            and r["role"] == "OWNER"
            and r["retired_at"] is None
            and r["binding_status"] == "ACTIVE"
            and r["membership_status"] == "ACTIVE"
            and r["effective_from"] <= at
            and (r["effective_until"] is None or at < r["effective_until"])
            and r["bound_at"] <= at
            and (r["revoked_at"] is None or at < r["revoked_at"])
            for r in repo.authority(principal, project)
        ):
            fail(ErrorCode.FORBIDDEN, "current Human OWNER required")
        return at

    def _admit(
        self,
        uow,
        repo,
        principal,
        command,
        context,
        ids,
        prepared,
        *,
        written=False,
        provenance_at=None,
    ):
        args = command.arguments
        request = isinstance(args, RequestInvocationArguments)
        at = (
            self._authorize(repo, principal, command.project_id, write=True)
            if request
            else self._registration_authority(repo, principal, command.project_id)
        )
        task = self._scoped(repo, command.project_id, command.task_id)
        if task["row_version"] != command.expected_row_version + int(written):
            fail(ErrorCode.CONCURRENT_MODIFICATION, "stale task revision")
        if task["status"] not in ("CREATED", "PLANNING"):
            fail(ErrorCode.INVALID_STATE_TRANSITION, "nonterminal planning task required")
        policy, registry, manifest, pins = prepared
        for identity, (digest, size) in pins.items():
            row = self._pin(repo, command.project_id, identity, digest)
            if row["byte_size"] != size:
                fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "retained size changed")
        if not request:
            occupied = repo.policy(command.project_id, args.policy_id)
            if (
                repo.gateway_identity_occupied("agent_tool_policies", args.policy_id)
                and not (written and occupied and occupied["receipt_id"] == ids["receipt"])
            ) or (
                repo.policy_version_occupied(command.project_id, policy.version)
                and not (written and occupied and occupied["receipt_id"] == ids["receipt"])
            ):
                fail(ErrorCode.CONCURRENT_MODIFICATION, "policy identity or version occupied")
            return task, at
        if type(context) is not AgentExecutionContext or not self._trusted(
            context.consumer_capability
        ):
            fail(ErrorCode.FORBIDDEN, "trusted in-process context required")
        if (
            context.principal != principal
            or context.project_id != command.project_id
            or context.task_id != command.task_id
        ):
            fail(ErrorCode.FORBIDDEN, "trusted context scope disagrees")
        version = repo.agent_version(args.agent_version_id)
        if version is None:
            fail(ErrorCode.NOT_FOUND, "AgentVersion unavailable")
        if version["project_id"] != command.project_id or not repo.live_agent(
            version["actor_id"], command.project_id
        ):
            fail(ErrorCode.FORBIDDEN, "live enrolled Agent required")
        availability = repo.agent_availability(args.agent_version_id)
        if availability is None:
            fail(ErrorCode.FORBIDDEN, "active Agent required")
        dto = AgentVersionDTO(
            **version,
            current_availability=AgentAvailabilityDTO(
                **{f.name: availability[f.name] for f in fields(AgentAvailabilityDTO)}
            ),
        )
        row, current_policy = policy_spec(repo, command.project_id, args.policy_id)
        if current_policy != policy:
            fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "preflight policy changed")
        invocations = repo.task_invocations(command.project_id, command.task_id)
        prior = [i for i in invocations if i["request_receipt_id"] != ids["receipt"]]
        own = next((i for i in invocations if i["id"] == args.invocation_id), None)
        if repo.gateway_identity_occupied("capability_invocations", args.invocation_id) and not (
            written and own and own["request_receipt_id"] == ids["receipt"]
        ):
            fail(ErrorCode.CONCURRENT_MODIFICATION, "invocation identity occupied")
        if args.retry_parent_id is not None:
            parent = next((i for i in prior if i["id"] == args.retry_parent_id), None)
            final = [
                u
                for u in repo.rows("budget_usage_records", task["id"])
                if parent and u["reservation_id"] == parent["reservation_id"] and u["is_final"]
            ]
            if not parent or parent["status"] not in ("FAILED", "UNKNOWN_OUTCOME") or not final:
                fail(ErrorCode.INVALID_STATE_TRANSITION, "prior final failure required")
        self._validate_input_refs(
            uow,
            command.project_id,
            repo.inputs(task["id"]) + repo.inputs(task["id"], step=True),
            args.input_refs,
        )
        self._accounting.prepare(
            repo,
            task,
            args,
            at,
            receipt_id=ids["receipt"],
            capability=context.consumer_capability,
            event_id=ids["task_event"],
        )
        if provenance_at is not None:
            # Advancing checks do not extend the originally admitted reservation deadline.
            if at >= provenance_at + timedelta(seconds=args.deadline_seconds):
                fail(ErrorCode.INVALID_STATE_TRANSITION, "reservation deadline elapsed")
        SkillRouter().select(
            args,
            context,
            dto,
            CapabilityPolicy(
                command.project_id, args.policy_id, row["content_hash"], current_policy
            ),
            registry,
            FrozenArtifactPin(
                policy.registry_artifact_version_id,
                command.project_id,
                policy.registry_content_hash,
                True,
            ),
            tuple(
                FrozenArtifactPin(
                    e.intake_artifact_version_id, command.project_id, e.intake_content_hash, True
                )
                for e in {e.intake_artifact_version_id: e for e in registry.entries}.values()
            ),
            manifest,
            RoutingPolicy(
                3,
                True,
                True,
                True,
                len(prior),
                sum(
                    i["status"] in ("REQUESTED", "RUNNING", "UNKNOWN_OUTCOME")
                    and not any(
                        e["event_type"] == "RECONCILED"
                        for e in repo.invocation_events(command.project_id, task["id"], i["id"])
                    )
                    for i in prior
                ),
            ),
            self._consumer_capability,
        )
        return task, at


class CapabilityGateway(CapabilityGatewayService):
    """Application implementation of the caller-neutral finite fake gateway port."""
