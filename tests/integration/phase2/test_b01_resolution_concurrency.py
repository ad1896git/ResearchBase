"""Observable SHARE waits, snapshot reads, retries and rollback on PostgreSQL."""

from concurrent.futures import ThreadPoolExecutor
from functools import partial
from threading import Event
from time import monotonic
from uuid import uuid4

import pytest
from psycopg.errors import DeadlockDetected, LockNotAvailable, SerializationFailure
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError

from researchbase.application.novelty import ExactReadQuery, RecordSearchCoverageCommand
from researchbase.application.search_result_resolution import ExactResolutionQuery
from researchbase.domain.search_result_resolution import resolution_hash
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.novelty_repository import SqlAlchemyNoveltyRepository
from researchbase.persistence.search_result_resolution_repository import (
    R,
)
from researchbase.persistence.search_result_resolution_repository import (
    SqlAlchemySearchResultResolutionRepository as Repository,
)
from tests.integration.phase2.b01_support import count, record
from tests.integration.phase2.test_pr2_18_concurrency import _witness


def test_first_statement_and_read_only_snapshot_without_explicit_locks(b01_env):
    e = b01_env
    seen = []

    def observe(conn, cursor, statement, parameters, context, executemany):
        seen.append(statement)

    event.listen(Engine, "before_cursor_execute", observe)
    try:
        value = record(e)
        assert seen[0] == "LOCK TABLE " + ",".join(R) + " IN SHARE MODE"
        assert not any("FOR UPDATE" in s.upper() for s in seen)
        seen.clear()
        assert (
            e["service"].get_search_result_resolution(
                e["principal"], ExactResolutionQuery(e["project"], value.id)
            )
            == value
        )
        assert not any(
            "LOCK TABLE" in s.upper()
            or "ADVISORY" in s.upper()
            or "FOR UPDATE" in s.upper()
            or "FOR SHARE" in s.upper()
            for s in seen
        )
    finally:
        event.remove(Engine, "before_cursor_execute", observe)


def test_reader_does_not_block_writer_and_keeps_snapshot(b01_env, monkeypatch):
    e = b01_env
    value = record(e)
    ready, release = Event(), Event()
    original = Repository.exact

    def pause(repo, identity, project):
        row = original(repo, identity, project)
        assert (
            repo._session.execute(text("SHOW transaction_isolation")).scalar_one()
            == "repeatable read"
        )
        assert repo._session.execute(text("SHOW transaction_read_only")).scalar_one() == "on"
        ready.set()
        assert release.wait(10)
        return row

    monkeypatch.setattr(Repository, "exact", pause)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(
            e["service"].get_search_result_resolution,
            e["principal"],
            ExactResolutionQuery(e["project"], value.id),
        )
        try:
            assert ready.wait(10)
            with e["engine"].begin() as writer:
                writer.execute(text("SET LOCAL lock_timeout='1s'"))
                writer.execute(
                    text(
                        "INSERT INTO "
                        "actors(id,actor_type,display_name,created_at) VALUES "
                        "(:id,'HUMAN','Independent writer',clock_timestamp())"
                    ),
                    {"id": uuid4()},
                )
        finally:
            release.set()
        assert future.result(timeout=10) == value


@pytest.mark.parametrize("state", [DeadlockDetected, SerializationFailure])
@pytest.mark.parametrize("exhaust", [False, True])
def test_retry_only_retryable_sqlstates_at_most_three_fresh_uows(
    b01_env, monkeypatch, state, exhaust
):
    e = b01_env
    calls = []
    original = Repository.prepare_write

    def failure(repo, identity):
        calls.append(repo)
        original(repo, identity)
        if exhaust or len(calls) < 3:
            raise DBAPIError("test", {}, state("injected"), False)

    monkeypatch.setattr(Repository, "prepare_write", failure)
    if exhaust:
        with pytest.raises(ResearchBaseError) as error:
            record(e)
        assert error.value.code is ErrorCode.CONCURRENT_MODIFICATION
        assert count(e) == 0
    else:
        record(e)
        assert count(e) == 1
    assert len(calls) == 3 and len({id(r) for r in calls}) == 3


def test_timeout_is_sanitized_and_never_retried(b01_env, monkeypatch):
    calls = []

    def failure(repo, identity):
        calls.append(identity)
        raise DBAPIError("private SQL", {}, LockNotAvailable("private path"), False)

    monkeypatch.setattr(Repository, "prepare_write", failure)
    with pytest.raises(RuntimeError) as error:
        record(b01_env)
    assert len(calls) == 1 and "private" not in str(error.value)
    assert count(b01_env) == 0


