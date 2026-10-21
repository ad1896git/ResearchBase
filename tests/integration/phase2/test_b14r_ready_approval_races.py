"""Observed backend exclusion, post-wait authorization and atomic recovery."""

# SQL assertions preserve the literal lock and guard protocol.
# ruff: noqa: E501

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Barrier
from typing import Any, cast
from uuid import uuid4

import pytest
from sqlalchemy import event, text

from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.approval_repository import (
    B09_DECIDE_SHARE_SQL,
    B09_SHARE_SQL,
    SqlAlchemyApprovalRepository,
)
from tests.integration.phase2.test_b14r_ready_approval import (
    b04_env,
    b05_env,
    conclusion_env,
    counts,
    decide,
    phase2_database_url,
    setup,
)
from tests.integration.phase2.test_pr2_14_internal_review import _wait_for_pg_blocker
from tests.integration.phase2.test_revision_action import decision_env, revision_env

_FIXTURES = (b04_env, b05_env, conclusion_env, phase2_database_url, decision_env, revision_env)
pytestmark = pytest.mark.integration


def test_both_writer_prefixes_and_exact_target_parent_request_order(b05_env):
    env = b05_env
    app, cmd, actor = setup(env)
    statements = []

    def capture(conn, cursor, sql, params, context, many):
        if cursor.connection.isolation_level.name == "READ_COMMITTED":
            statements.append(sql)

    event.listen(env[5], "before_cursor_execute", capture)
    try:
        for deciding, action in enumerate(
            (
                lambda: app.request_approval(env[2], cmd),
                lambda: app.decide_approval(actor, decide(cmd)),
            )
        ):
            statements.clear()
            action()
            prefix = (
                [B09_SHARE_SQL]
                if not deciding
                else [
                    B09_DECIDE_SHARE_SQL,
                    "LOCK TABLE publications IN SHARE ROW EXCLUSIVE MODE",
                ]
            )
            assert statements[: len(prefix)] == prefix
            assert statements[len(prefix) : len(prefix) + 2] == [
                "SET LOCAL lock_timeout='10s'",
                "SET LOCAL statement_timeout='30s'",
            ]
            target = next(
                i
                for i, s in enumerate(statements)
                if "FROM manuscript_versions" in s and "FOR UPDATE" in s
            )
            parent = next(
                i for i, s in enumerate(statements) if "FROM publications" in s and "FOR SHARE" in s
            )
            assert target < parent
            saved = [
                i
                for i, s in enumerate(statements)
                if "FROM approval_requests" in s and "FOR UPDATE" in s
            ]
            if saved:
                assert parent < saved[0]
    finally:
        event.remove(env[5], "before_cursor_execute", capture)


@pytest.mark.parametrize(
    "kind", ["request_same", "request_competing", "decision_same", "decision_competing"]
)
def test_racing_uuid_and_request_have_one_winner(b05_env, kind):
    env = b05_env
    app, cmd, actor = setup(env)
    if kind.startswith("decision"):
        app.request_approval(env[2], cmd)
        first = decide(cmd)
        second = first if kind.endswith("same") else replace(first, id=uuid4())
        operation, caller = app.decide_approval, actor
    else:
        first = cmd
        second = first if kind.endswith("same") else replace(first, id=uuid4())
        operation, caller = app.request_approval, env[2]
    barrier = Barrier(2)

    def run(command):
        barrier.wait(timeout=10)
        try:
            return cast(Any, operation)(caller, command)
        except ResearchBaseError as error:
            return error.code

    with ThreadPoolExecutor(2) as pool:
        jobs = [pool.submit(run, c) for c in (first, second)]
        results = [job.result(timeout=30) for job in jobs]
    successes = [r for r in results if not isinstance(r, ErrorCode)]
    assert len(successes) == (2 if kind.endswith("same") else 1)
    if kind.endswith("same"):
        assert successes[0] == successes[1]
    else:
        assert ErrorCode.IDEMPOTENCY_CONFLICT in results
    assert counts(env) == (
        (1, 1, 2, 1, 1, 1) if kind.startswith("decision") else (1, 1, 1, 0, 0, 0)
    )


