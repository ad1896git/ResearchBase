import json
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from researchbase.agent_runtime.application.agent_executions import AgentExecutionService
from researchbase.agent_runtime.application.execution_contracts import (
    CreateAgentExecution,
    ExecutionCommand,
    GetAgentExecution,
    ListTaskExecutions,
)
from researchbase.agent_runtime.domain.harness_manifest import HarnessManifest
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.artifact_store import ArtifactStore
from researchbase.foundation.hashing import sha256_bytes
from researchbase.foundation.ids import new_uuid7
from researchbase.persistence.agent_execution_repository import (
    INTENT_SHARE_SQL,
    SqlAlchemyExecutionRepository,
)
from researchbase.persistence.uow import SqlAlchemyUnitOfWork


@pytest.fixture
def intent_protocol():
    """SQL/port observations with real service, UoW and repository control flow.

    Rows and time are deterministic doubles, not PostgreSQL isolation evidence.
    The integration snapshot/wait tests supply that separate evidence.
    """
    at = datetime(2026, 1, 1, tzinfo=UTC)
    project, actor, agent, task, step, version, harness, config = [new_uuid7() for _ in range(8)]
    caller = VerifiedPrincipal(actor, "test", "MTLS_URI", "spiffe://test", "cert", at)
    command = ExecutionCommand(
        project,
        caller,
        new_uuid7(),
        "create_agent_execution",
        None,
        CreateAgentExecution(new_uuid7(), version, task, step, 3, harness),
    )
    configuration = b"{}"
    manifest = HarnessManifest(
        1,
        "rev1",
        "runtime1",
        "model1",
        "prompt1",
        "a" * 64,
        str(sha256_bytes(configuration)),
        "strategy1",
        "rev1",
        (),
        (),
        (),
        (),
        (),
        (),
    )
    payloads = {str(config): configuration, str(harness): json.dumps(asdict(manifest)).encode()}
    artifacts = {
        identity: {
            "id": identity,
            "project_id": project,
            "status": "FROZEN",
            "frozen_at": at,
            "locator": str(identity),
            "byte_size": len(payloads[str(identity)]),
            "content_hash": str(sha256_bytes(payloads[str(identity)])),
        }
        for identity in (config, harness)
    }
    rows = {
        "research_tasks": [
            {
                "id": task,
                "project_id": project,
                "status": "PLANNING",
                "plan_sealed_at": at,
                "row_version": 3,
                "strategy_id": "strategy1",
                "strategy_version": "rev1",
            }
        ],
        "research_task_steps": [{"id": step, "status": "PENDING"}],
        "research_task_inputs": [],
        "research_task_step_inputs": [],
        "agent_versions": [
            {
                "id": version,
                "actor_id": agent,
                "project_id": project,
                "configuration_artifact_version_id": config,
                "model_profile_id": "model1",
                "prompt_template_version": "prompt1",
            }
        ],
        "agent_availability": [{"status": "ACTIVE"}],
        "agent_command_receipts": [],
        "agent_execution_instances": [],
        "agent_execution_events": [],
    }
    authority = {
        "actor_type": "HUMAN",
        "role": "OWNER",
        "retired_at": None,
        "binding_status": "ACTIVE",
        "membership_status": "ACTIVE",
        "effective_from": at,
        "effective_until": None,
        "bound_at": at,
        "revoked_at": None,
    }
    observations = []
    sessions = []
    held = set()

    def session_factory():
        session = MagicMock(spec=Session)
        session.autoflush = True  # begin_* must actively disable it.
        sessions.append(session)

        def execute(statement, params=None):
            nonlocal at
            sql = " ".join(str(statement).split())
            params = params or {}
            observations.append(("sql", sql))
            result = MagicMock()
            data = []
            if (
                sql.startswith("LOCK TABLE")
                or "FOR UPDATE" in sql
                or any(key in sql for key in ("pg_advisory_xact_lock", "rb_phase2_lock_project"))
            ):
                held.add(id(session))
                observations.append(("wait", sql))
            elif sql.startswith("INSERT INTO"):
                table = sql.split()[2]
                data = [dict(params)]
                rows[table].extend(data)
                observations.append(("wait", sql))
            elif sql == "SET CONSTRAINTS ALL IMMEDIATE":
                observations.append(("wait", sql))
            elif sql == "SELECT clock_timestamp()":
                at += timedelta(microseconds=1)
                result.scalar_one.return_value = at
                observations.append(("clock", at))
            elif "JOIN project_memberships m ON m.actor_id=a.id" in sql and "r.role," in sql:
                data = [authority.copy()]
                observations.append(("authority", data[0]))
            elif sql.startswith("SELECT lifecycle_status"):
                result.scalar_one_or_none.return_value = "ACTIVE"
            elif "FROM artifact_versions av" in sql:
                data = [artifacts[params["id"]]]
            elif sql.startswith("SELECT id FROM actors") or sql.startswith(
                "SELECT a.id FROM actors"
            ):
                data = [{"id": actor}]
            else:
                assert sql.startswith("SELECT * FROM "), sql
                data = rows[sql.split()[3]]
            result.mappings.return_value.__iter__.side_effect = lambda: iter(data)
            result.mappings.return_value.all.return_value = data
            result.mappings.return_value.first.return_value = data[0] if data else None
            result.mappings.return_value.one.side_effect = lambda: data[0]
            return result

        def finish(kind):
            observations.append((kind, id(session)))
            held.discard(id(session))

        session.execute.side_effect = execute
        session.commit.side_effect = lambda: finish("commit")
        session.close.side_effect = lambda: finish("close")
        session.rollback.side_effect = lambda: finish("rollback")
        return session

    def external(kind, result):
        def call(*args, **kwargs):
            assert not held, f"{kind} I/O while intent write locks are held"
            observations.append(("external", kind))
            return result(*args, **kwargs)

        return call

    store = MagicMock(spec=ArtifactStore)
    for name in ("open", "exists", "verify", "put_verified"):
        getattr(store, name).side_effect = external(
            "ArtifactStore." + name, lambda locator, *args, **kwargs: payloads[locator]
        )
    credentials = SimpleNamespace(
        is_valid=lambda principal, checked_at: observations.append(("credential", checked_at))
        or True
    )
    pins = SimpleNamespace(verify=external("pins.verify", lambda manifest: True))
    factory = MagicMock(side_effect=session_factory)
    service = AgentExecutionService(
        lambda: SqlAlchemyUnitOfWork(factory), credentials, store, pins=pins
    )
    return SimpleNamespace(
        service=service,
        command=command,
        observations=observations,
        sessions=sessions,
        factory=factory,
        external=external,
    )


