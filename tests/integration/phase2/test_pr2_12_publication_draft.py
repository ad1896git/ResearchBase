"""Disposable PostgreSQL contract tests for PR2-12 draft identity and document binding."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker

from researchbase.application.publication import PublicationService
from researchbase.foundation.artifact_store import ContentAddressedFilesystemArtifactStore
from researchbase.foundation.errors import ResearchBaseError
from researchbase.persistence.uow import SqlAlchemyUnitOfWork
from tests.integration.phase2.test_pr2_10_binding_contract import _artifact
from tests.integration.phase2.test_pr2_10_discussion_persistence import (
    discussion_database_url as _discussion_database_url,
)
from tests.integration.phase2.test_pr2_10_discussion_persistence import (
    discussion_env as _discussion_env,
)

pytestmark = pytest.mark.integration
discussion_database_url = _discussion_database_url
discussion_env = _discussion_env


def _setup(env, url, tmp_path):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "0035_pr2_12_publication_draft")
    _, engine, credentials, principal, project, _, _ = env
    factory = lambda: SqlAlchemyUnitOfWork(  # noqa: E731
        sessionmaker(engine, expire_on_commit=False, autoflush=False)
    )
    store = ContentAddressedFilesystemArtifactStore(tmp_path / "cas")
    return (PublicationService(factory, credentials, store), factory, store,
            engine, principal, project)


def test_create_draft_readback_and_no_implicit_freeze(
    discussion_env, discussion_database_url, tmp_path
):
    service, factory, store, engine, principal, project = _setup(
        discussion_env, discussion_database_url, tmp_path
    )
    document = _artifact(factory, store, principal, project, b"Test-only manuscript", "manuscript")
    publication = service.create_publication(principal, project, "PAPER", "Study", uuid4())
    result = service.create_draft(principal, project, publication.id, document,
                                  "Study", None, "INITIAL", uuid4())
    restarted = PublicationService(factory, discussion_env[2], store)
    view = restarted.read_draft(principal, project, publication.id, result.id)
    assert view.document_artifact_version_id == document
    assert view.status == "DRAFT" and view.version_number == 1
    assert view.content_hash is None and view.placement_set_hash is None
    with engine.connect() as conn:
        assert conn.execute(text("""SELECT current_manuscript_version_id
          FROM publications WHERE id=:id"""),
                            {"id": publication.id}).scalar_one() is None
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0035_pr2_12_publication_draft"
        )


def test_invalid_document_and_direct_sql_pointer_rejected(
    discussion_env, discussion_database_url, tmp_path
):
    service, factory, store, engine, principal, project = _setup(
        discussion_env, discussion_database_url, tmp_path
    )
    publication = service.create_publication(principal, project, "PAPER", "Study", uuid4())
    wrong_kind = _artifact(factory, store, principal, project, b"{}", "other_artifact")
    with pytest.raises(ResearchBaseError):
        service.create_draft(principal, project, publication.id, wrong_kind,
                             "Study", None, "INITIAL", uuid4())
    with pytest.raises(DBAPIError) as exc:
        with engine.begin() as conn:
            conn.execute(text("""INSERT INTO manuscript_versions
              (id,publication_id,version_number,status,document_artifact_version_id,
               title,semantic_change_class,created_by,created_at,row_version)
              VALUES (:id,:publication,1,'DRAFT',:document,'Study','INITIAL',:actor,now(),1)"""),
              {"id": uuid4(), "publication": publication.id, "document": wrong_kind,
               "actor": principal.actor_id})
    assert getattr(exc.value.orig, "sqlstate", None) == "P17D3"
    foreign_project, foreign_artifact, foreign_version = uuid4(), uuid4(), uuid4()
    draft_artifact, unfrozen_version = uuid4(), uuid4()
    with engine.begin() as conn:
        conn.execute(text("""INSERT INTO projects(id,name,created_by,created_at)
          VALUES (:id,'Test-only other publication project',:actor,now())"""),
          {"id": foreign_project, "actor": principal.actor_id})
        for artifact_id, owner in ((foreign_artifact, foreign_project),
                                   (draft_artifact, project)):
            conn.execute(text("""INSERT INTO artifacts(id,project_id,artifact_type,name,
              created_by,created_at)
              VALUES (:id,:project,'manuscript','Test-only',:actor,now())"""),
              {"id": artifact_id, "project": owner, "actor": principal.actor_id})
        for version_id, artifact_id, status, frozen_at in (
            (foreign_version, foreign_artifact, "FROZEN", "now()"),
            (unfrozen_version, draft_artifact, "DRAFT", "NULL"),
        ):
            conn.execute(text(f"""INSERT INTO artifact_versions(id,artifact_id,version_number,
              status,media_type,byte_size,content_hash,created_by,created_at,frozen_at)
              VALUES (:id,:artifact,1,:status,'text/plain',1,:digest,:actor,now(),{frozen_at})"""),
              {"id": version_id, "artifact": artifact_id, "status": status,
               "digest": "a" * 64, "actor": principal.actor_id})
    for invalid_id in (foreign_version, unfrozen_version):
        with pytest.raises(DBAPIError) as exc:
            with engine.begin() as conn:
                conn.execute(text("""INSERT INTO manuscript_versions
                  (id,publication_id,version_number,status,document_artifact_version_id,
                   title,semantic_change_class,created_by,created_at,row_version)
                  VALUES (:id,:publication,1,'DRAFT',:document,'Study','INITIAL',
                          :actor,now(),1)"""),
                  {"id": uuid4(), "publication": publication.id, "document": invalid_id,
                   "actor": principal.actor_id})
        assert getattr(exc.value.orig, "sqlstate", None) == "P17D3"
    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            conn.execute(text("""UPDATE publications SET current_manuscript_version_id=:id,
              row_version=row_version+1 WHERE id=:publication"""),
              {"id": uuid4(), "publication": publication.id})
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM manuscript_versions")).scalar_one() == 0


def test_idempotency_authority_and_missing_bytes_fail_closed(
    discussion_env, discussion_database_url, tmp_path
):
    service, factory, store, engine, principal, project = _setup(
        discussion_env, discussion_database_url, tmp_path
    )
    key = uuid4()
    publication = service.create_publication(principal, project, "PAPER", "Study", key)
    assert service.create_publication(principal, project, "PAPER", "Study", key) == publication
    with pytest.raises(ResearchBaseError):
        service.create_publication(principal, project, "PAPER", "Different", key)
    other = replace(principal, actor_id=uuid4())
    with pytest.raises(ResearchBaseError):
        service.create_publication(other, project, "PAPER", "Other", uuid4())
    doc = _artifact(factory, store, principal, project, b"Draft", "manuscript")
    draft_key = uuid4()
    draft = service.create_draft(principal, project, publication.id, doc,
                                 "Study", None, "INITIAL", draft_key)
    assert service.create_draft(principal, project, publication.id, doc,
                                "Study", None, "INITIAL", draft_key) == draft
    with pytest.raises(ResearchBaseError):
        service.create_draft(principal, project, publication.id, doc,
                             "Study", None, "INITIAL", uuid4())
    with pytest.raises(ResearchBaseError):
        service.create_draft(principal, project, publication.id, doc,
                             "Different", None, "INITIAL", draft_key)
    missing = PublicationService(factory, discussion_env[2],
                                 ContentAddressedFilesystemArtifactStore(tmp_path / "missing"))
    with pytest.raises(ResearchBaseError):
        missing.read_draft(principal, project, publication.id, draft.id)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM manuscript_versions")).scalar_one() == 1
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", discussion_database_url)
    with pytest.raises(DBAPIError) as exc:
        command.downgrade(config, "0034_pr2_10_exact_transcript_binding")
    assert getattr(exc.value.orig, "sqlstate", None) == "P17D4"
    with engine.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0035_pr2_12_publication_draft"
        )


def test_concurrent_replay_and_direct_sql_history_guards(
    discussion_env, discussion_database_url, tmp_path
):
    service, factory, store, engine, principal, project = _setup(
        discussion_env, discussion_database_url, tmp_path
    )
    publication = service.create_publication(principal, project, "PAPER", "Study", uuid4())
    document = _artifact(factory, store, principal, project, b"Draft", "manuscript")
    key = uuid4()
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(service.create_draft, principal, project, publication.id,
                               document, "Study", None, "INITIAL", key) for _ in range(2)]
        results = [future.result() for future in futures]
    assert results[0] == results[1]
    draft = results[0]
    other_publication = service.create_publication(
        principal, project, "REPORT", "Other study", uuid4()
    )
    other_draft = service.create_draft(
        principal, project, other_publication.id, document,
        "Other study", None, "INITIAL", uuid4()
    )
    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            conn.execute(text("""UPDATE publications
              SET current_manuscript_version_id=:wrong,row_version=row_version+1
              WHERE id=:publication"""),
              {"wrong": other_draft.id, "publication": publication.id})
    with pytest.raises(DBAPIError) as exc:
        with engine.begin() as conn:
            # Isolate the composite FK from the stricter draft-only update guard.
            conn.execute(text("ALTER TABLE publications DISABLE TRIGGER pr212_publication_guard"))
            conn.execute(text("""UPDATE publications
              SET current_manuscript_version_id=:wrong,row_version=row_version+1
              WHERE id=:publication"""),
              {"wrong": other_draft.id, "publication": publication.id})
    assert getattr(exc.value.orig, "sqlstate", None) == "23503"
    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            conn.execute(text("""UPDATE manuscript_versions SET title='tampered',
              row_version=row_version+1 WHERE id=:id"""), {"id": draft.id})
    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM manuscript_versions WHERE id=:id"),
                         {"id": draft.id})
    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            conn.execute(text("""UPDATE artifacts SET artifact_type='other_artifact'
              WHERE id=(SELECT artifact_id FROM artifact_versions WHERE id=:id)"""),
              {"id": document})


def test_create_draft_response_is_atomic_with_command(
    discussion_env, discussion_database_url, tmp_path
):
    service, factory, store, engine, principal, project = _setup(
        discussion_env, discussion_database_url, tmp_path
    )
    publication = service.create_publication(principal, project, "PAPER", "Study", uuid4())
    document = _artifact(factory, store, principal, project, b"Draft", "manuscript")

    class OnceVerifiedStore:
        def __init__(self):
            self.checks = 0

        def verify(self, digest):
            self.checks += 1
            return self.checks == 1 and store.verify(digest)

        def open(self, digest):
            return store.open(digest)

    bounded = OnceVerifiedStore()
    command = PublicationService(factory, discussion_env[2], bounded)
    draft = command.create_draft(principal, project, publication.id, document,
                                 "Study", None, "INITIAL", uuid4())
    assert bounded.checks == 1
    with engine.connect() as conn:
        assert conn.execute(text("SELECT id FROM manuscript_versions")).scalar_one() == draft.id
