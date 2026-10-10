"""Real PostgreSQL maximum32 inputs ×3 provider attempts, without hidden calls."""
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from tests.integration.phase2.test_pr2_03_literature_search_plan_application import _AlwaysValidCredential
from tests.integration.phase2.test_pr2_03_review_guards import _freeze, _setup
from tests.integration.phase2.test_pr2_04_execution_recovery import OutcomeBeforeFinalization
from tests.integration.phase2.test_pr2_04_schema_coverage import A, E, V, _insert, _reject, _rows
from tests.pr2_04_provider_observations import PROVIDER_RETRIEVED_AT
from tests.unit.phase2.test_pr2_04_provider_coverage import ScriptedProvider

from researchbase.application.literature_search_execution import (
    CreateLiteratureSearchExecution, ExecuteLiteratureSearchExecution,
    LiteratureSearchExecutionService, RecoverLiteratureSearchExecution,
)
from researchbase.application.literature_search_provider import ProviderError, ProviderFailureKind
from researchbase.domain.literature_search_execution import SearchResponse
from researchbase.persistence.literature_search_execution_uow import literature_search_execution_uow_factory


@pytest.mark.pr204_requirements("PR204-DB-05", "PR204-PROV-02")
def test_pg_maximum_32_queries_96_attempts_and_no_97th_reservation(phase2_database_url, pr204_trace):
    engine, plans, principal, project, plan, version = _setup(phase2_database_url)
    _freeze(engine, plans, principal, project, plan, version)
    queries = tuple(f"boundary query {index}" for index in range(32))
    script = []
    for query in queries:
        script.extend([ProviderError(ProviderFailureKind.RETRYABLE, "PROVIDER_TRANSIENT"),
                       ProviderError(ProviderFailureKind.RETRYABLE, "PROVIDER_TRANSIENT"),
                       SearchResponse.success(provider_id="provider-a", provider_version="1",
                           normalized_query=query, provider_request_id=None, hits=(),
                           retrieved_at=PROVIDER_RETRIEVED_AT)])
    provider = ScriptedProvider(script, "provider-a")
    factory = literature_search_execution_uow_factory(
        sessionmaker(bind=engine, expire_on_commit=False, autoflush=False))
    service = OutcomeBeforeFinalization(factory, provider, credential_verifier=_AlwaysValidCredential(),
                                       sleep=lambda _: None, random_uniform=lambda _lo, _hi: 0)
    created = service.create(CreateLiteratureSearchExecution(project, version, principal.actor_id,
        principal.deployment_id, uuid4(), "provider-a", "1", queries, max_provider_attempts=3,
        timeout_seconds=1, execution_budget_seconds=600, principal=principal))
    execution_id = UUID(created["execution_id"])
    command = ExecuteLiteratureSearchExecution(execution_id, principal.actor_id, principal.deployment_id,
                                              uuid4(), project_id=project, principal=principal)
    try:
        admission = service.execute(command)
        data = service.get_provenance(principal, project, execution_id)
        assert len(provider.calls) == len(data["attempts"]) == len(data["queries"]) == 96
        assert [q["ordinal"] for q in data["queries"]] == list(range(96))
        assert [a["query_index"] for a in data["attempts"]] == [i for i in range(32) for _ in range(3)]
        assert [a["attempt_number"] for a in data["attempts"]] == [1, 2, 3] * 32
        assert [a["status"] for a in data["attempts"]] == ["RETRYABLE_FAILURE", "RETRYABLE_FAILURE", "SUCCEEDED"] * 32
        assert len({call.attempt_id for call in provider.calls}) == 96
        assert len({q["query_hash"] for q in data["queries"]}) == 96
        assert data["results"] == []
        before = _rows(engine)
        execution = next(row for row in before[E] if row["id"] == execution_id)
        assert execution["status"] == "RUNNING"
        events = [row for row in before[V] if row["execution_id"] == execution_id]
        def excess(connection):
            at = connection.scalar(text("SELECT clock_timestamp()"))
            attempt_id = uuid4()
            connection.execute(text(f"UPDATE {E} SET row_version=row_version+1 WHERE id=:id"), {"id": execution_id})
            _insert(connection, A, dict(id=attempt_id, execution_id=execution_id, query_index=31,
                attempt_number=4, provider_request_key=attempt_id, reserved_at=at,
                deadline_at=at+timedelta(seconds=1), recovery_after=at+timedelta(seconds=31),
                status="RESERVED", row_version=1, created_at=at, created_by=principal.actor_id))
            _insert(connection, V, dict(id=uuid4(), execution_id=execution_id, sequence=len(events),
                kind="ATTEMPT_RESERVED", attempt_id=attempt_id, prior_status="RUNNING", new_status="RUNNING",
                prior_row_version=execution["row_version"], new_row_version=execution["row_version"]+1,
                occurred_at=at, created_at=at, created_by=principal.actor_id))
        # The97th necessarily violates a constituent per-query bound as well as total96.
        # This is joint boundary evidence, not an independently reachable isolated97th.
        _reject(engine, excess, "P17D5", pr204_trace, case="maximum_joint_boundary")
        assert service.execute(command) == admission
        assert _rows(engine) == before
        recovery = LiteratureSearchExecutionService(factory, provider, credential_verifier=_AlwaysValidCredential())
        recovery.recover(RecoverLiteratureSearchExecution(execution_id, principal.actor_id,
            principal.deployment_id, uuid4(), project_id=project, principal=principal))
        final = recovery.get_provenance(principal, project, execution_id)
        assert final["execution"]["status"] == "SUCCEEDED"
        assert len(provider.calls) == 96
        pr204_trace.record(provider_calls=96, admitted_queries=32, final=final,
                           boundary_kind="joint total/per-query maximum; not isolated redundant guard")
    finally:
        engine.dispose()
