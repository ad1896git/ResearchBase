"""No PR220 DDL: accepted migrations preserve disposable historical bytes and edges."""

from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine

from tests.contracts.pr2_20_reports import migration_inventory
from tests.integration.phase2 import pr2_20_support as s
from tests.integration.phase2 import test_pr2_00_migration as legacy
from tests.integration.phase2 import test_pr2_15_decision_schema as minimal
from tests.integration.phase2.test_pr2_15_decision import _command, _review

conclusion_env = s.conclusion_env
phase2_database_url = s.phase2_database_url
decision_env = s.decision_env
pytestmark = pytest.mark.integration


@pytest.mark.parametrize("start", ["base", "0018_current_pointer_same_parent_integrity"])
def test_empty_install_noop_reconnect_and_permitted_empty_round_trip(start, monkeypatch):
    scripts = migration_inventory()
    with s.database() as url:
        monkeypatch.setenv("DATABASE_URL", url)
        if start != "base":
            s.upgrade(url, start)
        s.upgrade(url)
        engine = create_engine(url)
        try:
            version = s.require_pg18(engine)
            before = s.catalog(engine)
            s.upgrade(url)
            assert s.catalog(engine) == before
            engine.dispose()
            with engine.connect() as conn:
                assert (
                    conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                    == scripts[-1]["revision"]
                )
            config = Config("alembic.ini")
            config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
            command.downgrade(config, "0041_pr2_15_review_coordination")
            s.upgrade(url)
            assert s.catalog(engine) == before
            s.save_migration(
                "empty-" + start,
                engine,
                start,
                "EMPTY",
                (
                    "alembic upgrade head",
                    "alembic upgrade head",
                    "alembic downgrade 0041_pr2_15_review_coordination",
                    "alembic upgrade head",
                ),
                {},
                {},
                empty_roundtrip=True,
            )
            s.save_observation(
                "migration-empty-" + start,
                {
                    "postgres_version": version,
                    "start": start,
                    "target": scripts[-1]["revision"],
                    "scripts": scripts,
                    "catalog_before": before,
                    "catalog_after": s.catalog(engine),
                    "history_equal": True,
                },
            )
        finally:
            engine.dispose()


def test_legal_populated_0018_upgrade_preserves_identity_and_scientific_history(
    monkeypatch, tmp_path
):
    from sqlalchemy.orm import sessionmaker

    from researchbase.domain.organization import ProjectId
    from researchbase.foundation.artifact_store import ContentAddressedFilesystemArtifactStore
    from researchbase.foundation.execution_context import ExecutionContext
    from researchbase.foundation.time import SystemClock
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork
    from tests.application_compat import LegacyApplicationService
    from tests.integration.test_pr12_application import seed_claim, seed_measurement

    with s.database() as url:
        monkeypatch.setenv("DATABASE_URL", url)
        s.upgrade(url, "0018_current_pointer_same_parent_integrity")
        engine = create_engine(url)
        try:
            actor, project = uuid4(), uuid4()
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "INSERT INTO actors(id,actor_type,display_name,created_at) "
                        "VALUES (:id,'HUMAN','TEST ONLY legal legacy owner',:at)"
                    ),
                    {"id": actor, "at": datetime.now(UTC)},
                )
                conn.execute(
                    text(
                        "INSERT INTO projects(id,name,created_by,created_at) "
                        "VALUES (:id,'TEST ONLY legal legacy project',:actor,:at)"
                    ),
                    {"id": project, "actor": actor, "at": datetime.now(UTC)},
                )
            factory = sessionmaker(engine, expire_on_commit=False, autoflush=False)
            app = LegacyApplicationService(
                lambda: SqlAlchemyUnitOfWork(factory),
                SystemClock(),
                ContentAddressedFilesystemArtifactStore(tmp_path / "cas"),
            )
            context = ExecutionContext(actor_id=actor, request_id=uuid4(), client_type="test")
            seed_measurement(app, ProjectId(project), context, "pr220-legacy")
            seed_claim(app, ProjectId(project), context)
            tables = (
                "actors",
                "projects",
                "claims",
                "claim_versions",
                "runs",
                "measurements",
                "run_dataset_inputs",
                "run_artifact_inputs",
            )
            before = s.manifest(engine, tables)
            s.upgrade(url)
            assert s.manifest(engine, tables) == before
            engine.dispose()
            assert s.manifest(engine, tables) == before
            s.save_migration(
                "legal0018",
                engine,
                "0018_current_pointer_same_parent_integrity",
                "LEGAL_POPULATED",
                ("alembic upgrade head",),
                before,
                s.manifest(engine, tables),
            )
            s.save_observation(
                "migration-legal0018",
                {
                    "manifest_before": before,
                    "manifest_after": s.manifest(engine, tables),
                    "reconnected": True,
                },
            )
        finally:
            engine.dispose()


