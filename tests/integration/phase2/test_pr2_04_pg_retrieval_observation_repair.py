"""R7B C–J: actual PostgreSQL observation ownership and fresh-context durability."""

from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from scripts.pr2_04_pytest_evidence import FactRecorder
from sqlalchemy import DateTime, create_engine, inspect, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker

from researchbase.application.literature_search_execution import (
    CreateLiteratureSearchExecution,
    ExecuteLiteratureSearchExecution,
    LiteratureSearchExecutionService,
)
from researchbase.application.literature_search_provider import FakeSearchCapability
from researchbase.domain.literature_search_execution import SearchHit, SearchResponse
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.literature_search_execution_uow import (
    literature_search_execution_uow_factory,
)
from tests.integration.phase2.test_pr2_03_literature_search_plan_application import (
    _AlwaysValidCredential,
)
from tests.integration.phase2.test_pr2_03_review_guards import _freeze, _setup
from tests.unit.phase2.test_pr2_04_retrieval_observation_repair import T1, PausedFinalization

pytestmark = pytest.mark.pr204_requirements("PR204-SUCCESS-01")


def material[S: LiteratureSearchExecutionService](
    url,
    hits=0,
    service_type: type[S] = LiteratureSearchExecutionService,
    *,
    migration_revision="head",
):
    engine, plans, principal, project, plan, version = _setup(
        url, migration_revision=migration_revision
    )
    _freeze(engine, plans, principal, project, plan, version)
    response = SearchResponse.success(
        provider_id="provider-a",
        provider_version="1",
        normalized_query="normalization evidence",
        provider_request_id="provider-observation",
        retrieved_at=T1,
        hits=tuple(SearchHit(str(i), f"Paper {i}", None, None, None) for i in range(hits)),
    )
    provider = FakeSearchCapability(capability_id="provider-a", responses=[response])
    service = service_type(
        literature_search_execution_uow_factory(
            sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        ),
        provider,
        credential_verifier=_AlwaysValidCredential(),
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
    command = ExecuteLiteratureSearchExecution(
        UUID(created["execution_id"]),
        principal.actor_id,
        principal.deployment_id,
        uuid4(),
        project_id=project,
        principal=principal,
    )
    return engine, principal, project, provider, service, command


@pytest.mark.parametrize("hits", [0, 2])
def test_pg_tx_b_serialization_retry_reuses_T1_without_provider_reinvocation(
    phase2_database_url,
    hits,
    pr204_trace: FactRecorder,
):
    from tests.integration.phase2.test_pr2_04_transaction_coverage import ObservedTransactions

    engine, principal, project, provider, original, command = material(phase2_database_url, hits)
    observations = ObservedTransactions(engine, pr204_trace)
    observations.target = "outcome"
    observations.failures_remaining = 1
    service = LiteratureSearchExecutionService(
        observations.factory,
        provider,
        credential_verifier=_AlwaysValidCredential(),
        sleep=lambda _: None,
    )
    try:
        service.execute(command)
        data = service.get_provenance(principal, project, command.execution_id)
        assert observations.injections == 1
        assert any(e.get("injected_sqlstate") == "40001" for e in observations.events)
        assert len(provider.calls) == 1
        assert len(data["attempts"]) == len(data["queries"]) == 1
        assert data["attempts"][0]["retrieved_at"] == T1
        assert len(data["results"]) == hits
        assert all(r["retrieved_at"] == T1 for r in data["results"])
        pr204_trace.record(
            provider_T1=T1,
            tx_b_faults=observations.injections,
            provider_calls=len(provider.calls),
            provenance=data,
        )
    finally:
        engine.dispose()


@pytest.mark.parametrize("hits", [0, 2])
def test_pg_provider_observation_survives_fresh_context_and_public_replay(
    phase2_database_url,
    hits,
    pr204_trace: FactRecorder,
):
    engine, principal, project, provider, service, command = material(phase2_database_url, hits)
    admission = service.execute(command)
    before = service.get_provenance(principal, project, command.execution_id)
    assert before["attempts"][0]["retrieved_at"] == T1
    assert before["attempts"][0]["returned_at"] != T1
    assert len(before["results"]) == hits
    assert all(r["retrieved_at"] == T1 for r in before["results"])
    assert set(admission) == {"execution_id", "command_name", "accepted_at", "accepted_row_version"}
    assert len(provider.calls) == 1
    engine.dispose()
    del service
    fresh_engine = create_engine(phase2_database_url)
    fresh_provider = FakeSearchCapability(capability_id="provider-a")
    fresh = LiteratureSearchExecutionService(
        literature_search_execution_uow_factory(
            sessionmaker(bind=fresh_engine, expire_on_commit=False, autoflush=False)
        ),
        fresh_provider,
        credential_verifier=_AlwaysValidCredential(),
    )
    try:
        after = fresh.get_provenance(principal, project, command.execution_id)
        assert after == before
        assert fresh.execute(command) == admission
        assert fresh.get_provenance(principal, project, command.execution_id) == before
        assert fresh_provider.calls == [] and len(provider.calls) == 1
        columns = {
            c["name"]: c
            for c in inspect(fresh_engine).get_columns("literature_search_provider_attempts")
        }
        assert columns["retrieved_at"]["nullable"] is True
        column_type = columns["retrieved_at"]["type"]
        assert isinstance(column_type, DateTime)
        assert column_type.timezone is True
        pr204_trace.record(
            provider_T1=T1,
            hits=hits,
            original_calls=len(provider.calls),
            fresh_calls=len(fresh_provider.calls),
            before=before,
            after=after,
            proof="disposed original engine/service; new engine/session factory/service; same OS process",  # noqa: E501
            admission=admission,
            column_type=str(columns["retrieved_at"]["type"]),
        )
    finally:
        fresh_engine.dispose()


@pytest.mark.parametrize("hits", [0, 2])
def test_pg_internal_same_T1_noop_and_T2_immutable_mismatch(
    phase2_database_url,
    hits,
    pr204_trace: FactRecorder,
):
    engine, principal, project, provider, service, command = material(
        phase2_database_url, hits, PausedFinalization
    )
    try:
        service.execute(command)
        before = deepcopy(service.get_provenance(principal, project, command.execution_id))
        assert isinstance(service, PausedFinalization)
        assert service.outcome_args is not None
        args, kwargs = service.outcome_args
        service._persist_outcome(*args, **kwargs)
        assert service.get_provenance(principal, project, command.execution_id) == before
        changed = list(args)
        changed[6] = replace(changed[6], retrieved_at=T1 + timedelta(seconds=1))
        with pytest.raises(ResearchBaseError) as caught:
            service._persist_outcome(*changed, **kwargs)
        assert caught.value.code is ErrorCode.IMMUTABLE_RECORD
        assert service.get_provenance(principal, project, command.execution_id) == before
        assert len(provider.calls) == 1
        pr204_trace.record(
            provider_T1=T1,
            before=before,
            after=service.get_provenance(principal, project, command.execution_id),
            error=caught.value.code.value,
            provider_calls=len(provider.calls),
        )
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "case,expected",
    [
        ("success_missing", "23514"),
        ("failure_claims", "23514"),
        ("uniform_wrong", "P17D5"),
        ("nonuniform", "P17D5"),
        ("valid_zero", None),
        ("valid_two", None),
    ],
)
def test_pg_atomic_observation_shape_and_result_owner_guard(
    phase2_database_url,
    case,
    expected,
    pr204_trace: FactRecorder,
):
    from tests.integration.phase2.test_pr2_04_schema_coverage import (
        A,
        Q,
        R,
        _insert,
        _material,
        _rows,
    )

    value = _material(phase2_database_url, "reserved")
    engine = value["engine"]
    try:
        before = _rows(engine)
        attempt = before[A][0]
        query = uuid4()
        failure = case == "failure_claims"
        hits = 2 if case in {"uniform_wrong", "nonuniform", "valid_two"} else 0
        caught = None
        try:
            with engine.begin() as connection:
                if not failure:
                    _insert(
                        connection,
                        Q,
                        dict(
                            id=query,
                            literature_search_execution_id=value["execution"],
                            provider_attempt_id=attempt["id"],
                            query_text="normalization evidence",
                            perspective=None,
                            provider_id="provider-a",
                            provider_version="1",
                            ordinal=0,
                            executed_at=attempt["reserved_at"],
                            query_hash="a" * 64,
                            hash_scheme="sha256-cjson-v1",
                            created_by=value["principal"].actor_id,
                            created_at=attempt["reserved_at"],
                        ),
                    )
                    for rank in range(hits):
                        at = (
                            T1 + timedelta(seconds=1)
                            if case == "uniform_wrong" or (case == "nonuniform" and rank == 1)
                            else T1
                        )
                        _insert(
                            connection,
                            R,
                            dict(
                                id=uuid4(),
                                search_query_record_id=query,
                                rank=rank,
                                title=f"Paper {rank}",
                                external_identifier=None,
                                url=None,
                                snippet=None,
                                provider_score=None,
                                retrieved_at=at,
                                content_hash="b" * 64,
                                hash_scheme="sha256-cjson-v1",
                                created_by=value["principal"].actor_id,
                                created_at=attempt["reserved_at"],
                            ),
                        )
                connection.execute(
                    text(f"""UPDATE {A} SET status=:status,
                    query_record_id=:query, invoked_at=:invoked, returned_at=:invoked,
                    completed_at=clock_timestamp(), delivery_certainty=:certainty,
                    failure_code=:failure, result_count=:hits, warning_codes='[]'::jsonb,
                    retrieved_at=:retrieved, row_version=2 WHERE id=:id"""),
                    dict(
                        id=attempt["id"],
                        status="PERMANENT_FAILURE" if failure else "SUCCEEDED",
                        query=None if failure else query,
                        invoked=None if failure else attempt["reserved_at"],
                        certainty="NOT_SENT" if failure else "RESPONSE_RECEIVED",
                        failure="PROVIDER_PERMANENT" if failure else None,
                        hits=hits,
                        retrieved=None if case == "success_missing" else T1,
                    ),
                )
        except DBAPIError as error:
            caught = error
        actual = getattr(caught.orig, "sqlstate", None) if caught else None
        assert actual == expected
        after = _rows(engine)
        if expected:
            assert caught is not None and after == before
        else:
            assert caught is None
            assert after[A][0]["retrieved_at"] == T1
            assert len(after[R]) == hits
            assert all(r["retrieved_at"] == T1 for r in after[R])
        assert value["provider"].calls == []
        pr204_trace.record(
            case=case,
            expected_sqlstate=expected,
            actual_sqlstate=actual,
            before=before,
            after=after,
            provider_calls=0,
        )
    finally:
        engine.dispose()


@pytest.mark.parametrize("field,expected", [("attempt", "P17D1"), ("result", "P17D1")])
def test_pg_sealed_retrieval_observations_are_immutable(
    phase2_database_url,
    field,
    expected,
    pr204_trace: FactRecorder,
):
    engine, principal, project, provider, service, command = material(
        phase2_database_url, 2, PausedFinalization
    )
    try:
        service.execute(command)
        before = service.get_provenance(principal, project, command.execution_id)
        table = (
            "literature_search_provider_attempts" if field == "attempt" else "search_result_records"
        )
        with pytest.raises(DBAPIError) as caught:
            with engine.begin() as connection:
                connection.execute(
                    text(f"UPDATE {table} SET retrieved_at=:t"), {"t": T1 + timedelta(seconds=1)}
                )
        assert getattr(caught.value.orig, "sqlstate", None) == expected
        assert service.get_provenance(principal, project, command.execution_id) == before
        pr204_trace.record(
            field=field,
            sqlstate=getattr(caught.value.orig, "sqlstate", None),
            before=before,
            provider_calls=len(provider.calls),
        )
    finally:
        engine.dispose()
