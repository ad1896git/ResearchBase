"""Transactional recordings of S4 orchestration, not PostgreSQL race evidence."""

from copy import deepcopy
from dataclasses import asdict
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from tests.unit.phase3.test_experiment_search_repository import SAFETY

from researchbase.agent_runtime.application.contracts import CommandResult
from researchbase.agent_runtime.application.experiment_search import ExperimentSearchService
from researchbase.agent_runtime.application.safety_contracts import (
    BudgetSpec,
    CheckpointPolicySpec,
    TerminationSpec,
    material_value,
    policy_hash,
)
from researchbase.agent_runtime.application.search_contracts import (
    CreateSearchArguments,
    SearchCommand,
)
from researchbase.agent_runtime.ports.search_repository import (
    SearchStorageStage,
    StoredSearchWriteRows,
)
from researchbase.agent_runtime.ports.task_repository import UncertainTaskCommit
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.ids import new_uuid7

NOW = datetime(2026, 10, 28, tzinfo=UTC)
WRITE_TABLES = (
    "research_task_command_receipts",
    "experiment_search_sessions",
    "experiment_search_events",
    "research_task_events",
    "research_task_receipt_events",
)
LOCK_STAGES = (
    SearchStorageStage("share"),
    SearchStorageStage("project"),
    SearchStorageStage("command_key"),
    SearchStorageStage("task_key"),
    SearchStorageStage("task_row"),
    SearchStorageStage("read", "research_task_steps"),
    SearchStorageStage("step_row"),
    SearchStorageStage("read", "research_task_step_dependencies"),
    SearchStorageStage("read", "research_task_inputs"),
    SearchStorageStage("read", "research_task_step_inputs"),
    *(SearchStorageStage("read", table) for table in SAFETY),
    *(
        SearchStorageStage("read", table)
        for table in (
            "experiment_search_events",
            "experiment_search_nodes",
            "experiment_search_sessions",
            "hypothesis_versions",
            "experiment_spec_versions",
        )
    ),
)


def label(stage):
    return stage.operation + (":" + stage.table if stage.table else "")


class Fixture:
    def __init__(self):
        self.project, self.task, self.actor = (new_uuid7() for _ in range(3))
        self.principal = VerifiedPrincipal(self.actor, "test", "OS_UID", "1", "test", NOW)
        self.clock = NOW
        self.actor_type, self.role = "HUMAN", "OWNER"
        self.valid = self.active = True
        self.trace: list[Any] = []
        self.writes: list[Any] = []
        self.hook: Any = None
        self.fail_stage: str | None = None
        self.retry_stage: str | None = None
        self.uncertain: str | None = None
        self.open_uows = self.commands = self.commits = self.rollbacks = 0
        self.replay_receipt: Any = None
        self.replay_result: Any = None
        self.tables: dict[str, list[dict[str, Any]]] = {
            name: [] for name in (*SAFETY, *WRITE_TABLES, "experiment_search_nodes")
        }
        self.task_row: dict[str, Any] = dict(
            id=self.task,
            project_id=self.project,
            row_version=1,
            status="PLANNING",
            objective="  Owning task objective e\u0301  ",
            autonomy_level="A0",
            plan_sealed_at=None,
        )
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
            content = spec
            if table == "checkpoint_policies":
                values.pop("allowed_dataset_snapshot_ids")
                values.pop("allowed_metric_version_ids")
                content = material_value(spec)
                content.pop("allowed_dataset_snapshot_ids")
                content.pop("allowed_metric_version_ids")
                content.update(allowed_dataset_snapshots=[], allowed_metric_versions=[])
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
        self.tables["human_checkpoints"].append(
            dict(
                id=new_uuid7(),
                research_task_id=self.task,
                step_id=None,
                checkpoint_type="plan_review",
                status="APPROVED",
                created_at=NOW,
                expires_at=NOW,
            )
        )
        self.references: dict[Any, Any] = {}
        self.owners: dict[Any, Any] = {}
        self.repo = Repository(self)
        self.service = ExperimentSearchService(self.factory, self)

    def is_valid(self, principal, at):
        self.trace.append("credential")
        return self.valid

    def command(self, **changes):
        return SearchCommand(
            changes.pop("project_id", self.project),
            changes.pop("command_id", new_uuid7()),
            changes.pop("task_id", self.task),
            changes.pop("expected_row_version", 1),
            changes.pop("command_name", "create_search_session"),
            changes.pop("arguments", CreateSearchArguments(new_uuid7())),
            **changes,
        )

    def run(self, command=None):
        return self.service.execute(self.principal, command or self.command())

    def factory(self) -> Any:
        return Uow(self)

    def stage(self, stage):
        name = label(stage)
        self.trace.append(("stage", name))
        if self.hook:
            self.hook(stage)
        if self.fail_stage == name:
            raise RuntimeError("injected " + name)
        if self.retry_stage == name:
            self.retry_stage = None
            raise ResearchBaseError(
                ErrorCode.CONCURRENT_MODIFICATION, "transient", {"retryable_pr301": True}
            )
        self.repo.callback(stage)


