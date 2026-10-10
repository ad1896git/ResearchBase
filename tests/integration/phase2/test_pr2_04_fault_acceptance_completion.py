"""Real-PG phase faults with independent visibility before acknowledgement failure.

Faults are test-owned SQLSTATE injections, not naturally occurring deadlocks or
network disconnects. A post-commit injection executes in a separate cleanup
transaction after the original commit; the trace retains both transaction IDs.
"""

from contextlib import contextmanager
from dataclasses import replace
from time import monotonic, sleep
from uuid import UUID, uuid4

import pytest
from scripts.pr2_04_pytest_evidence import FactRecorder
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker
from tests.integration.phase2.test_pr2_03_literature_search_plan_application import (
    _AlwaysValidCredential,
)
from tests.integration.phase2.test_pr2_04_idempotency_coverage import (
    _command,
    _execution_setup,
    _service,
    _snapshot,
)
from tests.unit.phase2.test_pr2_04_provider_coverage import ScriptedProvider, success

from researchbase.application.literature_search_execution import LiteratureSearchExecutionService
from researchbase.application.phase2_identity import AssignProjectRole
from tests.integration.phase2.test_pr2_00_challenges import _service as _identity_service
from tests.integration.phase2.test_pr2_03_effective_authority import _provision
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.uow import SqlAlchemyUnitOfWork


@pytest.fixture
def fault_completion_case(phase2_database_url):
    yield from _execution_setup(phase2_database_url)


def _protected(snapshot):
    return {name: values for name, values in snapshot.items() if name != "receipts"}


def _wait_until_recovery(engine, deadline):
    stop = monotonic() + 40
    while True:
        with engine.connect() as connection:
            at = connection.execute(text("SELECT clock_timestamp()")).scalar_one()
        if at >= deadline:
            return at
        assert monotonic() < stop, "actual PostgreSQL recovery deadline not reached"
        sleep(min(0.25, (deadline - at).total_seconds()))


