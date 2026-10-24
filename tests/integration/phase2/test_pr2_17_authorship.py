"""TEST ONLY disposable PostgreSQL facts, entitlement, replay and corruption."""

from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from researchbase.application.authorship import (
    AuthorshipService,
    CreateAuthorshipSnapshotCommand,
    GetAuthorshipSnapshotQuery,
    GetContributionQuery,
    RecordContributionCommand,
)
from researchbase.application.phase2_identity import AssignProjectRole, CloseProjectRole
from researchbase.application.publication import PublicationService
from researchbase.foundation.artifact_store import ContentAddressedFilesystemArtifactStore
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.uow import SqlAlchemyUnitOfWork
from tests.disposable_postgres import disposable_database
from tests.integration.phase2.test_pr2_00_challenges import _service as identity_service
from tests.integration.phase2.test_pr2_00_ownership import _add_owner
from tests.integration.phase2.test_pr2_01_source_identity import _authorized_service

pytestmark = pytest.mark.integration
REVISION = "0046_pr2_17_authorship"
PREVIOUS = "0045_pr2_16_basic_approval"


@pytest.fixture
def authorship_url(monkeypatch):
    with disposable_database("researchbase_pr212_test_") as url:
        monkeypatch.setenv("DATABASE_URL", url)
        yield url


class Credentials:
    enabled = True
    expires = None

    def is_valid(self, principal, at):
        return self.enabled and (self.expires is None or at < self.expires)


@pytest.fixture
def authorship_env(authorship_url, tmp_path):
    engine, _, _, principal, project = _authorized_service(authorship_url)
    credentials = Credentials()
    factory = lambda: SqlAlchemyUnitOfWork(sessionmaker(engine, expire_on_commit=False))  # noqa: E731
    publications = PublicationService(
        factory, credentials, ContentAddressedFilesystemArtifactStore(tmp_path / "cas")
    )
    pub = publications.create_publication(
        principal, project, "PAPER", "TEST ONLY publication", uuid4()
    )
    service = AuthorshipService(factory, credentials)
    yield service, factory, engine, credentials, principal, project, pub.id
    engine.dispose()


def _record(env, **changes):
    return replace(
        RecordContributionCommand(
            uuid4(), env[5], env[6], env[4].actor_id, "WRITING", "TEST ONLY writing"
        ),
        **changes,
    )


def _snapshot(env, ids, **changes):
    author = env[4].actor_id
    return replace(
        CreateAuthorshipSnapshotCommand(uuid4(), env[5], env[6], (author,), (author,), (), ids),
        **changes,
    )


def _count(env):
    with env[2].connect() as conn:
        return tuple(
            conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
            for table in ("contribution_records", "authorship_snapshots")
        )


def test_creations_exact_reads_restart_replay_and_new_fact(authorship_env):
    env = authorship_env
    service, factory, engine, credentials, principal, project, _ = env
    cmd = _record(env)
    record = service.record_contribution(principal, cmd)
    snap_cmd = _snapshot(env, (record.id,))
    snapshot = service.create_authorship_snapshot(principal, snap_cmd)
    restarted = AuthorshipService(factory, credentials)
    assert restarted.record_contribution(principal, cmd) == record
    assert restarted.create_authorship_snapshot(principal, snap_cmd) == snapshot
    assert restarted.get_contribution(principal, GetContributionQuery(project, record.id)) == record
    assert (
        restarted.get_authorship_snapshot(
            principal, GetAuthorshipSnapshotQuery(project, snapshot.id)
        )
        == snapshot
    )
    assert snapshot.contributions[0].contribution_record.content_hash == record.content_hash
    assert restarted.record_contribution(principal, replace(cmd, id=uuid4())).id != record.id
    assert _count(env) == (2, 1)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM manuscript_versions")).scalar_one() == 0
        assert conn.execute(text("SELECT count(*) FROM approval_grants")).scalar_one() == 0
        assert conn.execute(text("SELECT count(*) FROM claims")).scalar_one() == 0


