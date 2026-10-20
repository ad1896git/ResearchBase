"""Actual independent PostgreSQL backend waits, rollback, and bounded retry."""

# SQL and independent literal hash vectors preserve contract spelling.
# ruff: noqa: E501

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from typing import Any, cast

import pytest
from sqlalchemy import text

from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.decision_repository import B11_SHARE_SQL, SqlAlchemyDecisionRepository
from researchbase.persistence.uow import SqlAlchemyUnitOfWork
from tests.integration.phase2.test_b04_manuscript_migration import normal_sql_role
from tests.integration.phase2.test_b05_review_races import insert_sql
from tests.integration.phase2.test_b11_readiness_decision import (
    b04_env,
    b05_env,
    command,
    conclusion_env,
    create,
    decision_env,
    phase2_database_url,
    read,
    record,
    revision_env,
    seal,
    service,
)
from tests.integration.phase2.test_pr2_14_internal_review import _wait_for_pg_blocker

_FIXTURES = (
    b04_env,
    b05_env,
    conclusion_env,
    phase2_database_url,
    normal_sql_role,
    revision_env,
    decision_env,
)
pytestmark = pytest.mark.integration


@pytest.mark.parametrize("kind", ["review", "issue", "upstream_issue"])
@pytest.mark.parametrize("first", ["decision", "writer"])
def test_review_and_blocker_both_commit_orders(b05_env, normal_sql_role, monkeypatch, kind, first):
    env = b05_env
    if kind == "upstream_issue":
        from uuid import uuid4

        from tests.integration.phase2.test_b11_readiness_decision import place_claim

        place_claim(env)
    seal(env)
    template = create(env)
    if kind == "upstream_issue":
        template = env[0].create(
            env[3],
            env[1].project_id,
            "CLAIM_VERSION",
            env[8],
            "SCIENTIFIC",
            "REJECT",
            "Upstream review",
            (),
            uuid4(),
        )
    entered, release = Event(), Event()
    original = SqlAlchemyDecisionRepository.insert_decision
    holder_pid = []

    def pause(self, row):
        holder_pid.append(self._session.execute(text("SELECT pg_backend_pid()")).scalar_one())
        entered.set()
        assert release.wait(15)
        return original(self, row)

    def write():
        with env[5].begin() as conn:
            conn.execute(text(f'SET LOCAL ROLE "{normal_sql_role}"'))
            insert_sql(conn, "issue" if kind == "upstream_issue" else kind, template)

    with ThreadPoolExecutor(max_workers=2) as pool:
        if first == "decision":
            monkeypatch.setattr(SqlAlchemyDecisionRepository, "insert_decision", pause)
            future = pool.submit(record, env)
            assert entered.wait(15)
            writer = pool.submit(write)
            try:
                witness = _wait_for_pg_blocker(env[5], holder_pid[0], "relation")
                assert witness["mode"] == "RowExclusiveLock"
            finally:
                release.set()
            saved = future.result(timeout=15)
            writer.result(timeout=15)
            assert len(saved.basis) == 2
            current = read(env, saved.id)
            assert bool(current.current_blocking_issue_ids) == (kind != "review")
        else:
            with env[5].connect() as conn:
                tx = conn.begin()
                conn.execute(text(f'SET LOCAL ROLE "{normal_sql_role}"'))
                insert_sql(conn, "issue" if kind == "upstream_issue" else kind, template)
                pid = conn.execute(text("SELECT pg_backend_pid()")).scalar_one()
                future = pool.submit(record, env)
                try:
                    witness = _wait_for_pg_blocker(env[5], pid, "relation")
                    assert witness["query"] == B11_SHARE_SQL
                finally:
                    tx.commit()
                if kind != "review":
                    with pytest.raises(ResearchBaseError) as exc:
                        future.result(timeout=15)
                    assert exc.value.code == ErrorCode.DECISION_BASIS_INVALID
                else:
                    assert len(future.result(timeout=15).basis) == 3


@pytest.mark.parametrize("same", [False, True])
def test_same_and_different_uuid_scope_races(b05_env, same):
    env = b05_env
    seal(env)
    create(env)
    cmd = command(env)

    def run(c):
        try:
            return record(env, c)
        except ResearchBaseError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run, c) for c in (cmd, cmd if same else command(env))]
        results = [f.result(timeout=20) for f in futures]
    saved = [r for r in results if not isinstance(r, ErrorCode)]
    assert len(saved) == (2 if same else 1)
    if same:
        assert saved[0].content_hash == saved[1].content_hash
    else:
        assert ErrorCode.IDEMPOTENCY_CONFLICT in results


