"""Recording evidence for S2 storage; no PostgreSQL contention/expiry claim."""

from datetime import UTC, datetime
from typing import Any, cast, get_type_hints
from uuid import UUID

import pytest
from sqlalchemy.orm import Session
from tests.unit.phase3.test_capability_gateway_repository import SHARE, normalized

from researchbase.agent_runtime.ports import search_repository as port
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.database import Base
from researchbase.persistence.experiment_search_repository import (
    COMMITTED_RECEIPT_SQL,
    EXPERIMENT_SPEC_SQL,
    HYPOTHESIS_SQL,
    SqlAlchemyExperimentSearchRepository,
)
from researchbase.persistence.uow import SqlAlchemyUnitOfWork

P, A, C, T, S, H, E = (UUID(int=i) for i in range(1, 8))
STEP1, STEP2 = UUID(int=20), UUID(int=30)
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


class Result:
    rowcount = 1

    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return self

    def __iter__(self):
        return iter(self.rows)

    def scalar_one(self):
        return self.rows[0]


class RecordingSession:
    autoflush = False
    rowcount = 1

    def __init__(self):
        self.trace = []
        self.results: dict[str, list[dict[str, Any]]] = {
            "SELECT id FROM research_task_steps WHERE research_task_id=:id ORDER BY id": [
                {"id": STEP1},
                {"id": STEP2},
            ],
        }

    def execute(self, sql, params=None):
        sql = normalized(sql)
        self.trace.append((sql, dict(params or {})))
        result = Result(self.results.get(sql, []))
        result.rowcount = self.rowcount
        return result

    def flush(self):
        self.trace.append(("FLUSH", {}))

    def connection(self, *, execution_options):
        self.trace.append(("CONNECTION", execution_options))

    def commit(self):
        self.trace.append(("COMMIT", {}))


def repository(session):
    return SqlAlchemyExperimentSearchRepository(cast(Session, session))


def lock(repo, callback, kind: port.SearchCallerKind = "HUMAN"):
    return repo.lock_write(
        P,
        A,
        C,
        T,
        caller_kind=kind,
        after_stage=callback,
        hypothesis_versions=(H,),
        experiment_spec_versions=(E,),
    )


def callback_for(session):
    def callback(stage):
        session.trace.append(("CALLBACK", stage))

    return callback


@pytest.mark.parametrize("kind", ["HUMAN", "AGENT"])
@pytest.mark.parametrize("command", ["create_search_session", "append_search_node"])
def test_first_statement_and_complete_lock_order(kind, command):
    session = RecordingSession()
    repo = repository(session)
    assert session.trace == []
    rows = lock(repo, callback_for(session), kind)
    trace = [item for item in session.trace if item[0] != "CALLBACK"]
    expected = [
        (SHARE, {}),
        ("SELECT rb_phase2_lock_project(:id)", {"id": P}),
        (
            "SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",
            {"key": f"pr301:command:{P}:{A}:{C}"},
        ),
        ("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))", {"key": f"pr301:task:{T}"}),
    ]
    if kind == "AGENT":
        expected.append(
            ("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))", {"key": f"pr302:actor:{A}"})
        )
    expected += [
        ("SELECT id FROM research_tasks WHERE id=:id FOR UPDATE", {"id": T}),
        ("SELECT id FROM research_task_steps WHERE research_task_id=:id ORDER BY id", {"id": T}),
        (
            "SELECT id FROM research_task_steps WHERE research_task_id=:task AND id=:id FOR UPDATE",
            {"task": T, "id": STEP1},
        ),
        (
            "SELECT id FROM research_task_steps WHERE research_task_id=:task AND id=:id FOR UPDATE",
            {"task": T, "id": STEP2},
        ),
        (
            "SELECT predecessor_id,dependent_id FROM research_task_step_dependencies "
            "WHERE research_task_id=:id ORDER BY predecessor_id,dependent_id",
            {"id": T},
        ),
        ("SELECT * FROM research_task_inputs WHERE research_task_id=:id ORDER BY id", {"id": T}),
        (
            "SELECT * FROM research_task_step_inputs WHERE research_task_id=:id ORDER BY id",
            {"id": T},
        ),
    ]
    expected += [
        (f"SELECT * FROM {table} WHERE research_task_id=:id ORDER BY id", {"id": T})
        for table in SAFETY
    ]
    expected += [
        (f"SELECT * FROM {table} WHERE research_task_id=:id ORDER BY id", {"id": T})
        for table in (
            "experiment_search_events",
            "experiment_search_nodes",
            "experiment_search_sessions",
        )
    ]
    expected += [
        (normalized(HYPOTHESIS_SQL), {"id": H}),
        (normalized(EXPERIMENT_SPEC_SQL), {"id": E}),
    ]
    assert trace == expected
    assert rows == port.StoredSearchWriteRows((), (), (), (), ())
    assert not any(
        "agent_version" in sql or "availability" in sql or "execution:" in str(params)
        for sql, params in trace
    )
    # Both admitted operations enter this same trace before storage effects.
    repo.insert(
        "experiment_search_sessions"
        if command == "create_search_session"
        else "experiment_search_nodes",
        {"id": S},
    )
    assert session.trace[-1][1].operation == "insert"