def test_agent_evidence_but_no_agent_authorship_and_coverage(authorship_env):
    env = authorship_env
    agent, other = uuid4(), uuid4()
    with env[2].begin() as conn:
        for identity, kind in ((agent, "AGENT"), (other, "HUMAN")):
            conn.execute(
                text(
                    "INSERT INTO actors(id,actor_type,display_name,created_at) VALUES "
                    "(:id,:kind,'TEST ONLY',clock_timestamp())"
                ),
                {"id": identity, "kind": kind},
            )
    human = env[0].record_contribution(env[4], _record(env))
    evidence = env[0].record_contribution(
        env[4], _record(env, actor_id=agent, contribution_role="SOFTWARE")
    )
    snapshot = env[0].create_authorship_snapshot(env[4], _snapshot(env, (human.id, evidence.id)))
    assert len(snapshot.contributions) == 2 and len(snapshot.authors) == 1
    for author, corresponding in ((agent, agent), (other, other)):
        with pytest.raises(ResearchBaseError) as error:
            env[0].create_authorship_snapshot(
                env[4],
                _snapshot(
                    env,
                    (human.id, evidence.id),
                    author_ids=(author,),
                    corresponding_author_ids=(corresponding,),
                ),
            )
        assert error.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    assert _count(env) == (2, 1)


def test_changed_uuid_material_and_foreign_denial(authorship_env):
    env = authorship_env
    cmd = _record(env)
    record = env[0].record_contribution(env[4], cmd)
    with pytest.raises(ResearchBaseError) as error:
        env[0].record_contribution(env[4], replace(cmd, contribution_statement="Changed"))
    assert error.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    foreign = uuid4()
    with env[2].begin() as conn:
        conn.execute(
            text(
                "INSERT INTO projects(id,name,created_by,created_at) VALUES (:id,'TEST ONLY "
                "foreign',:actor,clock_timestamp())"
            ),
            {"id": foreign, "actor": env[4].actor_id},
        )
    with pytest.raises(ResearchBaseError) as error:
        env[0].get_contribution(env[4], GetContributionQuery(foreign, record.id))
    assert error.value.code is ErrorCode.FORBIDDEN
    with pytest.raises(ResearchBaseError) as error:
        env[0].get_contribution(env[4], GetContributionQuery(env[5], uuid4()))
    assert error.value.code is ErrorCode.NOT_FOUND


def test_role_loss_replays_but_no_new_write_and_lost_read_denies(authorship_env):
    env = authorship_env
    cmd = _record(env)
    record = env[0].record_contribution(env[4], cmd)
    snap_cmd = _snapshot(env, (record.id,))
    snapshot = env[0].create_authorship_snapshot(env[4], snap_cmd)
    with env[2].begin() as conn:
        _add_owner(
            conn,
            actor_id=uuid4(),
            project_id=env[5],
            now=datetime.now(UTC),
            event_kind="ACTIVATED",
            request_id=uuid4(),
        )
    identity, _, _ = identity_service(env[2].url.render_as_string(hide_password=False))
    viewer = identity.assign_project_role(
        AssignProjectRole(env[4], env[5], env[4].actor_id, "VIEWER", "TEST ONLY reader", uuid4())
    )
    with env[2].connect() as conn:
        owner = conn.execute(
            text("SELECT id FROM project_role_assignments WHERE actor_id=:actor AND role='OWNER'"),
            {"actor": env[4].actor_id},
        ).scalar_one()
    identity.close_project_role(
        CloseProjectRole(env[4], env[5], owner, "TEST ONLY writer loss", uuid4())
    )
    assert AuthorshipService(env[1], env[3]).record_contribution(env[4], cmd) == record
    assert env[0].create_authorship_snapshot(env[4], snap_cmd) == snapshot
    with pytest.raises(ResearchBaseError) as error:
        env[0].record_contribution(env[4], replace(cmd, id=uuid4()))
    assert error.value.code is ErrorCode.FORBIDDEN
    with pytest.raises(ResearchBaseError) as error:
        env[0].create_authorship_snapshot(env[4], replace(snap_cmd, id=uuid4()))
    assert error.value.code is ErrorCode.FORBIDDEN
    env[3].enabled = False
    with pytest.raises(ResearchBaseError) as error:
        env[0].record_contribution(env[4], cmd)
    assert error.value.code is ErrorCode.AUTHENTICATION_REQUIRED
    with pytest.raises(ResearchBaseError) as error:
        env[0].create_authorship_snapshot(env[4], snap_cmd)
    assert error.value.code is ErrorCode.AUTHENTICATION_REQUIRED
    env[3].enabled = True
    # The retained owner closes the caller's VIEWER role through the canonical identity boundary.
    with env[2].connect() as conn:
        actor = conn.execute(
            text(
                "SELECT actor_id FROM project_role_assignments WHERE role='OWNER' AND "
                "effective_until IS NULL"
            )
        ).scalar_one()
    retained_owner = replace(
        env[4],
        actor_id=actor,
        deployment_id="test-deployment",
        subject_value=str(actor.int),
        credential_id=f"uid:{actor.int}",
    )
    identity.close_project_role(
        CloseProjectRole(retained_owner, env[5], viewer, "TEST ONLY read loss", uuid4())
    )
    with pytest.raises(ResearchBaseError) as error:
        env[0].record_contribution(env[4], cmd)
    assert error.value.code is ErrorCode.FORBIDDEN
    with pytest.raises(ResearchBaseError) as error:
        env[0].create_authorship_snapshot(env[4], snap_cmd)
    assert error.value.code is ErrorCode.FORBIDDEN


