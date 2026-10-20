"""B10 transaction statements and independent PostgreSQL backend races."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import event, text

from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.approval_repository import B09_SHARE_SQL
from tests.integration.phase2 import test_b10_reconsideration as fixtures
from tests.integration.phase2.test_pr2_14_internal_review import _wait_for_pg_blocker

approval_env = fixtures.approval_env
conclusion_env = fixtures.conclusion_env
decision_env = fixtures.decision_env
phase2_database_url = fixtures.phase2_database_url
reconsideration_env = fixtures.reconsideration_env
pytestmark = pytest.mark.integration


def test_first_statement_isolation_and_lock_free_read_replay(reconsideration_env):
    service, command, actor, approval = reconsideration_env
    engine = approval[-1][-1][8]
    statements = []

    def capture(conn, cursor, statement, parameters, context, many):
        statements.append(
            (statement, cursor.connection.isolation_level.name, cursor.connection.read_only)
        )

    event.listen(engine, "before_cursor_execute", capture)
    try:
        saved = service.record_rejection_reconsideration(command, actor)
        share = [i for i, r in enumerate(statements) if r[0] == B09_SHARE_SQL]
        assert len(share) == 1
        first_write = share[0]
        assert statements[first_write][1:] == ("READ_COMMITTED", False)
        assert all(r[1:] == ("REPEATABLE_READ", True) for r in statements[:first_write])
        assert statements[first_write + 1][0] == "SET LOCAL lock_timeout='10s'"
        assert statements[first_write + 2][0] == "SET LOCAL statement_timeout='30s'"
        statements.clear()
        assert service.record_rejection_reconsideration(command, actor) == saved
        assert service.get_rejection_reconsideration(command.project_id, saved.id, actor) == saved
        assert statements and all(r[1:] == ("REPEATABLE_READ", True) for r in statements)
        assert not any(
            any(
                word in row[0].upper()
                for word in (
                    "LOCK TABLE",
                    "ADVISORY",
                    "FOR SHARE",
                    "FOR UPDATE",
                    "INSERT ",
                    "UPDATE ",
                    "DELETE ",
                )
            )
            for row in statements
        )
    finally:
        event.remove(engine, "before_cursor_execute", capture)


@pytest.mark.parametrize("changed", [False, True])
def test_same_uuid_competing_writers_replay_identically(reconsideration_env, monkeypatch, changed):
    service, command, actor, approval = reconsideration_env
    barrier = Barrier(2)
    original = service._record_reconsideration_once

    def together(command, principal):
        barrier.wait(timeout=5)
        return original(command, principal)

    monkeypatch.setattr(service, "_record_reconsideration_once", together)
    with ThreadPoolExecutor(max_workers=2) as pool:
        other = (
            replace(command, rationale=command.rationale + " Additional explanation.")
            if changed
            else command
        )
        futures = [
            pool.submit(service.record_rejection_reconsideration, row, actor)
            for row in (command, other)
        ]
        results = []
        for future in futures:
            try:
                results.append(future.result(timeout=15))
            except ResearchBaseError as exc:
                results.append(exc.code)
    if changed:
        assert sum(isinstance(r, ErrorCode) for r in results) == 1
        assert ErrorCode.IDEMPOTENCY_CONFLICT in results
    else:
        assert results[0] == results[1]
    with approval[-1][-1][8].connect() as conn:
        assert (
            conn.execute(
                text("SELECT count(*) FROM decision_records WHERE id=:id"), {"id": command.id}
            ).scalar_one()
            == 1
        )


def test_two_successors_compete_for_one_reconsideration(reconsideration_env):
    service, command, actor, approval = reconsideration_env
    saved = service.record_rejection_reconsideration(command, actor)
    approvals, requester, _, old, _ = approval
    barrier = Barrier(2)

    def submit():
        successor = replace(
            old, id=uuid4(), prior_rejected_request_id=old.id, reconsideration_decision_id=saved.id
        )
        barrier.wait(timeout=5)
        try:
            return approvals.request_approval(requester, successor)
        except ResearchBaseError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: submit(), range(2)))
    assert sum(not isinstance(r, ErrorCode) for r in results) == 1
    assert ErrorCode.IDEMPOTENCY_CONFLICT in results


@pytest.mark.parametrize("lock", ["inventory", "scope", "target"])
def test_credential_loss_across_first_inventory_wait_rolls_back(reconsideration_env, lock):
    service, command, actor, approval = reconsideration_env
    base = approval[-1][-1]
    engine = base[8]
    with engine.connect() as holder, ThreadPoolExecutor(max_workers=1) as pool:
        tx = holder.begin()
        if lock == "inventory":
            holder.execute(text("LOCK TABLE actors IN ROW EXCLUSIVE MODE"))
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
        pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
        future = pool.submit(service.record_rejection_reconsideration, command, actor)
        witness = _wait_for_pg_blocker(
            engine,
            pid,
            {"inventory": "relation", "scope": "advisory", "target": "transactionid"}[lock],
        )
        assert witness["pid"] != pid
        base[9].principals.pop(actor.actor_id)
        tx.commit()
        with pytest.raises(ResearchBaseError) as denied:
            future.result(timeout=10)
        assert denied.value.code is ErrorCode.FORBIDDEN
    with engine.connect() as conn:
        assert (
            conn.execute(
                text("SELECT count(*) FROM decision_records WHERE id=:id"), {"id": command.id}
            ).scalar_one()
            == 0
        )


def test_uncertain_commit_recovers_with_same_uuid(reconsideration_env, monkeypatch):
    service, command, actor, approval = reconsideration_env
    original = service._record_reconsideration_once
    observed = []

    def lose_response(command, principal):
        observed.append(original(command, principal))
        raise RuntimeError("TEST ONLY response lost after committed transaction")

    monkeypatch.setattr(service, "_record_reconsideration_once", lose_response)
    with pytest.raises(RuntimeError):
        service.record_rejection_reconsideration(command, actor)
    assert service.record_rejection_reconsideration(command, actor) == observed[0]
    with approval[-1][-1][8].connect() as conn:
        assert (
            conn.execute(
                text("SELECT count(*) FROM decision_records WHERE id=:id"), {"id": command.id}
            ).scalar_one()
            == 1
        )
