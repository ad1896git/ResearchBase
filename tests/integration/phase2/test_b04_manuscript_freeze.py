"""B04 Application seal, retained closure, replay and failure atomicity."""

# SQL assertions preserve the literal contract.
# ruff: noqa: E501

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import text

from researchbase.application.manuscript_freeze import (
    FreezeManuscriptCommand,
    GetManuscriptVersionQuery,
    ManuscriptFreezeService,
)
from researchbase.application.manuscript_placement import (
    ArtifactPlacementService,
    CitationPlacementService,
    ClaimPlacementService,
)
from researchbase.application.manuscript_scientific_trace import ManuscriptScientificTraceService
from researchbase.application.scientific_conclusion import ClaimInputRequest
from researchbase.foundation.artifact_store import ContentAddressedFilesystemArtifactStore
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.manuscript_freeze_repository import (
    SqlAlchemyManuscriptFreezeRepository,
)
from tests.integration.phase2.test_pr2_10_binding_contract import _artifact
from tests.integration.phase2.test_pr2_11_r2_persistence import (
    SCOPE,
)
from tests.integration.phase2.test_pr2_11_r2_persistence import conclusion_env as _conclusion_env
from tests.integration.phase2.test_pr2_11_r2_persistence import (
    phase2_database_url as _phase2_database_url,
)
from tests.integration.phase2.test_pr2_13_claim_placement import _draft

conclusion_env = _conclusion_env
phase2_database_url = _phase2_database_url

pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)
pytestmark = pytest.mark.integration


@pytest.fixture
def b04_env(conclusion_env, phase2_database_url, tmp_path):
    scientific, factory, engine, credentials, actor, project, claim, publication, draft = _draft(
        conclusion_env, phase2_database_url, tmp_path
    )
    store = ContentAddressedFilesystemArtifactStore(tmp_path / "cas")
    # Existing owner fixtures intentionally use a separate CAS; B04 uses one store.
    for path in (tmp_path / "claim-cas" / "sha256").rglob("*"):
        if path.is_file():
            store.put_verified(path.read_bytes(), path.name)
    service = ManuscriptFreezeService(factory, credentials, store)
    query = GetManuscriptVersionQuery(project, publication.id, draft.id)
    return service, query, actor, factory, engine, credentials, store, claim, conclusion_env


def freeze(service, actor, query):
    preview = service.get_manuscript_version(actor, query)
    return service.freeze_manuscript_version(
        actor,
        FreezeManuscriptCommand(
            query.project_id,
            query.publication_id,
            query.manuscript_version_id,
            preview.preview_placement_set_hash,
            preview.preview_content_hash,
        ),
    )


def test_empty_seal_restart_and_replay(b04_env):
    service, query, actor, factory, engine, credentials, store, _, _ = b04_env
    result = freeze(service, actor, query)
    assert result.status == "FROZEN" and result.current_validity == "VALID"
    assert result.preview_content_hash is None and result.frozen_at is not None
    restarted = ManuscriptFreezeService(factory, credentials, store)
    assert restarted.get_manuscript_version(actor, query) == result
    command = FreezeManuscriptCommand(
        query.project_id,
        query.publication_id,
        query.manuscript_version_id,
        result.placement_set_hash,
        result.content_hash,
    )
    assert restarted.freeze_manuscript_version(actor, command) == result
    with engine.connect() as conn:
        assert (
            conn.execute(
                text("SELECT row_version FROM manuscript_versions WHERE id=:id"),
                {"id": query.manuscript_version_id},
            ).scalar_one()
            == 2
        )
        parent = conn.execute(
            text(
                "SELECT lifecycle_status,current_manuscript_version_id,row_version FROM publications WHERE id=:id"
            ),
            {"id": query.publication_id},
        ).one()
        assert tuple(parent) == ("DRAFTING", query.manuscript_version_id, 2)
    with pytest.raises(ResearchBaseError) as exc:
        restarted.freeze_manuscript_version(actor, replace(command, expected_content_hash="0" * 64))
    assert exc.value.code == ErrorCode.IDEMPOTENCY_CONFLICT