@pytest.mark.parametrize("lock", ["inventory", "scope", "target", "request", "actor_fk"])
def test_actual_wait_crosses_credential_expiry_with_zero_partial_history(b05_env, lock):
    env = b05_env
    app, cmd, actor = setup(env)
    app.request_approval(env[2], cmd)
    command = decide(cmd)
    before = counts(env)
    with env[5].connect() as holder, ThreadPoolExecutor(1) as pool:
        pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
        started, expiry = holder.execute(
            text("SELECT clock_timestamp(),clock_timestamp()+interval '0.8 seconds'")
        ).one()
        original = env[9].is_valid
        env[9].is_valid = lambda principal, at: original(principal, at) and (
            principal.actor_id != actor.actor_id or at < expiry
        )
        if lock == "inventory":
            holder.execute(text("LOCK TABLE review_issues IN ROW EXCLUSIVE MODE"))
        elif lock == "scope":
            holder.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
                dict(key=f"pr216:scope:{cmd.project_id}:READY_FOR_SUBMISSION"),
            )
        else:
            table, identity = {
                "target": ("manuscript_versions", cmd.manuscript_version_id),
                "request": ("approval_requests", cmd.id),
                "actor_fk": ("actors", actor.actor_id),
            }[lock]
            holder.execute(
                text(f"SELECT id FROM {table} WHERE id=:id FOR UPDATE"), dict(id=identity)
            )
        future = pool.submit(app.decide_approval, actor, command)
        try:
            witness = _wait_for_pg_blocker(
                env[5],
                pid,
                "relation"
                if lock == "inventory"
                else "advisory"
                if lock == "scope"
                else "transactionid",
            )
            assert witness["pid"] != pid
            holder.execute(
                text(
                    "SELECT pg_sleep(greatest(0,extract(epoch FROM (:expiry-clock_timestamp())))+0.01)"
                ),
                dict(expiry=expiry),
            )
            acquired = holder.execute(text("SELECT clock_timestamp()")).scalar_one()
            holder.commit()
            with pytest.raises(ResearchBaseError) as error:
                future.result(timeout=15)
            assert error.value.code == ErrorCode.FORBIDDEN
            assert started < expiry <= acquired
        finally:
            holder.rollback()
            env[9].is_valid = original
    assert counts(env) == before


@pytest.mark.parametrize(
    "stage", ["insert_decision", "insert_grant", "constraints", "final_credential"]
)
def test_midwrite_failure_rolls_back_all_outputs(b05_env, monkeypatch, stage):
    env = b05_env
    app, cmd, actor = setup(env)
    app.request_approval(env[2], cmd)
    before = counts(env)
    insert = SqlAlchemyApprovalRepository.insert
    force = SqlAlchemyApprovalRepository.force_constraints

    def write(self, table, row):
        result = insert(self, table, row)
        if (stage == "insert_decision" and table == "approval_decisions") or (
            stage == "insert_grant" and table == "approval_grants"
        ):
            raise ResearchBaseError(ErrorCode.CONCURRENT_MODIFICATION, "injected write failure")
        return result

    def constraints(self):
        force(self)
        if stage == "constraints":
            raise ResearchBaseError(ErrorCode.CONCURRENT_MODIFICATION, "injected force failure")
        if stage == "final_credential":
            env[9].enabled = False

    monkeypatch.setattr(SqlAlchemyApprovalRepository, "insert", write)
    monkeypatch.setattr(SqlAlchemyApprovalRepository, "force_constraints", constraints)
    try:
        with pytest.raises(ResearchBaseError):
            app.decide_approval(actor, decide(cmd))
    finally:
        env[9].enabled = True
    assert counts(env) == before


@pytest.mark.parametrize(
    "message,expected",
    [("decision transaction rejected", 3), ("timeout", 1), ("business conflict", 1)],
)
def test_only_normalized_serialization_deadlock_retries_exactly_three_fresh_uows(
    b05_env, monkeypatch, message, expected
):
    env = b05_env
    app, cmd, _ = setup(env)
    calls = []

    def fail(self, *, deciding=False):
        calls.append(self._session)
        raise ResearchBaseError(ErrorCode.CONCURRENT_MODIFICATION, message)

    monkeypatch.setattr(SqlAlchemyApprovalRepository, "lock_snapshot", fail)
    with pytest.raises(ResearchBaseError):
        app.request_approval(env[2], cmd)
    assert len(calls) == expected and len({id(s) for s in calls}) == expected
    assert counts(env) == (0,) * 6


