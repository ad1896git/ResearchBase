from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

import pytest

from researchbase.application.literature_search_execution import (
    CreateLiteratureSearchExecution,
    ExecuteLiteratureSearchExecution,
    LiteratureSearchExecutionService,
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


def test_known_not_sent_failure_creates_a_new_provider_attempt() -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()
    provider = FakeSearchCapability(
        responses=[
            SearchResponse.not_sent(
                provider_id="fake", provider_version="1", normalized_query="cortex"
            ),
            SearchResponse.success(
                provider_id="fake",
                provider_version="1",
                normalized_query="cortex",
                provider_request_id="r2",
                retrieved_at=PROVIDER_RETRIEVED_AT,
            ),
        ]
    )
    service = LiteratureSearchExecutionService(
        lambda: InMemoryExecutionUnitOfWork(repository), provider, allow_unverified_principal=True
    )
    actor, project, plan = uuid4(), uuid4(), uuid4()
    dto = service.create(
        CreateLiteratureSearchExecution(
            project, plan, actor, "test", uuid4(), "fake", "1", ("cortex",)
        )
    )
    execution_id = UUID(dto["execution_id"])
    service.execute(ExecuteLiteratureSearchExecution(execution_id, actor, "test", uuid4()))

    attempts = repository.attempts(execution_id)
    assert len(provider.calls) == 2
    assert [row["attempt_number"] for row in attempts] == [1, 2]
    reservations = [event for event in repository.events if event["kind"] == "ATTEMPT_RESERVED"]
    assert [(event["prior_row_version"], event["new_row_version"]) for event in reservations] == [
        (1, 2),
        (3, 4),
    ]
    assert repository.executions[execution_id].status.value == "SUCCEEDED"


def test_not_sent_response_with_hits_is_malformed_and_never_retried() -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()
    provider = FakeSearchCapability(
        responses=[
            SearchResponse(
                "fake",
                "1",
                "cortex",
                None,
                DeliveryCertainty.NOT_SENT,
                hits=(SearchHit("external-1", "Contradictory result", None, None, None),),
            )
        ]
    )
    service = LiteratureSearchExecutionService(
        lambda: InMemoryExecutionUnitOfWork(repository), provider, allow_unverified_principal=True
    )
    actor, project, plan = uuid4(), uuid4(), uuid4()
    created = service.create(
        CreateLiteratureSearchExecution(
            project, plan, actor, "test", uuid4(), "fake", "1", ("cortex",)
        )
    )
    execution_id = UUID(created["execution_id"])

    service.execute(ExecuteLiteratureSearchExecution(execution_id, actor, "test", uuid4()))

    assert len(provider.calls) == 1
    assert len(repository.attempts(execution_id)) == 1
    assert repository.attempts(execution_id)[0]["status"] == "PERMANENT_FAILURE"
    assert repository.attempts(execution_id)[0]["failure_code"] == "PROVIDER_MALFORMED"
    assert repository.results == []
    assert repository.executions[execution_id].status.value == "FAILED"


def test_permanent_provider_failure_does_not_retry() -> None:
    class Permanent(FakeSearchCapability):
        def search(self, request, context=None):
            self.calls.append(request)
            raise ProviderError(ProviderFailureKind.PERMANENT, "AUTH_FAILED")

    repository = InMemoryLiteratureSearchExecutionRepository()
    provider = Permanent()
    service = LiteratureSearchExecutionService(
        lambda: InMemoryExecutionUnitOfWork(repository), provider, allow_unverified_principal=True
    )
    actor, project, plan = uuid4(), uuid4(), uuid4()
    dto = service.create(
        CreateLiteratureSearchExecution(
            project, plan, actor, "test", uuid4(), "fake", "1", ("cortex",)
        )
    )
    execution_id = UUID(dto["execution_id"])
    service.execute(ExecuteLiteratureSearchExecution(execution_id, actor, "test", uuid4()))
    assert len(provider.calls) == 1
    assert repository.executions[execution_id].status.value == "FAILED"
    assert service.get(None, project, execution_id)["failure_code"] == "PROVIDER_PERMANENT"


def test_provider_retry_exhaustion_preserves_attempt_reasons_and_terminal_reason() -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()
    provider = FakeSearchCapability(
        responses=[
            SearchResponse(
                "fake",
                "1",
                "cortex",
                None,
                DeliveryCertainty.NOT_SENT,
                failure_code="PROVIDER_TRANSIENT",
            ),
            SearchResponse(
                "fake",
                "1",
                "cortex",
                None,
                DeliveryCertainty.NOT_SENT,
                failure_code="PROVIDER_TRANSIENT",
            ),
        ]
    )
    service = LiteratureSearchExecutionService(
        lambda: InMemoryExecutionUnitOfWork(repository),
        provider,
        sleep=lambda _seconds: None,
        allow_unverified_principal=True,
    )
    actor, project, plan = uuid4(), uuid4(), uuid4()
    created = service.create(
        CreateLiteratureSearchExecution(
            project,
            plan,
            actor,
            "test",
            uuid4(),
            "fake",
            "1",
            ("cortex",),
            max_provider_attempts=2,
        )
    )
    execution_id = UUID(created["execution_id"])
    service.execute(ExecuteLiteratureSearchExecution(execution_id, actor, "test", uuid4()))

    assert len(provider.calls) == 2
    assert [row["failure_code"] for row in repository.attempts(execution_id)] == [
        "PROVIDER_TRANSIENT",
        "PROVIDER_TRANSIENT",
    ]
    assert repository.executions[execution_id].failure_code == "PROVIDER_RETRY_EXHAUSTED"


def test_tx_b_retry_reuses_provider_response_without_second_call() -> None:
    class RetryOnceRepository(InMemoryLiteratureSearchExecutionRepository):
        failed = False

        def append_query(self, record):
            if not self.failed:
                self.failed = True
                raise ResearchBaseError(
                    ErrorCode.CONCURRENT_MODIFICATION, "simulated serialization failure"
                )
            super().append_query(record)

    repository = RetryOnceRepository()
    response = SearchResponse.success(
        provider_id="fake",
        provider_version="1",
        normalized_query="cortex",
        provider_request_id="provider-request-1",
        retrieved_at=PROVIDER_RETRIEVED_AT,
    )
    provider = FakeSearchCapability(responses=[response])
    service = LiteratureSearchExecutionService(
        lambda: InMemoryExecutionUnitOfWork(repository), provider, allow_unverified_principal=True
    )
    actor, project, plan = uuid4(), uuid4(), uuid4()
    dto = service.create(
        CreateLiteratureSearchExecution(
            project, plan, actor, "test", uuid4(), "fake", "1", ("cortex",)
        )
    )
    execution_id = UUID(dto["execution_id"])
    service.execute(ExecuteLiteratureSearchExecution(execution_id, actor, "test", uuid4()))
    assert len(provider.calls) == 1
    assert len(repository.attempts(execution_id)) == 1
    assert repository.executions[execution_id].status.value == "SUCCEEDED"


def test_tx_b_lost_commit_ack_recognizes_identical_sealed_outcome() -> None:
    class LostAcknowledgmentService(LiteratureSearchExecutionService):
        lost_ack = False

        def _persist_outcome(self, *args, **kwargs):
            result = super()._persist_outcome(*args, **kwargs)
            if not self.lost_ack:
                self.lost_ack = True
                raise ResearchBaseError(
                    ErrorCode.CONCURRENT_MODIFICATION,
                    "simulated lost commit acknowledgment after durable commit",
                )
            return result

    repository = InMemoryLiteratureSearchExecutionRepository()
    response = SearchResponse.success(
        provider_id="fake",
        provider_version="1",
        normalized_query="cortex",
        provider_request_id="provider-request-1",
        hits=(SearchHit("external-1", "Paper", None, None, None),),
        retrieved_at=PROVIDER_RETRIEVED_AT,
    )
    provider = FakeSearchCapability(responses=[response])
    service = LostAcknowledgmentService(
        lambda: InMemoryExecutionUnitOfWork(repository), provider, allow_unverified_principal=True
    )
    actor, project, plan = uuid4(), uuid4(), uuid4()
    created = service.create(
        CreateLiteratureSearchExecution(
            project, plan, actor, "test", uuid4(), "fake", "1", ("cortex",)
        )
    )
    execution_id = UUID(created["execution_id"])

    service.execute(ExecuteLiteratureSearchExecution(execution_id, actor, "test", uuid4()))

    assert service.lost_ack
    assert len(provider.calls) == 1
    assert len(repository.attempts(execution_id)) == 1
    assert len(repository.queries) == 1
    assert len(repository.results) == 1
    assert [event["kind"] for event in repository.events].count("OUTCOME_RECORDED") == 1
    assert repository.executions[execution_id].status.value == "SUCCEEDED"


def test_lost_reservation_commit_ack_never_dispatches_provider() -> None:
    class LostReservationAcknowledgmentService(LiteratureSearchExecutionService):
        lost_ack = False

        def _execute_admission(self, command):
            result = super()._execute_admission(command)
            if result[2] is not None and not self.lost_ack:
                self.lost_ack = True
                raise ResearchBaseError(
                    ErrorCode.CONCURRENT_MODIFICATION,
                    "simulated lost reservation commit acknowledgment",
                )
            return result

    repository = InMemoryLiteratureSearchExecutionRepository()
    provider = FakeSearchCapability(
        responses=[
            SearchResponse.success(
                provider_id="fake",
                provider_version="1",
                normalized_query="cortex",
                provider_request_id=None,
                retrieved_at=PROVIDER_RETRIEVED_AT,
            )
        ]
    )
    service = LostReservationAcknowledgmentService(
        lambda: InMemoryExecutionUnitOfWork(repository),
        provider,
        allow_unverified_principal=True,
    )
    actor, project, plan = uuid4(), uuid4(), uuid4()
    created = service.create(
        CreateLiteratureSearchExecution(
            project, plan, actor, "test", uuid4(), "fake", "1", ("cortex",)
        )
    )
    execution_id = UUID(created["execution_id"])

    service.execute(ExecuteLiteratureSearchExecution(execution_id, actor, "test", uuid4()))

    assert provider.calls == []
    assert service.lost_ack
    assert len(repository.attempts(execution_id)) == 1
    assert repository.attempts(execution_id)[0]["status"] == "RESERVED"
    assert repository.executions[execution_id].status.value == "RUNNING"


def test_tx_b_lost_commit_ack_rejects_different_sealed_outcome() -> None:
    class ConflictingAcknowledgmentService(LiteratureSearchExecutionService):
        persisted_conflict = False

        def _persist_outcome(
            self,
            execution_id,
            attempt_id,
            actor_id,
            query_index,
            query_count,
            context,
            response,
            principal=None,
            invoked_at=None,
            returned_at=None,
            project_id=None,
            *,
            provider_confirmation=None,
        ):
            if not self.persisted_conflict:
                self.persisted_conflict = True
                conflicting = SearchResponse.success(
                    provider_id=response.provider_id,
                    provider_version=response.provider_version,
                    normalized_query=response.normalized_query,
                    provider_request_id="different-provider-request",
                    hits=(SearchHit("other-result", "Different paper", None, None, None),),
                    retrieved_at=PROVIDER_RETRIEVED_AT,
                )
                super()._persist_outcome(
                    execution_id,
                    attempt_id,
                    actor_id,
                    query_index,
                    query_count,
                    context,
                    conflicting,
                    principal,
                    invoked_at,
                    returned_at,
                    project_id,
                    provider_confirmation=provider_confirmation,
                )
                raise ResearchBaseError(
                    ErrorCode.CONCURRENT_MODIFICATION,
                    "simulated lost commit acknowledgment after conflicting durable outcome",
                )
            return super()._persist_outcome(
                execution_id,
                attempt_id,
                actor_id,
                query_index,
                query_count,
                context,
                response,
                principal,
                invoked_at,
                returned_at,
                project_id,
                provider_confirmation=provider_confirmation,
            )

    repository = InMemoryLiteratureSearchExecutionRepository()
    response = SearchResponse.success(
        provider_id="fake",
        provider_version="1",
        normalized_query="cortex",
        provider_request_id="provider-request-1",
        hits=(SearchHit("external-1", "Paper", None, None, None),),
        retrieved_at=PROVIDER_RETRIEVED_AT,
    )
    provider = FakeSearchCapability(responses=[response])
    service = ConflictingAcknowledgmentService(
        lambda: InMemoryExecutionUnitOfWork(repository), provider, allow_unverified_principal=True
    )
    actor, project, plan = uuid4(), uuid4(), uuid4()
    created = service.create(
        CreateLiteratureSearchExecution(
            project, plan, actor, "test", uuid4(), "fake", "1", ("cortex",)
        )
    )

    with pytest.raises(ResearchBaseError) as caught:
        service.execute(
            ExecuteLiteratureSearchExecution(UUID(created["execution_id"]), actor, "test", uuid4())
        )

    assert caught.value.code is ErrorCode.IMMUTABLE_RECORD
    assert len(provider.calls) == 1
    assert len(repository.attempts(UUID(created["execution_id"]))) == 1
    assert len(repository.queries) == 1
    assert len(repository.results) == 1
    assert repository.results[0]["external_identifier"] == "other-result"


def test_definite_provider_rate_limit_response_is_recorded_then_retried() -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()
    provider = FakeSearchCapability(
        responses=[
            SearchResponse(
                "fake",
                "1",
                "cortex",
                "request-1",
                DeliveryCertainty.RESPONSE_RECEIVED,
                retry_after_seconds=0,
                failure_code="PROVIDER_RATE_LIMIT",
            ),
            SearchResponse.success(
                provider_id="fake",
                provider_version="1",
                normalized_query="cortex",
                provider_request_id="request-2",
                retrieved_at=PROVIDER_RETRIEVED_AT,
            ),
        ]
    )
    service = LiteratureSearchExecutionService(
        lambda: InMemoryExecutionUnitOfWork(repository),
        provider,
        sleep=lambda _seconds: None,
        allow_unverified_principal=True,
    )
    actor, project, plan = uuid4(), uuid4(), uuid4()
    created = service.create(
        CreateLiteratureSearchExecution(
            project, plan, actor, "test", uuid4(), "fake", "1", ("cortex",)
        )
    )
    execution_id = UUID(created["execution_id"])
    service.execute(ExecuteLiteratureSearchExecution(execution_id, actor, "test", uuid4()))

    attempts = repository.attempts(execution_id)
    assert len(provider.calls) == 2
    assert [row["status"] for row in attempts] == ["RETRYABLE_FAILURE", "SUCCEEDED"]


def test_retryable_provider_error_preserves_canonical_reason_and_retry_after() -> None:
    class RateLimited(FakeSearchCapability):
        def search(self, request, context=None):
            self.calls.append(request)
            if len(self.calls) == 1:
                raise ProviderError(
                    ProviderFailureKind.RETRYABLE,
                    "PROVIDER_RATE_LIMIT",
                    delivery_certainty=DeliveryCertainty.RESPONSE_RECEIVED,
                    retry_after_seconds=0,
                )
            return SearchResponse.success(
                provider_id="fake",
                provider_version="1",
                normalized_query="cortex",
                provider_request_id="request-2",
                retrieved_at=PROVIDER_RETRIEVED_AT,
            )

    repository = InMemoryLiteratureSearchExecutionRepository()
    provider = RateLimited()
    service = LiteratureSearchExecutionService(
        lambda: InMemoryExecutionUnitOfWork(repository),
        provider,
        sleep=lambda _seconds: None,
        allow_unverified_principal=True,
    )
    actor, project, plan = uuid4(), uuid4(), uuid4()
    created = service.create(
        CreateLiteratureSearchExecution(
            project, plan, actor, "test", uuid4(), "fake", "1", ("cortex",)
        )
    )
    execution_id = UUID(created["execution_id"])
    service.execute(ExecuteLiteratureSearchExecution(execution_id, actor, "test", uuid4()))

    attempts = repository.attempts(execution_id)
    assert len(provider.calls) == 2
    assert attempts[0]["failure_code"] == "PROVIDER_RATE_LIMIT"
    assert attempts[0]["delivery_certainty"] == DeliveryCertainty.RESPONSE_RECEIVED.value
    assert attempts[0]["retry_after_seconds"] == 0


def test_untyped_provider_response_is_recorded_as_malformed_not_unknown() -> None:
    class MalformedProvider(FakeSearchCapability):
        def search(self, request, context=None):
            self.calls.append(request)
            return object()

    repository = InMemoryLiteratureSearchExecutionRepository()
    provider = MalformedProvider()
    service = LiteratureSearchExecutionService(
        lambda: InMemoryExecutionUnitOfWork(repository),
        cast(FakeSearchCapability, provider),
        allow_unverified_principal=True,
    )
    actor, project, plan = uuid4(), uuid4(), uuid4()
    created = service.create(
        CreateLiteratureSearchExecution(
            project, plan, actor, "test", uuid4(), "fake", "1", ("cortex",)
        )
    )
    execution_id = UUID(created["execution_id"])
    service.execute(ExecuteLiteratureSearchExecution(execution_id, actor, "test", uuid4()))

    assert len(provider.calls) == 1
    assert repository.attempts(execution_id)[0]["status"] == "PERMANENT_FAILURE"
    assert repository.executions[execution_id].status.value == "FAILED"
    assert repository.executions[execution_id].failure_code == "PROVIDER_MALFORMED"


def test_provider_adapter_can_report_known_malformed_response_without_retry() -> None:
    class MalformedResponseProvider(FakeSearchCapability):
        def search(self, request, context=None):
            self.calls.append(request)
            raise ProviderError(
                ProviderFailureKind.PERMANENT,
                "PROVIDER_MALFORMED",
                delivery_certainty=DeliveryCertainty.RESPONSE_RECEIVED,
            )

    repository = InMemoryLiteratureSearchExecutionRepository()
    provider = MalformedResponseProvider()
    service = LiteratureSearchExecutionService(
        lambda: InMemoryExecutionUnitOfWork(repository),
        provider,
        allow_unverified_principal=True,
    )
    actor, project, plan = uuid4(), uuid4(), uuid4()
    created = service.create(
        CreateLiteratureSearchExecution(
            project, plan, actor, "test", uuid4(), "fake", "1", ("cortex",)
        )
    )
    execution_id = UUID(created["execution_id"])

    service.execute(ExecuteLiteratureSearchExecution(execution_id, actor, "test", uuid4()))

    assert len(provider.calls) == 1
    assert repository.attempts(execution_id)[0]["failure_code"] == "PROVIDER_MALFORMED"
    assert repository.executions[execution_id].failure_code == "PROVIDER_MALFORMED"


def test_provider_timeout_uses_remaining_reserved_attempt_deadline() -> None:
    planned_reservation_at = datetime.now(UTC)
    fixed_now = planned_reservation_at + timedelta(seconds=4)

    class DelayedReservationRepository(InMemoryLiteratureSearchExecutionRepository):
        def database_now(self):
            return fixed_now

        def reserve(self, execution_id, query_index, actor_id, reserved_at=None):
            attempt_id = super().reserve(execution_id, query_index, actor_id, reserved_at)
            self.attempt_rows[attempt_id]["reserved_at"] = planned_reservation_at
            self.attempt_rows[attempt_id]["deadline_at"] = planned_reservation_at + timedelta(
                seconds=5
            )
            self.attempt_rows[attempt_id]["recovery_after"] = planned_reservation_at + timedelta(
                seconds=35
            )
            return attempt_id

    class DeadlineProvider(FakeSearchCapability):
        remaining_timeout: float | None = None

        def search(self, request, context=None):
            assert context is not None
            self.remaining_timeout = context.remaining_timeout_seconds
            return super().search(request, context)

    repository = DelayedReservationRepository()
    provider = DeadlineProvider()
    monotonic_ticks = iter((7.0, 7.5, 7.5))
    service = LiteratureSearchExecutionService(
        lambda: InMemoryExecutionUnitOfWork(repository),
        provider,
        clock=lambda: datetime(2099, 1, 1, tzinfo=UTC),
        allow_unverified_principal=True,
        monotonic=lambda: next(monotonic_ticks),
    )
    actor, project, plan = uuid4(), uuid4(), uuid4()
    created = service.create(
        CreateLiteratureSearchExecution(
            project, plan, actor, "test", uuid4(), "fake", "1", ("cortex",)
        )
    )
    service.execute(
        ExecuteLiteratureSearchExecution(
            UUID(created["execution_id"]), actor, "test", uuid4(), project_id=project
        )
    )

    assert provider.remaining_timeout == 0.5


def test_execution_budget_exhaustion_finalizes_without_reserving_next_query() -> None:
    started_at = datetime.now(UTC)

    class ControlledClockRepository(InMemoryLiteratureSearchExecutionRepository):
        now = started_at

        def database_now(self):
            return self.now

    repository = ControlledClockRepository()

    class BudgetExhaustingProvider(FakeSearchCapability):
        def search(self, request, context=None):
            self.calls.append(request)
            started = repository.executions[request.execution_id].started_at
            assert started is not None
            repository.now = started + timedelta(seconds=10)
            return SearchResponse.success(
                provider_id=self.capability_id,
                provider_version=self.version,
                normalized_query=request.query_text,
                provider_request_id="known-response",
                hits=(),
                retrieved_at=PROVIDER_RETRIEVED_AT,
            )

    provider = BudgetExhaustingProvider()
    service = LiteratureSearchExecutionService(
        lambda: InMemoryExecutionUnitOfWork(repository),
        provider,
        allow_unverified_principal=True,
    )
    actor, project, plan = uuid4(), uuid4(), uuid4()
    created = service.create(
        CreateLiteratureSearchExecution(
            project,
            plan,
            actor,
            "test",
            uuid4(),
            "fake",
            "1",
            ("first query", "second query"),
            execution_budget_seconds=10,
        )
    )
    execution_id = UUID(created["execution_id"])

    service.execute(
        ExecuteLiteratureSearchExecution(execution_id, actor, "test", uuid4(), project_id=project)
    )

    assert len(provider.calls) == 1
    assert len(repository.attempts(execution_id)) == 1
    assert len(repository.queries) == 1
    execution = repository.executions[execution_id]
    assert execution.status.value == "FAILED"
    assert execution.failure_code == "PROVIDER_RETRY_EXHAUSTED"


def test_initial_one_second_budget_can_reserve_at_the_same_database_instant_as_start() -> None:
    fixed_now = datetime.now(UTC)

    class FixedDatabaseClockRepository(InMemoryLiteratureSearchExecutionRepository):
        def database_now(self):
            return fixed_now

    repository = FixedDatabaseClockRepository()
    provider = FakeSearchCapability()
    service = LiteratureSearchExecutionService(
        lambda: InMemoryExecutionUnitOfWork(repository),
        provider,
        allow_unverified_principal=True,
    )
    actor, project, plan = uuid4(), uuid4(), uuid4()
    created = service.create(
        CreateLiteratureSearchExecution(
            project,
            plan,
            actor,
            "test",
            uuid4(),
            "fake",
            "1",
            ("query",),
            timeout_seconds=1,
            execution_budget_seconds=1,
        )
    )
    execution_id = UUID(created["execution_id"])

    service.execute(
        ExecuteLiteratureSearchExecution(execution_id, actor, "test", uuid4(), project_id=project)
    )

    attempt = repository.attempts(execution_id)[0]
    execution = repository.executions[execution_id]
    started_at = execution.started_at
    assert started_at is not None
    assert started_at == attempt["reserved_at"]
    assert attempt["deadline_at"] == started_at + timedelta(seconds=1)
    assert len(provider.calls) == 1
    assert execution.status.value == "SUCCEEDED"


def test_new_execute_key_cannot_bypass_persisted_retry_after() -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()
    provider = FakeSearchCapability()

    class ReservationOnlyService(LiteratureSearchExecutionService):
        def _drive(self, execution_id, actor_id, principal=None, reserved=None, project_id=None):
            return None

    service = ReservationOnlyService(
        lambda: InMemoryExecutionUnitOfWork(repository),
        provider,
        allow_unverified_principal=True,
    )
    actor, project, plan = uuid4(), uuid4(), uuid4()
    created = service.create(
        CreateLiteratureSearchExecution(
            project, plan, actor, "test", uuid4(), "fake", "1", ("cortex",)
        )
    )
    execution_id = UUID(created["execution_id"])
    service.execute(ExecuteLiteratureSearchExecution(execution_id, actor, "test", uuid4()))
    attempt = next(iter(repository.attempt_rows.values()))
    attempt.update(
        status="RETRYABLE_FAILURE",
        failure_code="PROVIDER_RATE_LIMIT",
        retry_after_seconds=60,
        completed_at=datetime.now(UTC),
    )

    try:
        service.execute(ExecuteLiteratureSearchExecution(execution_id, actor, "test", uuid4()))
    except ResearchBaseError as exc:
        assert exc.code is ErrorCode.CONCURRENT_MODIFICATION
    else:
        raise AssertionError("a new request key must not bypass Retry-After")

    assert len(provider.calls) == 0
