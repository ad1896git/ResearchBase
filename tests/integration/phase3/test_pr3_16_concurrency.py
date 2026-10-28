"""PG18 create-only waits; no claim of every DML/FK wait or node capacity.

SQL/callback traces establish order. pg_locks/pg_stat_activity establish actual
contention. The project exclusion prevents a second command committing a receipt
while a create holds a later key: late-key tests check receipt lookup after the
wait, then committed replay on the next call. The separate concurrent receipt
case proves replay immediately after real SHARE/project waits.
"""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from threading import Event, get_ident
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from tests.disposable_postgres import disposable_database
from tests.integration.phase2.pr2_20_support import upgrade
from tests.integration.phase2.test_pr2_01_source_identity import _authorized_service
from tests.integration.phase3.agent_fixtures import (
    Credentials as IdentityCredentials,
)
from tests.integration.phase3.agent_fixtures import (
    EnrollmentVerifier,
    SubjectCredentials,
    enrollment,
)
from tests.integration.phase3.conftest import Credentials, PlanningFixture
from tests.integration.phase3.test_pr3_03_concurrency import ADVISORY_SQL, observed_wait
from tests.integration.phase3.test_pr3_04_application import approve, bind
from tests.integration.phase3.test_pr3_16_application import (
    assert_create_effects,
    frozen_references,
    snapshot,
)
from tests.unit.phase3.test_experiment_search import pg_command

from researchbase.agent_runtime.application.agent_versions import AgentVersionService
from researchbase.agent_runtime.application.experiment_search import ExperimentSearchService
from researchbase.agent_runtime.application.research_task import ResearchTaskService
from researchbase.application.phase2_identity import (
    AssignProjectRole,
    CloseProjectRole,
    Phase2IdentityService,
    ProvisionActor,
    ProvisioningAttestation,
    VerifiedSubject,
)
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.artifact_store import ContentAddressedFilesystemArtifactStore
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.ids import new_uuid7
from researchbase.persistence.experiment_search_repository import (
    SqlAlchemyExperimentSearchRepository as Repository,
)
from researchbase.persistence.research_task_repository import SHARE_SQL, SHARE_TABLES
from researchbase.persistence.uow import SqlAlchemyUnitOfWork

OPERATIONS = dict(
    share="share", project="project", command="command_key", task="task_key", actor="actor_key"
)


@pytest.fixture(name="search_env", scope="module")
def _search_env(tmp_path_factory):
    """Create task authority through Application commands, with empty search history."""
    with disposable_database("researchbase_pr212_test_") as url:
        with pytest.MonkeyPatch.context() as patch:
            patch.setenv("DATABASE_URL", url)
            admin, _, _, principal, project = _authorized_service(
                url, migration_revision="0081_agent_execution_intents"
            )
        role = "pr316_" + new_uuid7().hex
        engine = None
        try:
            upgrade(url, "0082_experiment_search_core")
            with admin.begin() as conn:
                conn.execute(
                    text(f"CREATE ROLE {role} NOSUPERUSER NOCREATEDB NOCREATEROLE NOLOGIN")
                )
                conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {role}"))
                conn.execute(
                    text(
                        "GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public "
                        f"TO {role}"
                    )
                )
            engine = create_engine(
                url,
                connect_args={
                    "options": f"-c role={role} -c lock_timeout=10s -c statement_timeout=30s"
                },
            )
            sessions = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

            def factory():
                return SqlAlchemyUnitOfWork(sessions)

            store = ContentAddressedFilesystemArtifactStore(tmp_path_factory.mktemp("search-cas"))
            p = PlanningFixture(
                engine,
                factory,
                ResearchTaskService(factory, Credentials(), store),
                principal,
                project,
                url,
                store,
            )
            task = p.create()
            bind(p, task)
            approve(p, task, 2)
            yield SimpleNamespace(engine=engine, admin=admin, url=url, p=p, task=task, role=role)
        finally:
            if engine is not None:
                engine.dispose()
            with admin.begin() as conn:
                conn.execute(text(f"DROP OWNED BY {role}"))
                conn.execute(text(f"DROP ROLE IF EXISTS {role}"))
            admin.dispose()


