"""Observed PostgreSQL waits, exact lock order, bounded retry and atomic rollback."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Barrier, Event, Lock, get_ident
from uuid import uuid4

import pytest
from psycopg.errors import DeadlockDetected, LockNotAvailable, SerializationFailure
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError

from researchbase.application.strategy_candidate_promotion import (
    CaptureNativeStrategyCommand,
    ExactStrategyQuery,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.strategy_candidate_promotion_repository import S
from researchbase.persistence.strategy_candidate_promotion_repository import (
    SqlAlchemyStrategyCandidatePromotionRepository as Repository,
)
from tests.integration.phase2.b02_support import capture, count, hcommand, qcommand
from tests.integration.phase2.test_pr2_18_concurrency import _witness


def test_first_sql_and_lock_free_read_snapshot(b02_env, monkeypatch):
    e = b02_env
    saved = capture(e)
    seen = []

    def observe(conn, cursor, statement, parameters, context, executemany):
        seen.append(statement)

    event.listen(Engine, "before_cursor_execute", observe)
    try:
        value = e["service"].promote_strategy_question(e["principal"], qcommand(e, saved))
        assert seen[0] == "LOCK TABLE " + ",".join(S) + " IN SHARE MODE"
        seen.clear()
        original = Repository.exact

        def exact(repo, *args):
            assert (
                repo._session.execute(text("SHOW transaction_isolation")).scalar_one()
                == "repeatable read"
            )
            assert repo._session.execute(text("SHOW transaction_read_only")).scalar_one() == "on"
            return original(repo, *args)

        monkeypatch.setattr(Repository, "exact", exact)
        assert (
            e["service"].get_strategy_question_promotion(
                e["other"], ExactStrategyQuery(value.id, e["project"])
            )
            == value
        )
        assert not any(
            any(
                x in s.upper()
                for x in ("LOCK TABLE", "ADVISORY", "FOR UPDATE", "FOR SHARE", "INSERT", "UPDATE ")
            )
            for s in seen
        )
    finally:
        event.remove(Engine, "before_cursor_execute", observe)


@pytest.mark.parametrize("kind", ["capture", "question", "hypothesis"])
@pytest.mark.parametrize("same_id", [True, False])
def test_two_connection_writer_races(b02_env, monkeypatch, kind, same_id):
    e = b02_env
    saved = capture(e)
    cmd = (
        CaptureNativeStrategyCommand(uuid4(), e["project"], "Recall", e["sources"])
        if kind == "capture"
        else qcommand(e, saved)
        if kind == "question"
        else hcommand(e, saved)
    )
    invoke = (
        e["service"].capture_native_strategy
        if kind == "capture"
        else getattr(e["service"], f"promote_strategy_{kind}")
    )
    barrier = Barrier(2)
    guard = Lock()
    initial = [0]
    pids = []
    attempts_by_thread = {}
    original = Repository.prepare_write

    def prepare(repo, k, identity):
        with guard:
            initial[0] += 1
            number = initial[0]
            thread = get_ident()
            attempts_by_thread[thread] = attempts_by_thread.get(thread, 0) + 1
        if number <= 2:
            pids.append(repo._session.connection().connection.driver_connection.info.backend_pid)
            barrier.wait(10)
        original(repo, k, identity)

    monkeypatch.setattr(Repository, "prepare_write", prepare)

    def run(command):
        try:
            result = invoke(e["principal"], command)
        except ResearchBaseError as exc:
            result = exc
        return result, attempts_by_thread[get_ident()]

    commands = (cmd, cmd if same_id else replace(cmd, id=uuid4()))
    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(run, commands[0])
        b = pool.submit(run, commands[1])
        outcomes = [a.result(timeout=40), b.result(timeout=40)]
    assert len(set(pids)) == 2
    assert any(not isinstance(value, ResearchBaseError) for value, _ in outcomes)
    values = []
    for (value, attempts), command in zip(outcomes, commands, strict=True):
        if isinstance(value, ResearchBaseError) and value.code is ErrorCode.CONCURRENT_MODIFICATION:
            assert attempts == 3 and value.details and value.details.get("retryable_b02")
            # The guide bounds attempts; a caller may recover by the original ID
            # after the winning transaction completes. Never add an internal retry.
            try:
                value = invoke(e["principal"], command)
            except ResearchBaseError as recovered:
                value = recovered
        values.append(value.code if isinstance(value, ResearchBaseError) else value)
    if same_id:
        assert values[0] == values[1] and not isinstance(values[0], ErrorCode)
    elif kind != "capture":
        assert sum(v is ErrorCode.DUPLICATE_CONTENT for v in values) == 1
    else:
        assert all(not isinstance(v, ErrorCode) for v in values)
    assert count(
        e, "strategy_" + ("candidate_captures" if kind == "capture" else kind + "_admissions")
    ) == ((2 if same_id else 3) if kind == "capture" else 1)


@pytest.mark.parametrize(
    "error,attempts", [(SerializationFailure, 3), (DeadlockDetected, 3), (LockNotAvailable, 1)]
)
def test_exactly_three_retryable_attempts_no_timeout_retry(b02_env, monkeypatch, error, attempts):
    e = b02_env
    saved = capture(e)
    calls = []
    original = Repository.prepare_write

    def prepare(repo, *args):
        original(repo, *args)
        calls.append(repo._session)
        raise DBAPIError("test", {}, error("synthetic"), False)

    monkeypatch.setattr(Repository, "prepare_write", prepare)
    with pytest.raises(ResearchBaseError) as caught:
        e["service"].promote_strategy_question(e["principal"], qcommand(e, saved))
    assert caught.value.code is ErrorCode.CONCURRENT_MODIFICATION
    assert len(calls) == attempts and len({id(v) for v in calls}) == attempts
    assert count(e, "strategy_question_admissions") == 0


@pytest.mark.parametrize(
    "kind,stage",
    [
        ("capture", "artifact"),
        ("capture", "artifact_version"),
        ("capture", "artifact_pointer"),
        ("capture", "receipt"),
        ("capture", "deferred"),
        ("question", "identity"),
        ("question", "version"),
        ("question", "pointer"),
        ("question", "receipt"),
        ("question", "deferred"),
        ("hypothesis", "identity"),
        ("hypothesis", "version"),
        ("hypothesis", "pointer"),
        ("hypothesis", "receipt"),
        ("hypothesis", "deferred"),
    ],
)
def test_failure_at_each_write_step_rolls_back(b02_env, monkeypatch, kind, stage):
    from researchbase.persistence import repositories as repos

    e = b02_env
    saved = capture(e)
    tables = (
        "artifacts",
        "artifact_versions",
        "research_questions",
        "research_question_versions",
        "hypotheses",
        "hypothesis_versions",
        "strategy_candidate_captures",
        "strategy_candidate_sources",
        "strategy_question_admissions",
        "strategy_hypothesis_admissions",
    )
    before = [count(e, t) for t in tables]
    if stage in {"receipt", "deferred"}:
        cls, method = Repository, "insert" if stage == "receipt" else "force_constraints"
    elif kind == "capture":
        cls, method = {
            "artifact": (repos.SqlAlchemyArtifactRepository, "add"),
            "artifact_version": (repos.SqlAlchemyArtifactVersionRepository, "add"),
            "artifact_pointer": (repos.SqlAlchemyArtifactRepository, "update_current_version"),
        }[stage]
    else:
        cls = (
            repos.SqlAlchemyResearchQuestionRepository
            if kind == "question"
            else repos.SqlAlchemyHypothesisRepository
        )
        method = {"identity": "add", "version": "add_version", "pointer": "update_current_version"}[
            stage
        ]
    original = getattr(cls, method)

    def fail(obj, *args, **kwargs):
        original(obj, *args, **kwargs)
        raise RuntimeError("injected after " + stage)

    monkeypatch.setattr(cls, method, fail)
    invoke = (
        e["service"].capture_native_strategy
        if kind == "capture"
        else getattr(e["service"], f"promote_strategy_{kind}")
    )
    cmd = (
        CaptureNativeStrategyCommand(uuid4(), e["project"], "Recall", e["sources"])
        if kind == "capture"
        else qcommand(e, saved)
        if kind == "question"
        else hcommand(e, saved)
    )
    with pytest.raises(RuntimeError, match="injected after"):
        invoke(e["principal"], cmd)
    assert [count(e, t) for t in tables] == before


@pytest.mark.parametrize("change", ["archive", "credential_expiry", "role_expiry"])
def test_initial_wait_refreshes_authority_and_source_closure(b02_env, monkeypatch, change):
    e = b02_env
    saved = capture(e)
    samples = []
    acquired = []
    original_at, original_prepare = Repository.at, Repository.prepare_write

    def at(repo):
        value = original_at(repo)
        samples.append(value)
        return value

    def prepare(repo, *args):
        original_prepare(repo, *args)
        acquired.append(original_at(repo))

    monkeypatch.setattr(Repository, "at", at)
    monkeypatch.setattr(Repository, "prepare_write", prepare)
    with e["engine"].connect() as blocker, ThreadPoolExecutor(max_workers=1) as pool:
        tx = blocker.begin()
        blocker.execute(text("LOCK TABLE projects IN ROW EXCLUSIVE MODE"))
        pid = blocker.execute(text("SELECT pg_backend_pid()")).scalar_one()
        expiry = blocker.execute(text("SELECT clock_timestamp()+interval '1 second'")).scalar_one()
        if change == "credential_expiry":
            original = e["credentials"].is_valid
            monkeypatch.setattr(
                e["credentials"], "is_valid", lambda p, at: at < expiry and original(p, at)
            )
        if change == "role_expiry":
            role = blocker.execute(
                text(
                    "UPDATE project_role_assignments SET "
                    "effective_until=:at,row_version=row_version+1 WHERE "
                    "actor_id=:actor AND project_id=:project AND effective_until IS "
                    "NULL RETURNING id"
                ),
                {"at": expiry, "actor": e["principal"].actor_id, "project": e["project"]},
            ).scalar_one()
            blocker.execute(
                text(
                    "INSERT INTO "
                    "project_role_events(id, role_assignment_id, actor_id, event_kind, "
                    "occurred_at, reason, request_id)"
                    "VALUES(:id,:role,:actor,'CLOSED',:at,'B02 expiry',:request)"
                ),
                {
                    "id": uuid4(),
                    "role": role,
                    "actor": e["principal"].actor_id,
                    "at": expiry,
                    "request": uuid4(),
                },
            )
        future = pool.submit(
            e["service"].promote_strategy_question, e["principal"], qcommand(e, saved)
        )
        waiter = _witness(e["engine"], pid, before=expiry)
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
        if change.endswith("expiry"):
            while blocker.execute(text("SELECT clock_timestamp()")).scalar_one() < expiry:
                Event().wait(0.01)
        tx.commit()
        with pytest.raises(ResearchBaseError) as caught:
            future.result(timeout=15)
    assert caught.value.code is ErrorCode.FORBIDDEN
    assert count(e, "strategy_question_admissions") == 0
    if change.endswith("expiry"):
        assert started < expiry and observed < expiry <= acquired[0] <= samples[0]
        print(
            "B02_EXPIRY",
            {
                "tx_started_at": str(started),
                "expiry_at": str(expiry),
                "lock_wait_started_at": str(observed),
                "lock_acquired_at": str(acquired[0]),
                "authorization_checked_at": str(samples[0]),
                "protected_rows": 0,
            },
        )


def test_reader_keeps_snapshot_and_does_not_block_writer(b02_env, monkeypatch):
    e = b02_env
    saved = capture(e)
    ready, release = Event(), Event()
    original = Repository.exact

    def exact(repo, *args):
        row = original(repo, *args)
        ready.set()
        assert release.wait(10)
        return row

    monkeypatch.setattr(Repository, "exact", exact)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(
            e["service"].get_strategy_capture,
            e["principal"],
            ExactStrategyQuery(saved.id, e["project"]),
        )
        try:
            assert ready.wait(10)
            with e["engine"].begin() as writer:
                writer.execute(text("SET LOCAL lock_timeout='1s'"))
                writer.execute(
                    text(
                        "INSERT INTO actors(id,actor_type,display_name,created_at) "
                        "VALUES(:id,'HUMAN','Concurrent ordinary "
                        "writer',clock_timestamp())"
                    ),
                    {"id": uuid4()},
                )
        finally:
            release.set()
        assert future.result(timeout=10) == saved


def test_fresh_credential_check_after_observed_constraint_wait_rolls_back(b02_env, monkeypatch):
    """Inject a blocking constraint-step boundary, then observe the real PG wait."""
    e = b02_env
    saved = capture(e)
    original_force, original_at = Repository.force_constraints, Repository.at
    samples = []
    acquired = []

    def at(repo):
        value = original_at(repo)
        samples.append(value)
        return value

    def force(repo):
        # Test-only coordination makes a deferred-check wait deterministic without
        # adding any lock or advisory key to the production write protocol.
        repo._session.execute(text("SELECT pg_advisory_xact_lock(782348923)"))
        acquired.append(original_at(repo))
        original_force(repo)

    monkeypatch.setattr(Repository, "at", at)
    monkeypatch.setattr(Repository, "force_constraints", force)
    before = count(e, "research_questions")
    with e["engine"].connect() as blocker, ThreadPoolExecutor(max_workers=1) as pool:
        tx = blocker.begin()
        blocker.execute(text("SELECT pg_advisory_xact_lock(782348923)"))
        pid = blocker.execute(text("SELECT pg_backend_pid()")).scalar_one()
        expiry = blocker.execute(text("SELECT clock_timestamp()+interval '1 second'")).scalar_one()
        original_valid = e["credentials"].is_valid
        monkeypatch.setattr(
            e["credentials"], "is_valid", lambda p, at: at < expiry and original_valid(p, at)
        )
        future = pool.submit(
            e["service"].promote_strategy_question, e["principal"], qcommand(e, saved)
        )
        waiter = _witness(e["engine"], pid, before=expiry)
        with e["engine"].connect() as observer:
            started, observed = observer.execute(
                text("SELECT xact_start,clock_timestamp() FROM pg_stat_activity WHERE pid=:pid"),
                {"pid": waiter},
            ).one()
        while blocker.execute(text("SELECT clock_timestamp()")).scalar_one() < expiry:
            Event().wait(0.01)
        tx.commit()
        with pytest.raises(ResearchBaseError) as caught:
            future.result(timeout=15)
    assert caught.value.code is ErrorCode.FORBIDDEN
    assert started < expiry and observed < expiry <= acquired[0] <= samples[-1]
    assert samples[0] < expiry < samples[-1]
    assert (
        count(e, "research_questions") == before and count(e, "strategy_question_admissions") == 0
    )
    print(
        "B02_FINAL_EXPIRY",
        {
            "tx_started_at": str(started),
            "expiry_at": str(expiry),
            "lock_wait_started_at": str(observed),
            "lock_acquired_at": str(acquired[0]),
            "first_authorization_at": str(samples[0]),
            "final_authorization_at": str(samples[-1]),
            "protected_rows": 0,
        },
    )


def test_source_link_phantom_revocation_is_share_blocked_then_immutable(b02_env, monkeypatch):
    e = b02_env
    saved = capture(e)
    ready, release = Event(), Event()
    writer_pid = []
    original = Repository.prepare_write

    def prepare(repo, *args):
        original(repo, *args)
        writer_pid.append(repo._session.execute(text("SELECT pg_backend_pid()")).scalar_one())
        ready.set()
        assert release.wait(10)

    monkeypatch.setattr(Repository, "prepare_write", prepare)

    def revoke():
        with e["engine"].begin() as conn:
            conn.execute(
                text("DELETE FROM literature_source_project_links WHERE project_id=:id"),
                {"id": e["project"]},
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        admission = pool.submit(
            e["service"].promote_strategy_question, e["principal"], qcommand(e, saved)
        )
        assert ready.wait(10)
        revocation = pool.submit(revoke)
        try:
            assert _witness(e["engine"], writer_pid[0]) != writer_pid[0]
        finally:
            release.set()
        assert admission.result(timeout=15).capture_id == saved.id
        with pytest.raises(DBAPIError) as denied:
            revocation.result(timeout=15)
        assert getattr(denied.value.orig, "sqlstate", None) == "P17D1"
    assert count(e, "strategy_question_admissions") == 1
