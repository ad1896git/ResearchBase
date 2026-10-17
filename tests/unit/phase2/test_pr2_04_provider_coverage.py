"""Provider failure taxonomy and committed-outcome causal observations."""

from __future__ import annotations

import json
import socket
import urllib.request
from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from scripts.pr2_04_pytest_evidence import FactRecorder

from researchbase.application.literature_search_execution import (
    CancelLiteratureSearchExecution,
    CreateLiteratureSearchExecution,
    ExecuteLiteratureSearchExecution,
    LiteratureSearchExecutionService,
    SearchQueryInput,
)
from researchbase.application.literature_search_provider import (
    FakeSearchCapability,
    ProviderError,
    ProviderFailureKind,
)
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

CANARY = "PR204_SECRET_DO_NOT_PERSIST_9d8b"


class ScriptedProvider(FakeSearchCapability):
    def __init__(self, script: Sequence[object], capability_id: str = "fake") -> None:
        super().__init__(capability_id=capability_id)
        self.script = list(script)

    def search(self, request, context=None) -> Any:
        if self.observer:
            self.observer(request)
        self.calls.append(request)
        step = self.script.pop(0)
        if isinstance(step, Exception):
            raise step
        return step(request) if callable(step) else step


def success(query: str = "cortex", provider: str = "fake", hits: int = 0) -> SearchResponse:
    return SearchResponse.success(
        provider_id=provider,
        provider_version="1",
        normalized_query=query,
        provider_request_id="remote-safe",
        hits=tuple(SearchHit("duplicate", f"Paper {i}", None, None, None) for i in range(hits)),
        retrieved_at=PROVIDER_RETRIEVED_AT,
    )


RETRY_CASES = [
    ("429", "PROVIDER_RATE_LIMIT", DeliveryCertainty.RESPONSE_RECEIVED),
    ("503", "PROVIDER_TRANSIENT", DeliveryCertainty.RESPONSE_RECEIVED),
    ("transport-not-sent", "PROVIDER_TRANSIENT", DeliveryCertainty.NOT_SENT),
    ("timeout-not-sent", "PROVIDER_TIMEOUT", DeliveryCertainty.NOT_SENT),
]


def harness(script: list[object]):
    repo = InMemoryLiteratureSearchExecutionRepository()
    provider = ScriptedProvider(script)
    service = LiteratureSearchExecutionService(
        lambda: InMemoryExecutionUnitOfWork(repo),
        provider,
        sleep=lambda _: None,
        random_uniform=lambda _lo, _hi: 0,
        allow_unverified_principal=True,
    )
    actor, project = uuid4(), uuid4()
    created = service.create(
        CreateLiteratureSearchExecution(
            project, uuid4(), actor, "test", uuid4(), "fake", "1", ("cortex",)
        )
    )
    execution_id = UUID(created["execution_id"])
    command = ExecuteLiteratureSearchExecution(execution_id, actor, "test", uuid4())
    return repo, provider, service, command, project


@pytest.mark.pr204_requirements("PR204-PROV-01", "PR204-TRACE-02", "PR204-DOM-02")
@pytest.mark.parametrize("name,code,certainty", RETRY_CASES, ids=[c[0] for c in RETRY_CASES])
def test_safe_failure_commits_before_distinct_retry(
    name: str, code: str, certainty: DeliveryCertainty, pr204_trace: FactRecorder
) -> None:
    repo, provider, service, command, project = harness(
        [
            ProviderError(
                ProviderFailureKind.RETRYABLE,
                code,
                delivery_certainty=certainty,
                retry_after_seconds=0,
            ),
            success(),
        ]
    )
    observed = []

    def observe(request) -> None:
        prior = repo.attempts(command.execution_id)
        if observed:
            assert prior[0]["status"] == "RETRYABLE_FAILURE"
            assert len(repo.queries) == 1
            assert any(e["kind"] == "OUTCOME_RECORDED" for e in repo.events)
        assert prior[-1]["status"] == "RESERVED"
        observed.append(str(request.attempt_id))

    provider.observer = observe
    service.execute(command)
    attempts = repo.attempts(command.execution_id)
    assert len(provider.calls) == len(attempts) == len(repo.queries) == 2
    assert len(set(observed)) == 2
    assert [a["attempt_number"] for a in attempts] == [1, 2]
    assert [a["status"] for a in attempts] == ["RETRYABLE_FAILURE", "SUCCEEDED"]
    assert (
        attempts[0]["failure_code"] == code and attempts[0]["delivery_certainty"] == certainty.value
    )
    assert [q.ordinal for q in repo.queries] == [0, 1]
    assert len({q.query_hash for q in repo.queries}) == 2
    assert repo.executions[command.execution_id].status.value == "SUCCEEDED"
    pr204_trace.record(
        case=name,
        observed_attempts=observed,
        provenance=service.get_provenance(None, project, command.execution_id),
    )


