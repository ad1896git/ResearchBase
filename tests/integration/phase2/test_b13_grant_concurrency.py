"""Real PostgreSQL isolation, lock-free history and bounded retry witnesses."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import event, text

from researchbase.application.approval import EvaluateApprovalGrantCommand
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.approval_repository import B13_APPROVAL_SQL, B13_SHARE_SQL
from tests.integration.phase2.test_b13_grant_consumption import (
    approval_env as approval_env,
)
from tests.integration.phase2.test_b13_grant_consumption import (
    conclusion_env as conclusion_env,
)
from tests.integration.phase2.test_b13_grant_consumption import (
    counts,
    issued,
)
from tests.integration.phase2.test_b13_grant_consumption import (
    decision_env as decision_env,
)
from tests.integration.phase2.test_b13_grant_consumption import (
    phase2_database_url as phase2_database_url,
)

_FIXTURES = (approval_env, conclusion_env, decision_env, phase2_database_url)
pytestmark = pytest.mark.integration
pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)


def test_first_statement_inventory_isolation_and_lock_free_history(approval_env):
    owner, actor, cmd, _ = issued(approval_env)
    engine = approval_env[-1][-1][8]
    statements = []

    def capture(conn, cursor, statement, parameters, context, executemany):
        statements.append(
            (statement, cursor.connection.isolation_level.name, cursor.connection.read_only)
        )

    event.listen(engine, "before_cursor_execute", capture)
    try:
        result = owner.record_internal_scientific_release(actor, cmd)
        writer = [(s, i, r) for s, i, r in statements if i == "SERIALIZABLE"]
        assert [row[0] for row in writer[:3]] == [
            B13_SHARE_SQL,
            "LOCK TABLE publications IN SHARE ROW EXCLUSIVE MODE",
            B13_APPROVAL_SQL,
        ]
        statements.clear()
        assert owner.record_internal_scientific_release(actor, cmd) == result
        assert (
            approval_env[0].get_grant_consumption(actor, cmd.project_id, cmd.command_key) == result
        )
        assert approval_env[0].get_grant(actor, cmd.project_id, cmd.grant_id).status == "CONSUMED"
        assert statements and all(i == "REPEATABLE_READ" and r for _, i, r in statements)
        assert all(
            all(
                word not in s.upper()
                for word in (
                    "LOCK TABLE",
                    "ADVISORY",
                    "FOR SHARE",
                    "FOR UPDATE",
                    "INSERT INTO",
                    "UPDATE APPROVAL",
                    "DELETE FROM",
                )
            )
            for s, _, _ in statements
        )
        statements.clear()
        approval_env[0].evaluate_approval_grant(
            actor, EvaluateApprovalGrantCommand(cmd.project_id, cmd.grant_id)
        )
        assert [row[0] for row in statements[:3]] == [
            B13_SHARE_SQL,
            "LOCK TABLE publications IN SHARE ROW EXCLUSIVE MODE",
            B13_APPROVAL_SQL,
        ]
        assert all(i == "READ_COMMITTED" and not r for _, i, r in statements)
    finally:
        event.remove(engine, "before_cursor_execute", capture)


@pytest.mark.parametrize("same_key", [True, False])
def test_racing_consumers_have_exactly_one_result(approval_env, same_key):
    owner, actor, cmd, _ = issued(approval_env)
    barrier = Barrier(2)

    def run(command):
        barrier.wait(timeout=5)
        try:
            return owner.record_internal_scientific_release(actor, command)
        except ResearchBaseError as error:
            return error.code

    with ThreadPoolExecutor(2) as pool:
        futures = [
            pool.submit(run, cmd),
            pool.submit(run, cmd if same_key else replace(cmd, command_key=uuid4())),
        ]
        results = [f.result(timeout=20) for f in futures]
    if same_key:
        assert results[0] == results[1]
    else:
        assert sum(r == ErrorCode.GRANT_INVALID for r in results) == 1
    assert counts(approval_env) == (1, 2, 1)


@pytest.mark.parametrize("retryable,expected", [(True, 3), (False, 1)])
def test_only_retryable_sqlstates_have_three_total_attempts(
    approval_env, monkeypatch, retryable, expected
):
    from researchbase.application.approval import ApprovalService

    owner, actor, cmd, _ = issued(approval_env)
    attempts = []

    def fail(self, principal, command):
        attempts.append(command.command_key)
        raise ResearchBaseError(
            ErrorCode.CONCURRENT_MODIFICATION, "injected", {"retryable_b13": retryable}
        )

    monkeypatch.setattr(ApprovalService, "_release_once", fail)
    with pytest.raises(ResearchBaseError):
        owner.record_internal_scientific_release(actor, cmd)
    assert len(attempts) == expected
    assert counts(approval_env) == (0, 1, 1)


def test_real_table_wait_crosses_credential_expiry_without_effect(approval_env):
    from tests.integration.phase2.test_pr2_14_internal_review import _wait_for_pg_blocker

    owner, actor, cmd, _ = issued(approval_env)
    engine = approval_env[-1][-1][8]
    registry = approval_env[-1][-1][9]
    with engine.connect() as holder:
        holder.execute(text("BEGIN"))
        holder.execute(text("LOCK TABLE internal_review_records IN ROW EXCLUSIVE MODE"))
        pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
        with ThreadPoolExecutor(1) as pool:
            future = pool.submit(owner.record_internal_scientific_release, actor, cmd)
            _wait_for_pg_blocker(engine, pid, "relation")
            registry.enabled = False
            holder.rollback()
            with pytest.raises(ResearchBaseError) as error:
                future.result(timeout=15)
            assert error.value.code == ErrorCode.FORBIDDEN
    registry.enabled = True
    assert counts(approval_env) == (0, 1, 1)


@pytest.mark.parametrize("maintenance", ["revoke", "evaluate"])
@pytest.mark.parametrize("maintenance_first", [False, True])
def test_consume_and_maintenance_both_lock_orders(
    approval_env, monkeypatch, maintenance, maintenance_first
):
    from threading import Event

    from researchbase.application.approval import RevokeApprovalGrantCommand
    from researchbase.persistence.approval_repository import SqlAlchemyApprovalRepository
    from tests.integration.phase2.test_pr2_14_internal_review import _wait_for_pg_blocker

    owner, actor, cmd, _ = issued(approval_env)
    engine = approval_env[-1][-1][8]
    held, release = Event(), Event()
    original = SqlAlchemyApprovalRepository.prepare_write
    holder = []

    def hold(self):
        original(self)
        if not holder:
            holder.append(self._session.execute(text("SELECT pg_backend_pid()")).scalar_one())
            held.set()
            assert release.wait(10)

    monkeypatch.setattr(SqlAlchemyApprovalRepository, "prepare_write", hold)

    def maintain():
        if maintenance == "revoke":
            return approval_env[0].revoke_approval_grant(
                actor, RevokeApprovalGrantCommand(cmd.project_id, cmd.grant_id, "Owner revoke")
            )
        return approval_env[0].evaluate_approval_grant(
            actor, EvaluateApprovalGrantCommand(cmd.project_id, cmd.grant_id)
        )

    def consume():
        return owner.record_internal_scientific_release(actor, cmd)

    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(maintain if maintenance_first else consume)
        assert held.wait(10)
        second = pool.submit(consume if maintenance_first else maintain)
        try:
            _wait_for_pg_blocker(engine, holder[0], "relation")
        finally:
            release.set()
        first.result(timeout=15)
        if maintenance_first and maintenance == "revoke":
            with pytest.raises(ResearchBaseError) as error:
                second.result(timeout=15)
            assert error.value.code == ErrorCode.GRANT_INVALID
            assert counts(approval_env) == (0, 2, 1)
        else:
            second.result(timeout=15)
            assert counts(approval_env) == (1, 2, 1)


@pytest.mark.parametrize("table", ["publications", "approval_requests", "internal_review_records"])
def test_w_and_a_and_n_waits_precede_first_serializable_snapshot(approval_env, table, monkeypatch):
    from researchbase.persistence.approval_repository import SqlAlchemyApprovalRepository
    from tests.integration.phase2.test_pr2_14_internal_review import _wait_for_pg_blocker

    owner, actor, cmd, _ = issued(approval_env)
    engine = approval_env[-1][-1][8]
    # backend_xmin may reflect catalog lookup snapshots during LOCK TABLE. A
    # committed-row witness proves the first data snapshot, independent of that.
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE b13_snapshot_witness(value integer)"))
    seen = []
    original = SqlAlchemyApprovalRepository.prepare_write

    def inspect_snapshot(self):
        original(self)
        seen.append(
            self._session.execute(text("SELECT count(*) FROM b13_snapshot_witness")).scalar_one()
        )

    monkeypatch.setattr(SqlAlchemyApprovalRepository, "prepare_write", inspect_snapshot)
    with engine.connect() as holder:
        holder.execute(text("LOCK TABLE " + table + " IN ROW EXCLUSIVE MODE"))
        pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
        with ThreadPoolExecutor(1) as pool:
            future = pool.submit(owner.record_internal_scientific_release, actor, cmd)
            try:
                _wait_for_pg_blocker(engine, pid, "relation")
                holder.execute(text("INSERT INTO b13_snapshot_witness VALUES (1)"))
            finally:
                holder.commit()
            future.result(timeout=15)
    assert seen == [1]
    assert counts(approval_env) == (1, 2, 1)


@pytest.mark.parametrize(
    "state,expected", [("40001", 3), ("40P01", 3), ("55P03", 1), ("57014", 1), ("23505", 1)]
)
def test_actual_sqlstate_classification_and_fresh_uows(approval_env, monkeypatch, state, expected):
    from sqlalchemy.exc import DBAPIError

    from researchbase.persistence.approval_repository import SqlAlchemyApprovalRepository

    owner, actor, cmd, _ = issued(approval_env)
    sessions = []

    class DriverError(Exception):
        sqlstate = state

    def fail(self):
        sessions.append(self._session)
        raise DBAPIError("redacted", {}, DriverError())

    monkeypatch.setattr(SqlAlchemyApprovalRepository, "prepare_write", fail)
    with pytest.raises(ResearchBaseError):
        owner.record_internal_scientific_release(actor, cmd)
    assert len(sessions) == expected and len({id(s) for s in sessions}) == expected
    assert counts(approval_env) == (0, 1, 1)


@pytest.mark.parametrize("lock", ["inventory", "scope", "target", "grant", "deferred_actor_fk"])
def test_real_wait_crosses_grant_expiry_with_zero_partial_history(approval_env, lock):
    from datetime import timedelta
    from time import monotonic, sleep

    from tests.integration.phase2.test_pr2_14_internal_review import _wait_for_pg_blocker

    engine = approval_env[-1][-1][8]
    with engine.connect() as conn:
        until = conn.execute(text("SELECT clock_timestamp()")).scalar_one() + timedelta(seconds=2)
    owner, actor, cmd, _ = issued(approval_env, expiry=until)
    with engine.connect() as holder:
        if lock == "inventory":
            holder.execute(text("LOCK TABLE internal_review_records IN ROW EXCLUSIVE MODE"))
            kind = "relation"
        elif lock == "scope":
            holder.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
                {"key": f"pr216:scope:{cmd.project_id}:INTERNAL_SCIENTIFIC_RELEASE"},
            )
            kind = "advisory"
        else:
            table, identity = {
                "target": ("scientific_conclusion_versions", cmd.result_id),
                "grant": ("approval_grants", cmd.grant_id),
                "deferred_actor_fk": ("actors", actor.actor_id),
            }[lock]
            holder.execute(
                text("SELECT id FROM " + table + " WHERE id=:id FOR UPDATE"), {"id": identity}
            )
            kind = "transactionid"
        pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
        with ThreadPoolExecutor(1) as pool:
            future = pool.submit(owner.record_internal_scientific_release, actor, cmd)
            try:
                witness = _wait_for_pg_blocker(engine, pid, kind)
                assert witness["observed_at"] < until
                deadline = monotonic() + 5
                while holder.execute(text("SELECT clock_timestamp()")).scalar_one() < until:
                    assert monotonic() < deadline
                    sleep(0.01)
            finally:
                holder.rollback()
            with pytest.raises(ResearchBaseError) as error:
                future.result(timeout=15)
            assert error.value.code == ErrorCode.GRANT_INVALID
    assert counts(approval_env) == (0, 1, 1)


@pytest.mark.parametrize("authority", ["issuer", "caller", "issuer_and_grant"])
def test_authority_expiry_during_late_fk_wait_denies_without_hidden_maintenance(
    approval_env, authority
):
    from time import monotonic, sleep

    from tests.integration.phase2.test_pr2_14_internal_review import _wait_for_pg_blocker

    engine = approval_env[-1][-1][8]
    # This deadline includes grant issuance and role-event provisioning before
    # the observed FK wait. Allow that setup under six concurrent suite shards;
    # stay below the production 10s lock timeout and retain all assertions.
    with engine.connect() as conn:
        until = conn.execute(text("SELECT clock_timestamp()+interval '6 seconds'")).scalar_one()
    owner, actor, cmd, _ = issued(
        approval_env, expiry=until if authority == "issuer_and_grant" else None
    )
    target = actor if authority == "caller" else approval_env[2]
    target_role = "OWNER" if authority == "caller" else "APPROVER"
    with engine.begin() as conn:
        role = conn.execute(
            text("""UPDATE project_role_assignments SET effective_until=:until,
          row_version=row_version+1 WHERE actor_id=:actor AND role=:role RETURNING id"""),
            {"until": until, "actor": target.actor_id, "role": target_role},
        ).scalar_one()
        conn.execute(
            text("""INSERT INTO project_role_events
          (id,role_assignment_id,actor_id,event_kind,occurred_at,reason,request_id)
          VALUES(:id,:role,:actor,'CLOSED',:at,'Scheduled issuer expiry',:key)"""),
            {"id": uuid4(), "role": role, "actor": target.actor_id, "at": until, "key": uuid4()},
        )
    with engine.connect() as holder, ThreadPoolExecutor(1) as pool:
        holder.execute(
            text("SELECT id FROM actors WHERE id=:id FOR UPDATE"), {"id": actor.actor_id}
        )
        pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
        future = pool.submit(owner.record_internal_scientific_release, actor, cmd)
        try:
            witness = _wait_for_pg_blocker(engine, pid, "transactionid")
            assert witness["observed_at"] < until
            deadline = monotonic() + 10
            while holder.execute(text("SELECT clock_timestamp()")).scalar_one() < until:
                assert monotonic() < deadline
                sleep(0.01)
        finally:
            holder.rollback()
        with pytest.raises(ResearchBaseError) as error:
            future.result(timeout=15)
        assert (
            error.value.code
            == {
                "issuer": ErrorCode.GRANT_STALE,
                "caller": ErrorCode.FORBIDDEN,
                "issuer_and_grant": ErrorCode.GRANT_INVALID,
            }[authority]
        )
    assert counts(approval_env) == (0, 1, 1)
    evaluator = approval_env[-1][2] if authority == "caller" else actor
    result = approval_env[0].evaluate_approval_grant(
        evaluator, EvaluateApprovalGrantCommand(cmd.project_id, cmd.grant_id)
    )
    assert (
        result.grant.status
        == {"issuer": "STALE", "caller": "ACTIVE", "issuer_and_grant": "EXPIRED"}[authority]
    )
    assert counts(approval_env) == ((0, 1, 1) if authority == "caller" else (0, 2, 1))
