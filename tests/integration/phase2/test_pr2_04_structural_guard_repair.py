"""Frozen pack §§13.2–13.7: scoped keys and required PostgreSQL indexes."""

from uuid import UUID, uuid4

import pytest
from scripts.pr2_04_pytest_evidence import FactRecorder
from sqlalchemy import inspect, text
from sqlalchemy.orm import sessionmaker

from researchbase.application.literature_search_execution import (
    CreateLiteratureSearchExecution,
    ExecuteLiteratureSearchExecution,
)
from researchbase.application.literature_search_provider import FakeSearchCapability
from researchbase.domain.literature_search_execution import SearchResponse
from researchbase.persistence.literature_search_execution_uow import (
    literature_search_execution_uow_factory,
)
from tests.integration.phase2.test_pr2_03_literature_search_plan_application import (
    _AlwaysValidCredential,
)
from tests.integration.phase2.test_pr2_04_execution_recovery import (
    OutcomeBeforeFinalization,
    ReservedBeforeInvocation,
)
from tests.integration.phase2.test_pr2_04_schema_coverage import (
    Q,
    _insert,
    _material,
    _reject,
    _rows,
)
from tests.pr2_04_provider_observations import PROVIDER_RETRIEVED_AT


def _additional_execution(material, *, reserved=False):
    provider = FakeSearchCapability(
        capability_id="provider-a",
        version="1",
        responses=[
            SearchResponse.success(
                provider_id="provider-a",
                provider_version="1",
                normalized_query="normalization evidence",
                provider_request_id=None,
                hits=(),
                retrieved_at=PROVIDER_RETRIEVED_AT,
            )
        ],
    )
    service_type = ReservedBeforeInvocation if reserved else OutcomeBeforeFinalization
    service = service_type(
        literature_search_execution_uow_factory(
            sessionmaker(
                bind=material["engine"],
                expire_on_commit=False,
                autoflush=False,
            )
        ),
        provider,
        credential_verifier=_AlwaysValidCredential(),
    )
    p = material["principal"]
    created = service.create(
        CreateLiteratureSearchExecution(
            material["project"],
            material["version"],
            p.actor_id,
            p.deployment_id,
            uuid4(),
            "provider-a",
            "1",
            ("normalization evidence",),
            principal=p,
        )
    )
    execution = UUID(created["execution_id"])
    service.execute(
        ExecuteLiteratureSearchExecution(
            execution,
            p.actor_id,
            p.deployment_id,
            uuid4(),
            project_id=material["project"],
            principal=p,
        )
    )
    return execution, provider


@pytest.mark.pr204_requirements("PR204-DB-01")
def test_exact_scoped_query_key_supports_concrete_fk(
    phase2_database_url, pr204_trace: FactRecorder
):
    material = _material(phase2_database_url, "sealed")
    engine = material["engine"]
    try:
        before = _rows(engine)
        query = before[Q][0]
        uniques = inspect(engine).get_unique_constraints(Q)
        # Temporary dependent is a catalog capability probe, not canonical persistence.
        with engine.begin() as connection:
            connection.execute(
                text("""
                CREATE TEMP TABLE r5_scoped_query_probe (
                  execution_id uuid, query_id uuid,
                  FOREIGN KEY(execution_id,query_id)
                    REFERENCES search_query_records(literature_search_execution_id,id)
                ) ON COMMIT DROP
            """)
            )
            connection.execute(
                text("INSERT INTO r5_scoped_query_probe VALUES (:e,:q)"),
                {"e": query["literature_search_execution_id"], "q": query["id"]},
            )
            assert (
                connection.execute(text("SELECT count(*) FROM r5_scoped_query_probe")).scalar_one()
                == 1
            )
            with pytest.raises(Exception) as caught:
                with connection.begin_nested():
                    connection.execute(
                        text("INSERT INTO r5_scoped_query_probe VALUES (:e,:q)"),
                        {"e": uuid4(), "q": query["id"]},
                    )
            assert getattr(getattr(caught.value, "orig", None), "sqlstate", None) == "23503"
        pr204_trace.record(
            unique_constraints=uniques,
            query=query,
            valid_scoped_fk_accepted=True,
            wrong_scope_sqlstate="23503",
            durable_rows_unchanged=_rows(engine) == before,
        )
        assert any(
            u["name"] == "uq_sqr_execution_id"
            and u["column_names"] == ["literature_search_execution_id", "id"]
            for u in uniques
        )
        assert _rows(engine) == before
    finally:
        engine.dispose()


@pytest.mark.pr204_requirements("PR204-DB-01")
def test_duplicate_scoped_query_identity_preserves_global_primary_key(
    phase2_database_url,
    pr204_trace: FactRecorder,
):
    material = _material(phase2_database_url, "sealed")
    engine = material["engine"]
    try:
        row = _rows(engine)[Q][0]
        _reject(
            engine,
            lambda c: _insert(c, Q, row),
            "23505",
            pr204_trace,
            case="duplicate exact query identity",
        )
    finally:
        engine.dispose()


@pytest.mark.pr204_requirements("PR204-DB-01")
def test_same_query_text_is_permitted_in_different_execution_scope(
    phase2_database_url,
    pr204_trace: FactRecorder,
):
    material = _material(phase2_database_url, "sealed")
    engine = material["engine"]
    try:
        original = _rows(engine)[Q][0]
        execution, provider = _additional_execution(material)
        queries = _rows(engine)[Q]
        other = next(q for q in queries if q["literature_search_execution_id"] == execution)
        pr204_trace.record(
            original_query=original, other_query=other, provider_calls=len(provider.calls)
        )
        assert other["query_text"] == original["query_text"]
        assert other["literature_search_execution_id"] != original["literature_search_execution_id"]
        assert other["id"] != original["id"]
        assert other["query_hash"] != original["query_hash"]
        assert len(provider.calls) == 1
    finally:
        engine.dispose()