@pytest.mark.parametrize("kind", ["HUMAN", "AGENT"])
def test_every_blocking_stage_calls_fresh_validation(kind):
    session = RecordingSession()
    repo = repository(session)
    lock(repo, callback_for(session), kind)
    repo.update_task(T, 5)
    for table in (
        "research_task_command_receipts",
        "experiment_search_sessions",
        "experiment_search_nodes",
        "experiment_search_events",
        "research_task_events",
        "research_task_receipt_events",
    ):
        repo.insert(table, {"research_task_id": T})
    repo.flush()
    repo.force_constraints()
    repo.before_commit()
    # Every SQL operation and flush completes before its own validation. Final is
    # a distinct precommit callback; no repository transaction method is invoked.
    assert session.trace[-1] == ("CALLBACK", port.SearchStorageStage("final"))
    trace = session.trace[:-1]
    assert len(trace) % 2 == 0
    for index in range(0, len(trace), 2):
        assert trace[index][0] != "CALLBACK"
        assert trace[index + 1][0] == "CALLBACK"
    effects = [stage.operation for sql, stage in session.trace if sql == "CALLBACK"]
    assert effects[-12:] == ["update"] + ["insert"] * 6 + [
        "flush",
        "constraints",
        "flush",
        "constraints",
        "final",
    ]


@pytest.mark.parametrize(
    "kind,stop",
    [(kind, stop) for kind in ("HUMAN", "AGENT") for stop in range(1, 30 + (kind == "AGENT"))],
)
def test_callback_denial_stops_at_each_stage_and_cannot_resume(kind, stop):
    session = RecordingSession()
    repo = repository(session)
    observed = []

    def deny(stage):
        observed.append(stage)
        if len(observed) == stop:
            raise PermissionError("test boundary denied")

    def attempt():
        lock(repo, deny, kind)
        repo.update_task(T, 5)
        repo.insert("research_task_command_receipts", {"id": S})
        repo.before_commit()

    # The complete trace has 29 Human stages, 30 Agent stages.
    with pytest.raises(PermissionError):
        attempt()
    assert len(observed) == stop
    before = list(session.trace)
    with pytest.raises(RuntimeError):
        repo.insert("experiment_search_events", {"id": S})
    with pytest.raises(RuntimeError):
        repo.before_commit()
    with pytest.raises(RuntimeError):
        lock(repo, lambda stage: None, kind)
    assert session.trace == before


def test_immutable_reads_do_not_lock_runs_or_lineage():
    session = RecordingSession()
    repo = repository(session)
    lock(repo, lambda stage: None, "AGENT")
    assert not any("runs" in sql for sql, _ in session.trace)
    locked = [sql for sql, _ in session.trace if "FOR UPDATE" in sql]
    assert len(locked) == 3
    assert all(
        "FROM research_tasks " in sql or "FROM research_task_steps " in sql for sql in locked
    )
    session.trace.clear()
    repo.sessions(P, T)
    repo.nodes(T, S)
    repo.search_events(T, S)
    repo.node_runs(P, T, S)
    repo.run(P, S)
    repo.hypothesis_version(H)
    repo.experiment_spec_version(E)
    assert all(sql.startswith("SELECT") and "FOR UPDATE" not in sql for sql, _ in session.trace)


