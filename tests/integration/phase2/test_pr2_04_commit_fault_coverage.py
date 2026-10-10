"""Faults around actual PostgreSQL commits; no database or retry policy is replaced."""

from tests.pr2_04_provider_observations import PROVIDER_RETRIEVED_AT

from dataclasses import replace
from time import monotonic, sleep
from uuid import UUID

import pytest
from scripts.pr2_04_pytest_evidence import FactRecorder
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from tests.integration.phase2.test_pr2_03_literature_search_plan_application import (
    _AlwaysValidCredential,
)
from tests.integration.phase2.test_pr2_04_idempotency_coverage import (
    _command,
    _execution_setup,
    _snapshot,
)

from researchbase.application.literature_search_execution import LiteratureSearchExecutionService
from researchbase.domain.literature_search_execution import SearchHit, SearchResponse
from researchbase.persistence.uow import SqlAlchemyUnitOfWork


class ProcessStopped(BaseException):
    """Test-owned process-loss signal, outside ordinary provider exception handling."""


class CommitFault:
    def __init__(self, engine, trace, event_kind, side):
        self.engine, self.trace = engine, trace
        self.event_kind, self.side = event_kind, side
        self.armed = True
        self.fired = 0
        self.attempt = 0

    def factory(self):
        fault = self

        class Uow(SqlAlchemyUnitOfWork):
            def __enter__(self):
                super().__enter__()
                fault.attempt += 1
                self.attempt = fault.attempt
                return self

            def commit(self):
                session = self._require_session()
                last = session.execute(text(
                    "SELECT kind FROM literature_search_execution_events "
                    "ORDER BY created_at DESC,sequence DESC LIMIT 1"
                )).scalar_one_or_none()
                pid, xid = session.execute(text("SELECT pg_backend_pid(),txid_current()")).one()
                inject = fault.armed and last == fault.event_kind
                fault.trace.record(db_attempt=self.attempt, backend_pid=pid, transaction_id=xid,
                                   observed_last_event=last, fault_side=fault.side, inject=inject)
                if inject:
                    fault.armed = False
                    fault.fired += 1
                    if fault.side == "before_commit":
                        raise ProcessStopped()
                super().commit()
                if inject:
                    fault.trace.record(db_attempt=self.attempt, commit_acknowledged_by_database=True)
                    raise ProcessStopped()

        return Uow(sessionmaker(bind=self.engine, expire_on_commit=False, autoflush=False),
                   pr204_error_normalization=True)


def _wait_for_actual_deadline(engine, deadline, trace):
    limit = monotonic() + 40
    while True:
        with engine.connect() as connection:
            now = connection.execute(text("SELECT clock_timestamp()")).scalar_one()
        if now >= deadline:
            trace.record(observed_database_time=now, actual_recovery_after=deadline)
            return
        assert monotonic() < limit, "actual database recovery deadline did not arrive"
        sleep(min(.25, (deadline-now).total_seconds()))


@pytest.fixture
def execution_case(phase2_database_url):
    yield from _execution_setup(phase2_database_url)


