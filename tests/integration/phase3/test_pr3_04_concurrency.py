"""Actual PostgreSQL lock waits and fresh post-wait database authorization time."""

from concurrent.futures import ThreadPoolExecutor
from time import monotonic, sleep

import pytest
from sqlalchemy import text
from tests.integration.phase3.test_pr3_04_accounting import setup
from tests.integration.phase3.test_pr3_04_application import bind, command, reserve, service

from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.ids import new_uuid7
from researchbase.persistence.task_safety_repository import SqlAlchemyTaskSafetyRepository


def waiters(engine, count=1):
    deadline = monotonic() + 5
    while monotonic() < deadline:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT l.pid,l.waitstart,a.xact_start FROM pg_locks l JOIN pg_stat_activity a ON a.pid=l.pid WHERE NOT l.granted AND a.datname=current_database() AND l.locktype='advisory'"  # noqa: E501
                )
            ).all()
            if len(rows) >= count:
                return rows
        sleep(0.01)
    raise AssertionError("expected real advisory lock waiter")


def test_two_reservations_last_unit_have_one_winner(planning):
    p = planning
    task, fake = setup(p, max_llm_calls=1)
    key = f"pr301:task:{task}"
    with p.engine.connect() as blocker, ThreadPoolExecutor(max_workers=2) as pool:
        blocker.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"), {"key": key}
        )
        commands = [reserve(p, task, 4), reserve(p, task, 4)]
        futures = [pool.submit(fake.execute, p.principal, c) for c in commands]
        # The project lock serializes the second command; at least one is waiting on the held task lock.  # noqa: E501
        observed = waiters(p.engine)
        assert observed[0].waitstart is not None
        blocker.commit()
        results = []
        for future in futures:
            try:
                results.append(future.result(timeout=5))
            except ResearchBaseError as exc:
                results.append(exc)
    assert sum(not isinstance(r, ResearchBaseError) for r in results) == 1
    denied = next(r for r in results if isinstance(r, ResearchBaseError))
    assert denied.code == ErrorCode.CONCURRENT_MODIFICATION
    view = fake.reconstruct(p.principal, p.project, task)
    assert view.task_row_version == 5 and view.reserved.llm_calls == 1


def test_response_waits_through_expiry_and_denies_without_effects(planning, monkeypatch):
    p = planning
    task = p.create()
    bind(p, task, checkpoint={"timeout_seconds": 2})
    checkpoint_id = new_uuid7()
    service(p).execute(
        p.principal,
        command(
            p,
            task,
            2,
            "request_human_checkpoint",
            {
                "checkpoint_id": str(checkpoint_id),
                "step_id": None,
                "checkpoint_type": "plan_review",
                "reason": "Expiry wait test.",
            },
        ),
    )
    times = []
    original = SqlAlchemyTaskSafetyRepository.at

    def at(repo):
        stamp = original(repo)
        times.append(stamp)
        return stamp

    monkeypatch.setattr(SqlAlchemyTaskSafetyRepository, "at", at)
    response = command(
        p,
        task,
        3,
        "respond_human_checkpoint",
        {
            "checkpoint_id": str(checkpoint_id),
            "expected_checkpoint_row_version": 1,
            "response": "APPROVED",
            "reason": "Late response denied.",
        },
    )
    with p.engine.connect() as blocker, ThreadPoolExecutor(max_workers=1) as pool:
        expiry = blocker.execute(
            text("SELECT expires_at FROM human_checkpoints WHERE id=:id"), {"id": checkpoint_id}
        ).scalar_one()
        blocker.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
            {"key": f"pr301:task:{task}"},
        )
        future = pool.submit(service(p).execute, p.principal, response)
        waiting = waiters(p.engine)[0]
        assert waiting.xact_start < expiry and waiting.waitstart < expiry
        blocker.execute(
            text("SELECT pg_sleep(greatest(0,extract(epoch FROM (:expiry-clock_timestamp()))))"),
            {"expiry": expiry},
        )
        released = blocker.execute(text("SELECT clock_timestamp()")).scalar_one()
        blocker.commit()
        with pytest.raises(ResearchBaseError) as exc:
            future.result(timeout=5)
    assert exc.value.code == ErrorCode.INVALID_STATE_TRANSITION
    assert times[0] < expiry
    assert released >= expiry and times and times[-1] >= released
    assert (
        service(p).get_task_checkpoint_history(p.principal, p.project, task).checkpoints[0].status
        == "PENDING"
    )
    assert p.service.get_research_task(p.principal, p.project, task).row_version == 3
    print(
        f"TEMP_AUTH: tx_started_at={waiting.xact_start} expiry_at={expiry} lock_wait_started_at={waiting.waitstart} lock_released_at={released} authorization_checked_at={times[-1]} effects=0"  # noqa: E501
    )


