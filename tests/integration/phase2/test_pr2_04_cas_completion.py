"""Frozen pack §§6/13: stale CAS and immutable unique lifecycle events on real PG."""

from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from threading import Event
from time import monotonic, sleep
from uuid import UUID, uuid4

import pytest
from scripts.pr2_04_pytest_evidence import FactRecorder
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker

from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.literature_search_execution_repository import (
    SqlAlchemyLiteratureSearchExecutionRepository,
)
from tests.integration.phase2.test_pr2_04_idempotency_coverage import _execution_setup, _snapshot


@pytest.fixture
def cas_case(phase2_database_url):
    yield from _execution_setup(phase2_database_url)


def _event(connection, execution, actor, kind, prior, new, old_version, new_version, sequence):
    connection.execute(
        text(
            "INSERT INTO literature_search_execution_events "
            "(id,execution_id,sequence,kind,attempt_id,prior_status,new_status,"
            "prior_row_version,new_row_version,occurred_at,created_by,created_at) "
            "VALUES (:id,:execution,:sequence,:kind,NULL,:prior,:new,:old_version,:new_version,"
            "clock_timestamp(),:actor,clock_timestamp())"
        ),
        dict(
            id=uuid4(),
            execution=execution,
            actor=actor,
            kind=kind,
            prior=prior,
            new=new,
            old_version=old_version,
            new_version=new_version,
            sequence=sequence,
        ),
    )


def _intent(connection, execution, actor):
    changed = connection.execute(
        text(
            "UPDATE literature_search_executions SET row_version=2 "
            "WHERE id=:id AND row_version=1 RETURNING row_version"
        ),
        {"id": execution},
    ).scalar_one()
    assert changed == 2
    _event(connection, execution, actor, "CANCEL_REQUESTED", "PLANNED", "PLANNED", 1, 2, 1)


@pytest.mark.pr204_requirements("PR204-DB-03", "PR204-DB-06")
def test_pg_stale_repository_cas_waits_for_winner_and_cannot_overwrite(
    cas_case, pr204_trace: FactRecorder
):
    engine, service, provider, principal, project, create = cas_case
    execution = UUID(service.create(create)["execution_id"])
    factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    with factory() as session:
        stale = SqlAlchemyLiteratureSearchExecutionRepository(session).get(execution)
        assert stale is not None and stale.row_version == 1
    stale.row_version = 2
    ready, release = Event(), Event()
    pids = Queue()

    def winner():
        with engine.begin() as connection:
            pid = connection.execute(text("SELECT pg_backend_pid()")).scalar_one()
            _intent(connection, execution, principal.actor_id)
            pids.put(("winner", pid))
            ready.set()
            assert release.wait(10)
        return pid

    def loser():
        assert ready.wait(10)
        with factory() as session:
            pids.put(("loser", session.execute(text("SELECT pg_backend_pid()")).scalar_one()))
            with pytest.raises(ResearchBaseError) as caught:
                SqlAlchemyLiteratureSearchExecutionRepository(session).save(stale, 1)
            assert caught.value.code is ErrorCode.CONCURRENT_MODIFICATION
            session.rollback()
            return caught.value.code.value

    with ThreadPoolExecutor(max_workers=2) as workers:
        win, lose = workers.submit(winner), workers.submit(loser)
        try:
            ids = dict([pids.get(timeout=10), pids.get(timeout=10)])
            deadline = monotonic() + 10
            waits = []
            with engine.connect() as connection:
                while monotonic() < deadline:
                    connection.execute(text("SELECT pg_stat_clear_snapshot()"))
                    row = connection.execute(
                        text(
                            "SELECT wait_event_type,pg_blocking_pids(pid) "
                            "FROM pg_stat_activity WHERE pid=:pid"
                        ),
                        {"pid": ids["loser"]},
                    ).one()
                    if row[0] == "Lock" and ids["winner"] in row[1]:
                        waits.append(dict(wait_event_type=row[0], blockers=list(row[1])))
                        break
                    sleep(0.01)
            assert waits, "actual PostgreSQL row-lock wait was not observed"
        finally:
            release.set()
        assert win.result(timeout=10) == ids["winner"]
        assert lose.result(timeout=10) == "CONCURRENT_MODIFICATION"
    rows = _snapshot(engine, project)
    assert rows["executions"][0]["status"] == "PLANNED"
    assert rows["executions"][0]["row_version"] == 2
    assert len(rows["events"]) == 2
    assert len([e for e in rows["events"] if e["kind"] == "CANCEL_REQUESTED"]) == 1
    assert len(rows["receipts"]) == 1
    assert rows["attempts"] == rows["queries"] == rows["results"] == provider.calls == []
    pr204_trace.record(
        backend_pids=ids,
        actual_lock_waits=waits,
        stale_expected_version=1,
        final_version=2,
        loser_error="CONCURRENT_MODIFICATION",
        cancellation_intents=1,
        provider_calls=0,
    )


@pytest.mark.pr204_requirements("PR204-DB-06")
@pytest.mark.parametrize("kind", ["CANCEL_REQUESTED", "FINISHED"])
def test_pg_duplicate_lifecycle_event_is_rejected_without_mutation(cas_case, kind, pr204_trace):
    engine, service, provider, principal, project, create = cas_case
    execution = UUID(service.create(create)["execution_id"])
    with engine.begin() as connection:
        _intent(connection, execution, principal.actor_id)
    if kind == "FINISHED":
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE literature_search_executions SET status='CANCELLED',"
                    "failure_code='CANCELLED',"
                    "finished_at=clock_timestamp(),row_version=3 WHERE id=:id"
                ),
                {"id": execution},
            )
            _event(connection, execution, principal.actor_id, kind, "PLANNED", "CANCELLED", 2, 3, 2)
    before = _snapshot(engine, project)
    with pytest.raises(DBAPIError) as caught:
        with engine.begin() as connection:
            if kind == "CANCEL_REQUESTED":
                connection.execute(
                    text("UPDATE literature_search_executions SET row_version=3 WHERE id=:id"),
                    {"id": execution},
                )
            _event(
                connection,
                execution,
                principal.actor_id,
                kind,
                "PLANNED",
                "CANCELLED" if kind == "FINISHED" else "PLANNED",
                2,
                3,
                3 if kind == "FINISHED" else 2,
            )
    state = getattr(caught.value.orig, "sqlstate", None)
    constraint = getattr(getattr(caught.value.orig, "diag", None), "constraint_name", None)
    assert state == "23505"
    assert constraint in {"uq_lsee_cancel_requested", "uq_lsee_finished"}
    assert _snapshot(engine, project) == before and provider.calls == []
    pr204_trace.record(
        duplicate_event=kind,
        sqlstate=state,
        constraint=constraint,
        durable_rows_unchanged=True,
        provider_calls=0,
    )
