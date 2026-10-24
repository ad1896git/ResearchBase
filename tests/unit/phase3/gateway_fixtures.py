"""Transactional recording doubles for S4; no PostgreSQL atomicity claim."""

from copy import deepcopy
from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

from tests.unit.phase3.test_capability_gateway_contracts import request
from tests.unit.phase3.test_capability_routing import route_inputs

from researchbase.agent_runtime.application.capability_gateway import (
    SAFETY_TABLES,
    CapabilityGatewayService,
)
from researchbase.agent_runtime.application.gateway_contracts import (
    AgentExecutionContext,
    GatewayCommand,
    RegisterToolPolicyArguments,
)
from researchbase.agent_runtime.application.safety_contracts import (
    BudgetSpec,
    CheckpointPolicySpec,
    TerminationSpec,
    material_value,
    policy_hash,
)
from researchbase.agent_runtime.domain.capability_invocation import GatewayRef, material
from researchbase.agent_runtime.ports.task_safety_repository import FakeConsumerCapability
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.canonical_json import canonical_json_bytes
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.hashing import sha256_bytes
from researchbase.foundation.ids import new_uuid7
from researchbase.persistence.capability_gateway_repository import SqlAlchemyGatewayRepository

NOW = datetime(2026, 10, 22, tzinfo=UTC)