@pytest.mark.parametrize(
    "table",
    [
        "actors",
        "actor_subject_bindings",
        "project_memberships",
        "project_role_assignments",
        "audit_findings",
        "review_issues",
        "internal_review_records",
    ],
)
def test_first_inventory_wait_rereads_credential(b05_env, table):
    env = b05_env
    seal(env)
    create(env)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with env[5].begin() as holder:
            pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
            holder.execute(text(f"LOCK TABLE {table} IN ROW EXCLUSIVE MODE"))
            future = pool.submit(record, env)
            witness = _wait_for_pg_blocker(env[5], pid, "relation")
            assert witness["query"] == B11_SHARE_SQL
            env[9].enabled = False
        with pytest.raises(ResearchBaseError) as exc:
            future.result(timeout=15)
        assert exc.value.code == ErrorCode.FORBIDDEN


@pytest.mark.parametrize("stage", ["parent", "manuscript", "review", "constraints"])
def test_midwrite_failures_are_atomic(b05_env, monkeypatch, stage):
    env = b05_env
    seal(env)
    create(env)
    name = {
        "parent": "insert_decision",
        "manuscript": "insert_manuscript_basis",
        "review": "insert_review_basis",
        "constraints": "force_readiness_constraints",
    }[stage]
    original = getattr(SqlAlchemyDecisionRepository, name)

    def fail(self, *args):
        original(self, *args)
        raise ResearchBaseError(ErrorCode.INVALID_STATE_TRANSITION, "injected failure")

    monkeypatch.setattr(SqlAlchemyDecisionRepository, name, fail)
    with pytest.raises(ResearchBaseError):
        record(env)
    with env[5].connect() as conn:
        for table in ("decision_records", "decision_basis_manuscripts", "decision_basis_reviews"):
            assert conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() == 0


@pytest.mark.parametrize(
    "state,attempts", [("40001", 3), ("40P01", 3), ("55P03", 1), ("57014", 1), ("P17F3", 1)]
)
def test_only_sqlstate_retry_and_three_fresh_uows(b05_env, monkeypatch, state, attempts):
    from types import SimpleNamespace

    from sqlalchemy.exc import DBAPIError

    env = b05_env
    seal(env)
    create(env)
    count = []
    original = SqlAlchemyDecisionRepository.prepare_readiness_write

    def fail(self):
        original(self)
        count.append(self._session)
        raise DBAPIError(None, None, cast(Any, SimpleNamespace(sqlstate=state, diag=None)))

    monkeypatch.setattr(SqlAlchemyDecisionRepository, "prepare_readiness_write", fail)
    with pytest.raises(ResearchBaseError) as exc:
        record(env)
    assert len(count) == attempts and len({id(s) for s in count}) == attempts
    assert exc.value.code == (
        ErrorCode.CONCURRENT_MODIFICATION
        if attempts == 3
        else ErrorCode.IDEMPOTENCY_CONFLICT
        if state == "P17F3"
        else ErrorCode.INVALID_STATE_TRANSITION
    )


def test_lost_commit_acknowledgment_recovers_same_uuid(b05_env, monkeypatch):
    env = b05_env
    seal(env)
    create(env)
    cmd = command(env)
    original = SqlAlchemyUnitOfWork.commit

    def uncertain(self):
        original(self)
        raise ResearchBaseError(ErrorCode.INVALID_STATE_TRANSITION, "uncertain commit")

    with monkeypatch.context() as patch:
        patch.setattr(SqlAlchemyUnitOfWork, "commit", uncertain)
        with pytest.raises(ResearchBaseError):
            record(env, cmd)
    saved = record(env, cmd)
    assert read(env, saved.id).content_hash == saved.content_hash


@pytest.mark.parametrize("wait_at", ["request", "target", "project", "publication"])
def test_expiry_after_every_admission_wait(b05_env, wait_at):
    env = b05_env
    seal(env)
    create(env)
    cmd = command(env)

    class Expiring:
        until = None

        def is_valid(self, principal, at):
            return env[9].is_valid(principal, at) and (self.until is None or at < self.until)

    credentials = Expiring()
    policy = service(env)
    policy._credentials = credentials
    with ThreadPoolExecutor(max_workers=1) as pool:
        with env[5].begin() as holder:
            pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
            if wait_at == "request":
                holder.execute(
                    text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
                    {"key": f"b11:decision:{cmd.id}"},
                )
                locktype = "advisory"
            else:
                table, identity = {
                    "target": ("manuscript_versions", cmd.manuscript_version_id),
                    "project": ("projects", cmd.project_id),
                    "publication": ("publications", env[1].publication_id),
                }[wait_at]
                holder.execute(
                    text(f"SELECT id FROM {table} WHERE id=:id FOR UPDATE"), {"id": identity}
                )
                locktype = "transactionid"
            future = pool.submit(policy.record_ready_for_submission_decision, env[3], cmd)
            witness = _wait_for_pg_blocker(env[5], pid, locktype)
            credentials.until = witness["observed_at"]
        with pytest.raises(ResearchBaseError) as exc:
            future.result(timeout=15)
        assert exc.value.code == ErrorCode.FORBIDDEN
    with env[5].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM decision_records")).scalar_one() == 0


