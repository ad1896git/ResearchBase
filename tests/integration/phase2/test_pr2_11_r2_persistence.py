"""Disposable PostgreSQL R2 conclusion tests; all actors are TEST ONLY."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
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
from tests.disposable_postgres import disposable_database
from tests.integration.test_pr12_application import seed_claim, seed_measurement

pytestmark = pytest.mark.integration


@pytest.fixture
def phase2_database_url(monkeypatch):
    with disposable_database("researchbase_pr211_r2_test_", "RB_PR211_R2_TEST_ADMIN_URL") as url:
        name = make_url(url).database
        monkeypatch.setenv("DATABASE_URL", url)
        engine = create_engine(url)
        with engine.connect() as conn:
            assert conn.execute(text("SELECT current_database()")).scalar_one() == name
            assert (
                conn.execute(
                    text("SELECT count(*) FROM pg_tables WHERE schemaname='public'")
                ).scalar_one()
                == 0
            )
        engine.dispose()
        config = Config("alembic.ini")
        config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
        # This suite verifies the exact accepted R2 revision, not future heads.
        command.upgrade(config, "0033_pr2_11_r2_scientific_conclusion")
        engine = create_engine(url)
        with engine.connect() as conn:
            revision = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        engine.dispose()
        assert revision == "0033_pr2_11_r2_scientific_conclusion"
        print(f"PR211_R2_REVISION: {name}={revision}")
        yield url


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
    app.link_evidence(
        LinkEvidenceCommand(
            claim.id, draft.id, measurement, None, "supports", None, draft.row_version, context
        )
    )
    linked = app.get_current_claim_version(claim.id)
    frozen = app.freeze_claim_version(
        FreezeClaimVersionCommand(claim.id, linked.id, context, linked.row_version)
    )
    service = ScientificConclusionService(factory, credentials, evidence_service)
    return (
        service,
        factory,
        evidence_service,
        author,
        reviewer,
        project,
        UUID(str(frozen.id)),
        source,
        engine,
        credentials,
    )


SCOPE = {"population": "Adults", "conditions": None, "time_window": None, "applicability": None}


def test_pg_claim_only_freeze_exact_hash_restart_and_supersession(conclusion_env):
    (service, factory, evidence_service, author, _, project, claim_id, _, engine, credentials) = (
        conclusion_env
    )
    request = uuid4()
    created = service.create(
        author,
        project,
        "Evidence supports the effect.",
        SCOPE,
        "MODERATE",
        None,
        (ClaimInputRequest(claim_id, "SUPPORTS"),),
        (),
        request,
    )
    assert (
        service.create(
            author,
            project,
            "Evidence supports the effect.",
            SCOPE,
            "MODERATE",
            None,
            (ClaimInputRequest(claim_id, "SUPPORTS"),),
            (),
            request,
        )
        == created
    )
    draft = service.read(author, project, created.conclusion_id, created.version_id)
    assert draft.status == "DRAFT" and draft.support_set_hash is None
    service.freeze(author, project, created.conclusion_id, created.version_id, uuid4())
    restarted = ScientificConclusionService(factory, credentials, evidence_service)
    frozen = restarted.read(author, project, created.conclusion_id, created.version_id)
    assert frozen.status == "FROZEN"
    assert frozen.claim_inputs[0].claim_version_id == claim_id
    assert frozen.literature_inputs == ()
    assert frozen.support_set_hash and frozen.content_hash
    with engine.connect() as conn:
        stored = conn.execute(
            text("""SELECT support_set_hash,content_hash,hash_scheme
          FROM scientific_conclusion_versions WHERE id=:id"""),
            {"id": created.version_id},
        ).one()
    assert stored.hash_scheme == "sha256-cjson-v1"
    assert stored.support_set_hash == frozen.support_set_hash
    assert stored.content_hash == frozen.content_hash
    assert str(sha256_canonical_json(frozen.support_material)) == frozen.support_set_hash
    assert str(sha256_canonical_json(frozen.content_material)) == frozen.content_hash
    assert frozen.content_material is not None
    assert frozen.content_material["scientific_conclusion_id"] == str(created.conclusion_id)


def test_pg_snapshot_exact_claim_and_project_binding(conclusion_env):
    (service, _, evidence_service, author, reviewer, project, claim_id, source, engine, _) = (
        conclusion_env
    )
    evidence = evidence_service.create(author, project, source, "improved recall", uuid4())
    evidence_id = UUID(evidence["id"])
    evidence_service.review(
        reviewer, project, evidence_id, "VERIFIED", "Test-only exact passage inspection", uuid4()
    )
    edge = {
        "evidence_id": str(evidence_id),
        "relation_type": "SUPPORTS",
        "qualification": "Test-only support",
    }
    snapshot = evidence_service.snapshot(author, project, "ClaimVersion", claim_id, [edge], uuid4())
    snapshot_id = UUID(snapshot["id"])
    created = service.create(
        author,
        project,
        "Bound exact claim snapshot",
        SCOPE,
        "MODERATE",
        None,
        (ClaimInputRequest(claim_id, "SUPPORTS", snapshot_id),),
        (),
        uuid4(),
    )
    service.freeze(author, project, created.conclusion_id, created.version_id, uuid4())
    view = service.read(author, project, created.conclusion_id, created.version_id)
    assert view.claim_inputs[0].literature_support_snapshot_id == snapshot_id
    assert view.support_material is not None
    snapshot_ref = view.support_material["claim_inputs"][0]["literature_support_snapshot"]
    assert snapshot_ref["id"] == str(snapshot_id)
    with engine.connect() as conn:
        assert (
            conn.execute(
                text("""SELECT literature_support_snapshot_id FROM
           scientific_conclusion_claim_inputs WHERE conclusion_version_id=:id"""),
                {"id": created.version_id},
            ).scalar_one()
            == snapshot_id
        )


def test_pg_empty_freeze_and_unreviewed_positive_support_fail_closed(conclusion_env):
    service, _, evidence_service, author, _, project, _, source, engine, _ = conclusion_env
    empty = service.create(
        author,
        project,
        "Draft awaiting exact input",
        SCOPE,
        "INCONCLUSIVE",
        "No support yet",
        (),
        (),
        uuid4(),
    )
    with pytest.raises(ResearchBaseError) as missing:
        service.freeze(author, project, empty.conclusion_id, empty.version_id, uuid4())
    assert missing.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    evidence = evidence_service.create(author, project, source, "improved recall", uuid4())
    with pytest.raises(ResearchBaseError):
        service.create(
            author,
            project,
            "Unreviewed support",
            SCOPE,
            "MODERATE",
            None,
            (),
            (LiteratureInputRequest(UUID(evidence["id"]), "SUPPORTS"),),
            uuid4(),
        )
    with engine.connect() as conn:
        count = conn.execute(text("SELECT count(*) FROM scientific_conclusions")).scalar_one()
        assert count == 1


def test_pg_duplicate_request_concurrent_and_unauthorized(conclusion_env):
    service, _, _, author, _, project, claim_id, _, engine, credentials = conclusion_env
    request = uuid4()

    def create(_):
        return service.create(
            author,
            project,
            "Concurrent test conclusion",
            SCOPE,
            "WEAK",
            None,
            (ClaimInputRequest(claim_id, "QUALIFIES"),),
            (),
            request,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = tuple(pool.map(create, (1, 2)))
    assert first == second
    credentials.enabled = False
    with pytest.raises(ResearchBaseError) as denied:
        create(3)
    assert denied.value.code is ErrorCode.FORBIDDEN
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM scientific_conclusions")).scalar_one() == 1


def test_pg_literature_only_freeze_and_hash_readback(conclusion_env):
    service, _, evidence_service, author, reviewer, project, _, source, _, _ = conclusion_env
    evidence = evidence_service.create(author, project, source, "improved recall", uuid4())
    evidence_id = UUID(evidence["id"])
    evidence_service.review(
        reviewer, project, evidence_id, "VERIFIED", "Test-only exact inspection", uuid4()
    )
    result = service.create(
        author,
        project,
        "Direct reviewed evidence supports recall.",
        SCOPE,
        "WEAK",
        None,
        (),
        (LiteratureInputRequest(evidence_id, "SUPPORTS"),),
        uuid4(),
    )
    service.freeze(author, project, result.conclusion_id, result.version_id, uuid4())
    view = service.read(author, project, result.conclusion_id, result.version_id)
    assert view.status == "FROZEN" and view.claim_inputs == ()
    assert view.literature_inputs[0].literature_evidence_id == evidence_id
    assert str(sha256_canonical_json(view.support_material)) == view.support_set_hash


def test_pg_positive_review_must_be_independent_of_conclusion_author(conclusion_env):
    service, _, evidence_service, author, reviewer, project, _, source, engine, _ = conclusion_env
    evidence = evidence_service.create(reviewer, project, source, "improved recall", uuid4())
    evidence_id = UUID(evidence["id"])
    evidence_service.review(
        author, project, evidence_id, "VERIFIED", "Test-only exact inspection", uuid4()
    )
    with pytest.raises(ResearchBaseError) as denied:
        service.create(
            author,
            project,
            "Self-reviewed support cannot promote.",
            SCOPE,
            "WEAK",
            None,
            (),
            (LiteratureInputRequest(evidence_id, "SUPPORTS"),),
            uuid4(),
        )
    assert denied.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM scientific_conclusions")).scalar_one() == 0


def test_pg_direct_evidence_dispute_blocks_freeze_without_partial_write(conclusion_env):
    service, _, evidence_service, author, reviewer, project, _, source, engine, _ = conclusion_env
    evidence = evidence_service.create(author, project, source, "improved recall", uuid4())
    evidence_id = UUID(evidence["id"])
    evidence_service.review(
        reviewer, project, evidence_id, "VERIFIED", "Test-only exact inspection", uuid4()
    )
    result = service.create(
        author,
        project,
        "Evidence under review.",
        SCOPE,
        "WEAK",
        None,
        (),
        (LiteratureInputRequest(evidence_id, "SUPPORTS"),),
        uuid4(),
    )
    evidence_service.review(
        reviewer, project, evidence_id, "DISPUTED", "Test-only dispute", uuid4()
    )
    with pytest.raises(ResearchBaseError) as blocked:
        service.freeze(author, project, result.conclusion_id, result.version_id, uuid4())
    assert blocked.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    with engine.connect() as conn:
        row = conn.execute(
            text("""SELECT status,support_set_hash,content_hash
           FROM scientific_conclusion_versions WHERE id=:id"""),
            {"id": result.version_id},
        ).one()
    assert row.status == "DRAFT"
    assert row.support_set_hash is None and row.content_hash is None


def test_pg_dispute_projects_stale_without_rewriting_frozen_history(conclusion_env):
    service, _, evidence_service, author, reviewer, project, _, source, _, _ = conclusion_env
    evidence = evidence_service.create(author, project, source, "improved recall", uuid4())
    evidence_id = UUID(evidence["id"])
    evidence_service.review(
        reviewer, project, evidence_id, "VERIFIED", "Test-only exact inspection", uuid4()
    )
    result = service.create(
        author,
        project,
        "Historical exact support.",
        SCOPE,
        "WEAK",
        None,
        (),
        (LiteratureInputRequest(evidence_id, "SUPPORTS"),),
        uuid4(),
    )
    service.freeze(author, project, result.conclusion_id, result.version_id, uuid4())
    before = service.read(author, project, result.conclusion_id, result.version_id)
    evidence_service.review(
        reviewer, project, evidence_id, "DISPUTED", "Test-only later dispute", uuid4()
    )
    after = service.read(author, project, result.conclusion_id, result.version_id)
    assert after.validity == "STALE"
    assert after.status == "FROZEN"
    assert after.support_set_hash == before.support_set_hash
    assert after.content_hash == before.content_hash


def test_pg_revision_preserves_prior_hashes_and_moves_same_parent_pointer(conclusion_env):
    service, _, _, author, _, project, claim_id, _, engine, _ = conclusion_env
    first = service.create(
        author,
        project,
        "First synthesis.",
        SCOPE,
        "WEAK",
        None,
        (ClaimInputRequest(claim_id, "SUPPORTS"),),
        (),
        uuid4(),
    )
    service.freeze(author, project, first.conclusion_id, first.version_id, uuid4())
    original = service.read(author, project, first.conclusion_id, first.version_id)
    revised = service.revise(
        author,
        project,
        first.conclusion_id,
        "Revised synthesis.",
        SCOPE,
        "MODERATE",
        None,
        (ClaimInputRequest(claim_id, "SUPPORTS"),),
        (),
        uuid4(),
    )
    assert revised.conclusion_id == first.conclusion_id
    assert revised.version_id != first.version_id
    draft = service.read(author, project, revised.conclusion_id, revised.version_id)
    assert draft.status == "DRAFT"
    service.freeze(author, project, revised.conclusion_id, revised.version_id, uuid4())
    prior = service.read(author, project, first.conclusion_id, first.version_id)
    current = service.read(author, project, revised.conclusion_id, revised.version_id)
    assert prior.status == "SUPERSEDED" and prior.content_hash == original.content_hash
    assert current.status == "FROZEN" and current.version_number == 2
    with engine.connect() as conn:
        pointer = conn.execute(
            text("""SELECT current_version_id FROM scientific_conclusions
           WHERE id=:id"""),
            {"id": first.conclusion_id},
        ).scalar_one()
    assert pointer == revised.version_id


def test_pg_frozen_science_rejects_direct_mutation(conclusion_env):
    service, _, _, author, _, project, claim_id, _, engine, _ = conclusion_env
    result = service.create(
        author,
        project,
        "Immutable synthesis.",
        SCOPE,
        "WEAK",
        None,
        (ClaimInputRequest(claim_id, "SUPPORTS"),),
        (),
        uuid4(),
    )
    service.freeze(author, project, result.conclusion_id, result.version_id, uuid4())
    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            conn.execute(
                text("""UPDATE scientific_conclusion_versions SET statement='tampered',
              row_version=row_version+1 WHERE id=:id"""),
                {"id": result.version_id},
            )
    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            conn.execute(
                text("""DELETE FROM scientific_conclusion_claim_inputs
              WHERE conclusion_version_id=:id"""),
                {"id": result.version_id},
            )
    view = service.read(author, project, result.conclusion_id, result.version_id)
    assert view.statement == "Immutable synthesis." and view.status == "FROZEN"


def test_pg_current_pointer_cannot_reference_superseded_at_commit(conclusion_env):
    service, _, _, author, _, project, claim_id, _, engine, _ = conclusion_env
    result = service.create(
        author,
        project,
        "Current pointer invariant.",
        SCOPE,
        "WEAK",
        None,
        (ClaimInputRequest(claim_id, "SUPPORTS"),),
        (),
        uuid4(),
    )
    service.freeze(author, project, result.conclusion_id, result.version_id, uuid4())
    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            conn.execute(
                text("""UPDATE scientific_conclusion_versions
              SET status='SUPERSEDED',row_version=row_version+1 WHERE id=:version"""),
                {"version": result.version_id},
            )
    with engine.connect() as conn:
        status = conn.execute(
            text("""SELECT status FROM scientific_conclusion_versions
          WHERE id=:version"""),
            {"version": result.version_id},
        ).scalar_one()
    assert status == "FROZEN"


def test_pg_draft_inputs_change_only_through_authorized_application_command(conclusion_env):
    service, _, _, author, _, project, claim_id, _, engine, credentials = conclusion_env
    draft = service.create(
        author,
        project,
        "Draft composition.",
        SCOPE,
        "WEAK",
        None,
        (),
        (),
        uuid4(),
    )
    request = uuid4()
    changed = service.replace_inputs(
        author,
        project,
        draft.conclusion_id,
        draft.version_id,
        (ClaimInputRequest(claim_id, "SUPPORTS"),),
        (),
        request,
    )
    assert changed == draft
    assert (
        service.replace_inputs(
            author,
            project,
            draft.conclusion_id,
            draft.version_id,
            (ClaimInputRequest(claim_id, "SUPPORTS"),),
            (),
            request,
        )
        == draft
    )
    service.freeze(author, project, draft.conclusion_id, draft.version_id, uuid4())
    with pytest.raises(ResearchBaseError) as sealed:
        service.replace_inputs(
            author,
            project,
            draft.conclusion_id,
            draft.version_id,
            (),
            (),
            uuid4(),
        )
    assert sealed.value.code is ErrorCode.INVALID_STATE_TRANSITION
    credentials.enabled = False
    with pytest.raises(ResearchBaseError) as denied:
        service.replace_inputs(
            author,
            project,
            draft.conclusion_id,
            draft.version_id,
            (),
            (),
            uuid4(),
        )
    assert denied.value.code is ErrorCode.FORBIDDEN
    with engine.connect() as conn:
        count = conn.execute(
            text("""SELECT count(*) FROM scientific_conclusion_claim_inputs
           WHERE conclusion_version_id=:version"""),
            {"version": draft.version_id},
        ).scalar_one()
    assert count == 1


@pytest.mark.parametrize("encoded_url", [False, True])
def test_pg_empty_0033_downgrade_and_nonempty_history_protection(
    phase2_database_url, conclusion_env, encoded_url, monkeypatch
):
    if encoded_url:
        phase2_database_url = (
            make_url(phase2_database_url)
            .update_query_dict({"application_name": "task2b/downgrade"})
            .render_as_string(hide_password=False)
        )
        assert "%2F" in phase2_database_url
    monkeypatch.delenv("DATABASE_URL", raising=False)
    service, _, _, author, _, project, claim_id, _, engine, _ = conclusion_env
    result = service.create(
        author,
        project,
        "History protected.",
        SCOPE,
        "WEAK",
        None,
        (ClaimInputRequest(claim_id, "SUPPORTS"),),
        (),
        uuid4(),
    )
    service.freeze(author, project, result.conclusion_id, result.version_id, uuid4())
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url.replace("%", "%%"))
    with pytest.raises(Exception, match="preserves scientific history"):
        command.downgrade(config, "0032_pr2_10_discussion")
    with engine.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0033_pr2_11_r2_scientific_conclusion"
        )


@pytest.mark.parametrize("encoded_url", [False, True])
def test_pg_empty_0033_downgrade_succeeds(phase2_database_url, encoded_url, monkeypatch):
    if encoded_url:
        phase2_database_url = (
            make_url(phase2_database_url)
            .update_query_dict({"application_name": "task2b/downgrade"})
            .render_as_string(hide_password=False)
        )
        assert "%2F" in phase2_database_url
    monkeypatch.delenv("DATABASE_URL", raising=False)
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url.replace("%", "%%"))
    command.downgrade(config, "0032_pr2_10_discussion")
    engine = create_engine(phase2_database_url)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0032_pr2_10_discussion"
        )
        assert not conn.execute(
            text("""SELECT to_regclass('public.scientific_conclusions')""")
        ).scalar_one()
    engine.dispose()
