"""Real locks, independent connections, retries and atomic expiry failure."""

# SQL assertions retain the exact reviewed lock/guard literals.
# ruff: noqa: E501

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Barrier, Event
from uuid import uuid4

import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import DBAPIError

from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.publication_repository import (
    B14A_SHARE_SQL,
    SqlAlchemyPublicationRepository,
)
from tests.integration.phase2.test_approval import approval_env, decision_env
from tests.integration.phase2.test_b14a_entry_replay import read
from tests.integration.phase2.test_b14a_publication_entry import (
    b04_env,
    b05_env,
    command,
    conclusion_env,
    counts,
    enter,
    phase2_database_url,
    seal,
    service,
)
from tests.integration.phase2.test_pr2_14_internal_review import _wait_for_pg_blocker

_FIXTURES = (b04_env, b05_env, conclusion_env, phase2_database_url, approval_env, decision_env)
pytestmark = pytest.mark.integration


def test_first_sql_inventory_isolation_and_target_before_parent(b05_env):
    env = b05_env
    seal(env)
    cmd = command(env)
    statements = []

    def capture(conn, cursor, sql, params, context, many):
        statements.append(
            (sql, cursor.connection.isolation_level.name, cursor.connection.read_only)
        )

    event.listen(env[5], "before_cursor_execute", capture)
    try:
        saved = enter(env, cmd)
        writer = [s for s, i, r in statements if i == "READ_COMMITTED"]
        assert writer[:3] == [
            B14A_SHARE_SQL,
            "LOCK TABLE publications IN SHARE ROW EXCLUSIVE MODE",
            "LOCK TABLE approval_decisions,approval_request_reviews,approval_requests IN SHARE MODE",
        ]
        target = next(
            i for i, s in enumerate(writer) if "manuscript_versions" in s and "FOR UPDATE" in s
        )
        parent = next(
            i for i, s in enumerate(writer) if "FROM publications" in s and "FOR UPDATE" in s
        )
        assert target < parent
        statements.clear()
        assert enter(env, cmd) == saved and read(env, saved.id) == saved
        assert all(i == "REPEATABLE_READ" and r for _, i, r in statements)
        assert not any(
            t in s.upper()
            for s, _, _ in statements
            for t in ("LOCK TABLE", "ADVISORY", "FOR SHARE", "FOR UPDATE")
        )
    finally:
        event.remove(env[5], "before_cursor_execute", capture)


@pytest.mark.parametrize("race", ["same", "changed", "competing"])
def test_racing_ids_one_effect(b05_env, race):
    env = b05_env
    seal(env)
    cmd = command(env)
    other = (
        cmd
        if race == "same"
        else replace(cmd, expected_content_hash="0" * 64)
        if race == "changed"
        else replace(cmd, id=uuid4())
    )
    barrier = Barrier(2)

    def run(c):
        barrier.wait(timeout=5)
        try:
            return enter(env, c)
        except ResearchBaseError as error:
            return error.code

    with ThreadPoolExecutor(2) as pool:
        results = [f.result(timeout=20) for f in (pool.submit(run, cmd), pool.submit(run, other))]
    if race == "same":
        assert results[0] == results[1]
    elif race == "competing":
        assert sum(r == ErrorCode.INVALID_STATE_TRANSITION for r in results) == 1
    else:
        assert any(
            r in {ErrorCode.IDEMPOTENCY_CONFLICT, ErrorCode.CONCURRENT_MODIFICATION}
            for r in results
        )
    assert counts(env)[1] == 2


@pytest.mark.parametrize(
    "sqlstate,attempts", [("40001", 3), ("40P01", 3), ("55P03", 1), ("57014", 1)]
)
def test_retry_only_deadlock_and_serialization_whole_uow(b05_env, monkeypatch, sqlstate, attempts):
    env = b05_env
    seal(env)
    cmd = command(env)
    seen = []

    class DriverFailure(Exception):
        sqlstate: str

    def fail(self, *args):
        seen.append(self._session)
        orig = DriverFailure("injected")
        orig.sqlstate = sqlstate
        raise DBAPIError("injected", None, orig)

    monkeypatch.setattr(SqlAlchemyPublicationRepository, "transition_entry", fail)
    before = counts(env)
    with pytest.raises(ResearchBaseError) as error:
        enter(env, cmd)
    assert error.value.code == ErrorCode.CONCURRENT_MODIFICATION
    assert len(seen) == attempts and len({id(s) for s in seen}) == attempts
    assert counts(env) == before