@pytest.mark.parametrize("point", ["before", "after", "deferred"])
def test_known_rollback_leaves_no_resolution(b01_env, monkeypatch, point):
    original = Repository.insert

    def failure(repo, row):
        if point != "before":
            original(repo, row)
        if point != "deferred":
            raise RuntimeError("injected rollback")
        repo._session.execute(
            text(
                "DELETE FROM literature_source_project_links WHERE "
                "literature_source_id=:source AND project_id=:project"
            ),
            {"source": row["source_id"], "project": b01_env["project"]},
        )

    monkeypatch.setattr(Repository, "insert", failure)
    with pytest.raises((RuntimeError, ResearchBaseError)):
        record(b01_env)
    assert count(b01_env) == 0


@pytest.mark.parametrize("same_id", [False, True])
def test_concurrent_same_tuple_and_id(b01_env, same_id):
    e = b01_env

    def invoke(identity):
        try:
            return record(e, id=identity)
        except ResearchBaseError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(invoke, e["command"].id)
        b = pool.submit(invoke, e["command"].id if same_id else uuid4())
        values = [a.result(timeout=40), b.result(timeout=40)]
    if same_id:
        assert values[0] == values[1]
    else:
        assert sum(v is ErrorCode.DUPLICATE_CONTENT for v in values) == 1
    assert count(e) == 1


@pytest.mark.parametrize(
    "change", ["archive", "identifier_reject", "credential_expiry", "role_expiry"]
)
def test_fresh_authorization_and_identity_after_observed_initial_wait(b01_env, monkeypatch, change):
    e = b01_env
    if change == "role_expiry":
        from datetime import UTC, datetime

        from tests.integration.phase2.test_pr2_00_ownership import _add_owner

        with e["engine"].begin() as conn:
            _add_owner(
                conn,
                actor_id=uuid4(),
                project_id=e["project"],
                now=datetime.now(UTC),
                event_kind="ACTIVATED",
                request_id=uuid4(),
            )
    samples, acquired = [], []
    original_at, original_prepare = Repository.at, Repository.prepare_write

    def clock(repo):
        at = original_at(repo)
        samples.append(at)
        return at

    def prepare(repo, identity):
        original_prepare(repo, identity)
        acquired.append(original_at(repo))

    monkeypatch.setattr(Repository, "at", clock)
    monkeypatch.setattr(Repository, "prepare_write", prepare)
    with e["engine"].connect() as blocker, ThreadPoolExecutor(max_workers=1) as pool:
        tx = blocker.begin()
        blocker.execute(text("LOCK TABLE projects IN ROW EXCLUSIVE MODE"))
        pid = blocker.execute(text("SELECT pg_backend_pid()")).scalar_one()
        expiry = blocker.execute(text("SELECT clock_timestamp()+interval '1 second'")).scalar_one()
        if change == "credential_expiry":
            original = e["service"]._credentials.is_valid
            monkeypatch.setattr(
                e["service"]._credentials, "is_valid", lambda p, at: at < expiry and original(p, at)
            )
        if change == "role_expiry":
            role = blocker.execute(
                text("""UPDATE project_role_assignments
                SET effective_until=:expiry,row_version=row_version+1
                WHERE actor_id=:actor AND project_id=:project AND role='OWNER' RETURNING id"""),
                {"expiry": expiry, "actor": e["principal"].actor_id, "project": e["project"]},
            ).scalar_one()
            blocker.execute(
                text("""INSERT INTO project_role_events
                (id,role_assignment_id,actor_id,event_kind,occurred_at,reason,request_id)
                VALUES(:id,:role,:actor,'CLOSED',:expiry,'Scheduled B01 role expiry',:request)"""),
                {
                    "id": uuid4(),
                    "role": role,
                    "actor": e["principal"].actor_id,
                    "expiry": expiry,
                    "request": uuid4(),
                },
            )
        future = pool.submit(record, e)
        waiter = _witness(e["engine"], pid, before=expiry)
        assert waiter != pid
        with e["engine"].connect() as observer:
            started, observed = observer.execute(
                text("SELECT xact_start,clock_timestamp() FROM pg_stat_activity WHERE pid=:pid"),
                {"pid": waiter},
            ).one()
        if change == "archive":
            blocker.execute(
                text("UPDATE projects SET lifecycle_status='ARCHIVED' WHERE id=:id"),
                {"id": e["project"]},
            )
        elif change == "identifier_reject":
            # Owning transition and its append-only verification event in this blocking transaction.
            from sqlalchemy.orm import Session

            from researchbase.persistence.source_identity_repository import (
                SqlAlchemySourceIdentityRepository,
            )

            repo = SqlAlchemySourceIdentityRepository(Session(bind=blocker))
            at = blocker.execute(text("SELECT clock_timestamp()")).scalar_one()
            repo.transition_identifier(
                {
                    "id": e["identifier"],
                    "status": "REJECTED",
                    "verified_at": None,
                    "verified_by": None,
                    "basis": None,
                }
            )
            repo.insert_verification_event(
                {
                    "id": uuid4(),
                    "identifier": e["identifier"],
                    "prior": "VERIFIED",
                    "new": "REJECTED",
                    "basis": e["basis"],
                    "actor": e["principal"].actor_id,
                    "at": at,
                    "reason": "Reject while admission waits",
                    "request_id": uuid4(),
                }
            )
        if change in {"credential_expiry", "role_expiry"}:
            deadline = monotonic() + 5
            while blocker.execute(text("SELECT clock_timestamp()")).scalar_one() < expiry:
                assert monotonic() < deadline
                Event().wait(0.01)
        tx.commit()
        with pytest.raises(ResearchBaseError) as error:
            future.result(timeout=15)
    assert error.value.code is (
        ErrorCode.SOURCE_IDENTITY_CONFLICT if change == "identifier_reject" else ErrorCode.FORBIDDEN
    )
    assert count(e) == 0
    assert samples and acquired and samples[0] >= acquired[0]
    if change in {"credential_expiry", "role_expiry"}:
        assert started < expiry and observed < expiry <= acquired[0] <= samples[0]
        print(
            "B01_EXPIRY_WITNESS",
            dict(
                case=change,
                transaction_started_at=started.isoformat(),
                wait_observed_at=observed.isoformat(),
                expiry_at=expiry.isoformat(),
                lock_acquired_at=acquired[0].isoformat(),
                authorization_checked_at=samples[0].isoformat(),
                resolution_count=count(e),
            ),
        )