class PhaseFault:
    def __init__(self, engine, project, recorder):
        self.engine = engine
        self.project = project
        self.recorder = recorder
        self.phase = None
        self.target = None
        self.mode = None
        self.remaining = 0
        self.phase_attempts = []
        self.faults = []
        self.transactions = []
        self.captured_outcomes = []
        self.suppress_finalization = False

    def arm(self, phase, mode, count=1):
        self.target, self.mode, self.remaining = phase, mode, count

    @contextmanager
    def enter_phase(self, phase):
        old = self.phase
        self.phase = phase
        self.phase_attempts.append(phase)
        try:
            yield
        finally:
            self.phase = old

    def service(self, provider):
        control = self

        class FaultSession(Session):
            def commit(self):
                targeted = control.phase == control.target and control.remaining > 0
                if not targeted:
                    return super().commit()
                # Flush actual phase writes before testing rollback or committing.
                self.flush()
                pid, xid = self.execute(text("SELECT pg_backend_pid(),txid_current()")).one()
                fault = {
                    "phase": control.phase,
                    "mode": control.mode,
                    "phase_backend_pid": pid,
                    "phase_transaction_id": xid,
                    "injection_number": len(control.faults) + 1,
                }
                control.remaining -= 1
                if control.mode == "post_commit_ack_lost":
                    super().commit()
                    fault["phase_commit_completed"] = True
                else:
                    assert control.mode == "rollback"
                    fault["phase_commit_completed"] = False
                # Independent ordinary SELECTs see only committed facts. Snapshot
                # is made before the injected exception and before any retry.
                fault["independent_snapshot_before_fault"] = _snapshot(
                    control.engine, control.project
                )
                cleanup_pid, cleanup_xid = self.execute(
                    text("SELECT pg_backend_pid(),txid_current()")
                ).one()
                fault["injection_backend_pid"] = cleanup_pid
                fault["injection_transaction_id"] = cleanup_xid
                if control.mode == "post_commit_ack_lost":
                    assert cleanup_xid != xid
                else:
                    assert cleanup_xid == xid
                try:
                    self.execute(text("DO $$ BEGIN RAISE SQLSTATE '40001'; END $$"))
                except DBAPIError as error:
                    fault["sqlstate"] = getattr(error.orig, "sqlstate", None)
                    assert fault["sqlstate"] == "40001"
                    control.faults.append(fault)
                    control.recorder.record(commit_fault=fault)
                    raise

        sessions = sessionmaker(
            bind=control.engine, class_=FaultSession, expire_on_commit=False, autoflush=False
        )

        class ObservedUow(SqlAlchemyUnitOfWork):
            def __enter__(self):
                super().__enter__()
                self.fact = {"phase": control.phase, "order": []}
                control.transactions.append(self.fact)
                plan = self.literature_search_plan
                lock, authorize, at = plan.lock_project, plan.authorize, plan.at

                def observed_lock(project_id):
                    result = lock(project_id)
                    self.fact["order"].append("project_lock_returned")
                    return result

                def observed_authorize(*args, **kwargs):
                    result = authorize(*args, **kwargs)
                    self.fact["order"].append("authority_read_returned")
                    self.fact["roles"] = [row["role"] for row in result]
                    return result

                def observed_at():
                    value = at()
                    self.fact["order"].append("fresh_database_time")
                    self.fact.setdefault("database_times", []).append(value)
                    return value

                plan.lock_project = observed_lock
                plan.authorize = observed_authorize
                plan.at = observed_at
                return self

            def begin_serializable(self):
                super().begin_serializable()
                pid, xid = self._require_session().execute(
                    text("SELECT pg_backend_pid(),txid_current()")
                ).one()
                self.fact.update(backend_pid=pid, transaction_id=xid)

            def __exit__(self, *args):
                try:
                    return super().__exit__(*args)
                except ResearchBaseError as error:
                    self.fact["error_code"] = error.code.value
                    raise
                finally:
                    self.fact["closed"] = self._session is None
                    control.recorder.record(database_transaction=self.fact)

        class FaultService(LiteratureSearchExecutionService):
            def _execute_admission(self, *args, **kwargs):
                with control.enter_phase("reserve"):
                    return super()._execute_admission(*args, **kwargs)

            def _persist_outcome(self, *args, **kwargs):
                control.captured_outcomes.append((args, kwargs))
                with control.enter_phase("outcome"):
                    return super()._persist_outcome(*args, **kwargs)

            def _finalize_execution(self, *args, **kwargs):
                if control.suppress_finalization:
                    return None
                with control.enter_phase("finalization"):
                    return super()._finalize_execution(*args, **kwargs)

            def _finalize_cancel(self, *args, **kwargs):
                with control.enter_phase("cancel_finalization"):
                    return super()._finalize_cancel(*args, **kwargs)

        return FaultService(
            lambda: ObservedUow(sessions, pr204_error_normalization=True),
            provider,
            credential_verifier=_AlwaysValidCredential(),
        )

    def assert_clean_fresh_attempts(self, phase, expected):
        attempts = [item for item in self.transactions if item["phase"] == phase]
        assert len(attempts) == expected
        assert len({item["transaction_id"] for item in attempts}) == expected
        assert all(item["closed"] for item in self.transactions)
        assert self.engine.pool.checkedout() == 0
        for item in attempts:
            order = item["order"]
            assert order.index("project_lock_returned") < order.index("authority_read_returned")
            assert order.index("authority_read_returned") < order.index("fresh_database_time")
            assert item["database_times"] and item["roles"] == ["OWNER"]


