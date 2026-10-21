"""Disposable PostgreSQL contract test for citation-only manuscript placement."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
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


def test_citation_placement_persists_as_citation_only(
    discussion_env,
    discussion_database_url,
    tmp_path,
):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", discussion_database_url)
    command.upgrade(config, "0075_m1_reconsideration")
    _, engine, credentials, principal, project, _, source_version = discussion_env
    factory = lambda: SqlAlchemyUnitOfWork(  # noqa: E731
        sessionmaker(engine, expire_on_commit=False, autoflush=False)
    )
    store = ContentAddressedFilesystemArtifactStore(tmp_path / "cas")
    publications = PublicationService(factory, credentials, store)
    document = _artifact(factory, store, principal, project, b"Test-only draft", "manuscript")
    publication = publications.create_publication(principal, project, "PAPER", "Study", uuid4())
    draft = publications.create_draft(
        principal, project, publication.id, document, "Study", None, "INITIAL", uuid4()
    )
    placements = CitationPlacementService(factory, credentials)
    key = uuid4()
    placed = placements.add(
        principal,
        project,
        publication.id,
        draft.id,
        source_version,
        "INTRO",
        {"kind": "PARAGRAPH", "value": "p1"},
        "BACKGROUND",
        0,
        key,
    )
    assert (
        placements.add(
            principal,
            project,
            publication.id,
            draft.id,
            source_version,
            "INTRO",
            {"kind": "PARAGRAPH", "value": "p1"},
            "BACKGROUND",
            0,
            key,
        )
        == placed
    )
    trace = CitationPlacementService(factory, credentials).trace(
        principal, project, publication.id, draft.id
    )
    assert trace == (placed,)
    assert placed.source_version_id == source_version
    with engine.connect() as conn:
        assert (
            placed.source_content_hash
            == conn.execute(
                text("SELECT content_hash FROM source_versions WHERE id=:id"),
                {"id": source_version},
            ).scalar_one()
        )
    assert placed.path_kind == "CITATION_ONLY"
    with engine.connect() as conn:
        assert (
            conn.execute(text("SELECT count(*) FROM manuscript_citation_placements")).scalar_one()
            == 1
        )
        assert conn.execute(text("SELECT count(*) FROM literature_evidence")).scalar_one() == 0
        assert (
            conn.execute(
                text("SELECT placement_set_hash FROM manuscript_versions WHERE id=:id"),
                {"id": draft.id},
            ).scalar_one()
            is None
        )
    with pytest.raises(DBAPIError):
        command.downgrade(config, "0035_pr2_12_publication_draft")


def test_citation_rejects_tampering_and_bad_authority(
    discussion_env,
    discussion_database_url,
    tmp_path,
):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", discussion_database_url)
    command.upgrade(config, "head")
    _, engine, credentials, principal, project, _, source_version = discussion_env
    factory = lambda: SqlAlchemyUnitOfWork(  # noqa: E731
        sessionmaker(engine, expire_on_commit=False, autoflush=False)
    )
    store = ContentAddressedFilesystemArtifactStore(tmp_path / "cas")
    publications = PublicationService(factory, credentials, store)
    document = _artifact(factory, store, principal, project, b"Test-only draft", "manuscript")
    publication = publications.create_publication(principal, project, "PAPER", "Study", uuid4())
    draft = publications.create_draft(
        principal, project, publication.id, document, "Study", None, "INITIAL", uuid4()
    )
    placements = CitationPlacementService(factory, credentials)
    args = (
        principal,
        project,
        publication.id,
        draft.id,
        source_version,
        "INTRO",
        {"kind": "PARAGRAPH", "value": "p1"},
        "BACKGROUND",
        0,
    )
    key = uuid4()
    placed = placements.add(*args, key)
    with pytest.raises(ResearchBaseError):
        placements.add(*args[:6], {"kind": "PAGE", "value": "p1"}, *args[7:], uuid4())
    with pytest.raises(ResearchBaseError):
        placements.add(*args[:5], "S" * 2001, *args[6:], uuid4())
    with pytest.raises(ResearchBaseError):
        placements.add(*args[:6], {"kind": "PARAGRAPH", "value": "p" * 2001}, *args[7:], uuid4())
    with pytest.raises(ResearchBaseError):
        placements.add(*args[:6], {"kind": "PARAGRAPH", "value": "p2"}, *args[7:], key)
    with pytest.raises(ResearchBaseError):
        placements.add(replace(principal, actor_id=uuid4()), *args[1:], uuid4())
    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            conn.execute(
                text("""INSERT INTO manuscript_citation_placements
              (id,manuscript_version_id,source_version_id,section_id,locator,
               citation_purpose,ordinal,created_by,created_at,row_version)
              VALUES (:id,:manuscript,:source,'INTRO',CAST(:locator AS jsonb),
                      'BACKGROUND',1,:actor,now(),1)"""),
                {
                    "id": uuid4(),
                    "manuscript": draft.id,
                    "source": source_version,
                    "locator": '{"kind":"PARAGRAPH","value":"p2","extra":1}',
                    "actor": principal.actor_id,
                },
            )
    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            conn.execute(
                text("""INSERT INTO manuscript_citation_placements
              (id,manuscript_version_id,source_version_id,section_id,locator,
               citation_purpose,ordinal,created_by,created_at,row_version)
              VALUES (:id,:manuscript,:source,'INTRO',CAST(:locator AS jsonb),
                      'BACKGROUND',0,:actor,now(),1)"""),
                {
                    "id": uuid4(),
                    "manuscript": draft.id,
                    "source": source_version,
                    "locator": '{"kind":"PARAGRAPH","value":"p1"}',
                    "actor": principal.actor_id,
                },
            )
    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            conn.execute(
                text("""INSERT INTO manuscript_citation_placements
              (id,manuscript_version_id,source_version_id,section_id,locator,
               citation_purpose,ordinal,created_by,created_at,row_version)
              VALUES (:id,:manuscript,:source,:section,CAST(:locator AS jsonb),
                      'BACKGROUND',1,:actor,now(),1)"""),
                {
                    "id": uuid4(),
                    "manuscript": draft.id,
                    "source": source_version,
                    "section": "S" * 2001,
                    "locator": '{"kind":"PARAGRAPH","value":"p1"}',
                    "actor": principal.actor_id,
                },
            )
    draft_source = uuid4()
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
    with pytest.raises(DBAPIError) as exc:
        with engine.begin() as conn:
            conn.execute(
                text("""INSERT INTO manuscript_citation_placements
              (id,manuscript_version_id,source_version_id,section_id,locator,
               citation_purpose,ordinal,created_by,created_at,row_version)
              VALUES (:id,:manuscript,:source,'INTRO',CAST(:locator AS jsonb),
                      'BACKGROUND',1,:actor,now(),1)"""),
                {
                    "id": uuid4(),
                    "manuscript": draft.id,
                    "source": draft_source,
                    "locator": '{"kind":"PARAGRAPH","value":"p2"}',
                    "actor": principal.actor_id,
                },
            )
    assert getattr(exc.value.orig, "sqlstate", None) == "P17D3"
    unlinked_source, unlinked_version = uuid4(), uuid4()
    with engine.begin() as conn:
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
    with pytest.raises(DBAPIError) as exc:
        with engine.begin() as conn:
            conn.execute(
                text("""INSERT INTO manuscript_citation_placements
              (id,manuscript_version_id,source_version_id,section_id,locator,
               citation_purpose,ordinal,created_by,created_at,row_version)
              VALUES (:id,:manuscript,:source,'INTRO',CAST(:locator AS jsonb),
                      'BACKGROUND',1,:actor,now(),1)"""),
                {
                    "id": uuid4(),
                    "manuscript": draft.id,
                    "source": unlinked_version,
                    "locator": '{"kind":"PARAGRAPH","value":"p2"}',
                    "actor": principal.actor_id,
                },
            )
    assert getattr(exc.value.orig, "sqlstate", None) == "P17D3"
    with engine.connect() as conn:
        assert (
            conn.execute(text("SELECT count(*) FROM manuscript_citation_placements")).scalar_one()
            == 1
        )
    assert placements.trace(principal, project, publication.id, draft.id) == (placed,)
    concurrent_key = uuid4()

    def add_same_request():
        return placements.add(
            principal,
            project,
            publication.id,
            draft.id,
            source_version,
            "METHOD",
            {"kind": "ANCHOR", "value": "a1"},
            "METHOD",
            0,
            concurrent_key,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(add_same_request) for _ in range(2)]
        assert futures[0].result() == futures[1].result()
    with engine.connect() as conn:
        assert (
            conn.execute(text("SELECT count(*) FROM manuscript_citation_placements")).scalar_one()
            == 2
        )


def test_citation_migration_catalog_and_empty_downgrade(discussion_database_url):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", discussion_database_url)
    command.upgrade(config, "0035_pr2_12_publication_draft")
    engine = create_engine(discussion_database_url)
    with engine.connect() as conn:
        baseline = set(
            conn.execute(
                text("""SELECT tablename,indexname,indexdef
          FROM pg_indexes WHERE schemaname='public'""")
            ).all()
        )
    command.upgrade(config, "0036_pr2_13_citation_placement")
    with engine.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0036_pr2_13_citation_placement"
        )
        indexes = conn.execute(
            text("""SELECT indexname,indexdef FROM pg_indexes
          WHERE schemaname='public' AND tablename='manuscript_citation_placements'""")
        ).all()
        definitions = [row[1] for row in indexes]
        assert sum("USING btree (source_version_id)" in d for d in definitions) == 1
        assert sum("USING btree (created_by)" in d for d in definitions) == 1
        assert (
            sum(
                "USING btree (manuscript_version_id, section_id, ordinal)" in d for d in definitions
            )
            == 1
        )
        assert (
            conn.execute(
                text("""SELECT count(*) FROM pg_constraint
          WHERE conrelid='manuscript_citation_placements'::regclass AND contype='f'""")
            ).scalar_one()
            == 3
        )
    engine.dispose()
    command.downgrade(config, "0035_pr2_12_publication_draft")
    engine = create_engine(discussion_database_url)
    with engine.connect() as conn:
        assert (
            set(
                conn.execute(
                    text("""SELECT tablename,indexname,indexdef
          FROM pg_indexes WHERE schemaname='public'""")
                ).all()
            )
            == baseline
        )
        assert (
            conn.execute(text("SELECT to_regclass('manuscript_citation_placements')")).scalar_one()
            is None
        )
    engine.dispose()
