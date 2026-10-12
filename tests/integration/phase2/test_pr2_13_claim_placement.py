"""Disposable PostgreSQL tests for exact Claim/Conclusion manuscript placement."""

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

from researchbase.application.manuscript_placement import ClaimPlacementService
from researchbase.application.publication import PublicationService
from researchbase.application.scientific_conclusion import ClaimInputRequest
from researchbase.foundation.artifact_store import ContentAddressedFilesystemArtifactStore
from researchbase.foundation.errors import ResearchBaseError
from researchbase.persistence.uow import SqlAlchemyUnitOfWork
from tests.integration.phase2.test_pr2_10_binding_contract import _artifact
from tests.integration.phase2.test_pr2_11_r2_persistence import SCOPE
from tests.integration.phase2.test_pr2_11_r2_persistence import (
    conclusion_env as _conclusion_env,
)
from tests.integration.phase2.test_pr2_11_r2_persistence import (
    phase2_database_url as _phase2_database_url,
)

pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)
pytestmark = pytest.mark.integration
conclusion_env = _conclusion_env
phase2_database_url = _phase2_database_url


def _draft(conclusion_env, phase2_database_url, tmp_path):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "head")
    scientific, _, _, principal, _, project, claim_id, _, engine, credentials = (
        conclusion_env
    )
    factory = lambda: SqlAlchemyUnitOfWork(  # noqa: E731
        sessionmaker(engine, expire_on_commit=False, autoflush=False)
    )
    store = ContentAddressedFilesystemArtifactStore(tmp_path / "cas")
    publications = PublicationService(factory, credentials, store)
    document = _artifact(factory, store, principal, project, b"Test-only manuscript", "manuscript")
    publication = publications.create_publication(principal, project, "PAPER", "Study", uuid4())
    draft = publications.create_draft(principal, project, publication.id, document,
                                      "Study", None, "INITIAL", uuid4())
    return (
        scientific, factory, engine, credentials, principal, project,
        claim_id, publication, draft,
    )


def test_exact_claim_and_conclusion_placements_do_not_create_support(
    conclusion_env, phase2_database_url, tmp_path,
):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    (scientific, factory, engine, credentials, principal, project, claim_id,
     publication, draft) = _draft(conclusion_env, phase2_database_url, tmp_path)
    before_relations = None
    with engine.connect() as conn:
        before_relations = conn.execute(text("SELECT count(*) FROM evidence_relations"))\
            .scalar_one()
    conclusion = scientific.create(principal, project, "Test-only conclusion", SCOPE,
                                   "MODERATE", None,
                                   (ClaimInputRequest(claim_id, "SUPPORTS"),), (), uuid4())
    scientific.freeze(principal, project, conclusion.conclusion_id,
                      conclusion.version_id, uuid4())
    placements = ClaimPlacementService(factory, credentials)
    claim = placements.add(principal, project, publication.id, draft.id,
                           claim_id, None, "RESULTS",
                           {"kind": "PARAGRAPH", "value": "p1"},
                           "DESCRIPTIVE", 0, uuid4())
    synthesis = placements.add(principal, project, publication.id, draft.id,
                               None, conclusion.version_id, "DISCUSSION",
                               {"kind": "PARAGRAPH", "value": "p2"},
                               "SUGGESTIVE", 0, uuid4())
    assert claim.target_kind == "CLAIM_VERSION"
    assert synthesis.target_kind == "SCIENTIFIC_CONCLUSION_VERSION"
    assert claim.path_kind == synthesis.path_kind == "PLACEMENT_ONLY"
    assert ClaimPlacementService(factory, credentials).trace(
        principal, project, publication.id, draft.id
    ) == (synthesis, claim)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM evidence_relations"))\
            .scalar_one() == before_relations
        assert conn.execute(text("SELECT count(*) FROM literature_evidence_review_events"))\
            .scalar_one() == 0
        assert conn.execute(text("SELECT placement_set_hash FROM manuscript_versions WHERE id=:id"),
                            {"id": draft.id}).scalar_one() is None
    with pytest.raises(DBAPIError):
        command.downgrade(config, "0036_pr2_13_citation_placement")