@pytest.mark.pr204_requirements("PR204-PROV-03", "PR204-SEC-01")
@pytest.mark.parametrize("code", ["AUTH_FAILED", "VALIDATION_FAILED", "PERMANENT_REMOTE_FAILURE"])
def test_permanent_errors_redact_and_never_retry(
    code: str, pr204_trace: FactRecorder, caplog: pytest.LogCaptureFixture
) -> None:
    repo, provider, service, command, project = harness(
        [ProviderError(ProviderFailureKind.PERMANENT, code + CANARY)]
    )
    admission = service.execute(command)
    provenance = service.get_provenance(None, project, command.execution_id)
    assert len(provider.calls) == 1
    assert repo.executions[command.execution_id].failure_code == "PROVIDER_PERMANENT"
    assert repo.attempts(command.execution_id)[0]["status"] == "PERMANENT_FAILURE"
    assert repo.results == []
    assert (
        CANARY
        not in json.dumps(provenance, default=str)
        + json.dumps(admission, default=str)
        + caplog.text
    )
    pr204_trace.record(
        provider_calls=1, provenance=provenance, admission=admission, canary_absent=True
    )


@pytest.mark.pr204_requirements("PR204-UNKNOWN-01", "PR204-PROV-03")
def test_not_sent_timeout_exhaustion_keeps_all_reasons(pr204_trace: FactRecorder) -> None:
    repo, provider, service, command, project = harness(
        [
            ProviderError(
                ProviderFailureKind.RETRYABLE,
                "PROVIDER_TIMEOUT",
                delivery_certainty=DeliveryCertainty.NOT_SENT,
            )
        ]
        * 3
    )
    service.execute(command)
    attempts = repo.attempts(command.execution_id)
    assert len(provider.calls) == 3
    assert [a["attempt_number"] for a in attempts] == [1, 2, 3]
    assert all(
        a["failure_code"] == "PROVIDER_TIMEOUT"
        and a["status"] == "RETRYABLE_FAILURE"
        and a["delivery_certainty"] == "NOT_SENT"
        for a in attempts
    )
    assert repo.executions[command.execution_id].status.value == "FAILED"
    assert repo.executions[command.execution_id].failure_code == "PROVIDER_RETRY_EXHAUSTED"
    assert repo.results == []
    pr204_trace.record(
        provenance=service.get_provenance(None, project, command.execution_id), provider_calls=3
    )


