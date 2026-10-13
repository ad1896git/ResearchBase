"""Required-lock expiry across actual execution phases and their DB retries.

A worker past the project lock prevents concurrent role mutation by design.
Consequently later-lock role cases close a legitimate finite RESEARCHER interval
before the retry starts, append its exact CLOSED event, and cross that interval's
end while blocked. Existing create/project-lock tests cover concurrent closure.
No authority guard or production clock is replaced.
"""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace
from datetime import timedelta
from queue import Queue
from threading import Event, get_ident, local
from time import monotonic
from uuid import UUID, uuid4

import pytest
from scripts.pr2_04_pytest_evidence import FactRecorder
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from researchbase.application.literature_search_execution import LiteratureSearchExecutionService
from researchbase.application.phase2_identity import AssignProjectRole
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.literature_search_plan_repository import (
    SqlAlchemyLiteratureSearchPlanRepository,
)
from researchbase.persistence.uow import SqlAlchemyUnitOfWork
from tests.integration.phase2.test_pr2_00_challenges import _service as _identity_service
from tests.integration.phase2.test_pr2_03_effective_authority import _authority_rows, _provision
from tests.integration.phase2.test_pr2_04_execution_recovery import OutcomeBeforeFinalization
from tests.integration.phase2.test_pr2_04_idempotency_coverage import (
    _command,
    _execution_setup,
    _service,
    _snapshot,
)
from tests.unit.phase2.test_pr2_04_provider_coverage import ScriptedProvider, success

# Each pair names a required lock the real phase actually acquires. No read is
# claimed to acquire an execution lock when its implementation does not do so.
PHASE_LOCKS = (
    [
        (phase, lock)
        for phase in ("execute_admission", "cancel_admission", "recover_admission")
        for lock in ("receipt", "execution", "authority")
    ]
    + [
        (phase, lock)
        for phase in (
            "outcome",
            "finalization",
            "cancel_finalization",
            "recovery_finalization",
            "next_reservation",
            "disclosure",
        )
        for lock in ("execution", "authority")
    ]
    + [(phase, "authority") for phase in ("get", "list", "get_provenance")]
)
READS = {"get", "list", "get_provenance"}


@pytest.fixture
def temporal_completion_case(phase2_database_url):
    yield from _execution_setup(phase2_database_url)