class Uow:
    def __init__(self, fixture):
        self.f = fixture
        self.experiment_search = self.research_tasks = fixture.repo
        self.hypotheses = self.experiment_specs = SimpleNamespace(
            get_version=lambda identity: fixture.owners.get(identity)
        )
        self.committed = False

    def __enter__(self):
        assert self.f.open_uows == 0, "nested command/UoW"
        self.f.open_uows += 1
        self.saved = deepcopy((self.f.task_row, self.f.tables))
        self.f.repo.own_receipts = set()
        return self

    def begin_experiment_search(self):
        self.f.commands += 1
        self.f.trace.append("command_begin")

    def begin_formal_read(self):
        self.f.trace.append("read_begin")

    def commit(self):
        self.f.repo.before_commit()
        if self.f.uncertain == "rolled_back":
            raise UncertainTaskCommit()
        self.f.trace.append("commit")
        self.f.commits += 1
        self.committed = True
        if self.f.uncertain == "committed":
            raise UncertainTaskCommit()

    def __exit__(self, kind, value, traceback):
        self.f.open_uows -= 1
        if not self.committed:
            self.f.task_row, self.f.tables = self.saved
            self.f.rollbacks += 1
        self.f.repo.own_receipts = set()


class Repository:
    def __init__(self, fixture):
        self.f = fixture
        self.callback: Any = None
        self.own_receipts = set()

    def lock_write(self, project, actor, command, task, *, caller_kind, after_stage, **refs):
        self.callback = after_stage
        for stage in LOCK_STAGES:
            self.f.stage(stage)
            if stage.operation == "share":
                kind = caller_kind() if callable(caller_kind) else caller_kind
                assert kind == self.f.actor_type
            if stage.operation == "task_key" and self.f.actor_type == "AGENT":
                self.f.stage(SearchStorageStage("actor_key"))
        return StoredSearchWriteRows((), (), (), (), ())

    def authority(self, principal, project):
        self.f.trace.append("authority")
        return (
            [
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
            if project == self.f.project
            else []
        )

    def at(self):
        return self.f.clock

    snapshot_at = at

    def project_active(self, project):
        return self.f.active

    def task(self, identity):
        self.f.trace.append("task_read")
        return dict(self.f.task_row) if identity == self.f.task else None

    def rows(self, table, task):
        return deepcopy(self.f.tables[table])

    def events(self, task, *, step=False):
        return self.rows("research_task_events", task)

    def sessions(self, project, task):
        return self.rows("experiment_search_sessions", task)

    def nodes(self, task, session):
        return [
            r
            for r in self.rows("experiment_search_nodes", task)
            if r["search_session_id"] == session
        ]

    def search_events(self, task, session):
        return [
            r
            for r in self.rows("experiment_search_events", task)
            if r["search_session_id"] == session
        ]

    def hypothesis_version(self, identity):
        return deepcopy(self.f.references.get(identity))

    experiment_spec_version = hypothesis_version

    def committed_receipt(self, project, actor, command):
        self.f.trace.append("committed_receipt")
        if self.f.replay_receipt is not None:
            return self.f.replay_receipt
        return next(
            (
                r
                for r in self.f.tables["research_task_command_receipts"]
                if r["id"] not in self.own_receipts
                and (r["project_id"], r["actor_id"], r["command_id"]) == (project, actor, command)
            ),
            None,
        )

    def receipt_history(self, task):
        return self.rows("research_task_command_receipts", task)

    def result(self, receipt, *, replayed):
        if receipt is self.f.replay_receipt:
            return self.f.replay_result
        events = [
            r["event_id"]
            for r in self.f.tables["research_task_receipt_events"]
            if r["receipt_id"] == receipt["id"]
        ]
        return CommandResult(
            receipt["research_task_id"],
            receipt["resulting_row_version"],
            tuple(events),
            (),
            replayed,
        )

    def update_task(self, identity, expected_revision):
        assert self.f.task_row["row_version"] == expected_revision
        self.f.task_row["row_version"] += 1
        self.f.writes.append(("update", identity))
        self.f.stage(SearchStorageStage("update", "research_tasks", identity))

    def insert(self, table, row):
        self.f.tables[table].append(deepcopy(row))
        if table == "research_task_command_receipts":
            self.own_receipts.add(row["id"])
        self.f.writes.append((table, deepcopy(row)))
        self.f.stage(SearchStorageStage("insert", table, row.get("id")))

    def flush(self):
        self.f.stage(SearchStorageStage("flush"))

    def force_constraints(self):
        self.f.stage(SearchStorageStage("constraints"))

    def before_commit(self):
        self.flush()
        self.force_constraints()
        self.f.stage(SearchStorageStage("final"))
