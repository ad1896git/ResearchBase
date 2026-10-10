from __future__ import annotations

from tests.pr2_04_provider_observations import PROVIDER_RETRIEVED_AT

import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from researchbase.api.routes import LiteratureSearchExecutionIn
from researchbase.application.literature_search_execution import (
    CancelLiteratureSearchExecution,
    CreateLiteratureSearchExecution,
    ExecuteLiteratureSearchExecution,
    LiteratureSearchExecutionService,
    RecoverLiteratureSearchExecution,
    SearchQueryInput,
)
from researchbase.application.literature_search_provider import (
    FakeSearchCapability,
    ProviderError,
    ProviderFailureKind,
    StaticSearchCapabilityRegistry,
)
from researchbase.domain.literature_search_execution import (
    DeliveryCertainty,
    SearchHit,
    SearchResponse,
)
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.in_memory_literature_search_execution import (
    InMemoryExecutionUnitOfWork,
    InMemoryLiteratureSearchExecutionRepository,
    _InMemoryProjectLockRepository,
)


def _service(
    provider: FakeSearchCapability, repository: InMemoryLiteratureSearchExecutionRepository
) -> LiteratureSearchExecutionService:
    return LiteratureSearchExecutionService(
        lambda: InMemoryExecutionUnitOfWork(repository),
        provider,
        lambda: datetime.now(UTC),
        allow_unverified_principal=True,
    )


def test_execution_keeps_provider_outside_database_uow() -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()
    provider = FakeSearchCapability()
    service = _service(provider, repository)
    actor, project, plan = uuid4(), uuid4(), uuid4()
    created = service.create(
        CreateLiteratureSearchExecution(
            project, plan, actor, "test", uuid4(), "fake", "1", ("cortex",)
        )
    )
    service.execute(
        ExecuteLiteratureSearchExecution(UUID(created["execution_id"]), actor, "test", uuid4())
    )

    assert len(provider.calls) == 1
    assert repository.executions[UUID(created["execution_id"])].status.value == "SUCCEEDED"
    provenance = service.get_provenance(None, project, UUID(created["execution_id"]))
    assert provenance["plan"]["plan_version_id"] == str(plan)
    assert [event["kind"] for event in provenance["events"]] == [
        "CREATED",
        "ATTEMPT_RESERVED",
        "OUTCOME_RECORDED",
        "FINISHED",
    ]
    assert {receipt["command_name"] for receipt in provenance["receipts"]} == {
        "CREATE_LITERATURE_SEARCH_EXECUTION",
        "EXECUTE_LITERATURE_SEARCH_EXECUTION",
    }
    attempt = provenance["attempts"][0]
    assert attempt["provider_request_key"] == attempt["id"]
    assert attempt["row_version"] == 2
    assert attempt["returned_at"] is not None
    assert attempt["result_count"] == 0


def test_execution_get_begins_one_read_transaction() -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()
    uows: list[InMemoryExecutionUnitOfWork] = []

    def factory() -> InMemoryExecutionUnitOfWork:
        uow = InMemoryExecutionUnitOfWork(repository)
        uows.append(uow)
        return uow

    service = LiteratureSearchExecutionService(
        factory, FakeSearchCapability(), allow_unverified_principal=True
    )
    actor, project, plan = uuid4(), uuid4(), uuid4()
    created = service.create(
        CreateLiteratureSearchExecution(
            project, plan, actor, "test", uuid4(), "fake", "1", ("cortex",)
        )
    )
    uows.clear()

    service.get(None, project, UUID(created["execution_id"]))

    assert len(uows) == 1
    assert uows[0].trace.count("TX_BEGIN") == 1


def test_in_memory_uow_rolls_back_uncommitted_provenance_mutations() -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()
    service = _service(FakeSearchCapability(), repository)
    actor, project, plan = uuid4(), uuid4(), uuid4()
    created = service.create(
        CreateLiteratureSearchExecution(
            project, plan, actor, "test", uuid4(), "fake", "1", ("cortex",)
        )
    )
    execution_id = UUID(created["execution_id"])
    event_count = len(repository.events)

    try:
        with InMemoryExecutionUnitOfWork(repository):
            repository.events.clear()
            repository.attempt_rows[uuid4()] = {"execution_id": execution_id}
            raise RuntimeError("simulated transaction abort")
    except RuntimeError:
        pass

    assert len(repository.events) == event_count
    assert repository.attempt_rows == {}


def test_provenance_read_recomputes_query_hash() -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()
    service = _service(FakeSearchCapability(), repository)
    actor, project, plan = uuid4(), uuid4(), uuid4()
    created = service.create(
        CreateLiteratureSearchExecution(
            project, plan, actor, "test", uuid4(), "fake", "1", ("cortex",)
        )
    )
    execution_id = UUID(created["execution_id"])
    service.execute(ExecuteLiteratureSearchExecution(execution_id, actor, "test", uuid4()))
    query = repository.queries[0]
    repository.queries[0] = cast(
        Any,
        SimpleNamespace(
            id=query.id,
            execution_id=query.execution_id,
            attempt_id=query.attempt_id,
            ordinal=query.ordinal,
            query_text=query.query_text,
            provider_id=query.provider_id,
            provider_version=query.provider_version,
            executed_at=query.executed_at,
            perspective=query.perspective,
            query_hash="0" * 64,
        ),
    )

    with pytest.raises(ResearchBaseError) as exc:
        service.get_provenance(None, project, execution_id)

    assert exc.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION


def test_provider_observer_sees_no_active_uow() -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()
    active = 0
    trace: list[str] = []

    class TrackingUow(InMemoryExecutionUnitOfWork):
        def __enter__(self):
            nonlocal active
            active += 1
            trace.append("TX_ENTER")
            return super().__enter__()

        def __exit__(self, exc_type, exc_value, traceback):
            nonlocal active
            try:
                trace.append("TX_EXIT")
                return super().__exit__(exc_type, exc_value, traceback)
            finally:
                active -= 1

        def commit(self):
            trace.append("TX_COMMIT")
            return super().commit()

    def observe_provider(_request) -> None:
        trace.append("PROVIDER_ENTER")
        if active:
            raise AssertionError("provider invoked inside UoW")
        trace.append("PROVIDER_EXIT")

    provider = FakeSearchCapability(observer=observe_provider)
    service = LiteratureSearchExecutionService(
        lambda: TrackingUow(repository), provider, allow_unverified_principal=True
    )
    actor, project, plan = uuid4(), uuid4(), uuid4()
    created = service.create(
        CreateLiteratureSearchExecution(
            project, plan, actor, "test", uuid4(), "fake", "1", ("cortex",)
        )
    )
    trace.clear()
    service.execute(
        ExecuteLiteratureSearchExecution(UUID(created["execution_id"]), actor, "test", uuid4())
    )
    assert len(provider.calls) == 1
    assert trace == [
        "TX_ENTER",
        "TX_COMMIT",
        "TX_EXIT",
        "TX_ENTER",
        "TX_COMMIT",
        "TX_EXIT",
        "PROVIDER_ENTER",
        "PROVIDER_EXIT",
        "TX_ENTER",
        "TX_COMMIT",
        "TX_EXIT",
        "TX_ENTER",
        "TX_COMMIT",
        "TX_EXIT",
    ]


def test_authority_loss_during_provider_call_preserves_reservation_but_denies_tx_b() -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()
    now = datetime.now(UTC)
    actor, project, plan = uuid4(), uuid4(), uuid4()
    principal = VerifiedPrincipal(
        actor, "test", "OS_UID", "subject", "credential", now - timedelta(seconds=1)
    )
    authority = {"active": True}

    class PlanRepository(_InMemoryProjectLockRepository):
        def project_active(self, _project_id):
            return True

        def authorize(self, _principal, _project_id):
            if not authority["active"]:
                return []
            return [
                {
                    "actor_type": "HUMAN",
                    "retired_at": None,
                    "membership_status": "ACTIVE",
                    "role": "RESEARCHER",
                    "effective_from": now - timedelta(days=1),
                    "effective_until": None,
                    "binding_status": "ACTIVE",
                    "bound_at": now - timedelta(days=1),
                    "revoked_at": None,
                }
            ]

        def at(self):
            return datetime.now(UTC)

    class AuthorizedUow(InMemoryExecutionUnitOfWork):
        def __init__(self, execution_repository):
            super().__init__(execution_repository)
            self.literature_search_plan = PlanRepository()

    class CredentialVerifier:
        def is_valid(self, principal: VerifiedPrincipal, at: datetime) -> bool:
            del principal, at
            return True

    class RevokingProvider(FakeSearchCapability):
        def search(self, request, context=None):
            self.calls.append(request)
            authority["active"] = False
            return SearchResponse.success(
                provider_id=self.capability_id,
                provider_version=self.version,
                normalized_query=request.query_text,
                provider_request_id=str(request.provider_request_key),
                hits=(SearchHit("external-1", "Result", None, None, None),),
                retrieved_at=PROVIDER_RETRIEVED_AT,
            )

    provider = RevokingProvider()
    service = LiteratureSearchExecutionService(
        lambda: AuthorizedUow(repository),
        provider,
        credential_verifier=CredentialVerifier(),
    )
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
            principal=principal,
        )
    )
    execution_id = UUID(created["execution_id"])

    with pytest.raises(ResearchBaseError) as denied:
        service.execute(
            ExecuteLiteratureSearchExecution(
                execution_id,
                actor,
                "test",
                uuid4(),
                project_id=project,
                principal=principal,
            )
        )

    assert denied.value.code is ErrorCode.FORBIDDEN
    assert len(provider.calls) == 1
    assert repository.executions[execution_id].status.value == "RUNNING"
    assert repository.attempts(execution_id)[0]["status"] == "RESERVED"
    assert repository.queries == []
    assert repository.results == []


def test_create_exact_replay_returns_same_execution() -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()
    provider = FakeSearchCapability()
    service = _service(provider, repository)
    actor, project, plan, request = uuid4(), uuid4(), uuid4(), uuid4()
    command = CreateLiteratureSearchExecution(
        project, plan, actor, "test", request, "fake", "1", ("cortex",)
    )
    assert service.create(command) == service.create(command)
    assert len(repository.executions) == 1


def test_create_same_receipt_key_with_changed_payload_conflicts() -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()
    service = _service(FakeSearchCapability(), repository)
    actor, project, plan, request = uuid4(), uuid4(), uuid4(), uuid4()
    service.create(
        CreateLiteratureSearchExecution(
            project, plan, actor, "test", request, "fake", "1", ("cortex",)
        )
    )

    with pytest.raises(ResearchBaseError) as exc_info:
        service.create(
            CreateLiteratureSearchExecution(
                project, plan, actor, "test", request, "fake", "1", ("hippocampus",)
            )
        )

    assert exc_info.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    assert len(repository.executions) == 1
    assert len(repository.receipts) == 1


def test_create_same_request_in_distinct_project_scope_is_independent() -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()
    service = _service(FakeSearchCapability(), repository)
    actor, request = uuid4(), uuid4()
    first = service.create(
        CreateLiteratureSearchExecution(
            uuid4(), uuid4(), actor, "test", request, "fake", "1", ("cortex",)
        )
    )
    second = service.create(
        CreateLiteratureSearchExecution(
            uuid4(), uuid4(), actor, "test", request, "fake", "1", ("cortex",)
        )
    )

    assert first["execution_id"] != second["execution_id"]
    assert len(repository.executions) == 2
    assert len(repository.receipts) == 2