class PhaseExpiry:
    def __init__(self, phase, recorder):
        self.target = phase
        self.recorder = recorder
        self._thread_context = local()
        self.current = None
        self.attempts = []
        self.ready = Event()
        self.release = Event()
        self.transactions = Queue()
        self.credential_samples = []
        self.credential_expires_at = None
        self.injected = False

    @property
    def current(self):
        return getattr(self._thread_context, "current", None)

    @current.setter
    def current(self, value):
        self._thread_context.current = value

    @contextmanager
    def enter(self, phase):
        if phase != self.target:
            yield
            return
        entry = {"attempt": len(self.attempts) + 1, "phase": phase, "order": []}
        self.attempts.append(entry)
        self.current = entry
        try:
            # Mutating phases first prove effective authority in a real DB
            # attempt, then fail with 40001 before the first effect. The actual
            # Application retry waits here while the coordinator acquires the
            # specific receipt/execution/authority lock. Public reads do not
            # have this retry wrapper, so their first attempt waits directly.
            if self.injected or phase in READS:
                self.ready.set()
                assert self.release.wait(15), "coordinator did not release target phase"
            yield
        except ResearchBaseError as error:
            entry["error_code"] = error.code.value
            raise
        finally:
            self.current = None

    def is_valid(self, principal, at):
        valid = self.credential_expires_at is None or at < self.credential_expires_at
        self.credential_samples.append(
            {
                "attempt": self.current["attempt"] if self.current else None,
                "at": at,
                "valid": valid,
                "thread_id": get_ident(),
                "source": "application_phase" if self.current else "coordinator_positive_control",
            }
        )
        return valid

    def service(self, engine, provider):
        control = self

        class ObservedUow(SqlAlchemyUnitOfWork):
            def __enter__(self):
                super().__enter__()
                self.observation = control.current
                if self.observation is None:
                    return self
                plan = self.literature_search_plan
                execution = self.literature_search_execution
                lock_project = plan.lock_project
                lock_receipt = plan.lock_literature_search_execution_command
                lock_execution = execution.get_for_update
                authorize = plan.authorize
                database_time = plan.at

                def project(*args, **kwargs):
                    self.observation["order"].append("project_lock_enter")
                    result = lock_project(*args, **kwargs)
                    self.observation["order"].append("project_lock_return")
                    return result

                def receipt(*args, **kwargs):
                    self.observation["order"].append("receipt_lock_enter")
                    result = lock_receipt(*args, **kwargs)
                    self.observation["order"].append("receipt_lock_return")
                    return result

                def execution_row(*args, **kwargs):
                    self.observation["order"].append("execution_lock_enter")
                    result = lock_execution(*args, **kwargs)
                    self.observation["order"].append("execution_lock_return")
                    return result

                def authority(*args, **kwargs):
                    self.observation["order"].append("authority_lock_enter")
                    result = authorize(*args, **kwargs)
                    self.observation["authority_facts"] = result
                    self.observation["order"].append("authority_lock_return")
                    return result

                def at():
                    value = database_time()
                    self.observation["order"].append("fresh_database_time")
                    self.observation.setdefault("authorization_times", []).append(value)
                    return value

                plan.lock_project = project
                plan.lock_literature_search_execution_command = receipt
                execution.get_for_update = execution_row
                plan.authorize = authority
                plan.at = at
                return self

            def begin_serializable(self):
                super().begin_serializable()
                if self.observation is not None:
                    pid, xid, at = (
                        self._require_session()
                        .execute(text("SELECT pg_backend_pid(),txid_current(),clock_timestamp()"))
                        .one()
                    )
                    self.observation.update(backend_pid=pid, transaction_id=xid, entered_at=at)
                    control.transactions.put(self.observation)

            def __exit__(self, *args):
                try:
                    return super().__exit__(*args)
                finally:
                    if self.observation is not None:
                        self.observation["closed"] = self._session is None

        class ObservedService(LiteratureSearchExecutionService):
            def _authorize(self, uow, principal, project_id, **kwargs):
                try:
                    result = super()._authorize(uow, principal, project_id, **kwargs)
                except ResearchBaseError as error:
                    if control.current is not None:
                        control.current["authorization_decision"] = error.code.value
                    raise
                if control.current is not None:
                    control.current["authorization_decision"] = "ALLOWED"
                    if not control.injected and control.target not in READS:
                        control.injected = True
                        control.current["injected_sqlstate"] = "40001"
                        uow._require_session().execute(
                            text("DO $$ BEGIN RAISE SQLSTATE '40001'; END $$")
                        )
                return result

            def _execute_admission(self, *args, **kwargs):
                with control.enter("execute_admission"):
                    return super()._execute_admission(*args, **kwargs)

            def _cancel_or_recover(self, *args, **kwargs):
                phase = "recover_admission" if args[4] else "cancel_admission"
                with control.enter(phase):
                    return super()._cancel_or_recover(*args, **kwargs)

            def _persist_outcome(self, *args, **kwargs):
                with control.enter("outcome"):
                    return super()._persist_outcome(*args, **kwargs)

            def _finalize_execution(self, *args, **kwargs):
                with control.enter("finalization"):
                    return super()._finalize_execution(*args, **kwargs)

            def _finalize_cancel(self, *args, **kwargs):
                with control.enter("cancel_finalization"):
                    return super()._finalize_cancel(*args, **kwargs)

            def _finalize_recovery(self, *args, **kwargs):
                with control.enter("recovery_finalization"):
                    return super()._finalize_recovery(*args, **kwargs)

            def _prepare_attempt_tx(self, *args, **kwargs):
                if args[3] is not None:
                    return super()._prepare_attempt_tx(*args, **kwargs)
                with control.enter("next_reservation"):
                    return super()._prepare_attempt_tx(*args, **kwargs)

            def _authorize_disclosure(self, *args, **kwargs):
                with control.enter("disclosure"):
                    return super()._authorize_disclosure(*args, **kwargs)

            def get(self, *args, **kwargs):
                with control.enter("get"):
                    return super().get(*args, **kwargs)

            def list(self, *args, **kwargs):
                with control.enter("list"):
                    return super().list(*args, **kwargs)

            def get_provenance(self, *args, **kwargs):
                with control.enter("get_provenance"):
                    return super().get_provenance(*args, **kwargs)

        factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        return ObservedService(
            lambda: ObservedUow(factory, pr204_error_normalization=True),
            provider,
            credential_verifier=control,
        )