def test_final_post_constraint_expiry_rolls_back_everything(b05_env, monkeypatch):
    env = b05_env
    seal(env)
    create(env)
    original = SqlAlchemyDecisionRepository.force_readiness_constraints

    def expire(self):
        original(self)
        env[9].enabled = False

    monkeypatch.setattr(SqlAlchemyDecisionRepository, "force_readiness_constraints", expire)
    with pytest.raises(ResearchBaseError) as exc:
        record(env)
    assert exc.value.code == ErrorCode.FORBIDDEN
    with env[5].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM decision_records")).scalar_one() == 0


def test_snapshot_read_final_expiry_denies(b05_env, monkeypatch):
    env = b05_env
    seal(env)
    create(env)
    saved = record(env)
    original = SqlAlchemyDecisionRepository.applicable_manuscript_reviews

    def expire(self, *args):
        result = original(self, *args)
        env[9].enabled = False
        return result

    monkeypatch.setattr(SqlAlchemyDecisionRepository, "applicable_manuscript_reviews", expire)
    with pytest.raises(ResearchBaseError) as exc:
        read(env, saved.id)
    assert exc.value.code == ErrorCode.FORBIDDEN


@pytest.mark.parametrize("mutation", ["role", "binding", "membership", "validity"])
@pytest.mark.parametrize("order", ["decision_first", "mutation_first"])
def test_actual_mutations_both_commit_orders(b05_env, monkeypatch, mutation, order):
    from threading import get_ident
    from uuid import uuid4

    from sqlalchemy import event

    from researchbase.application.governance import (
        CreateAuditFindingCommand,
        CreateImpactAssessmentCommand,
        GovernanceService,
        ProposedImpactTarget,
    )
    from researchbase.application.phase2_identity import (
        CloseProjectRole,
        RevokeActorSubjectBinding,
        SuspendProjectMembership,
    )
    from researchbase.foundation.execution_context import ExecutionContext
    from researchbase.foundation.time import SystemClock
    from tests.integration.phase2.test_b11_readiness_decision import place_claim
    from tests.integration.phase2.test_pr2_15_decision import identity_service

    env = b05_env
    place_claim(env)
    seal(env)
    create(env)
    identity, _, _ = identity_service(env[5].url.render_as_string(hide_password=False))
    identity._uow_factory = env[4]
    with env[5].connect() as conn:
        role = conn.execute(
            text(
                "SELECT id FROM project_role_assignments WHERE actor_id=:id AND role='OWNER' AND effective_until IS NULL"
            ),
            {"id": env[3].actor_id},
        ).scalar_one()
        binding = conn.execute(
            text("SELECT id FROM actor_subject_bindings WHERE actor_id=:id AND status='ACTIVE'"),
            {"id": env[3].actor_id},
        ).scalar_one()
        membership = conn.execute(
            text("SELECT id FROM project_memberships WHERE actor_id=:id AND project_id=:project"),
            {"id": env[3].actor_id, "project": env[1].project_id},
        ).scalar_one()
    from dataclasses import replace

    with env[5].connect() as conn:
        operator_credential = conn.execute(
            text("SELECT operator_credential_id FROM actor_subject_bindings WHERE id=:id"),
            {"id": binding},
        ).scalar_one()
    operator = replace(env[2], credential_id=operator_credential)
    if mutation == "role":

        def mutate():
            identity.close_project_role(
                CloseProjectRole(env[2], env[1].project_id, role, "TEST ONLY", uuid4())
            )

        marker = "UPDATE project_role_assignments"
    elif mutation == "binding":

        def mutate():
            identity.revoke_actor_subject_binding(
                RevokeActorSubjectBinding(operator, binding, "TEST ONLY", uuid4())
            )

        marker = "UPDATE actor_subject_bindings"
    elif mutation == "membership":

        def mutate():
            identity.suspend_project_membership(
                SuspendProjectMembership(
                    env[2], env[1].project_id, membership, "TEST ONLY", uuid4()
                )
            )

        # Reserve the complete membership mutation (projection + immutable event)
        # before admitting the competing snapshot. Earlier pauses deliberately
        # permit the older target-first writer's documented deadlock cycle.
        marker = "INSERT INTO project_membership_events"
    else:

        def mutate():
            governance = GovernanceService(env[4], SystemClock())
            context = ExecutionContext(
                actor_id=env[2].actor_id, request_id=uuid4(), client_type="test"
            )
            finding = governance.create_audit_finding(
                CreateAuditFindingCommand(
                    env[1].project_id,
                    "code_bug",
                    "major",
                    "Concurrent problem",
                    "Recheck",
                    "claim_version",
                    env[8],
                    context,
                )
            )
            governance.create_impact_assessment(
                CreateImpactAssessmentCommand(
                    env[1].project_id,
                    finding.id,
                    {"basis": "TEST ONLY"},
                    "stale",
                    (ProposedImpactTarget("claim_version", env[8], "stale"),),
                    context,
                )
            )

        marker = "INSERT INTO impact_assessments"
    entered, release = Event(), Event()
    holder = {}

    def pause(conn, cursor, statement, parameters, context, many):
        if get_ident() != holder.get("thread") or entered.is_set():
            return
        if (
            "INSERT INTO decision_records" in statement
            if order == "decision_first"
            else marker in statement
        ):
            holder["pid"] = conn.connection.driver_connection.info.backend_pid
            entered.set()
            assert release.wait(15)

    def first():
        holder["thread"] = get_ident()
        return record(env) if order == "decision_first" else mutate()

    event.listen(env[5], "after_cursor_execute", pause)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            one = pool.submit(first)
            assert entered.wait(15)
            second = mutate if order == "decision_first" else lambda: record(env)
            two = pool.submit(second)
            try:
                _wait_for_pg_blocker(
                    env[5],
                    holder["pid"],
                    "transactionid"
                    if order == "decision_first" and mutation != "validity"
                    else "relation",
                )
            finally:
                release.set()
            one.result(timeout=20)
            if order == "decision_first":
                two.result(timeout=20)
            else:
                with pytest.raises(ResearchBaseError) as exc:
                    two.result(timeout=20)
                assert exc.value.code == (
                    ErrorCode.PROVENANCE_CLOSURE_VIOLATION
                    if mutation == "validity"
                    else ErrorCode.FORBIDDEN
                )
    finally:
        release.set()
        event.remove(env[5], "after_cursor_execute", pause)
    with env[5].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM decision_records")).scalar_one() == (
            1 if order == "decision_first" else 0
        )


