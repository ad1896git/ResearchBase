import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest
from sqlalchemy import text
from tests.integration.phase3.intent_fixtures import _intent_env as _intent_env
from tests.integration.phase3.intent_fixtures import effect_counts

from researchbase.foundation.errors import ErrorCode, ResearchBaseError


def observed_wait(env, pattern):
    deadline = time.monotonic() + 6
    while time.monotonic() < deadline:
        with env.owning_engine.connect() as conn:
            row = (
                conn.execute(
                    text(
                        "SELECT xact_start,query_start,clock_timestamp() observed_at,query FROM pg_stat_activity WHERE datname=current_database() AND wait_event_type='Lock' AND query LIKE :pattern"  # noqa: E501
                    ),
                    {"pattern": pattern},
                )
                .mappings()
                .first()
            )
            if row:
                return dict(row)
        time.sleep(0.01)
    raise AssertionError("required actual wait not observed")


def outcome(env, command):
    try:
        return env.intents.execute(command)
    except ResearchBaseError as exc:
        return exc.code


@pytest.mark.parametrize("wait", ["first_share", "second_key", "task_row", "version_row"])
def test_observed_wait_rechecks_intent_authority(intent_env, monkeypatch, wait):
    env = intent_env
    import threading

    from sqlalchemy import event

    checks = []
    acquired_at = []
    main_thread = threading.get_ident()

    def acquired(conn, cursor, statement, parameters, context, many):
        if threading.get_ident() == main_thread:
            return
        selected = (
            statement.startswith("LOCK TABLE actor_subject_bindings")
            if wait == "first_share"
            else statement.startswith("SELECT pg_advisory_xact_lock")
            and parameters.get("key") == f"pr302:execution:{env.intent.arguments.execution_id}"
            if wait == "second_key"
            else statement.startswith("SELECT id FROM research_tasks") and "FOR UPDATE" in statement
            if wait == "task_row"
            else statement.startswith("SELECT id FROM agent_versions") and "FOR UPDATE" in statement
        )
        if selected:
            acquired_at.append(conn.execute(text("SELECT clock_timestamp()")).scalar_one())

    event.listen(env.owning_engine, "after_cursor_execute", acquired)
    before = effect_counts(env)
    with env.owning_engine.connect() as holder:
        tx = holder.begin()
        if wait == "first_share":
            holder.execute(text("LOCK TABLE actor_subject_bindings IN ROW EXCLUSIVE MODE"))
            pattern = "LOCK TABLE actor_subject_bindings%"
        elif wait == "second_key":
            key = f"pr302:execution:{env.intent.arguments.execution_id}"
            holder.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"), {"key": key}
            )
            pattern = "SELECT pg_advisory_xact_lock%"
        else:
            table = "research_tasks" if wait == "task_row" else "agent_versions"
            identity = (
                env.intent.arguments.research_task_id
                if wait == "task_row"
                else env.intent.arguments.agent_version_id
            )
            holder.execute(
                text(f"SELECT id FROM {table} WHERE id=:id FOR UPDATE"), {"id": identity}
            )
            pattern = f"SELECT id FROM {table}%FOR UPDATE"
        expiry = holder.execute(text("SELECT clock_timestamp()+interval '0.7 second'")).scalar_one()

        def valid(principal, at):
            checks.append(at)
            return at < expiry

        monkeypatch.setattr(env.credentials, "is_valid", valid)
        with ThreadPoolExecutor(1) as pool:
            job = pool.submit(outcome, env, env.intent)
            row = observed_wait(env, pattern)
            assert row["xact_start"] < expiry and row["observed_at"] < expiry
            while holder.execute(text("SELECT clock_timestamp()")).scalar_one() < expiry:
                time.sleep(0.01)
            tx.commit()
            result = job.result(timeout=8)
        assert result == ErrorCode.FORBIDDEN
        assert acquired_at and acquired_at[-1] >= expiry
        assert checks[-1] >= acquired_at[-1] and checks[-1] > row["observed_at"]
        assert any(at < row["observed_at"] for at in checks)
        print(
            "wait evidence",
            wait,
            {
                **row,
                "expiry_at": expiry,
                "lock_wait_started_at": row["observed_at"],
                "lock_acquired_at": acquired_at[-1],
                "authorization_checked_at": checks[-1],
            },
            "effects",
            effect_counts(env),
        )
    event.remove(env.owning_engine, "after_cursor_execute", acquired)
    assert effect_counts(env) == before


