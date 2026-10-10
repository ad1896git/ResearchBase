"""Direct SQL successor rules after legitimate committed provider outcomes."""

import time
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from tests.integration.phase2.test_pr2_04_outcome_reapplication_acceptance import OutcomeOnly
from tests.integration.phase2.test_pr2_04_pg_retrieval_observation_repair import material
from tests.integration.phase2.test_pr2_04_schema_coverage import (
    A,
    E,
    V,
    _insert,
    _reject,
    _rows,
)
from tests.pr2_04_provider_observations import PROVIDER_RETRIEVED_AT

from researchbase.application.literature_search_execution import (
    CancelLiteratureSearchExecution,
    CreateLiteratureSearchExecution,
    ExecuteLiteratureSearchExecution,
)
from researchbase.domain.literature_search_execution import DeliveryCertainty, SearchResponse


@pytest.mark.pr204_requirements("PR204-DB-01", "PR204-DB-05")
@pytest.mark.parametrize(
    "case",
    [
        "lowered_cap",
        "permanent",
        "unknown",
        "cancelled",
        "success",
        "advance_without_success",
        "retry_after_not_elapsed",
        "expired_budget",
    ],
)
def test_pg_direct_successor_reservation_requires_remaining_safe_work(
    case, phase2_database_url, pr204_trace
):
    engine, principal, project, provider, service, original = material(
        phase2_database_url, 0, OutcomeOnly
    )
    original_row = next(row for row in _rows(engine)[E] if row["id"] == original.execution_id)
    created = service.create(
        CreateLiteratureSearchExecution(
            project,
            original_row["search_plan_version_id"],
            principal.actor_id,
            principal.deployment_id,
            uuid4(),
            "provider-a",
            "1",
            ("normalization evidence", "next query"),
            max_provider_attempts=1 if case == "lowered_cap" else 3,
            timeout_seconds=1,
            execution_budget_seconds=2 if case == "expired_budget" else 300,
            principal=principal,
        )
    )
    execution_id = UUID(created["execution_id"])
    command = ExecuteLiteratureSearchExecution(
        execution_id,
        principal.actor_id,
        principal.deployment_id,
        uuid4(),
        project_id=project,
        principal=principal,
    )
    reason = {
        "permanent": "PROVIDER_PERMANENT",
        "unknown": None,
        "cancelled": "PROVIDER_CANCELLED",
        "success": None,
    }.get(case, "PROVIDER_TRANSIENT")
    provider.responses = [
        SearchResponse(
            "provider-a",
            "1",
            "normalization evidence",
            "previous-outcome",
            DeliveryCertainty.MAY_HAVE_BEEN_SENT
            if case == "unknown"
            else DeliveryCertainty.RESPONSE_RECEIVED,
            failure_code=reason,
            retrieved_at=PROVIDER_RETRIEVED_AT if case == "success" else None,
            retry_after_seconds=60 if case == "retry_after_not_elapsed" else None,
        )
    ]
    if case == "cancelled":

        def cancel(_request):
            service.cancel(
                CancelLiteratureSearchExecution(
                    execution_id,
                    principal.actor_id,
                    principal.deployment_id,
                    uuid4(),
                    project_id=project,
                    principal=principal,
                )
            )

        provider.observer = cancel
    try:
        service.execute(command)
        if case == "expired_budget":
            # Genuine elapsed database budget, no fabricated historical timestamps.
            while True:
                with engine.connect() as connection:
                    now = connection.scalar(text("SELECT clock_timestamp()"))
                state = next(row for row in _rows(engine)[E] if row["id"] == execution_id)
                if now >= state["started_at"] + timedelta(seconds=2):
                    break
                time.sleep(0.05)
        rows = _rows(engine)
        execution = next(row for row in rows[E] if row["id"] == execution_id)
        events = [row for row in rows[V] if row["execution_id"] == execution_id]
        assert execution["status"] == "RUNNING"
        assert all(
            row["status"] != "RESERVED" for row in rows[A] if row["execution_id"] == execution_id
        )

        def mutate(connection):
            now = connection.scalar(text("SELECT clock_timestamp()"))
            next_id = uuid4()
            connection.execute(
                text(f"UPDATE {E} SET row_version=row_version+1 WHERE id=:id"), {"id": execution_id}
            )
            index = 1 if case == "advance_without_success" else 0
            _insert(
                connection,
                A,
                dict(
                    id=next_id,
                    execution_id=execution_id,
                    query_index=index,
                    attempt_number=1 if index else 2,
                    provider_request_key=next_id,
                    reserved_at=now,
                    deadline_at=now + timedelta(seconds=1),
                    recovery_after=now + timedelta(seconds=31),
                    status="RESERVED",
                    row_version=1,
                    created_by=principal.actor_id,
                    created_at=now,
                ),
            )
            _insert(
                connection,
                V,
                dict(
                    id=uuid4(),
                    execution_id=execution_id,
                    sequence=len(events),
                    kind="ATTEMPT_RESERVED",
                    attempt_id=next_id,
                    prior_status="RUNNING",
                    new_status="RUNNING",
                    prior_row_version=execution["row_version"],
                    new_row_version=execution["row_version"] + 1,
                    occurred_at=now,
                    created_at=now,
                    created_by=principal.actor_id,
                ),
            )

        _reject(engine, mutate, "P17D5", pr204_trace, case=case)
        assert len(provider.calls) == 1
    finally:
        engine.dispose()
