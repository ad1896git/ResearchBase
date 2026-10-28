"""Committed receipt behavior under contention and a lost response."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest
from sqlalchemy import text
from tests.integration.phase3.search_fixtures import _search_env as _search_env
from tests.integration.phase3.test_pr3_03_concurrency import ADVISORY_SQL, observed_wait
from tests.integration.phase3.test_pr3_16_application import assert_create_effects, snapshot
from tests.integration.phase3.test_pr3_16_concurrency import credentials
from tests.unit.phase3.test_experiment_search import pg_command

from researchbase.agent_runtime.application.experiment_search import ExperimentSearchService
from researchbase.agent_runtime.ports.task_repository import UncertainTaskCommit
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.ids import new_uuid7
from researchbase.persistence.uow import SqlAlchemyUnitOfWork


def test_same_command_waiter_replays_one_committed_effect_set(search_env, monkeypatch):
    env = search_env
    command = pg_command(env)
    before = snapshot(env)
    from researchbase.persistence.experiment_search_repository import (
        SqlAlchemyExperimentSearchRepository as Repository,
    )

    original_notify = Repository._notify
    own_receipts = []

    def notify(repo, stage):
        original_notify(repo, stage)
        if stage.operation == "insert" and stage.table == "research_task_command_receipts":
            # The row really exists in this transaction, but own xmin must never
            # be mistaken for a committed saved result during subsequent checks.
            row = repo._session.execute(
                text("SELECT id FROM research_task_command_receipts WHERE command_id=:id"),
                {"id": command.command_id},
            ).scalar_one()
            assert (
                repo.committed_receipt(env.p.project, env.p.principal.actor_id, command.command_id)
                is None
            )
            own_receipts.append(row)

    monkeypatch.setattr(Repository, "_notify", notify)
    service = ExperimentSearchService(env.p.factory, credentials(env, []))
    key = f"pr301:command:{env.p.project}:{env.p.principal.actor_id}:{command.command_id}"
    with env.engine.connect() as holder, ThreadPoolExecutor(2) as pool:
        holder.execute(text(ADVISORY_SQL), {"key": key})
        jobs = [
            pool.submit(service.create_search_session, env.p.principal, command) for _ in range(2)
        ]
        try:
            waiting = observed_wait(env.engine, blocker=holder, query="pg_advisory_xact_lock")
            observed_wait(env.engine, blocker=waiting.pid, query="rb_phase2_lock_project")
        finally:
            holder.rollback()
        results = [job.result(timeout=30) for job in jobs]
    assert len(own_receipts) == 1
    fresh = next(r for r in results if not r.command_result.replayed)
    replay = next(r for r in results if r.command_result.replayed)
    assert replay == replace(fresh, command_result=replace(fresh.command_result, replayed=True))
    saved = snapshot(env)
    assert_create_effects(before, saved, env.task, command.expected_row_version)
    changed = replace(command, arguments=replace(command.arguments, session_id=new_uuid7()))
    with pytest.raises(ResearchBaseError) as error:
        service.create_search_session(env.p.principal, changed)
    assert error.value.code == ErrorCode.IDEMPOTENCY_CONFLICT
    assert snapshot(env) == saved


def test_lost_response_hash_conflict_and_bounded_retries(search_env, monkeypatch):
    env = search_env
    command = pg_command(env)
    before = snapshot(env)
    original = SqlAlchemyUnitOfWork.commit
    commits = []

    def lost_after_commit(uow):
        original(uow)
        commits.append(True)
        raise UncertainTaskCommit("injected lost response after commit")

    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", lost_after_commit)
    service = ExperimentSearchService(env.p.factory, credentials(env, []))
    result = service.create_search_session(env.p.principal, command)
    assert commits == [True] and result.command_result.replayed
    saved = snapshot(env)
    assert_create_effects(before, saved, env.task, command.expected_row_version)
    assert service.replay(env.p.principal, command) == result
    changed = replace(command, arguments=replace(command.arguments, session_id=new_uuid7()))
    with pytest.raises(ResearchBaseError) as error:
        service.create_search_session(env.p.principal, changed)
    assert error.value.code == ErrorCode.IDEMPOTENCY_CONFLICT
    assert snapshot(env) == saved


@pytest.mark.parametrize("failures", [1, 3])
def test_real_database_deadlock_recovery_is_bounded(search_env, monkeypatch, failures):
    """A real project/task lock cycle, not a raised SQLSTATE or Python error.

    The command is already observed waiting on the task key before the holder
    requests its project key. PostgreSQL's waiting command detects the cycle.
    Retry attempts are gated until the preceding holder has rolled back.
    """
    from threading import Event

    from sqlalchemy import event

    from researchbase.persistence.experiment_search_repository import (
        SqlAlchemyExperimentSearchRepository as Repository,
    )

    env = search_env
    command = pg_command(env)
    before = snapshot(env)
    gates = [Event() for _ in range(3)]
    attempts, rejected, transactions, states = [], [], [], []
    original_once = ExperimentSearchService._create_once
    original_notify = Repository._notify

    def once(service, principal, material, ids):
        index = len(attempts)
        attempts.append(ids)
        assert gates[index].wait(8), "next deadlock attempt not released"
        try:
            return original_once(service, principal, material, ids)
        except ResearchBaseError as error:
            rejected.append(error)
            raise

    def notify(repo, stage):
        if stage.operation == "share":
            transactions.append(
                repo._session.execute(text("SELECT pg_current_xact_id()::text")).scalar_one()
            )
        return original_notify(repo, stage)

    def database_error(context):
        states.append(getattr(context.original_exception, "sqlstate", None))

    monkeypatch.setattr(ExperimentSearchService, "_create_once", once)
    monkeypatch.setattr(Repository, "_notify", notify)
    event.listen(env.engine, "handle_error", database_error)
    service = ExperimentSearchService(env.p.factory, credentials(env, []))
    try:
        with ThreadPoolExecutor(2) as pool:
            job = pool.submit(service.create_search_session, env.p.principal, command)
            try:
                for index in range(failures):
                    with env.engine.connect() as holder:
                        holder.execute(text(ADVISORY_SQL), {"key": f"pr301:task:{env.task}"})
                        try:
                            gates[index].set()
                            waiting = observed_wait(
                                env.engine, blocker=holder, query="pg_advisory_xact_lock"
                            )
                            # Use the *same ordinary-role holder transaction* to
                            # complete the real lock cycle. No canonical SQL writes.
                            holder_job = pool.submit(
                                holder.execute,
                                text("SELECT rb_phase2_lock_project(:id)"),
                                {"id": env.p.project},
                            )
                            try:
                                observed_wait(
                                    env.engine,
                                    blocker=waiting.pid,
                                    query="rb_phase2_lock_project",
                                )
                            finally:
                                holder_job.result(timeout=8)
                        finally:
                            holder.rollback()
                if failures < 3:
                    gates[failures].set()
                    result = job.result(timeout=15)
                else:
                    with pytest.raises(ResearchBaseError) as error:
                        job.result(timeout=15)
                    assert error.value.code == ErrorCode.CONCURRENT_MODIFICATION
            finally:
                for gate in gates:
                    gate.set()
    finally:
        event.remove(env.engine, "handle_error", database_error)
    assert states == ["40P01"] * failures
    assert len(attempts) == min(failures + 1, 3)
    assert len(transactions) == len(set(transactions)) == len(attempts)
    assert all(ids == attempts[0] for ids in attempts)
    assert all(error.details == {"retryable_pr301": True} for error in rejected)
    assert len(rejected) == failures
    if failures < 3:
        assert not result.command_result.replayed
        assert result.search_event_id == attempts[0][1]
        assert result.command_result.task_event_ids == (attempts[0][2],)
        assert_create_effects(before, snapshot(env), env.task, command.expected_row_version)
    else:
        assert snapshot(env) == before
    print("REAL_DEADLOCK", states, "fresh transactions", transactions, "stable IDs", attempts)


def test_actual_lock_timeout_is_not_retried(search_env, monkeypatch):
    """Use the fixture's unchanged production 10s lock timeout."""
    from sqlalchemy import event

    env = search_env
    command = pg_command(env)
    before = snapshot(env)
    attempts, states = [], []
    original = ExperimentSearchService._create_once

    def once(service, *args):
        attempts.append(True)
        return original(service, *args)

    def database_error(context):
        states.append(getattr(context.original_exception, "sqlstate", None))

    monkeypatch.setattr(ExperimentSearchService, "_create_once", once)
    event.listen(env.engine, "handle_error", database_error)
    try:
        with ThreadPoolExecutor(1) as pool:
            with env.engine.connect() as holder:
                holder.execute(text(ADVISORY_SQL), {"key": f"pr301:task:{env.task}"})
                try:
                    service = ExperimentSearchService(env.p.factory, credentials(env, []))
                    job = pool.submit(service.create_search_session, env.p.principal, command)
                    observed_wait(env.engine, blocker=holder, query="pg_advisory_xact_lock")
                    with pytest.raises(ResearchBaseError) as error:
                        job.result(timeout=15)
                finally:
                    holder.rollback()
    finally:
        event.remove(env.engine, "handle_error", database_error)
    assert error.value.code == ErrorCode.CONCURRENT_MODIFICATION
    assert attempts == [True] and states == ["55P03"]
    assert snapshot(env) == before


