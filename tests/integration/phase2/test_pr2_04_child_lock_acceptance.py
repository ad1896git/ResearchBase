"""Direct SQL child appends serialize on the execution row with terminalization."""

from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from threading import Event
from time import monotonic
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from tests.integration.phase2.test_pr2_04_cas_completion import _event
from tests.integration.phase2.test_pr2_04_schema_coverage import (
    E,
    Q,
    R,
    V,
    _insert,
    _material,
    _rows,
)


@pytest.mark.parametrize("run", range(1, 6))
@pytest.mark.parametrize("winner", ["child", "terminal"])
@pytest.mark.parametrize("child", [Q, R])
@pytest.mark.pr204_requirements("PR204-DB-04", "PR204-CONC-06")
def test_pg_direct_child_append_and_terminalization_share_execution_lock(
    phase2_database_url, run, winner, child, pr204_trace
):
    material = _material(phase2_database_url, "sealed")
    engine = material["engine"]
    before = _rows(engine)
    execution = before[E][0]
    row = before[child][0].copy()
    row["id"] = uuid4()
    if child == Q:
        row.update(ordinal=1, query_hash="b" * 64)
    else:
        row.update(rank=1)
    ready, release = Event(), Event()
    entered = Queue()
    observations = []

    def worker(label):
        fact = {"label": label, "sqlstate": None, "committed": False}
        observations.append(fact)
        try:
            with engine.connect() as conn:
                tx = conn.begin()
                pid, xid = conn.execute(text("SELECT pg_backend_pid(),txid_current()")).one()
                fact.update(pid=pid, xid=xid)
                if label != winner:
                    entered.put(pid)
                if label == "child":
                    _insert(conn, child, row)
                else:
                    conn.execute(
                        text(
                            "UPDATE literature_search_executions SET status='SUCCEEDED',finished_at=clock_timestamp(),row_version=row_version+1 WHERE id=:id"
                        ),
                        {"id": execution["id"]},
                    )
                    _event(
                        conn,
                        execution["id"],
                        material["principal"].actor_id,
                        "FINISHED",
                        "RUNNING",
                        "SUCCEEDED",
                        execution["row_version"],
                        execution["row_version"] + 1,
                        len(before[V]),
                    )
                fact["statement_completed"] = True
                if label == winner:
                    ready.set()
                    assert release.wait(15)
                tx.commit()
                fact["committed"] = True
        except DBAPIError as error:
            fact["sqlstate"] = error.orig.sqlstate
        return fact

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(worker, winner)
            second = None
            try:
                assert ready.wait(10)
                second = pool.submit(worker, "terminal" if winner == "child" else "child")
                waiting_pid = entered.get(timeout=10)
                blocker = next(x["pid"] for x in observations if x["label"] == winner)
                limit = monotonic() + 10
                wait = None
                while monotonic() < limit:
                    with engine.connect() as observer:
                        wait = dict(
                            observer.execute(
                                text(
                                    "SELECT wait_event_type,pg_blocking_pids(pid) AS blockers FROM pg_stat_activity WHERE pid=:pid"
                                ),
                                {"pid": waiting_pid},
                            )
                            .mappings()
                            .one()
                        )
                    if wait["wait_event_type"] == "Lock" and blocker in wait["blockers"]:
                        break
                    Event().wait(0.01)
                assert (
                    wait is not None
                    and wait["wait_event_type"] == "Lock"
                    and blocker in wait["blockers"]
                )
                pr204_trace.record(
                    phase="actual_lock_wait",
                    run=run,
                    child=child,
                    winner=winner,
                    waiting_pid=waiting_pid,
                    blocker_pid=blocker,
                    wait=wait,
                )
            finally:
                release.set()
            first.result(timeout=20)
            assert second is not None
            second.result(timeout=20)
        after = _rows(engine)
        child_fact = next(x for x in observations if x["label"] == "child")
        terminal_fact = next(x for x in observations if x["label"] == "terminal")
        pr204_trace.record(
            before=before,
            after=after,
            transactions=observations,
            provider_calls=len(material["provider"].calls),
        )
        assert child_fact["sqlstate"] == ("P17D5" if winner == "child" else "P17D3")
        assert not child_fact["committed"] and terminal_fact["committed"]
        assert len({x["pid"] for x in observations}) == 2
        assert len({x["xid"] for x in observations}) == 2
        assert after[Q] == before[Q] and after[R] == before[R]
        assert after[E][0]["status"] == "SUCCEEDED"
        assert after[E][0]["row_version"] == execution["row_version"] + 1
        assert len(after[V]) == len(before[V]) + 1
        assert sum(x["kind"] == "FINISHED" for x in after[V]) == 1
        assert len(material["provider"].calls) == 1
        pr204_trace.record(before=before, after=after, transactions=observations, provider_calls=1)
    finally:
        engine.dispose()