def test_successful_rejection_does_not_self_fence_but_next_request_does(b05_env):
    env = b05_env
    app, cmd, actor = setup(env)
    app.request_approval(env[2], cmd)
    assert app.decide_approval(actor, decide(cmd, "REJECT")).grant is None
    before = counts(env)
    with pytest.raises(ResearchBaseError) as error:
        app.request_approval(env[2], replace(cmd, id=uuid4()))
    assert error.value.code == ErrorCode.REJECTION_RECONSIDERATION_REQUIRED
    assert counts(env) == before


@pytest.mark.parametrize("expiry_kind", ["role", "conditions"])
def test_actor_fk_wait_crosses_scheduled_role_or_condition_expiry(b05_env, expiry_kind):
    env = b05_env
    app, cmd, actor = setup(env)
    app.request_approval(env[2], cmd)
    with env[5].begin() as conn:
        expiry = conn.execute(text("SELECT clock_timestamp()+interval '1.2 seconds'")).scalar_one()
        if expiry_kind == "role":
            role = conn.execute(
                text(
                    "UPDATE project_role_assignments SET effective_until=:expiry,row_version=row_version+1 WHERE actor_id=:actor AND role='APPROVER' RETURNING id"
                ),
                dict(expiry=expiry, actor=actor.actor_id),
            ).scalar_one()
            conn.execute(
                text(
                    "INSERT INTO project_role_events(id,role_assignment_id,actor_id,event_kind,occurred_at,reason,request_id) VALUES (:id,:role,:actor,'CLOSED',:expiry,'Scheduled',:request)"
                ),
                dict(id=uuid4(), role=role, actor=actor.actor_id, expiry=expiry, request=uuid4()),
            )
    command = (
        decide(cmd, "APPROVE_WITH_CONDITIONS", valid_until=expiry)
        if expiry_kind == "conditions"
        else decide(cmd)
    )
    before = counts(env)
    with env[5].connect() as holder, ThreadPoolExecutor(1) as pool:
        pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
        holder.execute(
            text("SELECT id FROM actors WHERE id=:id FOR UPDATE"), dict(id=actor.actor_id)
        )
        future = pool.submit(app.decide_approval, actor, command)
        try:
            assert _wait_for_pg_blocker(env[5], pid, "transactionid")["pid"] != pid
            holder.execute(
                text(
                    "SELECT pg_sleep(greatest(0,extract(epoch FROM (:expiry-clock_timestamp())))+0.01)"
                ),
                dict(expiry=expiry),
            )
            holder.commit()
            with pytest.raises(ResearchBaseError) as error:
                future.result(timeout=15)
            assert error.value.code == (
                ErrorCode.FORBIDDEN if expiry_kind == "role" else ErrorCode.VALIDATION_ERROR
            )
        finally:
            holder.rollback()
    assert counts(env) == before


def test_review_insert_phantom_waits_for_approval_snapshot(b05_env, monkeypatch):
    from threading import Event

    from tests.integration.phase2.test_b14r_ready_approval import create

    env = b05_env
    app, cmd, actor = setup(env)
    app.request_approval(env[2], cmd)
    entered, release = Event(), Event()
    writer_pid = []
    original = SqlAlchemyApprovalRepository.insert

    def insert(self, table, row):
        if table == "approval_decisions":
            writer_pid.append(self._session.execute(text("SELECT pg_backend_pid()")).scalar_one())
            entered.set()
            assert release.wait(timeout=15)
        return original(self, table, row)

    monkeypatch.setattr(SqlAlchemyApprovalRepository, "insert", insert)
    with ThreadPoolExecutor(2) as pool:
        approving = pool.submit(app.decide_approval, actor, decide(cmd))
        assert entered.wait(timeout=10)
        reviewing = pool.submit(create, env, recommendation="REJECT")
        try:
            witness = _wait_for_pg_blocker(env[5], writer_pid[0], "relation")
            assert witness["pid"] != writer_pid[0]
            release.set()
            result = approving.result(timeout=20)
            later = reviewing.result(timeout=20)
            assert result.grant is not None and later.id not in cmd.review_ids
            assert (
                tuple(r.id for r in app.get_request(env[2], cmd.project_id, cmd.id).reviews)
                == cmd.review_ids
            )
        finally:
            release.set()