def test_formal_read_has_one_snapshot_and_no_writes():
    session = RecordingSession()
    uow = SqlAlchemyUnitOfWork(lambda: cast(Session, session))
    uow._session = cast(Session, session)
    uow.begin_formal_read()
    repo = repository(session)
    repo.task(T)
    repo.steps(T)
    repo.edges(T)
    repo.inputs(T)
    repo.inputs(T, step=True)
    for table in SAFETY:
        repo.rows(table, T)
    repo.sessions(P, T)
    repo.nodes(T, S)
    repo.search_events(T, S)
    repo.node_runs(P, T, S)
    repo.run(P, S)
    repo.hypothesis_version(H)
    repo.experiment_spec_version(E)
    assert session.trace[0] == (
        "CONNECTION",
        {"isolation_level": "REPEATABLE READ", "postgresql_readonly": True},
    )
    assert sum(sql == "CONNECTION" for sql, _ in session.trace) == 1
    assert all(sql.startswith("SELECT") for sql, _ in session.trace[1:])
    assert not any(
        token in sql.upper()
        for sql, _ in session.trace[1:]
        for token in ("FOR UPDATE", "LOCK TABLE", "ADVISORY", "LIMIT", "OFFSET")
    )


def test_committed_replay_filter_and_application_callback_order():
    session = RecordingSession()
    repo = repository(session)
    saved = {"id": S, "request_hash": "a" * 64}
    session.results[normalized(COMMITTED_RECEIPT_SQL)] = [saved]
    order = []

    class Replay(Exception):
        pass

    def validate(stage):
        order.append("current entitlement")
        receipt = repo.committed_receipt(P, A, C)
        order.append("committed hash replay")
        assert receipt is not None and receipt["id"] == S
        assert receipt["request_hash"] == "a" * 64
        raise Replay

    with pytest.raises(Replay):
        lock(repo, validate)
    assert order == ["current entitlement", "committed hash replay"]
    assert session.trace[0][0] == SHARE
    assert len(session.trace) == 2
    assert "xmin<>pg_current_xact_id()::xid" in session.trace[1][0]


def test_callback_can_read_but_cannot_nest_locks_or_effects():
    session = RecordingSession()
    repo = repository(session)

    def validate(stage):
        repo.task(T)
        with pytest.raises(RuntimeError):
            lock(repo, validate)
        with pytest.raises(RuntimeError):
            repo.insert("experiment_search_events", {"id": S})

    lock(repo, validate)
    assert not any(sql.startswith("INSERT") for sql, _ in session.trace)


@pytest.mark.parametrize(
    "table,stored",
    [
        ("experiment_search_sessions", port.StoredSearchSession),
        ("experiment_search_nodes", port.StoredSearchNode),
        ("experiment_search_node_runs", port.StoredSearchNodeRun),
        ("experiment_search_events", port.StoredSearchEvent),
        ("research_task_command_receipts", port.StoredSearchReceipt),
    ],
)
def test_closed_rows_match_exact_mapped_columns(table, stored):
    mapped = Base.metadata.tables[table]
    assert set(get_type_hints(stored)) == set(mapped.columns.keys())
    assert stored.__required_keys__ == frozenset(mapped.columns.keys())
    assert all(column.default is None for column in mapped.columns)


@pytest.mark.parametrize(
    "table", ["experiment_search_node_runs", "runs", "budget_reservations", "actors"]
)
def test_storage_cannot_write_run_links_science_identity_or_d1(table):
    session = RecordingSession()
    with pytest.raises(ValueError):
        repository(session).insert(table, {"id": S})
    assert session.trace == []


def test_storage_rejects_unknown_columns_and_writes_before_locking():
    session = RecordingSession()
    repo = repository(session)
    with pytest.raises(ValueError):
        repo.insert("experiment_search_sessions", {"id": S, "objective_definition": "extra goal"})
    with pytest.raises(RuntimeError):
        repo.insert("experiment_search_sessions", {"id": S})
    assert session.trace == []