@pytest.mark.pr204_requirements("PR204-UNKNOWN-02", "PR204-UNKNOWN-04", "PR204-SEC-01")
@pytest.mark.parametrize(
    "failure",
    [
        ProviderError(
            ProviderFailureKind.RETRYABLE,
            "PROVIDER_TIMEOUT",
            delivery_certainty=DeliveryCertainty.MAY_HAVE_BEEN_SENT,
        ),
        ProviderError(ProviderFailureKind.UNCERTAIN, "disconnect"),
        RuntimeError(CANARY),
    ],
    ids=["timeout-after-dispatch", "disconnect", "unexpected-exception"],
)
def test_uncertainty_stops_and_replay_or_late_outcome_is_fenced(
    failure: Exception, pr204_trace: FactRecorder
) -> None:
    repo, provider, service, command, project = harness([failure, success()])
    first = service.execute(command)
    before = service.get_provenance(None, project, command.execution_id)
    assert service.execute(command) == first
    attempt = repo.attempts(command.execution_id)[0]
    with pytest.raises(ResearchBaseError) as caught:
        service._persist_outcome(
            command.execution_id,
            UUID(str(attempt["id"])),
            command.actor_id,
            0,
            1,
            repo.executions[command.execution_id].execution_context,
            success(),
        )
    assert caught.value.code is ErrorCode.INVALID_STATE_TRANSITION
    assert before == service.get_provenance(None, project, command.execution_id)
    assert len(provider.calls) == len(repo.queries) == 1
    assert repo.executions[command.execution_id].status.value == "UNKNOWN"
    assert attempt["status"] == "UNKNOWN" and attempt["delivery_certainty"] == "MAY_HAVE_BEEN_SENT"
    assert repo.results == [] and CANARY not in json.dumps(before, default=str)
    pr204_trace.record(
        provenance=before, provider_calls=1, late_response_error=caught.value.code.value
    )


@pytest.mark.pr204_requirements("PR204-PROV-04")
@pytest.mark.parametrize("kind", ["provider", "version", "query", "oversized", "untyped"])
def test_malformed_batch_rejects_all_hits(kind: str, pr204_trace: FactRecorder) -> None:
    response = success(hits=2)
    if kind != "untyped":
        response = SearchResponse.success(
            provider_id="other" if kind == "provider" else "fake",
            provider_version="2" if kind == "version" else "1",
            normalized_query="other" if kind == "query" else "cortex",
            provider_request_id=None,
            hits=success(hits=21 if kind == "oversized" else 2).hits,
            retrieved_at=PROVIDER_RETRIEVED_AT,
        )
    repo, provider, service, command, project = harness([{} if kind == "untyped" else response])
    service.execute(command)
    assert len(provider.calls) == 1 and len(repo.queries) == 1
    assert repo.results == []
    assert repo.attempts(command.execution_id)[0]["failure_code"] == "PROVIDER_MALFORMED"
    assert repo.executions[command.execution_id].status.value == "FAILED"
    pr204_trace.record(
        rejected_kind=kind,
        provider_calls=1,
        provenance=service.get_provenance(None, project, command.execution_id),
    )


@pytest.mark.pr204_requirements("PR204-PROV-02")
@pytest.mark.parametrize(
    "retry_after,budget,expected_calls,delays",
    [
        (None, 300, 3, [1.0, 2.0]),
        (2, 300, 3, [2.0, 2.0]),
        (2147483647, 300, 1, []),
        (None, 1, 1, []),
    ],
    ids=["exponential-jitter-bound", "retry-after", "retry-after-over-budget", "time-budget"],
)
def test_retry_policy_clock_and_budget(
    retry_after: int | None,
    budget: int,
    expected_calls: int,
    delays: list[float],
    pr204_trace: FactRecorder,
) -> None:
    class ClockRepo(InMemoryLiteratureSearchExecutionRepository):
        now = datetime.now(UTC)

        def database_now(self):
            return self.now

        def seal(self, attempt_id, values):
            super().seal(attempt_id, values)
            self.attempt_rows[attempt_id]["completed_at"] = self.now

    repo = ClockRepo()
    provider = ScriptedProvider(
        [
            ProviderError(
                ProviderFailureKind.RETRYABLE, "PROVIDER_TRANSIENT", retry_after_seconds=retry_after
            )
        ]
        * 3
    )
    sleeps, caps = [], []

    def sleep(seconds):
        assert repo.attempt_rows and all(
            a["status"] != "RESERVED" for a in repo.attempt_rows.values()
        )
        sleeps.append(seconds)
        repo.now += timedelta(seconds=seconds)

    def jitter(lo, hi):
        caps.append((lo, hi))
        return hi

    service = LiteratureSearchExecutionService(
        lambda: InMemoryExecutionUnitOfWork(repo),
        provider,
        clock=repo.database_now,
        sleep=sleep,
        random_uniform=jitter,
        allow_unverified_principal=True,
    )
    actor, project = uuid4(), uuid4()
    created = service.create(
        CreateLiteratureSearchExecution(
            project,
            uuid4(),
            actor,
            "test",
            uuid4(),
            "fake",
            "1",
            ("cortex",),
            execution_budget_seconds=budget,
            timeout_seconds=1,
        )
    )
    execution_id = UUID(created["execution_id"])
    service.execute(ExecuteLiteratureSearchExecution(execution_id, actor, "test", uuid4()))
    assert len(provider.calls) == expected_calls
    assert sleeps == delays
    if retry_after is None and budget == 300:
        assert caps == [(0.0, 1.0), (0.0, 2.0)]
    assert repo.executions[execution_id].failure_code == "PROVIDER_RETRY_EXHAUSTED"
    pr204_trace.record(
        provider_calls=len(provider.calls),
        delays=sleeps,
        jitter_bounds=caps,
        provenance=service.get_provenance(None, project, execution_id),
    )


