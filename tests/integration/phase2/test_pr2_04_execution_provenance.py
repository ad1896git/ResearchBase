from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from scripts.pr2_04_pytest_evidence import FactRecorder
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker

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
from researchbase.persistence.literature_search_execution_uow import (
    literature_search_execution_uow_factory,
)
from tests.integration.phase2.test_pr2_03_effective_authority import _lose_owner_authority
from tests.integration.phase2.test_pr2_03_literature_search_plan_application import (
    _AlwaysValidCredential,
)
from tests.integration.phase2.test_pr2_03_review_guards import _freeze, _setup
from tests.pr2_04_provider_observations import PROVIDER_RETRIEVED_AT


def _execution_service(engine, provider: FakeSearchCapability) -> LiteratureSearchExecutionService:
    return LiteratureSearchExecutionService(
        literature_search_execution_uow_factory(
            sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        ),
        provider,
        credential_verifier=_AlwaysValidCredential(),
    )


@pytest.mark.pr204_requirements("PR204-DOM-04")
def test_pr2_04_draft_plan_version_cannot_be_bound_to_execution(
    phase2_database_url: str,
    pr204_trace: FactRecorder,
) -> None:
    engine, _plan_service, principal, project, _plan, draft_version = _setup(phase2_database_url)
    service = _execution_service(engine, FakeSearchCapability(capability_id="provider-a"))

    with pytest.raises(ResearchBaseError) as caught:
        service.create(
            CreateLiteratureSearchExecution(
                project,
                draft_version,
                principal.actor_id,
                principal.deployment_id,
                uuid4(),
                "provider-a",
                "1",
                ("normalization evidence",),
                principal=principal,
            )
        )

    assert caught.value.code is ErrorCode.SEARCH_PLAN_NOT_FROZEN
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM literature_search_executions")
            ).scalar_one()
            == 0
        )
        pr204_trace.record(
            plan_version_id=str(draft_version),
            error_code=caught.value.code.value,
            execution_count=connection.execute(
                text("SELECT count(*) FROM literature_search_executions")
            ).scalar_one(),
        )
    engine.dispose()


