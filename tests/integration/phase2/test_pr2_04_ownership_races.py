"""Five-run PostgreSQL ownership races; serialization retries stay observable."""

from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from threading import Event, Lock, local
from time import monotonic
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from scripts.pr2_04_pytest_evidence import FactRecorder
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from tests.integration.phase2.test_pr2_03_literature_search_plan_application import (
    _AlwaysValidCredential,
)
from tests.integration.phase2.test_pr2_03_review_guards import _freeze, _setup

from researchbase.application.literature_search_execution import (
    CancelLiteratureSearchExecution,
    CreateLiteratureSearchExecution,
    ExecuteLiteratureSearchExecution,
    LiteratureSearchExecutionService,
    RecoverLiteratureSearchExecution,
)
from researchbase.application.literature_search_provider import FakeSearchCapability
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.literature_search_plan_repository import (
    SqlAlchemyLiteratureSearchPlanRepository,
)
from researchbase.persistence.uow import SqlAlchemyUnitOfWork


def _sqlstates(error):
    values, seen = [], set()
    while error is not None and id(error) not in seen:
        seen.add(id(error))
        state = getattr(error, "sqlstate", None)
        if state is not None:
            values.append(state)
        error = getattr(error, "orig", None) or error.__cause__ or error.__context__
    return values


def _race(engine, provider, winner, commands, operation, trace):
    """Hold a real production admission commit, not an invented inverse lock."""
    ready, release = Event(), Event()
    context = local()
    guard = Lock()
    waiting = Queue()
    attempts = []
    commits = []
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
            if context.label == winner and not held:
                held = True
                ready.set()
                assert release.wait(15), "race controller did not release production commit"
            super().commit()
            with guard:
                self.observation["commit_order"] = len(commits) + 1
                commits.append(context.label)

        def __exit__(self, *args):
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

    factory = lambda: Uow(  # noqa: E731
        sessionmaker(bind=engine, expire_on_commit=False, autoflush=False),
        pr204_error_normalization=True,
    )
    service = LiteratureSearchExecutionService(
        factory, provider, credential_verifier=_AlwaysValidCredential()
    )
    original = SqlAlchemyLiteratureSearchPlanRepository.lock_project

    def observed_lock(repo, project_id):
        observation = context.uow.observation
        pid, xid = repo._session.execute(text("SELECT pg_backend_pid(),txid_current()")).one()
        observation.update(backend_pid=pid, transaction_id=xid, project_lock_entered=True)
        if context.label != winner:
            waiting.put(observation)
        original(repo, project_id)
        observation["project_lock_resumed"] = True

    def worker(label):
        context.label = label
        try:
            selected = operation[label] if isinstance(operation, dict) else operation
            return getattr(service, selected)(commands[label])
        except ResearchBaseError as error:
            return error.code

    with patch.object(SqlAlchemyLiteratureSearchPlanRepository, "lock_project", observed_lock):
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(worker, winner)
            second = None
            try:
                assert ready.wait(10), "winning production transaction did not reach commit"
                second = pool.submit(worker, "B" if winner == "A" else "A")
                blocked = waiting.get(timeout=10)
                winner_pid = next(a["backend_pid"] for a in attempts if a["label"] == winner)
                deadline = monotonic() + 10
                wait = None
                while monotonic() < deadline:
                    with engine.connect() as observer:
                        wait = (
                            observer.execute(
                                text(
                                    "SELECT wait_event_type,pg_blocking_pids(pid) AS blockers "
                                    "FROM pg_stat_activity WHERE pid=:pid"
                                ),
                                {"pid": blocked["backend_pid"]},
                            )
                            .mappings()
                            .one()
                        )
                    if wait["wait_event_type"] == "Lock" and winner_pid in wait["blockers"]:
                        break
                    Event().wait(0.01)
                assert wait is not None
                trace.record(
                    phase="observed_postgres_wait",
                    winner=winner,
                    waiting_attempt=blocked.copy(),
                    winner_pid=winner_pid,
                    wait_event_type=wait["wait_event_type"],
                    blocking_pids=list(wait["blockers"]),
                )
                assert wait["wait_event_type"] == "Lock" and winner_pid in wait["blockers"]
                blocked.update(postgres_wait_observed=True, blocker_pid=winner_pid)
            finally:
                release.set()
            results = {winner: first.result(timeout=20)}
            assert second is not None
            results["B" if winner == "A" else "A"] = second.result(timeout=20)
    trace.record(
        phase="race_complete",
        attempts=attempts,
        commit_order=commits,
        results={k: v.value if isinstance(v, ErrorCode) else v for k, v in results.items()},
        provider_calls=len(provider.calls),
    )
    assert commits[0] == winner
    assert all(a["closed"] for a in attempts)
    assert all(set(a["sqlstates"]) <= {"40001"} for a in attempts)
    assert all(
        a.get("canonical_error")
        in {None, "CONCURRENT_MODIFICATION", "IDEMPOTENCY_CONFLICT", "INVALID_STATE_TRANSITION"}
        for a in attempts
    )
    return results