def test_fresh_checks_after_each_wait(intent_protocol, monkeypatch):
    env = intent_protocol

    # Any new model/network/process call must obey the same external-I/O boundary.
    def unexpected_io(*args, **kwargs):
        raise AssertionError("intent creation must not start network/process work")

    monkeypatch.setattr("socket.create_connection", env.external("network", unexpected_io))
    monkeypatch.setattr("subprocess.Popen", env.external("process", unexpected_io))
    result = env.service.execute(env.command)
    assert not result.replayed
    observations = env.observations
    waits = [i for i, (kind, _) in enumerate(observations) if kind == "wait"]
    commit = next(i for i, (kind, _) in enumerate(observations) if kind == "commit")
    assert len(waits) == 18  # prefix, project + five keys, seven rows, three writes, constraints
    checks = []
    for start, end in zip(waits, [*waits[1:], commit], strict=True):
        interval = observations[start + 1 : end]
        kinds = [kind for kind, _ in interval]
        assert {"authority", "clock", "credential"} <= set(kinds), observations[start:end]
        assert kinds.index("authority") < kinds.index("clock") < kinds.index("credential")
        checked_at = next(value for kind, value in interval if kind == "credential")
        assert checked_at == next(value for kind, value in interval if kind == "clock")
        checks.append(checked_at)
    assert all(left < right for left, right in zip(checks, checks[1:], strict=False))
    external_calls = [
        (i, value) for i, (kind, value) in enumerate(observations) if kind == "external"
    ]
    assert [value for _, value in external_calls] == [
        "ArtifactStore.open",
        "ArtifactStore.open",
        "pins.verify",
    ]
    assert all(i < waits[0] for i, _ in external_calls)