@pytest.mark.parametrize(
    "state,attempts", [("40001", 3), ("40P01", 3), ("55P03", 1), ("57014", 1), ("23505", 1)]
)
def test_real_sqlstate_classification_and_fresh_writer_attempts(
    b05_env, monkeypatch, state, attempts
):
    env = b05_env
    app, cmd, _ = setup(env)
    original = SqlAlchemyApprovalRepository.lock_snapshot
    sessions = []

    def fail(self, *, deciding=False):
        original(self, deciding=deciding)
        sessions.append(self._session)
        self._session.execute(
            text(f"DO $$ BEGIN RAISE EXCEPTION 'injected' USING ERRCODE='{state}'; END $$")
        )

    monkeypatch.setattr(SqlAlchemyApprovalRepository, "lock_snapshot", fail)
    with pytest.raises(ResearchBaseError):
        app.request_approval(env[2], cmd)
    assert len(sessions) == attempts and len({id(s) for s in sessions}) == attempts
    assert counts(env) == (0,) * 6


@pytest.mark.parametrize("kind", ["request", "decision"])
def test_uncertain_commit_recovers_only_by_same_uuid(b05_env, monkeypatch, kind):
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork

    env = b05_env
    app, cmd, actor = setup(env)
    if kind == "decision":
        app.request_approval(env[2], cmd)
    command = cmd if kind == "request" else decide(cmd)
    operation, caller = (
        (app.request_approval, env[2]) if kind == "request" else (app.decide_approval, actor)
    )
    original = SqlAlchemyUnitOfWork.commit
    calls = []

    def uncertain(self):
        calls.append(self)
        original(self)
        raise RuntimeError("uncertain commit acknowledgement")

    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", uncertain)
    with pytest.raises(RuntimeError, match="uncertain commit"):
        cast(Any, operation)(caller, command)
    assert len(calls) == 1
    before = counts(env)
    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", original)
    assert cast(Any, operation)(caller, command).id == command.id
    assert counts(env) == before


@pytest.mark.parametrize("rejection_first", [True, False])
def test_rejection_vs_old_pending_decision_both_observed_orders(
    b05_env, monkeypatch, rejection_first
):
    from threading import Event

    from tests.integration.phase2.test_b14r_ready_approval import another_target

    env = b05_env
    app, old, actor = setup(env)
    app.request_approval(env[2], old)
    _, newer = another_target(env)
    app.request_approval(env[2], newer)
    rejecting = decide(newer, "REJECT")
    deciding = decide(old)
    first_command, second_command = (
        (rejecting, deciding) if rejection_first else (deciding, rejecting)
    )
    entered, release = Event(), Event()
    pid = []
    original = SqlAlchemyApprovalRepository.lock_scope

    def scope(self, project, purpose):
        original(self, project, purpose)
        if not entered.is_set():
            pid.append(self._session.execute(text("SELECT pg_backend_pid()")).scalar_one())
            entered.set()
            assert release.wait(timeout=20)

    monkeypatch.setattr(SqlAlchemyApprovalRepository, "lock_scope", scope)

    def execute(command):
        try:
            return app.decide_approval(actor, command)
        except ResearchBaseError as error:
            return error.code

    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(execute, first_command)
        assert entered.wait(timeout=15)
        second = pool.submit(execute, second_command)
        try:
            assert _wait_for_pg_blocker(env[5], pid[0], "relation")["pid"] != pid[0]
            release.set()
            result1, result2 = first.result(timeout=25), second.result(timeout=25)
        finally:
            release.set()
    if rejection_first:
        assert not isinstance(result1, ErrorCode)
        assert result1.grant is None and result2 == ErrorCode.REJECTION_RECONSIDERATION_REQUIRED
    else:
        assert not isinstance(result2, ErrorCode)
        assert result1 == ErrorCode.APPROVAL_TARGET_STALE and result2.grant is None
    assert counts(env) == (2, 2, 3, 1, 0, 0)