@pytest.mark.parametrize("state,count", [("40001", 3), ("40P01", 3), ("55P03", 1), ("57014", 1)])
def test_injected_server_sqlstate_retry_convention(search_env, monkeypatch, state, count):
    """Classification probes only; RAISE is not a database-induced conflict."""

    from researchbase.persistence.experiment_search_repository import (
        SqlAlchemyExperimentSearchRepository as Repository,
    )

    env = search_env
    command = pg_command(env)
    before, transactions = snapshot(env), []
    original = Repository.lock_write

    def lock(repo, *args, **kwargs):
        original(repo, *args, **kwargs)
        transactions.append(
            repo._session.execute(text("SELECT pg_current_xact_id()::text")).scalar_one()
        )
        # State is one of the fixed pytest parameters, never caller input.
        repo._session.execute(
            text(
                "DO $$ BEGIN RAISE EXCEPTION 'injected retry probe' "
                f"USING ERRCODE='{state}'; END $$"
            )
        )

    monkeypatch.setattr(Repository, "lock_write", lock)
    with pytest.raises(ResearchBaseError) as error:
        ExperimentSearchService(env.p.factory, credentials(env, [])).create_search_session(
            env.p.principal, command
        )
    assert error.value.code == ErrorCode.CONCURRENT_MODIFICATION
    assert len(transactions) == len(set(transactions)) == count
    assert snapshot(env) == before