@pytest.mark.pr204_requirements(
    "PR204-SUCCESS-01", "PR204-TRACE-01", "PR204-DB-03", "PR204-DB-04", "PR204-DB-05"
)
def test_pr2_04_execution_persists_reconstructable_plan_attempt_query_result_chain(
    phase2_database_url: str,
    pr204_trace: FactRecorder,
) -> None:
    engine, plan_service, principal, project, plan, version = _setup(phase2_database_url)
    frozen = _freeze(engine, plan_service, principal, project, plan, version)
    response = SearchResponse.success(
        provider_id="provider-a",
        provider_version="1",
        normalized_query="normalization evidence",
        provider_request_id="provider-request-1",
        hits=(
            SearchHit(
                "result-1",
                "A result",
                "https://example.org/result-1",
                "A bounded snippet",
                0.75,
            ),
        ),
        retrieved_at=PROVIDER_RETRIEVED_AT,
    )
    provider = FakeSearchCapability(capability_id="provider-a", version="1", responses=[response])
    service = _execution_service(engine, provider)
    created = service.create(
        CreateLiteratureSearchExecution(
            project,
            version,
            principal.actor_id,
            principal.deployment_id,
            uuid4(),
            "provider-a",
            "1",
            ("normalization evidence",),
            principal=principal,
        )
    )
    execution_id = UUID(created["execution_id"])

    service.execute(
        ExecuteLiteratureSearchExecution(
            execution_id,
            principal.actor_id,
            principal.deployment_id,
            uuid4(),
            project_id=project,
            principal=principal,
        )
    )
    provenance = service.get_provenance(principal, project, execution_id)

    assert provenance["plan"]["plan_version_id"] == str(version)
    assert provenance["plan"]["content_hash"] == frozen["content_hash"]
    assert provenance["execution"]["status"] == "SUCCEEDED"
    assert len(provenance["attempts"]) == 1
    assert provenance["attempts"][0]["status"] == "SUCCEEDED"
    assert len(provenance["queries"]) == 1
    assert provenance["queries"][0]["provider_attempt_id"] == provenance["attempts"][0]["id"]
    assert provenance["queries"][0]["query_text"] == "normalization evidence"
    assert len(provenance["results"]) == 1
    assert provenance["results"][0]["search_query_record_id"] == provenance["queries"][0]["id"]
    assert provenance["results"][0]["external_identifier"] == "result-1"
    assert len(provenance["results"][0]["content_hash"]) == 64

    query_id = UUID(provenance["queries"][0]["id"])
    result_id = UUID(provenance["results"][0]["id"])
    guard_sqlstates = []

    def assert_direct_sql_rejected(statement: str, parameters: dict[str, object]) -> None:
        with pytest.raises(DBAPIError) as caught:
            with engine.begin() as connection:
                connection.execute(text(statement), parameters)
        assert getattr(caught.value.orig, "sqlstate", None) == "P17D1"
        guard_sqlstates.append(getattr(caught.value.orig, "sqlstate", None))

    assert_direct_sql_rejected(
        "UPDATE search_query_records SET query_text='tampered' WHERE id=:id", {"id": query_id}
    )
    assert_direct_sql_rejected("DELETE FROM search_query_records WHERE id=:id", {"id": query_id})
    assert_direct_sql_rejected(
        "UPDATE search_result_records SET title='tampered' WHERE id=:id", {"id": result_id}
    )
    assert_direct_sql_rejected(
        "UPDATE literature_search_executions SET row_version=row_version+1 WHERE id=:id",
        {"id": execution_id},
    )

    reserved_at = datetime.now(UTC)
    with pytest.raises(DBAPIError) as caught:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO literature_search_provider_attempts "
                    "(id,execution_id,query_index,attempt_number,provider_request_key,reserved_at,"
                    "deadline_at,recovery_after,created_by,created_at) VALUES "
                    "(:id,:execution,0,99,:id,:reserved,:deadline,:recovery,:actor,:reserved)"
                ),
                {
                    "id": uuid4(),
                    "execution": execution_id,
                    "actor": principal.actor_id,
                    "reserved": reserved_at,
                    "deadline": reserved_at + timedelta(seconds=10),
                    "recovery": reserved_at + timedelta(seconds=40),
                },
            )
    assert getattr(caught.value.orig, "sqlstate", None) == "P17D3"
    guard_sqlstates.append(getattr(caught.value.orig, "sqlstate", None))

    with engine.connect() as connection:
        assert (
            connection.execute(
                text(
                    "SELECT count(*) FROM literature_search_execution_events WHERE execution_id=:id"
                ),
                {"id": execution_id},
            ).scalar_one()
            >= 4
        )
    pr204_trace.record(
        provenance=provenance,
        provider_calls=len(provider.calls),
        rejected_sqlstates=guard_sqlstates,
    )
    engine.dispose()