@pytest.mark.pr204_requirements("PR204-BOUND-03")
def test_pg_lost_reservation_commit_acknowledgement_never_grants_dispatch(
    fault_completion_case, pr204_trace: FactRecorder
):
    engine, normal, provider, principal, project, create = fault_completion_case
    execution_id = UUID(normal.create(create)["execution_id"])
    control = PhaseFault(engine, project, pr204_trace)
    driver = control.service(provider)
    control.arm("reserve", "post_commit_ack_lost")
    command = _command("execute", principal, project, execution_id)
    admission = driver.execute(command)
    control.assert_clean_fresh_attempts("reserve", 2)
    assert len(control.faults) == 1 and control.faults[0]["phase_commit_completed"]
    visible = control.faults[0]["independent_snapshot_before_fault"]
    after = _snapshot(engine, project)
    assert visible == after
    assert after["executions"][0]["status"] == "RUNNING"
    assert after["executions"][0]["row_version"] == 2
    assert len(after["attempts"]) == 1 and after["attempts"][0]["status"] == "RESERVED"
    assert after["attempts"][0]["row_version"] == 1
    assert len(after["receipts"]) == len(after["events"]) == 2
    assert {e["kind"] for e in after["events"]} == {"CREATED", "ATTEMPT_RESERVED"}
    assert after["queries"] == after["results"] == provider.calls == []
    assert normal.execute(command) == admission and _snapshot(engine, project) == after
    new_admission = normal.execute(_command("execute", principal, project, execution_id))
    final = _snapshot(engine, project)
    assert _protected(final) == _protected(after)
    assert len(final["receipts"]) == len(after["receipts"]) + 1
    assert new_admission["accepted_row_version"] == 2 and provider.calls == []
    pr204_trace.record(before_retry=visible, after=after, final=final, provider_calls=0)


@pytest.mark.pr204_requirements("PR204-CRASH-05")
def test_pg_lost_outcome_commit_ack_matches_exact_tuple_and_rejects_changed_tuple(
    fault_completion_case, pr204_trace: FactRecorder
):
    engine, _, _, principal, project, create = fault_completion_case
    provider = ScriptedProvider([success("normalization evidence", "provider-a", 2)], "provider-a")
    control = PhaseFault(engine, project, pr204_trace)
    control.suppress_finalization = True
    driver = control.service(provider)
    execution_id = UUID(driver.create(create)["execution_id"])
    control.arm("outcome", "post_commit_ack_lost")
    driver.execute(_command("execute", principal, project, execution_id))
    control.assert_clean_fresh_attempts("outcome", 2)
    assert len(control.faults) == 1
    after = _snapshot(engine, project)
    assert control.faults[0]["independent_snapshot_before_fault"] == after
    assert after["executions"][0]["status"] == "RUNNING"
    assert after["executions"][0]["row_version"] == 3
    assert len(after["attempts"]) == 1 and after["attempts"][0]["status"] == "SUCCEEDED"
    assert after["attempts"][0]["row_version"] == 2
    assert len(after["queries"]) == 1 and len(after["results"]) == 2
    assert len(after["receipts"]) == 2
    assert sum(e["kind"] == "OUTCOME_RECORDED" for e in after["events"]) == 1
    assert not any(e["kind"] == "FINISHED" for e in after["events"])
    assert len(provider.calls) == 1
    args, kwargs = control.captured_outcomes[0]
    # Calling the same private Application phase is a test seam, not a public
    # endpoint for caller-supplied provider responses. Preserve exact times.
    ordinary = _service(engine, provider)
    ordinary._persist_outcome(*args, **kwargs)
    assert _snapshot(engine, project) == after and len(provider.calls) == 1
    changed = list(args)
    changed[7] = replace(changed[7], provider_request_id="different-valid-correlation")
    with pytest.raises(ResearchBaseError) as different:
        ordinary._persist_outcome(*changed, **kwargs)
    assert different.value.code is ErrorCode.IMMUTABLE_RECORD
    assert _snapshot(engine, project) == after and len(provider.calls) == 1
    ordinary.recover(_command("recover", principal, project, execution_id))
    final = _snapshot(engine, project)
    assert final["executions"][0]["status"] == "SUCCEEDED"
    assert final["executions"][0]["row_version"] == 4
    assert sum(e["kind"] == "FINISHED" for e in final["events"]) == 1
    for key in ("attempts", "queries", "results"):
        assert final[key] == after[key]
    assert len(provider.calls) == 1
    pr204_trace.record(after=after, final=final, different_error=different.value.code.value, provider_calls=1)