@pytest.fixture
def agent_search_env(search_env):
    """Provision Human operator and Agent through public commands under the DML role."""
    source = search_env
    owner = source.p
    trusted = IdentityCredentials()
    verifier = EnrollmentVerifier()
    identity = Phase2IdentityService(
        owner.factory,
        nonce_issuer=trusted,
        operator_policy=trusted,
        credential_verifier=trusted,
        subject_credential_verifier=SubjectCredentials(),
        attestation_verifier=trusted,
        agent_enrollment_verifier=verifier,
        agent_mtls_resolver=trusted,
    )
    # An external verified deployment operator attests provisioning; the durable
    # Human operator used for Agent enrollment is created by the owning command.
    witness = VerifiedPrincipal(
        new_uuid7(),
        owner.principal.deployment_id,
        "MTLS_URI",
        f"spiffe://test/provisioners/{new_uuid7()}",
        "test-provisioner",
        datetime.now(UTC),
    )
    actor = new_uuid7()
    subject = VerifiedSubject(
        owner.principal.deployment_id,
        "MTLS_URI",
        f"spiffe://test/operators/{actor}",
        f"test-operator-{actor}",
    )
    identity.provision_actor(
        ProvisionActor(
            owner.principal,
            subject,
            actor,
            "S8 Human operator",
            ProvisioningAttestation(
                actor,
                subject.deployment_id,
                subject.subject_kind,
                subject.subject_value,
                subject.credential_id,
                witness,
                "a" * 64,
                "test-only:operator-attestation",
                "Provision S8 Human operator",
            ),
            new_uuid7(),
        )
    )
    operator = VerifiedPrincipal(
        actor,
        subject.deployment_id,
        subject.subject_kind,
        subject.subject_value,
        subject.credential_id,
        datetime.now(UTC),
    )
    intake = SimpleNamespace(
        owner=owner.principal,
        project=owner.project,
        operator=operator,
        verifier=verifier,
    )
    enrolled = enrollment(intake)
    AgentVersionService(
        owner.factory,
        trusted,
        identity=identity,
        enrollment_verifier=verifier,
    ).execute(enrolled)
    principal = identity.resolve_agent_subject(enrolled.arguments.subject)
    task = owner.create()
    bind(owner, task)
    approve(owner, task, 2)
    frozen_references(owner)
    return SimpleNamespace(
        engine=source.engine,
        p=replace(owner, principal=principal),
        task=task,
        identity=identity,
        owner=owner.principal,
        role=source.role,
    )


class BoundedCredentials:
    """Explicit trusted test composition: bounded, synchronous and no I/O."""

    def __init__(self, expires_at, trace):
        self.expires_at = expires_at
        self.revoked = Event()
        self.trace = trace

    def is_valid(self, principal, at):
        valid = not self.revoked.is_set() and principal.verified_at <= at < self.expires_at
        self.trace.append(("credential", at, valid))
        return valid


def credentials(env, trace):
    with env.engine.connect() as conn:
        at = conn.execute(text("SELECT clock_timestamp()")).scalar_one()
    return BoundedCredentials(at + timedelta(minutes=5), trace)


def key_for(env, command, stage):
    return {
        "command": f"pr301:command:{env.p.project}:{env.p.principal.actor_id}:{command.command_id}",
        "task": f"pr301:task:{env.task}",
        "actor": f"pr302:actor:{env.p.principal.actor_id}",
    }[stage]


@contextmanager
def blocker(env, command, stage):
    with env.engine.connect() as conn:
        try:
            if stage == "share":
                conn.execute(text("LOCK TABLE actor_subject_bindings IN ROW EXCLUSIVE MODE"))
                query = SHARE_SQL
            elif stage == "project":
                conn.execute(text("SELECT rb_phase2_lock_project(:id)"), {"id": env.p.project})
                query = "rb_phase2_lock_project"
            else:
                conn.execute(text(ADVISORY_SQL), {"key": key_for(env, command, stage)})
                query = "pg_advisory_xact_lock"
            yield conn, query
        finally:
            conn.rollback()


def install_trace(monkeypatch, trace):
    notify, receipt, admission = (
        Repository._notify,
        Repository.committed_receipt,
        ExperimentSearchService._admission,
    )

    def stage(repo, current):
        trace.append(("stage", current.operation))
        return notify(repo, current)

    def saved(repo, *args):
        result = receipt(repo, *args)
        trace.append(("receipt", result is not None))
        return result

    def fresh(repo, task, at):
        trace.append(("fresh", task["row_version"]))
        return admission(repo, task, at)

    monkeypatch.setattr(Repository, "_notify", stage)
    monkeypatch.setattr(Repository, "committed_receipt", saved)
    monkeypatch.setattr(ExperimentSearchService, "_admission", staticmethod(fresh))