class Fixture:
    def __init__(self):
        self.project, self.task, self.actor, self.policy_id, self.version_id = (
            new_uuid7() for _ in range(5)
        )
        self.principal = VerifiedPrincipal(self.actor, "test", "OS_UID", "1", "test", NOW)
        self.consumer = FakeConsumerCapability()
        self.trace: list[Any] = []
        self.open_uows = 0
        self.locked = False
        self.in_command = False
        self.command_transactions = self.commits = 0
        self.role, self.actor_type = "OWNER", "HUMAN"
        self.valid = self.active = self.agent_live = True
        self.clock = NOW
        self.fail_stage = None
        self.retry_stage: str | None = None
        self.wait_hook: Any = None
        self.stage_hook: Any = None
        self.byte_failure = False
        self.new_receipts: list[Any] = []
        self.attempt_writes: list[Any] = []
        self.tables: dict[str, list[dict[str, Any]]] = {
            name: []
            for name in (
                *SAFETY_TABLES,
                "agent_tool_policies",
                "agent_tool_policy_permissions",
                "capability_invocations",
                "capability_invocation_refs",
                "capability_invocation_events",
                "research_task_command_receipts",
                "research_task_events",
                "research_task_receipt_events",
            )
        }
        self.task_row: dict[str, Any] = dict(
            id=self.task,
            project_id=self.project,
            row_version=1,
            status="PLANNING",
            autonomy_level="A0",
            plan_sealed_at=None,
        )
        self.artifacts: dict[Any, Any] = {}
        self.blobs: dict[str, bytes] = {}
        routes = route_inputs()
        self.manifest = routes["manifest"]
        self.harness, self.harness_hash = self.retain(canonical_json_bytes(material(self.manifest)))
        self.intake, intake_hash = self.retain(
            b"Reviewed MIT fake revision; no scripts or data exposure."
        )
        entry = replace(
            routes["registry"].entries[0],
            intake_artifact_version_id=self.intake,
            intake_content_hash=intake_hash,
        )
        self.registry = replace(routes["registry"], entries=(entry,))
        registry_id, registry_hash = self.retain(canonical_json_bytes(material(self.registry)))
        self.policy = replace(
            routes["binding"].policy,
            registry_artifact_version_id=registry_id,
            registry_content_hash=registry_hash,
        )
        parameters = request().parameters
        params_id, params_hash = self.retain(parameters.canonical_bytes())
        self.ref_id, self.ref_hash = self.retain(b"retained candidate input")
        self.args = replace(
            request(),
            invocation_id=new_uuid7(),
            agent_version_id=self.version_id,
            policy_id=self.policy_id,
            policy_content_hash=self.policy.digest(self.project),
            harness_artifact_version_id=self.harness,
            harness_content_hash=self.harness_hash,
            parameters_artifact_version_id=params_id,
            parameters_content_hash=params_hash,
            input_refs=(GatewayRef("RESEARCH_QUESTION_VERSION", self.ref_id, self.ref_hash, None),),
        )
        self.context = AgentExecutionContext(
            self.principal,
            self.project,
            self.task,
            None,
            self.version_id,
            self.harness,
            self.harness_hash,
            self.consumer,
        )
        self.version = asdict(routes["version"])
        del self.version["current_availability"]
        self.version.update(
            id=self.version_id,
            project_id=self.project,
            configuration_artifact_version_id=self.harness,
            configuration_content_hash=self.harness_hash,
            tool_policy_version=self.policy.version,
        )
        self.availability = dict(status="ACTIVE", revision=1, changed_by=self.actor, changed_at=NOW)
        for table, key, spec, envelope in (
            (
                "execution_budgets",
                "budget_policy_id",
                BudgetSpec("fake-usd-v1"),
                "ExecutionBudgetPolicy",
            ),
            (
                "termination_policies",
                "termination_policy_id",
                TerminationSpec(),
                "TerminationPolicy",
            ),
            (
                "checkpoint_policies",
                "checkpoint_policy_id",
                CheckpointPolicySpec(),
                "CheckpointPolicy",
            ),
        ):
            identity = new_uuid7()
            self.task_row[key] = identity
            values = asdict(spec)
            if table == "checkpoint_policies":
                values.pop("allowed_dataset_snapshot_ids")
                values.pop("allowed_metric_version_ids")
                content = material_value(spec)
                content.pop("allowed_dataset_snapshot_ids")
                content.pop("allowed_metric_version_ids")
                content.update(allowed_dataset_snapshots=[], allowed_metric_versions=[])
            else:
                content = spec
            self.tables[table].append(
                dict(
                    id=identity,
                    research_task_id=self.task,
                    receipt_id=new_uuid7(),
                    created_at=NOW,
                    content_hash=policy_hash(envelope, content),
                    hash_scheme="sha256-cjson-v1",
                    **values,
                )
            )
        self.tables["human_checkpoints"] = [
            dict(
                id=new_uuid7(),
                step_id=None,
                checkpoint_type="plan_review",
                status="APPROVED",
                created_at=NOW,
                expires_at=NOW + timedelta(days=1),
            )
        ]
        self.repo: Any = Repository(self)
        self.service = CapabilityGatewayService(
            self.factory, self, self, consumer_capability=self.consumer
        )

    def retain(self, data):
        identity, digest = new_uuid7(), str(sha256_bytes(data))
        self.blobs[digest] = data
        self.artifacts[identity] = dict(
            id=identity,
            content_hash=digest,
            byte_size=len(data),
            project_id=self.project,
            scoped=True,
            status="FROZEN",
            frozen_at=NOW,
        )
        return identity, digest

    def is_valid(self, principal, at):
        self.trace.append(["credential", at])
        return self.valid

    def open(self, digest):
        assert not self.locked, "retained-byte I/O under locks"
        self.trace.append(["bytes", digest])
        if self.byte_failure:
            raise OSError("missing bytes")
        return self.blobs[digest]

    def factory(self):
        return Uow(self)

    def command(self, *, register=False, **changes):
        name = "register_agent_tool_policy" if register else "request_capability_invocation"
        args = (
            RegisterToolPolicyArguments(self.policy_id, self.policy, "register")
            if register
            else self.args
        )
        return GatewayCommand(
            self.project,
            self.task,
            changes.pop("command_id", new_uuid7()),
            changes.pop("expected_row_version", self.task_row["row_version"]),
            name,
            changes.pop("arguments", args),
            **changes,
        )

    def run(self, command=None, *, register=False, context=None):
        command = command or self.command(register=register)
        if register:
            return self.service.register_agent_tool_policy(self.principal, command)
        return self.service.request_capability_invocation(
            self.principal, command, self.context if context is None else context
        )

    def install_policy(self):
        self.run(register=True)
        self.trace.clear()
        self.command_transactions = self.commits = 0
        self.attempt_writes.clear()

    def stage(self, name):
        self.trace.append(["wait", name])
        if self.stage_hook:
            self.stage_hook(name)
        if self.fail_stage == name:
            raise RuntimeError("injected " + name)
        if self.retry_stage == name:
            self.retry_stage = None
            raise ResearchBaseError(
                ErrorCode.CONCURRENT_MODIFICATION, "transient", {"retryable_pr301": True}
            )


