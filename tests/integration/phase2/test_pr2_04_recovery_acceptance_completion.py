"""Additional real-PG recovery facets; no synthetic identity or deadline writes."""

from dataclasses import replace
from datetime import datetime
from time import monotonic, sleep
from uuid import UUID, uuid4

import pytest
from scripts.pr2_04_pytest_evidence import FactRecorder
from sqlalchemy import text

from researchbase.application.literature_search_execution import LiteratureSearchExecutionService
from researchbase.application.literature_search_provider import ProviderError, ProviderFailureKind
from researchbase.application.phase2_identity import AssignProjectRole
from researchbase.domain.literature_search_execution import DeliveryCertainty, SearchResponse
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.test_pr2_00_challenges import _service as _identity_service
from tests.integration.phase2.test_pr2_03_effective_authority import _provision
from tests.integration.phase2.test_pr2_04_execution_recovery import ReservedBeforeInvocation
from tests.integration.phase2.test_pr2_04_idempotency_coverage import (
    _command,
    _execution_setup,
    _service,
    _snapshot,
)
from tests.unit.phase2.test_pr2_04_provider_coverage import ScriptedProvider, success


class TestOwnedInterruption(RuntimeError):
    """Raised outside provider exception classification to retain durable boundary."""


@pytest.fixture
def completion_case(phase2_database_url):
    yield from _execution_setup(phase2_database_url)


def _await_recovery_deadline(engine, deadline):
    assert isinstance(deadline, datetime)
    stop = monotonic() + 40
    samples = []
    while True:
        with engine.connect() as connection:
            at = connection.execute(text("SELECT clock_timestamp()")).scalar_one()
        samples.append(at)
        if at >= deadline:
            return samples
        assert monotonic() < stop, "actual PostgreSQL recovery deadline was not reached"
        sleep(min(0.25, (deadline - at).total_seconds()))


def _protected(snapshot):
    return {key: rows for key, rows in snapshot.items() if key != "receipts"}


@pytest.mark.pr204_requirements("PR204-AUTH-04")
@pytest.mark.parametrize("boundary", ["before_invocation", "lost_response"])
def test_pg_replacement_writer_recovers_expired_reservation_without_unproved_response(
    completion_case, phase2_database_url, boundary, pr204_trace: FactRecorder
):
    engine, _, _, initiator, project, create = completion_case
    identity, _, _ = _identity_service(phase2_database_url)
    replacement, _ = _provision(identity, initiator)
    identity.assign_project_role(
        AssignProjectRole(
            initiator, project, replacement.actor_id, "RESEARCHER", "recovery proof", uuid4()
        )
    )
    provider = ScriptedProvider([success("normalization evidence", "provider-a", 2)], "provider-a")
    captured = []

    class StopBeforeOutcome(LiteratureSearchExecutionService):
        def _persist_outcome(self, *args, **kwargs):
            captured.append((args, kwargs))
            raise TestOwnedInterruption("returned response was not persisted")

    cls = ReservedBeforeInvocation if boundary == "before_invocation" else StopBeforeOutcome
    driver = _service(engine, provider, cls)
    execution_id = UUID(driver.create(replace(create, timeout_seconds=1))["execution_id"])
    execute = _command("execute", initiator, project, execution_id)
    if boundary == "lost_response":
        with pytest.raises(TestOwnedInterruption):
            driver.execute(execute)
        assert len(captured) == 1
    else:
        driver.execute(execute)
    before = _snapshot(engine, project)
    calls = 0 if boundary == "before_invocation" else 1
    assert len(provider.calls) == calls
    assert len(before["attempts"]) == 1 and before["attempts"][0]["status"] == "RESERVED"
    assert before["executions"][0]["status"] == "RUNNING"
    assert before["executions"][0]["row_version"] == 2
    assert before["queries"] == before["results"] == []
    recovery = _service(engine, provider)
    denied = _command("recover", replacement, project, execution_id)
    with engine.connect() as connection:
        early_at = connection.execute(text("SELECT clock_timestamp()")).scalar_one()
    deadline = before["attempts"][0]["recovery_after"]
    assert early_at < deadline
    with pytest.raises(ResearchBaseError) as early:
        recovery.recover(denied)
    assert early.value.code is ErrorCode.CONCURRENT_MODIFICATION
    assert _snapshot(engine, project) == before and len(provider.calls) == calls
    samples = _await_recovery_deadline(engine, deadline)
    command = _command("recover", replacement, project, execution_id)
    admission = recovery.recover(command)
    after = _snapshot(engine, project)
    execution, attempt = after["executions"][0], after["attempts"][0]
    assert execution["status"] == "UNKNOWN" and execution["row_version"] == 4
    assert execution["failure_code"] == "RECOVERY_OUTCOME_UNKNOWN"
    assert execution["requested_by"] == execution["executed_by"] == initiator.actor_id
    assert attempt["id"] == before["attempts"][0]["id"]
    assert attempt["created_by"] == initiator.actor_id
    assert attempt["status"] == "UNKNOWN" and attempt["row_version"] == 2
    assert attempt["failure_code"] == "RECOVERY_OUTCOME_UNKNOWN"
    assert attempt["delivery_certainty"] == "MAY_HAVE_BEEN_SENT"
    assert attempt["invoked_at"] is None and attempt["returned_at"] is None
    assert attempt["retrieved_at"] is None and attempt["query_record_id"] is None
    assert attempt["result_count"] == 0 and after["queries"] == after["results"] == []
    for kind in ("OUTCOME_RECORDED", "FINISHED"):
        matching = [event for event in after["events"] if event["kind"] == kind]
        assert len(matching) == 1 and matching[0]["created_by"] == replacement.actor_id
    assert len(after["receipts"]) == len(before["receipts"]) + 1
    assert len(provider.calls) == calls
    assert recovery.recover(command) == admission and _snapshot(engine, project) == after
    late_error = None
    if captured:
        args, kwargs = captured[0]
        with pytest.raises(ResearchBaseError) as late:
            recovery._persist_outcome(*args, **kwargs)
        late_error = late.value.code.value
        assert late.value.code is ErrorCode.INVALID_STATE_TRANSITION
        assert _snapshot(engine, project) == after and len(provider.calls) == calls
    pr204_trace.record(
        boundary=boundary,
        initiator=initiator.actor_id,
        recovery_actor=replacement.actor_id,
        early_database_time=early_at,
        recovery_after=deadline,
        final_database_time=samples[-1],
        early_error=early.value.code.value,
        late_original_response_error=late_error,
        before=before,
        after=after,
        admission=admission,
        provider_calls=calls,
        forbidden_new_query_results=0,
    )