@pytest.mark.pr204_requirements("PR204-PROV-01", "PR204-TRACE-02")
def test_pr2_04_provider_retry_persists_distinct_attempt_and_query_observations(
    phase2_database_url: str,
    pr204_trace: FactRecorder,
) -> None:
    engine, plan_service, principal, project, plan, version = _setup(phase2_database_url)
    _freeze(engine, plan_service, principal, project, plan, version)
    provider = FakeSearchCapability(
        capability_id="provider-a",
        version="1",
        responses=[
            SearchResponse.not_sent(
                provider_id="provider-a",
                provider_version="1",
                normalized_query="normalization evidence",
            ),
            SearchResponse.success(
                provider_id="provider-a",
                provider_version="1",
                normalized_query="normalization evidence",
                provider_request_id="provider-request-2",
                hits=(SearchHit("result-1", "A result", None, None, None),),
                retrieved_at=PROVIDER_RETRIEVED_AT,
            ),
        ],
    )
    service = _execution_service(engine, provider)
    created = service.create(
        CreateLiteratureSearchExecution(
            project,
            version,
            principal.actor_id,
            principal.deployment_id,
            uuid4(),
            "provider-a",
            "1",
            ("normalization evidence",),
            max_provider_attempts=2,
            principal=principal,
        )
    )
    execution_id = UUID(created["execution_id"])

    service.execute(
        ExecuteLiteratureSearchExecution(
            execution_id,
            principal.actor_id,
            principal.deployment_id,
            uuid4(),
            project_id=project,
            principal=principal,
        )
    )
    provenance = service.get_provenance(principal, project, execution_id)

    assert len(provider.calls) == 2
    assert [row["attempt_number"] for row in provenance["attempts"]] == [1, 2]
    assert [row["status"] for row in provenance["attempts"]] == [
        "RETRYABLE_FAILURE",
        "SUCCEEDED",
    ]
    assert len(provenance["queries"]) == 2
    assert [row["ordinal"] for row in provenance["queries"]] == [0, 1]
    assert provenance["queries"][0]["query_hash"] != provenance["queries"][1]["query_hash"]
    assert [row["provider_attempt_id"] for row in provenance["queries"]] == [
        row["id"] for row in provenance["attempts"]
    ]
    assert len(provenance["results"]) == 1
    assert provenance["execution"]["status"] == "SUCCEEDED"
    pr204_trace.record(provenance=provenance, provider_calls=len(provider.calls))
    engine.dispose()


@pytest.mark.pr204_requirements("PR204-CANCEL-01", "PR204-CRASH-07", "PR204-IDEM-01")
def test_pr2_04_interrupted_c1_recovers_cancelled_without_provider_dispatch(
    phase2_database_url: str,
    pr204_trace: FactRecorder,
) -> None:
    engine, plan_service, principal, project, plan, version = _setup(phase2_database_url)
    _freeze(engine, plan_service, principal, project, plan, version)
    provider = FakeSearchCapability(capability_id="provider-a", version="1")
    factory = literature_search_execution_uow_factory(
        sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    )

    def crash_after_c1() -> None:
        raise RuntimeError("simulated process interruption after committed cancellation intent")

    service = LiteratureSearchExecutionService(
        factory,
        provider,
        credential_verifier=_AlwaysValidCredential(),
        after_cancel_admission=crash_after_c1,
    )
    created = service.create(
        CreateLiteratureSearchExecution(
            project,
            version,
            principal.actor_id,
            principal.deployment_id,
            uuid4(),
            "provider-a",
            "1",
            ("normalization evidence",),
            principal=principal,
        )
    )
    execution_id = UUID(created["execution_id"])
    cancel = CancelLiteratureSearchExecution(
        execution_id,
        principal.actor_id,
        principal.deployment_id,
        uuid4(),
        project_id=project,
        principal=principal,
    )

    with pytest.raises(RuntimeError, match="simulated process interruption"):
        service.cancel(cancel)
    pr204_trace.record(
        phase="after_committed_C1",
        execution=service.get(principal, project, execution_id),
        provider_calls=len(provider.calls),
    )

    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT status,row_version FROM literature_search_executions WHERE id=:id"),
            {"id": execution_id},
        ).one() == ("PLANNED", 2)
        assert (
            connection.execute(
                text(
                    "SELECT count(*) FROM literature_search_execution_events "
                    "WHERE execution_id=:id AND kind='CANCEL_REQUESTED'"
                ),
                {"id": execution_id},
            ).scalar_one()
            == 1
        )
        assert (
            connection.execute(
                text(
                    "SELECT count(*) FROM literature_search_execution_events "
                    "WHERE execution_id=:id AND kind='FINISHED'"
                ),
                {"id": execution_id},
            ).scalar_one()
            == 0
        )
        assert (
            connection.execute(
                text(
                    "SELECT count(*) FROM literature_search_provider_attempts "
                    "WHERE execution_id=:id"
                ),
                {"id": execution_id},
            ).scalar_one()
            == 0
        )

    replay = LiteratureSearchExecutionService(
        factory, provider, credential_verifier=_AlwaysValidCredential()
    )
    assert replay.cancel(cancel)["accepted_row_version"] == 2
    recover = RecoverLiteratureSearchExecution(
        execution_id,
        principal.actor_id,
        principal.deployment_id,
        uuid4(),
        project_id=project,
        principal=principal,
    )
    recovered = replay.recover(recover)

    assert recovered["accepted_row_version"] == 3
    assert provider.calls == []
    with engine.connect() as connection:
        assert connection.execute(
            text(
                "SELECT status,row_version,started_at FROM literature_search_executions "
                "WHERE id=:id"
            ),
            {"id": execution_id},
        ).one() == ("CANCELLED", 3, None)
        assert (
            connection.execute(
                text(
                    "SELECT count(*) FROM literature_search_execution_events "
                    "WHERE execution_id=:id AND kind='FINISHED'"
                ),
                {"id": execution_id},
            ).scalar_one()
            == 1
        )
    replay.recover(recover)
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT row_version FROM literature_search_executions WHERE id=:id"),
                {"id": execution_id},
            ).scalar_one()
            == 3
        )
        assert (
            connection.execute(
                text(
                    "SELECT count(*) FROM literature_search_execution_events "
                    "WHERE execution_id=:id AND kind='FINISHED'"
                ),
                {"id": execution_id},
            ).scalar_one()
            == 1
        )
    pr204_trace.record(
        phase="after_recovery_and_replay",
        admission=recovered,
        provenance=replay.get_provenance(principal, project, execution_id),
        provider_calls=len(provider.calls),
    )
    engine.dispose()


