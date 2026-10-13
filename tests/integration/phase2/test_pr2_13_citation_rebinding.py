"""Disposable PostgreSQL checks for citation placement identity binding."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker

from researchbase.application.manuscript_placement import CitationPlacementService
from researchbase.application.publication import PublicationService
from researchbase.foundation.artifact_store import ContentAddressedFilesystemArtifactStore
from researchbase.persistence.uow import SqlAlchemyUnitOfWork
from tests.integration.phase2.test_pr2_10_binding_contract import _artifact
from tests.integration.phase2.test_pr2_13_citation_placement import (
    discussion_database_url as _discussion_database_url,
)
from tests.integration.phase2.test_pr2_13_citation_placement import (
    discussion_env as _discussion_env,
)

pytestmark = pytest.mark.integration
discussion_database_url = _discussion_database_url
discussion_env = _discussion_env


def _two_drafts(discussion_env, discussion_database_url, tmp_path, revision="head"):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", discussion_database_url)
    command.upgrade(config, revision)
    _, engine, credentials, principal, project, _, source_version = discussion_env
    factory = lambda: SqlAlchemyUnitOfWork(  # noqa: E731
        sessionmaker(engine, expire_on_commit=False, autoflush=False)
    )
    store = ContentAddressedFilesystemArtifactStore(tmp_path / "cas")
    publications = PublicationService(factory, credentials, store)
    document = _artifact(factory, store, principal, project, b"Test-only draft", "manuscript")
    manuscripts = []
    for label in ("First", "Second"):
        publication = publications.create_publication(principal, project, "PAPER", label, uuid4())
        draft = publications.create_draft(
            principal, project, publication.id, document, label, None, "INITIAL", uuid4()
        )
        manuscripts.append((publication, draft))
    placements = CitationPlacementService(factory, credentials)
    first, second = manuscripts
    placed = placements.add(
        principal,
        project,
        first[0].id,
        first[1].id,
        source_version,
        "INTRO",
        {"kind": "PARAGRAPH", "value": "p1"},
        "BACKGROUND",
        0,
        uuid4(),
    )
    return engine, config, principal, project, source_version, placements, first, second, placed


def test_citation_parent_cannot_be_rebound_by_direct_sql(
    discussion_env,
    discussion_database_url,
    tmp_path,
):
    (engine, _, principal, project, source_version, placements, first, second, placed) = (
        _two_drafts(discussion_env, discussion_database_url, tmp_path)
    )
    with pytest.raises(DBAPIError) as exc:
        with engine.begin() as conn:
            conn.execute(
                text("""UPDATE manuscript_citation_placements
              SET manuscript_version_id=:new_parent,section_id='METHOD',ordinal=1,
                  source_version_id=:source,citation_purpose='METHOD'
              WHERE id=:id"""),
                {"new_parent": second[1].id, "source": source_version, "id": placed.id},
            )
    assert getattr(exc.value.orig, "sqlstate", None) == "P17D3"
    assert placements.trace(principal, project, first[0].id, first[1].id) == (placed,)
    assert placements.trace(principal, project, second[0].id, second[1].id) == ()
    with ThreadPoolExecutor(max_workers=2) as pool:

        def rebind():
            with engine.begin() as conn:
                conn.execute(
                    text("""UPDATE manuscript_citation_placements
                  SET manuscript_version_id=:parent WHERE id=:id"""),
                    {"parent": second[1].id, "id": placed.id},
                )

        futures = [pool.submit(rebind) for _ in range(2)]
        for future in futures:
            with pytest.raises(DBAPIError) as concurrent_error:
                future.result()
            assert getattr(concurrent_error.value.orig, "sqlstate", None) == "P17D3"


def test_draft_edits_remain_allowed_but_invalid_targets_fail(
    discussion_env,
    discussion_database_url,
    tmp_path,
):
    (engine, _, principal, project, source_version, placements, first, _, placed) = _two_drafts(
        discussion_env, discussion_database_url, tmp_path
    )
    with engine.begin() as conn:
        conn.execute(
            text("""UPDATE manuscript_citation_placements
          SET section_id='METHOD',locator='{"kind":"ANCHOR","value":"a1"}'::jsonb,
              citation_purpose='METHOD',ordinal=1,row_version=2 WHERE id=:id"""),
            {"id": placed.id},
        )
    assert placements.trace(principal, project, first[0].id, first[1].id)[0].section_id == (
        "METHOD"
    )
    draft_source = uuid4()
    unlinked_source, unlinked_version = uuid4(), uuid4()
    with engine.begin() as conn:
        parent_source = conn.execute(
            text("""SELECT literature_source_id
          FROM source_versions WHERE id=:id"""),
            {"id": source_version},
        ).scalar_one()
        conn.execute(
            text("""INSERT INTO source_versions
          (id,literature_source_id,version_number,version_kind,title,authors,
           status,hash_scheme,created_by,created_at)
          VALUES (:id,:parent,2,'PUBLISHED','Test-only draft source','[]'::jsonb,
                  'DRAFT','sha256-cjson-v1',:actor,now())"""),
            {"id": draft_source, "parent": parent_source, "actor": principal.actor_id},
        )
        conn.execute(
            text("""INSERT INTO literature_sources
          (id,source_kind,canonical_title,lifecycle_status,created_by,created_at)
          VALUES (:id,'PAPER','Test-only unlinked source','ACTIVE',:actor,now())"""),
            {"id": unlinked_source, "actor": principal.actor_id},
        )
        conn.execute(
            text("""INSERT INTO source_versions
          (id,literature_source_id,version_number,version_kind,title,authors,
           status,hash_scheme,created_by,created_at)
          VALUES (:id,:parent,1,'PUBLISHED','Test-only unlinked source','[]'::jsonb,
                  'DRAFT','sha256-cjson-v1',:actor,now())"""),
            {"id": unlinked_version, "parent": unlinked_source, "actor": principal.actor_id},
        )
        conn.execute(
            text("""UPDATE source_versions SET status='FROZEN',
          content_hash=:digest,frozen_at=now() WHERE id=:id"""),
            {"id": unlinked_version, "digest": "a" * 64},
        )
    for invalid in (draft_source, unlinked_version):
        with pytest.raises(DBAPIError) as exc:
            with engine.begin() as conn:
                conn.execute(
                    text("""UPDATE manuscript_citation_placements
                  SET source_version_id=:source,section_id='RESULTS' WHERE id=:id"""),
                    {"source": invalid, "id": placed.id},
                )
        assert getattr(exc.value.orig, "sqlstate", None) == "P17D3"
    with engine.begin() as conn:
        conn.execute(
            text("""UPDATE source_versions SET status='FROZEN',
          content_hash=:digest,frozen_at=now() WHERE id=:id"""),
            {"id": draft_source, "digest": "b" * 64},
        )
        conn.execute(
            text("""UPDATE manuscript_citation_placements
          SET source_version_id=:source,row_version=3 WHERE id=:id"""),
            {"source": draft_source, "id": placed.id},
        )
    changed = placements.trace(principal, project, first[0].id, first[1].id)[0]
    assert changed.source_version_id == draft_source
    assert changed.source_content_hash == "b" * 64
    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE source_versions SET status='DRAFT' WHERE id=:id"),
                {"id": source_version},
            )
    rolled_back = uuid4()
    with pytest.raises(RuntimeError):
        with engine.begin() as conn:
            conn.execute(
                text("""INSERT INTO manuscript_citation_placements
              (id,manuscript_version_id,source_version_id,section_id,locator,
               citation_purpose,ordinal,created_by,created_at,row_version)
              VALUES (:id,:manuscript,:source,'METHOD',
                      '{"kind":"ANCHOR","value":"temporary"}'::jsonb,
                      'METHOD',2,:actor,now(),1)"""),
                {
                    "id": rolled_back,
                    "manuscript": first[1].id,
                    "source": source_version,
                    "actor": principal.actor_id,
                },
            )
            raise RuntimeError("force test transaction rollback")
    engine.dispose()
    with engine.connect() as conn:
        assert (
            conn.execute(
                text("""SELECT count(*) FROM manuscript_citation_placements
          WHERE id=:id"""),
                {"id": rolled_back},
            ).scalar_one()
            == 0
        )
    assert len(placements.trace(principal, project, first[0].id, first[1].id)) == 1


def test_forward_guard_preserves_rows_and_downgrade_refuses_history(
    discussion_env,
    discussion_database_url,
    tmp_path,
):
    (engine, config, principal, project, _, placements, first, _, placed) = _two_drafts(
        discussion_env,
        discussion_database_url,
        tmp_path,
        revision="0038_pr2_13_artifact_placement",
    )
    with engine.connect() as conn:
        original = (
            conn.execute(
                text("""SELECT * FROM manuscript_citation_placements
          WHERE id=:id"""),
                {"id": placed.id},
            )
            .mappings()
            .one()
        )
    command.upgrade(config, "head")
    with engine.connect() as conn:
        assert (
            conn.execute(
                text("""SELECT * FROM manuscript_citation_placements
          WHERE id=:id"""),
                {"id": placed.id},
            )
            .mappings()
            .one()
            == original
        )
    assert placements.trace(principal, project, first[0].id, first[1].id) == (placed,)
    with pytest.raises(DBAPIError):
        command.downgrade(config, "0038_pr2_13_artifact_placement")


def test_empty_upgrade_downgrade_catalog_is_exact(discussion_database_url):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", discussion_database_url)
    command.upgrade(config, "0038_pr2_13_artifact_placement")
    engine = create_engine(discussion_database_url)
    with engine.connect() as conn:
        tables = set(
            conn.execute(
                text("""SELECT tablename FROM pg_tables
          WHERE schemaname='public'""")
            ).scalars()
        )
        columns = set(
            conn.execute(
                text("""SELECT table_name,column_name
          FROM information_schema.columns WHERE table_schema='public'""")
            ).all()
        )
        triggers = set(
            conn.execute(
                text("""SELECT tgname FROM pg_trigger
          WHERE tgrelid='manuscript_citation_placements'::regclass
            AND NOT tgisinternal""")
            ).scalars()
        )
    # This catalog comparison isolates the 0038 -> 0039 citation guard delta.
    command.upgrade(config, "0039_pr2_13_citation_rebinding_guard")
    with engine.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0039_pr2_13_citation_rebinding_guard"
        )
        assert (
            "OLD.manuscript_version_id IS DISTINCT FROM"
            in conn.execute(
                text("""
          SELECT prosrc FROM pg_proc WHERE proname='pr213_citation_guard'""")
            ).scalar_one()
        )
        assert (
            set(
                conn.execute(
                    text("""SELECT tablename FROM pg_tables
          WHERE schemaname='public'""")
                ).scalars()
            )
            == tables
        )
        assert (
            set(
                conn.execute(
                    text("""SELECT table_name,column_name
          FROM information_schema.columns WHERE table_schema='public'""")
                ).all()
            )
            == columns
        )
        assert (
            set(
                conn.execute(
                    text("""SELECT tgname FROM pg_trigger
          WHERE tgrelid='manuscript_citation_placements'::regclass
            AND NOT tgisinternal""")
                ).scalars()
            )
            == triggers
        )
    engine.dispose()
    command.downgrade(config, "0038_pr2_13_artifact_placement")
    engine = create_engine(discussion_database_url)
    with engine.connect() as conn:
        assert (
            "OLD.manuscript_version_id IS DISTINCT FROM"
            not in conn.execute(
                text("""
          SELECT prosrc FROM pg_proc WHERE proname='pr213_citation_guard'""")
            ).scalar_one()
        )
    engine.dispose()