@pytest.mark.pr204_requirements("PR204-CRASH-05")
@pytest.mark.parametrize("fault_count", [1, 3], ids=["retry", "exhaustion"])
def test_pg_outcome_commit_rollback_preserves_atomic_batch_and_single_invocation(
    fault_completion_case, fault_count, pr204_trace: FactRecorder
):
    engine, _, _, principal, project, create = fault_completion_case
    provider = ScriptedProvider([success("normalization evidence", "provider-a", 2)], "provider-a")
    control = PhaseFault(engine, project, pr204_trace)
    driver = control.service(provider)
    execution_id = UUID(driver.create(replace(create, timeout_seconds=1))["execution_id"])
    control.arm("outcome", "rollback", fault_count)
    execute = _command("execute", principal, project, execution_id)
    if fault_count == 3:
        with pytest.raises(ResearchBaseError) as exhausted:
            driver.execute(execute)
        assert exhausted.value.code is ErrorCode.CONCURRENT_MODIFICATION
    else:
        driver.execute(execute)
    control.assert_clean_fresh_attempts("outcome", 3 if fault_count == 3 else 2)
    assert len(control.faults) == fault_count and len(provider.calls) == 1
    for fault in control.faults:
        visible = fault["independent_snapshot_before_fault"]
        assert not fault["phase_commit_completed"]
        assert visible["executions"][0]["status"] == "RUNNING"
        assert visible["executions"][0]["row_version"] == 2
        assert visible["attempts"][0]["status"] == "RESERVED"
        assert visible["queries"] == visible["results"] == []
        assert len(visible["receipts"]) == len(visible["events"]) == 2
    after = _snapshot(engine, project)
    if fault_count == 3:
        assert after == control.faults[-1]["independent_snapshot_before_fault"]
        # The response is unavailable to this fresh recovery service. It can
        # only observe the unresolved reservation and actual recovery deadline.
        recovery = _service(engine, provider)
        recovery_at = _wait_until_recovery(engine, after["attempts"][0]["recovery_after"])
        recovery.recover(_command("recover", principal, project, execution_id))
        final = _snapshot(engine, project)
        assert final["executions"][0]["status"] == "UNKNOWN"
        assert final["executions"][0]["failure_code"] == "RECOVERY_OUTCOME_UNKNOWN"
        assert final["queries"] == final["results"] == []
        assert final["attempts"][0]["invoked_at"] is None
        assert final["attempts"][0]["returned_at"] is None
        pr204_trace.record(recovery_database_time=recovery_at)
    else:
        final = after
        assert final["executions"][0]["status"] == "SUCCEEDED"
        assert len(final["queries"]) == 1 and len(final["results"]) == 2
    assert final["executions"][0]["row_version"] == 4
    assert sum(e["kind"] == "OUTCOME_RECORDED" for e in final["events"]) == 1
    assert sum(e["kind"] == "FINISHED" for e in final["events"]) == 1
    assert len(provider.calls) == 1
    pr204_trace.record(fault_count=fault_count, after=after, final=final, provider_calls=1)


