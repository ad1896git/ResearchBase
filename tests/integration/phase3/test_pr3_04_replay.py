"""Saved concrete results converge without repeating effects or current CAS checks."""

from dataclasses import replace

import pytest
from tests.integration.phase3.test_pr3_04_accounting import setup
from tests.integration.phase3.test_pr3_04_application import (
    approve,
    bind,
    command,
    reserve,
    service,
)

from researchbase.foundation.errors import ErrorCode, ResearchBaseError


def test_reservation_exact_replay_and_changed_hash(planning):
    p = planning
    task, fake = setup(p)
    c = reserve(p, task, 4)
    first = fake.execute(p.principal, c)
    replay = fake.execute(p.principal, c)
    assert first.reservation_ids == replay.reservation_ids and replay.command_result.replayed
    assert fake.reconstruct(p.principal, p.project, task).reserved.llm_calls == 1
    changed = replace(c, arguments=replace(c.arguments, reason="Changed request."))
    with pytest.raises(ResearchBaseError) as exc:
        fake.execute(p.principal, changed)
    assert exc.value.code == ErrorCode.IDEMPOTENCY_CONFLICT
    saved = fake.service.replay_safety(p.principal, c)
    assert saved is not None and saved.reservation_ids == first.reservation_ids


def test_response_replay_before_stale_revisions(planning):
    p = planning
    task = p.create()
    bind(p, task)
    c = approve(p, task, 2)
    service(p).execute(
        p.principal, command(p, task, 4, "evaluate_task_termination", {"reason": "Later revision."})
    )
    replay = service(p).execute(p.principal, c)
    assert replay.command_result.resulting_row_version == 4 and replay.command_result.replayed
    assert len(replay.responded_checkpoint_ids) == 1


def test_replay_requires_live_current_read_entitlement(planning):
    from researchbase.agent_runtime.application.task_safety import TaskSafetyService

    p = planning
    task = p.create()
    c, _ = bind(p, task)

    class Revoked:
        def is_valid(self, principal, at):
            return False

    denied = TaskSafetyService(p.factory, Revoked(), p.store)
    for operation in (denied.execute, denied.replay_safety):
        with pytest.raises(ResearchBaseError) as exc:
            operation(p.principal, c)
        assert exc.value.code == ErrorCode.FORBIDDEN


def test_uncertain_commit_reads_original_receipt_without_retry(planning, monkeypatch):
    from researchbase.agent_runtime.ports.task_repository import UncertainTaskCommit
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork

    p = planning
    task = p.create()
    original = SqlAlchemyUnitOfWork.commit
    calls = []

    def commit(uow):
        original(uow)
        calls.append(1)
        raise UncertainTaskCommit("lost acknowledgement")

    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", commit)
    c, result = bind(p, task)
    assert result.command_result.replayed and calls == [1]
    assert len(result.budget_ids) == 1
    saved = service(p).replay_safety(p.principal, c)
    assert saved is not None and saved.budget_ids == result.budget_ids
