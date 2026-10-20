"""F9 concrete internal release consumption; READY/package effects stay blocked."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from threading import Event
from uuid import uuid4

import pytest
from sqlalchemy import event, text

from researchbase.application.approval import ApprovalService, RevokeApprovalGrantCommand
from researchbase.application.internal_review import ReviewIssueRequest
from researchbase.application.scientific_conclusion import ScientificConclusionService
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.approval_repository import (
    B13_APPROVAL_SQL,
    B13_SHARE_SQL,
    SqlAlchemyApprovalRepository,
)
from tests.integration.phase2.b30_observations import (
    assert_first_share,
    assert_snapshot_read,
    poll_db_clock,
    sql_protocol,
)
from tests.integration.phase2.pr2_19_support import counts
from tests.integration.phase2.test_b13_grant_consumption import (
    approval_env,
    conclusion_env,
    decision_env,
    issued,
    phase2_database_url,
)
from tests.integration.phase2.test_pr2_14_internal_review import _wait_for_pg_blocker
from tests.integration.phase2.test_pr2_15_decision import _review, _stale

_FIXTURES = (approval_env, conclusion_env, decision_env, phase2_database_url)
pytestmark = pytest.mark.integration


def fresh(env):
    base = env[-1][-1]
    return ScientificConclusionService(base[1], base[9], base[2]), ApprovalService(
        base[1], base[9], base[2]
    )


def test_exact_receipt_replay_is_snapshot_only_after_write_authority_loss(approval_env):
    from researchbase.application.phase2_identity import AssignProjectRole, CloseProjectRole
    from tests.integration.phase2.test_pr2_00_challenges import _service

    owner, actor, cmd, grant = issued(approval_env)
    base = approval_env[-1][-1]
    with sql_protocol(base[8]) as statements:
        saved = owner.record_internal_scientific_release(actor, cmd)
    assert_first_share(statements, B13_SHARE_SQL, "SERIALIZABLE")
    writes = [s for s, _, r in statements if not r]
    assert writes[:3] == [
        B13_SHARE_SQL,
        "LOCK TABLE publications IN SHARE ROW EXCLUSIVE MODE",
        B13_APPROVAL_SQL,
    ]
    assert (
        saved.grant_id == grant.id
        and saved.result.scientific_conclusion_version_id == cmd.result_id
    )
    identity, _, _ = _service(str(base[8].url))
    identity.assign_project_role(
        AssignProjectRole(
            approval_env[-1][2],
            cmd.project_id,
            actor.actor_id,
            "VIEWER",
            "Historical receipt reader",
            uuid4(),
        )
    )
    with base[8].connect() as conn:
        role = conn.execute(
            text("SELECT id FROM project_role_assignments WHERE actor_id=:id AND role='OWNER'"),
            {"id": actor.actor_id},
        ).scalar_one()
    identity.close_project_role(
        CloseProjectRole(approval_env[-1][2], cmd.project_id, role, "Close writer", uuid4())
    )
    owner, reader = fresh(approval_env)
    before = counts(base[8])
    with sql_protocol(base[8]) as statements:
        assert owner.record_internal_scientific_release(actor, cmd) == saved
        assert reader.get_grant_consumption(actor, cmd.project_id, cmd.command_key) == saved
        assert reader.get_grant(actor, cmd.project_id, grant.id).status == "CONSUMED"
    assert_snapshot_read(statements)
    assert counts(base[8]) == before
    del base[9].principals[actor.actor_id]
    with pytest.raises(ResearchBaseError) as denied:
        owner.record_internal_scientific_release(actor, cmd)
    assert denied.value.code is ErrorCode.FORBIDDEN
    assert counts(base[8]) == before


@pytest.mark.parametrize(
    "condition,code",
    [
        ("missing", ErrorCode.NOT_FOUND),
        ("revoked", ErrorCode.GRANT_INVALID),
        ("stale", ErrorCode.GRANT_STALE),
        ("consumed", ErrorCode.GRANT_INVALID),
        ("blocker", ErrorCode.GRANT_STALE),
    ],
)
def test_unusable_grant_has_no_partial_receipt_or_terminalization(approval_env, condition, code):
    owner, actor, cmd, _ = issued(approval_env)
    base = approval_env[-1][-1]
    if condition == "missing":
        cmd = replace(cmd, grant_id=uuid4())
    elif condition == "revoked":
        approval_env[0].revoke_approval_grant(
            actor, RevokeApprovalGrantCommand(cmd.project_id, cmd.grant_id, "Test owner revocation")
        )
    elif condition == "stale":
        _stale(approval_env[-1])
    elif condition == "consumed":
        owner.record_internal_scientific_release(actor, cmd)
        cmd = replace(cmd, command_key=uuid4())
    else:
        _review(
            approval_env[-1],
            "REJECT",
            (ReviewIssueRequest("BLOCKING", "OVERCLAIM", "Later concern"),),
        )
    before = counts(base[8])
    owner, reader = fresh(approval_env)
    with pytest.raises(ResearchBaseError) as denied:
        owner.record_internal_scientific_release(actor, cmd)
    assert denied.value.code is code
    assert counts(base[8]) == before
    if condition != "missing":
        assert reader.get_grant(actor, cmd.project_id, cmd.grant_id).id == cmd.grant_id
    assert counts(base[8]) == before


@pytest.mark.parametrize("stage", ["insert_consumption", "terminalize", "force_constraints"])
def test_receipt_and_terminal_event_rollback_then_fresh_recovery(approval_env, monkeypatch, stage):
    owner, actor, cmd, _ = issued(approval_env)
    base = approval_env[-1][-1]
    before = counts(base[8])
    original = getattr(SqlAlchemyApprovalRepository, stage)

    def fail(self, *args, **kwargs):
        original(self, *args, **kwargs)
        raise RuntimeError("B30 protected release fault")

    with monkeypatch.context() as patch:
        patch.setattr(SqlAlchemyApprovalRepository, stage, fail)
        with pytest.raises(RuntimeError, match="B30"):
            owner.record_internal_scientific_release(actor, cmd)
    assert counts(base[8]) == before
    owner, reader = fresh(approval_env)
    assert reader.get_grant(actor, cmd.project_id, cmd.grant_id).status == "ACTIVE"
    result = owner.record_internal_scientific_release(actor, cmd)
    assert reader.get_grant_consumption(actor, cmd.project_id, cmd.command_key) == result


@pytest.mark.parametrize("same_key", [False, True])
def test_two_backends_wait_then_single_grant_winner(approval_env, same_key):
    owner, actor, cmd, _ = issued(approval_env)
    engine = approval_env[-1][-1][8]
    held, release = Event(), Event()
    pids = []

    def pause(conn, cursor, sql, parameters, context, executemany):
        if sql == B13_APPROVAL_SQL and not held.is_set():
            pids.append(conn.execute(text("SELECT pg_backend_pid()")).scalar_one())
            held.set()
            assert release.wait(15)

    event.listen(engine, "after_cursor_execute", pause)
    try:
        with ThreadPoolExecutor(2) as pool:
            first = pool.submit(owner.record_internal_scientific_release, actor, cmd)
            try:
                assert held.wait(10)
                second_owner, _ = fresh(approval_env)
                second_cmd = cmd if same_key else replace(cmd, command_key=uuid4())
                second = pool.submit(
                    second_owner.record_internal_scientific_release, actor, second_cmd
                )
                witness = _wait_for_pg_blocker(engine, pids[0], "relation")
                assert witness["pid"] != pids[0] and not second.done()
            finally:
                release.set()
            saved = first.result(timeout=20)
            if same_key:
                assert second.result(timeout=20) == saved
            else:
                with pytest.raises(ResearchBaseError) as denied:
                    second.result(timeout=20)
                assert denied.value.code is ErrorCode.GRANT_INVALID
    finally:
        release.set()
        event.remove(engine, "after_cursor_execute", pause)
    _, reader = fresh(approval_env)
    assert reader.get_grant_consumption(actor, cmd.project_id, cmd.command_key) == saved
    assert counts(engine, ("approval_grant_consumptions", "approval_grant_events")) == {
        "approval_grant_consumptions": 1,
        "approval_grant_events": 2,
    }


def test_observed_inventory_wait_crosses_credential_expiry(approval_env):
    owner, actor, cmd, _ = issued(approval_env)
    base = approval_env[-1][-1]
    engine, registry = base[8], base[9]
    checked = []
    with engine.connect() as observer:
        expiry = observer.execute(text("SELECT clock_timestamp()")).scalar_one() + timedelta(
            seconds=5
        )

    class Expiring:
        def is_valid(self, principal, at):
            checked.append(at)
            return at < expiry and registry.is_valid(principal, at)

    owner = ScientificConclusionService(base[1], Expiring(), base[2])
    before = counts(engine)
    with engine.connect() as holder:
        holder.execute(text("LOCK TABLE internal_review_records IN ROW EXCLUSIVE MODE"))
        pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
        with ThreadPoolExecutor(1) as pool:
            future = pool.submit(owner.record_internal_scientific_release, actor, cmd)
            try:
                witness = _wait_for_pg_blocker(engine, pid, "relation")
                with engine.connect() as observer:
                    started, waited = observer.execute(
                        text(
                            "SELECT xact_start,clock_timestamp() FROM pg_stat_activity "
                            "WHERE pid=:pid"
                        ),
                        {"pid": witness["pid"]},
                    ).one()
                    assert started < expiry and waited < expiry
                    acquired_after = poll_db_clock(observer, expiry)
            finally:
                holder.rollback()
            with pytest.raises(ResearchBaseError) as denied:
                future.result(timeout=15)
            assert denied.value.code is ErrorCode.FORBIDDEN
    assert checked[-1] >= acquired_after > expiry
    assert counts(engine) == before
    _, reader = fresh(approval_env)
    assert reader.get_grant(actor, cmd.project_id, cmd.grant_id).status == "ACTIVE"
    print(
        "B30_TEMP_AUTH",
        {
            "tx_started_at": str(started),
            "lock_wait_started_at": str(waited),
            "expiry_at": str(expiry),
            "release_at": str(acquired_after),
            "authorization_checked_at": str(checked[-1]),
        },
    )


def test_expired_grant_denies_without_implicit_terminalization(approval_env):
    base = approval_env[-1][-1]
    with base[8].connect() as conn:
        expiry = conn.execute(text("SELECT clock_timestamp()")).scalar_one() + timedelta(seconds=5)
    _, actor, cmd, _ = issued(approval_env, expiry=expiry)
    before = counts(base[8])
    with base[8].connect() as conn:
        poll_db_clock(conn, expiry)
    owner, reader = fresh(approval_env)
    with pytest.raises(ResearchBaseError) as denied:
        owner.record_internal_scientific_release(actor, cmd)
    assert denied.value.code is ErrorCode.GRANT_INVALID
    assert counts(base[8]) == before
    grant = reader.get_grant(actor, cmd.project_id, cmd.grant_id)
    assert grant.status == "ACTIVE" and not grant.usable
    assert counts(base[8]) == before


@pytest.mark.parametrize("expiry_kind", ["grant", "caller_role", "issuer_role"])
def test_observed_wait_crosses_grant_or_role_expiry_without_partial_effect(
    approval_env, expiry_kind
):
    base = approval_env[-1][-1]
    engine = base[8]
    with engine.connect() as conn:
        expiry = conn.execute(text("SELECT clock_timestamp()")).scalar_one() + timedelta(seconds=8)
    owner, actor, cmd, _ = issued(approval_env, expiry=expiry if expiry_kind == "grant" else None)
    if expiry_kind != "grant":
        target = actor if expiry_kind == "caller_role" else approval_env[2]
        role_kind = "OWNER" if expiry_kind == "caller_role" else "APPROVER"
        # Same legal scheduled-role fixture as the B09/B13 owner tests; this is
        # audited role history, never fabricated grant/consent/scientific state.
        with engine.begin() as conn:
            role_id = conn.execute(
                text("""UPDATE project_role_assignments
                SET effective_until=:until,row_version=row_version+1
                WHERE actor_id=:actor AND role=:role RETURNING id"""),
                {"until": expiry, "actor": target.actor_id, "role": role_kind},
            ).scalar_one()
            conn.execute(
                text("""INSERT INTO project_role_events
                (id,role_assignment_id,actor_id,event_kind,occurred_at,reason,request_id)
                VALUES(:id,:role,:actor,'CLOSED',:at,'B30 scheduled role expiry',:request)"""),
                {
                    "id": uuid4(),
                    "role": role_id,
                    "actor": target.actor_id,
                    "at": expiry,
                    "request": uuid4(),
                },
            )
    checked = []
    registry = base[9]

    class ObservedCredentials:
        def is_valid(self, principal, at):
            checked.append(at)
            return registry.is_valid(principal, at)

    owner = ScientificConclusionService(base[1], ObservedCredentials(), base[2])
    before = counts(engine)
    with engine.connect() as holder:
        # Block the FIRST inventory statement. A late FK wait can be reached
        # only after expensive closure checks, making its pre-expiry witness
        # depend on machine load. The owning B13 suite separately covers late waits.
        holder.execute(text("LOCK TABLE internal_review_records IN ROW EXCLUSIVE MODE"))
        pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
        with ThreadPoolExecutor(1) as pool:
            future = pool.submit(owner.record_internal_scientific_release, actor, cmd)
            try:
                witness = _wait_for_pg_blocker(engine, pid, "relation")
                with engine.connect() as observer:
                    started = observer.execute(
                        text("SELECT xact_start FROM pg_stat_activity WHERE pid=:pid"),
                        {"pid": witness["pid"]},
                    ).scalar_one()
                    assert started < witness["observed_at"] < expiry
                    released = poll_db_clock(observer, expiry)
            finally:
                holder.rollback()
            with pytest.raises(ResearchBaseError) as denied:
                future.result(timeout=15)
            assert (
                denied.value.code
                is {
                    "grant": ErrorCode.GRANT_INVALID,
                    "caller_role": ErrorCode.FORBIDDEN,
                    "issuer_role": ErrorCode.GRANT_STALE,
                }[expiry_kind]
            )
    assert checked[-1] >= released > expiry
    assert counts(engine) == before
    _, reader = fresh(approval_env)
    entitled_reader = approval_env[-1][2] if expiry_kind == "caller_role" else actor
    assert reader.get_grant(entitled_reader, cmd.project_id, cmd.grant_id).status == "ACTIVE"
    assert counts(engine) == before
    print(
        "B30_ROLE_GRANT_WAIT",
        {
            "tx_started_at": str(started),
            "wait_observed_at": str(witness["observed_at"]),
            "expiry_at": str(expiry),
            "release_at": str(released),
            "authorization_checked_at": str(checked[-1]),
            "outcome": denied.value.code.value,
        },
    )