@pytest.mark.parametrize(
    "race", ("response_response", "stop_admission", "settlement_stop", "bind_seal", "bind_cancel")
)
def test_shared_old_new_command_keys_converge(planning, race):
    from tests.integration.phase3.test_pr3_04_application import settle

    p = planning
    if race in ("bind_seal", "bind_cancel"):
        task, _ = p.plan()
        c, _ = bind(p, p.create())
        from dataclasses import replace

        c = replace(
            c,
            task_id=task,
            expected_row_version=2,
            command_id=new_uuid7(),
            arguments=replace(
                c.arguments,
                budget_id=new_uuid7(),
                termination_policy_id=new_uuid7(),
                checkpoint_policy_id=new_uuid7(),
            ),
        )
        old = p.command(
            "seal_task_plan" if race == "bind_seal" else "cancel_research_task",
            task,
            2,
            {} if race == "bind_seal" else {"reason": "Concurrent cancel."},
        )
        calls = [
            lambda: service(p).execute(p.principal, c),
            lambda: p.service.execute(p.principal, old),
        ]
        expected = 3
    else:
        task, fake = setup(p)
        expected = 5
        if race == "response_response":
            c = command(
                p,
                task,
                4,
                "request_human_checkpoint",
                {
                    "checkpoint_id": str(new_uuid7()),
                    "step_id": None,
                    "checkpoint_type": "exception",
                    "reason": "Concurrent response.",
                },
            )
            service(p).execute(p.principal, c)
            from researchbase.agent_runtime.application.safety_contracts import (
                RequestCheckpointArguments,
            )

            assert isinstance(c.arguments, RequestCheckpointArguments)
            checkpoint_id = c.arguments.checkpoint_id
            responses = [
                command(
                    p,
                    task,
                    5,
                    "respond_human_checkpoint",
                    {
                        "checkpoint_id": str(checkpoint_id),
                        "expected_checkpoint_row_version": 1,
                        "response": status,
                        "reason": "Competing response.",
                    },
                )
                for status in ("APPROVED", "REJECTED")
            ]
            calls = [lambda c=c: service(p).execute(p.principal, c) for c in responses]
            expected = 6
        elif race == "stop_admission":
            c = command(
                p,
                task,
                4,
                "evaluate_task_termination",
                {"human_stop": True, "reason": "Stop before spend."},
            )
            admission = reserve(p, task, 4)
            calls = [
                lambda: service(p).execute(p.principal, c),
                lambda: fake.execute(p.principal, admission),
            ]
        else:
            reservation = fake.execute(p.principal, reserve(p, task, 4)).reservation_ids[0]
            c = command(
                p,
                task,
                5,
                "evaluate_task_termination",
                {"human_stop": True, "reason": "Stop while settling."},
            )
            measurement = settle(p, task, 5, reservation)
            calls = [
                lambda: service(p).execute(p.principal, c),
                lambda: fake.execute(p.principal, measurement),
            ]
            expected = 6
    with p.engine.connect() as blocker, ThreadPoolExecutor(max_workers=2) as pool:
        blocker.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
            {"key": f"pr301:task:{task}"},
        )
        futures = [pool.submit(call) for call in calls]
        waiters(p.engine)
        blocker.commit()
        successes = 0
        for future in futures:
            try:
                future.result(timeout=5)
                successes += 1
            except ResearchBaseError as exc:
                assert exc.code == ErrorCode.CONCURRENT_MODIFICATION
    assert successes == 1
    assert p.service.get_research_task(p.principal, p.project, task).row_version == expected