@pytest.mark.parametrize("writer_first", [False, True])
def test_both_coverage_commit_orders_and_empty_history_phantom(b01_env, monkeypatch, writer_first):
    e = b01_env
    with e["engine"].connect() as conn:
        execution, plan = conn.execute(
            text(
                "SELECT e.id,e.search_plan_version_id FROM "
                "search_result_records r JOIN search_query_records q ON "
                "q.id=r.search_query_record_id JOIN "
                "literature_search_executions e ON "
                "e.id=q.literature_search_execution_id WHERE r.id=:id"
            ),
            {"id": e["results"][0]},
        ).one()
    command = RecordSearchCoverageCommand(
        uuid4(), e["project"], plan, (execution,), "Bounded B01 concurrency scope"
    )
    ready, release = Event(), Event()
    if writer_first:
        original = Repository.insert

        def pause_writer(repo, row):
            original(repo, row)
            ready.set()
            assert release.wait(15)

        monkeypatch.setattr(Repository, "insert", pause_writer)

        def first():
            return record(e)

        def second():
            return e["bundle"].novelty.record_search_coverage(e["principal"], command)
    else:
        original = SqlAlchemyNoveltyRepository.prepare

        def pause_coverage(repo, *args, **kwargs):
            original(repo, *args, **kwargs)
            ready.set()
            assert release.wait(15)

        monkeypatch.setattr(SqlAlchemyNoveltyRepository, "prepare", pause_coverage)

        def first():
            return e["bundle"].novelty.record_search_coverage(e["principal"], command)

        def second():
            return record(e)

    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(first)
        assert ready.wait(15)
        b = pool.submit(second)
        try:
            # Observe actual blocking on the shared resolution table before releasing.
            deadline = monotonic() + 10
            while True:
                with e["engine"].connect() as observer:
                    blocked = (
                        observer.execute(
                            text(
                                "SELECT pid,xact_start,clock_timestamp() AS observed_at,"
                                "pg_blocking_pids(pid) AS blocker_pids FROM pg_stat_activity WHERE "
                                "datname=current_database() AND "
                                "wait_event_type='Lock'"
                            )
                        )
                        .mappings()
                        .all()
                    )
                if blocked:
                    print(
                        "B18_PHANTOM_WAIT",
                        dict(writer_first=writer_first, waiters=[dict(row) for row in blocked]),
                    )
                    break
                assert monotonic() < deadline
                Event().wait(0.01)
        finally:
            release.set()
        a.result(timeout=20)
        b.result(timeout=20)
    value = e["bundle"].novelty.read_search_coverage(
        e["principal"], ExactReadQuery(e["project"], command.id)
    )
    assert value.resolved_source_count == (1 if writer_first else 0)
    assert value.quality.current_unresolved_result_count == 1
    print(
        "B18_PHANTOM_CAPTURE",
        dict(
            writer_first=writer_first,
            coverage_id=str(value.id),
            content_hash=value.content_hash,
            query_count=value.query_count,
            result_count=value.result_count,
            resolved_source_count=value.resolved_source_count,
            current_unresolved_result_count=value.quality.current_unresolved_result_count,
        ),
    )


