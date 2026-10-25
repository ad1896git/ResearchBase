from types import SimpleNamespace
from uuid import UUID

from researchbase.persistence.agent_execution_repository import (
    INTENT_SHARE_SQL,
    SqlAlchemyExecutionRepository,
)


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


def test_bounded_whole_transaction_retry_and_no_timeout_retry(monkeypatch):
    import pytest

    from researchbase.agent_runtime.application.agent_executions import AgentExecutionService
    from researchbase.foundation.errors import ErrorCode, ResearchBaseError

    service = AgentExecutionService(lambda: None, None, None)
    monkeypatch.setattr(service, "_preflight", lambda command: None)
    attempts = []

    def retry(command, ids, preflight, preflight_error):
        attempts.append(id(ids))
        raise ResearchBaseError(
            ErrorCode.CONCURRENT_MODIFICATION, "retry", {"retryable_pr302": True}
        )

    monkeypatch.setattr(service, "_once", retry)
    with pytest.raises(ResearchBaseError):
        service.execute(object())
    assert len(attempts) == 3 and len(set(attempts)) == 1
    attempts.clear()

    def timeout(command, ids, preflight, preflight_error):
        attempts.append(id(ids))
        raise ResearchBaseError(
            ErrorCode.CONCURRENT_MODIFICATION, "timeout", {"retryable_pr302": False}
        )

    monkeypatch.setattr(service, "_once", timeout)
    with pytest.raises(ResearchBaseError):
        service.execute(object())
    assert len(attempts) == 1