def _finite_researcher_interval(engine, role_id, actor_id):
    # Accepted identity R2 uses half-open intervals; this complete test-owned
    # transition has its matching event and runs before the worker takes any
    # lock. Never mutate this interval again or backdate it after expiry.
    with engine.begin() as connection:
        deadline = connection.execute(
            text(
                "UPDATE project_role_assignments SET "
                "effective_until=clock_timestamp()+interval '2 seconds',row_version=row_version+1 "
                "WHERE id=:id RETURNING effective_until"
            ),
            {"id": role_id},
        ).scalar_one()
        connection.execute(
            text(
                "INSERT INTO project_role_events(id,role_assignment_id,actor_id,event_kind,"
                "occurred_at,reason,request_id) VALUES "
                "(:id,:role,:actor,'CLOSED',:at,'finite temporal acceptance interval',:request)"
            ),
            {"id": uuid4(), "role": role_id, "actor": actor_id, "at": deadline, "request": uuid4()},
        )
    return deadline


def _hold_required_lock(connection, lock, principal, project, execution_id, command, role_id):
    if lock == "receipt":
        name = {
            "ExecuteLiteratureSearchExecution": "EXECUTE_LITERATURE_SEARCH_EXECUTION",
            "CancelLiteratureSearchExecution": "CANCEL_LITERATURE_SEARCH_EXECUTION",
            "RecoverLiteratureSearchExecution": "RECOVER_LITERATURE_SEARCH_EXECUTION",
        }[type(command).__name__]
        SqlAlchemyLiteratureSearchPlanRepository(
            connection
        ).lock_literature_search_execution_command(
            principal.deployment_id, principal.actor_id, project, name, command.request_id
        )
    elif lock == "execution":
        connection.execute(
            text("SELECT id FROM literature_search_executions WHERE id=:id FOR UPDATE"),
            {"id": execution_id},
        ).one()
    else:
        assert lock == "authority"
        connection.execute(
            text("SELECT id FROM project_role_assignments WHERE id=:id FOR UPDATE"),
            {"id": role_id},
        ).one()


