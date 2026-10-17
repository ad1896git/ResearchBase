"""Disposable PostgreSQL contract tests for exact ArtifactVersion placements."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from researchbase.application.manuscript_placement import ArtifactPlacementService
from researchbase.application.publication import PublicationService
from researchbase.foundation.artifact_store import ContentAddressedFilesystemArtifactStore
from researchbase.foundation.errors import ResearchBaseError
from tests.integration.phase2.test_pr2_10_binding_contract import _artifact
from tests.integration.phase2.test_pr2_13_claim_placement import _draft
from tests.integration.phase2.test_pr2_13_claim_placement import (
    conclusion_env as _conclusion_env,
)
from tests.integration.phase2.test_pr2_13_claim_placement import (
    phase2_database_url as _phase2_database_url,
)

pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)
pytestmark = pytest.mark.integration
conclusion_env = _conclusion_env
phase2_database_url = _phase2_database_url


def test_artifact_exact_readback_and_no_promotion(
    conclusion_env,
    phase2_database_url,
    tmp_path,
):
    _, factory, engine, credentials, principal, project, _, publication, draft = _draft(
        conclusion_env, phase2_database_url, tmp_path
    )
    store = ContentAddressedFilesystemArtifactStore(tmp_path / "cas")
    figure = _artifact(factory, store, principal, project, b"Test-only figure", "figure")
    with engine.connect() as conn:
        before_relations = conn.execute(
            text("SELECT count(*) FROM evidence_relations")
        ).scalar_one()
    service = ArtifactPlacementService(factory, credentials)
    args = (
        principal,
        project,
        publication.id,
        draft.id,
        figure,
        "RESULTS",
        {"kind": "CAPTION", "value": "Figure 1"},
        "FIGURE",
        0,
    )
    placed = service.add(*args, uuid4())
    assert placed.path_kind == "PLACEMENT_ONLY"
    assert placed.artifact_version_id == figure
    assert service.trace(principal, project, publication.id, draft.id) == (placed,)
    engine.dispose()
    assert ArtifactPlacementService(factory, credentials).trace(
        principal, project, publication.id, draft.id
    ) == (placed,)
    with engine.connect() as conn:
        assert (
            conn.execute(
                text("SELECT placement_set_hash FROM manuscript_versions WHERE id=:id"),
                {"id": draft.id},
            ).scalar_one()
            is None
        )
        assert (
            conn.execute(text("SELECT count(*) FROM evidence_relations")).scalar_one()
            == before_relations
        )
    with ThreadPoolExecutor(max_workers=2) as pool:
        key = uuid4()
        futures = [
            pool.submit(
                service.add, *args[:5], "METHOD", {"kind": "ANCHOR", "value": "a1"}, "OTHER", 0, key
            )
            for _ in range(2)
        ]
        assert futures[0].result() == futures[1].result()
    assert len(service.trace(principal, project, publication.id, draft.id)) == 2


def test_artifact_fail_closed_direct_sql_and_reparent(
    conclusion_env,
    phase2_database_url,
    tmp_path,
):
    _, factory, engine, credentials, principal, project, _, publication, draft = _draft(
        conclusion_env, phase2_database_url, tmp_path
    )
    store = ContentAddressedFilesystemArtifactStore(tmp_path / "cas")
    artifact = _artifact(factory, store, principal, project, b"Test-only chart", "figure")
    service = ArtifactPlacementService(factory, credentials)
    args = (
        principal,
        project,
        publication.id,
        draft.id,
        artifact,
        "RESULTS",
        {"kind": "CAPTION", "value": "Chart"},
        "FIGURE",
        0,
    )
    placed = service.add(*args, uuid4())
    with pytest.raises(ResearchBaseError):
        service.add(replace(principal, actor_id=uuid4()), *args[1:], uuid4())
    with pytest.raises(ResearchBaseError):
        service.add(*args[:7], "WRONG", 0, uuid4())
    with pytest.raises(ResearchBaseError):
        service.add(*args[:4], uuid4(), *args[5:], uuid4())
    foreign_project, foreign_artifact, foreign_version = uuid4(), uuid4(), uuid4()
    draft_artifact, draft_version = uuid4(), uuid4()
    with engine.begin() as conn:
        conn.execute(
            text("""INSERT INTO projects(id,name,created_by,created_at)
          VALUES (:id,'Test-only foreign artifact project',:actor,now())"""),
            {"id": foreign_project, "actor": principal.actor_id},
        )
        for identity, owning_project in (
            (foreign_artifact, foreign_project),
            (draft_artifact, project),
        ):
            conn.execute(
                text("""INSERT INTO artifacts
              (id,project_id,artifact_type,name,created_by,created_at,row_version)
              VALUES (:id,:project,'figure','Test-only artifact',:actor,now(),1)"""),
                {"id": identity, "project": owning_project, "actor": principal.actor_id},
            )
        for version_id, parent, status, frozen in (
            (foreign_version, foreign_artifact, "FROZEN", True),
            (draft_version, draft_artifact, "DRAFT", False),
        ):
            conn.execute(
                text("""INSERT INTO artifact_versions
              (id,artifact_id,version_number,status,content_hash,created_by,
               created_at,frozen_at,row_version)
              VALUES (:id,:parent,1,:status,:digest,:actor,now(),
                      CASE WHEN :frozen THEN now() ELSE NULL END,1)"""),
                {
                    "id": version_id,
                    "parent": parent,
                    "status": status,
                    "digest": "a" * 64 if frozen else "b" * 64,
                    "actor": principal.actor_id,
                    "frozen": frozen,
                },
            )
    for invalid in (foreign_version, draft_version):
        with pytest.raises(ResearchBaseError):
            service.add(*args[:4], invalid, *args[5:], uuid4())
        with pytest.raises(DBAPIError) as exc:
            with engine.begin() as conn:
                conn.execute(
                    text("""INSERT INTO manuscript_artifact_placements
                  (id,manuscript_version_id,artifact_version_id,section_id,locator,
                   artifact_role,ordinal,created_by,created_at,row_version)
                  VALUES (:id,:manuscript,:artifact,'METHOD',
                          '{"kind":"CAPTION","value":"x"}'::jsonb,
                          'TABLE',1,:actor,now(),1)"""),
                    {
                        "id": uuid4(),
                        "manuscript": draft.id,
                        "artifact": invalid,
                        "actor": principal.actor_id,
                    },
                )
        assert getattr(exc.value.orig, "sqlstate", None) == "P17D3"
    with engine.connect() as conn:
        document = conn.execute(
            text("""SELECT document_artifact_version_id
          FROM manuscript_versions WHERE id=:id"""),
            {"id": draft.id},
        ).scalar_one()
    publications = PublicationService(factory, credentials, store)
    other_publication = publications.create_publication(
        principal, project, "PAPER", "Other test-only draft", uuid4()
    )
    other_draft = publications.create_draft(
        principal,
        project,
        other_publication.id,
        document,
        "Other test-only draft",
        None,
        "INITIAL",
        uuid4(),
    )
    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            conn.execute(
                text("""UPDATE manuscript_artifact_placements
              SET manuscript_version_id=:other WHERE id=:id"""),
                {"other": other_draft.id, "id": placed.id},
            )
    for target in (uuid4(),):
        with pytest.raises(DBAPIError):
            with engine.begin() as conn:
                conn.execute(
                    text("""INSERT INTO manuscript_artifact_placements
                  (id,manuscript_version_id,artifact_version_id,section_id,locator,
                   artifact_role,ordinal,created_by,created_at,row_version)
                  VALUES (:id,:manuscript,:artifact,'METHOD',
                          '{"kind":"CAPTION","value":"x"}'::jsonb,
                          'TABLE',1,:actor,now(),1)"""),
                    {
                        "id": uuid4(),
                        "manuscript": draft.id,
                        "artifact": target,
                        "actor": principal.actor_id,
                    },
                )
    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            conn.execute(
                text("""INSERT INTO manuscript_artifact_placements
              (id,manuscript_version_id,artifact_version_id,section_id,locator,
               artifact_role,ordinal,created_by,created_at,row_version)
              VALUES (:id,:manuscript,:artifact,'RESULTS',
                      '{"kind":"CAPTION","value":"duplicate"}'::jsonb,
                      'FIGURE',0,:actor,now(),1)"""),
                {
                    "id": uuid4(),
                    "manuscript": draft.id,
                    "artifact": artifact,
                    "actor": principal.actor_id,
                },
            )
    rolled_back = uuid4()
    with pytest.raises(RuntimeError):
        with engine.begin() as conn:
            conn.execute(
                text("""INSERT INTO manuscript_artifact_placements
              (id,manuscript_version_id,artifact_version_id,section_id,locator,
               artifact_role,ordinal,created_by,created_at,row_version)
              VALUES (:id,:manuscript,:artifact,'METHOD',
                      '{"kind":"CAPTION","value":"temporary"}'::jsonb,
                      'OTHER',2,:actor,now(),1)"""),
                {
                    "id": rolled_back,
                    "manuscript": draft.id,
                    "artifact": artifact,
                    "actor": principal.actor_id,
                },
            )
            raise RuntimeError("force test transaction rollback")
    with engine.connect() as conn:
        assert (
            conn.execute(
                text("""SELECT count(*) FROM manuscript_artifact_placements
          WHERE id=:id"""),
                {"id": rolled_back},
            ).scalar_one()
            == 0
        )
    assert service.trace(principal, project, publication.id, draft.id) == (placed,)
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    with pytest.raises(DBAPIError):
        command.downgrade(config, "0037_pr2_13_claim_placement")


def test_artifact_migration_catalog_and_downgrade(phase2_database_url):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "0037_pr2_13_claim_placement")
    engine = create_engine(phase2_database_url)
    with engine.connect() as conn:
        baseline = set(
            conn.execute(
                text("""SELECT tablename,indexname,indexdef
          FROM pg_indexes WHERE schemaname='public'""")
            ).all()
        )
    engine.dispose()
    command.upgrade(config, "0038_pr2_13_artifact_placement")
    engine = create_engine(phase2_database_url)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0038_pr2_13_artifact_placement"
        )
        indexes = (
            conn.execute(
                text("""SELECT indexdef FROM pg_indexes WHERE
          schemaname='public' AND tablename='manuscript_artifact_placements'""")
            )
            .scalars()
            .all()
        )
        for column in ("artifact_version_id", "created_by"):
            assert sum(f"USING btree ({column})" in definition for definition in indexes) == 1
        assert (
            sum(
                "USING btree (manuscript_version_id, section_id, ordinal)" in definition
                for definition in indexes
            )
            == 1
        )
        assert (
            conn.execute(
                text("""SELECT count(*) FROM pg_constraint WHERE
          conrelid='manuscript_artifact_placements'::regclass AND contype='f'""")
            ).scalar_one()
            == 3
        )
    engine.dispose()
    command.downgrade(config, "0037_pr2_13_claim_placement")
    engine = create_engine(phase2_database_url)
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
            conn.execute(text("SELECT to_regclass('manuscript_artifact_placements')")).scalar_one()
            is None
        )
    engine.dispose()