@pytest.mark.pr204_requirements("PR204-CRASH-07")
@pytest.mark.parametrize("phase", ["finalization", "cancel_finalization"])
@pytest.mark.parametrize("fault", ["rollback_once", "rollback_exhaustion", "post_commit_ack_lost"])
def test_pg_terminal_commit_fault_rereads_durable_state_without_duplicate_finish(
    fault_completion_case, phase, fault, pr204_trace: FactRecorder
):
    engine, _, _, principal, project, create = fault_completion_case
    provider = ScriptedProvider([success("normalization evidence", "provider-a", 2)], "provider-a")
    control = PhaseFault(engine, project, pr204_trace)
    driver = control.service(provider)
    execution_id = UUID(driver.create(create)["execution_id"])
    cancellation = phase == "cancel_finalization"
    count = 3 if fault == "rollback_exhaustion" else 1
    mode = "post_commit_ack_lost" if fault == "post_commit_ack_lost" else "rollback"
    control.arm(phase, mode, count)
    name = "cancel" if cancellation else "execute"
    command = _command(name, principal, project, execution_id)
    if count == 3:
        with pytest.raises(ResearchBaseError) as exhausted:
            getattr(driver, name)(command)
        assert exhausted.value.code is ErrorCode.CONCURRENT_MODIFICATION
    else:
        getattr(driver, name)(command)
    control.assert_clean_fresh_attempts(phase, 3 if count == 3 else 2)
    assert len(control.faults) == count
    expected_calls = 0 if cancellation else 1
    expected_status = "CANCELLED" if cancellation else "SUCCEEDED"
    terminal_version = 3 if cancellation else 4
    for injected in control.faults:
        visible = injected["independent_snapshot_before_fault"]
        execution = visible["executions"][0]
        assert len(visible["receipts"]) == 2
        if mode == "post_commit_ack_lost":
            assert injected["phase_commit_completed"]
            assert execution["status"] == expected_status
            assert execution["row_version"] == terminal_version
            assert sum(e["kind"] == "FINISHED" for e in visible["events"]) == 1
        else:
            assert not injected["phase_commit_completed"]
            assert execution["status"] == ("PLANNED" if cancellation else "RUNNING")
            assert execution["row_version"] == terminal_version - 1
            assert not any(e["kind"] == "FINISHED" for e in visible["events"])
        if cancellation:
            assert execution["started_at"] is None
            assert visible["attempts"] == visible["queries"] == visible["results"] == []
            assert sum(e["kind"] == "CANCEL_REQUESTED" for e in visible["events"]) == 1
        else:
            assert len(visible["attempts"]) == len(visible["queries"]) == 1
            assert visible["attempts"][0]["status"] == "SUCCEEDED"
            assert len(visible["results"]) == 2
    after = _snapshot(engine, project)
    if mode == "post_commit_ack_lost" or count == 3:
        assert after == control.faults[-1]["independent_snapshot_before_fault"]
    ordinary = _service(engine, provider)
    # Receipt replay does not resume either interrupted finalizer.
    admission = getattr(ordinary, name)(command)
    assert _snapshot(engine, project) == after and len(provider.calls) == expected_calls
    saved = next(r for r in after["receipts"] if r["request_id"] == command.request_id)
    assert admission == saved["result_dto"]
    if count == 3:
        ordinary.recover(_command("recover", principal, project, execution_id))
    final = _snapshot(engine, project)
    assert final["executions"][0]["status"] == expected_status
    assert final["executions"][0]["row_version"] == terminal_version
    assert sum(e["kind"] == "FINISHED" for e in final["events"]) == 1
    for key in ("attempts", "queries", "results"):
        assert final[key] == after[key]
    assert len(final["receipts"]) == 2 + (1 if count == 3 else 0)
    if cancellation:
        assert final["executions"][0]["started_at"] is None
        assert final["attempts"] == final["queries"] == final["results"] == []
    assert len(provider.calls) == expected_calls
    pr204_trace.record(
        phase=phase,
        fault=fault,
        after=after,
        final=final,
        admission=admission,
        provider_calls=expected_calls,
    )


def _assert_exact_admission_replay(control, provider, command, before):
    calls = len(provider.calls)
    saved = next(row for row in before["receipts"] if row["request_id"] == command.request_id)
    name = "cancel" if type(command).__name__.startswith("Cancel") else "execute"
    replay = getattr(control.service(provider), name)(command)
    assert replay == saved["result_dto"]
    assert _snapshot(control.engine, control.project) == before
    assert len(provider.calls) == calls
    control.recorder.record(exact_receipt_replay=dict(
        request_id=command.request_id, command=name, saved=saved, returned=replay,
        unchanged_snapshot=before, provider_calls=calls))


def _accounting(control, provider, expected_phase_attempts):
    for phase, expected in expected_phase_attempts.items():
        attempts = [t for t in control.transactions if t["phase"] == phase]
        assert len(attempts) == expected
        assert len({t["transaction_id"] for t in attempts}) == expected
    assert all(t["closed"] for t in control.transactions)
    assert control.engine.pool.checkedout() == 0
    provider_ids = [call.attempt_id for call in provider.calls]
    assert len(provider_ids) == len(set(provider_ids))
    control.recorder.record(
        accounting=dict(public_commands=control.commands,
            expected_phase_attempts=expected_phase_attempts,
            database_transactions=control.transactions,
            sqlstate_faults=control.faults,
            provider_invocation_attempt_ids=provider_ids,
            durable_outcome=_snapshot(control.engine, control.project)))