@pytest.mark.parametrize("blocker_first", [True, False])
@pytest.mark.parametrize("upstream", [False, True])
def test_zero_issue_and_upstream_insert_phantom_both_orders(
    b05_env, monkeypatch, blocker_first, upstream
):
    from threading import Event

    from tests.integration.phase2.test_b11_readiness_decision import place_claim
    from tests.integration.phase2.test_b14r_ready_approval_schema import insert_blocker

    env = b05_env
    if upstream:
        place_claim(env)
    app, cmd, actor = setup(env)
    entered, release = Event(), Event()
    pids = []
    original = SqlAlchemyApprovalRepository.insert

    def insert(self, table, row):
        if table == "approval_requests":
            pids.append(self._session.execute(text("SELECT pg_backend_pid()")).scalar_one())
            entered.set()
            assert release.wait(timeout=20)
        return original(self, table, row)

    monkeypatch.setattr(SqlAlchemyApprovalRepository, "insert", insert)

    def blocking():
        with env[5].begin() as conn:
            conn.execute(
                text("LOCK TABLE internal_review_records,review_issues IN ROW EXCLUSIVE MODE")
            )
            if blocker_first:
                pids.append(conn.execute(text("SELECT pg_backend_pid()")).scalar_one())
                entered.set()
                assert release.wait(timeout=20)
            insert_blocker(conn, env, cmd, upstream=upstream)

    with ThreadPoolExecutor(2) as pool:
        first = (
            pool.submit(blocking)
            if blocker_first
            else pool.submit(app.request_approval, env[2], cmd)
        )
        assert entered.wait(timeout=15)
        second = (
            pool.submit(app.request_approval, env[2], cmd)
            if blocker_first
            else pool.submit(blocking)
        )
        try:
            witness = _wait_for_pg_blocker(env[5], pids[0], "relation")
            assert witness["pid"] != pids[0]
            release.set()
            if blocker_first:
                first.result(timeout=25)
                with pytest.raises(ResearchBaseError) as error:
                    second.result(timeout=25)
                assert error.value.code == ErrorCode.APPROVAL_GATE_FAILED
                assert counts(env) == (0,) * 6
            else:
                saved = first.result(timeout=25)
                second.result(timeout=25)
                assert app.get_request(env[2], cmd.project_id, cmd.id) == saved
                with pytest.raises(ResearchBaseError) as error:
                    app.decide_approval(actor, decide(cmd))
                assert error.value.code == ErrorCode.APPROVAL_GATE_FAILED
        finally:
            release.set()


@pytest.mark.parametrize(
    "wait,expiry_kind",
    [("grant", "credential"), ("deferred", "credential"), ("deferred", "conditions")],
)
def test_affected_grant_and_deferred_waits_recheck_after_expiry(b05_env, wait, expiry_kind):
    env = b05_env
    app, cmd, actor = setup(env)
    app.request_approval(env[2], cmd)
    if wait == "grant":
        first = app.decide_approval(actor, decide(cmd))
        assert first.grant
        cmd = replace(cmd, id=uuid4())
        app.request_approval(env[2], cmd)
    key = uuid4().int % (2**63)
    if wait == "deferred":
        with env[5].begin() as conn:
            conn.execute(
                text(
                    f"CREATE FUNCTION b14r_test_deferred_wait() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN PERFORM pg_advisory_xact_lock({key}); RETURN NULL; END $$"
                )
            )
            conn.execute(
                text(
                    "CREATE CONSTRAINT TRIGGER zz_b14r_test_wait AFTER INSERT ON approval_decisions DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION b14r_test_deferred_wait()"
                )
            )
    with env[5].connect() as holder, ThreadPoolExecutor(1) as pool:
        pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
        if wait == "grant":
            assert first.grant is not None
            holder.execute(
                text("SELECT id FROM approval_grants WHERE id=:id FOR UPDATE"),
                dict(id=first.grant.id),
            )
        else:
            holder.execute(text("SELECT pg_advisory_xact_lock(:key)"), dict(key=key))
        started, expiry = holder.execute(
            text("SELECT clock_timestamp(),clock_timestamp()+interval '2 seconds'")
        ).one()
        original = env[9].is_valid
        checked = []

        def valid(principal, at):
            if principal.actor_id == actor.actor_id:
                checked.append(at)
            return original(principal, at) and (
                expiry_kind != "credential" or principal.actor_id != actor.actor_id or at < expiry
            )

        env[9].is_valid = valid
        command = (
            decide(cmd, "APPROVE_WITH_CONDITIONS", valid_until=expiry)
            if expiry_kind == "conditions"
            else decide(cmd, "REJECT" if wait == "grant" else "APPROVE")
        )
        before = counts(env)
        future = pool.submit(app.decide_approval, actor, command)
        try:
            witness = _wait_for_pg_blocker(
                env[5], pid, "transactionid" if wait == "grant" else "advisory"
            )
            assert witness["pid"] != pid
            holder.execute(
                text(
                    "SELECT pg_sleep(greatest(0,extract(epoch FROM (:expiry-clock_timestamp())))+0.01)"
                ),
                dict(expiry=expiry),
            )
            acquired = holder.execute(text("SELECT clock_timestamp()")).scalar_one()
            holder.commit()
            with pytest.raises(ResearchBaseError) as error:
                future.result(timeout=20)
            assert error.value.code == (
                ErrorCode.FORBIDDEN if expiry_kind == "credential" else ErrorCode.VALIDATION_ERROR
            )
            assert started < expiry <= acquired and checked
            if expiry_kind == "credential":
                assert max(checked) >= expiry
        finally:
            env[9].is_valid = original
            holder.rollback()
    assert counts(env) == before


