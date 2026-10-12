"""Disposable PostgreSQL R2 conclusion tests; all actors are TEST ONLY."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from researchbase.application.commands import FreezeClaimVersionCommand, LinkEvidenceCommand
from researchbase.application.scientific_conclusion import (
    ClaimInputRequest,
    LiteratureInputRequest,
    ScientificConclusionService,
)
from researchbase.domain.organization import ProjectId
from researchbase.foundation.artifact_store import ContentAddressedFilesystemArtifactStore
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.execution_context import ExecutionContext
from researchbase.foundation.hashing import sha256_canonical_json
from researchbase.foundation.time import SystemClock
from researchbase.persistence.uow import SqlAlchemyUnitOfWork
from tests.application_compat import LegacyApplicationService as ApplicationService
from tests.integration.test_pr12_application import seed_claim, seed_measurement

pytestmark = pytest.mark.integration
pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)

ADMIN_URL = "postgresql+psycopg://onephone@/postgres?host=/private/tmp&port=55442"


@pytest.fixture
def phase2_database_url(monkeypatch):
    if os.getenv("RB_PR211_R2_TEST_ADMIN_URL") != ADMIN_URL:
        pytest.fail("RB_PR211_R2_TEST_ADMIN_URL must name the approved disposable cluster")
    admin = create_engine(ADMIN_URL)
    with admin.connect() as conn:
        identity = conn.execute(text("""SELECT current_user,current_database(),
          current_setting('port'),current_setting('data_directory'),
          (SELECT system_identifier FROM pg_control_system())""")).one()
    assert tuple(map(str, identity)) == (
        "onephone", "postgres", "55442", "/private/tmp/rb-m3-postgres",
        "7695073913076924777",
    )
    name = f"researchbase_pr211_r2_test_{uuid4().hex}"
    with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        assert not conn.execute(
            text("SELECT EXISTS(SELECT 1 FROM pg_database WHERE datname=:name)"),
            {"name": name},
        ).scalar_one()
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    print(f"PR211_R2_CREATED: {name}")
    url = f"postgresql+psycopg://onephone@/{name}?host=/private/tmp&port=55442"
    monkeypatch.setenv("DATABASE_URL", url)
    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            assert conn.execute(text("SELECT current_database()")).scalar_one() == name
            assert conn.execute(text("SELECT count(*) FROM pg_tables WHERE schemaname='public'"))\
                .scalar_one() == 0
        engine.dispose()
        config = Config("alembic.ini")
        config.set_main_option("sqlalchemy.url", url)
        command.upgrade(config, "head")
        engine = create_engine(url)
        with engine.connect() as conn:
            revision = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        engine.dispose()
        assert revision == "0033_pr2_11_r2_scientific_conclusion"
        print(f"PR211_R2_REVISION: {name}={revision}")
        yield url
    finally:
        with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.execute(text("""SELECT pg_terminate_backend(pid) FROM pg_stat_activity
              WHERE datname=:name AND pid<>pg_backend_pid()"""), {"name": name})
            conn.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))
        admin.dispose()
        print(f"PR211_R2_DROPPED: {name}")


@pytest.fixture
def conclusion_env(request, tmp_path):
    m3 = request.getfixturevalue("m3")
    evidence_service, author, reviewer, project, source, _, _, engine, credentials = m3
    sf = sessionmaker(engine, expire_on_commit=False, autoflush=False)

    def factory():
        return SqlAlchemyUnitOfWork(sf)

    app = ApplicationService(
        factory, SystemClock(), ContentAddressedFilesystemArtifactStore(tmp_path / "claim-cas")
    )
    context = ExecutionContext(actor_id=author.actor_id, request_id=uuid4(), client_type="test")
    measurement = seed_measurement(app, ProjectId(project), context, "pr211-r2")
    claim, draft = seed_claim(app, ProjectId(project), context)
    app.link_evidence(LinkEvidenceCommand(
        claim.id, draft.id, measurement, None, "supports", None, draft.row_version, context
    ))
    linked = app.get_current_claim_version(claim.id)
    frozen = app.freeze_claim_version(FreezeClaimVersionCommand(
        claim.id, linked.id, context, linked.row_version
    ))
    service = ScientificConclusionService(factory, credentials)
    return (service, factory, evidence_service, author, reviewer, project,
            UUID(str(frozen.id)), source, engine, credentials)


SCOPE = {"population": "Adults", "conditions": None,
         "time_window": None, "applicability": None}


def test_pg_claim_only_freeze_exact_hash_restart_and_supersession(conclusion_env):
    service, factory, _, author, _, project, claim_id, _, engine, credentials = conclusion_env
    request = uuid4()
    created = service.create(
        author, project, "Evidence supports the effect.", SCOPE,
        "MODERATE", None, (ClaimInputRequest(claim_id, "SUPPORTS"),), (), request,
    )
    assert service.create(
        author, project, "Evidence supports the effect.", SCOPE,
        "MODERATE", None, (ClaimInputRequest(claim_id, "SUPPORTS"),), (), request,
    ) == created
    draft = service.read(author, project, created.conclusion_id, created.version_id)
    assert draft.status == "DRAFT" and draft.support_set_hash is None
    service.freeze(author, project, created.conclusion_id, created.version_id, uuid4())
    restarted = ScientificConclusionService(factory, credentials)
    frozen = restarted.read(author, project, created.conclusion_id, created.version_id)
    assert frozen.status == "FROZEN"
    assert frozen.claim_inputs[0].claim_version_id == claim_id
    assert frozen.literature_inputs == ()
    assert frozen.support_set_hash and frozen.content_hash
    with engine.connect() as conn:
        stored = conn.execute(text("""SELECT support_set_hash,content_hash,hash_scheme
          FROM scientific_conclusion_versions WHERE id=:id"""), {"id": created.version_id}).one()
    assert stored.hash_scheme == "sha256-cjson-v1"
    assert stored.support_set_hash == frozen.support_set_hash
    assert stored.content_hash == frozen.content_hash
    assert str(sha256_canonical_json(frozen.support_material)) == frozen.support_set_hash
    assert str(sha256_canonical_json(frozen.content_material)) == frozen.content_hash
    assert frozen.content_material["scientific_conclusion_id"] == str(created.conclusion_id)


def test_pg_snapshot_exact_claim_and_project_binding(conclusion_env):
    (
        service, _, evidence_service, author, reviewer, project, claim_id, source, engine, _
    ) = conclusion_env
    evidence = evidence_service.create(author, project,
        source, "improved recall", uuid4())
    evidence_id = UUID(evidence["id"])
    evidence_service.review(reviewer, project, evidence_id, "VERIFIED",
                            "Test-only exact passage inspection", uuid4())
    edge = {"evidence_id": str(evidence_id), "relation_type": "SUPPORTS",
            "qualification": "Test-only support"}
    snapshot = evidence_service.snapshot(author, project, "ClaimVersion", claim_id, [edge], uuid4())
    snapshot_id = UUID(snapshot["id"])
    created = service.create(author, project, "Bound exact claim snapshot", SCOPE,
        "MODERATE", None, (ClaimInputRequest(claim_id, "SUPPORTS", snapshot_id),), (), uuid4())
    service.freeze(author, project, created.conclusion_id, created.version_id, uuid4())
    view = service.read(author, project, created.conclusion_id, created.version_id)
    assert view.claim_inputs[0].literature_support_snapshot_id == snapshot_id
    snapshot_ref = view.support_material["claim_inputs"][0]["literature_support_snapshot"]
    assert snapshot_ref["id"] == str(snapshot_id)
    with engine.connect() as conn:
        assert conn.execute(text("""SELECT literature_support_snapshot_id FROM
           scientific_conclusion_claim_inputs WHERE conclusion_version_id=:id"""),
           {"id": created.version_id}).scalar_one() == snapshot_id


def test_pg_empty_freeze_and_unreviewed_positive_support_fail_closed(conclusion_env):
    service, _, evidence_service, author, _, project, _, source, engine, _ = conclusion_env
    empty = service.create(author, project, "Draft awaiting exact input", SCOPE,
                           "INCONCLUSIVE", "No support yet", (), (), uuid4())
    with pytest.raises(ResearchBaseError) as missing:
        service.freeze(author, project, empty.conclusion_id, empty.version_id, uuid4())
    assert missing.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    evidence = evidence_service.create(author, project,
        source, "improved recall", uuid4())
    with pytest.raises(ResearchBaseError):
        service.create(author, project, "Unreviewed support", SCOPE,
            "MODERATE", None, (),
            (LiteratureInputRequest(UUID(evidence["id"]), "SUPPORTS"),), uuid4())
    with engine.connect() as conn:
        count = conn.execute(text("SELECT count(*) FROM scientific_conclusions")).scalar_one()
        assert count == 1


def test_pg_duplicate_request_concurrent_and_unauthorized(conclusion_env):
    service, _, _, author, _, project, claim_id, _, engine, credentials = conclusion_env
    request = uuid4()

    def create(_):
        return service.create(author, project, "Concurrent test conclusion", SCOPE,
            "WEAK", None, (ClaimInputRequest(claim_id, "QUALIFIES"),), (), request)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = tuple(pool.map(create, (1, 2)))
    assert first == second
    credentials.enabled = False
    with pytest.raises(ResearchBaseError) as denied:
        create(3)
    assert denied.value.code is ErrorCode.FORBIDDEN
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM scientific_conclusions")).scalar_one() == 1