@pytest.mark.parametrize("operation", ["replay", "get", "list"])
def test_formal_read_has_one_readonly_snapshot(intent_protocol, operation):
    env = intent_protocol
    env.service.execute(env.command)
    env.observations.clear()
    env.sessions.clear()
    env.factory.reset_mock()
    command = env.command
    if operation == "replay":
        assert env.service.replay(command).replayed
    elif operation == "get":
        assert (
            env.service.get_agent_execution(
                GetAgentExecution(
                    command.project_id, command.arguments.execution_id, command.caller
                )
            ).id
            == command.arguments.execution_id
        )
    else:
        assert (
            len(
                env.service.list_task_executions(
                    ListTaskExecutions(
                        command.project_id, command.arguments.research_task_id, command.caller
                    )
                )
            )
            == 1
        )
    env.factory.assert_called_once_with()
    (session,) = env.sessions
    session.begin.assert_called_once_with()
    session.connection.assert_called_once_with(
        execution_options={
            "isolation_level": "REPEATABLE READ",
            "postgresql_readonly": True,
        }
    )
    assert session.autoflush is False
    for method in (session.flush, session.add, session.add_all, session.delete, session.commit):
        method.assert_not_called()
    sql = [value for kind, value in env.observations if kind == "sql"]
    assert sql and all(statement.startswith("SELECT ") for statement in sql)
    assert not any(kind in {"wait", "external"} for kind, _ in env.observations)
    assert not any(
        token in statement.upper()
        for statement in sql
        for token in (" FOR ", "ADVISORY", "LOCK_PROJECT", "INSERT ", "UPDATE ", "DELETE ")
    )
    session.rollback.assert_called_once_with()
    session.close.assert_called_once_with()


def test_ordered_intent_prefix_and_keys(monkeypatch):
    calls = []
    ids = [UUID(int=i) for i in range(1, 8)]
    repo = object.__new__(SqlAlchemyExecutionRepository)
    repo._session = SimpleNamespace(execute=lambda sql: calls.append(str(sql)))
    repo.one = lambda sql, **p: calls.append(sql)
    repo.advisory = lambda key: calls.append(key)
    monkeypatch.setattr(repo, "many", lambda sql, **p: calls.append(sql))
    monkeypatch.setattr(repo, "version", lambda _: {"actor_id": ids[2]})
    monkeypatch.setattr(repo, "steps", lambda _: [{"id": ids[5]}])
    command = SimpleNamespace(
        project_id=ids[0],
        caller=SimpleNamespace(actor_id=ids[1]),
        command_id=ids[3],
        arguments=SimpleNamespace(
            agent_version_id=ids[4], research_task_id=ids[5], execution_id=ids[6]
        ),
    )
    repo.lock_write(command, lambda: calls.append("fresh"))
    assert calls[0] == INTENT_SHARE_SQL
    assert (
        len(INTENT_SHARE_SQL.split(" IN SHARE MODE")[0].replace("LOCK TABLE ", "").split(", "))
        == 23
    )
    keys = [s for s in calls if s.startswith(("pr302:", "pr301:"))]
    assert [s.split(":")[1] for s in keys] == ["command", "actor", "task", "version", "execution"]
    assert [s for s in calls if "FOR UPDATE" in s] == [
        "SELECT id FROM actors WHERE id=:id FOR UPDATE",
        "SELECT id FROM actors WHERE id=:id FOR UPDATE",
        "SELECT id FROM research_tasks WHERE id=:id FOR UPDATE",
        "SELECT id FROM research_task_steps WHERE id=:id FOR UPDATE",
        "SELECT id FROM agent_versions WHERE id=:id FOR UPDATE",
        "SELECT agent_version_id FROM agent_availability WHERE agent_version_id=:id FOR UPDATE",
        "SELECT id FROM agent_execution_instances WHERE id=:id FOR UPDATE",
    ]
    assert all(
        calls[i + 1] == "fresh"
        for i, s in enumerate(calls)
        if s.startswith(("SELECT", "LOCK", "pr302:", "pr301:"))
    )


