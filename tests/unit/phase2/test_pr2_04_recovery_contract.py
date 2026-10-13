"""Frozen recovery decisions, using real orchestration with deterministic persistence.

These tests do not establish PostgreSQL locking/trigger acceptance. They catch
replacement of a specific durable failure reason by a generic recovery reason.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from scripts.pr2_04_pytest_evidence import FactRecorder

from researchbase.application.literature_search_execution import (
    CancelLiteratureSearchExecution,
    CreateLiteratureSearchExecution,
    ExecuteLiteratureSearchExecution,
    LiteratureSearchExecutionService,
    RecoverLiteratureSearchExecution,
)
from researchbase.application.literature_search_provider import FakeSearchCapability
from researchbase.domain.literature_search_execution import (
    DeliveryCertainty,
    SearchHit,
    SearchResponse,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.in_memory_literature_search_execution import (
    InMemoryExecutionUnitOfWork,
    InMemoryLiteratureSearchExecutionRepository,
)
from tests.pr2_04_provider_observations import PROVIDER_RETRIEVED_AT


class ControlledClockRepository(InMemoryLiteratureSearchExecutionRepository):
    now = datetime(2026, 10, 7, tzinfo=UTC)

    def database_now(self) -> datetime:
        return self.now


class InterruptedDriver(LiteratureSearchExecutionService):
    def _drive(self, execution_id, actor_id, principal=None, reserved=None, project_id=None):
        # Test crash point: reservation committed, but invocation has not run.
        return None


class InterruptedFinalizer(LiteratureSearchExecutionService):
    def _finalize_execution(self, execution_id, actor_id, status, principal=None, project_id=None):
        # Test crash point: TX B committed, TX C did not run.
        return None


@pytest.mark.pr204_requirements("PR204-UNKNOWN-03", "PR204-CRASH-03")
def test_expired_unobserved_reservation_retains_recovery_unknown_reason(
    pr204_trace: FactRecorder,
) -> None:
    repository = ControlledClockRepository()
    provider = FakeSearchCapability()
    actor, project = uuid4(), uuid4()

    def factory():
        return InMemoryExecutionUnitOfWork(repository)

    service = InterruptedDriver(factory, provider, allow_unverified_principal=True)
    admission = service.create(
        CreateLiteratureSearchExecution(
            project,
            uuid4(),
            actor,
            "test",
            uuid4(),
            "fake",
            "1",
            ("query",),
        )
    )
    execution_id = UUID(admission["execution_id"])
    service.execute(ExecuteLiteratureSearchExecution(execution_id, actor, "test", uuid4()))
    reserved = repository.attempts(execution_id)[0]
    recovery_after = reserved["recovery_after"]
    assert isinstance(recovery_after, datetime)
    repository.now = recovery_after + timedelta(seconds=1)
    recovery = LiteratureSearchExecutionService(factory, provider, allow_unverified_principal=True)
    recovery.recover(RecoverLiteratureSearchExecution(execution_id, actor, "test", uuid4()))
    provenance = recovery.get_provenance(None, project, execution_id)
    pr204_trace.record(
        storage_kind="deterministic_in_memory",
        provenance=provenance,
        provider_calls=len(provider.calls),
        recovery_at=repository.now,
    )
    assert provider.calls == []
    assert provenance["queries"] == [] and provenance["results"] == []
    assert provenance["execution"]["status"] == "UNKNOWN"
    assert provenance["attempts"][0]["invoked_at"] is None
    assert provenance["attempts"][0]["failure_code"] == "RECOVERY_OUTCOME_UNKNOWN"
    assert provenance["execution"]["failure_code"] == "RECOVERY_OUTCOME_UNKNOWN"


@pytest.mark.pr204_requirements("PR204-CRASH-06")
def test_recovery_after_known_permanent_outcome_preserves_original_failure_reason(
    pr204_trace: FactRecorder,
) -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()
    provider = FakeSearchCapability(
        responses=[
            SearchResponse(
                "fake",
                "1",
                "query",
                None,
                DeliveryCertainty.RESPONSE_RECEIVED,
                failure_code="PROVIDER_PERMANENT",
            )
        ]
    )
    actor, project = uuid4(), uuid4()

    def factory():
        return InMemoryExecutionUnitOfWork(repository)

    service = InterruptedFinalizer(factory, provider, allow_unverified_principal=True)
    admission = service.create(
        CreateLiteratureSearchExecution(
            project,
            uuid4(),
            actor,
            "test",
            uuid4(),
            "fake",
            "1",
            ("query",),
        )
    )
    execution_id = UUID(admission["execution_id"])
    service.execute(ExecuteLiteratureSearchExecution(execution_id, actor, "test", uuid4()))
    before = service.get_provenance(None, project, execution_id)
    assert before["execution"]["status"] == "RUNNING"
    assert before["attempts"][0]["status"] == "PERMANENT_FAILURE"
    recovery = LiteratureSearchExecutionService(factory, provider, allow_unverified_principal=True)
    recovery.recover(RecoverLiteratureSearchExecution(execution_id, actor, "test", uuid4()))
    after = recovery.get_provenance(None, project, execution_id)
    pr204_trace.record(
        storage_kind="deterministic_in_memory",
        before=before,
        after=after,
        provider_calls=len(provider.calls),
    )
    assert len(provider.calls) == 1
    assert after["attempts"] == before["attempts"]
    assert after["execution"]["status"] == "FAILED"
    assert after["execution"]["failure_code"] == "PROVIDER_PERMANENT"


@pytest.mark.parametrize(
    ("failure_code", "certainty", "terminal"),
    [
        ("PROVIDER_MALFORMED", DeliveryCertainty.RESPONSE_RECEIVED, "FAILED"),
        ("PROVIDER_OUTCOME_UNKNOWN", DeliveryCertainty.MAY_HAVE_BEEN_SENT, "UNKNOWN"),
    ],
)
@pytest.mark.pr204_requirements("PR204-CRASH-06")
def test_recovery_derives_terminal_reason_from_sealed_provider_outcome(
    failure_code: str,
    certainty: DeliveryCertainty,
    terminal: str,
    pr204_trace: FactRecorder,
) -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()
    provider = FakeSearchCapability(
        responses=[SearchResponse("fake", "1", "query", None, certainty, failure_code=failure_code)]
    )

    def factory():
        return InMemoryExecutionUnitOfWork(repository)

    actor, project = uuid4(), uuid4()
    service = InterruptedFinalizer(factory, provider, allow_unverified_principal=True)
    admitted = service.create(
        CreateLiteratureSearchExecution(
            project, uuid4(), actor, "test", uuid4(), "fake", "1", ("query",)
        )
    )
    execution_id = UUID(admitted["execution_id"])
    service.execute(ExecuteLiteratureSearchExecution(execution_id, actor, "test", uuid4()))
    before = service.get_provenance(None, project, execution_id)
    assert before["execution"]["status"] == "RUNNING"
    recovery = LiteratureSearchExecutionService(factory, provider, allow_unverified_principal=True)
    command = RecoverLiteratureSearchExecution(execution_id, actor, "test", uuid4())
    admission = recovery.recover(command)
    after = recovery.get_provenance(None, project, execution_id)
    pr204_trace.record(
        storage_kind="deterministic_in_memory",
        before=before,
        after=after,
        provider_calls=len(provider.calls),
    )
    assert after["attempts"] == before["attempts"]
    assert after["queries"] == before["queries"] and after["results"] == before["results"]
    assert after["execution"]["status"] == terminal
    assert after["execution"]["failure_code"] == failure_code
    assert len(provider.calls) == 1

    # A distinct terminal recovery may insert its no-op receipt only. Exact replay is read-only.
    assert recovery.recover(command) == admission
    assert recovery.get_provenance(None, project, execution_id) == after
    recovery.recover(RecoverLiteratureSearchExecution(execution_id, actor, "test", uuid4()))
    final = recovery.get_provenance(None, project, execution_id)
    for field in ("execution", "attempts", "queries", "results", "events"):
        assert final[field] == after[field]
    assert len(final["receipts"]) == len(after["receipts"]) + 1
    assert len(provider.calls) == 1
    pr204_trace.record(
        phase="terminal_noop_and_replay", provenance=final, provider_calls=len(provider.calls)
    )


@pytest.mark.parametrize("failure_code", ["PROVIDER_PERMANENT", "PROVIDER_OUTCOME_UNKNOWN"])
@pytest.mark.pr204_requirements("PR204-CRASH-06")
def test_recovery_preserves_cancellation_and_uncertainty_precedence(
    failure_code: str,
    pr204_trace: FactRecorder,
) -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()
    certainty = (
        DeliveryCertainty.MAY_HAVE_BEEN_SENT
        if failure_code == "PROVIDER_OUTCOME_UNKNOWN"
        else DeliveryCertainty.RESPONSE_RECEIVED
    )
    provider = FakeSearchCapability(
        responses=[SearchResponse("fake", "1", "query", None, certainty, failure_code=failure_code)]
    )

    def factory():
        return InMemoryExecutionUnitOfWork(repository)

    actor, project = uuid4(), uuid4()
    service = InterruptedFinalizer(factory, provider, allow_unverified_principal=True)
    admitted = service.create(
        CreateLiteratureSearchExecution(
            project, uuid4(), actor, "test", uuid4(), "fake", "1", ("query",)
        )
    )
    execution_id = UUID(admitted["execution_id"])
    service.execute(ExecuteLiteratureSearchExecution(execution_id, actor, "test", uuid4()))

    def interrupt_after_c1():
        raise RuntimeError("C1 committed before recovery")

    cancellation = LiteratureSearchExecutionService(
        factory,
        provider,
        allow_unverified_principal=True,
        after_cancel_admission=interrupt_after_c1,
    )
    with pytest.raises(RuntimeError, match="C1 committed"):
        cancellation.cancel(CancelLiteratureSearchExecution(execution_id, actor, "test", uuid4()))
    before = service.get_provenance(None, project, execution_id)
    assert before["execution"]["status"] == "RUNNING"
    recovery = LiteratureSearchExecutionService(factory, provider, allow_unverified_principal=True)
    recovery.recover(RecoverLiteratureSearchExecution(execution_id, actor, "test", uuid4()))
    after = recovery.get_provenance(None, project, execution_id)
    pr204_trace.record(
        storage_kind="deterministic_in_memory",
        before=before,
        after=after,
        provider_calls=len(provider.calls),
    )
    expected_status = "UNKNOWN" if failure_code == "PROVIDER_OUTCOME_UNKNOWN" else "CANCELLED"
    expected_reason = failure_code if expected_status == "UNKNOWN" else "CANCELLED"
    assert after["execution"]["status"] == expected_status
    assert after["execution"]["failure_code"] == expected_reason
    assert after["attempts"] == before["attempts"]
    assert len(provider.calls) == 1
    assert sum(event["kind"] == "FINISHED" for event in after["events"]) == 1


@pytest.mark.pr204_requirements("PR204-UNKNOWN-03", "PR204-CRASH-03")
def test_recovery_before_deadline_denies_without_seal_receipt_or_redispatch(
    pr204_trace: FactRecorder,
) -> None:
    repository = ControlledClockRepository()
    provider = FakeSearchCapability()

    def factory():
        return InMemoryExecutionUnitOfWork(repository)

    actor, project = uuid4(), uuid4()
    service = InterruptedDriver(factory, provider, allow_unverified_principal=True)
    admitted = service.create(
        CreateLiteratureSearchExecution(
            project, uuid4(), actor, "test", uuid4(), "fake", "1", ("query",)
        )
    )
    execution_id = UUID(admitted["execution_id"])
    service.execute(ExecuteLiteratureSearchExecution(execution_id, actor, "test", uuid4()))
    before = service.get_provenance(None, project, execution_id)
    recovery = LiteratureSearchExecutionService(factory, provider, allow_unverified_principal=True)
    with pytest.raises(ResearchBaseError) as caught:
        recovery.recover(RecoverLiteratureSearchExecution(execution_id, actor, "test", uuid4()))
    after = recovery.get_provenance(None, project, execution_id)
    pr204_trace.record(
        storage_kind="deterministic_in_memory",
        before=before,
        after=after,
        error_code=caught.value.code.value,
        provider_calls=len(provider.calls),
    )
    assert caught.value.code is ErrorCode.CONCURRENT_MODIFICATION
    assert after == before
    assert provider.calls == []


@pytest.mark.pr204_requirements("PR204-UNKNOWN-03", "PR204-CRASH-03")
def test_recovery_resumes_durable_recovery_unknown_after_interrupted_finalization(
    pr204_trace: FactRecorder,
) -> None:
    repository = ControlledClockRepository()
    provider = FakeSearchCapability()

    def factory():
        return InMemoryExecutionUnitOfWork(repository)

    actor, project = uuid4(), uuid4()
    driver = InterruptedDriver(factory, provider, allow_unverified_principal=True)
    admitted = driver.create(
        CreateLiteratureSearchExecution(
            project, uuid4(), actor, "test", uuid4(), "fake", "1", ("query",)
        )
    )
    execution_id = UUID(admitted["execution_id"])
    driver.execute(ExecuteLiteratureSearchExecution(execution_id, actor, "test", uuid4()))
    recovery_after = repository.attempts(execution_id)[0]["recovery_after"]
    assert isinstance(recovery_after, datetime)
    repository.now = recovery_after  # At the exact recovery boundary, not earlier.

    class InterruptedRecovery(LiteratureSearchExecutionService):
        def _finalize_recovery(self, execution_id, actor_id, principal=None, project_id=None):
            return None

    interrupted = InterruptedRecovery(factory, provider, allow_unverified_principal=True)
    first = RecoverLiteratureSearchExecution(execution_id, actor, "test", uuid4())
    admission = interrupted.recover(first)
    pending = interrupted.get_provenance(None, project, execution_id)
    pr204_trace.record(
        phase="after_recovery_seal_before_finalization",
        storage_kind="deterministic_in_memory",
        provenance=pending,
        provider_calls=len(provider.calls),
    )
    assert pending["execution"]["status"] == "RUNNING"
    assert pending["execution"]["row_version"] == 3
    assert pending["attempts"][0]["failure_code"] == "RECOVERY_OUTCOME_UNKNOWN"
    assert pending["attempts"][0]["row_version"] == 2
    assert pending["queries"] == [] and pending["results"] == []
    assert interrupted.recover(first) == admission
    assert interrupted.get_provenance(None, project, execution_id) == pending

    recovery = LiteratureSearchExecutionService(factory, provider, allow_unverified_principal=True)
    recovery.recover(RecoverLiteratureSearchExecution(execution_id, actor, "test", uuid4()))
    final = recovery.get_provenance(None, project, execution_id)
    pr204_trace.record(
        phase="after_second_recovery", provenance=final, provider_calls=len(provider.calls)
    )
    assert final["attempts"] == pending["attempts"]
    assert final["execution"]["status"] == "UNKNOWN"
    assert final["execution"]["failure_code"] == "RECOVERY_OUTCOME_UNKNOWN"
    assert final["execution"]["row_version"] == 4
    assert sum(event["kind"] == "FINISHED" for event in final["events"]) == 1
    assert provider.calls == []


@pytest.mark.pr204_requirements("PR204-UNKNOWN-03", "PR204-CRASH-03")
def test_recovery_finalization_retry_rereads_terminal_state_without_resealing(
    pr204_trace: FactRecorder,
) -> None:
    repository = ControlledClockRepository()
    provider = FakeSearchCapability()

    def factory():
        return InMemoryExecutionUnitOfWork(repository)

    actor, project = uuid4(), uuid4()
    driver = InterruptedDriver(factory, provider, allow_unverified_principal=True)
    admitted = driver.create(
        CreateLiteratureSearchExecution(
            project, uuid4(), actor, "test", uuid4(), "fake", "1", ("query",)
        )
    )
    execution_id = UUID(admitted["execution_id"])
    driver.execute(ExecuteLiteratureSearchExecution(execution_id, actor, "test", uuid4()))
    recovery_after = repository.attempts(execution_id)[0]["recovery_after"]
    assert isinstance(recovery_after, datetime)
    repository.now = recovery_after

    class LostFinalizationAcknowledgment(LiteratureSearchExecutionService):
        finalization_calls = 0

        def _finalize_recovery(self, *args, **kwargs):
            self.finalization_calls += 1
            super()._finalize_recovery(*args, **kwargs)
            if self.finalization_calls == 1:
                raise ResearchBaseError(
                    ErrorCode.CONCURRENT_MODIFICATION, "test-owned lost finalization acknowledgment"
                )

    recovery = LostFinalizationAcknowledgment(factory, provider, allow_unverified_principal=True)
    recovery.recover(RecoverLiteratureSearchExecution(execution_id, actor, "test", uuid4()))
    final = recovery.get_provenance(None, project, execution_id)
    pr204_trace.record(
        storage_kind="deterministic_in_memory",
        provenance=final,
        finalization_calls=recovery.finalization_calls,
        provider_calls=len(provider.calls),
    )
    assert recovery.finalization_calls == 2
    assert final["execution"]["row_version"] == 4
    assert final["execution"]["failure_code"] == "RECOVERY_OUTCOME_UNKNOWN"
    assert final["attempts"][0]["row_version"] == 2
    assert sum(event["kind"] == "OUTCOME_RECORDED" for event in final["events"]) == 1
    assert sum(event["kind"] == "FINISHED" for event in final["events"]) == 1
    assert len(final["receipts"]) == 3
    assert provider.calls == []


@pytest.mark.pr204_requirements("PR204-CRASH-06")
def test_recovery_of_known_incomplete_work_keeps_interrupted_reason_and_prior_hits(
    pr204_trace: FactRecorder,
) -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()
    provider = FakeSearchCapability(
        responses=[
            SearchResponse.success(
                provider_id="fake",
                provider_version="1",
                normalized_query="first",
                provider_request_id="known-first-response",
                hits=(SearchHit("hit-1", "First observation", None, None, None),),
                retrieved_at=PROVIDER_RETRIEVED_AT,
            )
        ]
    )

    def factory():
        return InMemoryExecutionUnitOfWork(repository)

    class InterruptedBetweenQueries(LiteratureSearchExecutionService):
        def _persist_outcome(self, *args, **kwargs):
            super()._persist_outcome(*args, **kwargs)
            raise RuntimeError("TX B committed; next query was not dispatched")

    actor, project = uuid4(), uuid4()
    service = InterruptedBetweenQueries(factory, provider, allow_unverified_principal=True)
    admitted = service.create(
        CreateLiteratureSearchExecution(
            project, uuid4(), actor, "test", uuid4(), "fake", "1", ("first", "second")
        )
    )
    execution_id = UUID(admitted["execution_id"])
    with pytest.raises(RuntimeError, match="TX B committed"):
        service.execute(ExecuteLiteratureSearchExecution(execution_id, actor, "test", uuid4()))
    before = service.get_provenance(None, project, execution_id)
    assert before["execution"]["status"] == "RUNNING"
    assert [attempt["status"] for attempt in before["attempts"]] == ["SUCCEEDED"]
    assert len(before["results"]) == 1
    recovery = LiteratureSearchExecutionService(factory, provider, allow_unverified_principal=True)
    recovery.recover(RecoverLiteratureSearchExecution(execution_id, actor, "test", uuid4()))
    after = recovery.get_provenance(None, project, execution_id)
    pr204_trace.record(
        storage_kind="deterministic_in_memory",
        before=before,
        after=after,
        provider_calls=len(provider.calls),
    )
    assert after["execution"]["status"] == "FAILED"
    assert after["execution"]["failure_code"] == "RECOVERY_INTERRUPTED"
    for field in ("attempts", "queries", "results"):
        assert after[field] == before[field]
    assert len(provider.calls) == 1