def test_claim_placement_fail_closed_and_concurrent_replay(
    conclusion_env, phase2_database_url, tmp_path,
):
    (scientific, factory, engine, credentials, principal, project, claim_id,
     publication, draft) = _draft(conclusion_env, phase2_database_url, tmp_path)
    placements = ClaimPlacementService(factory, credentials)
    args = (principal, project, publication.id, draft.id, claim_id, None,
            "RESULTS", {"kind": "PARAGRAPH", "value": "p1"}, "DESCRIPTIVE", 0)
    key = uuid4()
    placed = placements.add(*args, key)
    assert placements.add(*args, key) == placed
    with engine.connect() as conn:
        document = conn.execute(text("""SELECT document_artifact_version_id
          FROM manuscript_versions WHERE id=:id"""), {"id": draft.id}).scalar_one()
    publications = PublicationService(
        factory, credentials, ContentAddressedFilesystemArtifactStore(tmp_path / "cas")
    )
    other_publication = publications.create_publication(
        principal, project, "PAPER", "Other test-only manuscript", uuid4()
    )
    other_draft = publications.create_draft(
        principal, project, other_publication.id, document,
        "Other test-only manuscript", None, "INITIAL", uuid4()
    )
    with pytest.raises(DBAPIError) as exc:
        with engine.begin() as conn:
            conn.execute(text("""UPDATE manuscript_claim_placements
              SET manuscript_version_id=:other WHERE id=:id"""),
              {"other": other_draft.id, "id": placed.id})
    assert getattr(exc.value.orig, "sqlstate", None) == "P17D3"
    with pytest.raises(ResearchBaseError):
        placements.add(*args[:7], {"kind": "PARAGRAPH", "value": "p2"},
                       *args[8:], key)
    with pytest.raises(ResearchBaseError):
        placements.add(replace(principal, actor_id=uuid4()), *args[1:], uuid4())
    with pytest.raises(ResearchBaseError):
        placements.add(*args[:4], None, None, *args[6:], uuid4())
    with pytest.raises(ResearchBaseError):
        placements.add(*args[:4], claim_id, uuid4(), *args[6:], uuid4())
    with pytest.raises(ResearchBaseError):
        placements.add(*args[:4], uuid4(), None, *args[6:], uuid4())
    draft_conclusion = scientific.create(principal, project, "Draft only", SCOPE,
                                         "MODERATE", None, (), (), uuid4())
    with pytest.raises(ResearchBaseError):
        placements.add(*args[:4], None, draft_conclusion.version_id,
                       *args[6:], uuid4())
    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            conn.execute(text("""INSERT INTO manuscript_claim_placements
              (id,manuscript_version_id,claim_version_id,scientific_conclusion_version_id,
               section_id,locator,rhetorical_strength,ordinal,created_by,created_at,row_version)
              VALUES (:id,:manuscript,:claim,:conclusion,'DISCUSSION',
                      '{"kind":"PARAGRAPH","value":"p2"}'::jsonb,
                      'DESCRIPTIVE',0,:actor,now(),1)"""),
              {"id": uuid4(), "manuscript": draft.id, "claim": claim_id,
               "conclusion": draft_conclusion.version_id, "actor": principal.actor_id})
    with pytest.raises(DBAPIError) as exc:
        with engine.begin() as conn:
            conn.execute(text("""INSERT INTO manuscript_claim_placements
              (id,manuscript_version_id,claim_version_id,section_id,locator,
               rhetorical_strength,ordinal,created_by,created_at,row_version)
              VALUES (:id,:manuscript,:claim,'DISCUSSION',
                      '{"kind":"PARAGRAPH","value":"p2"}'::jsonb,
                      'DESCRIPTIVE',0,:actor,now(),1)"""),
              {"id": uuid4(), "manuscript": draft.id,
               "claim": uuid4(), "actor": principal.actor_id})
    assert getattr(exc.value.orig, "sqlstate", None) == "P17D3"
    foreign_project, foreign_claim, foreign_version = uuid4(), uuid4(), uuid4()
    with engine.begin() as conn:
        conn.execute(text("""INSERT INTO projects(id,name,created_by,created_at)
          VALUES (:id,'Test-only foreign claim project',:actor,now())"""),
          {"id": foreign_project, "actor": principal.actor_id})
        conn.execute(text("""INSERT INTO claims(id,project_id,created_by,created_at)
          VALUES (:id,:project,:actor,now())"""),
          {"id": foreign_claim, "project": foreign_project, "actor": principal.actor_id})
        conn.execute(text("""INSERT INTO claim_versions
          (id,claim_id,version_number,status,statement,created_by,created_at)
          VALUES (:id,:claim,1,'DRAFT','Test-only foreign claim',:actor,now())"""),
          {"id": foreign_version, "claim": foreign_claim, "actor": principal.actor_id})
        conn.execute(text("""UPDATE claims SET current_version_id=:version
          WHERE id=:claim"""), {"version": foreign_version, "claim": foreign_claim})
        conn.execute(text("""UPDATE claim_versions SET status='FROZEN',
          content_hash=:digest,support_set_hash=:digest,frozen_at=now(),
          row_version=row_version+1
          WHERE id=:id"""), {"id": foreign_version, "digest": "a" * 64})
    with pytest.raises(DBAPIError) as exc:
        with engine.begin() as conn:
            conn.execute(text("""INSERT INTO manuscript_claim_placements
              (id,manuscript_version_id,claim_version_id,section_id,locator,
               rhetorical_strength,ordinal,created_by,created_at,row_version)
              VALUES (:id,:manuscript,:claim,'DISCUSSION',
                      '{"kind":"PARAGRAPH","value":"p3"}'::jsonb,
                      'DESCRIPTIVE',1,:actor,now(),1)"""),
              {"id": uuid4(), "manuscript": draft.id,
               "claim": foreign_version, "actor": principal.actor_id})
    assert getattr(exc.value.orig, "sqlstate", None) == "P17D3"
    concurrent_key = uuid4()
    def same_request():
        return placements.add(*args[:6], "METHOD",
                              {"kind": "ANCHOR", "value": "a1"},
                              "SUGGESTIVE", 0, concurrent_key)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(same_request) for _ in range(2)]
        assert futures[0].result() == futures[1].result()
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM manuscript_claim_placements"))\
            .scalar_one() == 2


