"""Actual backend waits for terminal selection and mutable validity ranges."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Event, get_ident
from uuid import uuid4

import psycopg
import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import OperationalError

from researchbase.application.novelty import ExactReadQuery, NoveltyReadback
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.novelty_repository import N, SqlAlchemyNoveltyRepository
from researchbase.persistence.uow import SqlAlchemyUnitOfWork
from tests.integration.phase2.b19_basis_support import record, setup
from tests.integration.phase2.pr2_18_fixtures import add_resolution
from tests.integration.phase2.test_pr2_18_concurrency import _witness

pytest_plugins = ("tests.integration.phase2.pr2_18_fixtures",)


def outcome(call):
    try:
        return call()
    except ResearchBaseError as exc:
        return exc.code


@pytest.mark.parametrize("correction_first", [False, True])
def test_b22_b19_both_claim_lock_orders(novelty_env, monkeypatch, correction_first):
    e = novelty_env
    c, rc, relation, _ = setup(e)
    ready, release = Event(), Event()
    original = SqlAlchemyNoveltyRepository.prepare
    pids = []
    first_kind = "prior_art" if correction_first else "novelty"

    def pause(repo, kind, *args):
        original(repo, kind, *args)
        if kind == first_kind:
            pids.append(repo._session.execute(text("SELECT pg_backend_pid()")).scalar_one())
            ready.set()
            assert release.wait(10)

    monkeypatch.setattr(SqlAlchemyNoveltyRepository, "prepare", pause)

    def correction():
        return e["service"].record_prior_art_relation(
            e["author"], replace(rc, id=uuid4(), supersedes_prior_art_relation_id=relation.id)
        )

    def assessment():
        return outcome(lambda: record(e, c))

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(correction if correction_first else assessment)
        assert ready.wait(10)
        second = pool.submit(assessment if correction_first else correction)
        try:
            _witness(e["race_engine"], pids[0])
        finally:
            release.set()
        a, b = first.result(timeout=15), second.result(timeout=15)
    if correction_first:
        assert b is ErrorCode.INVALID_STATE_TRANSITION
    else:
        assert isinstance(a, NoveltyReadback)
        assert a.id == c.id
        read = e["service"].read_novelty_assessment(e["author"], ExactReadQuery(e["project"], c.id))
        assert (
            read.content_hash == a.content_hash
            and not read.current_validity.usable_for_current_judgment
        )


@pytest.mark.parametrize("assessment_first", [False, True])
@pytest.mark.parametrize("change", ["resolution", "evidence", "source"])
def test_mutable_closure_both_commit_orders(novelty_env, monkeypatch, assessment_first, change):
    e = novelty_env
    c, _, _, _ = setup(e)
    ready, release = Event(), Event()
    pids = []
    writer_thread = []
    original = SqlAlchemyUnitOfWork.commit
    source_service = source_command = None
    if change == "source":
        from researchbase.domain.source_version import SourceVersionKind
        from tests.integration.phase2.b19_basis_support import source_change

        source_service, source_command = source_change(e, SourceVersionKind.RETRACTED)
    original_force = SqlAlchemyNoveltyRepository.force_constraints

    def pause_commit(uow):
        if writer_thread and get_ident() == writer_thread[0] and not assessment_first:
            pids.append(uow._session.execute(text("SELECT pg_backend_pid()")).scalar_one())
            ready.set()
            assert release.wait(10)
        original(uow)

    def pause_force(repo):
        original_force(repo)
        if assessment_first:
            pids.append(repo._session.execute(text("SELECT pg_backend_pid()")).scalar_one())
            ready.set()
            assert release.wait(10)

    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", pause_commit)
    monkeypatch.setattr(SqlAlchemyNoveltyRepository, "force_constraints", pause_force)

    def change_validity():
        writer_thread.append(get_ident())
        if change == "source":
            assert source_service is not None and source_command is not None
            return source_service.freeze(source_command)
        if change == "evidence":
            return e["literature"].review(
                e["reviewer"], e["project"], e["evidence"], "DISPUTED", "New dispute", uuid4()
            )
        with e["race_engine"].connect() as conn:
            # No additional resolution exists at admission's range check.
            add_resolution(e, e["results"][0], version=False, connection=conn)
            if not assessment_first:
                pids.append(conn.execute(text("SELECT pg_backend_pid()")).scalar_one())
                ready.set()
                assert release.wait(10)
            conn.commit()

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = (
            pool.submit(lambda: outcome(lambda: record(e, c)))
            if assessment_first
            else pool.submit(change_validity)
        )
        assert ready.wait(10)
        second = (
            pool.submit(change_validity)
            if assessment_first
            else pool.submit(lambda: outcome(lambda: record(e, c)))
        )
        try:
            _witness(e["race_engine"], pids[0])
        finally:
            release.set()
        a, b = first.result(timeout=15), second.result(timeout=15)
    if assessment_first:
        assert isinstance(a, NoveltyReadback)
        read = e["service"].read_novelty_assessment(e["author"], ExactReadQuery(e["project"], c.id))
        assert (
            read.content_hash == a.content_hash
            and not read.current_validity.usable_for_current_judgment
        )
    else:
        assert b is (
            ErrorCode.PROVENANCE_CLOSURE_VIOLATION
            if change in {"resolution", "source"}
            else ErrorCode.INVALID_STATE_TRANSITION
        )


def test_same_uuid_and_single_predecessor(novelty_env):
    e = novelty_env
    c, _, _, _ = setup(e)
    with ThreadPoolExecutor(max_workers=2) as pool:
        saved = [pool.submit(record, e, c) for _ in range(2)]
        assert len({f.result(timeout=15).content_hash for f in saved}) == 1
    c = replace(c, id=uuid4(), supersedes_assessment_id=c.id)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [
            pool.submit(lambda command: outcome(lambda: record(e, command)), x)
            for x in (c, replace(c, id=uuid4()))
        ]
        values = [f.result(timeout=15) for f in results]
    assert sum(x is ErrorCode.INVALID_STATE_TRANSITION for x in values) == 1


@pytest.mark.parametrize(
    "state,cls,count",
    [
        ("40001", psycopg.errors.SerializationFailure, 3),
        ("40P01", psycopg.errors.DeadlockDetected, 3),
        ("55P03", psycopg.errors.LockNotAvailable, 1),
        ("57014", psycopg.errors.QueryCanceled, 1),
    ],
)
def test_retry_normalization(novelty_env, monkeypatch, state, cls, count):
    e = novelty_env
    c, _, _, _ = setup(e)
    calls = []

    def injected(repo, *args):
        calls.append(repo)
        raise OperationalError("injected", {}, cls("injected"))

    monkeypatch.setattr(SqlAlchemyNoveltyRepository, "insert", injected)
    if state in {"55P03", "57014"}:
        # Approved B20 §11.2: timeouts use the sanitized INTERNAL_ERROR fallback.
        with pytest.raises(RuntimeError, match="novelty transaction timeout"):
            record(e, c)
    else:
        assert outcome(lambda: record(e, c)) is ErrorCode.CONCURRENT_MODIFICATION
    assert len(calls) == count and len({id(x) for x in calls}) == count


def test_read_snapshot_no_explicit_locks_and_first_write_inventory(novelty_env, monkeypatch):
    e = novelty_env
    c, rc, relation, _ = setup(e)
    statements = []

    def capture(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(e["engine"], "before_cursor_execute", capture)
    try:
        record(e, c)
    finally:
        event.remove(e["engine"], "before_cursor_execute", capture)
    assert statements[0] == "LOCK TABLE " + ",".join(N) + " IN SHARE MODE"
    assert "pg_advisory_xact_lock" in statements[3] and "FOR UPDATE" in statements[4]
    ready, release = Event(), Event()
    original = SqlAlchemyNoveltyRepository.basis

    def pause(repo, identity):
        rows = original(repo, identity)
        if repo._session.execute(text("SHOW transaction_read_only")).scalar_one() == "on":
            assert (
                repo._session.execute(text("SHOW transaction_isolation")).scalar_one()
                == "repeatable read"
            )
            ready.set()
            assert release.wait(10)
        return rows

    monkeypatch.setattr(SqlAlchemyNoveltyRepository, "basis", pause)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(
            e["service"].read_novelty_assessment, e["author"], ExactReadQuery(e["project"], c.id)
        )
        assert ready.wait(10)
        try:
            e["service"].record_prior_art_relation(
                e["author"], replace(rc, id=uuid4(), supersedes_prior_art_relation_id=relation.id)
            )
        finally:
            release.set()
        assert future.result(timeout=15).current_validity.usable_for_current_judgment
    statements = []
    event.listen(e["engine"], "before_cursor_execute", capture)
    try:
        read = e["service"].read_novelty_assessment(e["author"], ExactReadQuery(e["project"], c.id))
    finally:
        event.remove(e["engine"], "before_cursor_execute", capture)
    assert not read.current_validity.usable_for_current_judgment
    assert not any(
        "FOR UPDATE" in x
        or "FOR SHARE" in x
        or "LOCK TABLE" in x
        or "pg_advisory" in x
        or x.startswith(("INSERT ", "UPDATE ", "DELETE "))
        for x in statements
    )


@pytest.mark.parametrize("stage", ["insert_child", "force_constraints"])
def test_failure_rolls_back_parent_and_basis(novelty_env, monkeypatch, stage):
    e = novelty_env
    c, _, _, _ = setup(e)

    def injected(*args):
        raise RuntimeError("injected")

    monkeypatch.setattr(SqlAlchemyNoveltyRepository, stage, injected)
    with pytest.raises(RuntimeError):
        record(e, c)
    with e["engine"].connect() as conn:
        for table in ("novelty_assessments", "novelty_assessment_prior_art_inputs"):
            assert conn.execute(text("SELECT count(*) FROM " + table)).scalar_one() == 0


def test_commit_uncertainty_exact_uuid_recovery(novelty_env, monkeypatch):
    e = novelty_env
    c, _, _, _ = setup(e)
    original = SqlAlchemyUnitOfWork.commit
    calls = []

    def uncertain(uow):
        original(uow)
        calls.append(True)
        raise OperationalError("uncertain", {}, psycopg.OperationalError("connection lost"))

    with monkeypatch.context() as patcher:
        patcher.setattr(SqlAlchemyUnitOfWork, "commit", uncertain)
        with pytest.raises(RuntimeError):
            record(e, c)
    assert calls == [True]
    assert record(e, c).id == c.id


def test_post_claim_wait_credential_expiry(novelty_env):
    from datetime import timedelta
    from time import monotonic

    e = novelty_env
    c, _, _, _ = setup(e)
    with e["race_engine"].connect() as holder:
        holder.execute(
            text("SELECT id FROM claim_versions WHERE id=:id FOR UPDATE"), {"id": e["claim"]}
        )
        pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
        expires = holder.execute(text("SELECT clock_timestamp()")).scalar_one() + timedelta(
            seconds=1
        )
        e["credentials"].expires_at = expires
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(lambda: outcome(lambda: record(e, c)))
            _witness(e["race_engine"], pid, expires)
            deadline = monotonic() + 3
            while holder.execute(text("SELECT clock_timestamp()")).scalar_one() < expires:
                assert monotonic() < deadline
                Event().wait(0.01)
            holder.commit()
            assert future.result(timeout=10) is ErrorCode.FORBIDDEN
    with e["engine"].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM novelty_assessments")).scalar_one() == 0