def assert_replay(service, env, command, result, trace):
    saved = snapshot(env)
    trace.clear()
    replay = service.create_search_session(env.p.principal, command)
    assert replay == replace(result, command_result=replace(result.command_result, replayed=True))
    # Original expected revision is now stale. Current read entitlement and the
    # committed receipt precede fresh CAS/admission and every later lock class.
    assert trace[0] == ("stage", "share")
    assert any(item[0] == "credential" and item[2] for item in trace)
    assert ("receipt", True) in trace
    assert not any(item[0] == "fresh" for item in trace)
    assert [item for item in trace if item[0] == "stage"] == [("stage", "share")]
    assert snapshot(env) == saved


@pytest.mark.parametrize("kind", ["human", "agent"])
def test_observed_lock_order_and_competing_writers(search_env, request, kind):
    env = search_env if kind == "human" else request.getfixturevalue("agent_search_env")
    if kind == "human":
        frozen_references(env.p)
    first = pg_command(env)
    commands = (
        first,
        replace(
            first,
            command_id=new_uuid7(),
            arguments=replace(first.arguments, session_id=new_uuid7()),
        ),
    )
    before, trace = snapshot(env), {}
    service = ExperimentSearchService(env.p.factory, credentials(env, []))
    main = get_ident()

    def record(conn, cursor, statement, params, context, many):
        if get_ident() != main:
            trace.setdefault(get_ident(), []).append(
                (statement, dict(params) if isinstance(params, dict) else params)
            )

    event.listen(env.engine, "before_cursor_execute", record)
    try:
        with ThreadPoolExecutor(2) as pool:
            with blocker(env, first, "task") as (holder, query):
                jobs = [
                    pool.submit(service.create_search_session, env.p.principal, c) for c in commands
                ]
                waiting = observed_wait(env.engine, blocker=holder, query=query)
                observed_wait(env.engine, blocker=waiting.pid, query="rb_phase2_lock_project")
                with env.engine.connect() as observer:
                    shares = (
                        observer.execute(
                            text(
                                "SELECT relation::regclass::text FROM pg_locks "
                                "WHERE pid=:pid AND granted AND mode='ShareLock' "
                                "AND locktype='relation'"
                            ),
                            {"pid": waiting.pid},
                        )
                        .scalars()
                        .all()
                    )
                    held = observer.execute(
                        text(
                            "SELECT classid::bigint,objid::bigint,granted FROM pg_locks "
                            "WHERE pid=:pid AND locktype='advisory'"
                        ),
                        {"pid": waiting.pid},
                    ).all()
                    # Match the *real* lock inventory, including the blocked task
                    # key; no Run/lineage/checkpoint/AgentVersion namespaces.
                    winning_command = next(
                        c
                        for c in commands
                        if any(
                            p.get("key") == key_for(env, c, "command")
                            for rows in trace.values()
                            for sql, p in rows
                            if isinstance(p, dict) and "pg_advisory_xact_lock" in sql
                        )
                    )
                    keys = [
                        f"researchbase-project:{env.p.project}",
                        key_for(env, winning_command, "command"),
                        key_for(env, first, "task"),
                    ]
                    hashes = {
                        observer.execute(
                            text("SELECT hashtextextended(:key,0)"), {"key": key}
                        ).scalar_one()
                        & ((1 << 64) - 1)
                        for key in keys
                    }
                    assert {(hi << 32) | lo for hi, lo, granted in held} == hashes
                    assert sum(not granted for hi, lo, granted in held) == 1
                    assert set(shares) == set(SHARE_TABLES)
            results = []
            for job in jobs:
                try:
                    results.append(job.result(timeout=15))
                except ResearchBaseError as error:
                    results.append(error)
    finally:
        event.remove(env.engine, "before_cursor_execute", record)
    errors = [result for result in results if isinstance(result, ResearchBaseError)]
    assert len(errors) == 1 and errors[0].code == ErrorCode.CONCURRENT_MODIFICATION
    assert_create_effects(before, snapshot(env), env.task, first.expected_row_version)
    completed = next(
        rows
        for rows in trace.values()
        if any("FOR UPDATE" in sql and "research_tasks" in sql for sql, _ in rows)
    )
    assert completed[0][0] == SHARE_SQL
    lock_sql = [
        (sql, params)
        for sql, params in completed
        if sql == SHARE_SQL
        or "rb_phase2_lock_project" in sql
        or "pg_advisory_xact_lock" in sql
        or "FOR UPDATE" in sql
    ]
    assert lock_sql[0][0] == SHARE_SQL and "rb_phase2_lock_project" in lock_sql[1][0]
    actual_keys = [params["key"] for sql, params in lock_sql if "pg_advisory_xact_lock" in sql]
    expected_keys = [key_for(env, winning_command, "command"), key_for(env, first, "task")]
    if kind == "agent":
        expected_keys.append(key_for(env, first, "actor"))
    assert actual_keys == expected_keys
    last_key = max(i for i, (sql, _) in enumerate(lock_sql) if "pg_advisory_xact_lock" in sql)
    first_row = next(i for i, (sql, _) in enumerate(lock_sql) if "FOR UPDATE" in sql)
    assert last_key < first_row
    assert all(
        "research_tasks" in sql or "research_task_steps" in sql
        for sql, _ in lock_sql
        if "FOR UPDATE" in sql
    )
    print(
        "LOCK_EVIDENCE",
        kind,
        "SQL order",
        actual_keys,
        "DB waits task/project; actor wait covered separately",
    )