def test_uow_construction_wiring_and_commit_boundary_emit_no_early_sql():
    calls = []

    def factory():
        calls.append(True)
        return Session()

    SqlAlchemyUnitOfWork(factory)
    assert calls == []
    with SqlAlchemyUnitOfWork(lambda: Session()) as unit:
        assert isinstance(unit.experiment_search, SqlAlchemyExperimentSearchRepository)
        assert unit._session is not None and not unit._session.in_nested_transaction()
        assert unit.experiment_search._session is unit._session
    session = RecordingSession()
    unit = SqlAlchemyUnitOfWork(lambda: cast(Session, session))
    unit._session = cast(Session, session)
    unit.experiment_search = repository(session)
    unit.begin_experiment_search()
    assert session.trace == [
        ("CONNECTION", {"isolation_level": "READ COMMITTED", "postgresql_readonly": False})
    ]
    session.trace.clear()
    lock(unit.experiment_search, callback_for(session))
    unit.commit()
    assert [getattr(stage, "operation", sql) for sql, stage in session.trace[-6:]] == [
        "FLUSH",
        "flush",
        "SET CONSTRAINTS ALL IMMEDIATE",
        "constraints",
        "final",
        "COMMIT",
    ]


def test_task_cas_failure_is_closed_without_callback_or_commit():
    session = RecordingSession()
    repo = repository(session)
    lock(repo, lambda stage: None)
    session.rowcount = 0
    with pytest.raises(ResearchBaseError) as exc:
        repo.update_task(T, 5)
    assert exc.value.code == ErrorCode.CONCURRENT_MODIFICATION


def test_stored_rows_are_detached_and_retain_hashes_and_owner_scope():
    session = RecordingSession()
    row = dict(
        id=H,
        hypothesis_id=S,
        project_id=P,
        status="FROZEN",
        frozen_at=datetime(2026, 10, 28, tzinfo=UTC),
        content_hash="a" * 64,
    )
    session.results[normalized(HYPOTHESIS_SQL)] = [row]
    repo = repository(session)
    result = repo.hypothesis_version(H)
    assert result == row and result is not row
    assert result is not None
    result["content_hash"] = "b" * 64
    assert row["content_hash"] == "a" * 64


def test_mapped_search_check_expressions_follow_canonical_alembic():
    import ast
    import re
    from pathlib import Path

    from sqlalchemy import CheckConstraint

    tree = ast.parse(Path("migrations/versions/0082_experiment_search_core.py").read_text())
    constants = {
        node.targets[0].id: node.value.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and isinstance(node.targets[0], ast.Name)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    }
    declared = {}
    for name in ("SESSIONS", "NODES", "NODE_RUNS", "EVENTS", "RECEIPTS"):
        sql = constants[name]
        for match in re.finditer(r"ADD\s+CONSTRAINT\s+(pr316_\w+)\s+CHECK\s*\(", sql):
            start, depth, end = match.end(), 1, match.end()
            while depth:
                depth += (sql[end] == "(") - (sql[end] == ")")
                end += 1
            declared[match[1]] = " ".join(sql[start : end - 1].split())
    commands = "'admit_bearing_evaluation_v2','settle_bearing_evaluation_v2'"
    events = "'BEARING_EVALUATION_ADMITTED','BEARING_EVALUATION_SETTLED'"
    declared["pr316_command_names"] = (
        f"({declared['pr316_command_names']}) OR command_name IN ({commands})"
    )
    declared["pr316_receipt_shape_ck"] = (
        f"({declared['pr316_receipt_shape_ck']}) OR "
        "(command_name='admit_bearing_evaluation_v2' AND "
        "num_nonnulls(result_search_session_id,result_search_node_id,result_search_event_id)=3 "
        "AND resulting_row_version>=2)"
    )
    declared["pr316_task_event_names"] = (
        f"({declared['pr316_task_event_names']}) OR event_type IN ({events})"
    )
    declared["pr316_task_event_states"] = (
        f"({declared['pr316_task_event_states']}) OR "
        "(event_type='BEARING_EVALUATION_ADMITTED' AND prior_status IN "
        "('CREATED','PLANNING') AND new_status=prior_status) OR "
        "(event_type='BEARING_EVALUATION_SETTLED' AND prior_status IN "
        "('CREATED','PLANNING','CANCELLED') AND new_status=prior_status)"
    )
    declared["pr316_task_event_reason"] = (
        f"(event_type NOT IN ({events}) AND ({declared['pr316_task_event_reason']})) OR "
        f"(event_type IN ({events}) AND reason IS NOT NULL AND pr316_reason(reason))"
    )
    mapped = {
        constraint.name: " ".join(str(constraint.sqltext).split())
        for table in Base.metadata.tables.values()
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
        and isinstance(constraint.name, str)
        and constraint.name.startswith("pr316_")
    }
    assert declared and mapped == declared