@pytest.mark.parametrize("event_kind", [
    pytest.param("CREATED", marks=pytest.mark.pr204_requirements("PR204-CRASH-01", "PR204-CRASH-02")),
    pytest.param("ATTEMPT_RESERVED", marks=pytest.mark.pr204_requirements("PR204-CRASH-03", "PR204-BOUND-03")),
    pytest.param("OUTCOME_RECORDED", marks=pytest.mark.pr204_requirements("PR204-CRASH-04", "PR204-CRASH-05", "PR204-CRASH-06")),
    pytest.param("FINISHED", marks=pytest.mark.pr204_requirements("PR204-CRASH-07", "PR204-CRASH-08")),
])
@pytest.mark.parametrize("side", ["before_commit", "after_commit_lost_ack"])
@pytest.mark.pr204_requirements("PR204-IDEM-06")
def test_pg_commit_loss_preserves_atomic_facts_and_never_replays_provider(
    execution_case, event_kind, side, pr204_trace: FactRecorder
):
    engine, healthy, provider, principal, project, create = execution_case
    create = replace(create, timeout_seconds=1, execution_budget_seconds=120)
    provider.responses = [SearchResponse.success(
        provider_id="provider-a", provider_version="1", normalized_query="normalization evidence",
        provider_request_id="commit-fault-response",
        hits=(SearchHit("hit", "Paper", None, None, None),), retrieved_at=PROVIDER_RETRIEVED_AT,
)]
    fault = CommitFault(engine, pr204_trace, event_kind, side)
    interrupted = LiteratureSearchExecutionService(fault.factory, provider,
                                                   credential_verifier=_AlwaysValidCredential())
    if event_kind == "CREATED":
        with pytest.raises(ProcessStopped):
            interrupted.create(create)
        durable = _snapshot(engine, project)
        pr204_trace.record(point="AFTER_PROCESS_LOSS", rows=durable, provider_calls=len(provider.calls))
        expected = 0 if side == "before_commit" else 1
        assert len(durable["executions"]) == len(durable["receipts"]) == len(durable["events"]) == expected
        assert durable["attempts"] == durable["queries"] == durable["results"] == []
        assert provider.calls == []
        admission = healthy.create(create)
        execution_id = UUID(admission["execution_id"])
        before = _snapshot(engine, project)
        assert healthy.create(create) == admission
        assert _snapshot(engine, project) == before
        recover = healthy.recover(_command("recover", principal, project, execution_id))
        assert healthy.get(principal, project, execution_id)["status"] == "PLANNED"
        assert provider.calls == []
        pr204_trace.record(replayed_admission=admission, recovery_admission=recover,
                           rows=_snapshot(engine, project), provider_calls=len(provider.calls))
        assert fault.fired == 1
        return
    admitted = healthy.create(create)
    execution_id = UUID(admitted["execution_id"])
    execute = _command("execute", principal, project, execution_id)
    with pytest.raises(ProcessStopped):
        interrupted.execute(execute)
    assert fault.fired == 1
    before = healthy.get_provenance(principal, project, execution_id)
    calls = len(provider.calls)
    expected_calls = 0 if event_kind == "ATTEMPT_RESERVED" else 1
    assert calls == expected_calls
    pr204_trace.record(point="AFTER_PROCESS_LOSS", provenance=before, provider_calls=calls)
    if event_kind == "ATTEMPT_RESERVED" and side == "before_commit":
        assert before["execution"]["status"] == "PLANNED"
        assert before["attempts"] == [] and len(before["receipts"]) == 1
        assert [e["kind"] for e in before["events"]] == ["CREATED"]
        # Absence of a committed execute admission permits an explicit new start.
        healthy.execute(execute)
        after = healthy.get_provenance(principal, project, execution_id)
        assert after["execution"]["status"] == "SUCCEEDED" and len(provider.calls) == 1
        assert len(after["attempts"]) == len(after["queries"]) == len(after["results"]) == 1
        pr204_trace.record(explicit_retry=after, provider_calls=len(provider.calls))
        return
    # Every other execute admission is already durable: exact replay is read-only.
    replay = healthy.execute(execute)
    assert replay["accepted_row_version"] == 2
    assert healthy.get_provenance(principal, project, execution_id) == before
    assert len(provider.calls) == calls
    unresolved = (event_kind == "ATTEMPT_RESERVED" or
                  (event_kind == "OUTCOME_RECORDED" and side == "before_commit"))
    if unresolved:
        assert [a["status"] for a in before["attempts"]] == ["RESERVED"]
        assert before["queries"] == before["results"] == []
        _wait_for_actual_deadline(engine, before["attempts"][0]["recovery_after"], pr204_trace)
    else:
        assert [a["status"] for a in before["attempts"]] == ["SUCCEEDED"]
        assert len(before["queries"]) == len(before["results"]) == 1
    recover = _command("recover", principal, project, execution_id)
    receipt = healthy.recover(recover)
    after = healthy.get_provenance(principal, project, execution_id)
    pr204_trace.record(recovery_admission=receipt, provenance=after, provider_calls=len(provider.calls))
    assert after["execution"]["status"] == ("UNKNOWN" if unresolved else "SUCCEEDED")
    assert sum(e["kind"] == "FINISHED" for e in after["events"]) == 1
    assert len(provider.calls) == calls
    if unresolved:
        assert after["attempts"][0]["invoked_at"] is None
        assert after["attempts"][0]["returned_at"] is None
        assert after["queries"] == after["results"] == []
    else:
        assert after["attempts"] == before["attempts"]
        assert after["queries"] == before["queries"] and after["results"] == before["results"]
    assert healthy.recover(recover) == receipt
    assert healthy.get_provenance(principal, project, execution_id) == after
    assert len(provider.calls) == calls


