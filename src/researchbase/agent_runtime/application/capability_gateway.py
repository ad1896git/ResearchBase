"""PR3-03 S4 registration and request commands. No execution or dispatch."""

from __future__ import annotations

import json
from dataclasses import asdict, fields
from datetime import timedelta
from decimal import Decimal
from typing import Any

from researchbase.agent_runtime.application.agent_contracts import (
    AgentAvailabilityDTO,
    AgentVersionDTO,
)
from researchbase.agent_runtime.application.contracts import InputType, TaskInput
from researchbase.agent_runtime.application.gateway_contracts import (
    AgentExecutionContext,
    GatewayCommand,
    RegisterToolPolicyArguments,
    RequestInvocationArguments,
)
from researchbase.agent_runtime.application.research_task import _INPUT_COLUMNS, fail
from researchbase.agent_runtime.application.routing import (
    CapabilityPolicy,
    FrozenArtifactPin,
    RoutingPolicy,
    SkillRegistryLoader,
    SkillRouter,
)
from researchbase.agent_runtime.application.safety_contracts import ReserveBudgetArguments
from researchbase.agent_runtime.application.task_safety import (
    TaskSafetyService,
    causes,
    reservation_gauges,
    reservation_values,
    verify_saved_policies,
)
from researchbase.agent_runtime.domain.capability_invocation import material, typed
from researchbase.agent_runtime.domain.harness_manifest import HarnessManifest
from researchbase.agent_runtime.domain.research_task import invalid
from researchbase.agent_runtime.domain.task_safety import ResourceVector
from researchbase.agent_runtime.domain.tool_policy import PermissionSpec, ToolPolicySpec
from researchbase.agent_runtime.ports.task_repository import UncertainTaskCommit
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
            return policy, registry, manifest, pins

    def _run(self, principal, command, name, context):
        self._principal(principal)
        if type(command) is not GatewayCommand or command.command_name != name:
            invalid("typed named gateway command required")
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
            key: new_uuid7() for key in ("receipt", "reservation", "event", "task_event")
        }
        ids["permissions"] = tuple(
            new_uuid7()
            for _ in (
                args.policy.permissions if isinstance(args, RegisterToolPolicyArguments) else ()
            )
        )
        ids["refs"] = tuple(
            new_uuid7()
            for _ in (args.input_refs if isinstance(args, RequestInvocationArguments) else ())
        )
        for attempt in range(3):
            try:
                return self._once(principal, command, context, ids, prepared, preflight_error)
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
        self._saved_inputs(
            uow, command.project_id, repo.inputs(task["id"]) + repo.inputs(task["id"], step=True)
        )
        for ref in args.input_refs:
            self._resolve(
                uow,
                command.project_id,
                TaskInput(InputType(ref.family), ref.version_id),
                {"content_hash": ref.content_hash, "hash_scheme": ref.hash_scheme},
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