@pytest.mark.parametrize("run", range(1, 6))
@pytest.mark.parametrize("winner", ["A", "B"], ids=["A-first", "B-first"])
@pytest.mark.parametrize("changed", [False, True], ids=["exact", "payload-conflict"])
@pytest.mark.pr204_requirements("PR204-CONC-01", "PR204-CONC-06")
def test_pg_duplicate_create_has_one_durable_execution_after_observed_wait(
    phase2_database_url, run, winner, changed, pr204_trace: FactRecorder
):
    engine, plans, principal, project, plan, version = _setup(phase2_database_url)
    try:
        _freeze(engine, plans, principal, project, plan, version)
        request = uuid4()
        commands = {
            label: CreateLiteratureSearchExecution(
                project,
                version,
                principal.actor_id,
                principal.deployment_id,
                request,
                "provider-a",
                "1",
                ("different query" if changed and label == "B" else "normalization evidence",),
                principal=principal,
            )
            for label in ("A", "B")
        }
        provider = FakeSearchCapability(capability_id="provider-a")
        pr204_trace.record(run=run, ordering=winner, changed_payload=changed)
        results = _race(engine, provider, winner, commands, "create", pr204_trace)
        if changed:
            assert results["B" if winner == "A" else "A"] is ErrorCode.IDEMPOTENCY_CONFLICT
        else:
            assert results["A"] == results["B"]
        assert isinstance(results[winner], dict)
        with engine.connect() as c:
            executions = c.execute(
                text("SELECT count(*) FROM literature_search_executions WHERE project_id=:id"),
                {"id": project},
            ).scalar_one()
            receipts = c.execute(
                text(
                    "SELECT count(*) FROM literature_search_execution_command_receipts "
                    "WHERE request_id=:id"
                ),
                {"id": request},
            ).scalar_one()
        pr204_trace.record(
            execution_count=executions, receipt_count=receipts, provider_calls=len(provider.calls)
        )
        assert executions == 1 and receipts == 1 and provider.calls == []
    finally:
        engine.dispose()