@pytest.mark.parametrize("event_kind", ["CANCEL_REQUESTED", "FINISHED"])
@pytest.mark.parametrize("side", ["before_commit", "after_commit_lost_ack"])
@pytest.mark.pr204_requirements("PR204-CRASH-07", "PR204-CANCEL-01", "PR204-IDEM-06")
def test_pg_c1_c2_rollback_or_lost_ack_never_repeats_intent_or_finish(
    execution_case, event_kind, side, pr204_trace: FactRecorder
):
    engine, healthy, provider, principal, project, create = execution_case
    execution_id = UUID(healthy.create(create)["execution_id"])
    cancel = _command("cancel", principal, project, execution_id)
    fault = CommitFault(engine, pr204_trace, event_kind, side)
    interrupted = LiteratureSearchExecutionService(fault.factory, provider,
                                                   credential_verifier=_AlwaysValidCredential())
    with pytest.raises(ProcessStopped):
        interrupted.cancel(cancel)
    assert fault.fired == 1
    before = healthy.get_provenance(principal, project, execution_id)
    pr204_trace.record(point="CANCELLATION_PROCESS_LOSS", provenance=before,
                       provider_calls=len(provider.calls))
    if event_kind == "CANCEL_REQUESTED" and side == "before_commit":
        assert before["execution"]["row_version"] == 1
        assert [e["kind"] for e in before["events"]] == ["CREATED"]
        assert len(before["receipts"]) == 1
        healthy.recover(_command("recover", principal, project, execution_id))
        assert healthy.get(principal, project, execution_id)["status"] == "PLANNED"
        healthy.cancel(cancel)
    else:
        replay = healthy.cancel(cancel)
        assert replay["accepted_row_version"] == 2
        assert healthy.get_provenance(principal, project, execution_id) == before
        healthy.recover(_command("recover", principal, project, execution_id))
    after = healthy.get_provenance(principal, project, execution_id)
    pr204_trace.record(provenance=after, provider_calls=len(provider.calls))
    assert after["execution"]["status"] == "CANCELLED" and after["execution"]["row_version"] == 3
    assert after["execution"]["started_at"] is None
    assert [e["kind"] for e in after["events"]] == ["CREATED", "CANCEL_REQUESTED", "FINISHED"]
    assert after["attempts"] == after["queries"] == after["results"] == []
    assert provider.calls == []