@pytest.mark.pr204_requirements("PR204-AUTH-02", "PR204-CONC-06")
@pytest.mark.parametrize("phase,lock", PHASE_LOCKS, ids=[f"{p}-{k}" for p, k in PHASE_LOCKS])
@pytest.mark.parametrize("loss", ["role_expiry", "credential_expiry"])
@pytest.mark.parametrize("run", range(1, 6))
def test_pg_each_required_phase_reauthorizes_after_specific_lock_expiry(
    temporal_completion_case, phase2_database_url, phase, lock, loss, run, pr204_trace: FactRecorder
):
    engine, _, _, owner, project, create = temporal_completion_case
    identity, _, _ = _identity_service(phase2_database_url)
    target, _ = _provision(identity, owner)
    role_id = identity.assign_project_role(
        AssignProjectRole(owner, project, target.actor_id, "RESEARCHER", "temporal phases", uuid4())
    )
    queries = (
        ("first query", "second query")
        if phase == "next_reservation"
        else ("normalization evidence",)
    )
    provider = ScriptedProvider(
        [success(query, "provider-a", 2) for query in queries], "provider-a"
    )
    ordinary = _service(engine, provider)
    execution_id = UUID(ordinary.create(replace(create, queries=queries))["execution_id"])
    if phase == "recovery_finalization":
        _service(engine, provider, OutcomeBeforeFinalization).execute(
            _command("execute", target, project, execution_id)
        )
    control = PhaseExpiry(phase, pr204_trace)
    service = control.service(engine, provider)
    name = (
        "cancel"
        if phase in {"cancel_admission", "cancel_finalization"}
        else "recover"
        if phase in {"recover_admission", "recovery_finalization"}
        else "execute"
    )
    command = _command(name, target, project, execution_id)

    def worker():
        try:
            if phase == "list":
                return service.list(target, project)
            if phase in {"get", "get_provenance"}:
                return getattr(service, phase)(target, project, execution_id)
            return getattr(service, name)(command)
        except ResearchBaseError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(worker)
        try:
            assert control.ready.wait(15), "target phase did not reach pre-transaction barrier"
            # Prior legitimate commits remain part of history. The assertion
            # below compares only effects after this exact phase boundary.
            baseline = _snapshot(engine, project)
            calls_before = len(provider.calls)
            if loss == "role_expiry":
                deadline = _finite_researcher_interval(engine, role_id, target.actor_id)
            else:
                with engine.connect() as connection:
                    deadline = connection.execute(
                        text("SELECT clock_timestamp()")
                    ).scalar_one() + timedelta(seconds=2)
                control.credential_expires_at = deadline
            positive_at, _, effective_before = _authority_rows(engine, target.actor_id, project)
            assert "RESEARCHER" in effective_before and positive_at < deadline
            assert control.is_valid(target, positive_at)
            # Complete Application read with legitimate identity proves the
            # finite role fixture authorizes before its deadline.
            ordinary.get(target, project, execution_id)
            expected_attempt = 1 if phase in READS else 2
            with engine.connect() as controller:
                tx = controller.begin()
                blocker_pid = controller.execute(text("SELECT pg_backend_pid()")).scalar_one()
                _hold_required_lock(
                    controller, lock, target, project, execution_id, command, role_id
                )
                control.release.set()
                deadline_wait = monotonic() + 10
                blocked = None
                while monotonic() < deadline_wait:
                    item = control.transactions.get(timeout=10)
                    if item["attempt"] == expected_attempt:
                        blocked = item
                        break
                assert blocked is not None and blocked["entered_at"] < deadline
                observed_wait = None
                while monotonic() < deadline_wait:
                    with engine.connect() as observer:
                        observed_wait = dict(
                            observer.execute(
                                text(
                                    "SELECT wait_event_type,wait_event,pg_blocking_pids(pid) AS blockers "  # noqa: E501
                                    "FROM pg_stat_activity WHERE pid=:pid"
                                ),
                                {"pid": blocked["backend_pid"]},
                            )
                            .mappings()
                            .one()
                        )
                    if (
                        observed_wait["wait_event_type"] == "Lock"
                        and blocker_pid in observed_wait["blockers"]
                    ):
                        break
                    Event().wait(0.01)
                assert observed_wait["wait_event_type"] == "Lock"
                assert blocker_pid in observed_wait["blockers"] and not future.done()
                order = blocked["order"]
                assert f"{lock}_lock_enter" in order and f"{lock}_lock_return" not in order
                assert "project_lock_return" in order
                while True:
                    released_at = controller.execute(text("SELECT clock_timestamp()")).scalar_one()
                    if released_at >= deadline:
                        break
                    assert monotonic() < deadline_wait, "expiry wait exceeded bound"
                    Event().wait(0.01)
                tx.commit()
            result = future.result(timeout=20)
        finally:
            control.release.set()
    after = _snapshot(engine, project)
    assert result is ErrorCode.FORBIDDEN
    assert after == baseline and len(provider.calls) == calls_before
    assert len(control.attempts) == expected_attempt
    assert len({a["transaction_id"] for a in control.attempts}) == expected_attempt
    if phase not in READS:
        first = control.attempts[0]
        assert first["authorization_decision"] == "ALLOWED"
        assert first["injected_sqlstate"] == "40001"
        assert first["error_code"] == "CONCURRENT_MODIFICATION"
    final = control.attempts[-1]
    assert final["authorization_decision"] == final["error_code"] == "FORBIDDEN"
    assert final["authorization_times"][-1] >= deadline
    assert all(a["closed"] for a in control.attempts) and engine.pool.checkedout() == 0
    assert final["order"].index(f"{lock}_lock_return") < final["order"].index("fresh_database_time")
    at, roles, effective_after = _authority_rows(engine, target.actor_id, project)
    assert at >= deadline
    if loss == "role_expiry":
        assert effective_after == []
    else:
        assert "RESEARCHER" in effective_after
        assert not [
            s for s in control.credential_samples if s["attempt"] == expected_attempt and s["valid"]
        ]
    pr204_trace.record(
        phase=phase,
        lock=lock,
        loss=loss,
        run=run,
        expiry=deadline,
        authorized_before_expiry_at=positive_at,
        released_after_expiry_at=released_at,
        blocker_pid=blocker_pid,
        postgres_wait=observed_wait,
        database_attempts=control.attempts,
        credential_samples=control.credential_samples,
        roles=roles,
        effective_roles_after=effective_after,
        baseline=baseline,
        after=after,
        provider_calls_before=calls_before,
        provider_calls_after=len(provider.calls),
        result=result.value,
        forbidden_phase_effect_count=0,
    )