def _finite_role_before_phase(engine, role_id, actor_id):
    # Same finite-interval convention as the accepted temporal fixtures. This
    # runs before the phase opens its UoW; all causal fields and guards remain.
    with engine.begin() as connection:
        deadline = connection.execute(text(
            "UPDATE project_role_assignments SET "
            "effective_until=clock_timestamp()+interval '3 seconds',row_version=row_version+1 "
            "WHERE id=:id RETURNING effective_until"), {"id": role_id}).scalar_one()
        connection.execute(text(
            "INSERT INTO project_role_events(id,role_assignment_id,actor_id,event_kind,"
            "occurred_at,reason,request_id) VALUES "
            "(:id,:role,:actor,'CLOSED',:at,'finite fault acceptance interval',:request)"),
            dict(id=uuid4(), role=role_id, actor=actor_id, at=deadline, request=uuid4()))
    return deadline


@pytest.mark.pr204_requirements("PR204-IDEM-06", "PR204-CONC-05", "PR204-CONC-06")
@pytest.mark.parametrize("phase", ["outcome", "finalization", "cancel_finalization"])
@pytest.mark.parametrize("sqlstate", ["40001", "40P01"])
@pytest.mark.parametrize("loss", ["credential", "role_expiry"])
def test_pg_postcommit_fault_reauthorizes_before_disclosing_saved_admission(
    fault_completion_case, phase2_database_url, phase, sqlstate, loss,
    pr204_trace: FactRecorder,
):
    engine, normal, _, owner, project, create = fault_completion_case
    provider = ScriptedProvider([success("normalization evidence", "provider-a", 2)], "provider-a")
    identity, _, _ = _identity_service(phase2_database_url)
    principal, _ = _provision(identity, owner)
    role_id = identity.assign_project_role(AssignProjectRole(
        owner, project, principal.actor_id, "RESEARCHER", "postcommit authority", uuid4()))
    execution_id = UUID(normal.create(create)["execution_id"])
    control = PhaseFault(engine, project, pr204_trace, sqlstate)
    control.expected_roles = ["RESEARCHER"]
    samples = []

    class Credential:
        valid = True

        def is_valid(self, principal, at):
            samples.append(dict(phase=control.phase, at=at, valid=self.valid))
            return self.valid

    credential = Credential()
    control.credential = credential
    interval = {}

    def before_phase(current):
        if current == phase and loss == "role_expiry" and "deadline" not in interval:
            interval["deadline"] = _finite_role_before_phase(engine, role_id, owner.actor_id)

    def after_commit(fault):
        assert fault["phase_commit_completed"]
        # First phase really authorized and committed, so expiration cannot be
        # substituted for a failed setup or pre-effect authorization failure.
        at = [s["at"] for s in samples if s["phase"] == phase][-1]
        assert samples[-1]["valid"]
        if loss == "role_expiry":
            assert at < interval["deadline"]
            interval["after_commit_database_time"] = _wait_until_recovery(
                engine, interval["deadline"])
            assert interval["after_commit_database_time"] >= interval["deadline"]
        else:
            credential.valid = False

    control.before_phase = before_phase
    control.after_actual_commit = after_commit
    control.arm(phase, "post_commit_ack_lost")
    driver = control.service(provider)
    name = "cancel" if phase == "cancel_finalization" else "execute"
    command = _command(name, principal, project, execution_id)
    with pytest.raises(ResearchBaseError) as denied:
        getattr(driver, name)(command)
    assert denied.value.code is ErrorCode.FORBIDDEN
    assert len(control.faults) == 1
    after = _snapshot(engine, project)
    assert after == control.faults[0]["independent_snapshot_before_fault"]
    expected_calls = 0 if name == "cancel" else 1
    assert len(provider.calls) == expected_calls
    assert len(after["receipts"]) == 2
    assert after["executions"][0]["status"] == (
        "RUNNING" if phase == "outcome" else "CANCELLED" if name == "cancel" else "SUCCEEDED")
    attempts = [t for t in control.transactions if t["phase"] == phase]
    assert len(attempts) == 2
    for attempt in attempts:
        assert attempt["order"].index("project_lock_returned") < attempt["order"].index("authority_read_returned")
        assert attempt["order"].index("authority_read_returned") < attempt["order"].index("fresh_database_time")
    assert attempts[0]["database_times"][-1] < attempts[1]["database_times"][-1]
    assert attempts[1]["error_code"] == "FORBIDDEN"
    if loss == "credential":
        assert [s["valid"] for s in samples if s["phase"] == phase] == [True, False]
    else:
        assert attempts[0]["database_times"][-1] < interval["deadline"]
        assert attempts[1]["database_times"][-1] >= interval["deadline"]
    with pytest.raises(ResearchBaseError) as replay_denied:
        getattr(driver, name)(command)
    assert replay_denied.value.code is ErrorCode.FORBIDDEN
    assert _snapshot(engine, project) == after
    assert len(provider.calls) == expected_calls
    # Accepted owner is independently still entitled. It uses its own receipt
    # scope and cannot replay the denied principal's saved admission.
    replacement = PhaseFault(engine, project, pr204_trace, sqlstate)
    recovery = _command("recover", owner, project, execution_id)
    recovery_service = replacement.service(provider)
    admission = recovery_service.recover(recovery)
    final = _snapshot(engine, project)
    assert final["executions"][0]["status"] == ("CANCELLED" if name == "cancel" else "SUCCEEDED")
    assert sum(e["kind"] == "FINISHED" for e in final["events"]) == 1
    assert len(final["receipts"]) == 3
    assert final["attempts"] == after["attempts"]
    assert final["queries"] == after["queries"] and final["results"] == after["results"]
    assert all(row in final["receipts"] for row in after["receipts"])
    assert recovery_service.recover(recovery) == admission
    assert _snapshot(engine, project) == final and len(provider.calls) == expected_calls
    _accounting(control, provider, {phase: 2})
    _accounting(replacement, provider, {"recover_admission": 2})
    pr204_trace.record(authority_loss=loss, credential_samples=samples, role_interval=interval,
        denied_code=denied.value.code.value, denied_replay=replay_denied.value.code.value,
        committed_before_denial=after, after_entitled_recovery=final)


