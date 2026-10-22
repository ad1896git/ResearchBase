"""Recording sessions prove SQL composition, never live PostgreSQL lock contention."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import cast, get_type_hints
from uuid import UUID

import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from researchbase.agent_runtime.ports import gateway_repository as port
from researchbase.persistence.agent_version_repository import SqlAlchemyAgentRepository
from researchbase.persistence.capability_gateway_repository import SqlAlchemyGatewayRepository
from researchbase.persistence.database import Base
from researchbase.persistence.research_task_repository import SqlAlchemyResearchTaskRepository
from researchbase.persistence.task_safety_repository import SqlAlchemyTaskSafetyRepository
from researchbase.persistence.uow import SqlAlchemyUnitOfWork

P, A, C, T, V, TARGET = (UUID(int=i) for i in range(1, 7))
TABLES = (
    "agent_tool_policies",
    "agent_tool_policy_permissions",
    "capability_invocations",
    "capability_invocation_refs",
    "capability_invocation_events",
)
SAFETY = (
    "budget_reservations",
    "budget_usage_records",
    "checkpoint_policies",
    "checkpoint_policy_dataset_scopes",
    "checkpoint_policy_metric_scopes",
    "execution_budgets",
    "human_checkpoints",
    "termination_policies",
)
SHARE = (
    "LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, "
    "claim_versions, claims, hypothesis_versions, hypotheses, "
    "literature_source_project_links, literature_sources, manuscript_versions, "
    "project_memberships, project_role_assignments, projects, publications, "
    "research_question_versions, research_questions, source_versions IN SHARE MODE"
)


def normalized(sql):
    return " ".join(str(sql).split())


class Result:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return self

    def first(self):
        return self.rows[0] if self.rows else None

    def __iter__(self):
        return iter(self.rows)


class RecordingSession:
    def __init__(self, *, version_exists=True):
        self.trace = []
        self.version_exists = version_exists
        self.results = {}
        self.autoflush = False

    def execute(self, sql, params=None):
        sql = normalized(sql)
        self.trace.append([sql, dict(params or {})])
        rows = self.results.get(sql, [])
        if sql == "SELECT * FROM agent_versions WHERE id=:id" and self.version_exists:
            rows = [{"id": V, "actor_id": TARGET}]
        return Result(rows)

    def after_wait(self):
        self.trace.append(["CALLBACK", {}])


def record(name, expected, actual):
    path = Path(__file__).resolve().parents[3] / "tmp/pr3-03"
    path.mkdir(parents=True, exist_ok=True)
    (path / f"s2-trace-{name}.json").write_text(
        json.dumps({"expected": expected, "actual": actual}, default=str, indent=2) + "\n"
    )
    assert actual == expected


def prefix():
    return [
        [SHARE, {}],
        ["SELECT rb_phase2_lock_project(:id)", {"id": P}],
        [
            "SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",
            {"key": f"pr301:command:{P}:{A}:{C}"},
        ],
        ["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))", {"key": f"pr301:task:{T}"}],
    ]


def task_rows():
    return [
        ["SELECT id FROM research_tasks WHERE id=:id FOR UPDATE", {"id": T}],
        [
            "SELECT id FROM research_task_steps WHERE research_task_id=:id ORDER BY id FOR UPDATE",
            {"id": T},
        ],
        [
            "SELECT predecessor_id,dependent_id FROM research_task_step_dependencies "
            "WHERE research_task_id=:id ORDER BY predecessor_id,dependent_id",
            {"id": T},
        ],
        ["SELECT * FROM research_task_inputs WHERE research_task_id=:id ORDER BY id", {"id": T}],
        [
            "SELECT * FROM research_task_step_inputs WHERE research_task_id=:id ORDER BY id",
            {"id": T},
        ],
    ]


def expected_gateway(*, registration=False):
    trace = prefix()
    version_read = ["SELECT * FROM agent_versions WHERE id=:id", {"id": V}]
    if not registration:
        trace.append(version_read)
        trace.extend(
            ["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))", {"key": key}]
            for key in (f"pr302:actor:{TARGET}", f"pr302:version:{V}")
        )
    trace.extend(task_rows())
    trace.extend(
        [
            f"SELECT * FROM {table} WHERE research_task_id=:id ORDER BY id"
            + (" FOR UPDATE" if table == "human_checkpoints" else ""),
            {"id": T},
        ]
        for table in SAFETY
    )
    if not registration:
        trace.extend(
            [
                [
                    "SELECT * FROM agent_availability WHERE agent_version_id=:id FOR UPDATE",
                    {"id": V},
                ],
                version_read,
            ]
        )
    for table in TABLES:
        scope = "project_id=:project"
        if table.startswith("capability_"):
            scope += " AND research_task_id=:task"
        trace.append(
            [
                f"SELECT * FROM {table} WHERE {scope} ORDER BY id"
                + (" FOR UPDATE" if table == "capability_invocations" else ""),
                {"project": P, "task": T},
            ]
        )
    return trace


def callbacks(trace):
    result = []
    for sql, params in trace:
        result.append([sql, params])
        if (
            sql.startswith("LOCK TABLE")
            or "rb_phase2_lock_project" in sql
            or "pg_advisory_xact_lock" in sql
            or "FOR UPDATE" in sql
        ):
            result.append(["CALLBACK", {}])
    return result


def test_first_statement_is_literal_eighteen_parent_share():
    session = RecordingSession()
    SqlAlchemyGatewayRepository(cast(Session, session)).lock_gateway(P, A, C, T, agent_version=V)
    record("first-statement", [[SHARE, {}]], session.trace[:1])
    assert len(SHARE.split("LOCK TABLE ")[1].split(" IN SHARE")[0].split(",")) == 18


def test_registration_omits_target_actor_version_and_availability():
    session = RecordingSession()
    SqlAlchemyGatewayRepository(cast(Session, session)).lock_gateway(P, A, C, T)
    record("registration", expected_gateway(registration=True), session.trace)


def test_exact_advisory_row_and_table_order():
    session = RecordingSession()
    SqlAlchemyGatewayRepository(cast(Session, session)).lock_gateway(P, A, C, T, agent_version=V)
    record("complete-order", expected_gateway(), session.trace)


@pytest.mark.parametrize("registration", [False, True])
def test_callback_after_every_blocking_acquisition(registration):
    session = RecordingSession()
    SqlAlchemyGatewayRepository(cast(Session, session)).lock_gateway(
        P, A, C, T, agent_version=None if registration else V, after_wait=session.after_wait
    )
    record(
        f"callbacks-{registration}",
        callbacks(expected_gateway(registration=registration)),
        session.trace,
    )


def test_existing_safety_combined_recipe_unchanged():
    session = RecordingSession()
    SqlAlchemyTaskSafetyRepository(cast(Session, session)).lock_write(
        P, A, C, T, after_wait=session.after_wait
    )
    record("safety-compatibility", callbacks(prefix() + task_rows()), session.trace)
    old = RecordingSession()
    SqlAlchemyResearchTaskRepository(cast(Session, old)).lock_write(P, A, C, T)
    assert [entry for entry in session.trace if entry[0] != "CALLBACK"] == old.trace


@pytest.mark.parametrize("stop_at", range(1, 12))
def test_replay_or_denial_callback_can_stop_before_next_sql(stop_at):
    session = RecordingSession()
    calls = 0

    def stop():
        nonlocal calls
        calls += 1
        session.after_wait()
        if calls == stop_at:
            raise RuntimeError("stop at replay or entitlement check")

    with pytest.raises(RuntimeError, match="stop at replay"):
        SqlAlchemyGatewayRepository(cast(Session, session)).lock_gateway(
            P, A, C, T, agent_version=V, after_wait=stop
        )
    expected = callbacks(expected_gateway())
    positions = [i for i, row in enumerate(expected) if row[0] == "CALLBACK"]
    record(f"callback-stop-{stop_at}", expected[: positions[stop_at - 1] + 1], session.trace)


def test_receipt_and_scoped_reads_have_deterministic_order_and_detached_rows():
    session = RecordingSession()
    repository = SqlAlchemyGatewayRepository(cast(Session, session))
    receipt_sql = (
        "SELECT * FROM research_task_command_receipts "
        "WHERE project_id=:project AND actor_id=:actor AND command_id=:command"
    )
    original = {
        "id": C,
        "completed_at": datetime(2026, 1, 1, tzinfo=UTC),
        "result_tool_policy_id": V,
        "result_capability_invocation_id": None,
        "result_capability_event_id": None,
        "resulting_invocation_revision": None,
    }
    session.results[receipt_sql] = [original]
    receipt = repository.gateway_receipt(P, A, C)
    assert receipt == original and receipt is not original
    repository.policy(P, V)
    repository.permissions(P, V)
    repository.invocation(P, T, V)
    repository.invocation_refs(P, T, V)
    repository.invocation_events(P, T, V)
    repository.gateway_task_events(T)
    record(
        "scoped-reads",
        [
            [receipt_sql, {"project": P, "actor": A, "command": C}],
            [
                "SELECT * FROM agent_tool_policies WHERE project_id=:project AND id=:id",
                {"project": P, "id": V},
            ],
            [
                "SELECT * FROM agent_tool_policy_permissions "
                "WHERE project_id=:project AND policy_id=:id "
                "ORDER BY capability_id,capability_version,operation,adapter_id,adapter_version, "
                "parameter_schema_hash,effect",
                {"project": P, "id": V},
            ],
            [
                "SELECT * FROM capability_invocations WHERE project_id=:project "
                "AND research_task_id=:task AND id=:id",
                {"project": P, "task": T, "id": V},
            ],
            [
                "SELECT * FROM capability_invocation_refs WHERE project_id=:project "
                "AND research_task_id=:task AND invocation_id=:id ORDER BY direction, CASE "
                "WHEN research_question_version_id IS NOT NULL THEN 'RESEARCH_QUESTION_VERSION' "
                "WHEN hypothesis_version_id IS NOT NULL THEN 'HYPOTHESIS_VERSION' "
                "WHEN claim_version_id IS NOT NULL THEN 'CLAIM_VERSION' "
                "WHEN source_version_id IS NOT NULL THEN 'SOURCE_VERSION' "
                "WHEN artifact_version_id IS NOT NULL THEN 'ARTIFACT_VERSION' "
                "WHEN manuscript_version_id IS NOT NULL THEN 'MANUSCRIPT_VERSION' END, "
                "coalesce(research_question_version_id,hypothesis_version_id,claim_version_id, "
                "source_version_id,artifact_version_id,manuscript_version_id)",
                {"project": P, "task": T, "id": V},
            ],
            [
                "SELECT * FROM capability_invocation_events WHERE project_id=:project "
                "AND research_task_id=:task AND invocation_id=:id ORDER BY sequence",
                {"project": P, "task": T, "id": V},
            ],
            [
                "SELECT * FROM research_task_events WHERE research_task_id=:task ORDER BY sequence",
                {"task": T},
            ],
        ],
        session.trace,
    )
    assert repository.policy(P, V) is None


def test_no_sql_at_uow_or_adapter_construction():
    session = RecordingSession()
    factory_calls = []

    def factory():
        factory_calls.append(True)
        return cast(Session, session)

    SqlAlchemyUnitOfWork(factory)
    assert not factory_calls
    SqlAlchemyGatewayRepository(cast(Session, session))
    SqlAlchemyTaskSafetyRepository(cast(Session, session))
    SqlAlchemyAgentRepository(cast(Session, session))
    record("construction", [], session.trace)


@pytest.mark.parametrize(
    "table,stored",
    [
        ("agent_tool_policies", port.StoredToolPolicy),
        ("agent_tool_policy_permissions", port.StoredPermission),
        ("capability_invocations", port.StoredInvocation),
        ("capability_invocation_refs", port.StoredInvocationRef),
        ("capability_invocation_events", port.StoredInvocationEvent),
        ("research_task_command_receipts", port.StoredGatewayReceipt),
        ("research_task_events", port.StoredTaskEvent),
    ],
)
def test_closed_stored_columns_match_inert_metadata(table, stored):
    mapped = Base.metadata.tables[table]
    assert set(get_type_hints(stored)) == set(mapped.columns.keys())
    assert stored.__required_keys__ == frozenset(mapped.columns.keys())
    for fk in mapped.foreign_key_constraints:
        assert fk.ondelete == "RESTRICT"
    for column in mapped.columns:
        assert column.default is None


def test_nullable_receipt_event_extensions_are_mapped_and_relationships_deferred():
    from researchbase.persistence.models import (
        ResearchTaskCommandReceiptsModel,
        ResearchTaskEventsModel,
    )

    pointers = {
        "result_tool_policy_id",
        "result_capability_invocation_id",
        "result_capability_event_id",
    }
    for cls in (ResearchTaskCommandReceiptsModel, ResearchTaskEventsModel):
        mapped = inspect(cls)
        expected = pointers | (
            {"resulting_invocation_revision"} if cls is ResearchTaskCommandReceiptsModel else set()
        )
        assert expected <= set(mapped.columns.keys())
        for name in expected:
            assert mapped.columns[name].nullable
    for table, names in (
        (
            "research_task_command_receipts",
            {"pr303_receipt_policy", "pr303_receipt_invocation", "pr303_receipt_event"},
        ),
        (
            "research_task_events",
            {
                "pr303_task_event_policy",
                "pr303_task_event_invocation",
                "pr303_task_event_capability",
            },
        ),
    ):
        assert names <= {index.name for index in Base.metadata.tables[table].indexes}
    receipt = Base.metadata.tables["research_task_command_receipts"]
    for fk in receipt.foreign_key_constraints:
        if isinstance(fk.name, str) and fk.name.startswith("pr303_receipt_"):
            assert fk.deferrable and fk.initially == "DEFERRED"


def test_entering_uow_constructs_gateway_without_sql(monkeypatch):
    session = Session()
    trace = []

    def unexpected(*args, **kwargs):
        trace.append("unexpected SQL")
        raise AssertionError("construction emitted SQL")

    monkeypatch.setattr(session, "execute", unexpected)
    with SqlAlchemyUnitOfWork(lambda: session) as uow:
        assert isinstance(uow.gateway, SqlAlchemyGatewayRepository)
    record("uow-entry", [], trace)


def test_legacy_task_event_projection_preserves_dto_shape_after_0080():
    from researchbase.agent_runtime.application.contracts import TaskEventRead

    session = RecordingSession()
    SqlAlchemyResearchTaskRepository(cast(Session, session)).events(T)
    sql = session.trace[0][0]
    columns = set(sql.split("SELECT ")[1].split(" FROM ")[0].replace(" ", "").split(","))
    assert columns == set(get_type_hints(TaskEventRead))
    assert "result_tool_policy_id" not in columns
    assert not sql.startswith("SELECT *")


def test_committed_receipt_excludes_current_xmin_and_keeps_original_identity():
    from researchbase.persistence.capability_gateway_repository import COMMITTED_RECEIPT_SQL

    session = RecordingSession()
    repository = SqlAlchemyGatewayRepository(cast(Session, session))
    assert repository.committed_receipt(P, A, C) is None
    assert session.trace == [
        [normalized(COMMITTED_RECEIPT_SQL), {"project": P, "actor": A, "command": C}]
    ]
    assert "xmin <> pg_current_xact_id()::xid" in normalized(COMMITTED_RECEIPT_SQL)


def test_request_insert_is_parameterized_and_rejects_unknown_column():
    session = RecordingSession()
    repo = SqlAlchemyGatewayRepository(cast(Session, session))
    row = {"id": V, "project_id": P, "research_task_id": T, "status": "REQUESTED"}
    repo.insert("capability_invocations", row)
    sql, params = session.trace[0]
    assert params == row and str(V) not in sql
    assert sql == (
        "INSERT INTO capability_invocations ( id, project_id, research_task_id, status ) "
        "VALUES ( :id, :project_id, :research_task_id, :status )"
    )
    with pytest.raises(ValueError, match="unknown gateway column"):
        repo.insert("capability_invocations", {"untrusted": True})
    with pytest.raises(ValueError):
        repo.insert("untrusted_table", {"id": V})


def test_saved_gateway_result_uses_receipt_and_event_never_current_invocation():
    from researchbase.persistence.capability_gateway_repository import SAVED_EVENT_SQL

    session = RecordingSession()
    repo = SqlAlchemyGatewayRepository(cast(Session, session))
    stamp = datetime(2026, 10, 22, tzinfo=UTC)
    receipt = dict(
        id=C,
        project_id=P,
        research_task_id=T,
        actor_id=A,
        command_id=C,
        command_name="request_capability_invocation",
        result_tool_policy_id=V,
        result_capability_invocation_id=V,
        result_capability_event_id=TARGET,
        resulting_row_version=5,
        resulting_invocation_revision=1,
        completed_at=stamp,
    )
    session.results[normalized(SAVED_EVENT_SQL)] = [{"reservation_id": T, "usage_record_id": None}]
    result = repo.gateway_result(receipt, replayed=True)
    assert result.reservation_id == T and result.resulting_invocation_revision == 1
    assert result.resulting_row_version == 5 and result.completed_at == stamp
    assert session.trace == [[normalized(SAVED_EVENT_SQL), {"id": TARGET}]]


@pytest.mark.parametrize("gateway", [False, True])
@pytest.mark.parametrize(
    "constraint,expected",
    [
        ("agent_tool_policies_pkey", "CONCURRENT_MODIFICATION"),
        ("agent_tool_policies_project_id_version_key", "CONCURRENT_MODIFICATION"),
        ("capability_invocations_pkey", "CONCURRENT_MODIFICATION"),
        ("agent_tool_policy_permissions_policy_id_capability_id_key", "VALIDATION_ERROR"),
        ("unrelated_unique", "VALIDATION_ERROR"),
        ("research_task_command_receipt_project_id_actor_id_command_i_key", "IDEMPOTENCY_CONFLICT"),
    ],
)
def test_uniqueness_mapping_is_scoped_to_gateway_and_exact_diagnostics(
    gateway, constraint, expected
):
    from types import SimpleNamespace

    from sqlalchemy.exc import DBAPIError

    unit = SqlAlchemyUnitOfWork(lambda: Session())
    unit._research_task_error_normalization = True
    unit._gateway_error_normalization = gateway

    class Original(RuntimeError):
        sqlstate = "23505"
        diag = SimpleNamespace(constraint_name=constraint)

    original = Original("message must not be parsed")
    error = unit._command_database_error(DBAPIError(None, None, original))
    assert str(error.code) == (expected if gateway else "VALIDATION_ERROR")
    assert error.details is not None and not error.details["retryable_pr301"]


@pytest.mark.parametrize(
    "state,retry", [("40001", True), ("40P01", True), ("55P03", False), ("57014", False)]
)
def test_lifecycle_retry_sqlstates_are_closed(state, retry):
    from sqlalchemy.exc import DBAPIError
    from tests.unit.phase3.test_capability_gateway import (
        execute_lifecycle,
        lifecycle,
        running,
    )

    f = running()
    command = lifecycle(f)
    unit = SqlAlchemyUnitOfWork(lambda: Session())
    unit._research_task_error_normalization = True
    unit._gateway_error_normalization = True

    class Original(RuntimeError):
        sqlstate = state

    mapped = unit._command_database_error(DBAPIError(None, None, Original("not parsed")))
    calls = []
    lock = f.repo.lock_gateway

    def injected(*args, **kwargs):
        lock(*args, **kwargs)
        calls.append(True)
        raise mapped

    f.repo.lock_gateway = injected
    before = f.command_transactions
    with pytest.raises(type(mapped)):
        execute_lifecycle(f, command)
    assert len(calls) == (3 if retry else 1)
    assert f.command_transactions - before == len(calls)
    assert not f.tables["budget_usage_records"]


def test_lifecycle_invocation_identity_resolved_after_prefix_before_agent_keys():
    from researchbase.persistence.capability_gateway_repository import INVOCATION_SQL

    session = RecordingSession()
    session.results[normalized(INVOCATION_SQL)] = [{"agent_version_id": V}]
    repository = SqlAlchemyGatewayRepository(cast(Session, session))
    repository.lock_gateway(P, A, C, T, invocation_id=TARGET, after_wait=session.after_wait)
    queries = [entry[0] for entry in session.trace]
    lookup = queries.index(normalized(INVOCATION_SQL))
    assert queries[0] == SHARE
    assert lookup > next(
        i for i, row in enumerate(session.trace) if row[1].get("key") == f"pr301:task:{T}"
    )
    assert lookup < next(
        i for i, row in enumerate(session.trace) if row[1].get("key") == f"pr302:actor:{TARGET}"
    )
    assert lookup < next(
        i
        for i, row in enumerate(session.trace)
        if "research_tasks" in row[0] and "FOR UPDATE" in row[0]
    )


def test_invocation_update_is_parameterized_closed_cas():
    from types import SimpleNamespace

    from researchbase.foundation.errors import ErrorCode, ResearchBaseError

    calls = []

    class WriteSession:
        count = 1

        def execute(self, sql, params):
            calls.append((normalized(sql), params))
            return SimpleNamespace(rowcount=self.count)

    session = WriteSession()
    repository = SqlAlchemyGatewayRepository(cast(Session, session))
    repository.update_invocation(TARGET, 1, {"status": "RUNNING", "row_version": 2})
    assert calls[-1][1] == dict(
        identity=TARGET, expected_revision=1, status="RUNNING", row_version=2
    )
    assert "WHERE id=:identity AND row_version=:expected_revision" in calls[-1][0]
    with pytest.raises(ValueError):
        repository.update_invocation(TARGET, 1, {"parameters_content_hash": "injected"})
    session.count = 0
    with pytest.raises(ResearchBaseError) as error:
        repository.update_invocation(TARGET, 1, {"status": "RUNNING"})
    assert error.value.code == ErrorCode.CONCURRENT_MODIFICATION
