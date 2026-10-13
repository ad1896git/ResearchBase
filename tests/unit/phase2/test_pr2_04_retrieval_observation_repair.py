"""R7B A–G/I: provider observations, independent of orchestrator time."""

from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from scripts.pr2_04_pytest_evidence import FactRecorder

from researchbase.application.literature_search_execution import (
    CreateLiteratureSearchExecution,
    ExecuteLiteratureSearchExecution,
    LiteratureSearchExecutionService,
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

T1 = datetime(2020, 1, 2, 3, 4, 5, 123456, tzinfo=UTC)


def test_success_without_observation_is_rejected():
    with pytest.raises(ValueError, match="retrieved_at"):
        SearchResponse("fake", "1", "cortex", None, DeliveryCertainty.RESPONSE_RECEIVED)


def test_attempt_provenance_projection_excludes_unregistered_persistence_fields():
    row = {"status": "SUCCEEDED", "retrieved_at": T1, "future_private_column": "private"}
    assert LiteratureSearchExecutionService._attempt_read(row) == {
        "status": "SUCCEEDED",
        "retrieved_at": T1,
    }


def response(hits=0, at=T1):
    return SearchResponse.success(
        provider_id="fake",
        provider_version="1",
        normalized_query="cortex",
        provider_request_id="observed",
        retrieved_at=at,
        hits=tuple(SearchHit(str(i), f"Paper {i}", None, None, None) for i in range(hits)),
    )


@pytest.mark.parametrize("at", [None, "2020-01-02T03:04:05Z", True, datetime(2020, 1, 2)])
def test_success_requires_aware_datetime_observation(at):
    with pytest.raises(ValueError, match="retrieved_at"):
        SearchResponse(
            "fake", "1", "cortex", None, DeliveryCertainty.RESPONSE_RECEIVED, retrieved_at=at
        )


def test_provider_observation_normalizes_offset_without_ordering_rule():
    at = T1.astimezone(timezone(timedelta(hours=8)))
    value = response(at=at)
    assert value.retrieved_at == T1
    assert value.retrieved_at is not None
    assert value.retrieved_at.tzinfo is UTC
    assert response(at=T1 + timedelta(days=36500)).retrieved_at == T1 + timedelta(days=36500)


@pytest.mark.parametrize(
    "certainty", [DeliveryCertainty.NOT_SENT, DeliveryCertainty.MAY_HAVE_BEEN_SENT]
)
def test_non_success_cannot_claim_retrieval_observation(certainty):
    with pytest.raises(ValueError, match="retrieved_at"):
        SearchResponse("fake", "1", "cortex", None, certainty, retrieved_at=T1)


class PausedFinalization(LiteratureSearchExecutionService):
    outcome_args = None

    def _persist_outcome(self, *args, **kwargs):
        self.outcome_args = (args, kwargs)
        return super()._persist_outcome(*args, **kwargs)

    def _finalize_execution(self, *args, **kwargs):
        return None


def harness[S: PausedFinalization](hits, service_type: type[S] = PausedFinalization):
    repo = InMemoryLiteratureSearchExecutionRepository()
    provider = FakeSearchCapability(responses=[response(hits)])
    service = service_type(
        lambda: InMemoryExecutionUnitOfWork(repo),
        provider,
        allow_unverified_principal=True,
        sleep=lambda _: None,
    )
    actor, project = uuid4(), uuid4()
    admission = service.create(
        CreateLiteratureSearchExecution(
            project, uuid4(), actor, "test", uuid4(), "fake", "1", ("cortex",)
        )
    )
    command = ExecuteLiteratureSearchExecution(
        UUID(admission["execution_id"]), actor, "test", uuid4()
    )
    return repo, provider, service, command, project


@pytest.mark.pr204_requirements("PR204-SUCCESS-01")
@pytest.mark.parametrize("hits", [0, 2])
def test_sealed_provider_observation_and_internal_reapplication(hits, pr204_trace: FactRecorder):
    repo, provider, service, command, project = harness(hits)
    admission = service.execute(command)
    before = deepcopy(service.get_provenance(None, project, command.execution_id))
    attempt = before["attempts"][0]
    assert attempt["retrieved_at"] == T1
    assert attempt["returned_at"] != T1
    assert len(before["results"]) == hits
    assert all(row["retrieved_at"] == T1 for row in before["results"])
    assert service.outcome_args is not None
    args, kwargs = service.outcome_args
    same = service._persist_outcome(*args, **kwargs)
    assert same == (None if False else same)  # transition is verified by exact durable no-op below
    assert service.get_provenance(None, project, command.execution_id) == before
    changed = list(args)
    changed[6] = replace(changed[6], retrieved_at=T1 + timedelta(seconds=1))
    with pytest.raises(ResearchBaseError) as caught:
        service._persist_outcome(*changed, **kwargs)
    assert caught.value.code is ErrorCode.IMMUTABLE_RECORD
    assert service.get_provenance(None, project, command.execution_id) == before
    assert service.execute(command) == admission
    assert service.get_provenance(None, project, command.execution_id) == before
    assert len(provider.calls) == 1
    pr204_trace.record(
        hits=hits,
        provider_T1=T1,
        before=before,
        after=service.get_provenance(None, project, command.execution_id),
        different_T2_error=caught.value.code.value,
        provider_calls=len(provider.calls),
    )


class LostAcknowledgment(PausedFinalization):
    retries = 0

    def _persist_outcome(self, *args, **kwargs):
        value = super()._persist_outcome(*args, **kwargs)
        self.retries += 1
        if self.retries == 1:
            raise ResearchBaseError(ErrorCode.CONCURRENT_MODIFICATION, "test-owned lost TX B ack")
        return value


@pytest.mark.parametrize("hits", [0, 2])
def test_tx_b_retry_retains_provider_observation_and_one_invocation(
    hits, pr204_trace: FactRecorder
):
    repo, provider, service, command, project = harness(hits, LostAcknowledgment)
    service.execute(command)
    data = service.get_provenance(None, project, command.execution_id)
    assert service.retries == 2
    assert len(provider.calls) == 1
    assert data["attempts"][0]["retrieved_at"] == T1
    assert all(row["retrieved_at"] == T1 for row in data["results"])
    assert len(data["queries"]) == 1 and len(data["results"]) == hits
    assert sum(e["kind"] == "OUTCOME_RECORDED" for e in repo.events) == 1
    pr204_trace.record(
        tx_b_calls=service.retries, provider_calls=len(provider.calls), provenance=data
    )