def test_same_command_revision_and_existing_writer_races(intent_env):
    env = intent_env
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: outcome(env, env.intent), range(2)))
    assert all(
        getattr(r, "result_execution_id", None) == env.intent.arguments.execution_id
        for r in results
    )
    assert sum(getattr(r, "replayed", False) for r in results) == 1
    assert effect_counts(env)["agent_execution_instances"] == 1


@pytest.mark.parametrize("revocation", ["membership", "credential"])
def test_membership_revocation_during_first_share_wait(intent_env, monkeypatch, revocation):
    import threading

    from tests.integration.phase3.intent_fixtures import human_researcher

    from researchbase.application.phase2_identity import (
        RevokeActorSubjectBinding,
        SuspendProjectMembership,
    )
    from researchbase.foundation.ids import new_uuid7
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork

    env = intent_env
    principal = human_researcher(env)
    command = replace(env.intent, caller=principal)
    with env.owning_engine.connect() as conn:
        membership = conn.execute(
            text(
                "SELECT id FROM project_memberships WHERE actor_id=:actor AND project_id=:project"
            ),
            {"actor": principal.actor_id, "project": env.project},
        ).scalar_one()
        binding = conn.execute(
            text("SELECT id FROM actor_subject_bindings WHERE actor_id=:actor"),
            {"actor": principal.actor_id},
        ).scalar_one()
    ready, release = threading.Event(), threading.Event()
    holder_thread = []
    original = SqlAlchemyUnitOfWork.commit

    def commit(uow):
        if holder_thread and threading.get_ident() == holder_thread[0]:
            ready.set()
            assert release.wait(8)
        original(uow)

    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", commit)
    before = effect_counts(env)

    def revoke():
        holder_thread.append(threading.get_ident())
        if revocation == "membership":
            env.identity.suspend_project_membership(
                SuspendProjectMembership(
                    env.owner, env.project, membership, "revoked during prefix wait", new_uuid7()
                )
            )
        else:
            env.identity.revoke_actor_subject_binding(
                RevokeActorSubjectBinding(
                    env.operator, binding, "credential revoked during prefix wait", new_uuid7()
                )
            )

    with ThreadPoolExecutor(2) as pool:
        writer = pool.submit(revoke)
        assert ready.wait(6)
        job = pool.submit(outcome, env, command)
        try:
            observed_wait(env, "LOCK TABLE actor_subject_bindings%")
        finally:
            release.set()
        writer.result(timeout=8)
        assert job.result(timeout=8) == ErrorCode.FORBIDDEN
    assert effect_counts(env) == before