@pytest.mark.parametrize("stage", OPERATIONS)
@pytest.mark.parametrize("outcome", ["revoked", "expired", "authority", "replay"])
def test_each_wait_refreshes_entitlement_replay_and_expiry(
    agent_search_env, monkeypatch, stage, outcome
):
    env, trace = agent_search_env, []
    command = pg_command(env)
    verifier = credentials(env, trace)
    expiry = None
    if outcome == "authority":
        with env.engine.connect() as conn:
            role = conn.execute(
                text(
                    "SELECT id FROM project_role_assignments WHERE actor_id=:actor "
                    "AND project_id=:project AND effective_until IS NULL"
                ),
                {"actor": env.p.principal.actor_id, "project": env.p.project},
            ).scalar_one()
            expiry = conn.execute(
                text("SELECT clock_timestamp()+interval '2 seconds'")
            ).scalar_one()
        # Owning identity command schedules a real current-authority boundary.
        # Later project/key locks serialize an immediate concurrent role writer.
        env.identity.close_project_role(
            CloseProjectRole(
                env.owner,
                env.p.project,
                role,
                "S8 scheduled authority revocation",
                new_uuid7(),
                expiry,
            )
        )
    elif outcome == "expired":
        with env.engine.connect() as conn:
            expiry = conn.execute(
                text("SELECT clock_timestamp()+interval '2 seconds'")
            ).scalar_one()
        verifier.expires_at = expiry
    before = snapshot(env)
    install_trace(monkeypatch, trace)
    service = ExperimentSearchService(env.p.factory, verifier)
    with ThreadPoolExecutor(1) as pool:
        with blocker(env, command, stage) as (holder, query):
            job = pool.submit(service.create_search_session, env.p.principal, command)
            waiting = observed_wait(env.engine, blocker=holder, query=query)
            assert waiting.locktype == ("relation" if stage == "share" else "advisory")
            if expiry is not None:
                assert waiting.waitstart < expiry
                # Wait for the explicit DB time boundary, never a sleep-based
                # success guess; record release and post-acquisition validation.
                holder.execute(
                    text(
                        "SELECT pg_sleep(greatest(0,extract(epoch FROM "
                        "(:expiry-clock_timestamp()))))"
                    ),
                    {"expiry": expiry},
                )
                released = holder.execute(text("SELECT clock_timestamp()")).scalar_one()
                assert released >= expiry
            if outcome == "revoked":
                verifier.revoked.set()
        if outcome == "replay":
            result = job.result(timeout=15)
        else:
            with pytest.raises(ResearchBaseError) as error:
                job.result(timeout=15)
            assert error.value.code == ErrorCode.FORBIDDEN
    index = trace.index(("stage", OPERATIONS[stage]))
    refreshed = trace[index + 1 :]
    assert refreshed[0][0] == "credential"
    if outcome == "replay":
        assert refreshed[0][2] and refreshed[1] == ("receipt", False)
        assert any(item[0] == "fresh" for item in refreshed)
        assert_create_effects(before, snapshot(env), env.task, command.expected_row_version)
    else:
        assert snapshot(env) == before
        assert not any(item[0] in ("receipt", "fresh") for item in refreshed)
        if expiry is not None:
            assert refreshed[0][1] >= released >= expiry > waiting.waitstart
            print(
                "EXPIRY_EVIDENCE", stage, outcome, waiting.waitstart, expiry, released, refreshed[0]
            )
        verifier.revoked.clear()
        verifier.expires_at += timedelta(minutes=5)
        if outcome == "authority":
            env.identity.assign_project_role(
                AssignProjectRole(
                    env.owner,
                    env.p.project,
                    env.p.principal.actor_id,
                    "RESEARCHER",
                    "Restore S8 test entitlement",
                    new_uuid7(),
                )
            )
        restored = snapshot(env)
        result = service.create_search_session(env.p.principal, command)
        assert_create_effects(restored, snapshot(env), env.task, command.expected_row_version)
    assert_replay(service, env, command, result, trace)