@pytest.mark.parametrize("run", range(1, 6))
@pytest.mark.parametrize("winner", ["A", "B"], ids=["A-first", "B-first"])
@pytest.mark.pr204_requirements("PR204-CONC-03", "PR204-CRASH-07", "PR204-CONC-06")
def test_pg_interrupted_cancel_recovery_contenders_finalize_once(
    phase2_database_url, run, winner, pr204_trace: FactRecorder
):
    engine, plans, principal, project, plan, version = _setup(phase2_database_url)
    try:
        _freeze(engine, plans, principal, project, plan, version)
        provider = FakeSearchCapability(capability_id="provider-a")

        def crash_after_c1():
            raise RuntimeError("crash after committed C1")

        service = LiteratureSearchExecutionService(
            lambda: SqlAlchemyUnitOfWork(sessionmaker(bind=engine), pr204_error_normalization=True),
            provider, credential_verifier=_AlwaysValidCredential(), after_cancel_admission=crash_after_c1,
        )
        admission = service.create(CreateLiteratureSearchExecution(
            project, version, principal.actor_id, principal.deployment_id, uuid4(), "provider-a", "1",
            ("normalization evidence",), principal=principal,
        ))
        execution_id = UUID(admission["execution_id"])
        cancel = CancelLiteratureSearchExecution(
            execution_id, principal.actor_id, principal.deployment_id, uuid4(), project_id=project,
            principal=principal,
        )
        with pytest.raises(RuntimeError, match="crash after committed C1"):
            service.cancel(cancel)
        before = service.get_provenance(principal, project, execution_id)
        assert before["execution"]["status"] == "PLANNED" and before["execution"]["row_version"] == 2
        assert [e["kind"] for e in before["events"]] == ["CREATED", "CANCEL_REQUESTED"]
        assert before["attempts"] == [] and before["queries"] == [] and before["results"] == []
        assert len(before["receipts"]) == 2
        # Exact C1 replay is read-only and does not run the crash hook or C2.
        assert service.cancel(cancel)["accepted_row_version"] == 2
        assert service.get_provenance(principal, project, execution_id) == before
        commands = {label: RecoverLiteratureSearchExecution(
            execution_id, principal.actor_id, principal.deployment_id, uuid4(), project_id=project,
            principal=principal,
        ) for label in ("A", "B")}
        pr204_trace.record(run=run, ordering=winner, after_c1=before)
        results = _race(engine, provider, winner, commands, "recover", pr204_trace)
        assert all(isinstance(dto, dict) and dto["accepted_row_version"] == 3 for dto in results.values())
        after = service.get_provenance(principal, project, execution_id)
        pr204_trace.record(after_recovery=after, provider_calls=len(provider.calls))
        assert after["execution"]["status"] == "CANCELLED" and after["execution"]["row_version"] == 3
        assert after["execution"]["started_at"] is None
        assert [e["kind"] for e in after["events"]] == ["CREATED", "CANCEL_REQUESTED", "FINISHED"]
        assert after["attempts"] == [] and after["queries"] == [] and after["results"] == []
        assert len(after["receipts"]) == 4 and provider.calls == []
        for command in commands.values():
            assert service.recover(command)["accepted_row_version"] == 3
        assert service.get_provenance(principal, project, execution_id) == after
    finally:
        engine.dispose()


@pytest.mark.parametrize("run", range(1, 6))
@pytest.mark.parametrize("winner", ["A", "B"], ids=["A-first", "B-first"])
@pytest.mark.pr204_requirements("PR204-CONC-02", "PR204-CONC-06")
def test_pg_competing_execute_keys_get_only_one_reservation_owner(
    phase2_database_url, run, winner, pr204_trace: FactRecorder
):
    engine, plans, principal, project, plan, version = _setup(phase2_database_url)
    try:
        _freeze(engine, plans, principal, project, plan, version)
        provider = FakeSearchCapability(capability_id="provider-a")
        service = LiteratureSearchExecutionService(
            lambda: SqlAlchemyUnitOfWork(sessionmaker(bind=engine), pr204_error_normalization=True),
            provider,
            credential_verifier=_AlwaysValidCredential(),
        )
        admission = service.create(
            CreateLiteratureSearchExecution(
                project,
                version,
                principal.actor_id,
                principal.deployment_id,
                uuid4(),
                "provider-a",
                "1",
                ("normalization evidence",),
                principal=principal,
            )
        )
        execution_id = UUID(admission["execution_id"])
        commands = {
            label: ExecuteLiteratureSearchExecution(
                execution_id,
                principal.actor_id,
                principal.deployment_id,
                uuid4(),
                project_id=project,
                principal=principal,
            )
            for label in ("A", "B")
        }
        pr204_trace.record(run=run, ordering=winner)
        results = _race(engine, provider, winner, commands, "execute", pr204_trace)
        # A loser sees RESERVED or a completed execution, never receives dispatch ownership.
        assert isinstance(results[winner], dict)
        assert (
            isinstance(results["B" if winner == "A" else "A"], dict)
            or results["B" if winner == "A" else "A"] is ErrorCode.INVALID_STATE_TRANSITION
        )
        provenance = service.get_provenance(principal, project, execution_id)
        pr204_trace.record(provenance=provenance, provider_calls=len(provider.calls))
        assert len(provider.calls) == 1
        assert len(provenance["attempts"]) == 1 and len(provenance["queries"]) == 1
        assert provenance["execution"]["status"] == "SUCCEEDED"
        assert sum(e["kind"] == "FINISHED" for e in provenance["events"]) == 1
    finally:
        engine.dispose()