@pytest.mark.parametrize("order", ["decision_first", "disposition_first"])
def test_verified_upstream_disposition_both_commit_orders(b05_env, revision_env, order):
    from threading import get_ident
    from uuid import uuid4

    from sqlalchemy import event

    from researchbase.application.manuscript_placement import ClaimPlacementService
    from tests.integration.phase2.b08_support import disposition_case

    env = b05_env
    reviews, actor, cmd, _, _ = disposition_case(revision_env, dismiss=True)
    target = revision_env[2][3].version_id
    ClaimPlacementService(env[4], env[9]).add(
        env[2],
        env[1].project_id,
        env[1].publication_id,
        env[1].manuscript_version_id,
        None,
        target,
        "RESULTS",
        {"kind": "PARAGRAPH", "value": "p1"},
        "SUPPORTED",
        0,
        uuid4(),
    )
    seal(env)
    create(env)
    entered, release = Event(), Event()
    holder = {}

    def dispose():
        return reviews.record_issue_disposition(actor, cmd)

    def pause(conn, cursor, statement, parameters, context, many):
        if get_ident() != holder.get("thread") or entered.is_set():
            return
        match = (
            (
                "SELECT id FROM manuscript_versions WHERE id=" in statement
                and "FOR UPDATE" in statement
            )
            if order == "decision_first"
            else "INSERT INTO review_issue_events" in statement
        )
        if match:
            holder["pid"] = conn.connection.driver_connection.info.backend_pid
            entered.set()
            assert release.wait(15)

    def first():
        holder["thread"] = get_ident()
        return record(env) if order == "decision_first" else dispose()

    event.listen(env[5], "after_cursor_execute", pause)
    # B08 fixture uses the conclusion engine rather than B05's engine; both
    # address the same disposable database with independent backend sessions.
    other = revision_env[2][-1][8]
    event.listen(other, "after_cursor_execute", pause)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            one = pool.submit(first)
            assert entered.wait(15)
            second = dispose if order == "decision_first" else lambda: record(env)
            two = pool.submit(second)
            try:
                _wait_for_pg_blocker(env[5], holder["pid"], "relation")
            finally:
                release.set()
            if order == "decision_first":
                with pytest.raises(ResearchBaseError) as exc:
                    one.result(timeout=20)
                assert exc.value.code == ErrorCode.DECISION_BASIS_INVALID
                two.result(timeout=20)
            else:
                one.result(timeout=20)
                result = two.result(timeout=20)
                assert not result.current_blocking_issue_ids
    finally:
        release.set()
        event.remove(env[5], "after_cursor_execute", pause)
        event.remove(other, "after_cursor_execute", pause)