@pytest.mark.parametrize("kind", ["record", "snapshot"])
def test_saved_corruption_fails_closed(authorship_env, kind):
    env = authorship_env
    record = env[0].record_contribution(env[4], _record(env))
    snapshot = env[0].create_authorship_snapshot(env[4], _snapshot(env, (record.id,)))
    table = "contribution_records" if kind == "record" else "authorship_snapshots"
    identity = record.id if kind == "record" else snapshot.id
    # Deliberate TEST ONLY administrative corruption, never normal-role fixtures.
    with env[2].begin() as conn:
        conn.execute(text(f"ALTER TABLE {table} DISABLE TRIGGER USER"))
        conn.execute(
            text(f"UPDATE {table} SET content_hash=:digest WHERE id=:id"),
            {"digest": "0" * 64, "id": identity},
        )
        conn.execute(text(f"ALTER TABLE {table} ENABLE TRIGGER USER"))
    with pytest.raises(ResearchBaseError) as error:
        if kind == "record":
            env[0].get_contribution(env[4], GetContributionQuery(env[5], identity))
        else:
            env[0].get_authorship_snapshot(env[4], GetAuthorshipSnapshotQuery(env[5], identity))
    assert error.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION


def test_authentication_precedes_lookup(authorship_env):
    env = authorship_env
    with pytest.raises(ResearchBaseError) as error:
        env[0].record_contribution(None, _record(env))
    assert error.value.code is ErrorCode.AUTHENTICATION_REQUIRED
    assert _count(env) == (0, 0)


def test_researcher_first_execution_and_snapshot_changed_material(authorship_env):
    env = authorship_env
    with env[2].begin() as conn:
        _add_owner(
            conn,
            actor_id=uuid4(),
            project_id=env[5],
            now=datetime.now(UTC),
            event_kind="ACTIVATED",
            request_id=uuid4(),
        )
    identity, _, _ = identity_service(env[2].url.render_as_string(hide_password=False))
    identity.assign_project_role(
        AssignProjectRole(
            env[4], env[5], env[4].actor_id, "RESEARCHER", "TEST ONLY researcher", uuid4()
        )
    )
    with env[2].connect() as conn:
        owner = conn.execute(
            text("SELECT id FROM project_role_assignments WHERE actor_id=:actor AND role='OWNER'"),
            {"actor": env[4].actor_id},
        ).scalar_one()
    identity.close_project_role(
        CloseProjectRole(env[4], env[5], owner, "TEST ONLY researcher only", uuid4())
    )
    first = env[0].record_contribution(env[4], _record(env))
    second = env[0].record_contribution(env[4], _record(env))
    command = _snapshot(env, (first.id, second.id))
    result = env[0].create_authorship_snapshot(env[4], command)
    assert result.created_by == env[4].actor_id
    with pytest.raises(ResearchBaseError) as error:
        env[0].create_authorship_snapshot(
            env[4], replace(command, contribution_record_ids=(second.id, first.id))
        )
    assert error.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    assert _count(env) == (2, 1)