def test_intent_diagnostics_are_translated_by_exact_state_and_tag():
    from sqlalchemy.exc import DBAPIError

    from researchbase.foundation.errors import ErrorCode
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork

    uow = object.__new__(SqlAlchemyUnitOfWork)
    uow._intent_error_normalization = True
    tags = {
        "scope": ErrorCode.FORBIDDEN,
        "state": ErrorCode.INVALID_STATE_TRANSITION,
        "cas": ErrorCode.CONCURRENT_MODIFICATION,
        "binding": ErrorCode.REFERENTIAL_INTEGRITY_ERROR,
        "not_frozen": ErrorCode.VERSION_NOT_FROZEN,
        "unresolved": ErrorCode.FROZEN_REFERENCE_REQUIRED,
        "preheld": ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
        "provenance": ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
        "completeness": ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
        "late_history": ErrorCode.IMMUTABLE_RECORD,
        "immutable": ErrorCode.IMMUTABLE_RECORD,
        "value_type": ErrorCode.VALIDATION_ERROR,
    }
    for tag, expected in tags.items():

        class DiagnosticError(Exception):
            sqlstate: str
            diag: object

        original = DiagnosticError("private SQL must not reach caller")
        original.sqlstate = "22023" if tag == "value_type" else "23514"
        original.diag = SimpleNamespace(constraint_name="pr302s2_" + tag)
        error = DBAPIError(None, None, original)
        result = uow._command_database_error(error)
        assert result.code == expected
        assert "private SQL" not in str(result)


@pytest.mark.parametrize(
    "sqlstate,attempt_count", [("40001", 3), ("40P01", 3), ("55P03", 1), ("57014", 1)]
)
def test_bounded_whole_transaction_retry_and_no_timeout_retry(monkeypatch, sqlstate, attempt_count):
    from psycopg.errors import lookup
    from sqlalchemy.exc import DBAPIError

    from researchbase.foundation.errors import ErrorCode, ResearchBaseError

    service = AgentExecutionService(lambda: None, None, None)
    monkeypatch.setattr(service, "_preflight", lambda command: None)
    attempts = []
    sessions = []

    def retry(command, ids, preflight, preflight_error):
        attempts.append(id(ids))
        session = MagicMock(spec=Session)
        sessions.append(session)
        with SqlAlchemyUnitOfWork(lambda: session) as uow:
            uow.begin_execution_intent()
            # Driver error enters the real UoW normalization; no pre-tagged flag.
            raise DBAPIError(None, None, lookup(sqlstate)("private SQL diagnostic"))

    monkeypatch.setattr(service, "_once", retry)
    with pytest.raises(ResearchBaseError) as exc:
        service.execute(object())
    assert exc.value.code == ErrorCode.CONCURRENT_MODIFICATION
    assert exc.value.details == {"retryable_pr302": sqlstate in {"40001", "40P01"}}
    assert len(attempts) == attempt_count and len(set(attempts)) == 1
    assert len({id(session) for session in sessions}) == attempt_count
    for session in sessions:
        session.begin.assert_called_once_with()
        session.rollback.assert_called_once_with()
        session.close.assert_called_once_with()
        session.commit.assert_not_called()