@pytest.mark.pr204_requirements("PR204-CRASH-04", "PR204-CRASH-05", "PR204-DOM-02", "PR204-DB-05")
def test_pg_surviving_owner_persists_saved_response_exactly_once_with_fresh_authority(
    execution_case, pr204_trace: FactRecorder
):
    engine, healthy, provider, principal, project, create = execution_case
    captured = []

    class Interrupted(LiteratureSearchExecutionService):
        def _persist_outcome(self, *args, **kwargs):
            captured.append((args, kwargs))
            raise ProcessStopped()

    provider.responses = [SearchResponse.success(
        provider_id="provider-a", provider_version="1", normalized_query="normalization evidence",
        provider_request_id="surviving-response",
        hits=(SearchHit("hit", "Paper", None, None, None),), retrieved_at=PROVIDER_RETRIEVED_AT,
)]
    interrupted = Interrupted(healthy._uow_factory, provider,
                              credential_verifier=_AlwaysValidCredential())
    execution_id = UUID(healthy.create(create)["execution_id"])
    with pytest.raises(ProcessStopped):
        interrupted.execute(_command("execute", principal, project, execution_id))
    assert len(captured) == len(provider.calls) == 1
    before = healthy.get_provenance(principal, project, execution_id)
    assert before["queries"] == before["results"] == []
    assert before["attempts"][0]["status"] == "RESERVED"
    args, kwargs = captured[0]
    outcome = healthy._persist_outcome(*args, **kwargs)
    sealed = _snapshot(engine, project)
    assert healthy._persist_outcome(*args, **kwargs) == outcome
    assert _snapshot(engine, project) == sealed
    changed = list(args)
    changed[6] = replace(changed[6], provider_request_id="different-response")
    with pytest.raises(ResearchBaseError) as denied:
        healthy._persist_outcome(*changed, **kwargs)
    assert denied.value.code is ErrorCode.IMMUTABLE_RECORD
    assert _snapshot(engine, project) == sealed
    assert outcome[0] is not None
    healthy._finalize_execution(execution_id, principal.actor_id, outcome[0], principal, project)
    after = healthy.get_provenance(principal, project, execution_id)
    pr204_trace.record(before=before, sealed_rows=sealed, after=after,
                       changed_outcome_error=denied.value.code.value, provider_calls=len(provider.calls))
    assert after["execution"]["status"] == "SUCCEEDED"
    assert len(after["queries"]) == len(after["results"]) == 1
    assert len(after["attempts"]) == len(provider.calls) == 1
    assert after["attempts"][0]["row_version"] == 2


@pytest.mark.parametrize("point", ["partial_after_tx_b", "backoff"])
@pytest.mark.pr204_requirements("PR204-CRASH-06", "PR204-IDEM-06")
def test_pg_partial_hits_survive_interphase_and_backoff_process_loss(
    execution_case, point, pr204_trace: FactRecorder
):
    from researchbase.domain.literature_search_execution import DeliveryCertainty

    engine, healthy, provider, principal, project, create=execution_case
    create=replace(create,queries=("normalization evidence","second query"))
    provider.responses=[SearchResponse.success(provider_id="provider-a",provider_version="1",
        normalized_query="normalization evidence",provider_request_id="partial-response",
        hits=(SearchHit("retained","Paper",None,None,None),), retrieved_at=PROVIDER_RETRIEVED_AT,
),
        SearchResponse("provider-a","1","second query","retry-response",DeliveryCertainty.NOT_SENT,
                       retry_after_seconds=0,failure_code="PROVIDER_TRANSIENT")]

    class Interrupted(LiteratureSearchExecutionService):
        def _persist_outcome(self,*args,**kwargs):
            result=super()._persist_outcome(*args,**kwargs)
            if point=="partial_after_tx_b":
                raise ProcessStopped()
            return result

    def interrupted_backoff(_delay):
        raise ProcessStopped()

    driver=Interrupted(healthy._uow_factory,provider,credential_verifier=_AlwaysValidCredential(),sleep=interrupted_backoff)
    execution_id=UUID(healthy.create(create)["execution_id"])
    with pytest.raises(ProcessStopped):
        driver.execute(_command("execute",principal,project,execution_id))
    before=healthy.get_provenance(principal,project,execution_id)
    assert before["execution"]["status"]=="RUNNING" and len(before["results"])==1
    assert [a["status"] for a in before["attempts"]]==(["SUCCEEDED"] if point=="partial_after_tx_b" else ["SUCCEEDED","RETRYABLE_FAILURE"])
    calls=len(provider.calls)
    healthy.recover(_command("recover",principal,project,execution_id))
    after=healthy.get_provenance(principal,project,execution_id)
    pr204_trace.record(point=point,before=before,after=after,provider_calls=len(provider.calls))
    assert after["execution"]["status"]=="FAILED" and after["execution"]["failure_code"]=="RECOVERY_INTERRUPTED"
    assert after["attempts"]==before["attempts"] and after["queries"]==before["queries"] and after["results"]==before["results"]
    assert len(provider.calls)==calls and sum(e["kind"]=="FINISHED" for e in after["events"])==1