@pytest.mark.pr204_requirements("PR204-CONC-05", "PR204-CONC-06", "PR204-IDEM-06")
@pytest.mark.parametrize("phase", ["outcome", "finalization", "cancel_finalization"])
@pytest.mark.parametrize("sqlstate", ["40001", "40P01"])
@pytest.mark.parametrize("fault_count", [1, 3], ids=["retry", "exhaustion"])
def test_pg_actual_context_exit_fault_preserves_commit_and_bounds_phase_retry(
    fault_completion_case, phase, sqlstate, fault_count, pr204_trace: FactRecorder,
):
    engine, normal, _, principal, project, create = fault_completion_case
    provider = ScriptedProvider([success("normalization evidence", "provider-a", 2)], "provider-a")
    execution_id = UUID(normal.create(create)["execution_id"])
    control = PhaseFault(engine, project, pr204_trace, sqlstate)
    # Keep the complete TX B visible in RUNNING for exact sealed readback.
    control.suppress_finalization = phase == "outcome"
    control.arm(phase, "context_exit", fault_count)
    driver = control.service(provider)
    name = "cancel" if phase == "cancel_finalization" else "execute"
    command = _command(name, principal, project, execution_id)
    if fault_count == 3:
        with pytest.raises(ResearchBaseError) as exhausted:
            getattr(driver, name)(command)
        assert exhausted.value.code is ErrorCode.CONCURRENT_MODIFICATION
    else:
        getattr(driver, name)(command)
    count = 3 if fault_count == 3 else 2
    control.assert_clean_fresh_attempts(phase, count)
    assert len(control.faults) == fault_count
    after = _snapshot(engine, project)
    for fault in control.faults:
        assert fault["mode"] == "context_exit" and fault["phase_commit_completed"]
        assert fault["sqlstate"] == sqlstate
        assert fault["phase_transaction_id"] != fault["injection_transaction_id"]
        assert fault["independent_snapshot_before_fault"] == after
    assert len(after["receipts"]) == 2
    assert after["executions"][0]["status"] == (
        "RUNNING" if phase == "outcome" else "CANCELLED" if name == "cancel" else "SUCCEEDED")
    expected_calls = 0 if name == "cancel" else 1
    assert len(provider.calls) == expected_calls
    assert sum(e["kind"] == "OUTCOME_RECORDED" for e in after["events"]) == expected_calls
    assert sum(e["kind"] == "FINISHED" for e in after["events"]) == (0 if phase == "outcome" else 1)
    _assert_exact_admission_replay(control, provider, command, after)
    recovery = _command("recover", principal, project, execution_id)
    admission = driver.recover(recovery)
    final = _snapshot(engine, project)
    assert final["executions"][0]["status"] == ("CANCELLED" if name == "cancel" else "SUCCEEDED")
    assert sum(e["kind"] == "FINISHED" for e in final["events"]) == 1
    assert final["attempts"] == after["attempts"] and final["queries"] == after["queries"]
    assert final["results"] == after["results"] and len(final["receipts"]) == 3
    assert driver.recover(recovery) == admission
    assert _snapshot(engine, project) == final and len(provider.calls) == expected_calls
    _accounting(control, provider, {phase: count, "recover_admission": 2})