def test_b01_append_after_source_only_stays_ambiguous(b01_env):
    e = b01_env
    from datetime import UTC, datetime

    row = dict(
        id=uuid4(),
        search_result_record_id=e["results"][0],
        source_id=e["command"].source_id,
        source_version_id=None,
        resolved_by=e["principal"].actor_id,
        resolved_at=datetime.now(UTC),
        basis="Existing M2 source-only binding",
        hash_scheme="sha256-cjson-v1",
    )
    row["content_hash"] = resolution_hash(row)
    with e["service"]._factory() as uow:
        uow.metadata_observations.insert_resolution(row)
        uow.commit()
    admitted = record(e)
    assert admitted.source_version_id == e["command"].source_version_id
    assert count(e) == 2
    with e["engine"].connect() as conn:
        execution, plan = conn.execute(
            text("SELECT id,search_plan_version_id FROM literature_search_executions LIMIT 1")
        ).one()
    saved = e["bundle"].novelty.record_search_coverage(
        e["principal"],
        RecordSearchCoverageCommand(
            uuid4(), e["project"], plan, (execution,), "Source-only conflicting history"
        ),
    )
    assert saved.resolved_source_count == 0
    assert saved.quality.current_unresolved_result_count == 2


def test_initial_share_wait_has_connection_bounds_and_no_retry(b01_env, monkeypatch):
    e = b01_env
    calls = []
    original = Repository.prepare_write

    def traced(repo, identity):
        calls.append(repo)
        original(repo, identity)

    monkeypatch.setattr(Repository, "prepare_write", traced)
    with e["engine"].begin() as blocker, ThreadPoolExecutor(max_workers=1) as pool:
        blocker.execute(text("LOCK TABLE actors IN ROW EXCLUSIVE MODE"))
        pid = blocker.execute(text("SELECT pg_backend_pid()")).scalar_one()
        started = monotonic()
        future = pool.submit(record, e)
        _witness(e["engine"], pid)
        with pytest.raises(RuntimeError, match="recover by exact resolution ID"):
            future.result(timeout=14)
        assert 8 <= monotonic() - started < 14
    assert len(calls) == 1 and count(e) == 0


@pytest.mark.parametrize("change", ["merge", "correct", "membership_revocation"])
def test_owning_mutation_commits_before_waiting_b01_snapshot(b01_env, monkeypatch, change):
    from datetime import UTC, datetime

    from researchbase.application.phase2_identity import SuspendProjectMembership
    from researchbase.application.source_version import TransitionSourceVersion
    from researchbase.domain.source_version import SourceVersionKind
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork
    from tests.integration.phase2.b01_support import (
        correction_material,
        create_version,
        merge_command,
    )
    from tests.integration.phase2.test_pr2_00_ownership import _add_owner

    e = b01_env
    if change == "merge":
        command = merge_command(e)
        mutate = partial(e["bundle"].source_merge_execution.consume, command)
    elif change == "correct":
        version = create_version(
            e["bundle"],
            e["principal"],
            e["project"],
            correction_material(e, SourceVersionKind.CORRECTED),
            freeze=False,
        )
        mutate = partial(
            e["bundle"].source_versions.freeze,
            TransitionSourceVersion(e["principal"], e["project"], version, uuid4()),
        )
    else:
        with e["engine"].begin() as conn:
            _add_owner(
                conn,
                actor_id=uuid4(),
                project_id=e["project"],
                now=datetime.now(UTC),
                event_kind="ACTIVATED",
                request_id=uuid4(),
            )
            membership = conn.execute(
                text(
                    "SELECT id FROM project_memberships WHERE actor_id=:actor "
                    "AND project_id=:project AND status='ACTIVE'"
                ),
                {"actor": e["principal"].actor_id, "project": e["project"]},
            ).scalar_one()
        mutate = partial(
            e["bundle"].local_identity._identity.suspend_project_membership,
            SuspendProjectMembership(
                e["principal"], e["project"], membership, "Revoke before B01", uuid4()
            ),
        )
    ready, release = Event(), Event()
    holder = []
    original = SqlAlchemyUnitOfWork.commit

    def pause(uow):
        if not getattr(uow, "_b01_error_normalization", False):
            holder.append(
                uow._require_session().execute(text("SELECT pg_backend_pid()")).scalar_one()
            )
            ready.set()
            assert release.wait(15)
        original(uow)

    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", pause)
    with ThreadPoolExecutor(max_workers=2) as pool:
        owner = pool.submit(mutate)
        try:
            assert ready.wait(15)
            pending = pool.submit(record, e)
            _witness(e["engine"], holder[0])
        finally:
            release.set()
        owner.result(timeout=20)
        with pytest.raises(ResearchBaseError) as error:
            pending.result(timeout=20)
    assert (
        error.value.code
        is {
            "merge": ErrorCode.SOURCE_IDENTITY_CONFLICT,
            "correct": ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
            "membership_revocation": ErrorCode.FORBIDDEN,
        }[change]
    )
    assert count(e) == 0