def test_claim_placement_migration_catalog_and_empty_downgrade(phase2_database_url):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "0036_pr2_13_citation_placement")
    engine = create_engine(phase2_database_url)
    with engine.connect() as conn:
        baseline = set(conn.execute(text("""SELECT tablename,indexname,indexdef
          FROM pg_indexes WHERE schemaname='public'""")).all())
    engine.dispose()
    command.upgrade(config, "head")
    engine = create_engine(phase2_database_url)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0037_pr2_13_claim_placement"
        )
        indexes = conn.execute(text("""SELECT indexdef FROM pg_indexes WHERE
          schemaname='public' AND tablename='manuscript_claim_placements'""")).scalars().all()
        for column in ("claim_version_id", "scientific_conclusion_version_id", "created_by"):
            assert sum(f"USING btree ({column})" in definition for definition in indexes) == 1
        assert sum("USING btree (manuscript_version_id, section_id, ordinal)" in definition
                   for definition in indexes) == 1
        assert conn.execute(text("""SELECT count(*) FROM pg_constraint
          WHERE conrelid='manuscript_claim_placements'::regclass AND contype='f'"""))\
            .scalar_one() == 4
    engine.dispose()
    command.downgrade(config, "0036_pr2_13_citation_placement")
    engine = create_engine(phase2_database_url)
    with engine.connect() as conn:
        assert set(conn.execute(text("""SELECT tablename,indexname,indexdef FROM pg_indexes
          WHERE schemaname='public'""")).all()) == baseline
        assert conn.execute(text("SELECT to_regclass('manuscript_claim_placements')"))\
            .scalar_one() is None
    engine.dispose()