@pytest.mark.pr204_requirements("PR204-CONC-05", "PR204-CONC-06")
@pytest.mark.parametrize("phase", ["reserve", "cancel_admission"])
@pytest.mark.parametrize("sqlstate", ["40001", "40P01"])
@pytest.mark.parametrize("fault_count", [1, 3], ids=["retry", "exhaustion"])
def test_pg_execute_and_c1_precommit_fault_rolls_back_only_current_admission(
    fault_completion_case, phase, sqlstate, fault_count, pr204_trace: FactRecorder,
):
    engine, normal, _, principal, project, create = fault_completion_case
    provider = ScriptedProvider([success("normalization evidence", "provider-a", 2)], "provider-a")
    execution_id = UUID(normal.create(create)["execution_id"])
    before = _snapshot(engine, project)
    control = PhaseFault(engine, project, pr204_trace, sqlstate)
    control.arm(phase, "rollback", fault_count)
    driver = control.service(provider)
    name = "execute" if phase == "reserve" else "cancel"
    command = _command(name, principal, project, execution_id)
    if fault_count == 3:
        with pytest.raises(ResearchBaseError) as exhausted:
            getattr(driver, name)(command)
        assert exhausted.value.code is ErrorCode.CONCURRENT_MODIFICATION
    else:
        getattr(driver, name)(command)
    count = 3 if fault_count == 3 else 2
    control.assert_clean_fresh_attempts(phase, count)
    assert len(control.faults) == fault_count
    for fault in control.faults:
        assert not fault["phase_commit_completed"] and fault["mode"] == "rollback"
        assert fault["sqlstate"] == sqlstate
        assert fault["independent_snapshot_before_fault"] == before
        assert fault["phase_transaction_id"] == fault["injection_transaction_id"]
    after = _snapshot(engine, project)
    if fault_count == 3:
        assert after == before
        assert provider.calls == []
        assert after["executions"][0]["status"] == "PLANNED"
    else:
        assert len(after["receipts"]) == 2
        assert after["executions"][0]["status"] == ("SUCCEEDED" if name == "execute" else "CANCELLED")
        assert sum(e["kind"] == "FINISHED" for e in after["events"]) == 1
        assert len(provider.calls) == (1 if name == "execute" else 0)
        assert len(after["attempts"]) == (1 if name == "execute" else 0)
        _assert_exact_admission_replay(control, provider, command, after)
    _accounting(control, provider, {phase: count + (0 if fault_count == 3 else 1)})
    pr204_trace.record(pre_admission=before, after=after, rejected_admission=fault_count == 3)