@pytest.mark.pr204_requirements("PR204-DOM-03")
@pytest.mark.parametrize(
    "field,value",
    [
        ("queries", ()),
        ("queries", ("cortex",) * 33),
        ("queries", (" ",)),
        ("queries", ("x" * 4097,)),
        ("queries", (SearchQueryInput("cortex", query_type="SQL"),)),
        ("queries", (SearchQueryInput("cortex", perspective="x" * 257),)),
        ("max_results", 0),
        ("max_results", 101),
        ("max_provider_attempts", 0),
        ("max_provider_attempts", 4),
        ("timeout_seconds", 0),
        ("timeout_seconds", 31),
        ("execution_budget_seconds", 0),
        ("execution_budget_seconds", 601),
    ],
    ids=[
        "no-queries",
        "too-many-queries",
        "blank-query",
        "long-query",
        "non-TEXT",
        "long-perspective",
        "results-zero",
        "results-over",
        "attempts-zero",
        "attempts-over",
        "timeout-zero",
        "timeout-over",
        "budget-zero",
        "budget-over",
    ],
)
def test_create_rejects_frozen_request_bounds(
    field: str, value: Any, pr204_trace: FactRecorder
) -> None:
    repo = InMemoryLiteratureSearchExecutionRepository()
    provider = FakeSearchCapability()
    service = LiteratureSearchExecutionService(
        lambda: InMemoryExecutionUnitOfWork(repo), provider, allow_unverified_principal=True
    )
    command = CreateLiteratureSearchExecution(
        uuid4(), uuid4(), uuid4(), "test", uuid4(), "fake", "1", ("cortex",)
    )
    with pytest.raises(ResearchBaseError) as caught:
        service.create(replace(command, **{field: value}))
    assert caught.value.code is ErrorCode.VALIDATION_ERROR
    assert (
        repo.executions == {} and repo.receipts == {} and repo.events == [] and provider.calls == []
    )
    pr204_trace.record(
        rejected_field=field,
        error_code=caught.value.code.value,
        execution_count=0,
        receipt_count=0,
        provider_calls=0,
    )


@pytest.mark.pr204_requirements("PR204-DOM-03")
def test_normalized_query_and_pinned_plan_material_reach_provider(
    pr204_trace: FactRecorder,
) -> None:
    class PinnedRepo(InMemoryLiteratureSearchExecutionRepository):
        def plan_invocation(self, project_id, version_id):
            return "a" * 64, {
                "version_id": str(version_id),
                "planned_providers": ["fake"],
                "source_scope": "BIBLIOGRAPHIC",
            }

    repo = PinnedRepo()
    provider = FakeSearchCapability()
    service = LiteratureSearchExecutionService(
        lambda: InMemoryExecutionUnitOfWork(repo), provider, allow_unverified_principal=True
    )
    actor, project, version = uuid4(), uuid4(), uuid4()
    created = service.create(
        CreateLiteratureSearchExecution(
            project,
            version,
            actor,
            "test",
            uuid4(),
            " fake ",
            " 1 ",
            (SearchQueryInput(" Cafe\u0301\tsearch ", "  Pe\u0301rspective  "),),
        )
    )
    execution_id = UUID(created["execution_id"])
    service.execute(ExecuteLiteratureSearchExecution(execution_id, actor, "test", uuid4()))
    request = provider.calls[0]
    assert request.query_text == "Café search" and request.perspective == "  Pérspective  "
    assert request.provider_id == "fake" and request.provider_version == "1"
    assert request.plan_version_id == version and request.plan_content_hash == "a" * 64
    assert request.plan_material == {
        "version_id": str(version),
        "planned_providers": ["fake"],
        "source_scope": "BIBLIOGRAPHIC",
    }
    assert request.provider_request_key == request.attempt_id
    pr204_trace.record(
        plan_version_id=version,
        plan_hash=request.plan_content_hash,
        normalized_query=request.query_text,
        perspective=request.perspective,
        provider_id=request.provider_id,
        provider_version=request.provider_version,
    )