@pytest.mark.parametrize(
    "table",
    [
        "internal_review_records",
        "review_issues",
        "audit_findings",
        "project_role_assignments",
        "manuscript_versions",
        "approval_decisions",
    ],
)
def test_upstream_writer_first_wait_then_fresh_credential_denial(b05_env, table):
    env = b05_env
    seal(env)
    cmd = command(env)
    before = counts(env)
    with env[5].connect() as holder:
        holder.execute(text(f"LOCK TABLE {table} IN ROW EXCLUSIVE MODE"))
        pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
        with ThreadPoolExecutor(1) as pool:
            future = pool.submit(enter, env, cmd)
            _wait_for_pg_blocker(env[5], pid, "relation")
            env[9].enabled = False
            holder.rollback()
            with pytest.raises(ResearchBaseError) as error:
                future.result(timeout=15)
            assert error.value.code == ErrorCode.FORBIDDEN
    env[9].enabled = True
    assert counts(env) == before


@pytest.mark.parametrize(
    "stage", ["after_update", "after_event", "after_constraints", "final_credential"]
)
def test_failure_rolls_back_all_effects(b05_env, monkeypatch, stage):
    env = b05_env
    seal(env)
    cmd = command(env)
    before = counts(env)
    original_write = SqlAlchemyPublicationRepository.transition_entry
    original_force = SqlAlchemyPublicationRepository.force_entry_constraints

    def write(self, parent, values):
        if stage == "after_update":
            self._session.execute(
                text(
                    "UPDATE publications SET lifecycle_status='INTERNAL_REVIEW',row_version=row_version+1 WHERE id=:id"
                ),
                {"id": parent["id"]},
            )
            raise ResearchBaseError(ErrorCode.CONCURRENT_MODIFICATION, "injected")
        result = original_write(self, parent, values)
        if stage == "after_event":
            raise ResearchBaseError(ErrorCode.CONCURRENT_MODIFICATION, "injected")
        return result

    def force(self):
        original_force(self)
        if stage == "after_constraints":
            raise ResearchBaseError(ErrorCode.CONCURRENT_MODIFICATION, "injected")
        if stage == "final_credential":
            env[9].enabled = False

    monkeypatch.setattr(SqlAlchemyPublicationRepository, "transition_entry", write)
    monkeypatch.setattr(SqlAlchemyPublicationRepository, "force_entry_constraints", force)
    with pytest.raises(ResearchBaseError):
        enter(env, cmd)
    env[9].enabled = True
    assert counts(env) == before


def test_reads_do_not_wait_for_participating_write_locks(b05_env):
    env = b05_env
    seal(env)
    cmd = command(env)
    saved = enter(env, cmd)
    with env[5].connect() as writer:
        writer.execute(
            text(
                "LOCK TABLE internal_review_records,review_issues,publications IN ROW EXCLUSIVE MODE"
            )
        )
        with ThreadPoolExecutor(1) as pool:
            assert pool.submit(read, env, saved.id).result(timeout=5) == saved
            assert pool.submit(enter, env, cmd).result(timeout=5) == saved
        writer.rollback()


@pytest.mark.parametrize("entry_first", [False, True])
def test_zero_review_insert_phantom_both_real_commit_orders(b05_env, monkeypatch, entry_first):
    from threading import Event

    from researchbase.application.internal_review import ReviewIssueRequest
    from tests.integration.phase2.test_b05_manuscript_review import create

    env = b05_env
    seal(env)
    cmd = command(env)
    entered, release = Event(), Event()
    holder = []
    original = SqlAlchemyPublicationRepository.transition_entry

    def pause_entry(self, *args):
        holder.append(self._session.execute(text("SELECT pg_backend_pid()")).scalar_one())
        entered.set()
        assert release.wait(10)
        return original(self, *args)

    def pause_review(conn, cursor, sql, params, context, many):
        if sql.lstrip().upper().startswith("INSERT INTO INTERNAL_REVIEW_RECORDS"):
            holder.append(conn.execute(text("SELECT pg_backend_pid()")).scalar_one())
            entered.set()
            assert release.wait(10)

    def blocker():
        return create(env, issues=(ReviewIssueRequest("BLOCKING", "OTHER", "Racing concern"),))

    if entry_first:
        monkeypatch.setattr(SqlAlchemyPublicationRepository, "transition_entry", pause_entry)
    else:
        event.listen(env[5], "after_cursor_execute", pause_review)
    try:
        with ThreadPoolExecutor(2) as pool:
            first = pool.submit(enter, env, cmd) if entry_first else pool.submit(blocker)
            assert entered.wait(10)
            second = pool.submit(blocker) if entry_first else pool.submit(enter, env, cmd)
            try:
                _wait_for_pg_blocker(env[5], holder[0], "relation")
            finally:
                release.set()
            first.result(timeout=15)
            if entry_first:
                second.result(timeout=15)
                assert counts(env)[1] == 2
            else:
                with pytest.raises(ResearchBaseError) as error:
                    second.result(timeout=15)
                assert error.value.code == ErrorCode.APPROVAL_GATE_FAILED
                assert counts(env)[1] == 1
    finally:
        release.set()
        if not entry_first:
            event.remove(env[5], "after_cursor_execute", pause_review)