class Uow:
    def __init__(self, fixture):
        self.f = fixture
        self.gateway = fixture.repo
        self.research_tasks = fixture.repo
        self.research_questions = SimpleNamespace(
            get_version=lambda identity: SimpleNamespace(content_hash=fixture.ref_hash)
        )
        self.hypotheses = self.claims = self.research_questions
        self.committed = False

    def __enter__(self):
        assert self.f.open_uows == 0, "nested gateway UoW"
        self.f.open_uows += 1
        self.saved = deepcopy((self.f.task_row, self.f.tables))
        return self

    def begin_formal_read(self):
        self.f.trace.append(["formal_read"])

    def begin_gateway_command(self):
        self.f.in_command = True
        self.f.new_receipts = []
        self.f.command_transactions += 1
        self.f.trace.append(["command_begin"])

    def commit(self):
        self.f.stage("commit")
        self.f.commits += 1
        self.committed = True
        self.f.trace.append(["commit"])

    def __exit__(self, kind, value, traceback):
        self.f.open_uows -= 1
        if not self.committed:
            self.f.task_row, self.f.tables = self.saved
        self.f.locked = self.f.in_command = False


class Repository:
    gateway_result = SqlAlchemyGatewayRepository.gateway_result

    def __init__(self, fixture):
        self.f = fixture

    def _many(self, sql, params):
        return [r for r in self.f.tables["capability_invocation_events"] if r["id"] == params["id"]]

    def lock_gateway(
        self,
        project,
        actor,
        command,
        task,
        *,
        agent_version=None,
        invocation_id=None,
        after_wait=None,
    ):
        self.f.locked = True
        if invocation_id is not None:
            target = self.invocation(project, task, invocation_id)
            agent_version = target["agent_version_id"] if target else None
        for stage in (
            "share",
            "project",
            "command",
            "task_key",
            "agent_key",
            "version_key",
            "task_row",
            "steps",
            "checkpoints",
            "availability",
            "invocations",
        ):
            if agent_version is None and stage in ("agent_key", "version_key", "availability"):
                continue
            self.f.trace.append(["lock", stage])
            if self.f.wait_hook:
                self.f.wait_hook(stage)
            if after_wait is not None:
                after_wait()

    def authority(self, principal, project):
        self.f.trace.append(["authority"])
        return [
            dict(
                actor_type=self.f.actor_type,
                retired_at=None,
                binding_status="ACTIVE",
                membership_status="ACTIVE",
                role=self.f.role,
                effective_from=NOW,
                effective_until=None,
                bound_at=NOW,
                revoked_at=None,
            )
        ]

    def project_active(self, project):
        return self.f.active

    def at(self):
        return self.f.clock

    def snapshot_at(self):
        self.f.trace.append(["snapshot_at"])
        return self.f.clock

    def invocation_page(self, project, task, limit, after_at, after_id):
        rows = sorted(
            (
                row
                for row in self.f.tables["capability_invocations"]
                if row["project_id"] == project and row["research_task_id"] == task
            ),
            key=lambda row: (row["created_at"], row["id"]),
        )
        return deepcopy(
            [
                row
                for row in rows
                if after_at is None or (row["created_at"], row["id"]) > (after_at, after_id)
            ][: limit + 1]
        )

    def task(self, identity):
        return dict(self.f.task_row) if identity == self.f.task else None

    def committed_receipt(self, project, actor, command):
        self.f.trace.append(["committed_receipt"])
        saved = self.gateway_receipt(project, actor, command)
        if saved and saved not in self.f.new_receipts:
            return saved
        return None

    def gateway_receipt(self, project, actor, command):
        return next(
            (
                r
                for r in self.f.tables["research_task_command_receipts"]
                if (r["project_id"], r["actor_id"], r["command_id"]) == (project, actor, command)
            ),
            None,
        )

    def artifact_pin(self, project, identity):
        return self.f.artifacts.get(identity)

    def input_version(self, kind, identity, project):
        return self.artifact_pin(project, identity)

    def input_versions(self, refs, project):
        return {
            key: row
            for key in refs
            if (row := self.input_version(key[0], key[1], project)) is not None
        }

    def rows(self, table, task):
        return deepcopy(self.f.tables[table])

    def steps(self, task):
        return []

    def inputs(self, task, *, step=False):
        return []

    def gateway_task_events(self, task):
        return deepcopy(self.f.tables["research_task_events"])

    def events(self, task):
        return deepcopy(self.f.tables["research_task_events"])

    def policy(self, project, identity):
        return next(
            (
                r
                for r in self.f.tables["agent_tool_policies"]
                if r["id"] == identity and r["project_id"] == project
            ),
            None,
        )

    def permissions(self, project, identity):
        return [
            r for r in self.f.tables["agent_tool_policy_permissions"] if r["policy_id"] == identity
        ]

    def policy_version_occupied(self, project, version):
        return any(r["version"] == version for r in self.f.tables["agent_tool_policies"])

    def gateway_identity_occupied(self, table, identity):
        return any(r["id"] == identity for r in self.f.tables[table])

    def task_invocations(self, project, task):
        return deepcopy(self.f.tables["capability_invocations"])

    def invocation(self, project, task, identity):
        return next(
            (
                dict(r)
                for r in self.f.tables["capability_invocations"]
                if (r["project_id"], r["research_task_id"], r["id"]) == (project, task, identity)
            ),
            None,
        )

    def invocation_refs(self, project, task, identity):
        return deepcopy(
            [
                r
                for r in self.f.tables["capability_invocation_refs"]
                if r["invocation_id"] == identity
            ]
        )

    def receipt_history(self, task):
        return deepcopy(self.f.tables["research_task_command_receipts"])

    def update_invocation(self, identity, expected_revision, values):
        row = next(r for r in self.f.tables["capability_invocations"] if r["id"] == identity)
        if row["row_version"] != expected_revision:
            raise ResearchBaseError(ErrorCode.CONCURRENT_MODIFICATION, "stale invocation revision")
        row.update(values)
        self.f.attempt_writes.append(("invocation_update", dict(values)))
        self.f.stage("invocation_update")

    def invocation_events(self, project, task, invocation):
        return [
            r
            for r in self.f.tables["capability_invocation_events"]
            if r["invocation_id"] == invocation
        ]

    def agent_version(self, identity):
        return dict(self.f.version) if identity == self.f.version_id else None

    def agent_availability(self, identity):
        return self.f.availability

    def live_agent(self, actor, project):
        return self.f.agent_live

    def update_task(self, identity, values):
        self.f.task_row.update(values)
        self.f.attempt_writes.append(("task", dict(values)))
        self.f.stage("task")

    def insert(self, table, row):
        if table == "research_task_command_receipts":
            self.f.new_receipts.append(row)
        self.f.tables[table].append(deepcopy(row))
        self.f.attempt_writes.append((table, deepcopy(row)))
        self.f.stage(table)

    def force_constraints(self):
        self.f.stage("constraints")