@pytest.mark.pr204_requirements("PR204-AUTH-03")
def test_pr2_04_authority_loss_during_provider_call_denies_tx_b(
    phase2_database_url: str,
    pr204_trace: FactRecorder,
) -> None:
    engine, plan_service, principal, project, plan, version = _setup(phase2_database_url)
    _freeze(engine, plan_service, principal, project, plan, version)
    provider = FakeSearchCapability(
        capability_id="provider-a",
        version="1",
        responses=[
            SearchResponse.success(
                provider_id="provider-a",
                provider_version="1",
                normalized_query="normalization evidence",
                provider_request_id="provider-request-1",
                hits=(SearchHit("result-1", "A result", None, None, None),),
                retrieved_at=PROVIDER_RETRIEVED_AT,
            )
        ],
    )
    service = _execution_service(engine, provider)
    created = service.create(
        CreateLiteratureSearchExecution(
            project,
            version,
            principal.actor_id,
            principal.deployment_id,
            uuid4(),
            "provider-a",
            "1",
            ("normalization evidence",),
            principal=principal,
        )
    )
    execution_id = UUID(created["execution_id"])
    invoked = False

    def revoke_authority(_request) -> None:
        nonlocal invoked
        if not invoked:
            invoked = True
            _lose_owner_authority(engine, principal, project, phase2_database_url)

    provider.observer = revoke_authority
    with pytest.raises(ResearchBaseError) as caught:
        service.execute(
            ExecuteLiteratureSearchExecution(
                execution_id,
                principal.actor_id,
                principal.deployment_id,
                uuid4(),
                project_id=project,
                principal=principal,
            )
        )

    assert caught.value.code is ErrorCode.FORBIDDEN
    assert invoked
    assert len(provider.calls) == 1
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT status,row_version FROM literature_search_executions WHERE id=:id"),
            {"id": execution_id},
        ).one() == ("RUNNING", 2)
        assert (
            connection.execute(
                text(
                    "SELECT count(*) FROM literature_search_provider_attempts "
                    "WHERE execution_id=:id"
                ),
                {"id": execution_id},
            ).scalar_one()
            == 1
        )
        assert (
            connection.execute(
                text(
                    "SELECT count(*) FROM search_query_records "
                    "WHERE literature_search_execution_id=:id"
                ),
                {"id": execution_id},
            ).scalar_one()
            == 0
        )
        pr204_trace.record(
            error_code=caught.value.code.value,
            provider_calls=len(provider.calls),
            execution=dict(
                connection.execute(
                    text(
                        "SELECT id,status,row_version FROM literature_search_executions "
                        "WHERE id=:id"
                    ),
                    {"id": execution_id},
                )
                .mappings()
                .one()
            ),
            attempts=[
                dict(row)
                for row in connection.execute(
                    text(
                        "SELECT id,status,row_version FROM literature_search_provider_attempts "
                        "WHERE execution_id=:id"
                    ),
                    {"id": execution_id},
                ).mappings()
            ],
        )
        assert (
            connection.execute(
                text(
                    "SELECT count(*) FROM search_result_records r "
                    "JOIN search_query_records q ON q.id=r.search_query_record_id "
                    "WHERE q.literature_search_execution_id=:id"
                ),
                {"id": execution_id},
            ).scalar_one()
            == 0
        )
        assert (
            connection.execute(
                text(
                    "SELECT count(*) FROM literature_search_execution_events "
                    "WHERE execution_id=:id AND kind='OUTCOME_RECORDED'"
                ),
                {"id": execution_id},
            ).scalar_one()
            == 0
        )
    engine.dispose()


