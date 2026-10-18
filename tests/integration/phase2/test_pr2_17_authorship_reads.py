"""Exact reads use a read-only MVCC snapshot while writers retain their lock order."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event, get_ident
from uuid import uuid4

import pytest
from sqlalchemy import event, text

from researchbase.application.authorship import GetAuthorshipSnapshotQuery, GetContributionQuery
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.authorship_repository import SqlAlchemyAuthorshipRepository
from tests.integration.phase2.test_pr2_00_ownership import _add_owner
from tests.integration.phase2.test_pr2_17_authorship import (
    _record,
    _snapshot,
)
from tests.integration.phase2.test_pr2_17_authorship import (
    authorship_env as _env,
)
from tests.integration.phase2.test_pr2_17_authorship import (
    authorship_url as _url,
)
from tests.integration.phase2.test_pr2_17_authorship_concurrency import _past_expiry

pytestmark = pytest.mark.integration
authorship_env = _env
authorship_url = _url


@pytest.mark.parametrize("snapshot", [False, True])
@pytest.mark.parametrize("expire", [False, True])
def test_exact_reads_snapshot_first_no_locks_and_final_credential_check(
    authorship_env, monkeypatch, snapshot, expire
):
    """MVCC replaces read locks: writers commit and final credentials still use fresh time."""
    env = authorship_env
    service, _, engine, credentials, principal, project, publication = env
    other = uuid4()
    with engine.begin() as conn:
        # Retiring the reader must retain the project's required OWNER coverage.
        _add_owner(
            conn,
            actor_id=uuid4(),
            project_id=project,
            now=conn.execute(text("SELECT clock_timestamp()")).scalar_one(),
            event_kind="ACTIVATED",
            request_id=uuid4(),
        )
        conn.execute(
            text(
                "INSERT INTO actors(id,actor_type,display_name,created_at) "
                "VALUES (:id,'HUMAN','TEST ONLY coauthor',clock_timestamp())"
            ),
            {"id": other},
        )
    first = service.record_contribution(principal, _record(env))
    second = service.record_contribution(principal, _record(env, actor_id=other))
    saved = service.create_authorship_snapshot(
        principal,
        _snapshot(
            env,
            (first.id, second.id),
            author_ids=(principal.actor_id, other),
            corresponding_author_ids=(principal.actor_id, other),
            equal_contribution_groups=((principal.actor_id, other),),
        ),
    )
    expected = saved if snapshot else first
    ready, release = Event(), Event()
    trace = {"thread": None, "pid": None, "checks": []}
    statements = []
    lock_observations = []

    def capture(conn, cursor, statement, parameters, context, executemany):
        if get_ident() == trace["thread"]:
            statements.append(statement)

    def observe_locks():
        # Inspect from another backend, including after all relation reads have run.
        with engine.connect() as observer:
            assert observer.execute(text("SELECT pg_backend_pid()")).scalar_one() != trace["pid"]
            locks = observer.execute(
                text("SELECT locktype,mode,granted FROM pg_locks WHERE pid=:pid"),
                {"pid": trace["pid"]},
            ).all()
        relations = [row for row in locks if row.locktype == "relation"]
        assert relations and all(row.mode == "AccessShareLock" and row.granted for row in relations)
        assert all(row.locktype in {"relation", "virtualxid"} for row in locks)
        lock_observations.append(locks)

    method_name = "snapshot" if snapshot else "contribution"
    original = getattr(SqlAlchemyAuthorshipRepository, method_name)
    paused = False

    def pause_after_parent(repo, identity):
        nonlocal paused
        row = original(repo, identity)
        if identity == expected.id and not paused:
            paused = True
            trace["pid"] = repo._session.execute(text("SELECT pg_backend_pid()")).scalar_one()
            assert repo._session.execute(text("SHOW transaction_isolation")).scalar_one() == (
                "repeatable read"
            )
            assert repo._session.execute(text("SHOW transaction_read_only")).scalar_one() == "on"
            ready.set()
            assert release.wait(10)
            # The writer's committed retirement must stay outside the entire read,
            # including snapshot relation reconstruction and final authorization.
            assert repo.actor(principal.actor_id)["retired_at"] is None
        return row

    monkeypatch.setattr(SqlAlchemyAuthorshipRepository, method_name, pause_after_parent)
    authorize = service._authorize

    def checked(repo, caller, scope, roles):
        trace["checks"].append(repo.at())
        if len(trace["checks"]) == 2:
            observe_locks()
        return authorize(repo, caller, scope, roles)

    monkeypatch.setattr(service, "_authorize", checked)

    def read():
        trace["thread"] = get_ident()
        if snapshot:
            return service.get_authorship_snapshot(
                principal, GetAuthorshipSnapshotQuery(project, saved.id)
            )
        return service.get_contribution(principal, GetContributionQuery(project, first.id))

    event.listen(engine, "before_cursor_execute", capture)
    try:
        with engine.connect() as writer:
            transaction = writer.begin()
            try:
                writer.execute(text("SET LOCAL lock_timeout='1s'"))
                writer.execute(text("SET LOCAL statement_timeout='3s'"))
                writer_pid = writer.execute(text("SELECT pg_backend_pid()")).scalar_one()
                # Hold the exact Publication and both immutable authorship parents
                # before the read starts; no read should wait on any of them.
                for table, identity in (
                    ("publications", publication),
                    ("contribution_records", first.id),
                    ("authorship_snapshots", saved.id),
                ):
                    writer.execute(
                        text(f"SELECT id FROM {table} WHERE id=:id FOR UPDATE"), {"id": identity}
                    )
                with ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(read)
                    try:
                        assert ready.wait(10)
                        assert writer_pid != trace["pid"]
                        observe_locks()
                        writer.execute(
                            text("UPDATE actors SET retired_at=clock_timestamp() WHERE id=:id"),
                            {"id": principal.actor_id},
                        )
                        transaction.commit()
                        with engine.connect() as observer:
                            assert (
                                observer.execute(
                                    text("SELECT retired_at FROM actors WHERE id=:id"),
                                    {"id": principal.actor_id},
                                ).scalar_one()
                                is not None
                            )
                            if expire:
                                credentials.expires = observer.execute(
                                    text("SELECT clock_timestamp()")
                                ).scalar_one()
                        if expire:
                            _past_expiry(engine, credentials.expires)
                        assert not future.done()  # Writer committed while the read was paused.
                    finally:
                        release.set()
                    if expire:
                        with pytest.raises(ResearchBaseError) as error:
                            future.result(10)
                        assert error.value.code is ErrorCode.AUTHENTICATION_REQUIRED
                        assert trace["checks"][0] < credentials.expires < trace["checks"][-1]
                    else:
                        assert future.result(10) == expected  # Every DTO field and hash is old.
            finally:
                if transaction.is_active:
                    transaction.rollback()
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    assert len(trace["checks"]) == 2
    assert len(lock_observations) == 2
    # Capturing starts before UoW entry; SET TRANSACTION also rejects an earlier query snapshot.
    assert statements[0] == "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"
    assert statements.count(statements[0]) == 1
    for statement in statements:
        sql = " ".join(statement.upper().split())
        assert not any(
            forbidden in sql
            for forbidden in (
                "LOCK TABLE",
                "PG_ADVISORY",
                "FOR SHARE",
                "FOR UPDATE",
                "FOR KEY SHARE",
            )
        )