def test_distinct_receipt_scope_does_not_bypass_project_execution_uniqueness() -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()
    service = _service(FakeSearchCapability(), repository)
    project, plan, request = uuid4(), uuid4(), uuid4()
    service.create(
        CreateLiteratureSearchExecution(
            project, plan, uuid4(), "deployment-a", request, "fake", "1", ("cortex",)
        )
    )

    with pytest.raises(ResearchBaseError) as exc_info:
        service.create(
            CreateLiteratureSearchExecution(
                project, plan, uuid4(), "deployment-b", request, "fake", "1", ("cortex",)
            )
        )

    assert exc_info.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    assert len(repository.executions) == 1
    assert len(repository.receipts) == 1


def test_create_rejects_query_longer_than_frozen_contract_before_admission() -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()
    service = _service(FakeSearchCapability(), repository)
    with pytest.raises(ResearchBaseError) as exc_info:
        service.create(
            CreateLiteratureSearchExecution(
                uuid4(), uuid4(), uuid4(), "test", uuid4(), "fake", "1", ("q" * 4097,)
            )
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert repository.executions == {}


def test_create_normalizes_provider_identifiers_before_plan_matching_and_receipt_hashing() -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()
    provider = FakeSearchCapability()
    service = _service(provider, repository)
    actor, project, plan, request_id = (uuid4() for _ in range(4))

    created = service.create(
        CreateLiteratureSearchExecution(
            project,
            plan,
            actor,
            "test",
            request_id,
            " fake ",
            "1 ",
            ("cortex",),
        )
    )

    execution = repository.executions[UUID(created["execution_id"])]
    receipt = next(
        value
        for key, value in repository.receipts.items()
        if key[3] == "CREATE_LITERATURE_SEARCH_EXECUTION" and key[-1] == request_id
    )
    assert execution.execution_context["provider_id"] == "fake"
    assert execution.execution_context["provider_version"] == "1"
    payload = cast(dict[str, object], receipt["payload"])
    assert payload["provider_id"] == "fake"
    assert payload["provider_version"] == "1"


def test_create_maps_malformed_query_input_to_validation_error() -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()
    service = _service(FakeSearchCapability(), repository)
    malformed = SearchQueryInput("cortex")
    object.__setattr__(malformed, "query_text", 1)

    with pytest.raises(ResearchBaseError) as exc_info:
        service.create(
            CreateLiteratureSearchExecution(
                uuid4(), uuid4(), uuid4(), "test", uuid4(), "fake", "1", (malformed,)
            )
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert repository.executions == {}


def test_create_receipt_replay_does_not_revalidate_superseded_plan() -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()
    service = _service(FakeSearchCapability(), repository)
    actor, project, plan, request = uuid4(), uuid4(), uuid4(), uuid4()
    command = CreateLiteratureSearchExecution(
        project, plan, actor, "test", request, "fake", "1", ("cortex",)
    )
    first = service.create(command)

    def superseded_plan(*_args, **_kwargs):
        raise ResearchBaseError(ErrorCode.SEARCH_PLAN_NOT_FROZEN, "plan was superseded")

    repository.validate_plan_version = superseded_plan  # type: ignore[method-assign]
    assert service.create(command) == first


def test_create_receipt_hash_payload_excludes_request_id() -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()
    service = _service(FakeSearchCapability(), repository)
    actor, project, plan, request = uuid4(), uuid4(), uuid4(), uuid4()
    service.create(
        CreateLiteratureSearchExecution(
            project, plan, actor, "test", request, "fake", "1", ("cortex",)
        )
    )
    receipt = next(iter(repository.receipts.values()))
    payload = receipt["payload"]
    assert isinstance(payload, dict)
    assert "idempotency_key" not in payload
    execution = next(iter(repository.executions.values()))
    assert execution.idempotency_key == request
    assert set(execution.execution_context) == {
        "schema_version",
        "provider_id",
        "provider_version",
        "queries",
        "max_results",
        "max_provider_attempts",
        "timeout_seconds",
        "execution_budget_seconds",
    }


def test_create_receipt_replay_does_not_require_live_provider_adapter() -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()
    provider = FakeSearchCapability()
    service = _service(provider, repository)
    command = CreateLiteratureSearchExecution(
        uuid4(), uuid4(), uuid4(), "test", uuid4(), "fake", "1", ("cortex",)
    )
    first = service.create(command)
    provider.capability_id = "adapter-removed"
    assert service.create(command) == first


def test_execution_list_uses_project_scoped_created_at_id_cursor() -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()
    service = _service(FakeSearchCapability(), repository)
    actor, project, plan = uuid4(), uuid4(), uuid4()
    execution_ids = []
    for index in range(3):
        created = service.create(
            CreateLiteratureSearchExecution(
                project,
                plan,
                actor,
                "test",
                uuid4(),
                "fake",
                "1",
                (f"query {index}",),
            )
        )
        execution_ids.append(UUID(created["execution_id"]))

    first_page = service.list(None, project, limit=2)
    second_page = service.list(None, project, limit=2, after=UUID(first_page[-1]["execution_id"]))

    assert [row["execution_id"] for row in first_page + second_page] == [
        str(value) for value in execution_ids
    ]
    with pytest.raises(ResearchBaseError) as exc_info:
        service.list(None, uuid4(), limit=2, after=execution_ids[0])
    assert exc_info.value.code is ErrorCode.NOT_FOUND


def test_create_rejects_provider_absent_from_exact_frozen_plan() -> None:
    class PlanWithoutProvider(InMemoryLiteratureSearchExecutionRepository):
        def plan_invocation(self, project_id, version_id):
            digest, material = super().plan_invocation(project_id, version_id)
            cast(dict[str, Any], material)["planned_providers"] = []
            return digest, material

    repository = PlanWithoutProvider()
    service = _service(FakeSearchCapability(), repository)

    with pytest.raises(ResearchBaseError) as exc_info:
        service.create(
            CreateLiteratureSearchExecution(
                uuid4(), uuid4(), uuid4(), "test", uuid4(), "fake", "1", ("cortex",)
            )
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert repository.executions == {}


def test_create_resolves_provider_registry_by_exact_pinned_version() -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()
    provider_v1 = FakeSearchCapability(capability_id="fake", version="1")
    provider_v2 = FakeSearchCapability(capability_id="fake", version="2")
    service = LiteratureSearchExecutionService(
        lambda: InMemoryExecutionUnitOfWork(repository),
        StaticSearchCapabilityRegistry((provider_v1, provider_v2)),
        allow_unverified_principal=True,
    )

    accepted = service.create(
        CreateLiteratureSearchExecution(
            uuid4(), uuid4(), uuid4(), "test", uuid4(), "fake", "2", ("cortex",)
        )
    )

    assert accepted["command_name"] == "CREATE_LITERATURE_SEARCH_EXECUTION"
    assert (
        repository.executions[UUID(accepted["execution_id"])].execution_context["provider_version"]
        == "2"
    )


def test_each_mutation_phase_revalidates_exact_plan_material() -> None:
    class CountingPlanRepository(InMemoryLiteratureSearchExecutionRepository):
        plan_validation_count = 0

        def plan_invocation(self, project_id, version_id):
            self.plan_validation_count += 1
            return super().plan_invocation(project_id, version_id)

    repository = CountingPlanRepository()
    service = _service(FakeSearchCapability(), repository)
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

    # create, first start, reservation, TX B, and TX C bind to the same plan hash.
    assert repository.plan_validation_count >= 5


def test_cancellation_recovery_does_not_call_provider() -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()
    provider = FakeSearchCapability()
    service = _service(provider, repository)
    actor, project, plan = uuid4(), uuid4(), uuid4()
    created = service.create(
        CreateLiteratureSearchExecution(
            project, plan, actor, "test", uuid4(), "fake", "1", ("cortex",)
        )
    )
    execution_id = UUID(created["execution_id"])
    service.cancel(CancelLiteratureSearchExecution(execution_id, actor, "test", uuid4()))
    service.recover(RecoverLiteratureSearchExecution(execution_id, actor, "test", uuid4()))

    assert provider.calls == []
    assert repository.executions[execution_id].status.value == "CANCELLED"
    assert "cancellation_requested" not in repository.executions[execution_id].execution_context


def test_uncertain_response_is_terminal_without_redispatch() -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()
    provider = FakeSearchCapability(
        responses=[
            SearchResponse.uncertain(
                provider_id="fake",
                provider_version="1",
                normalized_query="cortex",
                provider_request_id=None,
            )
        ]
    )
    service = _service(provider, repository)
    actor, project, plan = uuid4(), uuid4(), uuid4()
    created = service.create(
        CreateLiteratureSearchExecution(
            project, plan, actor, "test", uuid4(), "fake", "1", ("cortex",)
        )
    )
    execution_id = UUID(created["execution_id"])
    service.execute(ExecuteLiteratureSearchExecution(execution_id, actor, "test", uuid4()))
    service.recover(RecoverLiteratureSearchExecution(execution_id, actor, "test", uuid4()))

    assert len(provider.calls) == 1
    assert repository.executions[execution_id].status.value == "UNKNOWN"


def test_late_provider_response_cannot_append_after_unknown_is_terminal() -> None:
    class UncertainProvider(FakeSearchCapability):
        def search(self, request, context=None):
            self.calls.append(request)
            raise ProviderError(
                ProviderFailureKind.UNCERTAIN,
                "connection-lost-after-dispatch",
                delivery_certainty=DeliveryCertainty.MAY_HAVE_BEEN_SENT,
            )

    repository = InMemoryLiteratureSearchExecutionRepository()
    provider = UncertainProvider()
    service = _service(provider, repository)
    actor, project, plan = uuid4(), uuid4(), uuid4()
    created = service.create(
        CreateLiteratureSearchExecution(
            project, plan, actor, "test", uuid4(), "fake", "1", ("cortex",)
        )
    )
    execution_id = UUID(created["execution_id"])
    service.execute(ExecuteLiteratureSearchExecution(execution_id, actor, "test", uuid4()))
    attempt = repository.attempts(execution_id)[0]
    execution = repository.get(execution_id)
    assert execution is not None
    context = execution.execution_context
    counts_before = (len(repository.queries), len(repository.results), len(repository.events))

    with pytest.raises(ResearchBaseError) as late_write:
        service._persist_outcome(
            execution_id,
            UUID(str(attempt["id"])),
            actor,
            0,
            1,
            context,
            SearchResponse.success(
                provider_id="fake",
                provider_version="1",
                normalized_query="cortex",
                provider_request_id="late-response",
                hits=(SearchHit("external-1", "Late result", None, None, None),),
                retrieved_at=PROVIDER_RETRIEVED_AT,
            ),
            invoked_at=datetime.now(UTC),
            returned_at=datetime.now(UTC),
            project_id=project,
        )

    assert late_write.value.code is ErrorCode.INVALID_STATE_TRANSITION
    assert provider.calls and repository.executions[execution_id].status.value == "UNKNOWN"
    assert (len(repository.queries), len(repository.results), len(repository.events)) == (
        counts_before
    )


def test_untrusted_provider_exception_text_is_not_persisted_in_provenance() -> None:
    secret = "PR204_SUPER_SECRET_DO_NOT_LEAK"

    class LeakingProvider(FakeSearchCapability):
        def search(self, request, context=None):
            self.calls.append(request)
            raise RuntimeError(secret)

    repository = InMemoryLiteratureSearchExecutionRepository()
    service = _service(LeakingProvider(), repository)
    actor, project, plan = uuid4(), uuid4(), uuid4()
    created = service.create(
        CreateLiteratureSearchExecution(
            project, plan, actor, "test", uuid4(), "fake", "1", ("cortex",)
        )
    )
    execution_id = UUID(created["execution_id"])
    service.execute(ExecuteLiteratureSearchExecution(execution_id, actor, "test", uuid4()))

    serialized = json.dumps(service.get_provenance(None, project, execution_id), default=str)

    assert secret not in serialized
    assert repository.executions[execution_id].status.value == "UNKNOWN"
    assert repository.attempts(execution_id)[0]["failure_code"] == "PROVIDER_OUTCOME_UNKNOWN"
    attempt_id = next(iter(repository.attempt_rows))
    try:
        repository.seal(attempt_id, {"status": "SUCCEEDED"})
    except ResearchBaseError as exc:
        assert exc.code is ErrorCode.IMMUTABLE_RECORD
    else:
        raise AssertionError("late attempt outcome must fail closed")


def test_execute_exact_replay_does_not_call_provider_again() -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()
    provider = FakeSearchCapability()
    service = _service(provider, repository)
    actor, project, plan, request = uuid4(), uuid4(), uuid4(), uuid4()
    created = service.create(
        CreateLiteratureSearchExecution(
            project, plan, actor, "test", uuid4(), "fake", "1", ("cortex",)
        )
    )
    command = ExecuteLiteratureSearchExecution(
        UUID(created["execution_id"]), actor, "test", request
    )
    first = service.execute(command)
    second = service.execute(command)
    assert second == first
    assert len(provider.calls) == 1
    receipt = next(
        value
        for key, value in repository.receipts.items()
        if key[3] == "EXECUTE_LITERATURE_SEARCH_EXECUTION"
    )
    assert receipt["payload"] == {
        "project_id": str(project),
        "execution_id": created["execution_id"],
    }


def test_execute_admission_locks_project_and_command_before_execution_read() -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()
    service = _service(FakeSearchCapability(), repository)
    actor, project, plan = uuid4(), uuid4(), uuid4()
    created = service.create(
        CreateLiteratureSearchExecution(
            project, plan, actor, "test", uuid4(), "fake", "1", ("cortex",)
        )
    )
    trace: list[str] = []
    original_get = repository.get
    original_get_for_update = repository.get_for_update
    repository.get = lambda execution_id: (trace.append("read"), original_get(execution_id))[1]
    repository.get_for_update = lambda execution_id: (
        trace.append("read_for_update"),
        original_get_for_update(execution_id),
    )[1]
    plan_repository = cast(Any, _InMemoryProjectLockRepository())
    original_lock_project = plan_repository.lock_project
    original_lock_command = plan_repository.lock_literature_search_execution_command
    plan_repository.lock_project = lambda project_id: (
        trace.append("project_lock"),
        original_lock_project(project_id),
    )[1]
    plan_repository.lock_literature_search_execution_command = lambda *args: (
        trace.append("command_lock"),
        original_lock_command(*args),
    )[1]

    class TrackingUow(InMemoryExecutionUnitOfWork):
        def __init__(self, repository):
            super().__init__(repository)
            self.literature_search_plan = plan_repository

    service._uow_factory = lambda: TrackingUow(repository)
    service._execute_admission(
        ExecuteLiteratureSearchExecution(
            UUID(created["execution_id"]), actor, "test", uuid4(), project_id=project
        )
    )

    assert trace[:3] == ["project_lock", "command_lock", "read"]


def test_cancel_runs_c1_and_c2_in_distinct_transactions() -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()
    provider = FakeSearchCapability()
    service = _service(provider, repository)
    actor, project, plan = uuid4(), uuid4(), uuid4()
    created = service.create(
        CreateLiteratureSearchExecution(
            project, plan, actor, "test", uuid4(), "fake", "1", ("cortex",)
        )
    )
    execution_id = UUID(created["execution_id"])
    service.cancel(CancelLiteratureSearchExecution(execution_id, actor, "test", uuid4()))
    execution = repository.executions[execution_id]
    assert execution.status.value == "CANCELLED"
    assert execution.row_version == 3
    assert [event["kind"] for event in repository.events] == [
        "CREATED",
        "CANCEL_REQUESTED",
        "FINISHED",
    ]
    assert provider.calls == []


def test_recovery_completes_crash_after_cancel_admission_once() -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()
    provider = FakeSearchCapability()

    def crash() -> None:
        raise RuntimeError("simulated crash after C1")

    service = LiteratureSearchExecutionService(
        lambda: InMemoryExecutionUnitOfWork(repository),
        provider,
        after_cancel_admission=crash,
        allow_unverified_principal=True,
    )
    actor, project, plan = uuid4(), uuid4(), uuid4()
    created = service.create(
        CreateLiteratureSearchExecution(
            project, plan, actor, "test", uuid4(), "fake", "1", ("cortex",)
        )
    )
    execution_id = UUID(created["execution_id"])
    try:
        service.cancel(CancelLiteratureSearchExecution(execution_id, actor, "test", uuid4()))
    except RuntimeError:
        pass
    else:
        raise AssertionError("fault injection must interrupt C2")
    interrupted = repository.executions[execution_id]
    assert interrupted.status.value == "PLANNED"
    assert interrupted.cancellation_requested
    assert interrupted.row_version == 2
    # Reuse the original cancellation key to prove replay does not perform C2.
    original_request_id = next(
        key[-1]
        for key, receipt in repository.receipts.items()
        if key[3] == "CANCEL_LITERATURE_SEARCH_EXECUTION"
        and isinstance((dto := receipt.get("dto")), dict)
        and dto.get("execution_id") == str(execution_id)
    )
    replay = CancelLiteratureSearchExecution(execution_id, actor, "test", original_request_id)
    service.cancel(replay)
    assert repository.executions[execution_id].status.value == "PLANNED"
    assert repository.executions[execution_id].row_version == 2
    recovery = RecoverLiteratureSearchExecution(execution_id, actor, "test", uuid4())
    service.recover(recovery)
    service.recover(recovery)
    assert repository.executions[execution_id].status.value == "CANCELLED"


def test_cancellation_committed_between_tx_b_and_tx_c_wins_terminal_precedence() -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()
    provider = FakeSearchCapability(
        responses=[
            SearchResponse.success(
                provider_id="fake",
                provider_version="1",
                normalized_query="cortex",
                provider_request_id="returned-before-cancel",
                hits=(SearchHit("record-1", "Observed result", None, None, None),),
                retrieved_at=PROVIDER_RETRIEVED_AT,
            )
        ]
    )

    class CancelBetweenTxBAndTxCService(LiteratureSearchExecutionService):
        cancellation_admitted = False

        def _finalize_execution(
            self, execution_id, actor_id, status, principal=None, project_id=None
        ):
            if status.value == "SUCCEEDED" and not self.cancellation_admitted:
                self.cancellation_admitted = True
                self._cancel_or_recover(
                    execution_id,
                    actor_id,
                    "test",
                    uuid4(),
                    False,
                    project_id,
                    principal,
                )
            return super()._finalize_execution(
                execution_id, actor_id, status, principal, project_id
            )

    service = CancelBetweenTxBAndTxCService(
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

    service.execute(
        ExecuteLiteratureSearchExecution(execution_id, actor, "test", uuid4(), project_id=project)
    )

    execution = repository.executions[execution_id]
    assert execution.status.value == "CANCELLED"
    assert execution.failure_code == "CANCELLED"
    assert len(repository.results) == 1
    assert sum(event["kind"] == "FINISHED" for event in repository.events) == 1
    assert execution.row_version == 5
    assert [event["kind"] for event in repository.events].count("FINISHED") == 1
    assert len(provider.calls) == 1


def test_concurrent_recovery_stale_cas_rereads_terminal_cancellation() -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()
    provider = FakeSearchCapability()

    def crash_after_c1() -> None:
        raise RuntimeError("simulated crash after C1")

    service = LiteratureSearchExecutionService(
        lambda: InMemoryExecutionUnitOfWork(repository),
        provider,
        after_cancel_admission=crash_after_c1,
        allow_unverified_principal=True,
    )
    actor, project, plan = uuid4(), uuid4(), uuid4()
    created = service.create(
        CreateLiteratureSearchExecution(
            project, plan, actor, "test", uuid4(), "fake", "1", ("cortex",)
        )
    )
    execution_id = UUID(created["execution_id"])
    with pytest.raises(RuntimeError, match="after C1"):
        service.cancel(CancelLiteratureSearchExecution(execution_id, actor, "test", uuid4()))

    recovery_a = repository.get_for_update(execution_id)
    recovery_b = repository.get_for_update(execution_id)
    assert recovery_a is not None and recovery_b is not None
    expected_version = recovery_a.row_version
    recovery_a.cancel(repository.database_now())
    repository.save(recovery_a, expected_version)
    repository.append_event(recovery_a, "FINISHED", actor)

    recovery_b.cancel(repository.database_now())
    with pytest.raises(ResearchBaseError) as exc_info:
        repository.save(recovery_b, expected_version)
    assert exc_info.value.code is ErrorCode.CONCURRENT_MODIFICATION

    service._after_cancel_admission = None
    replay = service.recover(
        RecoverLiteratureSearchExecution(execution_id, actor, "test", uuid4(), project_id=project)
    )
    assert replay["execution_id"] == str(execution_id)
    assert repository.executions[execution_id].status.value == "CANCELLED"
    assert repository.executions[execution_id].row_version == 3
    assert [event["kind"] for event in repository.events].count("FINISHED") == 1
    assert provider.calls == []


def test_new_execute_key_cannot_bypass_committed_prestart_cancel_intent() -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()
    provider = FakeSearchCapability()

    def crash_after_c1() -> None:
        raise RuntimeError("simulated crash after C1")

    service = LiteratureSearchExecutionService(
        lambda: InMemoryExecutionUnitOfWork(repository),
        provider,
        after_cancel_admission=crash_after_c1,
        allow_unverified_principal=True,
    )
    actor, project, plan = uuid4(), uuid4(), uuid4()
    created = service.create(
        CreateLiteratureSearchExecution(
            project, plan, actor, "test", uuid4(), "fake", "1", ("cortex",)
        )
    )
    execution_id = UUID(created["execution_id"])
    with pytest.raises(RuntimeError, match="after C1"):
        service.cancel(CancelLiteratureSearchExecution(execution_id, actor, "test", uuid4()))

    with pytest.raises(ResearchBaseError) as exc_info:
        service.execute(ExecuteLiteratureSearchExecution(execution_id, actor, "test", uuid4()))

    assert exc_info.value.code is ErrorCode.INVALID_STATE_TRANSITION
    assert repository.executions[execution_id].status.value == "PLANNED"
    assert repository.executions[execution_id].cancellation_requested
    assert repository.executions[execution_id].row_version == 2
    assert repository.attempt_rows == {}
    assert provider.calls == []


def test_terminal_recover_receipt_does_not_mutate_terminal_execution() -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()
    provider = FakeSearchCapability()
    service = _service(provider, repository)
    actor, project, plan = uuid4(), uuid4(), uuid4()
    created = service.create(
        CreateLiteratureSearchExecution(
            project, plan, actor, "test", uuid4(), "fake", "1", ("cortex",)
        )
    )
    execution_id = UUID(created["execution_id"])
    service.execute(ExecuteLiteratureSearchExecution(execution_id, actor, "test", uuid4()))
    before = repository.executions[execution_id]
    events = list(repository.events)
    attempts = list(repository.attempt_rows)
    service.recover(RecoverLiteratureSearchExecution(execution_id, actor, "test", uuid4()))
    after = repository.executions[execution_id]
    assert after.row_version == before.row_version
    assert after.status == before.status
    assert repository.events == events
    assert list(repository.attempt_rows) == attempts
    assert len(provider.calls) == 1


def test_read_authorization_accepts_viewer_but_write_authorization_does_not() -> None:
    actor_id, project_id = uuid4(), uuid4()
    now = datetime.now(UTC)
    principal = VerifiedPrincipal(
        actor_id,
        "test",
        "OS_UID",
        "subject",
        "credential",
        now,
    )

    class AuthorizationRepository:
        calls = []

        def lock_project(self, _project_id):
            self.calls.append("project")

        def lock_literature_search_execution_command(self, *_args):
            self.calls.append("command")

        def authorize(self, _principal, _project_id):
            self.calls.append("authorize")
            return [
                {
                    "actor_type": "HUMAN",
                    "retired_at": None,
                    "membership_status": "ACTIVE",
                    "role": "VIEWER",
                    "effective_from": now,
                    "effective_until": None,
                    "binding_status": "ACTIVE",
                    "bound_at": now,
                    "revoked_at": None,
                }
            ]

        def at(self):
            self.calls.append("clock")
            return now

    class AuthorizationUow:
        literature_search_plan = AuthorizationRepository()

    class CredentialVerifier:
        def is_valid(self, principal, at):
            return True

    service = LiteratureSearchExecutionService(
        lambda: InMemoryExecutionUnitOfWork(InMemoryLiteratureSearchExecutionRepository()),
        FakeSearchCapability(),
        credential_verifier=CredentialVerifier(),
    )

    repo = AuthorizationUow.literature_search_plan
    command_key = ("test", actor_id, project_id, "READ", uuid4())
    service._authorize(
        AuthorizationUow(), principal, project_id, require_writer=False, command_key=command_key
    )
    assert repo.calls == ["project", "command", "authorize", "clock"]
    try:
        service._authorize(AuthorizationUow(), principal, project_id)
    except ResearchBaseError as exc:
        assert exc.code is ErrorCode.FORBIDDEN
    else:
        raise AssertionError("VIEWER must not receive mutation authority")


def test_execution_authorization_rejects_inactive_project() -> None:
    actor_id, project_id = uuid4(), uuid4()
    now = datetime.now(UTC)
    principal = VerifiedPrincipal(actor_id, "test", "OS_UID", "subject", "credential", now)

    class AuthorizationRepository:
        def lock_project(self, _project_id):
            return None

        def project_active(self, _project_id):
            return False

        def authorize(self, _principal, _project_id):
            return [
                {
                    "actor_type": "HUMAN",
                    "retired_at": None,
                    "membership_status": "ACTIVE",
                    "role": "OWNER",
                    "effective_from": now,
                    "effective_until": None,
                    "binding_status": "ACTIVE",
                    "bound_at": now,
                    "revoked_at": None,
                }
            ]

        def at(self):
            return now

    class AuthorizationUow:
        literature_search_plan = AuthorizationRepository()

    class CredentialVerifier:
        def is_valid(self, principal: VerifiedPrincipal, at: datetime) -> bool:
            return True

    service = LiteratureSearchExecutionService(
        lambda: InMemoryExecutionUnitOfWork(InMemoryLiteratureSearchExecutionRepository()),
        FakeSearchCapability(),
        credential_verifier=CredentialVerifier(),
    )

    with pytest.raises(ResearchBaseError) as exc:
        service._authorize(AuthorizationUow(), principal, project_id)

    assert exc.value.code is ErrorCode.FORBIDDEN


def test_cancellation_during_first_query_prevents_next_query_dispatch() -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()
    provider = FakeSearchCapability()
    service = _service(provider, repository)
    actor, project, plan = uuid4(), uuid4(), uuid4()
    created = service.create(
        CreateLiteratureSearchExecution(
            project, plan, actor, "test", uuid4(), "fake", "1", ("first", "second")
        )
    )
    execution_id = UUID(created["execution_id"])
    cancelled = False

    def request_cancellation(_request):
        nonlocal cancelled
        if not cancelled:
            cancelled = True
            service.cancel(CancelLiteratureSearchExecution(execution_id, actor, "test", uuid4()))

    provider.observer = request_cancellation
    service.execute(ExecuteLiteratureSearchExecution(execution_id, actor, "test", uuid4()))

    assert len(provider.calls) == 1
    assert repository.executions[execution_id].status.value == "CANCELLED"


def test_confirmed_provider_cancellation_seals_cancelled_attempt() -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()

    class CancellingProvider(FakeSearchCapability):
        cancel_service: LiteratureSearchExecutionService | None = None
        command: CancelLiteratureSearchExecution | None = None

        def search(self, request, context=None):
            self.calls.append(request)
            assert self.cancel_service is not None
            assert self.command is not None
            self.cancel_service.cancel(self.command)
            raise ProviderError(
                ProviderFailureKind.CANCELLED,
                "provider-confirmed-cancel",
                delivery_certainty=DeliveryCertainty.NOT_SENT,
            )

    provider = CancellingProvider()
    service = _service(provider, repository)
    provider.cancel_service = service
    actor, project, plan = uuid4(), uuid4(), uuid4()
    created = service.create(
        CreateLiteratureSearchExecution(
            project, plan, actor, "test", uuid4(), "fake", "1", ("cortex",)
        )
    )
    execution_id = UUID(created["execution_id"])
    provider.command = CancelLiteratureSearchExecution(
        execution_id, actor, "test", uuid4(), project_id=project
    )

    service.execute(
        ExecuteLiteratureSearchExecution(execution_id, actor, "test", uuid4(), project_id=project)
    )

    attempt = repository.attempts(execution_id)[0]
    assert attempt["status"] == "CANCELLED"
    assert attempt["failure_code"] == "CANCELLED"
    assert repository.executions[execution_id].status.value == "CANCELLED"
    assert repository.results == []


def test_provider_cancellation_without_durable_cancel_intent_fails_closed() -> None:
    class UnrequestedCancellationProvider(FakeSearchCapability):
        def search(self, request, context=None):
            self.calls.append(request)
            raise ProviderError(
                ProviderFailureKind.CANCELLED,
                "provider-cancelled-without-request",
                delivery_certainty=DeliveryCertainty.NOT_SENT,
            )

    repository = InMemoryLiteratureSearchExecutionRepository()
    provider = UnrequestedCancellationProvider()
    service = _service(provider, repository)
    actor, project, plan = uuid4(), uuid4(), uuid4()
    created = service.create(
        CreateLiteratureSearchExecution(
            project, plan, actor, "test", uuid4(), "fake", "1", ("cortex",)
        )
    )
    execution_id = UUID(created["execution_id"])

    service.execute(
        ExecuteLiteratureSearchExecution(execution_id, actor, "test", uuid4(), project_id=project)
    )

    attempt = repository.attempts(execution_id)[0]
    execution = repository.executions[execution_id]
    assert attempt["status"] == "PERMANENT_FAILURE"
    assert attempt["failure_code"] == "PROVIDER_MALFORMED"
    assert execution.status.value == "FAILED"
    assert execution.failure_code == "PROVIDER_MALFORMED"
    assert not execution.cancellation_requested


def test_cancellation_committed_between_queries_prevents_next_reservation() -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()
    provider = FakeSearchCapability()
    actor, project, plan = uuid4(), uuid4(), uuid4()

    class CancelAfterFirstTxBService(LiteratureSearchExecutionService):
        cancellation_sent = False

        def _persist_outcome(self, *args, **kwargs):
            outcome = super()._persist_outcome(*args, **kwargs)
            query_index = args[3]
            if query_index == 0 and not self.cancellation_sent:
                self.cancellation_sent = True
                execution_id = args[0]
                self.cancel(
                    CancelLiteratureSearchExecution(
                        execution_id,
                        actor,
                        "test",
                        uuid4(),
                        project_id=project,
                    )
                )
            return outcome

    service = CancelAfterFirstTxBService(
        lambda: InMemoryExecutionUnitOfWork(repository),
        provider,
        allow_unverified_principal=True,
    )
    created = service.create(
        CreateLiteratureSearchExecution(
            project, plan, actor, "test", uuid4(), "fake", "1", ("first", "second")
        )
    )
    execution_id = UUID(created["execution_id"])
    service.execute(
        ExecuteLiteratureSearchExecution(execution_id, actor, "test", uuid4(), project_id=project)
    )

    assert len(provider.calls) == 1
    assert [row["query_index"] for row in repository.attempts(execution_id)] == [0]
    assert repository.executions[execution_id].status.value == "CANCELLED"


def test_provider_receives_live_cooperative_cancellation_signal() -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()
    actor, project, plan = uuid4(), uuid4(), uuid4()
    execution_id: UUID | None = None
    service: LiteratureSearchExecutionService

    class CooperativeProvider(FakeSearchCapability):
        requested = False

        def search(self, request, context=None):
            if not self.requested:
                self.requested = True
                assert execution_id is not None
                service.cancel(
                    CancelLiteratureSearchExecution(execution_id, actor, "test", uuid4())
                )
                assert context is not None and context.cancellation_requested()
            return super().search(request, context)

    provider = CooperativeProvider()
    service = _service(provider, repository)
    created = service.create(
        CreateLiteratureSearchExecution(
            project, plan, actor, "test", uuid4(), "fake", "1", ("cortex",)
        )
    )
    execution_id = UUID(created["execution_id"])
    service.execute(ExecuteLiteratureSearchExecution(execution_id, actor, "test", uuid4()))

    assert repository.executions[execution_id].status.value == "CANCELLED"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("max_provider_attempts", 4),
        ("timeout_seconds", 31),
        ("execution_budget_seconds", 601),
    ],
)
def test_http_create_limits_match_frozen_execution_bounds(field, value) -> None:
    payload = {
        "project_id": uuid4(),
        "search_plan_version_id": uuid4(),
        "provider_id": "fake",
        "provider_version": "1",
        "queries": [{"query_text": "cortex"}],
        field: value,
    }

    with pytest.raises(ValidationError):
        LiteratureSearchExecutionIn.model_validate(payload)


def test_new_execute_key_cannot_redispatch_unknown_before_tx_c_finalization() -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()
    provider = FakeSearchCapability(
        responses=[
            SearchResponse.uncertain(
                provider_id="fake",
                provider_version="1",
                normalized_query="cortex",
                provider_request_id=None,
            )
        ]
    )

    class InterruptedFinalizationService(LiteratureSearchExecutionService):
        def _finalize_execution(
            self, execution_id, actor_id, status, principal=None, project_id=None
        ):
            return None

    service = InterruptedFinalizationService(
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
    assert repository.executions[execution_id].status.value == "RUNNING"
    assert next(iter(repository.attempt_rows.values()))["status"] == "UNKNOWN"

    with pytest.raises(ResearchBaseError) as exc_info:
        service.execute(ExecuteLiteratureSearchExecution(execution_id, actor, "test", uuid4()))

    assert exc_info.value.code is ErrorCode.INVALID_STATE_TRANSITION
    assert len(provider.calls) == 1


def test_recovery_seals_expired_reservation_unknown_without_fabricating_query() -> None:
    repository = InMemoryLiteratureSearchExecutionRepository()
    provider = FakeSearchCapability()
    now = datetime.now(UTC)

    class StoppedDriverService(LiteratureSearchExecutionService):
        def _drive(self, execution_id, actor_id, principal=None, reserved=None, project_id=None):
            return None

    service = StoppedDriverService(
        lambda: InMemoryExecutionUnitOfWork(repository),
        provider,
        clock=lambda: now,
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
    attempt["recovery_after"] = now - timedelta(seconds=1)

    service.recover(RecoverLiteratureSearchExecution(execution_id, actor, "test", uuid4()))

    assert attempt["status"] == "UNKNOWN"
    assert repository.executions[execution_id].status.value == "UNKNOWN"
    assert repository.queries == []
    assert provider.calls == []
