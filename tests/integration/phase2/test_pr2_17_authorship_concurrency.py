"""Actual PostgreSQL wait witnesses, expiry denial and bounded transaction retries."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from time import monotonic, sleep
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.authorship_repository import SqlAlchemyAuthorshipRepository
from tests.integration.phase2.test_pr2_00_ownership import _add_owner
from tests.integration.phase2.test_pr2_14_internal_review import _wait_for_pg_blocker
from tests.integration.phase2.test_pr2_17_authorship import (
    _count,
    _record,
    _snapshot,
)
from tests.integration.phase2.test_pr2_17_authorship import (
    authorship_env as _env,
)
from tests.integration.phase2.test_pr2_17_authorship import (
    authorship_url as _url,
)
from tests.integration.phase2.test_pr2_17_authorship_schema import (
    _insert,
)
from tests.integration.phase2.test_pr2_17_authorship_schema import (
    normal_role as _role,
)

pytestmark = pytest.mark.integration
authorship_env = _env
authorship_url = _url
normal_role = _role


@pytest.mark.parametrize("snapshot", [False, True])
@pytest.mark.parametrize("changed", [False, True])
def test_same_uuid_identical_or_conflicting_create(authorship_env, snapshot, changed):
    env = authorship_env
    if snapshot:
        first = env[0].record_contribution(env[4], _record(env))
        second = env[0].record_contribution(env[4], _record(env))
        cmd = _snapshot(env, (first.id, second.id))
        other = replace(cmd, contribution_record_ids=(second.id, first.id)) if changed else cmd
        method = env[0].create_authorship_snapshot
    else:
        cmd = _record(env)
        other = replace(cmd, contribution_statement="conflicting writing") if changed else cmd
        method = env[0].record_contribution

    def run(command):
        try:
            return method(env[4], command)
        except ResearchBaseError as error:
            return error.code

    holder = env[2].connect()
    tx = holder.begin()
    try:
        pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
        holder.execute(text("SELECT id FROM publications WHERE id=:id FOR UPDATE"), {"id": env[6]})
        with ThreadPoolExecutor(max_workers=2) as pool:
            a = pool.submit(run, cmd)
            witness = _wait_for_pg_blocker(env[2], pid, "transactionid")
            b = pool.submit(run, other)
            _wait_for_pg_blocker(env[2], witness["pid"], "advisory")
            tx.commit()
            results = [a.result(10), b.result(10)]
        if changed:
            assert results[1] is ErrorCode.IDEMPOTENCY_CONFLICT
        else:
            assert results[0] == results[1]
        assert _count(env) == ((2, 1) if snapshot else (1, 0))
    finally:
        if tx.is_active:
            tx.rollback()
        holder.close()


def test_overlapping_snapshots_are_distinct_facts(authorship_env):
    env = authorship_env
    record = env[0].record_contribution(env[4], _record(env))
    commands = [_snapshot(env, (record.id,)) for _ in range(2)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(lambda cmd: env[0].create_authorship_snapshot(env[4], cmd), commands)
        )
    assert results[0].id != results[1].id
    assert results[0].content_hash == results[1].content_hash
    assert _count(env) == (1, 2)


def test_concurrent_late_child_waits_then_is_rejected(authorship_env, normal_role):
    env = authorship_env
    record = env[0].record_contribution(env[4], _record(env))
    snapshot = env[0].create_authorship_snapshot(env[4], _snapshot(env, (record.id,)))
    holder = env[2].connect()
    tx = holder.begin()
    try:
        pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
        holder.execute(
            text("SELECT id FROM authorship_snapshots WHERE id=:id FOR UPDATE"), {"id": snapshot.id}
        )

        def late():
            try:
                with env[2].begin() as conn:
                    conn.execute(text(f'SET LOCAL ROLE "{normal_role}"'))
                    _insert(
                        conn,
                        "authorship_snapshot_authors",
                        {
                            "id": uuid4(),
                            "created_by": env[4].actor_id,
                            "authorship_snapshot_id": snapshot.id,
                            "actor_id": env[4].actor_id,
                            "ordinal": 2,
                        },
                    )
            except DBAPIError as error:
                return getattr(error.orig, "sqlstate", None)

        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(late)
            _wait_for_pg_blocker(env[2], pid, "transactionid")
            tx.commit()
            assert future.result(10) == "P17A1"
        assert _count(env) == (1, 1)
    finally:
        if tx.is_active:
            tx.rollback()
        holder.close()


def _past_expiry(engine, expiry):
    deadline = monotonic() + 5
    while monotonic() < deadline:
        with engine.connect() as conn:
            at = conn.execute(text("SELECT clock_timestamp()")).scalar_one()
        if at > expiry:
            return at
        sleep(0.01)
    pytest.fail("database expiry not reached")


def _expire_authority(env, kind):
    with env[2].begin() as conn:
        now = conn.execute(text("SELECT clock_timestamp()")).scalar_one()
        expiry = now + timedelta(seconds=0.7)
        if kind == "role":
            _add_owner(
                conn,
                actor_id=uuid4(),
                project_id=env[5],
                now=now,
                event_kind="ACTIVATED",
                request_id=uuid4(),
            )
            # A legal temporal closure and its event, with retained OWNER coverage.
            row = conn.execute(
                text(
                    "UPDATE project_role_assignments SET "
                    "effective_until=:expiry,row_version=row_version+1 WHERE actor_id=:actor "
                    "AND role='OWNER' RETURNING id"
                ),
                {"expiry": expiry, "actor": env[4].actor_id},
            ).scalar_one()
            _insert(
                conn,
                "project_role_events",
                {
                    "id": uuid4(),
                    "role_assignment_id": row,
                    "actor_id": env[4].actor_id,
                    "event_kind": "CLOSED",
                    "occurred_at": expiry,
                    "reason": "TEST ONLY finite authority",
                    "request_id": uuid4(),
                },
            )
        else:
            env[3].expires = expiry
    return expiry


@pytest.mark.parametrize("snapshot", [False, True])
@pytest.mark.parametrize("target", ["Publication", "Project"])
@pytest.mark.parametrize("kind", ["credential", "role"])
def test_expiry_during_required_wait_zero_effect(
    authorship_env, monkeypatch, target, kind, snapshot
):
    env = authorship_env
    if snapshot:
        record = env[0].record_contribution(env[4], _record(env))
        command = _snapshot(env, (record.id,))
    else:
        command = _record(env)
    method = env[0].create_authorship_snapshot if snapshot else env[0].record_contribution
    trace = {"checks": []}
    original = SqlAlchemyAuthorshipRepository.lock_request

    def traced(repo, identity):
        original(repo, identity)
        trace["tx_started"], trace["pid"] = repo._session.execute(
            text("SELECT transaction_timestamp(),pg_backend_pid()")
        ).one()

    monkeypatch.setattr(SqlAlchemyAuthorshipRepository, "lock_request", traced)
    auth = env[0]._authorize

    def checked(repo, principal, project, roles):
        try:
            return auth(repo, principal, project, roles)
        finally:
            trace["checks"].append(repo.at())

    monkeypatch.setattr(env[0], "_authorize", checked)
    expiry = _expire_authority(env, kind)
    holder = env[2].connect()
    tx = holder.begin()
    try:
        pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
        table = "publications" if target == "Publication" else "projects"
        identity = env[6] if target == "Publication" else env[5]
        holder.execute(text(f"SELECT id FROM {table} WHERE id=:id FOR UPDATE"), {"id": identity})

        def run():
            with pytest.raises(ResearchBaseError) as error:
                method(env[4], command)
            return error.value.code

        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(run)
            witness = _wait_for_pg_blocker(env[2], pid, "transactionid")
            assert witness["pid"] == trace["pid"]
            _past_expiry(env[2], expiry)
            released = holder.execute(text("SELECT clock_timestamp()")).scalar_one()
            tx.commit()
            assert future.result(10) == (
                ErrorCode.AUTHENTICATION_REQUIRED if kind == "credential" else ErrorCode.FORBIDDEN
            )
        assert trace["tx_started"] < expiry
        assert witness["observed_at"] < expiry < released <= trace["checks"][-1]
        assert _count(env) == ((1, 0) if snapshot else (0, 0))
        print("PR217_EXPIRY_EVIDENCE", trace, "expiry", expiry, "release", released)
    finally:
        if tx.is_active:
            tx.rollback()
        holder.close()


@pytest.mark.parametrize("kind", ["credential", "role"])
@pytest.mark.parametrize("snapshot", [False, True])
def test_second_actor_wait_rechecks_authority(authorship_env, monkeypatch, kind, snapshot):
    env = authorship_env
    other = uuid4()
    with env[2].begin() as conn:
        conn.execute(
            text(
                "INSERT INTO actors(id,actor_type,display_name,created_at) VALUES "
                "(:id,'HUMAN','TEST ONLY',clock_timestamp())"
            ),
            {"id": other},
        )
    command = _record(env, actor_id=other)
    if snapshot:
        record = env[0].record_contribution(env[4], command)
        command = _snapshot(
            env, (record.id,), author_ids=(other,), corresponding_author_ids=(other,)
        )
    method = env[0].create_authorship_snapshot if snapshot else env[0].record_contribution
    expiry = _expire_authority(env, kind)
    checks = []
    original = env[0]._authorize

    def checked(repo, principal, project, roles):
        try:
            return original(repo, principal, project, roles)
        finally:
            checks.append(repo.at())

    monkeypatch.setattr(env[0], "_authorize", checked)
    holder = env[2].connect()
    tx = holder.begin()
    try:
        pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
        holder.execute(text("SELECT id FROM actors WHERE id=:id FOR UPDATE"), {"id": other})

        def run():
            with pytest.raises(ResearchBaseError) as error:
                method(env[4], command)
            return error.value.code

        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(run)
            witness = _wait_for_pg_blocker(env[2], pid, "transactionid")
            assert checks and checks[0] < expiry
            _past_expiry(env[2], expiry)
            tx.commit()
            assert future.result(10) is (
                ErrorCode.AUTHENTICATION_REQUIRED if kind == "credential" else ErrorCode.FORBIDDEN
            )
        assert witness["observed_at"] < expiry < checks[-1] and checks[-1] > checks[0]
        assert _count(env) == ((1, 0) if snapshot else (0, 0))
        print("PR217_SECOND_WAIT_EVIDENCE", checks, witness)
    finally:
        if tx.is_active:
            tx.rollback()
        holder.close()


@pytest.mark.parametrize(
    "state,failures,attempts",
    [
        ("40001", 2, 3),
        ("40P01", 2, 3),
        ("40001", 3, 3),
        ("40P01", 3, 3),
        ("55P03", 1, 1),
        ("57014", 1, 1),
        ("23505", 1, 1),
        ("XX000", 1, 1),
    ],
)
def test_real_database_failures_retry_only_private_flag(
    authorship_env, monkeypatch, state, failures, attempts
):
    env = authorship_env
    calls = []
    original = SqlAlchemyAuthorshipRepository.lock_request

    def injected(repo, identity):
        calls.append(identity)
        original(repo, identity)
        if len(calls) <= failures:
            repo._session.execute(
                text(
                    "DO $$ BEGIN RAISE EXCEPTION 'TEST ONLY secret driver detail' "
                    f"USING ERRCODE='{state}'; END $$"
                )
            )

    monkeypatch.setattr(SqlAlchemyAuthorshipRepository, "lock_request", injected)
    command = _record(env)
    if failures == 2:
        assert env[0].record_contribution(env[4], command).id == command.id
        assert _count(env) == (1, 0)
    else:
        with pytest.raises(ResearchBaseError) as error:
            env[0].record_contribution(env[4], command)
        assert error.value.code is (
            ErrorCode.INVALID_STATE_TRANSITION
            if state == "XX000"
            else ErrorCode.CONCURRENT_MODIFICATION
        )
        assert error.value.__cause__ is None
        assert "secret" not in str(error.value) and state not in str(error.value)
        assert _count(env) == (0, 0)
    assert len(calls) == attempts and set(calls) == {command.id}
