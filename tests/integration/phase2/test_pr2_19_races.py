"""Observed PostgreSQL lock schedules, never sleep-only race evidence."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import uuid4

import pytest
from sqlalchemy import event, text

from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.decision_repository import SqlAlchemyDecisionRepository
from tests.integration.phase2 import test_pr2_15_decision as cases
from tests.integration.phase2.pr2_19_support import _wait_for_pg_blocker
from tests.integration.phase2.pr2_19_support import conclusion_env as _conclusion_env
from tests.integration.phase2.pr2_19_support import decision_env as _decision_env
from tests.integration.phase2.pr2_19_support import (
    discussion_database_url as _discussion_database_url,
)
from tests.integration.phase2.pr2_19_support import discussion_env as _discussion_env
from tests.integration.phase2.pr2_19_support import m3 as _m3
from tests.integration.phase2.pr2_19_support import normal_sql_role as _normal_sql_role
from tests.integration.phase2.pr2_19_support import phase2_database_url as _phase2_database_url
from tests.integration.phase2.pr2_19_support import pr219_decision_env as _pr219_decision_env
from tests.integration.phase2.pr2_19_support import pr219_discussion_env as _pr219_discussion_env

pytestmark = pytest.mark.integration


def test_zero_issue_review_first(pr219_decision_env, normal_sql_role):
    cases.test_zero_issue_review_first_observed_wait_includes_committed_review(
        pr219_decision_env, normal_sql_role
    )


def test_blocking_issue_first(pr219_decision_env, normal_sql_role):
    cases.test_normal_role_issue_first_wait_refreshes_blockers(pr219_decision_env, normal_sql_role)


@pytest.mark.parametrize("writer_kind", ["issue", "zero_issue_review"])
def test_decision_first_review_or_issue_writer(pr219_decision_env, normal_sql_role, writer_kind):
    cases.test_decision_first_real_writer_wait_preserves_original_basis(
        pr219_decision_env, normal_sql_role, writer_kind
    )


@pytest.mark.parametrize("first", ["governance", "decision"])
def test_upstream_impact_both_orders(pr219_decision_env, first):
    cases.test_upstream_impact_writer_and_decision_actual_table_wait_both_orders(
        pr219_decision_env, first
    )


def test_authority_writer_first(pr219_decision_env, normal_sql_role):
    cases.test_authority_writer_first_real_table_wait_refreshes_role(
        pr219_decision_env, normal_sql_role
    )


def test_decision_first_authority_writer(pr219_decision_env, normal_sql_role):
    env = pr219_decision_env
    service, _, actor, _, base = env
    cases._review(env)
    request = cases._command(env)
    held, release = Event(), Event()
    pids = []

    def pause(conn, cursor, statement, parameters, context, executemany):
        if (
            statement.lstrip().upper().startswith("INSERT INTO DECISION_RECORDS")
            and not held.is_set()
        ):
            pids.append(conn.execute(text("SELECT pg_backend_pid()")).scalar_one())
            held.set()
            assert release.wait(15)

    def writer():
        with base[8].begin() as conn:
            cases._normal(conn, normal_sql_role)
            row = conn.execute(
                text(
                    "UPDATE project_role_assignments SET "
                    "effective_until=clock_timestamp(),row_version=row_version+1 WHERE "
                    "actor_id=:actor AND project_id=:project AND effective_until IS NULL "
                    "RETURNING id,effective_until"
                ),
                {"actor": actor.actor_id, "project": base[5]},
            ).one()
            conn.execute(
                text(
                    "INSERT INTO project_role_events "
                    "(id,role_assignment_id,actor_id,event_kind,occurred_at,reason,request_id) "
                    "VALUES (:id,:role,:actor,'CLOSED',:until,'PR219 concurrent close',:request)"
                ),
                {
                    "id": uuid4(),
                    "role": row.id,
                    "actor": actor.actor_id,
                    "until": row.effective_until,
                    "request": uuid4(),
                },
            )

    event.listen(base[8], "after_cursor_execute", pause)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            leading = pool.submit(service.record_decision, actor, request)
            try:
                assert held.wait(10)
                following = pool.submit(writer)
                witness = _wait_for_pg_blocker(base[8], pids[0], "relation")
                assert witness["relation"] == "project_role_assignments"
                assert not following.done()
            finally:
                release.set()
            saved = leading.result(timeout=10)
            following.result(timeout=10)
        assert cases._counts(base[8]) == (1, 1, 1)
        with base[8].connect() as conn:
            assert (
                conn.execute(
                    text("SELECT content_hash FROM decision_records WHERE id=:id"), {"id": saved.id}
                ).scalar_one()
                == saved.content_hash
            )
        with pytest.raises(ResearchBaseError) as denied:
            service.record_decision(actor, request)
        assert denied.value.code is ErrorCode.FORBIDDEN
    finally:
        release.set()
        event.remove(base[8], "after_cursor_execute", pause)


def test_cross_expiry_five_database_timestamps(pr219_decision_env, monkeypatch):
    env = pr219_decision_env
    service, _, actor, target, base = env
    engine = base[8]
    cases._review(env)
    with engine.begin() as conn:
        row = conn.execute(
            text(
                "UPDATE project_role_assignments SET "
                "effective_until=clock_timestamp()+interval '5 "
                "seconds',row_version=row_version+1 WHERE actor_id=:actor AND "
                "project_id=:project AND effective_until IS NULL RETURNING id,effective_until"
            ),
            {"actor": actor.actor_id, "project": base[5]},
        ).one()
        expiry = row.effective_until
        conn.execute(
            text(
                "INSERT INTO project_role_events "
                "(id,role_assignment_id,actor_id,event_kind,occurred_at,reason,request_id) "
                "VALUES (:id,:role,:actor,'CLOSED',:until,'PR219 scheduled expiry',:request)"
            ),
            {
                "id": uuid4(),
                "role": row.id,
                "actor": actor.actor_id,
                "until": expiry,
                "request": uuid4(),
            },
        )
    acquired, checked = [], []
    original_target = SqlAlchemyDecisionRepository.target
    original_valid = base[9].is_valid

    def instrument_target(self, *args):
        result = original_target(self, *args)
        acquired.append(self._session.execute(text("SELECT clock_timestamp()")).scalar_one())
        return result

    def instrument_credentials(principal, at):
        checked.append(at)
        return original_valid(principal, at)

    monkeypatch.setattr(SqlAlchemyDecisionRepository, "target", instrument_target)
    monkeypatch.setattr(base[9], "is_valid", instrument_credentials)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with engine.begin() as holder:
            pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
            holder.execute(
                text("SELECT id FROM scientific_conclusion_versions WHERE id=:id FOR UPDATE"),
                {"id": target.version_id},
            ).one()
            pending = pool.submit(service.record_decision, actor, cases._command(env))
            witness = _wait_for_pg_blocker(engine, pid, "transactionid")
            with engine.connect() as observer:
                started = observer.execute(
                    text("SELECT xact_start FROM pg_stat_activity WHERE pid=:pid"),
                    {"pid": witness["pid"]},
                ).scalar_one()
            assert started < expiry and witness["observed_at"] < expiry
            holder.execute(
                text(
                    "SELECT pg_sleep(GREATEST(0,EXTRACT(EPOCH FROM "
                    "(:expiry-clock_timestamp()))+0.1))"
                ),
                {"expiry": expiry},
            )
            assert _wait_for_pg_blocker(engine, pid, "transactionid")["observed_at"] >= expiry
        with pytest.raises(ResearchBaseError) as denied:
            pending.result(timeout=10)
    assert denied.value.code is ErrorCode.FORBIDDEN
    assert acquired and checked
    assert acquired[-1] >= expiry
    assert checked[-1] > expiry and checked[-1] >= acquired[-1]
    assert cases._counts(engine) == (0, 0, 0)
    print(
        "PR219_CROSS_EXPIRY",
        {
            "tx_started_at": str(started),
            "expiry_at": str(expiry),
            "lock_wait_started_at": str(witness["observed_at"]),
            "lock_acquired_at": str(acquired[-1]),
            "authorization_checked_at": str(checked[-1]),
            "protected_counts": cases._counts(engine),
        },
    )


# Register imported fixtures explicitly, matching the existing Phase 2 layout.
conclusion_env = _conclusion_env
decision_env = _decision_env
m3 = _m3
normal_sql_role = _normal_sql_role
phase2_database_url = _phase2_database_url
pr219_decision_env = _pr219_decision_env


def test_discussion_second_wait_rechecks_expiry(pr219_discussion_env, monkeypatch):
    from researchbase.persistence.discussion_repository import SqlAlchemyDiscussionRepository
    from tests.integration.phase2.test_pr2_10_discussion_persistence import _create

    env = pr219_discussion_env
    service, engine, credentials, actor, project, _, source = env
    session = _create(env).session_id
    from datetime import UTC, datetime

    from tests.integration.phase2.test_pr2_00_ownership import _add_owner

    with engine.begin() as conn:
        _add_owner(
            conn,
            actor_id=uuid4(),
            project_id=project,
            now=datetime.now(UTC),
            event_kind="ACTIVATED",
            request_id=uuid4(),
        )
    with engine.begin() as conn:
        row = conn.execute(
            text("""UPDATE project_role_assignments
            SET effective_until=clock_timestamp()+interval '5 seconds',row_version=row_version+1
            WHERE actor_id=:actor AND project_id=:project AND effective_until IS NULL
            RETURNING id,effective_until"""),
            {"actor": actor.actor_id, "project": project},
        ).one()
        expiry = row.effective_until
        conn.execute(
            text("""INSERT INTO project_role_events
            (id,role_assignment_id,actor_id,event_kind,occurred_at,reason,request_id)
            VALUES (:id,:role,:actor,'CLOSED',:until,'PR219 scheduled expiry',:request)"""),
            {
                "id": uuid4(),
                "role": row.id,
                "actor": actor.actor_id,
                "until": expiry,
                "request": uuid4(),
            },
        )
    acquired, checked = [], []
    original_session = SqlAlchemyDiscussionRepository.session
    original_valid = credentials.is_valid

    def instrument_session(self, *args, **kwargs):
        result = original_session(self, *args, **kwargs)
        if kwargs.get("lock"):
            acquired.append(self._session.execute(text("SELECT clock_timestamp()")).scalar_one())
        return result

    def instrument_credentials(principal, at):
        checked.append(at)
        return original_valid(principal, at)

    monkeypatch.setattr(SqlAlchemyDiscussionRepository, "session", instrument_session)
    monkeypatch.setattr(credentials, "is_valid", instrument_credentials)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with engine.begin() as holder:
            pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
            holder.execute(
                text("SELECT id FROM discussion_sessions WHERE id=:id FOR UPDATE"), {"id": session}
            ).one()
            pending = pool.submit(
                service.append,
                actor,
                project,
                session,
                "human",
                "No protected turn",
                (source,),
                (),
                uuid4(),
            )
            witness = _wait_for_pg_blocker(engine, pid, "transactionid")
            with engine.connect() as observer:
                started = observer.execute(
                    text("SELECT xact_start FROM pg_stat_activity WHERE pid=:pid"),
                    {"pid": witness["pid"]},
                ).scalar_one()
            assert started < expiry and witness["observed_at"] < expiry
            assert checked and checked[0] < expiry
            holder.execute(
                text(
                    "SELECT pg_sleep(GREATEST(0,EXTRACT(EPOCH FROM "
                    "(:expiry-clock_timestamp()))+0.1))"
                ),
                {"expiry": expiry},
            )
            assert _wait_for_pg_blocker(engine, pid, "transactionid")["observed_at"] >= expiry
        with pytest.raises(ResearchBaseError) as denied:
            pending.result(timeout=10)
    assert denied.value.code is ErrorCode.FORBIDDEN
    assert acquired[-1] >= expiry and checked[-1] >= acquired[-1]
    assert checked[-1] > expiry and checked[-1] > checked[0]
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM discussion_turns")).scalar_one() == 0
        assert (
            conn.execute(
                text(
                    "SELECT count(*) FROM discussion_command_receipts WHERE "
                    "command_name='APPEND_TURN'"
                )
            ).scalar_one()
            == 0
        )
    print(
        "PR219_SECOND_WAIT_EXPIRY",
        {
            "tx_started_at": str(started),
            "expiry_at": str(expiry),
            "lock_wait_started_at": str(witness["observed_at"]),
            "lock_acquired_at": str(acquired[-1]),
            "initial_authorization_checked_at": str(checked[0]),
            "authorization_checked_at": str(checked[-1]),
            "turns": 0,
            "append_receipts": 0,
        },
    )


discussion_database_url = _discussion_database_url
discussion_env = _discussion_env
pr219_discussion_env = _pr219_discussion_env