def test_populated_source_evidence_conclusion_placement_review_decision_head_noop(
    decision_env, phase2_database_url, tmp_path
):
    s._draft(decision_env[-1], phase2_database_url, tmp_path)
    _review(decision_env)
    saved = decision_env[0].record_decision(decision_env[2], _command(decision_env))
    engine = decision_env[-1][8]
    tables = (
        "literature_sources",
        "source_versions",
        "claim_versions",
        "scientific_conclusion_versions",
        "scientific_conclusion_claim_inputs",
        "manuscript_versions",
        "internal_review_records",
        "decision_records",
        "decision_basis_conclusions",
        "decision_basis_reviews",
    )
    before = s.manifest(engine, tables)
    catalog = s.catalog(engine)
    s.upgrade(phase2_database_url)
    assert s.manifest(engine, tables) == before
    assert s.catalog(engine) == catalog
    engine.dispose()
    with engine.connect() as conn:
        assert (
            conn.execute(
                text("SELECT content_hash FROM decision_records WHERE id=:id"), {"id": saved.id}
            ).scalar_one()
            == saved.content_hash
        )
    s.save_observation(
        "migration-populated-head",
        {
            "manifest_before": before,
            "manifest_after": s.manifest(engine, tables),
            "catalog": catalog,
        },
    )