def test_current_authority_closed_during_observed_share_wait(agent_search_env, monkeypatch):
    env, trace = agent_search_env, []
    command = pg_command(env)
    service = ExperimentSearchService(env.p.factory, credentials(env, trace))
    with env.engine.connect() as conn:
        role = conn.execute(
            text(
                "SELECT id FROM project_role_assignments WHERE actor_id=:actor "
                "AND effective_until IS NULL"
            ),
            {"actor": env.p.principal.actor_id},
        ).scalar_one()
    with ThreadPoolExecutor(1) as pool:
        with blocker(env, command, "share") as (holder, query):
            job = pool.submit(service.create_search_session, env.p.principal, command)
            observed_wait(env.engine, blocker=holder, query=query)
            env.identity.close_project_role(
                CloseProjectRole(
                    env.owner, env.p.project, role, "Revoke waiting caller", new_uuid7()
                )
            )
            before = snapshot(env)
            install_trace(monkeypatch, trace)
        with pytest.raises(ResearchBaseError) as error:
            job.result(timeout=15)
    assert error.value.code == ErrorCode.FORBIDDEN
    assert ("stage", "share") in trace and not any(
        item[0] in ("receipt", "fresh") for item in trace
    )
    assert snapshot(env) == before


@pytest.mark.parametrize("stage", ["share", "project"])
def test_committed_receipt_replays_immediately_after_observed_wait(search_env, monkeypatch, stage):
    env = search_env
    waiter_thread = []

    class WaiterTrace(list):
        def append(self, item):
            if waiter_thread and get_ident() == waiter_thread[0]:
                super().append(item)

    trace = WaiterTrace()
    command = pg_command(env)
    before = snapshot(env)
    install_trace(monkeypatch, trace)
    service = ExperimentSearchService(env.p.factory, credentials(env, trace))
    ready, release = Event(), Event()
    original = SqlAlchemyUnitOfWork.commit

    def commit(uow):
        if not ready.is_set():
            if stage == "share":
                # A lock only: no direct canonical mutation. The writer already
                # owns SHARE and its complete, still-uncommitted command effects.
                uow._require_session().execute(
                    text("LOCK TABLE actor_subject_bindings IN ROW EXCLUSIVE MODE")
                )
            writer_pid.append(
                uow._require_session().execute(text("SELECT pg_backend_pid()")).scalar_one()
            )
            ready.set()
            assert release.wait(8), "receipt writer release not signaled"
        return original(uow)

    def wait_and_replay():
        waiter_thread.append(get_ident())
        return service.create_search_session(env.p.principal, command)

    writer_pid = []
    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", commit)
    with ThreadPoolExecutor(2) as pool:
        writer = pool.submit(service.create_search_session, env.p.principal, command)
        try:
            assert ready.wait(8), "writer did not reach its real commit boundary"
            waiter = pool.submit(wait_and_replay)
            observed_wait(
                env.engine,
                blocker=writer_pid[0],
                query=SHARE_SQL if stage == "share" else "rb_phase2_lock_project",
            )
        finally:
            release.set()
        fresh, replay = writer.result(timeout=15), waiter.result(timeout=15)
    assert replay == replace(fresh, command_result=replace(fresh.command_result, replayed=True))
    index = trace.index(("stage", OPERATIONS[stage]))
    after_wait = trace[index + 1 :]
    assert after_wait[0][0] == "credential" and after_wait[0][2]
    assert after_wait[1] == ("receipt", True)
    assert not any(item[0] == "fresh" for item in after_wait)
    assert not any(item[0] == "stage" for item in after_wait)
    assert_create_effects(before, snapshot(env), env.task, command.expected_row_version)