@pytest.mark.parametrize("run", range(1, 6))
@pytest.mark.parametrize("winner", ["A", "B"], ids=["cancel-first", "reservation-first"])
@pytest.mark.pr204_requirements("PR204-CONC-04", "PR204-CANCEL-03", "PR204-CONC-06")
def test_pg_cancellation_versus_first_reservation_has_one_terminal_event(
    phase2_database_url, run, winner, pr204_trace: FactRecorder
):
    engine, plans, principal, project, plan, version = _setup(phase2_database_url)
    try:
        _freeze(engine, plans, principal, project, plan, version)
        provider = FakeSearchCapability(capability_id="provider-a")
        service = LiteratureSearchExecutionService(
            lambda: SqlAlchemyUnitOfWork(sessionmaker(bind=engine), pr204_error_normalization=True),
            provider, credential_verifier=_AlwaysValidCredential(),
        )
        admission = service.create(CreateLiteratureSearchExecution(
            project, version, principal.actor_id, principal.deployment_id, uuid4(), "provider-a", "1",
            ("normalization evidence",), principal=principal,
        ))
        execution_id = UUID(admission["execution_id"])

        def wait_for_durable_intent(request):
            # For reservation-first, allow C1 to commit before returning a known
            # provider response. This is a provider barrier, never a held DB UoW.
            deadline = monotonic()+10
            while monotonic() < deadline:
                with engine.connect() as c:
                    intent = c.execute(text(
                        "SELECT count(*) FROM literature_search_execution_events "
                        "WHERE execution_id=:id AND kind='CANCEL_REQUESTED'"
                    ), {"id": execution_id}).scalar_one()
                if intent == 1:
                    return
                Event().wait(0.01)
            raise AssertionError("durable cancellation intent did not arrive")

        provider.observer = wait_for_durable_intent
        commands = {
            "A": CancelLiteratureSearchExecution(execution_id, principal.actor_id, principal.deployment_id,
                uuid4(), project_id=project, principal=principal),
            "B": ExecuteLiteratureSearchExecution(execution_id, principal.actor_id, principal.deployment_id,
                uuid4(), project_id=project, principal=principal),
        }
        pr204_trace.record(run=run, first_admission=winner)
        results = _race(engine, provider, winner, commands, {"A":"cancel", "B":"execute"}, pr204_trace)
        assert isinstance(results["A"], dict)
        if winner == "A":
            assert results["B"] is ErrorCode.INVALID_STATE_TRANSITION
            assert provider.calls == []
        else:
            assert isinstance(results["B"], dict) and len(provider.calls) == 1
        provenance = service.get_provenance(principal, project, execution_id)
        pr204_trace.record(provenance=provenance, provider_calls=len(provider.calls))
        assert provenance["execution"]["status"] == "CANCELLED"
        assert sum(e["kind"] == "CANCEL_REQUESTED" for e in provenance["events"]) == 1
        assert sum(e["kind"] == "FINISHED" for e in provenance["events"]) == 1
        assert len(provenance["attempts"]) == (0 if winner == "A" else 1)
        assert len(provenance["queries"]) == (0 if winner == "A" else 1)
        assert provenance["results"] == []
    finally:
        engine.dispose()
