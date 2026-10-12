"""Contract-first PostgreSQL checks for exact, field-compliant transcript binding."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker

from researchbase.application.commands import (
    CreateArtifactCommand,
    CreateArtifactVersionCommand,
    FreezeArtifactVersionCommand,
)
from researchbase.application.discussion import DiscussionService
from researchbase.domain.artifact import ArtifactId, ArtifactVersionId
from researchbase.domain.organization import ProjectId
from researchbase.foundation.artifact_store import ContentAddressedFilesystemArtifactStore
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.execution_context import ExecutionContext
from researchbase.foundation.time import SystemClock, format_utc
from researchbase.persistence.uow import SqlAlchemyUnitOfWork
from tests.application_compat import LegacyApplicationService as ApplicationService
from tests.integration.phase2.test_pr2_10_discussion_persistence import (
    _create,
)
from tests.integration.phase2.test_pr2_10_discussion_persistence import (
    discussion_database_url as _discussion_database_url,
)
from tests.integration.phase2.test_pr2_10_discussion_persistence import (
    discussion_env as _discussion_env,
)

pytestmark = pytest.mark.integration
discussion_database_url = _discussion_database_url
discussion_env = _discussion_env


def _upgrade(url: str) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "0034_pr2_10_exact_transcript_binding")


def _service(env, tmp_path):
    engine = env[1]
    factory = lambda: SqlAlchemyUnitOfWork(  # noqa: E731
        sessionmaker(engine, expire_on_commit=False, autoflush=False)
    )
    store = ContentAddressedFilesystemArtifactStore(tmp_path / "cas")
    return DiscussionService(factory, env[2], store), factory, store


def _closed(env, utterance: str = "A test-only turn"):
    original, _, _, principal, project, _, source = env
    session_id = _create(env).session_id
    original.append(principal, project, session_id, "human", utterance,
                    (source,), (), uuid4())
    original.close(principal, project, session_id, uuid4())
    return session_id


def _artifact(factory, store, principal, project, content: bytes,
              kind: str = "discussion_transcript") -> UUID:
    app = ApplicationService(factory, SystemClock(), store)
    context = ExecutionContext(actor_id=principal.actor_id, request_id=uuid4(),
                               client_type="test")
    artifact = app.create_artifact(CreateArtifactCommand(
        ProjectId(project), kind, "Test-only transcript", None, context
    ))
    version = app.create_artifact_version(CreateArtifactVersionCommand(
        ArtifactId(artifact.id), content, None, None, "application/json", len(content), None,
        context,
    ))
    app.freeze_artifact_version(FreezeArtifactVersionCommand(
        ArtifactId(artifact.id), ArtifactVersionId(version.id), context, version.row_version,
    ))
    return UUID(str(version.id))


def test_exact_binding_and_restart_preserve_frozen_shape(
    discussion_env, discussion_database_url, tmp_path
):
    _upgrade(discussion_database_url)
    service, factory, store = _service(discussion_env, tmp_path)
    _, engine, _, principal, project, _, _ = discussion_env
    session_id = _closed(discussion_env, "Unicode Ω and quote \\\" with newline\n")
    candidate = service.read(principal, project, session_id).derived_candidates[0]
    version_id = _artifact(factory, store, principal, project, candidate.content)
    request_id = uuid4()
    first = service.bind_transcript(principal, project, session_id, version_id, request_id)
    assert service.bind_transcript(principal, project, session_id, version_id, request_id) == first
    restarted = DiscussionService(factory, discussion_env[2], store)
    view = restarted.read(principal, project, session_id)
    assert view.transcript_artifact_version_id == version_id
    assert view.derived_candidates[0].content == candidate.content
    with engine.connect() as conn:
        assert conn.execute(text("SELECT pr210_transcript_cjson(:id)"),
                            {"id": session_id}).scalar_one().encode("utf-8") == candidate.content
        for instant in (datetime(2026, 10, 12, 3, 0, tzinfo=UTC),
                        datetime(2026, 10, 12, 3, 0, 0, 123456, tzinfo=UTC)):
            assert conn.execute(text("SELECT pr210_cjson_time(:instant)"),
                                {"instant": instant}).scalar_one() == f'"{format_utc(instant)}"'
        columns = conn.execute(text("""SELECT column_name FROM information_schema.columns
          WHERE table_name='discussion_sessions' AND column_name LIKE 'transcript%'"""))
        assert columns.scalars().all() == ["transcript_artifact_version_id"]
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0034_pr2_10_exact_transcript_binding"
        )
    with pytest.raises(ResearchBaseError):
        service.request_promotion(principal, project, session_id)


def test_direct_sql_wrong_version_kind_and_missing_reference_fail_atomically(
    discussion_env, discussion_database_url, tmp_path
):
    _upgrade(discussion_database_url)
    service, factory, store = _service(discussion_env, tmp_path)
    _, engine, _, principal, project, _, _ = discussion_env
    session_id = _closed(discussion_env)
    content = service.read(principal, project, session_id).derived_candidates[0].content
    wrong_content = _artifact(factory, store, principal, project, b"{}")
    wrong_kind = _artifact(factory, store, principal, project, content, "other_artifact")
    correct = _artifact(factory, store, principal, project, content)
    other_project, other_artifact, other_version = uuid4(), uuid4(), uuid4()
    with engine.begin() as conn:
        conn.execute(text("""INSERT INTO projects(id,name,created_by,created_at)
          VALUES (:id,'Test-only other project',:actor,now())"""),
          {"id": other_project, "actor": principal.actor_id})
        conn.execute(text("""INSERT INTO artifacts(id,project_id,artifact_type,name,
          created_by,created_at) VALUES (:id,:project,'discussion_transcript',
          'Test-only foreign transcript',:actor,now())"""),
          {"id": other_artifact, "project": other_project, "actor": principal.actor_id})
        conn.execute(text("""INSERT INTO artifact_versions(id,artifact_id,version_number,
          status,media_type,byte_size,content_hash,created_by,created_at,frozen_at)
          SELECT :id,:artifact,1,'FROZEN','application/json',byte_size,content_hash,
                 :actor,now(),now() FROM artifact_versions WHERE id=:source"""),
          {"id": other_version, "artifact": other_artifact,
           "actor": principal.actor_id, "source": correct})
    for version_id in (wrong_content, wrong_kind, other_version, uuid4()):
        with pytest.raises(DBAPIError) as exc:
            with engine.begin() as conn:
                conn.execute(text("""UPDATE discussion_sessions SET
                  transcript_artifact_version_id=:version,row_version=row_version+1
                  WHERE id=:session"""), {"version": version_id, "session": session_id})
        assert getattr(exc.value.orig, "sqlstate", None) == "P17D3"
    with engine.connect() as conn:
        bound = conn.execute(text("""SELECT transcript_artifact_version_id
            FROM discussion_sessions WHERE id=:session"""), {"session": session_id})
        assert bound.scalar_one() is None
    service.bind_transcript(principal, project, session_id, correct, uuid4())
    with pytest.raises(DBAPIError) as exc:
        with engine.begin() as conn:
            conn.execute(text("""UPDATE discussion_sessions SET
              transcript_artifact_version_id=NULL,row_version=row_version+1
              WHERE id=:session"""), {"session": session_id})
    assert getattr(exc.value.orig, "sqlstate", None) == "P17D2"
    with pytest.raises(DBAPIError) as exc:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM artifact_versions WHERE id=:id"), {"id": correct})
    assert getattr(exc.value.orig, "sqlstate", None) == "P17D1"
    with pytest.raises(DBAPIError) as exc:
        with engine.begin() as conn:
            conn.execute(text("UPDATE artifact_versions SET status='ABANDONED' WHERE id=:id"),
                         {"id": correct})
    assert getattr(exc.value.orig, "sqlstate", None) in {"P17D3", "P17D5"}
    with pytest.raises(DBAPIError) as exc:
        with engine.begin() as conn:
            conn.execute(text("""UPDATE artifacts SET artifact_type='other_artifact'
                WHERE id=(SELECT artifact_id FROM artifact_versions WHERE id=:id)"""),
                {"id": correct})
    assert getattr(exc.value.orig, "sqlstate", None) == "P17D3"


def test_authorization_replay_concurrency_and_missing_cas_fail_closed(
    discussion_env, discussion_database_url, tmp_path
):
    _upgrade(discussion_database_url)
    service, factory, store = _service(discussion_env, tmp_path)
    _, _, _, principal, project, _, _ = discussion_env
    session_id = _closed(discussion_env)
    content = service.read(principal, project, session_id).derived_candidates[0].content
    version_id = _artifact(factory, store, principal, project, content)
    for who, target in ((replace(principal, actor_id=uuid4()), project),
                        (principal, uuid4())):
        with pytest.raises(ResearchBaseError) as exc:
            service.bind_transcript(who, target, session_id, version_id, uuid4())
        assert exc.value.code in {ErrorCode.FORBIDDEN, ErrorCode.AUTHENTICATION_REQUIRED}

    def attempt(request_id):
        try:
            return service.bind_transcript(principal, project, session_id, version_id, request_id)
        except ResearchBaseError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, (uuid4(), uuid4())))
    assert sum(result.__class__.__name__ == "DiscussionCommandResult" for result in results) == 1
    assert ErrorCode.INVALID_STATE_TRANSITION in results
    missing_store = ContentAddressedFilesystemArtifactStore(tmp_path / "missing")
    with pytest.raises(ResearchBaseError) as exc:
        DiscussionService(factory, discussion_env[2], missing_store).read(
            principal, project, session_id
        )
    assert exc.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION


def test_downgrade_preserves_unbound_history_and_refuses_bound_history(
    discussion_env, discussion_database_url, tmp_path
):
    _upgrade(discussion_database_url)
    service, factory, store = _service(discussion_env, tmp_path)
    _, engine, _, principal, project, _, _ = discussion_env
    session_id = _closed(discussion_env)
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", discussion_database_url)
    command.downgrade(config, "0033_pr2_11_r2_scientific_conclusion")
    with engine.connect() as conn:
        assert conn.execute(text("SELECT status FROM discussion_sessions WHERE id=:id"),
                            {"id": session_id}).scalar_one() == "CLOSED"
    _upgrade(discussion_database_url)
    content = service.read(principal, project, session_id).derived_candidates[0].content
    version_id = _artifact(factory, store, principal, project, content)
    service.bind_transcript(principal, project, session_id, version_id, uuid4())
    with pytest.raises(DBAPIError):
        command.downgrade(config, "0033_pr2_11_r2_scientific_conclusion")
    with engine.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0034_pr2_10_exact_transcript_binding"
        )
        assert conn.execute(text("""SELECT transcript_artifact_version_id
          FROM discussion_sessions WHERE id=:id"""), {"id": session_id}).scalar_one() == version_id


def test_direct_sql_cannot_bind_version_without_frozen_at(
    discussion_env, discussion_database_url, tmp_path
):
    _upgrade(discussion_database_url)
    service, factory, store = _service(discussion_env, tmp_path)
    _, engine, _, principal, project, _, _ = discussion_env
    session_id = _closed(discussion_env)
    content = service.read(principal, project, session_id).derived_candidates[0].content
    valid_id = _artifact(factory, store, principal, project, content)
    version_id, artifact_id = uuid4(), uuid4()
    with engine.begin() as conn:
        conn.execute(text("""INSERT INTO artifacts(id,project_id,artifact_type,name,
          created_by,created_at) VALUES (:id,:project,'discussion_transcript',
          'Test-only malformed frozen version',:actor,now())"""),
          {"id": artifact_id, "project": project, "actor": principal.actor_id})
        conn.execute(text("""INSERT INTO artifact_versions(id,artifact_id,version_number,
          status,media_type,byte_size,content_hash,created_by,created_at,frozen_at)
          SELECT :id,:artifact,1,'FROZEN','application/json',byte_size,content_hash,
                 :actor,now(),NULL FROM artifact_versions WHERE id=:source"""),
          {"id": version_id, "artifact": artifact_id,
           "actor": principal.actor_id, "source": valid_id})
    with pytest.raises(DBAPIError) as exc:
        with engine.begin() as conn:
            conn.execute(text("""UPDATE discussion_sessions SET
              transcript_artifact_version_id=:version,row_version=row_version+1
              WHERE id=:session"""), {"version": version_id, "session": session_id})
    assert getattr(exc.value.orig, "sqlstate", None) == "P17D3"


def test_direct_sql_cannot_clear_bound_version_frozen_at(
    discussion_env, discussion_database_url, tmp_path
):
    _upgrade(discussion_database_url)
    service, factory, store = _service(discussion_env, tmp_path)
    _, engine, _, principal, project, _, _ = discussion_env
    session_id = _closed(discussion_env)
    content = service.read(principal, project, session_id).derived_candidates[0].content
    version_id = _artifact(factory, store, principal, project, content)
    service.bind_transcript(principal, project, session_id, version_id, uuid4())
    with pytest.raises(DBAPIError) as exc:
        with engine.begin() as conn:
            conn.execute(text("""UPDATE artifact_versions SET frozen_at=NULL,
              row_version=row_version+1 WHERE id=:id"""),
                         {"id": version_id})
    assert getattr(exc.value.orig, "sqlstate", None) in {"P17D1", "P17D2"}