def test_all_placements_and_frozen_readback(b04_env):
    service, q, actor, factory, _, credentials, store, claim, base = b04_env
    scientific = base[0]
    conclusion = scientific.create(
        actor,
        q.project_id,
        "Test conclusion",
        SCOPE,
        "MODERATE",
        None,
        (ClaimInputRequest(claim, "SUPPORTS"),),
        (),
        uuid4(),
    )
    scientific.freeze(actor, q.project_id, conclusion.conclusion_id, conclusion.version_id, uuid4())
    claims = ClaimPlacementService(factory, credentials, store)
    claims.add(
        actor,
        q.project_id,
        q.publication_id,
        q.manuscript_version_id,
        claim,
        None,
        "RESULTS",
        {"kind": "PARAGRAPH", "value": "p1"},
        "SUPPORTED",
        0,
        uuid4(),
    )
    claims.add(
        actor,
        q.project_id,
        q.publication_id,
        q.manuscript_version_id,
        None,
        conclusion.version_id,
        "DISCUSSION",
        {"kind": "SPAN", "value": "s1"},
        "SUGGESTIVE",
        0,
        uuid4(),
    )
    citations = CitationPlacementService(factory, credentials, store)
    citations.add(
        actor,
        q.project_id,
        q.publication_id,
        q.manuscript_version_id,
        base[7],
        "INTRO",
        {"kind": "PARAGRAPH", "value": "p1"},
        "BACKGROUND",
        0,
        uuid4(),
    )
    figure = _artifact(factory, store, actor, q.project_id, b"Test figure", "figure")
    artifacts = ArtifactPlacementService(factory, credentials, store)
    artifacts.add(
        actor,
        q.project_id,
        q.publication_id,
        q.manuscript_version_id,
        figure,
        "RESULTS",
        {"kind": "CAPTION", "value": "f1"},
        "FIGURE",
        0,
        uuid4(),
    )
    before = (
        claims.trace(actor, q.project_id, q.publication_id, q.manuscript_version_id),
        citations.trace(actor, q.project_id, q.publication_id, q.manuscript_version_id),
        artifacts.trace(actor, q.project_id, q.publication_id, q.manuscript_version_id),
    )
    result = freeze(service, actor, q)
    assert result.current_validity == "VALID"
    assert (
        claims.trace(actor, q.project_id, q.publication_id, q.manuscript_version_id),
        citations.trace(actor, q.project_id, q.publication_id, q.manuscript_version_id),
        artifacts.trace(actor, q.project_id, q.publication_id, q.manuscript_version_id),
    ) == before
    trace = ManuscriptScientificTraceService(factory, credentials, store).trace(
        actor, q.project_id, q.publication_id, q.manuscript_version_id
    )
    assert trace.manuscript_content_hash == result.content_hash and len(trace.placements) == 4
    assert trace.claim_experiment_evidence and trace.conclusion_claim_inputs


def test_changed_expectations_and_expired_credentials(b04_env):
    service, q, actor, factory, _, credentials, _, claim, _ = b04_env
    preview = service.get_manuscript_version(actor, q)
    cmd = FreezeManuscriptCommand(
        q.project_id,
        q.publication_id,
        q.manuscript_version_id,
        preview.preview_placement_set_hash,
        preview.preview_content_hash,
    )
    ClaimPlacementService(factory, credentials).add(
        actor,
        q.project_id,
        q.publication_id,
        q.manuscript_version_id,
        claim,
        None,
        "RESULTS",
        {"kind": "PARAGRAPH", "value": "p1"},
        "SUPPORTED",
        0,
        uuid4(),
    )
    with pytest.raises(ResearchBaseError) as exc:
        service.freeze_manuscript_version(actor, cmd)
    assert exc.value.code == ErrorCode.CONCURRENT_MODIFICATION
    with pytest.raises(ResearchBaseError) as exc:
        service.get_manuscript_version(replace(actor, credential_id="expired"), q)
    assert exc.value.code == ErrorCode.FORBIDDEN
    assert service.get_manuscript_version(actor, q).status == "DRAFT"