@pytest.mark.parametrize("rejection_first", [True, False])
def test_rejection_vs_new_request_both_observed_orders(b05_env, monkeypatch, rejection_first):
    from threading import Event

    from tests.integration.phase2.test_b14r_ready_approval import another_target

    env = b05_env
    app, original_request, actor = setup(env)
    app.request_approval(env[2], original_request)
    app.decide_approval(actor, decide(original_request))
    _, pending = another_target(env)
    app.request_approval(env[2], pending)
    new_request = replace(original_request, id=uuid4())
    entered, release = Event(), Event()
    pids = []
    original = SqlAlchemyApprovalRepository.lock_scope

    def scope(self, project, purpose):
        original(self, project, purpose)
        if not entered.is_set():
            pids.append(self._session.execute(text("SELECT pg_backend_pid()")).scalar_one())
            entered.set()
            assert release.wait(timeout=20)

    monkeypatch.setattr(SqlAlchemyApprovalRepository, "lock_scope", scope)

    def reject():
        try:
            return app.decide_approval(actor, decide(pending, "REJECT"))
        except ResearchBaseError as error:
            return error.code

    def request():
        try:
            return app.request_approval(env[2], new_request)
        except ResearchBaseError as error:
            return error.code

    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(reject if rejection_first else request)
        assert entered.wait(timeout=15)
        second = pool.submit(request if rejection_first else reject)
        try:
            assert _wait_for_pg_blocker(env[5], pids[0], "relation")["pid"] != pids[0]
            release.set()
            one, two = first.result(timeout=25), second.result(timeout=25)
        finally:
            release.set()
    if rejection_first:
        assert not isinstance(one, ErrorCode)
        assert cast(Any, one).grant is None and two == ErrorCode.REJECTION_RECONSIDERATION_REQUIRED
        with env[4]() as uow:
            assert not uow.approval.rejected(uuid4(), "READY_FOR_SUBMISSION")
            assert not uow.approval.rejected(pending.project_id, "PREPARE_SUBMISSION")
            assert not uow.approval.rejected(pending.project_id, "INTERNAL_SCIENTIFIC_RELEASE")
    else:
        assert not isinstance(one, ErrorCode)
        assert one.id == new_request.id and two == ErrorCode.APPROVAL_TARGET_STALE


