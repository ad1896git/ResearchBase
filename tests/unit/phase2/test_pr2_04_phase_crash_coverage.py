"""Deterministic crash-position semantics, not PostgreSQL isolation evidence."""

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
from researchbase.domain.literature_search_execution import SearchHit, SearchResponse
from researchbase.persistence.in_memory_literature_search_execution import (
    InMemoryExecutionUnitOfWork,
    InMemoryLiteratureSearchExecutionRepository,
)
from tests.pr2_04_provider_observations import PROVIDER_RETRIEVED_AT


@pytest.mark.parametrize(
    "point",
    [
        pytest.param("before_create", marks=pytest.mark.pr204_requirements("PR204-CRASH-01")),
        pytest.param(
            "after_create", marks=pytest.mark.pr204_requirements("PR204-CRASH-02", "PR204-IDEM-06")
        ),
        pytest.param(
            "after_reserve",
            marks=pytest.mark.pr204_requirements("PR204-CRASH-03", "PR204-BOUND-03"),
        ),
        pytest.param(
            "provider_return",
            marks=pytest.mark.pr204_requirements("PR204-CRASH-04", "PR204-IDEM-06"),
        ),
        pytest.param("outcome_rollback", marks=pytest.mark.pr204_requirements("PR204-CRASH-05")),
        pytest.param("after_outcome", marks=pytest.mark.pr204_requirements("PR204-CRASH-06")),
        pytest.param(
            "terminal_ack", marks=pytest.mark.pr204_requirements("PR204-CRASH-08", "PR204-IDEM-06")
        ),
        pytest.param(
            "after_c1", marks=pytest.mark.pr204_requirements("PR204-CRASH-07", "PR204-CANCEL-01")
        ),
    ],
)
def test_interrupted_phase_replay_retains_only_committed_facts(
    point: str, pr204_trace: FactRecorder
) -> None:
    class Repository(InMemoryLiteratureSearchExecutionRepository):
        now = datetime(2026, 10, 7, tzinfo=UTC)

        def database_now(self):
            return self.now

        def create(self, *args):
            if point == "before_create":
                raise RuntimeError("test crash")
            return super().create(*args)

        def append_results(self, *args):
            super().append_results(*args)
            if point == "outcome_rollback":
                raise RuntimeError("test crash")

    class Interrupted(LiteratureSearchExecutionService):
        def _create_once(self, command):
            result = super()._create_once(command)
            if point == "after_create":
                raise RuntimeError("test crash")
            return result

        def _drive(self, *args, **kwargs):
            if point == "after_reserve":
                raise RuntimeError("test crash")
            return super()._drive(*args, **kwargs)

        def _persist_outcome(self, *args, **kwargs):
            if point == "provider_return":
                raise RuntimeError("test crash")
            return super()._persist_outcome(*args, **kwargs)

        def _finalize_execution(self, *args, **kwargs):
            if point == "after_outcome":
                raise RuntimeError("test crash")
            result = super()._finalize_execution(*args, **kwargs)
            if point == "terminal_ack":
                raise RuntimeError("test crash")
            return result

    repository = Repository()
    provider = FakeSearchCapability(
        responses=[
            SearchResponse.success(
                provider_id="fake",
                provider_version="1",
                normalized_query="query",
                provider_request_id="known-response",
                hits=(SearchHit("hit", "Paper", None, None, None),),
                retrieved_at=PROVIDER_RETRIEVED_AT,
            )
        ]
    )
    factory = lambda: InMemoryExecutionUnitOfWork(repository)  # noqa: E731

    def crash_after_c1():
        raise RuntimeError("test crash")

    service = Interrupted(
        factory, provider, allow_unverified_principal=True, after_cancel_admission=crash_after_c1
    )
    healthy = LiteratureSearchExecutionService(factory, provider, allow_unverified_principal=True)
    actor, project, plan = uuid4(), uuid4(), uuid4()
    create = CreateLiteratureSearchExecution(
        project, plan, actor, "test", uuid4(), "fake", "1", ("query",)
    )
    execution_id = None
    execute = None
    cancel = None
    with pytest.raises(RuntimeError, match="test crash"):
        admitted = service.create(create)
        execution_id = UUID(admitted["execution_id"])
        if point == "after_c1":
            cancel = CancelLiteratureSearchExecution(execution_id, actor, "test", uuid4())
            service.cancel(cancel)
        else:
            execute = ExecuteLiteratureSearchExecution(execution_id, actor, "test", uuid4())
            service.execute(execute)
    pr204_trace.record(
        storage_kind="deterministic_in_memory",
        crash_point=point,
        execution_count=len(repository.executions),
        receipt_count=len(repository.receipts),
        event_count=len(repository.events),
        provider_calls=len(provider.calls),
    )
    if point == "before_create":
        assert repository.executions == {} and repository.receipts == {} and repository.events == []
        assert repository.attempt_rows == {} and provider.calls == []
        return
    if point == "after_create":
        admission = healthy.create(create)
        execution_id = UUID(admission["execution_id"])
    assert execution_id is not None
    before = healthy.get_provenance(None, project, execution_id)
    pr204_trace.record(before_recovery=before, provider_calls=len(provider.calls))
    if point == "after_create":
        assert (
            before["execution"]["status"] == "PLANNED" and before["execution"]["row_version"] == 1
        )
        assert len(before["receipts"]) == 1 and before["attempts"] == []
        healthy.recover(RecoverLiteratureSearchExecution(execution_id, actor, "test", uuid4()))
        assert healthy.get(None, project, execution_id)["status"] == "PLANNED"
        assert provider.calls == []
        healthy.cancel(CancelLiteratureSearchExecution(execution_id, actor, "test", uuid4()))
        assert healthy.get(None, project, execution_id)["status"] == "CANCELLED"
        assert provider.calls == []
        return
    if point == "after_c1":
        assert (
            before["execution"]["status"] == "PLANNED" and before["execution"]["row_version"] == 2
        )
        assert [e["kind"] for e in before["events"]] == ["CREATED", "CANCEL_REQUESTED"]
        assert cancel is not None
        assert healthy.cancel(cancel)["accepted_row_version"] == 2
        assert healthy.get_provenance(None, project, execution_id) == before
        expected = "CANCELLED"
    elif point in {"after_reserve", "provider_return", "outcome_rollback"}:
        assert before["execution"]["status"] == "RUNNING"
        assert before["attempts"][0]["status"] == "RESERVED"
        assert before["queries"] == [] and before["results"] == []
        assert len(before["receipts"]) == 2
        assert execute is not None
        healthy.execute(execute)
        assert healthy.get_provenance(None, project, execution_id) == before
        repository.now = before["attempts"][0]["recovery_after"] + timedelta(seconds=1)
        expected = "UNKNOWN"
    else:
        assert before["attempts"][0]["status"] == "SUCCEEDED"
        assert len(before["queries"]) == 1 and len(before["results"]) == 1
        assert before["execution"]["status"] == (
            "SUCCEEDED" if point == "terminal_ack" else "RUNNING"
        )
        assert execute is not None
        healthy.execute(execute)
        assert healthy.get_provenance(None, project, execution_id) == before
        expected = "SUCCEEDED"
    calls = len(provider.calls)
    recover = RecoverLiteratureSearchExecution(execution_id, actor, "test", uuid4())
    receipt = healthy.recover(recover)
    after = healthy.get_provenance(None, project, execution_id)
    pr204_trace.record(after_recovery=after, provider_calls=len(provider.calls))
    assert after["execution"]["status"] == expected
    assert sum(e["kind"] == "FINISHED" for e in after["events"]) == 1
    assert len(provider.calls) == calls
    if point in {"after_outcome", "terminal_ack"}:
        assert after["attempts"] == before["attempts"]
        assert after["queries"] == before["queries"] and after["results"] == before["results"]
    elif point != "after_c1":
        assert after["queries"] == [] and after["results"] == []
        assert after["attempts"][0]["failure_code"] == "RECOVERY_OUTCOME_UNKNOWN"
        assert after["attempts"][0]["invoked_at"] is None
    assert healthy.recover(recover) == receipt
    assert healthy.get_provenance(None, project, execution_id) == after
    assert len(provider.calls) == calls