@pytest.mark.parametrize("wait_at", ["advisory", "manuscript", "publication", "event_actor_fk"])
def test_actual_wait_crosses_clock_credential_expiry(b05_env, wait_at):
    env = b05_env
    seal(env)
    cmd = command(env)
    before = counts(env)

    class Expiring:
        until = None

        def is_valid(self, principal, at):
            return env[9].is_valid(principal, at) and (self.until is None or at < self.until)

    credentials = Expiring()
    owner = service(env)
    owner._credentials = credentials
    with env[5].connect() as holder:
        pid = holder.execute(text("SELECT pg_backend_pid()")).scalar_one()
        if wait_at == "advisory":
            holder.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
                {"key": f"b14a:entry:{cmd.id}"},
            )
            locktype = "advisory"
        else:
            table, identity = {
                "manuscript": ("manuscript_versions", cmd.manuscript_version_id),
                "publication": ("publications", cmd.publication_id),
                "event_actor_fk": ("actors", env[2].actor_id),
            }[wait_at]
            holder.execute(
                text(f"SELECT id FROM {table} WHERE id=:id FOR UPDATE"), {"id": identity}
            )
            locktype = "transactionid"
        with ThreadPoolExecutor(1) as pool:
            future = pool.submit(owner.transition_publication_internal_review, env[2], cmd)
            try:
                witness = _wait_for_pg_blocker(env[5], pid, locktype)
                credentials.until = witness["observed_at"]
            finally:
                holder.rollback()
            with pytest.raises(ResearchBaseError) as error:
                future.result(timeout=15)
            assert error.value.code == ErrorCode.FORBIDDEN
    assert counts(env) == before


def test_real_legacy_target_first_deadlock_retries_one_effect(b05_env, monkeypatch):
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork

    env = b05_env
    seal(env)
    cmd = command(env)
    original = SqlAlchemyPublicationRepository.lock_entry_target
    normalize = SqlAlchemyUnitOfWork._command_database_error
    states, sessions = [], []

    def target(self, *args):
        sessions.append(self._session)
        self._session.execute(text("SET LOCAL deadlock_timeout='100ms'"))
        return original(self, *args)

    def observed(self, exc):
        states.append(getattr(exc.orig, "sqlstate", None))
        return normalize(self, exc)

    monkeypatch.setattr(SqlAlchemyPublicationRepository, "lock_entry_target", target)
    monkeypatch.setattr(SqlAlchemyUnitOfWork, "_command_database_error", observed)
    with env[5].connect() as legacy:
        legacy.execute(text("SET LOCAL deadlock_timeout='5s'"))
        legacy.execute(
            text("SELECT id FROM manuscript_versions WHERE id=:id FOR UPDATE"),
            {"id": cmd.manuscript_version_id},
        )
        pid = legacy.execute(text("SELECT pg_backend_pid()")).scalar_one()
        with ThreadPoolExecutor(1) as pool:
            future = pool.submit(enter, env, cmd)
            try:
                _wait_for_pg_blocker(env[5], pid, "transactionid")
                # Legacy parent-after-target path creates a real cycle with entry's W.
                legacy.execute(text("LOCK TABLE publications IN ROW EXCLUSIVE MODE"))
            finally:
                legacy.rollback()
            assert future.result(timeout=15).id == cmd.id
    assert "40P01" in states
    assert 2 <= len(sessions) <= 3 and len({id(s) for s in sessions}) == len(sessions)
    assert counts(env)[1] == 2


@pytest.mark.parametrize("mutation", ["role", "binding", "membership", "validity"])
@pytest.mark.parametrize("order", ["entry_first", "mutation_first"])
def test_actual_mutable_inputs_both_commit_orders(b05_env, monkeypatch, mutation, order):
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
        if "UPDATE publications" in statement if order == "entry_first" else marker in statement:
            holder["pid"] = conn.connection.driver_connection.info.backend_pid
            entered.set()
            assert release.wait(15)

    def first():
        holder["thread"] = get_ident()
        return enter(env, principal=env[3]) if order == "entry_first" else mutate()

    event.listen(env[5], "after_cursor_execute", pause)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            one = pool.submit(first)
            assert entered.wait(15)
            second = mutate if order == "entry_first" else lambda: enter(env, principal=env[3])
            two = pool.submit(second)
            try:
                _wait_for_pg_blocker(
                    env[5],
                    holder["pid"],
                    "relation",
                )
            finally:
                release.set()
            one.result(timeout=20)
            if order == "entry_first":
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
        assert conn.execute(
            text(
                "SELECT count(*) FROM publication_lifecycle_events WHERE new_status='INTERNAL_REVIEW'"
            )
        ).scalar_one() == (1 if order == "entry_first" else 0)