@pytest.mark.pr204_requirements("PR204-IDEM-01", "PR204-IDEM-02")
def test_pr2_04_create_receipt_replay_and_same_key_payload_conflict_are_durable(
    phase2_database_url: str,
    pr204_trace: FactRecorder,
) -> None:
    engine, plan_service, principal, project, plan, version = _setup(phase2_database_url)
    _freeze(engine, plan_service, principal, project, plan, version)
    provider = FakeSearchCapability(capability_id="provider-a", version="1")
    service = _execution_service(engine, provider)
    request_id = uuid4()
    command = CreateLiteratureSearchExecution(
        project,
        version,
        principal.actor_id,
        principal.deployment_id,
        request_id,
        "provider-a",
        "1",
        ("normalization evidence",),
        principal=principal,
    )

    first = service.create(command)
    replay = service.create(command)
    assert replay == first

    with pytest.raises(ResearchBaseError) as caught:
        service.create(
            CreateLiteratureSearchExecution(
                project,
                version,
                principal.actor_id,
                principal.deployment_id,
                request_id,
                "provider-a",
                "1",
                ("different query",),
                principal=principal,
            )
        )

    assert caught.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    assert provider.calls == []
    pr204_trace.record(
        first_admission=first,
        replay_admission=replay,
        conflicting_payload_error=caught.value.code.value,
        provider_calls=len(provider.calls),
    )
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM literature_search_executions WHERE project_id=:project"),
                {"project": project},
            ).scalar_one()
            == 1
        )
        assert (
            connection.execute(
                text(
                    "SELECT count(*) FROM literature_search_execution_command_receipts "
                    "WHERE command_name='CREATE_LITERATURE_SEARCH_EXECUTION' "
                    "AND request_id=:request"
                ),
                {"request": request_id},
            ).scalar_one()
            == 1
        )
    engine.dispose()