@pytest.mark.pr204_requirements("PR204-DOM-03")
@pytest.mark.parametrize(
    "kind,error",
    [
        ("unplanned", ErrorCode.VALIDATION_ERROR),
        ("scope", ErrorCode.ADAPTER_UNAVAILABLE),
        ("version", ErrorCode.ADAPTER_UNAVAILABLE),
    ],
)
def test_provider_plan_compatibility_rejects_before_admission(
    kind: str, error: ErrorCode, pr204_trace: FactRecorder
) -> None:
    class PlanRepo(InMemoryLiteratureSearchExecutionRepository):
        def plan_invocation(self, project_id, version_id):
            return "a" * 64, {
                "planned_providers": ["other" if kind == "unplanned" else "fake"],
                "source_scope": "UNKNOWN_SCOPE" if kind == "scope" else "BIBLIOGRAPHIC",
            }

    repo = PlanRepo()
    provider = FakeSearchCapability()
    service = LiteratureSearchExecutionService(
        lambda: InMemoryExecutionUnitOfWork(repo), provider, allow_unverified_principal=True
    )
    with pytest.raises(ResearchBaseError) as caught:
        service.create(
            CreateLiteratureSearchExecution(
                uuid4(),
                uuid4(),
                uuid4(),
                "test",
                uuid4(),
                "fake",
                "2" if kind == "version" else "1",
                ("cortex",),
            )
        )
    assert caught.value.code is error
    assert repo.executions == {} and repo.receipts == {} and provider.calls == []
    pr204_trace.record(
        rejected_kind=kind,
        error_code=caught.value.code.value,
        execution_count=0,
        receipt_count=0,
        provider_calls=0,
    )