def test_availability_change_at_existing_s1_writer_wait(intent_env, monkeypatch):
    import threading

    from researchbase.agent_runtime.application.agent_contracts import ChangeAgentAvailability
    from researchbase.foundation.ids import new_uuid7
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork

    env = intent_env
    ready, release = threading.Event(), threading.Event()
    holder_thread = []
    original = SqlAlchemyUnitOfWork.commit

    def commit(uow):
        if holder_thread and threading.get_ident() == holder_thread[0]:
            ready.set()
            assert release.wait(8)
        original(uow)

    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", commit)
    change = replace(
        env.version_command,
        command_id=new_uuid7(),
        operation="change_agent_availability",
        expected_revision=1,
        arguments=ChangeAgentAvailability(
            env.intent.arguments.agent_version_id, "DISABLED", "disable while intent waits"
        ),
    )
    before = effect_counts(env)

    def change_version():
        holder_thread.append(threading.get_ident())
        return env.service.execute(change)

    with ThreadPoolExecutor(2) as pool:
        writer = pool.submit(change_version)
        assert ready.wait(6)
        intent = pool.submit(outcome, env, env.intent)
        try:
            observed_wait(env, "SELECT rb_phase2_lock_project%")
        finally:
            release.set()
        assert writer.result(timeout=8).resulting_revision == 2
        assert intent.result(timeout=8) == ErrorCode.INVALID_STATE_TRANSITION
    after = effect_counts(env)
    assert after["agent_execution_instances"] == before["agent_execution_instances"]
    assert after["agent_execution_events"] == before["agent_execution_events"]
    assert after["agent_command_receipts"] == before["agent_command_receipts"] + 1


def contend_with_writer(env, monkeypatch, write, pattern):
    """Run an unchanged owning Application command before releasing its real locks."""
    import threading

    from researchbase.persistence.uow import SqlAlchemyUnitOfWork

    ready, release = threading.Event(), threading.Event()
    holder_thread = []
    original = SqlAlchemyUnitOfWork.commit

    def commit(uow):
        if holder_thread and threading.get_ident() == holder_thread[0]:
            ready.set()
            assert release.wait(8)
        original(uow)

    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", commit)

    def writer():
        holder_thread.append(threading.get_ident())
        return write()

    with ThreadPoolExecutor(2) as pool:
        owning = pool.submit(writer)
        assert ready.wait(6)
        creating = pool.submit(outcome, env, env.intent)
        try:
            observed_wait(env, pattern)
        finally:
            release.set()
        return owning.result(timeout=8), creating.result(timeout=8)


def test_unchanged_task_writer_coexistence(intent_env, monkeypatch):
    env = intent_env
    cancellation = env.planning.command(
        "cancel_research_task",
        env.intent.arguments.research_task_id,
        3,
        {"reason": "independent cancellation"},
    )
    _, result = contend_with_writer(
        env,
        monkeypatch,
        lambda: env.planning.service.execute(env.owner, cancellation),
        "SELECT rb_phase2_lock_project%",
    )
    assert result == ErrorCode.INVALID_STATE_TRANSITION
    assert effect_counts(env)["agent_execution_instances"] == 0


def test_unchanged_phase2_writer_coexistence(intent_env, monkeypatch):
    from researchbase.application.source_identity import (
        RegisterLiteratureSource,
        SourceIdentityService,
    )
    from researchbase.domain.source_identity import SourceKind
    from researchbase.foundation.ids import new_uuid7

    env = intent_env
    source = SourceIdentityService(env.owning_factory, env.credentials)
    command = RegisterLiteratureSource(
        env.owner, env.project, SourceKind.OTHER, "Independent Phase 2 source", new_uuid7()
    )
    saved, result = contend_with_writer(
        env,
        monkeypatch,
        lambda: source.register_literature_source(command),
        "LOCK TABLE actor_subject_bindings%",
    )
    assert saved["source_id"] is not None
    assert not isinstance(result, ErrorCode)
    assert result.result_execution_id == env.intent.arguments.execution_id


def test_unchanged_gateway_writer_coexistence(gateway, request, monkeypatch):
    # The existing gateway fixture is established before upgrading this same database
    # to the intent head. Registering its existing policy performs no invocation/spend.
    from tests.integration.phase3.gateway_fixtures import install

    env = request.getfixturevalue("intent_env")
    _, result = contend_with_writer(
        env, monkeypatch, lambda: install(gateway), "SELECT rb_phase2_lock_project%"
    )
    assert not isinstance(result, ErrorCode)
    assert result.result_execution_id == env.intent.arguments.execution_id
    assert effect_counts(env)["capability_invocations"] == 0
