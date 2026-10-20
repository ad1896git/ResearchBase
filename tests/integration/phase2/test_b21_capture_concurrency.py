"""Observed membership races, one snapshot, first SQL and uncertain commit replay."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Event
from uuid import uuid4

import pytest
from psycopg.errors import DeadlockDetected, LockNotAvailable, SerializationFailure
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker

from researchbase.application.search_result_resolution import SearchResultResolutionService
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.novelty_repository import N, SqlAlchemyNoveltyRepository
from researchbase.persistence.search_result_resolution_repository import (
    SqlAlchemySearchResultResolutionRepository,
)
from researchbase.persistence.uow import SqlAlchemyUnitOfWork
from tests.integration.phase2.b18_novelty_support import invoke, resolve_remaining
from tests.integration.phase2.b30_observations import (
    assert_first_share,
    assert_snapshot_read,
    sql_protocol,
)
from tests.integration.phase2.test_pr2_18_concurrency import _witness


def race_resolution(e):
    sf = sessionmaker(e["race_engine"], expire_on_commit=False, autoflush=False)
    service = SearchResultResolutionService(
        lambda: SqlAlchemyUnitOfWork(sf), e["credentials"], e["store"]
    )
    return dict(e, resolution=dict(e["resolution"], service=service))


@pytest.mark.parametrize("writer_first", [False, True])
def test_resolution_membership_both_lock_orders(b18_env, monkeypatch, writer_first):
    e = b18_env
    other = race_resolution(e)
    c = replace(e["commands"]["coverage"], id=uuid4())
    ready, release = Event(), Event()
    pids = []
    target = (
        SqlAlchemySearchResultResolutionRepository if writer_first else SqlAlchemyNoveltyRepository
    )
    method = "insert" if writer_first else "force_constraints"
    original = getattr(target, method)

    def pause(repo, *args):
        result = original(repo, *args)
        pids.append(repo._session.execute(text("SELECT pg_backend_pid()")).scalar_one())
        ready.set()
        assert release.wait(15)
        return result

    monkeypatch.setattr(target, method, pause)
    with ThreadPoolExecutor(max_workers=2) as pool:

        def capture():
            return e["service"].record_search_coverage(e["author"], c)

        a = pool.submit(resolve_remaining, other) if writer_first else pool.submit(capture)
        assert ready.wait(15)
        b = pool.submit(capture) if writer_first else pool.submit(resolve_remaining, other)
        try:
            waiter = _witness(e["engine"], pids[0])
            assert waiter != pids[0]
        finally:
            release.set()
        av, bv = a.result(timeout=15), b.result(timeout=15)
    captured = bv if writer_first else av
    assert captured.quality.captured_unresolved_result_count == (0 if writer_first else 1)
    saved = invoke(e, "coverage", "read", command=c)
    assert saved.content_hash == captured.content_hash
    assert saved.quality.current_unresolved_result_count == 0
    assert saved.quality.captured_unresolved_result_count == (0 if writer_first else 1)
    with e["engine"].connect() as conn:
        assert conn.execute(
            text("SELECT count(*) FROM search_coverage_resolutions WHERE search_coverage_id=:id"),
            {"id": c.id},
        ).scalar_one() == (2 if writer_first else 1)


def test_reader_does_not_block_resolution_and_retains_snapshot(b18_env, monkeypatch):
    e = b18_env
    other = race_resolution(e)
    ready, release = Event(), Event()
    original = SqlAlchemyNoveltyRepository.parent

    def pause(repo, kind, identity):
        row = original(repo, kind, identity)
        if kind == "coverage":
            ready.set()
            assert release.wait(10)
        return row

    monkeypatch.setattr(SqlAlchemyNoveltyRepository, "parent", pause)
    with sql_protocol(e["engine"]) as observed, ThreadPoolExecutor(max_workers=1) as pool:
        reader = pool.submit(invoke, e, "coverage", "read")
        try:
            assert ready.wait(10)
            resolve_remaining(other)
            assert not reader.done()
        finally:
            release.set()
        value = reader.result(timeout=10)
    assert_snapshot_read(observed, snapshots=1)
    assert value.quality.current_unresolved_result_count == 1
    assert value.quality.captured_unresolved_result_count == 1
    assert invoke(e, "coverage", "read").quality.current_unresolved_result_count == 0


@pytest.mark.parametrize("kind", ["coverage", "prior_art", "novelty"])
def test_first_sql_and_lock_free_reads(b18_env, kind):
    e = b18_env
    for operation in ("first", "replay"):
        command = (
            replace(e["commands"][kind], id=uuid4())
            if operation == "first"
            else e["commands"][kind]
        )
        with sql_protocol(e["engine"]) as observed:
            invoke(e, kind, operation, command=command)
        assert_first_share(observed, "LOCK TABLE " + ",".join(N) + " IN SHARE MODE")
    with sql_protocol(e["engine"]) as observed:
        invoke(e, kind, "read")
    assert_snapshot_read(observed, snapshots=1)


@pytest.mark.parametrize(
    "failure", [SerializationFailure, DeadlockDetected, LockNotAvailable, ResearchBaseError]
)
def test_retry_scope_for_membership_failure(b18_env, monkeypatch, failure):
    e = b18_env
    calls = []
    original = SqlAlchemyNoveltyRepository.insert_child

    def fail(repo, kind, values):
        if kind == "coverage_resolution":
            calls.append(repo)
            if failure is ResearchBaseError:
                raise ResearchBaseError(ErrorCode.CONCURRENT_MODIFICATION, "business conflict")
            raise DBAPIError("private SQL", {}, failure("private detail"), False)
        return original(repo, kind, values)

    monkeypatch.setattr(SqlAlchemyNoveltyRepository, "insert_child", fail)
    c = replace(e["commands"]["coverage"], id=uuid4())
    with pytest.raises((ResearchBaseError, RuntimeError)) as error:
        invoke(e, "coverage", "first", command=c)
    assert "private" not in str(error.value)
    expected = 3 if failure in (SerializationFailure, DeadlockDetected) else 1
    assert len(calls) == len({id(r) for r in calls}) == expected
    with e["engine"].connect() as conn:
        assert (
            conn.execute(
                text("SELECT count(*) FROM search_coverage WHERE id=:id"), {"id": c.id}
            ).scalar_one()
            == 0
        )


def test_uncertain_commit_same_uuid_replays_one_saved_set(b18_env, monkeypatch):
    e = b18_env
    original = SqlAlchemyUnitOfWork.commit
    calls = []

    def uncertain(uow):
        original(uow)
        calls.append(uow)
        raise RuntimeError("commit result unavailable")

    c = replace(e["commands"]["coverage"], id=uuid4())
    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", uncertain)
    with pytest.raises(RuntimeError):
        invoke(e, "coverage", "first", command=c)
    assert len(calls) == 1
    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", original)
    resolve_remaining(e)
    value = invoke(e, "coverage", "replay", command=c)
    assert value.quality.captured_unresolved_result_count == 1
    assert value.quality.current_unresolved_result_count == 0
    with e["engine"].connect() as conn:
        assert (
            conn.execute(
                text(
                    "SELECT count(*) FROM search_coverage_resolutions WHERE search_coverage_id=:id"
                ),
                {"id": c.id},
            ).scalar_one()
            == 1
        )
