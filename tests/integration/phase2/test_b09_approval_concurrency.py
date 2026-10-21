"""B09 transaction isolation, absence of read locks and observable writer waits."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Event
from uuid import uuid4

import pytest
from sqlalchemy import event, text

from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.approval_repository import (
    B09_DECIDE_SHARE_SQL,
    B09_SHARE_SQL,
    B09_SNAPSHOT_TABLES,
)
from researchbase.persistence.manuscript_freeze_repository import B04_SNAPSHOT_TABLES
from tests.integration.phase2 import test_approval as fixtures
from tests.integration.phase2.test_approval import (
    _counts,
    _decide,
)
from tests.integration.phase2.test_pr2_14_internal_review import _wait_for_pg_blocker

approval_env = fixtures.approval_env
conclusion_env = fixtures.conclusion_env
decision_env = fixtures.decision_env
phase2_database_url = fixtures.phase2_database_url

pytestmark = pytest.mark.integration


def test_literal_inventory():
    assert B09_SNAPSHOT_TABLES == tuple(
        sorted(
            set(B04_SNAPSHOT_TABLES)
            | {
                "manuscript_versions",
                "publications",
                "internal_review_records",
                "review_issues",
                "review_issue_events",
            }
        )
    )


def test_first_writer_statement_and_lock_free_reads_replay(approval_env):
    service, requester, approver, command, env = approval_env
    engine = env[-1][8]
    transactions = []

    def capture(conn, cursor, statement, parameters, context, many):
        if not transactions or transactions[-1][0] is not conn:
            transactions.append((conn, []))
        transactions[-1][1].append(statement)

    event.listen(engine, "before_cursor_execute", capture)
    try:
        saved = service.request_approval(requester, command)
        writer = next(sql for _, sql in transactions if B09_SHARE_SQL in sql)
        assert writer[0] == B09_SHARE_SQL
        transactions.clear()
        result = service.decide_approval(approver, _decide(command))
        writer = next(sql for _, sql in transactions if B09_DECIDE_SHARE_SQL in sql)
        assert writer[:2] == [
            B09_DECIDE_SHARE_SQL,
            "LOCK TABLE publications IN SHARE ROW EXCLUSIVE MODE",
        ]
        assert result.grant
        transactions.clear()
        service.get_request(requester, command.project_id, saved.id)
        service.get_decision(requester, command.project_id, result.id)
        service.get_grant(requester, command.project_id, result.grant.id)
        service.request_approval(requester, command)
        assert transactions
        for _, statements in transactions:
            assert not any(
                token in sql.upper()
                for sql in statements
                for token in (
                    "LOCK TABLE",
                    "FOR UPDATE",
                    "FOR SHARE",
                    "ADVISORY",
                    "INSERT ",
                    "UPDATE ",
                )
            )
        with engine.connect() as conn:
            assert conn.execute(text("SHOW server_version")).scalar_one().startswith("18.")
    finally:
        event.remove(engine, "before_cursor_execute", capture)


@pytest.mark.parametrize("lock", ["inventory", "scope", "target"])
def test_replay_does_not_wait_for_writer_exclusion(approval_env, lock):
    service, requester, _, command, env = approval_env
    saved = service.request_approval(requester, command)
    engine = env[-1][8]
    with engine.connect() as holder, ThreadPoolExecutor(max_workers=1) as pool:
        tx = holder.begin()
        if lock == "inventory":
            holder.execute(text("LOCK TABLE projects IN ROW EXCLUSIVE MODE"))
        elif lock == "scope":
            holder.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
                {"key": f"pr216:scope:{command.project_id}:{command.approval_purpose}"},
            )
        else:
            holder.execute(
                text("SELECT id FROM scientific_conclusion_versions WHERE id=:id FOR UPDATE"),
                {"id": command.scientific_conclusion_version_id},
            )
        try:
            assert (
                pool.submit(service.request_approval, requester, command).result(timeout=5) == saved
            )
        finally:
            tx.rollback()


@pytest.mark.parametrize("lock", ["inventory", "scope", "target"])
def test_rejection_waits_then_fences_new_requests(approval_env, lock):
    service, requester, approver, command, env = approval_env
    service.request_approval(requester, command)
    engine = env[-1][8]
    with engine.connect() as holder, ThreadPoolExecutor(max_workers=1) as pool:
        tx = holder.begin()
        pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
        if lock == "inventory":
            holder.execute(text("LOCK TABLE projects IN ROW EXCLUSIVE MODE"))
        elif lock == "scope":
            holder.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
                {"key": f"pr216:scope:{command.project_id}:{command.approval_purpose}"},
            )
        else:
            holder.execute(
                text("SELECT id FROM scientific_conclusion_versions WHERE id=:id FOR UPDATE"),
                {"id": command.scientific_conclusion_version_id},
            )
        future = pool.submit(service.decide_approval, approver, _decide(command, "REJECT"))
        try:
            witness = _wait_for_pg_blocker(
                engine,
                pid,
                "relation"
                if lock == "inventory"
                else ("advisory" if lock == "scope" else "transactionid"),
            )
            assert witness["pid"] != pid
            tx.commit()
            assert future.result(timeout=10).grant is None
        finally:
            if tx.is_active:
                tx.rollback()
    with pytest.raises(ResearchBaseError) as denied:
        service.request_approval(requester, replace(command, id=uuid4()))
    assert denied.value.code is ErrorCode.REJECTION_RECONSIDERATION_REQUIRED


def test_same_uuid_concurrent_replay_has_one_history(approval_env):
    service, requester, _, command, _ = approval_env
    start = Event()

    def request():
        start.wait(5)
        return service.request_approval(requester, command)

    with ThreadPoolExecutor(max_workers=2) as pool:
        a, b = pool.submit(request), pool.submit(request)
        start.set()
        assert a.result(timeout=10) == b.result(timeout=10)
    assert _counts(approval_env) == (1, 1, 1, 0, 0, 0)


def other_target(env):
    from researchbase.application.approval import RequestApprovalCommand
    from researchbase.application.scientific_conclusion import ClaimInputRequest
    from tests.integration.phase2.test_pr2_11_r2_persistence import SCOPE
    from tests.integration.phase2.test_pr2_15_decision import _command, _review

    scientific, _, _, author, _, project, claim, _, _, _ = env[-1]
    target = scientific.create(
        author,
        project,
        "TEST ONLY concurrent target",
        SCOPE,
        "MODERATE",
        None,
        (ClaimInputRequest(claim, "SUPPORTS"),),
        (),
        uuid4(),
    )
    scientific.freeze(author, project, target.conclusion_id, target.version_id, uuid4())
    updated = (env[0], env[1], env[2], target, env[-1])
    review = _review(updated)
    basis = env[0].record_decision(env[2], _command(updated))
    return RequestApprovalCommand(uuid4(), project, target.version_id, basis.id, (review.id,))


@pytest.mark.parametrize("first", ["rejection", "request"])
def test_cross_target_rejection_request_both_commit_orders(approval_env, first):
    service, requester, approver, command, env = approval_env
    service.request_approval(requester, command)
    other = other_target(env)
    reject = _decide(command, "REJECT")
    engine = env[-1][8]
    inserted, release = Event(), Event()
    holder_pid = []
    held_id = reject.id if first == "rejection" else other.id
    table = "approval_decisions" if first == "rejection" else "approval_requests"

    def hold(conn, cursor, statement, parameters, context, many):
        if statement.startswith("INSERT INTO " + table) and parameters.get("id") == held_id:
            holder_pid.append(conn.connection.driver_connection.info.backend_pid)
            inserted.set()
            assert release.wait(10)

    event.listen(engine, "after_cursor_execute", hold)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            if first == "rejection":
                holder = pool.submit(service.decide_approval, approver, reject)
                assert inserted.wait(10)
                waiter = pool.submit(service.request_approval, requester, other)
            else:
                holder = pool.submit(service.request_approval, requester, other)
                assert inserted.wait(10)
                waiter = pool.submit(service.decide_approval, approver, reject)
            try:
                witness = _wait_for_pg_blocker(engine, holder_pid[0], "relation")
                assert witness["pid"] != holder_pid[0]
            finally:
                release.set()
            holder.result(timeout=10)
            with pytest.raises(ResearchBaseError) as denied:
                waiter.result(timeout=10)
            expected = (
                ErrorCode.REJECTION_RECONSIDERATION_REQUIRED
                if first == "rejection"
                else ErrorCode.APPROVAL_TARGET_STALE
            )
            assert denied.value.code is expected
    finally:
        release.set()
        event.remove(engine, "after_cursor_execute", hold)


def test_cross_target_rejection_fences_waiting_older_pending_decision(approval_env):
    from researchbase.domain.approval import approval_decision_material
    from researchbase.foundation.hashing import sha256_canonical_json

    service, requester, approver, command, env = approval_env
    service.request_approval(requester, command)
    other = other_target(env)
    saved = service.request_approval(requester, other)
    assert other.scientific_conclusion_version_id is not None
    engine = env[-1][8]
    digest = str(
        sha256_canonical_json(
            approval_decision_material(
                other.id,
                other.scientific_conclusion_version_id,
                saved.target_content_hash,
                "REJECT",
                None,
                False,
                "TEST ONLY scoped rejection",
                approver.actor_id,
            )
        )
    )
    with engine.connect() as holder, ThreadPoolExecutor(max_workers=1) as pool:
        tx = holder.begin()
        holder.execute(text(B09_SHARE_SQL))
        pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
        holder.execute(
            text("""INSERT INTO approval_decisions
          (id,approval_request_id,decision,rationale,decided_by,decided_at,hash_scheme,content_hash)
          VALUES (:id,:request,'REJECT','TEST ONLY scoped rejection',:actor,clock_timestamp(),
          'sha256-cjson-v1',:hash)"""),
            {"id": uuid4(), "request": other.id, "actor": approver.actor_id, "hash": digest},
        )
        future = pool.submit(service.decide_approval, approver, _decide(command))
        try:
            assert _wait_for_pg_blocker(engine, pid, "relation")["pid"] != pid
            tx.commit()
            with pytest.raises(ResearchBaseError) as denied:
                future.result(timeout=10)
            assert denied.value.code is ErrorCode.REJECTION_RECONSIDERATION_REQUIRED
        finally:
            if tx.is_active:
                tx.rollback()
    assert service.get_request(requester, command.project_id, command.id).status == "PENDING"


def test_scheduled_approver_expiry_after_real_grant_wait_rolls_back(approval_env):
    service, requester, approver, command, env = approval_env
    service.request_approval(requester, command)
    first = service.decide_approval(approver, _decide(command))
    assert first.grant
    next_command = replace(command, id=uuid4())
    service.request_approval(requester, next_command)
    engine = env[-1][8]
    with engine.begin() as conn:
        expiry = conn.execute(text("SELECT clock_timestamp()+interval '1 second'")).scalar_one()
        role = conn.execute(
            text("""UPDATE project_role_assignments SET effective_until=:expiry,
                 row_version=row_version+1 WHERE actor_id=:actor AND role='APPROVER'
                 RETURNING id"""),
            {"expiry": expiry, "actor": approver.actor_id},
        ).scalar_one()
        conn.execute(
            text("""INSERT INTO project_role_events
          (id,role_assignment_id,actor_id,event_kind,occurred_at,reason,request_id)
          VALUES (:id,:role,:actor,'CLOSED',:at,'TEST ONLY scheduled expiry',:request)"""),
            {
                "id": uuid4(),
                "role": role,
                "actor": approver.actor_id,
                "at": expiry,
                "request": uuid4(),
            },
        )
    before = _counts(approval_env)
    with engine.connect() as holder, ThreadPoolExecutor(max_workers=1) as pool:
        tx = holder.begin()
        pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
        holder.execute(
            text("SELECT id FROM approval_grants WHERE id=:id FOR UPDATE"), {"id": first.grant.id}
        )
        future = pool.submit(service.decide_approval, approver, _decide(next_command, "REJECT"))
        try:
            assert _wait_for_pg_blocker(engine, pid, "transactionid")["pid"] != pid
            holder.execute(
                text(
                    """SELECT pg_sleep(greatest(0,
                        extract(epoch FROM (:expiry-clock_timestamp())))+0.01)"""
                ),
                {"expiry": expiry},
            )
            tx.commit()
            with pytest.raises(ResearchBaseError) as denied:
                future.result(timeout=10)
            assert denied.value.code is ErrorCode.FORBIDDEN
        finally:
            if tx.is_active:
                tx.rollback()
    assert _counts(approval_env) == before
    current = service.get_grant(requester, command.project_id, first.grant.id)
    assert current.status == "ACTIVE" and current.unusable_code == "GRANT_STALE"


def test_actual_postgresql_transaction_settings(approval_env):
    factory = approval_env[-1][-1][1]
    with factory() as uow:
        uow.configure_approval_transaction(readonly=True)
        settings = uow._session.execute(
            text(
                """SELECT current_setting('transaction_isolation'),
                       current_setting('transaction_read_only')"""
            )
        ).one()
        assert settings == ("repeatable read", "on")
    with factory() as uow:
        uow.configure_approval_transaction()
        uow.approval.lock_snapshot()
        settings = uow._session.execute(
            text(
                """SELECT current_setting('transaction_isolation'),
                       current_setting('transaction_read_only')"""
            )
        ).one()
        assert settings == ("read committed", "off")


def test_uncertain_commit_recovers_only_original_uuid(approval_env, monkeypatch):
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork

    service, requester, _, command, _ = approval_env
    original = SqlAlchemyUnitOfWork.commit
    lost = []

    def uncertain(self):
        original(self)
        if not lost:
            lost.append(True)
            raise RuntimeError("TEST ONLY lost commit acknowledgement")

    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", uncertain)
    with pytest.raises(RuntimeError):
        service.request_approval(requester, command)
    assert _counts(approval_env) == (1, 1, 1, 0, 0, 0)
    assert service.request_approval(requester, command).id == command.id
    assert _counts(approval_env) == (1, 1, 1, 0, 0, 0)
