"""Proposed missing C1 admission, recovery, and finalization races; NOT_RUN."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Event, Lock, local
from time import monotonic
from unittest.mock import patch
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from researchbase.application.literature_search_execution import LiteratureSearchExecutionService
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.literature_search_plan_repository import (
    SqlAlchemyLiteratureSearchPlanRepository,
)
from researchbase.persistence.uow import SqlAlchemyUnitOfWork
from tests.integration.phase2.test_pr2_03_literature_search_plan_application import (
    _AlwaysValidCredential,
)
from tests.integration.phase2.test_pr2_04_execution_recovery import ReservedBeforeInvocation
from tests.integration.phase2.test_pr2_04_idempotency_completion import (
    InterruptedAfterCommit,
    StopAfterOutcome,
)
from tests.integration.phase2.test_pr2_04_idempotency_coverage import (
    _command,
    _execution_setup,
    _service,
    _snapshot,
)
from tests.integration.phase2.test_pr2_04_ownership_races import _sqlstates
from tests.unit.phase2.test_pr2_04_provider_coverage import ScriptedProvider, success


class ForcedRollback(RuntimeError):
    pass


@pytest.fixture
def race_case(phase2_database_url):
    yield from _execution_setup(phase2_database_url)


def _race_callbacks(engine, provider, winner, callbacks, trace, *, rollback=False):
    """Recovery implementation of the documented real-UoW contender contract."""
    ready, release, loser_done = Event(), Event(), Event()
    context, guard = local(), Lock()
    attempts, commits = [], []
    held = False

    class Uow(SqlAlchemyUnitOfWork):
        def __enter__(self):
            super().__enter__()
            with guard:
                self.observation = {
                    "label": context.label,
                    "db_attempt": 1 + sum(a["label"] == context.label for a in attempts),
                    "backend_pid": None,
                    "sqlstates": [],
                }
                attempts.append(self.observation)
            context.uow = self
            return self

        def commit(self):
            nonlocal held
            first = context.label == winner and not held
            if first:
                held = True
                ready.set()
                assert release.wait(15)
                if rollback:
                    raise ForcedRollback("recovery test-owned precommit rollback")
            super().commit()
            with guard:
                self.observation["commit_order"] = len(commits) + 1
                commits.append(context.label)
            if first:
                assert loser_done.wait(20)

        def __exit__(self, *args):
            error = args[1] if len(args) > 1 else None
            if error is not None:
                self.observation.update(
                    exit_type=type(error).__name__,
                    canonical_error=error.code.value
                    if isinstance(error, ResearchBaseError)
                    else None,
                    sqlstates=_sqlstates(error),
                )
            try:
                return super().__exit__(*args)
            except Exception as error:
                self.observation.update(
                    exit_type=type(error).__name__,
                    canonical_error=error.code.value
                    if isinstance(error, ResearchBaseError)
                    else None,
                    sqlstates=_sqlstates(error),
                )
                raise
            finally:
                self.observation["closed"] = self._session is None

    def factory():
        return Uow(
            sessionmaker(bind=engine, expire_on_commit=False, autoflush=False),
            pr204_error_normalization=True,
        )

    service = LiteratureSearchExecutionService(
        factory, provider, credential_verifier=_AlwaysValidCredential()
    )
    original = SqlAlchemyLiteratureSearchPlanRepository.lock_project
    original_authorize = SqlAlchemyLiteratureSearchPlanRepository.authorize
    original_at = SqlAlchemyLiteratureSearchPlanRepository.at

    def lock_project(repo, project):
        pid, transaction = repo._session.execute(
            text("SELECT pg_backend_pid(), pg_current_xact_id()::text")
        ).one()
        context.uow.observation.update(backend_pid=pid, transaction_id=transaction)
        return original(repo, project)

    def observed_authorize(repo, principal, project):
        rows = original_authorize(repo, principal, project)
        context.uow.observation.setdefault("authority_reads", []).append(
            [dict(row) for row in rows]
        )
        return rows

    def observed_at(repo):
        at = original_at(repo)
        context.uow.observation.setdefault("authorization_times", []).append(at)
        return at

    def worker(label):
        context.label = label
        try:
            return callbacks[label](service)
        except ForcedRollback:
            return "ROLLED_BACK"
        except ResearchBaseError as error:
            return error.code
        finally:
            if label != winner:
                loser_done.set()

    loser = "B" if winner == "A" else "A"
    with (
        patch.object(SqlAlchemyLiteratureSearchPlanRepository, "lock_project", lock_project),
        patch.object(SqlAlchemyLiteratureSearchPlanRepository, "authorize", observed_authorize),
        patch.object(SqlAlchemyLiteratureSearchPlanRepository, "at", observed_at),
    ):
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(worker, winner)
            try:
                assert ready.wait(15)
                second = pool.submit(worker, loser)
                deadline = monotonic() + 15
                wait = None
                with engine.connect() as observer:
                    while monotonic() < deadline:
                        pids = [
                            a["backend_pid"]
                            for a in attempts
                            if a["label"] == loser and a["backend_pid"]
                        ]
                        if pids:
                            observer.execute(text("SELECT pg_stat_clear_snapshot()"))
                            wait = (
                                observer.execute(
                                    text(
                                        "SELECT wait_event_type, pg_blocking_pids(pid) AS blockers FROM pg_stat_activity WHERE pid=:pid"  # noqa: E501
                                    ),
                                    {"pid": pids[-1]},
                                )
                                .mappings()
                                .first()
                            )
                            if wait and wait["wait_event_type"] == "Lock" and wait["blockers"]:
                                break
                        Event().wait(0.01)
                    assert wait and wait["wait_event_type"] == "Lock" and wait["blockers"]
                    assert not second.done()
                trace.record(observed_wait=dict(wait), winner=winner, rollback=rollback)
            finally:
                release.set()
            results = {winner: first.result(timeout=30), loser: second.result(timeout=30)}
    assert all(a["closed"] for a in attempts) and engine.pool.checkedout() == 0
    trace.record(transaction_attempts=attempts, commit_order=commits)
    return results


def _assert_unique_terminal(rows, expected):
    assert rows["executions"][0]["status"] == expected
    assert sum(event["kind"] == "FINISHED" for event in rows["events"]) == 1


def _wait_recovery_deadline(engine, deadline, trace):
    # Reservation clocks are immutable. Cross their actual PG deadline without UPDATE/patch.
    with engine.connect() as observer:
        before = observer.execute(text("SELECT clock_timestamp()")).scalar_one()
    remaining = max(0.0, (deadline - before).total_seconds())
    assert remaining < 35, "fixture must reserve timeout_seconds=1"
    Event().wait(remaining + 0.03)
    with engine.connect() as observer:
        after = observer.execute(text("SELECT clock_timestamp()")).scalar_one()
    assert after >= deadline
    trace.record(recovery_deadline=deadline, database_before_wait=before, database_after_wait=after)


@pytest.mark.parametrize("run", range(1, 6))
@pytest.mark.parametrize("winner", ["A", "B"], ids=["A-first", "B-first"])
@pytest.mark.parametrize("rollback", [False, True], ids=["commit", "rollback"])
@pytest.mark.pr204_requirements("PR204-IDEM-01", "PR204-CONC-06")
def test_pg_same_cancel_key_contenders_before_c1_commit_or_rollback(
    race_case, run, winner, rollback, pr204_trace
):
    engine, service, provider, principal, project, create = race_case
    execution_id = UUID(service.create(create)["execution_id"])
    command = _command("cancel", principal, project, execution_id)
    before = _snapshot(engine, project)

    def c1(svc):
        # Invoke the real C1 transaction boundary; leave C2 deliberately undriven.
        dto, finalize = svc._retry_db(
            lambda: svc._cancel_or_recover(
                command.execution_id,
                command.actor_id,
                command.deployment_id,
                command.request_id,
                False,
                command.project_id,
                command.principal,
            )
        )
        return {"admission": dto, "drive_c2": finalize}

    results = _race_callbacks(
        engine, provider, winner, {"A": c1, "B": c1}, pr204_trace, rollback=rollback
    )
    admitted = "B" if rollback and winner == "A" else "A" if rollback else winner
    if rollback:
        assert results[winner] == "ROLLED_BACK"
    else:
        assert isinstance(results["A"], dict)
        assert isinstance(results["B"], dict)
        assert results["A"]["admission"] == results["B"]["admission"]
        winning_result = results[winner]
        losing_result = results["B" if winner == "A" else "A"]
        assert isinstance(winning_result, dict)
        assert isinstance(losing_result, dict)
        assert winning_result["drive_c2"] is True
        assert losing_result["drive_c2"] is False
    admitted_result = results[admitted]
    assert isinstance(admitted_result, dict)
    admission = admitted_result["admission"]
    after_c1 = _snapshot(engine, project)
    assert after_c1["executions"][0]["status"] == "PLANNED"
    assert after_c1["executions"][0]["row_version"] == 2
    assert len(after_c1["receipts"]) == 2
    assert sum(e["kind"] == "CANCEL_REQUESTED" for e in after_c1["events"]) == 1
    assert not any(e["kind"] == "FINISHED" for e in after_c1["events"])
    assert after_c1["attempts"] == after_c1["queries"] == after_c1["results"] == []
    assert service.cancel(command) == admission and _snapshot(engine, project) == after_c1
    service.recover(_command("recover", principal, project, execution_id))
    after_c2 = _snapshot(engine, project)
    _assert_unique_terminal(after_c2, "CANCELLED")
    assert after_c2["executions"][0]["row_version"] == 3
    assert service.cancel(command) == admission and _snapshot(engine, project) == after_c2
    assert provider.calls == []
    pr204_trace.record(
        run=run,
        ordering=winner,
        winner_rolled_back=rollback,
        before=before,
        after_c1=after_c1,
        after_c2=after_c2,
        provider_calls=0,
        admission=admission,
    )


@pytest.mark.parametrize("run", range(1, 6))
@pytest.mark.parametrize("winner", ["A", "B"], ids=["A-first", "B-first"])
@pytest.mark.pr204_requirements("PR204-CONC-03", "PR204-CONC-06")
def test_pg_expired_reserved_recovery_contenders_seal_and_finish_once(
    race_case, run, winner, pr204_trace
):
    engine, service, provider, principal, project, create = race_case
    execution_id = UUID(service.create(replace(create, timeout_seconds=1))["execution_id"])
    _service(engine, provider, ReservedBeforeInvocation).execute(
        _command("execute", principal, project, execution_id)
    )
    before = _snapshot(engine, project)
    _wait_recovery_deadline(engine, before["attempts"][0]["recovery_after"], pr204_trace)
    commands = {
        label: _command("recover", principal, project, execution_id) for label in ("A", "B")
    }
    callbacks = {label: (lambda svc, cmd=cmd: svc.recover(cmd)) for label, cmd in commands.items()}
    results = _race_callbacks(engine, provider, winner, callbacks, pr204_trace)
    assert all(isinstance(value, dict) for value in results.values())
    after = _snapshot(engine, project)
    _assert_unique_terminal(after, "UNKNOWN")
    assert len(after["attempts"]) == 1 and after["attempts"][0]["status"] == "UNKNOWN"
    assert after["attempts"][0]["row_version"] == 2
    assert after["attempts"][0]["invoked_at"] is None
    assert sum(e["kind"] == "OUTCOME_RECORDED" for e in after["events"]) == 1
    assert after["queries"] == after["results"] == [] and provider.calls == []
    assert len(after["receipts"]) == len(before["receipts"]) + 2
    for label, command in commands.items():
        assert service.recover(command) == results[label]
    assert _snapshot(engine, project) == after
    pr204_trace.record(run=run, ordering=winner, before=before, after=after, provider_calls=0)


@pytest.mark.parametrize("run", range(1, 6))
@pytest.mark.parametrize("winner", ["A", "B"], ids=["outcome-first", "recovery-first"])
@pytest.mark.pr204_requirements("PR204-CONC-03", "PR204-CONC-06")
def test_pg_saved_owner_response_versus_expired_recovery_has_one_durable_outcome(
    race_case, run, winner, pr204_trace
):
    engine, _, _, principal, project, create = race_case
    provider = ScriptedProvider(
        [success("normalization evidence", "provider-a", hits=2)], "provider-a"
    )
    captured = []

    class CaptureBeforeTxB(LiteratureSearchExecutionService):
        def _persist_outcome(self, *args, **kwargs):
            captured.append((args, kwargs))
            raise InterruptedAfterCommit("test-held live owner response before TX B")

    owner = _service(engine, provider, CaptureBeforeTxB)
    execution_id = UUID(owner.create(replace(create, timeout_seconds=1))["execution_id"])
    with pytest.raises(InterruptedAfterCommit):
        owner.execute(_command("execute", principal, project, execution_id))
    assert len(captured) == len(provider.calls) == 1
    before = _snapshot(engine, project)
    assert before["attempts"][0]["status"] == "RESERVED"
    _wait_recovery_deadline(engine, before["attempts"][0]["recovery_after"], pr204_trace)
    args, kwargs = captured[0]
    command = _command("recover", principal, project, execution_id)

    def persist(svc):
        terminal, retry, more, delay = svc._retry_db(lambda: svc._persist_outcome(*args, **kwargs))
        return {
            "terminal": terminal.value if terminal else None,
            "retry": retry,
            "more": more,
            "delay": delay,
        }

    results = _race_callbacks(
        engine, provider, winner, {"A": persist, "B": lambda svc: svc.recover(command)}, pr204_trace
    )
    assert isinstance(results["B"], dict)
    service = _service(engine, provider)
    after = _snapshot(engine, project)
    if winner == "A":
        assert isinstance(results["A"], dict)
        assert results["A"]["terminal"] == "SUCCEEDED"
        _assert_unique_terminal(after, "SUCCEEDED")
        assert len(after["queries"]) == 1 and len(after["results"]) == 2
        assert after["attempts"][0]["status"] == "SUCCEEDED"
    else:
        # Recovery seals before TX C; held first commit makes owner observe sealed UNKNOWN.
        assert results["A"] is ErrorCode.IMMUTABLE_RECORD
        _assert_unique_terminal(after, "UNKNOWN")
        assert after["queries"] == after["results"] == []
        assert after["attempts"][0]["status"] == "UNKNOWN"
    assert len(after["attempts"]) == 1 and after["attempts"][0]["row_version"] == 2
    assert sum(e["kind"] == "OUTCOME_RECORDED" for e in after["events"]) == 1
    assert len(provider.calls) == 1
    assert service.recover(command) == results["B"] and _snapshot(engine, project) == after
    pr204_trace.record(run=run, ordering=winner, before=before, after=after, provider_calls=1)


@pytest.mark.parametrize("run", range(1, 6))
@pytest.mark.parametrize("winner", ["A", "B"], ids=["cancel-first", "finalize-first"])
@pytest.mark.pr204_requirements("PR204-CONC-04", "PR204-CONC-06")
def test_pg_cancel_c1_versus_tx_c_has_one_compatible_terminal_transition(
    race_case, run, winner, pr204_trace
):
    from researchbase.domain.literature_search_execution import ExecutionStatus

    engine, _, _, principal, project, create = race_case
    provider = ScriptedProvider(
        [success("normalization evidence", "provider-a", hits=2)], "provider-a"
    )
    stopped = _service(engine, provider, StopAfterOutcome)
    execution_id = UUID(stopped.create(create)["execution_id"])
    with pytest.raises(InterruptedAfterCommit):
        stopped.execute(_command("execute", principal, project, execution_id))
    before = _snapshot(engine, project)
    assert before["executions"][0]["status"] == "RUNNING"
    command = _command("cancel", principal, project, execution_id)

    def finalize(svc):
        svc._retry_db(
            lambda: svc._finalize_execution(
                execution_id, principal.actor_id, ExecutionStatus.SUCCEEDED, principal, project
            )
        )
        return "FINALIZATION_RETURNED"

    results = _race_callbacks(
        engine, provider, winner, {"A": lambda svc: svc.cancel(command), "B": finalize}, pr204_trace
    )
    after = _snapshot(engine, project)
    _assert_unique_terminal(after, "CANCELLED" if winner == "A" else "SUCCEEDED")
    assert after["attempts"] == before["attempts"]
    assert after["queries"] == before["queries"] and after["results"] == before["results"]
    assert len(provider.calls) == 1
    assert results["B"] == "FINALIZATION_RETURNED"
    assert sum(e["kind"] == "CANCEL_REQUESTED" for e in after["events"]) == (
        1 if winner == "A" else 0
    )
    if winner == "A":
        assert isinstance(results["A"], dict)
        assert len(after["receipts"]) == len(before["receipts"]) + 1
    else:
        assert results["A"] is ErrorCode.INVALID_STATE_TRANSITION
        assert after["receipts"] == before["receipts"]
    pr204_trace.record(run=run, ordering=winner, before=before, after=after, provider_calls=1)