@pytest.mark.pr204_requirements("PR204-UNKNOWN-02", "PR204-UNKNOWN-04")
def test_pr2_04_unknown_is_terminal_and_replay_or_recovery_never_redispatches(
    phase2_database_url: str,
    pr204_trace: FactRecorder,
) -> None:
    engine, plan_service, principal, project, plan, version = _setup(phase2_database_url)
    _freeze(engine, plan_service, principal, project, plan, version)
    provider = FakeSearchCapability(
        capability_id="provider-a",
        version="1",
        responses=[
            SearchResponse.uncertain(
                provider_id="provider-a",
                provider_version="1",
                normalized_query="normalization evidence",
                provider_request_id=None,
            )
        ],
    )
    service = _execution_service(engine, provider)
    created = service.create(
        CreateLiteratureSearchExecution(
            project,
            version,
            principal.actor_id,
            principal.deployment_id,
            uuid4(),
            "provider-a",
            "1",
            ("normalization evidence",),
            principal=principal,
        )
    )
    execution_id = UUID(created["execution_id"])
    execute = ExecuteLiteratureSearchExecution(
        execution_id,
        principal.actor_id,
        principal.deployment_id,
        uuid4(),
        project_id=project,
        principal=principal,
    )

    service.execute(execute)
    service.execute(execute)
    service.recover(
        RecoverLiteratureSearchExecution(
            execution_id,
            principal.actor_id,
            principal.deployment_id,
            uuid4(),
            project_id=project,
            principal=principal,
        )
    )
    with pytest.raises(ResearchBaseError) as caught:
        service.execute(
            ExecuteLiteratureSearchExecution(
                execution_id,
                principal.actor_id,
                principal.deployment_id,
                uuid4(),
                project_id=project,
                principal=principal,
            )
        )

    assert caught.value.code is ErrorCode.INVALID_STATE_TRANSITION
    assert len(provider.calls) == 1
    provenance = service.get_provenance(principal, project, execution_id)
    assert provenance["execution"]["status"] == "UNKNOWN"
    assert len(provenance["attempts"]) == 1
    assert provenance["attempts"][0]["status"] == "UNKNOWN"
    assert len(provenance["results"]) == 0
    pr204_trace.record(
        provenance=provenance,
        provider_calls=len(provider.calls),
        new_execute_error=caught.value.code.value,
    )
    engine.dispose()


@pytest.mark.parametrize("failure_kind", ["permanent", "malformed_echo"])
@pytest.mark.pr204_requirements("PR204-PROV-03", "PR204-PROV-04")
def test_pr2_04_known_provider_failure_is_terminal_without_retry_or_partial_results(
    phase2_database_url: str,
    failure_kind: str,
    pr204_trace: FactRecorder,
) -> None:
    engine, plan_service, principal, project, plan, version = _setup(phase2_database_url)
    _freeze(engine, plan_service, principal, project, plan, version)
    if failure_kind == "permanent":
        response = SearchResponse(
            "provider-a",
            "1",
            "normalization evidence",
            "provider-request-1",
            DeliveryCertainty.RESPONSE_RECEIVED,
            failure_code="PROVIDER_PERMANENT",
        )
        expected_attempt = "PERMANENT_FAILURE"
        expected_failure = "PROVIDER_PERMANENT"
    else:
        response = SearchResponse.success(
            provider_id="different-provider",
            provider_version="1",
            normalized_query="normalization evidence",
            provider_request_id="provider-request-1",
            hits=(SearchHit("must-not-survive", "Malformed echo", None, None, None),),
            retrieved_at=PROVIDER_RETRIEVED_AT,
        )
        expected_attempt = "PERMANENT_FAILURE"
        expected_failure = "PROVIDER_MALFORMED"
    provider = FakeSearchCapability(capability_id="provider-a", version="1", responses=[response])
    service = _execution_service(engine, provider)
    created = service.create(
        CreateLiteratureSearchExecution(
            project,
            version,
            principal.actor_id,
            principal.deployment_id,
            uuid4(),
            "provider-a",
            "1",
            ("normalization evidence",),
            principal=principal,
        )
    )
    execution_id = UUID(created["execution_id"])
    service.execute(
        ExecuteLiteratureSearchExecution(
            execution_id,
            principal.actor_id,
            principal.deployment_id,
            uuid4(),
            project_id=project,
            principal=principal,
        )
    )
    provenance = service.get_provenance(principal, project, execution_id)

    assert len(provider.calls) == 1
    assert provenance["execution"]["status"] == "FAILED"
    assert provenance["execution"]["failure_code"] == expected_failure
    assert len(provenance["attempts"]) == 1
    assert provenance["attempts"][0]["status"] == expected_attempt
    assert provenance["attempts"][0]["failure_code"] == expected_failure
    assert len(provenance["results"]) == 0
    pr204_trace.record(
        failure_kind=failure_kind, provenance=provenance, provider_calls=len(provider.calls)
    )
    engine.dispose()