def test_interrupted_accepted_upgrade_transaction_rolls_back_without_repair(
    conclusion_env, phase2_database_url
):
    engine = conclusion_env[8]
    before = s.catalog(engine)
    history = s.manifest(engine, ("claim_versions", "source_versions", "evidence_relations"))

    def interrupt(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("CREATE TABLE INTERNAL_REVIEW_RECORDS"):
            raise RuntimeError("TEST ONLY interrupted transactional migration")

    event.listen(Engine, "after_cursor_execute", interrupt)
    try:
        with pytest.raises(RuntimeError, match="interrupted"):
            s.upgrade(phase2_database_url)
    finally:
        event.remove(Engine, "after_cursor_execute", interrupt)
    assert s.catalog(engine) == before
    assert s.manifest(engine, tuple(history)) == history
    with engine.connect() as conn:
        assert (
            conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == "0033_pr2_11_r2_scientific_conclusion"
        )
    s.upgrade(phase2_database_url)
    assert s.manifest(engine, tuple(history)) == history


@pytest.mark.parametrize(
    "violation,expected",
    [
        ("orphan_creator", "PROJECT_CREATOR_ORPHAN"),
        ("duplicate_external_key", "DUPLICATE_ACTOR_EXTERNAL_KEY"),
        ("actor_type", "INVALID_ACTOR_TYPE"),
        ("actor_type_null", "INVALID_ACTOR_TYPE"),
        ("project_lifecycle", "INVALID_PROJECT_LIFECYCLE"),
        ("project_lifecycle_null", "INVALID_PROJECT_LIFECYCLE"),
    ],
)
def test_owning_illegal_legacy_preflight_atomic_and_deterministic(violation, expected, monkeypatch):
    with s.database() as url:
        monkeypatch.setenv("DATABASE_URL", url)
        legacy.test_legacy_state_preflight_fails_before_phase2_ddl_and_is_deterministic(
            url, violation, expected
        )


def test_owning_populated_downgrade_refusal_without_history_loss(decision_env, phase2_database_url):
    minimal.test_0042_downgrade_refuses_committed_history_without_loss(
        decision_env, phase2_database_url
    )


@pytest.mark.parametrize(
    "checkpoint", ["0020_literature_source_identity", "0022_source_version_and_merge_lineage"]
)
def test_accepted_populated_source_checkpoints_preserve_exact_rows(checkpoint, monkeypatch):
    from uuid import UUID

    from sqlalchemy.orm import sessionmaker

    from researchbase.application.source_identity import RegisterLiteratureSource
    from researchbase.application.source_version import (
        CreateSourceVersion,
        SourceVersionService,
        TransitionSourceVersion,
    )
    from researchbase.domain.source_identity import IdentifierType, SourceKind
    from researchbase.domain.source_version import SourceVersionKind, SourceVersionMaterial
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork

    with s.database() as url:
        monkeypatch.setenv("DATABASE_URL", url)
        engine, _, service, principal, project = s._authorized_service(
            url, migration_revision=checkpoint
        )
        try:
            source = service.register_literature_source(
                RegisterLiteratureSource(
                    principal,
                    project,
                    SourceKind.PAPER,
                    "TEST ONLY populated checkpoint",
                    uuid4(),
                    IdentifierType.DOI,
                    "10.2202/checkpoint",
                )
            )
            tables = ("literature_sources", "source_identifiers", "literature_source_project_links")
            if checkpoint.startswith("0022"):
                sf = sessionmaker(engine, expire_on_commit=False, autoflush=False)
                versions = SourceVersionService(
                    lambda: SqlAlchemyUnitOfWork(sf), service._credential_verifier
                )
                material = SourceVersionMaterial(
                    UUID(str(source["source_id"])),
                    SourceVersionKind.PUBLISHED,
                    None,
                    None,
                    "TEST ONLY source version",
                    None,
                    (),
                    None,
                    None,
                    None,
                    None,
                    None,
                )
                created = versions.create(
                    CreateSourceVersion(principal, project, material, uuid4())
                )
                versions.freeze(
                    TransitionSourceVersion(
                        principal, project, UUID(str(created["source_version_id"])), uuid4()
                    )
                )
                tables += ("source_versions",)
            columns = s.column_inventory(engine, tables)
            before = s.manifest(engine, tables, columns)
            s.upgrade(url)
            engine.dispose()
            assert s.manifest(engine, tables, columns) == before
            assert (
                service.find_source_by_identifier(
                    principal, project, IdentifierType.DOI, "10.2202/checkpoint"
                )["source_id"]
                == source["source_id"]
            )
            s.save_migration(
                "source-" + checkpoint,
                engine,
                checkpoint,
                "LEGAL_POPULATED",
                ("alembic upgrade head",),
                before,
                s.manifest(engine, tables, columns),
            )
        finally:
            engine.dispose()


def test_accepted_populated_search_checkpoint_preserves_plan_execution_results(monkeypatch):
    from uuid import UUID

    from scripts.pr2_04_pytest_evidence import FactRecorder

    from researchbase.application.literature_search_execution import (
        ExecuteLiteratureSearchExecution,
    )
    from tests.integration.phase2 import test_pr2_04_transaction_coverage as owning

    original = owning._setup
    monkeypatch.setattr(
        owning, "_setup", lambda url: original(url, migration_revision="0028_provider_cancellation")
    )
    with s.database() as url:
        monkeypatch.setenv("DATABASE_URL", url)
        engine, _, provider, service, request = owning._prepared(url, FactRecorder([]))
        try:
            created = service.create(request)
            execution = UUID(created["execution_id"])
            service.execute(
                ExecuteLiteratureSearchExecution(
                    execution,
                    request.actor_id,
                    request.deployment_id,
                    uuid4(),
                    project_id=request.project_id,
                    principal=request.principal,
                )
            )
            saved = service.get_provenance(request.principal, request.project_id, execution)
            assert saved["execution"]["status"] == "SUCCEEDED" and len(provider.calls) == 1
            tables = (
                "literature_search_plans",
                "literature_search_plan_versions",
                "literature_search_executions",
                "search_query_records",
                "search_result_records",
                "literature_search_provider_attempts",
                "literature_search_execution_events",
            )
            before = s.manifest(engine, tables)
            s.upgrade(url)
            engine.dispose()
            assert s.manifest(engine, tables) == before
            assert service.get_provenance(request.principal, request.project_id, execution) == saved
            s.save_migration(
                "search0028",
                engine,
                "0028_provider_cancellation",
                "LEGAL_POPULATED",
                ("alembic upgrade head",),
                before,
                s.manifest(engine, tables),
            )
        finally:
            engine.dispose()


def test_accepted_populated_evidence_checkpoint_preserves_hash_locator_and_edges(
    monkeypatch, tmp_path
):
    from tests.integration.phase2.test_m3_evidence import m3 as fixture

    with s.database() as url:
        monkeypatch.setenv("DATABASE_URL", url)
        generator = cast(Any, fixture).__wrapped__(url, tmp_path)
        env = next(generator)
        service, author, _, project, source, _, _, engine, _ = env
        try:
            evidence = service.create(
                author, project, source, "improved recall", uuid4(), paragraph=1, start=18, end=33
            )
            tables = (
                "literature_sources",
                "source_versions",
                "literature_evidence",
                "literature_evidence_review_events",
            )
            before = s.manifest(engine, tables)
            s.upgrade(url)
            engine.dispose()
            assert s.manifest(engine, tables) == before
            from uuid import UUID

            assert service.get(author, project, UUID(evidence["id"])) == evidence
            s.save_migration(
                "evidence0031",
                engine,
                "0031_m3_snapshot_relation_cardinality",
                "LEGAL_POPULATED",
                ("alembic upgrade head",),
                before,
                s.manifest(engine, tables),
            )
        finally:
            generator.close()


def test_populated_conclusion_placement_review_and_0042_checkpoints(
    conclusion_env, phase2_database_url, tmp_path
):
    from researchbase.application.decision import DecisionService, RecordDecisionCommand
    from researchbase.application.internal_review import InternalReviewService
    from researchbase.application.manuscript_placement import ClaimPlacementService
    from researchbase.application.publication import PublicationService
    from researchbase.application.scientific_conclusion import ClaimInputRequest
    from researchbase.foundation.artifact_store import ContentAddressedFilesystemArtifactStore
    from tests.integration.phase2.test_pr2_10_binding_contract import _artifact
    from tests.integration.phase2.test_pr2_11_r2_persistence import SCOPE

    scientific, factory, evidence, author, reviewer, project, claim, _, engine, credentials = (
        conclusion_env
    )
    target = scientific.create(
        author,
        project,
        "TEST ONLY migration conclusion",
        SCOPE,
        "MODERATE",
        None,
        (ClaimInputRequest(claim, "SUPPORTS"),),
        (),
        uuid4(),
    )
    scientific.freeze(author, project, target.conclusion_id, target.version_id, uuid4())
    tables = (
        "claim_versions",
        "evidence_relations",
        "scientific_conclusion_versions",
        "scientific_conclusion_claim_inputs",
    )
    before = s.manifest(engine, tables)
    s.upgrade(phase2_database_url, "0037_pr2_13_claim_placement")
    assert s.manifest(engine, tables) == before
    store = ContentAddressedFilesystemArtifactStore(tmp_path / "migration-cas")
    artifact = _artifact(
        factory, store, author, project, b"TEST ONLY historical manuscript", "manuscript"
    )
    publications = PublicationService(factory, credentials, store)
    publication = publications.create_publication(
        author, project, "PAPER", "TEST ONLY migration", uuid4()
    )
    manuscript = publications.create_draft(
        author, project, publication.id, artifact, "TEST ONLY migration", None, "INITIAL", uuid4()
    )
    ClaimPlacementService(factory, credentials).add(
        author,
        project,
        publication.id,
        manuscript.id,
        None,
        target.version_id,
        "RESULTS",
        {"kind": "PARAGRAPH", "value": "p1"},
        "DESCRIPTIVE",
        0,
        uuid4(),
    )
    tables += ("manuscript_versions", "manuscript_claim_placements")
    before = s.manifest(engine, tables)
    s.upgrade(phase2_database_url, "0040_pr2_14_initial_internal_review")
    assert s.manifest(engine, tables) == before
    review = InternalReviewService(factory, credentials, evidence).create(
        reviewer,
        project,
        "SCIENTIFIC_CONCLUSION_VERSION",
        target.version_id,
        "SCIENTIFIC",
        "ACCEPT",
        "TEST ONLY independent migration review",
        (),
        uuid4(),
    )
    tables += ("internal_review_records", "review_issues")
    before = s.manifest(engine, tables)
    s.upgrade(phase2_database_url, "0042_pr2_15_minimal_decision")
    assert s.manifest(engine, tables) == before
    service = DecisionService(factory, credentials, evidence)
    request = RecordDecisionCommand(
        uuid4(), project, target.version_id, "Proceed?", "TEST ONLY migrated basis"
    )
    saved = service.record_decision(reviewer, request)
    assert any(ref.id == review.id for ref in saved.basis)
    tables += ("decision_records", "decision_basis_conclusions", "decision_basis_reviews")
    # Preserve every checkpoint field while permitting B23's additive metadata.
    # SELECT * would compare different row shapes after the authorized columns.
    with engine.connect() as conn:
        checkpoint_columns = {
            table: tuple(
                conn.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_schema='public' AND table_name=:table "
                        "ORDER BY ordinal_position"
                    ),
                    {"table": table},
                ).scalars()
            )
            for table in tables
        }
    before = s.manifest(engine, tables, columns=checkpoint_columns)
    s.upgrade(phase2_database_url)
    engine.dispose()
    after = s.manifest(engine, tables, columns=checkpoint_columns)
    assert after == before
    with engine.connect() as conn:
        assert conn.execute(
            text(
                "SELECT id,novelty_assessment_id,material_version "
                "FROM internal_review_records ORDER BY id"
            )
        ).all() == [(review.id, None, 1)]
    assert service.record_decision(reviewer, request) == saved
    s.save_migration(
        "conclusion-placement-review-decision",
        engine,
        "0033_pr2_11_r2_scientific_conclusion",
        "LEGAL_POPULATED",
        (
            "alembic upgrade 0037_pr2_13_claim_placement",
            "alembic upgrade 0040_pr2_14_initial_internal_review",
            "alembic upgrade 0042_pr2_15_minimal_decision",
            "alembic upgrade head",
        ),
        before,
        after,
    )