@pytest.mark.parametrize("change", ["binding", "membership"])
def test_committed_authority_change_before_snapshot_denies_waiting_writer(
    b05_env, monkeypatch, change
):
    from threading import Event

    from researchbase.application.phase2_identity import (
        RevokeActorSubjectBinding,
        SuspendProjectMembership,
    )
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork
    from tests.integration.phase2.test_pr2_00_challenges import _service as identity_service

    env = b05_env
    app, cmd, actor = setup(env)
    app.request_approval(env[2], cmd)
    identity, operator, _ = identity_service(env[5].url.render_as_string(hide_password=False))
    # _add_owner retained this operator credential in the binding's immutable proof.
    operator = replace(operator, credential_id="operator")
    with env[5].connect() as conn:
        binding = conn.execute(
            text("SELECT id FROM actor_subject_bindings WHERE actor_id=:id AND status='ACTIVE'"),
            dict(id=actor.actor_id),
        ).scalar_one()
        membership = conn.execute(
            text("SELECT id FROM project_memberships WHERE actor_id=:id AND project_id=:project"),
            dict(id=actor.actor_id, project=cmd.project_id),
        ).scalar_one()
    entered, release = Event(), Event()
    pids = []
    commit = SqlAlchemyUnitOfWork.commit

    def pause(self):
        if not entered.is_set():
            pids.append(self._session.execute(text("SELECT pg_backend_pid()")).scalar_one())
            entered.set()
            assert release.wait(timeout=20)
        return commit(self)

    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", pause)

    def mutation():
        if change == "binding":
            return identity.revoke_actor_subject_binding(
                RevokeActorSubjectBinding(operator, binding, "Revoked", uuid4())
            )
        return identity.suspend_project_membership(
            SuspendProjectMembership(env[3], cmd.project_id, membership, "Suspended", uuid4())
        )

    before = counts(env)
    with ThreadPoolExecutor(2) as pool:
        changing = pool.submit(mutation)
        assert entered.wait(timeout=15)
        deciding = pool.submit(app.decide_approval, actor, decide(cmd))
        try:
            assert _wait_for_pg_blocker(env[5], pids[0], "relation")["pid"] != pids[0]
            release.set()
            changing.result(timeout=25)
            with pytest.raises(ResearchBaseError) as error:
                deciding.result(timeout=25)
            assert error.value.code == ErrorCode.FORBIDDEN
        finally:
            release.set()
    assert counts(env) == before


def test_committed_validity_change_before_snapshot_denies_waiting_writer(b05_env, monkeypatch):
    from threading import Event

    from researchbase.application.governance import (
        CreateAuditFindingCommand,
        CreateImpactAssessmentCommand,
        GovernanceService,
        ProposedImpactTarget,
    )
    from researchbase.foundation.execution_context import ExecutionContext
    from researchbase.foundation.time import SystemClock
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork
    from tests.integration.phase2.test_b11_readiness_decision import place_claim

    env = b05_env
    place_claim(env)
    app, cmd, actor = setup(env)
    app.request_approval(env[2], cmd)
    governance = GovernanceService(env[4], SystemClock())
    context = ExecutionContext(actor_id=env[2].actor_id, request_id=uuid4(), client_type="test")
    finding = governance.create_audit_finding(
        CreateAuditFindingCommand(
            cmd.project_id,
            "code_bug",
            "major",
            "Problem",
            "Recheck",
            "claim_version",
            env[8],
            context,
        )
    )
    assessment = CreateImpactAssessmentCommand(
        cmd.project_id,
        finding.id,
        {"basis": "TEST"},
        "invalid",
        (ProposedImpactTarget("claim_version", env[8], "invalid"),),
        context,
    )
    entered, release = Event(), Event()
    pids = []
    original = SqlAlchemyUnitOfWork.commit

    def pause(self):
        if not entered.is_set():
            pids.append(self._session.execute(text("SELECT pg_backend_pid()")).scalar_one())
            entered.set()
            assert release.wait(timeout=20)
        return original(self)

    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", pause)
    before = counts(env)
    with ThreadPoolExecutor(2) as pool:
        changing = pool.submit(governance.create_impact_assessment, assessment)
        assert entered.wait(timeout=15)
        deciding = pool.submit(app.decide_approval, actor, decide(cmd))
        try:
            assert _wait_for_pg_blocker(env[5], pids[0], "relation")["pid"] != pids[0]
            release.set()
            changing.result(timeout=25)
            with pytest.raises(ResearchBaseError) as error:
                deciding.result(timeout=25)
            assert error.value.code == ErrorCode.APPROVAL_TARGET_STALE
        finally:
            release.set()
    assert counts(env) == before
