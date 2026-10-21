"""Frozen pack §§6/13: independently executable planned/cancelled SQL lifecycle guards."""

from uuid import UUID

import pytest
from scripts.pr2_04_pytest_evidence import FactRecorder
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from tests.integration.phase2.test_pr2_04_cas_completion import _event, _intent
from tests.integration.phase2.test_pr2_04_idempotency_coverage import _execution_setup, _snapshot


@pytest.fixture
def sql_case(phase2_database_url):
    yield from _execution_setup(phase2_database_url)


@pytest.mark.parametrize("target", ["SUCCEEDED", "FAILED", "UNKNOWN"])
@pytest.mark.pr204_requirements("PR204-DOM-01", "PR204-DB-01")
def test_pg_planned_cannot_skip_running_into_provider_terminal_state(
    sql_case, target, pr204_trace: FactRecorder
):
    engine, service, provider, principal, project, create = sql_case
    execution = UUID(service.create(create)["execution_id"])
    before = _snapshot(engine, project)
    with pytest.raises(DBAPIError) as caught:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE literature_search_executions SET status=:status,row_version=2 "
                    "WHERE id=:id"
                ),
                dict(status=target, id=execution),
            )
    assert getattr(caught.value.orig, "sqlstate", None) == "P17D4"
    assert _snapshot(engine, project) == before and provider.calls == []
    pr204_trace.record(
        source="PLANNED",
        attempted_target=target,
        sqlstate="P17D4",
        before=before,
        after=_snapshot(engine, project),
        provider_calls=0,
    )


@pytest.mark.parametrize(
    "target", ["PLANNED", "RUNNING", "SUCCEEDED", "FAILED", "UNKNOWN", "CANCELLED"]
)
@pytest.mark.pr204_requirements("PR204-DOM-01", "PR204-DB-01", "PR204-DB-06")
def test_pg_prestart_cancelled_is_immutable_for_every_target_including_same_state(
    sql_case, target, pr204_trace: FactRecorder
):
    engine, service, provider, principal, project, create = sql_case
    execution = UUID(service.create(create)["execution_id"])
    # Valid direct SQL fixture follows required state/event order, with no attempt
    # or trigger suppression. It independently tests the DB lifecycle backstop.
    with engine.begin() as connection:
        _intent(connection, execution, principal.actor_id)
        connection.execute(
            text(
                "UPDATE literature_search_executions SET status='CANCELLED',row_version=3,"
                "finished_at=clock_timestamp(),failure_code='CANCELLED' WHERE id=:id"
            ),
            dict(id=execution),
        )
        _event(
            connection, execution, principal.actor_id, "FINISHED", "PLANNED", "CANCELLED", 2, 3, 2
        )
    before = _snapshot(engine, project)
    assert before["executions"][0]["status"] == "CANCELLED"
    assert before["executions"][0]["started_at"] is None
    assert before["executions"][0]["executed_by"] == principal.actor_id
    assert before["attempts"] == before["queries"] == before["results"] == []
    with pytest.raises(DBAPIError) as caught:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE literature_search_executions SET status=:status,row_version=4 "
                    "WHERE id=:id"
                ),
                dict(status=target, id=execution),
            )
    assert getattr(caught.value.orig, "sqlstate", None) == "P17D1"
    assert _snapshot(engine, project) == before and provider.calls == []
    assert [e["kind"] for e in sorted(before["events"], key=lambda e: e["sequence"])] == [
        "CREATED",
        "CANCEL_REQUESTED",
        "FINISHED",
    ]
    pr204_trace.record(
        source="CANCELLED",
        attempted_target=target,
        sqlstate="P17D1",
        before=before,
        after=_snapshot(engine, project),
        provider_calls=0,
    )
