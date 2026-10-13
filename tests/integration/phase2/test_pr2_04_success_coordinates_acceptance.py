"""Actual PostgreSQL lifecycle timestamps and attribution for zero/one-hit success."""

from datetime import timedelta

import pytest
from sqlalchemy import text

from researchbase.domain.literature_search_execution import SearchHit, SearchResponse
from tests.integration.phase2.test_pr2_04_idempotency_coverage import _snapshot
from tests.integration.phase2.test_pr2_04_provider_pg_coverage import QUERY, setup_case
from tests.pr2_04_provider_observations import PROVIDER_RETRIEVED_AT


@pytest.mark.pr204_requirements("PR204-SUCCESS-01")
@pytest.mark.parametrize("hits", [0, 1], ids=["zero-hit", "one-hit"])
def test_pg_success_full_coordinates_and_admission(phase2_database_url, hits, pr204_trace):
    response = SearchResponse.success(
        provider_id="provider-a",
        provider_version="1",
        normalized_query=QUERY,
        provider_request_id="coordinates",
        retrieved_at=PROVIDER_RETRIEVED_AT,
        hits=tuple(SearchHit(str(i), "Paper", None, None, None) for i in range(hits)),
    )
    engine, provider, service, principal, project, command, frozen = setup_case(
        phase2_database_url, [response]
    )
    try:
        planned = _snapshot(engine, project)
        assert planned["executions"][0]["status"] == "PLANNED"
        assert planned["executions"][0]["started_at"] is None
        assert planned["executions"][0]["finished_at"] is None
        assert len(planned["receipts"]) == 1
        with engine.connect() as connection:
            before = connection.scalar(text("SELECT clock_timestamp()"))
        admission = service.execute(command)
        rows = _snapshot(engine, project)
        with engine.connect() as connection:
            after = connection.scalar(text("SELECT clock_timestamp()"))
        execution, attempt, query = rows["executions"][0], rows["attempts"][0], rows["queries"][0]
        assert execution["status"] == "SUCCEEDED" and execution["failure_code"] is None
        assert execution["requested_by"] == execution["executed_by"] == principal.actor_id
        assert execution["created_by"] == principal.actor_id
        assert before <= execution["started_at"] <= execution["finished_at"] <= after
        assert attempt["status"] == "SUCCEEDED" and attempt["row_version"] == 2
        assert attempt["failure_code"] is None
        assert attempt["delivery_certainty"] == "RESPONSE_RECEIVED"
        assert attempt["reserved_at"] <= attempt["completed_at"]
        assert attempt["invoked_at"] <= attempt["returned_at"]
        assert query["executed_at"] == attempt["invoked_at"]
        context = execution["execution_context"]
        assert attempt["deadline_at"] == min(
            attempt["reserved_at"] + timedelta(seconds=context["timeout_seconds"]),
            execution["started_at"] + timedelta(seconds=context["execution_budget_seconds"]),
        )
        assert attempt["recovery_after"] == attempt["deadline_at"] + timedelta(seconds=30)
        assert attempt["retrieved_at"] == PROVIDER_RETRIEVED_AT
        assert attempt["result_count"] == len(rows["results"]) == hits
        assert all(row["retrieved_at"] == PROVIDER_RETRIEVED_AT for row in rows["results"])
        assert query["provider_attempt_id"] == attempt["id"]
        assert attempt["query_record_id"] == query["id"]
        assert query["literature_search_execution_id"] == attempt["execution_id"] == execution["id"]
        assert query["ordinal"] == 0
        assert [row["rank"] for row in rows["results"]] == list(range(hits))
        assert all(row["search_query_record_id"] == query["id"] for row in rows["results"])
        events = sorted(rows["events"], key=lambda row: row["sequence"])
        assert [row["kind"] for row in events] == [
            "CREATED",
            "ATTEMPT_RESERVED",
            "OUTCOME_RECORDED",
            "FINISHED",
        ]
        assert [row["sequence"] for row in events] == [0, 1, 2, 3]
        assert [row["new_row_version"] for row in events] == [1, 2, 3, 4]
        assert [row["prior_row_version"] for row in events] == [None, 1, 2, 3]
        assert [row["new_status"] for row in events] == [
            "PLANNED",
            "RUNNING",
            "RUNNING",
            "SUCCEEDED",
        ]
        assert execution["row_version"] == 4
        assert all(row["created_by"] == principal.actor_id for row in events)
        assert len(rows["receipts"]) == 2
        assert set(admission) == {
            "execution_id",
            "command_name",
            "accepted_at",
            "accepted_row_version",
        }
        assert admission["accepted_row_version"] == 2
        receipt = next(row for row in rows["receipts"] if row["request_id"] == command.request_id)
        assert receipt["result_execution_id"] == execution["id"]
        assert receipt["result_json"] == admission
        data = service.get_provenance(principal, project, command.execution_id)
        assert data["plan"]["content_hash"] == frozen["content_hash"]
        assert service.execute(command) == admission
        assert _snapshot(engine, project) == rows
        assert len(provider.calls) == 1
        pr204_trace.record(
            provider_calls=1,
            admission=admission,
            db_before=before,
            db_after=after,
            provenance=data,
            rows=rows,
        )
    finally:
        engine.dispose()
