"""Observable correction coordination, snapshot reads and exact recovery."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Event
from uuid import uuid4

import psycopg
import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import OperationalError

from researchbase.application.novelty import ExactReadQuery
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.novelty_repository import N, SqlAlchemyNoveltyRepository
from tests.integration.phase2.test_b22_prior_art_correction import record, request
from tests.integration.phase2.test_b22_prior_art_selection import select
from tests.integration.phase2.test_pr2_18_concurrency import _witness

pytest_plugins = ("tests.integration.phase2.pr2_18_fixtures",)


@pytest.mark.parametrize("replay", [False, True])
def test_first_sql_lock_inventory_and_order(novelty_env, replay):
    e = novelty_env
    root = record(e, request(e))
    c = request(e, supersedes_prior_art_relation_id=root.id)
    if replay:
        record(e, c)
    statements = []

    def capture(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(e["engine"], "before_cursor_execute", capture)
    try:
        record(e, c)
    finally:
        event.remove(e["engine"], "before_cursor_execute", capture)
    assert statements[0] == "LOCK TABLE " + ",".join(N) + " IN SHARE MODE"
    assert statements[1:3] == ["SET LOCAL lock_timeout='10s'", "SET LOCAL statement_timeout='30s'"]
    assert "pg_advisory_xact_lock" in statements[3]
    assert statements[4] == "SELECT id FROM claim_versions WHERE id=%(id)s FOR UPDATE"
    if not replay:
        index = statements.index("SELECT id FROM prior_art_relations WHERE id=%(id)s FOR UPDATE")
        assert index > 4


def test_two_corrections_one_winner_with_observed_claim_wait(novelty_env, monkeypatch):
    e = novelty_env
    root = record(e, request(e))
    c = request(e, supersedes_prior_art_relation_id=root.id)
    ready, release = Event(), Event()
    original = SqlAlchemyNoveltyRepository.prior_art_predecessor
    pids = []

    def pause(repo, identity):
        result = original(repo, identity)
        pids.append(repo._session.execute(text("SELECT pg_backend_pid()")).scalar_one())
        ready.set()
        assert release.wait(10)
        return result

    monkeypatch.setattr(SqlAlchemyNoveltyRepository, "prior_art_predecessor", pause)

    def loser():
        with pytest.raises(ResearchBaseError) as error:
            record(e, replace(c, id=uuid4()))
        return error.value.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        winner = pool.submit(record, e, c)
        assert ready.wait(10)
        other = pool.submit(loser)
        try:
            _witness(e["race_engine"], pids[0])
        finally:
            release.set()
        assert winner.result(timeout=10).supersedes_prior_art_relation.id == root.id
        assert other.result(timeout=10) is ErrorCode.INVALID_STATE_TRANSITION
    with e["engine"].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM prior_art_relations")).scalar_one() == 2


def test_same_correction_uuid_one_parent_child_set(novelty_env):
    e = novelty_env
    root = record(e, request(e))
    c = request(e, supersedes_prior_art_relation_id=root.id)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [pool.submit(record, e, c) for _ in range(2)]
        assert len({f.result(timeout=15).content_hash for f in results}) == 1
    with e["engine"].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM prior_art_relations")).scalar_one() == 2
        assert (
            conn.execute(text("SELECT count(*) FROM prior_art_evidence_inputs")).scalar_one() == 2
        )


@pytest.mark.parametrize("selection", [False, True])
@pytest.mark.parametrize("append_root", [False, True])
def test_read_snapshot_unrelated_actor_and_concurrent_correction(
    novelty_env, monkeypatch, selection, append_root
):
    e = novelty_env
    root = record(e, request(e))
    ready, release = Event(), Event()
    original = (
        SqlAlchemyNoveltyRepository.prior_art_pair
        if selection
        else SqlAlchemyNoveltyRepository.parent
    )
    pids = []

    def pause(repo, *args):
        result = original(repo, *args)
        if selection or args == ("prior_art", root.id):
            assert (
                repo._session.execute(text("SHOW transaction_isolation")).scalar_one()
                == "repeatable read"
            )
            assert repo._session.execute(text("SHOW transaction_read_only")).scalar_one() == "on"
            pids.append(repo._session.execute(text("SELECT pg_backend_pid()")).scalar_one())
            ready.set()
            assert release.wait(10)
        return result

    monkeypatch.setattr(
        SqlAlchemyNoveltyRepository, "prior_art_pair" if selection else "parent", pause
    )
    # Only pause the reader thread, never the concurrent command's readback.
    original_author = e["author"]

    def operation():
        return (
            select(e)
            if selection
            else e["service"].read_prior_art_relation(
                original_author, ExactReadQuery(e["project"], root.id)
            )
        )

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(operation)
        assert ready.wait(10)
        monkeypatch.setattr(
            SqlAlchemyNoveltyRepository, "prior_art_pair" if selection else "parent", original
        )
        try:
            with e["race_engine"].begin() as writer:
                assert writer.execute(text("SELECT pg_backend_pid()")).scalar_one() != pids[0]
                writer.execute(text("SET LOCAL lock_timeout='1s'"))
                writer.execute(
                    text(
                        "INSERT INTO actors (id,actor_type,display_name,created_at) "
                        "VALUES (:id,'HUMAN','Unrelated',clock_timestamp())"
                    ),
                    {"id": uuid4()},
                )
            correction = record(
                e, request(e, supersedes_prior_art_relation_id=None if append_root else root.id)
            )
            assert not future.done()
        finally:
            release.set()
        saved = future.result(timeout=10)
    if selection:
        assert saved.selected_prior_art_relation_id == root.id
        if append_root:
            assert select(e).selected_prior_art_relation_id is None
            assert len(select(e).chains) == 2
        else:
            assert select(e).selected_prior_art_relation_id == correction.id
    else:
        assert saved.superseded_by_prior_art_relation_id is None


@pytest.mark.parametrize(
    "state,error_type,attempts",
    [
        ("40001", psycopg.errors.SerializationFailure, 3),
        ("40P01", psycopg.errors.DeadlockDetected, 3),
        ("55P03", psycopg.errors.LockNotAvailable, 1),
        ("57014", psycopg.errors.QueryCanceled, 1),
    ],
)
def test_retry_inventory(novelty_env, monkeypatch, state, error_type, attempts):
    e = novelty_env
    root = record(e, request(e))
    calls = []

    def injected(repo, *args):
        calls.append(repo)
        raise OperationalError("injected", {}, error_type("injected"))

    monkeypatch.setattr(SqlAlchemyNoveltyRepository, "insert", injected)
    with pytest.raises(ResearchBaseError) as error:
        record(e, request(e, supersedes_prior_art_relation_id=root.id))
    assert error.value.code is ErrorCode.CONCURRENT_MODIFICATION
    assert len(calls) == attempts and len({id(r) for r in calls}) == attempts
    assert error.value.details is None


@pytest.mark.parametrize("stage", ["request", "claim", "predecessor", "deferred"])
@pytest.mark.parametrize("authority", ["credential", "role"])
def test_database_clock_expiry_across_correction_waits(novelty_env, monkeypatch, stage, authority):
    e = novelty_env
    root = record(e, request(e))
    c = request(e, supersedes_prior_art_relation_id=root.id)
    clocks = []
    original_at = SqlAlchemyNoveltyRepository.at

    def at(repo):
        result = original_at(repo)
        clocks.append(result)
        return result

    monkeypatch.setattr(SqlAlchemyNoveltyRepository, "at", at)
    with e["race_engine"].connect() as holder:
        expiry = holder.execute(text("SELECT clock_timestamp()+interval '1 second'")).scalar_one()
        principal = e["author"] if authority == "credential" else e["researcher"]
        if authority == "credential":
            e["credentials"].expires_at = expiry
        else:
            with e["engine"].begin() as role_conn:
                role = role_conn.execute(
                    text("""UPDATE project_role_assignments
                    SET effective_until=:expiry,row_version=row_version+1
                    WHERE actor_id=:actor AND role='RESEARCHER' RETURNING id"""),
                    {"expiry": expiry, "actor": principal.actor_id},
                ).scalar_one()
                role_conn.execute(
                    text("""INSERT INTO project_role_events
                    (id,role_assignment_id,actor_id,event_kind,occurred_at,reason,request_id)
                    VALUES (:id,:role,:actor,'CLOSED',:expiry,'Scheduled expiry',:request)"""),
                    {
                        "id": uuid4(),
                        "role": role,
                        "actor": principal.actor_id,
                        "expiry": expiry,
                        "request": uuid4(),
                    },
                )
        if stage == "request":
            holder.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
                {"key": f"pr218:prior_art:{c.id}"},
            )
        elif stage == "claim":
            holder.execute(
                text("SELECT id FROM claim_versions WHERE id=:id FOR UPDATE"), {"id": e["claim"]}
            )
        elif stage == "predecessor":
            holder.execute(
                text("SELECT id FROM prior_art_relations WHERE id=:id FOR UPDATE"), {"id": root.id}
            )
        else:
            # Wait after constraint forcing, before final authorization.
            holder.execute(text("SELECT pg_advisory_xact_lock(9220017)"))
            original = SqlAlchemyNoveltyRepository.force_constraints

            def deferred(repo):
                original(repo)
                repo._session.execute(text("SELECT pg_advisory_xact_lock(9220017)"))

            monkeypatch.setattr(SqlAlchemyNoveltyRepository, "force_constraints", deferred)
        pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()

        def denied():
            with pytest.raises(ResearchBaseError) as error:
                record(e, c, principal)
            return error.value.code

        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(denied)
            try:
                _witness(e["engine"], pid, before=expiry)
                with e["engine"].connect() as observer:
                    while observer.execute(text("SELECT clock_timestamp()")).scalar_one() <= expiry:
                        Event().wait(0.01)
            finally:
                holder.commit()
            assert future.result(timeout=10) is ErrorCode.FORBIDDEN
        assert max(clocks) >= expiry
    with e["engine"].connect() as conn:
        assert (
            conn.execute(
                text("SELECT count(*) FROM prior_art_relations WHERE id=:id"), {"id": c.id}
            ).scalar_one()
            == 0
        )


def test_uncertain_commit_exact_recovery(novelty_env, monkeypatch):
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork

    e = novelty_env
    root = record(e, request(e))
    c = request(e, supersedes_prior_art_relation_id=root.id)
    original = SqlAlchemyUnitOfWork.commit
    calls = []

    def uncertain(uow):
        original(uow)
        calls.append(uow)
        raise RuntimeError("commit acknowledgement lost")

    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", uncertain)
    with pytest.raises(RuntimeError):
        record(e, c)
    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", original)
    recovered = e["service"].read_prior_art_relation(
        e["author"], ExactReadQuery(e["project"], c.id)
    )
    assert record(e, c).content_hash == recovered.content_hash
    assert len(calls) == 1


def test_revocation_during_initial_share_wait(novelty_env):
    e = novelty_env
    root = record(e, request(e))
    c = request(e, supersedes_prior_art_relation_id=root.id)
    with e["race_engine"].connect() as holder:
        holder.execute(
            text("UPDATE actors SET retired_at=clock_timestamp() WHERE id=:id"),
            {"id": e["researcher"].actor_id},
        )
        pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()

        def denied():
            with pytest.raises(ResearchBaseError) as error:
                record(e, c, e["researcher"])
            return error.value.code

        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(denied)
            try:
                _witness(e["engine"], pid)
            finally:
                holder.commit()
            assert future.result(timeout=10) is ErrorCode.FORBIDDEN


@pytest.mark.parametrize(
    "name,state,expected",
    [
        ("ck_b22_prior_art_material", "23514", ErrorCode.PROVENANCE_CLOSURE_VIOLATION),
        ("ck_b22_prior_art_not_self", "23514", ErrorCode.PROVENANCE_CLOSURE_VIOLATION),
        ("fk_b22_prior_art_predecessor", "23503", ErrorCode.PROVENANCE_CLOSURE_VIOLATION),
        ("uq_b22_prior_art_predecessor", "23505", ErrorCode.CONCURRENT_MODIFICATION),
        ("unrelated_fk", "23503", ErrorCode.REFERENTIAL_INTEGRITY_ERROR),
    ],
)
def test_named_denials_are_not_retried(novelty_env, monkeypatch, name, state, expected):
    from types import SimpleNamespace

    e = novelty_env
    root = record(e, request(e))
    calls = []

    class Denial(Exception):
        sqlstate = state
        diag = SimpleNamespace(constraint_name=name)

    def inserted(repo, *args):
        calls.append(repo)
        raise OperationalError("injected", {}, Denial("private SQL"))

    monkeypatch.setattr(SqlAlchemyNoveltyRepository, "insert", inserted)
    with pytest.raises(ResearchBaseError) as error:
        record(e, request(e, supersedes_prior_art_relation_id=root.id))
    assert error.value.code is expected and len(calls) == 1
    assert error.value.details is None and "private SQL" not in error.value.message