@pytest.mark.pr204_requirements("PR204-DOM-02")
@pytest.mark.parametrize("kind", ["success", "retryable", "permanent", "unknown", "cancelled"])
def test_attempt_outcome_seals_once_and_internal_reapplication_is_exact(
    kind: str, pr204_trace: FactRecorder
) -> None:
    class OutcomeOnlyService(LiteratureSearchExecutionService):
        def _finalize_execution(self, *args, **kwargs):
            # Observe TX B while RUNNING; the normal TX C is covered by other scenarios.
            pass

    certainty = (
        DeliveryCertainty.MAY_HAVE_BEEN_SENT
        if kind == "unknown"
        else DeliveryCertainty.NOT_SENT
        if kind == "retryable"
        else DeliveryCertainty.RESPONSE_RECEIVED
    )
    response = SearchResponse(
        "fake",
        "1",
        "cortex",
        "remote-safe",
        certainty,
        failure_code={
            "success": None,
            "retryable": "PROVIDER_TIMEOUT",
            "permanent": "PROVIDER_PERMANENT",
            "unknown": None,
            "cancelled": "PROVIDER_CANCELLED",
        }[kind],
        retrieved_at=PROVIDER_RETRIEVED_AT if kind == "success" else None,
    )
    repo = InMemoryLiteratureSearchExecutionRepository()
    provider = ScriptedProvider([response])
    service = OutcomeOnlyService(
        lambda: InMemoryExecutionUnitOfWork(repo),
        provider,
        sleep=lambda _: None,
        allow_unverified_principal=True,
    )
    actor, project = uuid4(), uuid4()
    created = service.create(
        CreateLiteratureSearchExecution(
            project,
            uuid4(),
            actor,
            "test",
            uuid4(),
            "fake",
            "1",
            ("cortex",),
            max_provider_attempts=1,
        )
    )
    execution_id = UUID(created["execution_id"])
    if kind == "cancelled":

        def cancel_at_entry(_request) -> None:
            service.cancel(CancelLiteratureSearchExecution(execution_id, actor, "test", uuid4()))

        provider.observer = cancel_at_entry

        def confirmed_response(request):
            return replace(
                response,
                execution_id=request.execution_id,
                attempt_id=request.attempt_id,
                provider_request_key=request.provider_request_key,
            )

        provider.script.clear()
        provider.script.append(confirmed_response)
    service.execute(ExecuteLiteratureSearchExecution(execution_id, actor, "test", uuid4()))
    before = service.get_provenance(None, project, execution_id)
    attempt = repo.attempts(execution_id)[0]
    assert (
        attempt["status"]
        == {
            "success": "SUCCEEDED",
            "retryable": "RETRYABLE_FAILURE",
            "permanent": "PERMANENT_FAILURE",
            "unknown": "UNKNOWN",
            "cancelled": "CANCELLED",
        }[kind]
    )
    assert attempt["row_version"] == 2
    assert (
        attempt["completed_at"] is not None
        and attempt["invoked_at"] is not None
        and attempt["returned_at"] is not None
    )
    assert attempt["query_record_id"] == repo.queries[0].id
    invoked_at, returned_at = attempt["invoked_at"], attempt["returned_at"]
    assert isinstance(invoked_at, datetime) and isinstance(returned_at, datetime)
    context = repo.executions[execution_id].execution_context
    arguments = (execution_id, UUID(str(attempt["id"])), actor, 0, 1, context)
    confirmation = provider.calls[0] if kind == "cancelled" else None
    if kind == "cancelled":
        response = confirmed_response(confirmation)
    service._persist_outcome(
        *arguments,
        response,
        invoked_at=invoked_at,
        returned_at=returned_at,
        provider_confirmation=confirmation,
    )
    assert service.get_provenance(None, project, execution_id) == before
    with pytest.raises(ResearchBaseError) as caught:
        service._persist_outcome(
            *arguments,
            success(hits=1),
            invoked_at=invoked_at,
            returned_at=returned_at,
        )
    assert caught.value.code is ErrorCode.IMMUTABLE_RECORD
    assert service.get_provenance(None, project, execution_id) == before
    pr204_trace.record(
        kind=kind,
        provenance=before,
        provider_calls=len(provider.calls),
        different_seal_error=caught.value.code.value,
    )


@pytest.mark.pr204_requirements("PR204-SEC-01")
def test_provider_hit_url_is_retained_without_implicit_fetch_or_egress(
    monkeypatch: pytest.MonkeyPatch, pr204_trace: FactRecorder
) -> None:
    network_calls = []

    def reject_network(*args, **kwargs):
        network_calls.append("unexpected network entry")
        raise AssertionError("external egress forbidden in acceptance")

    monkeypatch.setattr(socket.socket, "connect", reject_network)
    monkeypatch.setattr(socket, "create_connection", reject_network)
    monkeypatch.setattr(urllib.request, "urlopen", reject_network)
    url = "https://example.invalid/provider-hit"
    response = SearchResponse.success(
        provider_id="fake",
        provider_version="1",
        normalized_query="cortex",
        provider_request_id=None,
        hits=(SearchHit(None, "Paper", url, None, None),),
        retrieved_at=PROVIDER_RETRIEVED_AT,
    )
    repo, provider, service, command, project = harness([response])
    service.execute(command)
    assert network_calls == [] and len(provider.calls) == 1
    assert repo.results[0]["url"] == url
    assert repo.executions[command.execution_id].status.value == "SUCCEEDED"
    pr204_trace.record(
        network_calls=network_calls,
        retained_url=url,
        provider_calls=1,
        provenance=service.get_provenance(None, project, command.execution_id),
    )