@pytest.mark.parametrize("writer", ["b11", "b13"])
@pytest.mark.parametrize("entry_first", [False, True])
def test_real_b11_b13_writers_share_publication_protocol(
    b05_env, request, monkeypatch, writer, entry_first
):
    from threading import get_ident

    from tests.integration.phase2.test_b05_manuscript_review import create
    from tests.integration.phase2.test_b11_readiness_decision import record
    from tests.integration.phase2.test_b13_grant_consumption import issued

    env = b05_env
    seal(env)
    if writer == "b11":
        create(env)

        def write_readiness():
            return record(env)

        write = write_readiness

        marker = "INSERT INTO decision_records"
    else:
        grant_env = request.getfixturevalue("approval_env")
        owner, actor, grant_cmd, _ = issued(grant_env)
        # Use this same engine for both writers and the SQL lock witness.
        owner._factory = env[4]

        def write_release():
            return owner.record_internal_scientific_release(actor, grant_cmd)

        write = write_release

        marker = "INSERT INTO approval_grant_consumptions"
    cmd = command(env)
    entered, release = Event(), Event()
    holder = {}

    def pause(conn, cursor, sql, params, context, many):
        if get_ident() != holder.get("thread") or entered.is_set():
            return
        if "UPDATE publications" in sql if entry_first else marker in sql:
            holder["pid"] = conn.connection.driver_connection.info.backend_pid
            entered.set()
            assert release.wait(15)

    def first():
        holder["thread"] = get_ident()
        return enter(env, cmd) if entry_first else write()

    event.listen(env[5], "after_cursor_execute", pause)
    try:
        with ThreadPoolExecutor(2) as pool:
            one = pool.submit(first)
            assert entered.wait(15)
            two = pool.submit(write if entry_first else lambda: enter(env, cmd))
            try:
                _wait_for_pg_blocker(env[5], holder["pid"], "relation")
            finally:
                release.set()
            one.result(timeout=20)
            two.result(timeout=20)
    finally:
        release.set()
        event.remove(env[5], "after_cursor_execute", pause)
    assert counts(env)[1] == 2


@pytest.mark.parametrize("entry_first", [False, True])
def test_real_b04_seal_writer_both_commit_orders(b05_env, monkeypatch, entry_first):
    from researchbase.application.manuscript_freeze import FreezeManuscriptCommand

    env = b05_env
    q = env[1]
    preview = env[6].get_manuscript_version(env[2], q)
    freeze_cmd = FreezeManuscriptCommand(
        q.project_id,
        q.publication_id,
        q.manuscript_version_id,
        preview.preview_placement_set_hash,
        preview.preview_content_hash,
    )
    cmd = command(env, expected_content_hash=preview.preview_content_hash)
    entered, release = Event(), Event()
    holder = []
    original = SqlAlchemyPublicationRepository.lock_entry_target

    def pause_entry(self, *args):
        original(self, *args)
        holder.append(self._session.execute(text("SELECT pg_backend_pid()")).scalar_one())
        entered.set()
        assert release.wait(15)

    def pause_freeze(conn, cursor, sql, params, context, many):
        if sql.lstrip().upper().startswith("UPDATE PUBLICATIONS"):
            holder.append(conn.connection.driver_connection.info.backend_pid)
            entered.set()
            assert release.wait(15)

    def freeze():
        return env[6].freeze_manuscript_version(env[2], freeze_cmd)

    # B04 uses the original fixture engine; observe that real command's SQL too.
    freeze_engine = env[10][8]
    if entry_first:
        monkeypatch.setattr(SqlAlchemyPublicationRepository, "lock_entry_target", pause_entry)
    else:
        event.listen(freeze_engine, "after_cursor_execute", pause_freeze)
    try:
        with ThreadPoolExecutor(2) as pool:
            one = pool.submit(enter, env, cmd) if entry_first else pool.submit(freeze)
            assert entered.wait(15)
            two = pool.submit(freeze) if entry_first else pool.submit(enter, env, cmd)
            try:
                _wait_for_pg_blocker(
                    env[5], holder[0], "transactionid" if entry_first else "relation"
                )
            finally:
                release.set()
            admitted = not entry_first
            if entry_first:
                # The legacy parent-first freezer can deadlock with target-first entry.
                # Either bounded victim/retry order is valid; no unsealed entry commits.
                try:
                    admitted = one.result(timeout=20).id == cmd.id
                except ResearchBaseError as error:
                    assert error.code == ErrorCode.FROZEN_REFERENCE_REQUIRED
            else:
                one.result(timeout=20)
            two.result(timeout=20)
    finally:
        release.set()
        if not entry_first:
            event.remove(freeze_engine, "after_cursor_execute", pause_freeze)
    assert counts(env)[1] == (2 if admitted else 1)
