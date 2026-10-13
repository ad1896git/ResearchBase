from __future__ import annotations

import os
from collections.abc import Iterator
from threading import Event, Thread
from time import monotonic

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError

from researchbase.persistence.database import create_database_engine
from tests.integration.test_pr17dr_adversarial import _seed_planned_run_with_snapshot

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def engine() -> Iterator[Engine]:
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL is not set; run against PostgreSQL 18")
    value = create_database_engine()
    try:
        yield value
    finally:
        value.dispose()


def _lock_wait_observed(engine: Engine, backend_pid: int) -> bool:
    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT wait_event_type, wait_event FROM pg_stat_activity WHERE pid=:pid"),
            {"pid": backend_pid},
        ).one_or_none()
    return row is not None and row.wait_event_type == "Lock"


def test_parent_lock_and_child_insert_overlap_on_real_connections(
    engine: Engine,
) -> None:
    run_id, snapshot_id = _seed_planned_run_with_snapshot(engine)
    parent_locked = Event()
    child_statement_started = Event()
    release_parent = Event()
    child_finished = Event()
    parent_pid: list[int] = []
    child_pid: list[int] = []
    parent_errors: list[BaseException] = []
    child_errors: list[BaseException] = []

    def parent_transaction() -> None:
        try:
            with engine.connect() as connection:
                transaction = connection.begin()
                try:
                    parent_pid.append(
                        int(connection.execute(text("SELECT pg_backend_pid()")).scalar_one())
                    )
                    connection.execute(
                        text("SELECT id FROM public.runs WHERE id=:run FOR UPDATE"),
                        {"run": run_id},
                    )
                    parent_locked.set()
                    assert release_parent.wait(timeout=10)
                    connection.execute(
                        text(
                            "UPDATE public.runs SET status='RUNNING', "
                            "inputs_sealed_at=:now, started_at=:now, row_version=2 "
                            "WHERE id=:run"
                        ),
                        {"run": run_id, "now": "2026-09-05T01:00:00+00:00"},
                    )
                    transaction.commit()
                except BaseException:
                    transaction.rollback()
                    raise
        except BaseException as exc:
            parent_errors.append(exc)

    def child_transaction() -> None:
        assert parent_locked.wait(timeout=10)
        try:
            with engine.connect() as connection:
                transaction = connection.begin()
                child_pid.append(
                    int(connection.execute(text("SELECT pg_backend_pid()")).scalar_one())
                )
                child_statement_started.set()
                try:
                    connection.execute(
                        text(
                            "INSERT INTO public.run_dataset_inputs "
                            "(run_id, dataset_snapshot_id, role, ordinal) "
                            "VALUES (:run, :snapshot, 'train', 0)"
                        ),
                        {"run": run_id, "snapshot": snapshot_id},
                    )
                    transaction.commit()
                except BaseException:
                    transaction.rollback()
                    raise
        except BaseException as exc:
            child_errors.append(exc)
        finally:
            child_finished.set()

    parent = Thread(target=parent_transaction, name="pr17dr2-parent")
    child = Thread(target=child_transaction, name="pr17dr2-child")
    parent.start()
    child.start()

    assert parent_locked.wait(timeout=10)
    assert child_statement_started.wait(timeout=10)
    deadline = monotonic() + 10
    observed_lock_wait = False
    while monotonic() < deadline and not child_finished.is_set():
        if child_pid and _lock_wait_observed(engine, child_pid[0]):
            observed_lock_wait = True
            break
        Event().wait(0.02)
    release_parent.set()

    parent.join(timeout=10)
    child.join(timeout=10)
    assert not parent.is_alive()
    assert not child.is_alive()
    assert not parent_errors
    assert parent_pid and child_pid and parent_pid[0] != child_pid[0]
    assert observed_lock_wait
    assert child_errors
    assert isinstance(child_errors[0], DBAPIError)
    assert getattr(child_errors[0].orig, "sqlstate", None) == "P17D1"

    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT status, inputs_sealed_at, started_at, row_version "
                "FROM public.runs WHERE id=:run"
            ),
            {"run": run_id},
        ).one()
        child_count = connection.execute(
            text("SELECT count(*) FROM public.run_dataset_inputs WHERE run_id=:run"),
            {"run": run_id},
        ).scalar_one()
    assert row.status == "RUNNING"
    assert row.inputs_sealed_at is not None
    assert row.started_at is not None
    assert row.row_version == 2
    assert child_count == 0
