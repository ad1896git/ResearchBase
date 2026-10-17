"""R8A direct SQL time arithmetic, lock ordering, and additive migration proof."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from queue import Queue
from threading import Event
from time import monotonic
from typing import Any
from uuid import UUID, uuid4

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from researchbase.application.literature_search_execution import CreateLiteratureSearchExecution
from researchbase.domain.literature_search_execution import DeliveryCertainty, SearchResponse
from tests.integration.phase2.test_pr2_04_cas_completion import _event
from tests.integration.phase2.test_pr2_04_execution_migration import _alembic
from tests.integration.phase2.test_pr2_04_outcome_reapplication_acceptance import OutcomeOnly
from tests.integration.phase2.test_pr2_04_pg_retrieval_observation_repair import material
from tests.integration.phase2.test_pr2_04_schema_coverage import A, E, V, _insert, _reject, _rows

HEAD = "0025_pr2_04_reservation_guards"
PARENT = "0024_literature_search_execution"
pytestmark = pytest.mark.pr204_requirements("PR204-DB-01", "PR204-DB-05")


def _case(url, timeout=30, budget=300, outcome=None, *, migration_revision="head"):
    engine, principal, project, provider, service, original = material(
        url, 0, OutcomeOnly, migration_revision=migration_revision
    )
    plan = next(r for r in _rows(engine)[E] if r["id"] == original.execution_id)[
        "search_plan_version_id"
    ]
    created = service.create(
        CreateLiteratureSearchExecution(
            project,
            plan,
            principal.actor_id,
            principal.deployment_id,
            uuid4(),
            "provider-a",
            "1",
            ("normalization evidence", "next query"),
            timeout_seconds=timeout,
            execution_budget_seconds=budget,
            principal=principal,
        )
    )
    eid = UUID(created["execution_id"])
    if outcome:
        if outcome == "retry":
            provider.responses = [
                SearchResponse(
                    "provider-a",
                    "1",
                    "normalization evidence",
                    "prior",
                    DeliveryCertainty.NOT_SENT,
                    failure_code="PROVIDER_TRANSIENT",
                )
            ]
        service.execute(replace(original, execution_id=eid, request_id=uuid4()))
    state = next(r for r in _rows(engine)[E] if r["id"] == eid)
    return engine, principal.actor_id, provider, state


def _reserve(conn, state, actor, *, retry=False, remaining=None, offset=0):
    now = conn.scalar(text("SELECT clock_timestamp()"))
    context = state["execution_context"]
    start = state["started_at"]
    first = state["status"] == "PLANNED"
    if first:
        start = (
            now
            if remaining is None
            else now - timedelta(seconds=context["execution_budget_seconds"] - remaining)
        )
        conn.execute(
            text(
                f"UPDATE {E} SET status='RUNNING',started_at=:at,executed_by=:actor,"
                "row_version=row_version+1 WHERE id=:id"
            ),
            dict(at=start, actor=actor, id=state["id"]),
        )
    deadline = min(
        now + timedelta(seconds=context["timeout_seconds"]),
        start + timedelta(seconds=context["execution_budget_seconds"]),
    )
    deadline += timedelta(microseconds=offset)
    aid = uuid4()
    _insert(
        conn,
        A,
        dict(
            id=aid,
            execution_id=state["id"],
            query_index=0 if first or retry else 1,
            attempt_number=2 if retry else 1,
            provider_request_key=aid,
            reserved_at=now,
            deadline_at=deadline,
            recovery_after=deadline + timedelta(seconds=30),
            status="RESERVED",
            row_version=1,
            created_by=actor,
            created_at=now,
        ),
    )
    # For successors, INSERT itself must obtain the execution lock before this UPDATE.
    if not first:
        conn.execute(
            text(f"UPDATE {E} SET row_version=row_version+1 WHERE id=:id"), {"id": state["id"]}
        )
    version = conn.scalar(text(f"SELECT row_version FROM {E} WHERE id=:id"), {"id": state["id"]})
    seq = conn.scalar(text(f"SELECT count(*) FROM {V} WHERE execution_id=:id"), {"id": state["id"]})
    _insert(
        conn,
        V,
        dict(
            id=uuid4(),
            execution_id=state["id"],
            sequence=seq,
            kind="ATTEMPT_RESERVED",
            attempt_id=aid,
            prior_status=state["status"],
            new_status="RUNNING",
            prior_row_version=version - 1,
            new_row_version=version,
            occurred_at=now,
            created_by=actor,
            created_at=now,
        ),
    )
    return aid


def _cancel(conn, state, actor):
    version = conn.scalar(
        text(f"UPDATE {E} SET row_version=row_version+1 WHERE id=:id RETURNING row_version"),
        {"id": state["id"]},
    )
    seq = conn.scalar(text(f"SELECT count(*) FROM {V} WHERE execution_id=:id"), {"id": state["id"]})
    _event(
        conn,
        state["id"],
        actor,
        "CANCEL_REQUESTED",
        "RUNNING",
        "RUNNING",
        version - 1,
        version,
        seq,
    )


@pytest.mark.parametrize("kind", ["first", "retry", "next_query", "one_second", "budget"])
def test_r8a_valid_reservations_keep_exact_deadline(phase2_database_url, kind, pr204_trace):
    engine, actor, provider, state = _case(
        phase2_database_url,
        budget=1 if kind == "one_second" else 2 if kind == "budget" else 300,
        outcome="retry" if kind == "retry" else "success" if kind == "next_query" else None,
    )
    try:
        before = _rows(engine)
        with engine.begin() as conn:
            aid = _reserve(
                conn,
                state,
                actor,
                retry=kind == "retry",
            )
        after = _rows(engine)
        a = next(r for r in after[A] if r["id"] == aid)
        e = next(r for r in after[E] if r["id"] == state["id"])
        assert a["deadline_at"] == min(
            a["reserved_at"] + timedelta(seconds=state["execution_context"]["timeout_seconds"]),
            e["started_at"]
            + timedelta(seconds=state["execution_context"]["execution_budget_seconds"]),
        )
        if kind == "one_second":
            assert a["deadline_at"] - a["reserved_at"] == timedelta(seconds=1)
        assert len(after[A]) == len(before[A]) + 1
        assert a["status"] == "RESERVED"
        assert len(provider.calls) == (1 if kind in {"retry", "next_query"} else 0)
        pr204_trace.record(
            kind=kind,
            before=before,
            after=after,
            attempt_id=aid,
            committed=True,
            sqlstate=None,
            provider_calls=len(provider.calls),
        )
    finally:
        engine.dispose()


@pytest.mark.parametrize("offset", [-1, 1])
def test_r8a_deadline_minimum_is_exact_to_microsecond(phase2_database_url, offset, pr204_trace):
    engine, actor, _, state = _case(phase2_database_url)
    try:
        _reject(
            engine,
            lambda c: _reserve(c, state, actor, offset=offset),
            "P17D5",
            pr204_trace,
            case=f"deadline_offset_{offset}_microsecond",
        )
    finally:
        engine.dispose()


@pytest.mark.parametrize("isolation", ["READ COMMITTED", "REPEATABLE READ", "SERIALIZABLE"])
@pytest.mark.parametrize("ordering", ["cancel_commit", "cancel_rollback", "reservation_first"])
def test_r8a_cancellation_reservation_ordering(
    phase2_database_url, isolation, ordering, pr204_trace
):
    engine, actor, provider, state = _case(phase2_database_url, outcome="success")
    before = _rows(engine)
    ready, release = Event(), Event()
    entered = Queue()
    facts = []
    winner = "reserve" if ordering == "reservation_first" else "cancel"

    def worker(label):
        fact: dict[str, Any] = dict(
            label=label, isolation=isolation, committed=False, sqlstate=None
        )
        facts.append(fact)
        try:
            with engine.connect().execution_options(isolation_level=isolation) as conn:
                tx = conn.begin()
                pid, xid = conn.execute(text("SELECT pg_backend_pid(),txid_current()")).one()
                fact.update(pid=pid, xid=xid)
                if label != winner:
                    entered.put(pid)
                if label == "reserve":
                    fact["attempt_id"] = _reserve(conn, state, actor)
                else:
                    _cancel(conn, state, actor)
                if label == winner:
                    ready.set()
                    assert release.wait(20)
                if ordering == "cancel_rollback" and label == "cancel":
                    tx.rollback()
                    fact["rolled_back"] = True
                else:
                    tx.commit()
                    fact["committed"] = True
        except DBAPIError as error:
            fact["sqlstate"] = getattr(error.orig, "sqlstate", None)
        return fact

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(worker, winner)
            second = None
            try:
                assert ready.wait(15)
                second = pool.submit(worker, "cancel" if winner == "reserve" else "reserve")
                waiting = entered.get(timeout=10)
                blocker = next(f["pid"] for f in facts if f["label"] == winner)
                limit = monotonic() + 10
                wait = None
                while monotonic() < limit:
                    with engine.connect() as observer:
                        wait = observer.scalar(
                            text("SELECT pg_blocking_pids(:pid)"), {"pid": waiting}
                        )
                    if blocker in wait:
                        break
                    Event().wait(0.01)
                assert blocker in wait
                pr204_trace.record(
                    ordering=ordering,
                    isolation=isolation,
                    waiting_pid=waiting,
                    blocker_pid=blocker,
                    blockers=wait,
                )
            finally:
                release.set()
            first.result(timeout=25)
            assert second is not None
            second.result(timeout=25)
        after = _rows(engine)
        reserve = next(f for f in facts if f["label"] == "reserve")
        cancel = next(f for f in facts if f["label"] == "cancel")
        pr204_trace.record(
            before=before, after=after, transactions=facts, provider_calls=len(provider.calls)
        )
        if ordering == "cancel_commit":
            assert cancel["committed"]
            assert reserve["sqlstate"] == ("P17D5" if isolation == "READ COMMITTED" else "40001")
            assert not reserve["committed"]
            assert after[A] == before[A]
        else:
            assert reserve["committed"] and reserve["sqlstate"] is None
            assert len(after[A]) == len(before[A]) + 1
            if ordering == "cancel_rollback":
                assert cancel["rolled_back"] and cancel["sqlstate"] is None
            else:
                assert (
                    cancel["committed"]
                    if isolation == "READ COMMITTED"
                    else cancel["sqlstate"] == "40001"
                )
        expected_intents = int(
            ordering == "cancel_commit"
            or (ordering == "reservation_first" and isolation == "READ COMMITTED")
        )
        assert sum(r["kind"] == "CANCEL_REQUESTED" for r in after[V]) == expected_intents
        assert len(provider.calls) == 1
        assert len({f["pid"] for f in facts}) == 2
        assert len({f["xid"] for f in facts}) == 2
    finally:
        engine.dispose()


@pytest.mark.pr204_requirements("PR204-MIG-01", "PR204-MIG-02")
def test_r8a_populated_upgrade_downgrade_preserves_rows(phase2_database_url, pr204_trace):
    engine, _, _, _ = _case(phase2_database_url, outcome="success", migration_revision=HEAD)
    config = _alembic(phase2_database_url)
    try:
        before = _rows(engine)
        for revision in [PARENT, HEAD, PARENT, HEAD]:
            command.upgrade(config, revision) if revision == HEAD else command.downgrade(
                config, revision
            )
            with engine.connect() as conn:
                current = conn.scalar(text("SELECT version_num FROM alembic_version"))
                triggers = (
                    conn.execute(
                        text(
                            "SELECT tgname FROM pg_trigger WHERE NOT tgisinternal "
                            "AND tgname='trg_pr204_attempt_time_cancel_guard'"
                        )
                    )
                    .scalars()
                    .all()
                )
                functions = (
                    conn.execute(
                        text(
                            "SELECT proname FROM pg_proc "
                            "WHERE proname='pr204_guard_reservation_time_and_cancel'"
                        )
                    )
                    .scalars()
                    .all()
                )
            assert current == revision
            assert len(triggers) == len(functions) == int(revision == HEAD)
            assert _rows(engine) == before
            pr204_trace.record(
                revision=revision,
                triggers=triggers,
                functions=functions,
                before=before,
                after=_rows(engine),
                rows_unchanged=True,
            )
    finally:
        engine.dispose()