@pytest.mark.parametrize("failure", ["missing", "corrupt", "size"])
def test_document_cas_failures(b04_env, failure, monkeypatch):
    service, q, actor, _, _, _, store, _, _ = b04_env
    if failure == "missing":
        monkeypatch.setattr(store, "verify", lambda _: False)
    elif failure == "corrupt":
        monkeypatch.setattr(store, "open", lambda _: b"corrupt")
    else:
        original = store.open
        monkeypatch.setattr(store, "open", lambda x: original(x) + b" ")
    with pytest.raises(ResearchBaseError) as exc:
        service.get_manuscript_version(actor, q)
    assert exc.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION


@pytest.mark.parametrize("point", ["between_updates", "constraints", "commit"])
def test_rollback_seal_and_pointer(b04_env, point, monkeypatch):
    service, q, actor, _, engine, _, _, _, _ = b04_env
    preview = service.get_manuscript_version(actor, q)
    cmd = FreezeManuscriptCommand(
        q.project_id,
        q.publication_id,
        q.manuscript_version_id,
        preview.preview_placement_set_hash,
        preview.preview_content_hash,
    )

    def fail(*args, **kwargs):
        raise ResearchBaseError(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "injected")

    if point == "between_updates":

        def partial(self, row, parent, placement, content, at):
            self._session.execute(
                text(
                    "UPDATE manuscript_versions SET status='FROZEN',placement_set_hash=:p,content_hash=:c,frozen_at=:at,row_version=row_version+1 WHERE id=:id"
                ),
                {"id": row["id"], "p": placement, "c": content, "at": at},
            )
            fail()

        monkeypatch.setattr(SqlAlchemyManuscriptFreezeRepository, "seal", partial)
    elif point == "constraints":
        monkeypatch.setattr(SqlAlchemyManuscriptFreezeRepository, "force_constraints", fail)
    else:
        from researchbase.persistence.uow import SqlAlchemyUnitOfWork

        monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", fail)
    with pytest.raises(ResearchBaseError):
        service.freeze_manuscript_version(actor, cmd)
    with engine.connect() as conn:
        assert conn.execute(
            text(
                "SELECT status,content_hash,placement_set_hash,frozen_at,row_version FROM manuscript_versions WHERE id=:id"
            ),
            {"id": q.manuscript_version_id},
        ).one() == ("DRAFT", None, None, None, 1)
        assert (
            conn.execute(
                text("SELECT current_manuscript_version_id FROM publications WHERE id=:id"),
                {"id": q.publication_id},
            ).scalar_one()
            is None
        )


@pytest.mark.parametrize("change", ["DISPUTED", "REJECTED"])
def test_positive_support_denies_new_seal_and_preserves_history(b04_env, change):
    from uuid import UUID

    from researchbase.application.scientific_conclusion import LiteratureInputRequest

    service, q, actor, factory, _, credentials, store, _, base = b04_env
    scientific, _, evidence_service, _, reviewer, project, _, source, _, _ = base
    evidence = evidence_service.create(actor, project, source, "improved recall", uuid4())
    evidence_id = UUID(evidence["id"])
    evidence_service.review(
        reviewer, project, evidence_id, "VERIFIED", "Test independent review", uuid4()
    )
    conclusion = scientific.create(
        actor,
        project,
        "Test reviewed conclusion",
        SCOPE,
        "MODERATE",
        None,
        (),
        (LiteratureInputRequest(evidence_id, "SUPPORTS"),),
        uuid4(),
    )
    scientific.freeze(actor, project, conclusion.conclusion_id, conclusion.version_id, uuid4())
    ClaimPlacementService(factory, credentials).add(
        actor,
        project,
        q.publication_id,
        q.manuscript_version_id,
        None,
        conclusion.version_id,
        "DISCUSSION",
        {"kind": "PARAGRAPH", "value": "p1"},
        "SUPPORTED",
        0,
        uuid4(),
    )
    preview = service.get_manuscript_version(actor, q)
    cmd = FreezeManuscriptCommand(
        project,
        q.publication_id,
        q.manuscript_version_id,
        preview.preview_placement_set_hash,
        preview.preview_content_hash,
    )
    frozen = service.freeze_manuscript_version(actor, cmd)
    if change == "REJECTED":
        evidence_service.review(reviewer, project, evidence_id, "DISPUTED", "Test dispute", uuid4())
    evidence_service.review(reviewer, project, evidence_id, change, "Test later review", uuid4())
    read = service.get_manuscript_version(actor, q)
    assert read.current_validity == "STALE" and read.content_hash == frozen.content_hash
    assert service.freeze_manuscript_version(actor, cmd) == read
    # A second initial draft with the same closure must fail new admission.
    from researchbase.application.publication import PublicationService

    publications = PublicationService(factory, credentials, store)
    parent = publications.create_publication(actor, project, "PAPER", "Second", uuid4())
    draft = publications.create_draft(
        actor,
        project,
        parent.id,
        frozen.document_artifact_version_id,
        "Second",
        None,
        "INITIAL",
        uuid4(),
    )
    ClaimPlacementService(factory, credentials).add(
        actor,
        project,
        parent.id,
        draft.id,
        None,
        conclusion.version_id,
        "DISCUSSION",
        {"kind": "PARAGRAPH", "value": "p1"},
        "SUPPORTED",
        0,
        uuid4(),
    )
    with pytest.raises(ResearchBaseError) as exc:
        service.freeze_manuscript_version(
            actor, FreezeManuscriptCommand(project, parent.id, draft.id, "a" * 64, "b" * 64)
        )
    assert exc.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION


@pytest.mark.parametrize(
    "table,column",
    [
        ("claim_versions", "content_hash"),
        ("claim_versions", "support_set_hash"),
        ("measurements", "content_hash"),
        ("metric_definition_versions", "content_hash"),
        ("experiment_spec_versions", "content_hash"),
    ],
)
def test_broken_phase1_hashes_deny_formal_provenance(b04_env, table, column):
    service, q, actor, factory, engine, credentials, _, claim, _ = b04_env
    ClaimPlacementService(factory, credentials).add(
        actor,
        q.project_id,
        q.publication_id,
        q.manuscript_version_id,
        claim,
        None,
        "RESULTS",
        {"kind": "PARAGRAPH", "value": "p1"},
        "SUPPORTED",
        0,
        uuid4(),
    )
    with engine.begin() as conn:
        conn.execute(text("SET LOCAL session_replication_role='replica'"))
        conn.execute(text(f"UPDATE {table} SET {column}=repeat('0',64)"))
    with pytest.raises(ResearchBaseError):
        service.get_manuscript_version(actor, q)


@pytest.mark.parametrize("failure", ["basis_bytes", "predecessor_hash", "fulltext_validity"])
def test_literature_only_closure_verifies_source_artifacts_and_predecessor(
    b04_env, failure, monkeypatch
):
    from dataclasses import replace
    from uuid import UUID

    from researchbase.application.governance import (
        CreateImpactAssessmentCommand,
        GovernanceService,
        ProposedImpactTarget,
    )
    from researchbase.application.scientific_conclusion import LiteratureInputRequest
    from researchbase.application.source_version import (
        CreateSourceVersion,
        SourceVersionService,
        TransitionSourceVersion,
        _material_from_row,
    )
    from researchbase.domain.source_version import FrozenSourceReference, SourceVersionKind
    from researchbase.foundation.execution_context import ExecutionContext
    from researchbase.foundation.time import SystemClock

    service, q, actor, factory, engine, credentials, store, _, base = b04_env
    scientific, _, evidence_service, _, reviewer, project, _, source, _, _ = base
    basis = _artifact(factory, store, actor, project, b"Test correction basis", "other")
    with factory() as uow:
        old = uow.source_version.version(source)
        material = _material_from_row(uow.source_version, old)
        basis_row = uow.manuscript_freeze.artifact(basis, project)
    material = replace(
        material,
        version_kind=SourceVersionKind.CORRECTED,
        predecessor_source_version=FrozenSourceReference(source, old["content_hash"]),
        correction_basis_artifact=FrozenSourceReference(basis, basis_row["content_hash"]),
    )
    versions = SourceVersionService(factory, credentials)
    created = versions.create(CreateSourceVersion(actor, project, material, uuid4()))
    corrected = UUID(str(created["source_version_id"]))
    versions.freeze(TransitionSourceVersion(actor, project, corrected, uuid4()))
    evidence = evidence_service.create(actor, project, corrected, "improved recall", uuid4())
    evidence_id = UUID(evidence["id"])
    evidence_service.review(
        reviewer, project, evidence_id, "VERIFIED", "Independent test inspection", uuid4()
    )
    conclusion = scientific.create(
        actor,
        project,
        "Test corrected source conclusion",
        SCOPE,
        "MODERATE",
        None,
        (),
        (LiteratureInputRequest(evidence_id, "SUPPORTS"),),
        uuid4(),
    )
    scientific.freeze(actor, project, conclusion.conclusion_id, conclusion.version_id, uuid4())
    ClaimPlacementService(factory, credentials).add(
        actor,
        project,
        q.publication_id,
        q.manuscript_version_id,
        None,
        conclusion.version_id,
        "DISCUSSION",
        {"kind": "PARAGRAPH", "value": "p1"},
        "SUPPORTED",
        0,
        uuid4(),
    )
    if failure == "basis_bytes":
        original = store.verify
        monkeypatch.setattr(
            store,
            "verify",
            lambda x: False
            if x.removeprefix("sha256:") == basis_row["content_hash"]
            else original(x),
        )
    elif failure == "predecessor_hash":
        with engine.begin() as conn:
            conn.execute(text("SET LOCAL session_replication_role='replica'"))
            conn.execute(
                text("UPDATE source_versions SET title=title||'changed' WHERE id=:id"),
                {"id": source},
            )
    else:
        assert material.fulltext_artifact is not None
        governance = GovernanceService(factory, SystemClock())
        context = ExecutionContext(actor_id=actor.actor_id, request_id=uuid4(), client_type="test")
        governance.create_impact_assessment(
            CreateImpactAssessmentCommand(
                project,
                None,
                {"test": "invalid source bytes"},
                "invalid",
                (
                    ProposedImpactTarget(
                        "artifact_version", material.fulltext_artifact.id, "invalid"
                    ),
                ),
                context,
            )
        )
    with pytest.raises(ResearchBaseError) as exc:
        service.get_manuscript_version(actor, q)
    assert exc.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION


@pytest.mark.parametrize("state", ["40001", "40P01"])
@pytest.mark.parametrize("exhausted", [False, True])
def test_retry_aborted_transactions_from_fresh_share_snapshot(
    b04_env, state, exhausted, monkeypatch
):
    service, q, actor, _, engine, *_ = b04_env
    preview = service.get_manuscript_version(actor, q)
    cmd = FreezeManuscriptCommand(
        q.project_id,
        q.publication_id,
        q.manuscript_version_id,
        preview.preview_placement_set_hash,
        preview.preview_content_hash,
    )
    original = SqlAlchemyManuscriptFreezeRepository.force_constraints
    attempts = []

    def constraints(self):
        attempts.append(self._session)
        if exhausted or len(attempts) < 3:
            self._session.execute(
                text(
                    f"DO $$ BEGIN RAISE EXCEPTION 'injected transaction abort' USING ERRCODE='{state}'; END $$"
                )
            )
        else:
            original(self)

    monkeypatch.setattr(SqlAlchemyManuscriptFreezeRepository, "force_constraints", constraints)
    if exhausted:
        with pytest.raises(ResearchBaseError) as exc:
            service.freeze_manuscript_version(actor, cmd)
        assert exc.value.code == ErrorCode.CONCURRENT_MODIFICATION
        assert service.get_manuscript_version(actor, q).status == "DRAFT"
    else:
        result = service.freeze_manuscript_version(actor, cmd)
        assert result.status == "FROZEN"
    assert len(attempts) == 3 and len({id(x) for x in attempts}) == 3
    with engine.connect() as conn:
        status, row_version = conn.execute(
            text("SELECT status,row_version FROM manuscript_versions WHERE id=:id"),
            {"id": q.manuscript_version_id},
        ).one()
        assert (status, row_version) == (("DRAFT", 1) if exhausted else ("FROZEN", 2))