@pytest.mark.pr204_requirements("PR204-CRASH-06")
@pytest.mark.parametrize("boundary", ["between_queries", "retry_backoff"])
def test_pg_recovery_stops_known_incomplete_work_and_preserves_prior_hits(
    completion_case, boundary, pr204_trace: FactRecorder
):
    engine, _, _, principal, project, create = completion_case
    script: list[SearchResponse | ProviderError] = [success("first query", "provider-a", 2)]
    if boundary == "retry_backoff":
        script.append(
            ProviderError(
                ProviderFailureKind.RETRYABLE,
                "PROVIDER_RATE_LIMIT",
                delivery_certainty=DeliveryCertainty.RESPONSE_RECEIVED,
                retry_after_seconds=1,
            )
        )
    provider = ScriptedProvider(script, "provider-a")

    class StopBeforeNextReservation(LiteratureSearchExecutionService):
        drive_calls = 0

        def _drive(self, *args, **kwargs):
            self.drive_calls += 1
            if self.drive_calls == 2:
                raise TestOwnedInterruption("before next reservation")
            return super()._drive(*args, **kwargs)

    def interrupted_backoff(seconds):
        assert seconds == 1.0
        assert engine.pool.checkedout() == 0
        raise TestOwnedInterruption("after sealed retryable outcome before backoff")

    cls = (
        StopBeforeNextReservation
        if boundary == "between_queries"
        else LiteratureSearchExecutionService
    )
    driver = _service(engine, provider, cls, sleep=interrupted_backoff)
    execution_id = UUID(
        driver.create(replace(create, queries=("first query", "second query")))["execution_id"]
    )
    with pytest.raises(TestOwnedInterruption):
        driver.execute(_command("execute", principal, project, execution_id))
    before = _snapshot(engine, project)
    expected_calls = 1 if boundary == "between_queries" else 2
    assert (
        len(provider.calls) == len(before["attempts"]) == len(before["queries"]) == expected_calls
    )
    assert len(before["results"]) == 2
    assert before["executions"][0]["status"] == "RUNNING"
    assert not any(a["status"] == "RESERVED" for a in before["attempts"])
    assert not any(e["kind"] == "FINISHED" for e in before["events"])
    if boundary == "retry_backoff":
        retry = next(a for a in before["attempts"] if a["status"] == "RETRYABLE_FAILURE")
        assert retry["retry_after_seconds"] == 1
    recovery = _service(engine, provider)
    command = _command("recover", principal, project, execution_id)
    admission = recovery.recover(command)
    after = _snapshot(engine, project)
    execution = after["executions"][0]
    assert execution["status"] == "FAILED" and execution["failure_code"] == "RECOVERY_INTERRUPTED"
    assert execution["row_version"] == before["executions"][0]["row_version"] + 1
    for key in ("attempts", "queries", "results"):
        assert after[key] == before[key]
    assert len(after["events"]) == len(before["events"]) + 1
    assert sum(e["kind"] == "FINISHED" for e in after["events"]) == 1
    assert len(after["receipts"]) == len(before["receipts"]) + 1
    assert len(provider.calls) == expected_calls
    assert recovery.recover(command) == admission and _snapshot(engine, project) == after
    with pytest.raises(ResearchBaseError) as stopped:
        recovery.execute(_command("execute", principal, project, execution_id))
    assert stopped.value.code is ErrorCode.INVALID_STATE_TRANSITION
    assert _snapshot(engine, project) == after and len(provider.calls) == expected_calls
    pr204_trace.record(
        boundary=boundary,
        before=before,
        after=after,
        provider_calls=expected_calls,
        admission=admission,
        new_execute_error=stopped.value.code.value,
        preserved_prior_hits=2,
        exact_replay_read_only=True,
    )
