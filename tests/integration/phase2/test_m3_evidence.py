"""Technical PostgreSQL tests with distinct test actors, NOT human acceptance."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker

from researchbase.application.commands import (
    ApplicationService,
    CreateHypothesisCommand,
    FreezeHypothesisCommand,
)
from researchbase.application.source_identity import RegisterLiteratureSource
from researchbase.application.source_version import (
    CreateSourceVersion,
    SourceVersionService,
    TransitionSourceVersion,
)
from researchbase.domain.organization import ProjectId
from researchbase.domain.research import HypothesisId, HypothesisVersionId
from researchbase.domain.source_identity import SourceKind
from researchbase.domain.source_version import (
    FrozenSourceReference,
    SourceVersionKind,
    SourceVersionMaterial,
)
from researchbase.foundation.artifact_store import ContentAddressedFilesystemArtifactStore
from researchbase.foundation.errors import ResearchBaseError
from researchbase.foundation.execution_context import ExecutionContext
from researchbase.foundation.time import SystemClock
from researchbase.persistence.uow import SqlAlchemyUnitOfWork
from tests.integration.phase2.test_pr2_00_ownership import _add_owner
from tests.integration.phase2.test_pr2_01_source_identity import _authorized_service


class TechnicalCredentials:
    """Test credential registry only; never installed by production composition."""

    def __init__(self, principals):
        self.principals = {p.actor_id: p for p in principals}
        self.enabled = True

    def is_valid(self, principal, at):
        return self.enabled and self.principals.get(principal.actor_id) == principal


@pytest.fixture
def m3(phase2_database_url, tmp_path):
    from researchbase.application.literature_evidence import LiteratureEvidenceService

    engine, identity, sources, author, project = _authorized_service(
        phase2_database_url, migration_revision="0031_m3_snapshot_relation_cardinality"
    )
    reviewer_id = uuid4()
    with engine.begin() as conn:
        _add_owner(
            conn,
            actor_id=reviewer_id,
            project_id=project,
            now=datetime.now(UTC),
            event_kind="ACTIVATED",
            request_id=uuid4(),
        )
    reviewer = replace(
        author,
        actor_id=reviewer_id,
        deployment_id="test-deployment",
        subject_value=str(reviewer_id.int % 1_000_000),
        credential_id=f"uid:{reviewer_id.int}",
    )
    credentials = TechnicalCredentials([author, reviewer])
    sf = sessionmaker(engine, expire_on_commit=False, autoflush=False)

    def factory():
        return SqlAlchemyUnitOfWork(sf)

    store = ContentAddressedFilesystemArtifactStore(tmp_path / "cas")
    service = LiteratureEvidenceService(factory, credentials, store)
    source = sources.register_literature_source(
        RegisterLiteratureSource(author, project, SourceKind.PAPER, "Technical fixture", uuid4())
    )
    document = service.import_document(
        author,
        project,
        b"A measured effect improved recall.\n\nLimitations remain.",
        "text/plain",
        "Test-only text; unrestricted fixture",
        uuid4(),
    )
    versions = SourceVersionService(factory, credentials)
    version = versions.create(
        CreateSourceVersion(
            author,
            project,
            SourceVersionMaterial(
                UUID(str(source["source_id"])),
                SourceVersionKind.PUBLISHED,
                None,
                None,
                "Technical fixture",
                None,
                (),
                None,
                None,
                None,
                FrozenSourceReference(
                    UUID(document["artifact_version_id"]), document["content_hash"]
                ),
                None,
            ),
            uuid4(),
        )
    )
    version_id = UUID(str(version["source_version_id"]))
    versions.freeze(TransitionSourceVersion(author, project, version_id, uuid4()))
    app = ApplicationService(factory, SystemClock(), store)
    context = ExecutionContext(actor_id=author.actor_id, request_id=uuid4(), client_type="cli")
    h = app.create_hypothesis(
        CreateHypothesisCommand(
            ProjectId(project),
            "Recall may improve under the studied condition.",
            None,
            None,
            None,
            context,
        )
    )
    frozen = app.freeze_hypothesis(
        FreezeHypothesisCommand(HypothesisId(h.id), HypothesisVersionId(h.version_id), context)
    )
    yield (
        service,
        author,
        reviewer,
        project,
        version_id,
        UUID(str(frozen.id)),
        document,
        engine,
        credentials,
    )
    engine.dispose()


def create(m3, **kwargs):
    service, author, _, project, source, *_ = m3
    return service.create(author, project, source, "improved recall", uuid4(), **kwargs)


def test_pg_manual_evidence_replay_and_restart(m3):
    service, author, reviewer, project, source, hypothesis, document, engine, _ = m3
    request = uuid4()
    evidence = service.create(author, project, source, "improved recall", request)
    assert evidence["review_status"] == "UNREVIEWED"
    assert evidence["locator"]["paragraph"] == "1"
    assert evidence["artifact_version_id"] == document["artifact_version_id"]
    assert service.create(author, project, source, "improved recall", request) == evidence
    with pytest.raises(ResearchBaseError):
        service.create(author, project, source, "Limitations", request)
    evidence_id = UUID(evidence["id"])
    reviewed = service.review(
        reviewer,
        project,
        evidence_id,
        "VERIFIED",
        "Technical reviewer inspected exact fixture span",
        uuid4(),
    )
    assert reviewed["content_hash"] == evidence["content_hash"]
    assert reviewed["review_events"][0]["reviewed_by"] == str(reviewer.actor_id)
    snapshot = service.snapshot(
        author,
        project,
        "HypothesisVersion",
        hypothesis,
        [
            {
                "evidence_id": str(evidence_id),
                "relation_type": "SUPPORTS",
                "qualification": "Bounded fixture relevance",
            }
        ],
        uuid4(),
    )
    assert snapshot["validity"] == "VALID"
    assert snapshot["relations"][0]["relation_type"] == "SUPPORTS"
    from researchbase.application.literature_evidence import LiteratureEvidenceService

    fresh = LiteratureEvidenceService(service._factory, service._credentials, service._store)
    assert fresh.get(author, project, evidence_id) == reviewed
    assert fresh.get_snapshot(author, project, UUID(snapshot["id"])) == snapshot
    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM literature_evidence WHERE id=:id"), {"id": evidence_id})
    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE literature_evidence SET extracted_statement='forged' WHERE id=:id"),
                {"id": evidence_id},
            )


def test_pg_missing_content_version_mismatch_and_wrong_location(m3):
    service, author, _, project, source, *_ = m3
    for kwargs in (
        {"paragraph": 99, "start": 0, "end": 3},
        {"paragraph": 1, "start": 0, "end": 15},
        {"artifact_version_id": uuid4()},
    ):
        with pytest.raises(ResearchBaseError):
            create(m3, **kwargs)
    with pytest.raises(ResearchBaseError):
        service.create(author, project, uuid4(), "improved recall", uuid4())


def test_pg_independence_missing_approval_related_and_conflicts(m3):
    service, author, reviewer, project, _, hypothesis, *_ = m3
    evidence = create(m3)
    eid = UUID(evidence["id"])
    edge = {
        "evidence_id": str(eid),
        "relation_type": "SUPPORTS",
        "qualification": "Relevant fixture",
    }
    with pytest.raises(ResearchBaseError):
        service.snapshot(author, project, "HypothesisVersion", hypothesis, [edge], uuid4())
    with pytest.raises(ResearchBaseError):
        service.review(author, project, eid, "VERIFIED", "self verification", uuid4())
    service.review(reviewer, project, eid, "VERIFIED", "Technical exact-span verification", uuid4())
    with pytest.raises(ResearchBaseError):
        service.snapshot(reviewer, project, "HypothesisVersion", hypothesis, [edge], uuid4())
    with pytest.raises(ResearchBaseError):
        service.snapshot(
            author,
            project,
            "HypothesisVersion",
            hypothesis,
            [{**edge, "relation_type": "RELATED"}],
            uuid4(),
        )
    with pytest.raises(ResearchBaseError):
        service.snapshot(
            author,
            project,
            "HypothesisVersion",
            hypothesis,
            [edge, {**edge, "relation_type": "CONTRADICTS"}],
            uuid4(),
        )
    contextual = service.snapshot(
        author,
        project,
        "HypothesisVersion",
        hypothesis,
        [{**edge, "relation_type": "CONTEXTUALIZES"}],
        uuid4(),
    )
    assert contextual["relations"][0]["relation_type"] == "CONTEXTUALIZES"


def test_pg_authority_replay_integrity_and_derived_staleness(m3):
    service, author, reviewer, project, _, hypothesis, document, engine, credentials = m3
    evidence = create(m3)
    eid = UUID(evidence["id"])
    request = uuid4()
    service.review(reviewer, project, eid, "VERIFIED", "Technical check", request)
    assert (
        len(
            service.review(reviewer, project, eid, "VERIFIED", "Technical check", request)[
                "review_events"
            ]
        )
        == 1
    )
    edge = {
        "evidence_id": str(eid),
        "relation_type": "SUPPORTS",
        "qualification": "Technical relevance",
    }
    snap = service.snapshot(author, project, "HypothesisVersion", hypothesis, [edge], uuid4())
    service.review(reviewer, project, eid, "DISPUTED", "Technical counterexample", uuid4())
    assert service.get_snapshot(author, project, UUID(snap["id"]))["validity"] == "STALE"
    for principal, p in ((replace(author, actor_id=uuid4()), project), (author, uuid4())):
        with pytest.raises(ResearchBaseError):
            service.get(principal, p, eid)
    credentials.enabled = False
    with pytest.raises(ResearchBaseError):
        service.review(reviewer, project, eid, "VERIFIED", "Technical check", request)
    credentials.enabled = True
    identity = "sha256:" + document["content_hash"]
    service._store._path_for(identity).write_bytes(b"altered")
    with pytest.raises(ResearchBaseError):
        service.get(author, project, eid)
    service._store._path_for(identity).unlink()
    with pytest.raises(ResearchBaseError):
        service.get_snapshot(author, project, UUID(snap["id"]))


def test_pg_review_rejection_is_terminal_and_history_append_only(m3):
    service, author, reviewer, project, *_rest, engine, _credentials = m3
    evidence = create(m3)
    identity = UUID(evidence["id"])
    service.review(reviewer, project, identity, "REJECTED", "Technical rejection", uuid4())
    with pytest.raises(ResearchBaseError):
        service.review(
            reviewer, project, identity, "VERIFIED", "Cannot revive rejected history", uuid4()
        )
    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            conn.execute(
                text(
                    "DELETE FROM literature_evidence_review_events WHERE literature_evidence_id=:id"
                ),
                {"id": identity},
            )
    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE literature_evidence SET review_status='VERIFIED' WHERE id=:id"),
                {"id": identity},
            )


def test_pg_document_import_replay_and_missing_fulltext(m3):
    service, author, _reviewer, project, source, _hypothesis, _document, _engine, credentials = m3
    request = uuid4()
    doc = service.import_document(
        author, project, b"fixture text", "text/plain", "Fixture unrestricted", request
    )
    assert (
        service.import_document(
            author, project, b"fixture text", "text/plain", "Fixture unrestricted", request
        )
        == doc
    )
    with pytest.raises(ResearchBaseError):
        service.import_document(
            author, project, b"altered text", "text/plain", "Fixture unrestricted", request
        )
    with service._factory() as uow:
        source_row = uow.source_version.version(source)
    versions = SourceVersionService(service._factory, credentials)
    draft = versions.create(
        CreateSourceVersion(
            author,
            project,
            SourceVersionMaterial(
                source_row["literature_source_id"],
                SourceVersionKind.PUBLISHED,
                None,
                None,
                "Technical metadata only",
                None,
                (),
                None,
                None,
                None,
                None,
                None,
            ),
            uuid4(),
        )
    )
    vid = UUID(str(draft["source_version_id"]))
    versions.freeze(TransitionSourceVersion(author, project, vid, uuid4()))
    with pytest.raises(ResearchBaseError):
        service.create(author, project, vid, "fixture text", uuid4())


def test_pg_snapshot_sequence_empty_correction_and_sealed_rows(m3):
    service, author, _reviewer, project, _source, hypothesis, _document, engine, _credentials = m3
    evidence = create(m3)
    request = uuid4()
    edges = [
        {
            "evidence_id": evidence["id"],
            "relation_type": "CONTEXTUALIZES",
            "qualification": "Technical context",
        }
    ]
    first = service.snapshot(author, project, "HypothesisVersion", hypothesis, edges, request)
    assert (
        service.snapshot(author, project, "HypothesisVersion", hypothesis, edges, request) == first
    )
    second = service.snapshot(author, project, "HypothesisVersion", hypothesis, [], uuid4())
    assert second["snapshot_number"] == 2 and second["previous_snapshot_id"] == first["id"]
    assert second["relations"] == []
    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            conn.execute(
                text("""INSERT INTO literature_evidence_relations
              (id,literature_support_snapshot_id,literature_evidence_id,relation_type,ordinal,qualification,created_by,created_at)
              VALUES (:id,:snapshot,:evidence,'CONTEXTUALIZES',1,
                      'late',:actor,clock_timestamp())"""),
                {
                    "id": uuid4(),
                    "snapshot": UUID(first["id"]),
                    "evidence": UUID(evidence["id"]),
                    "actor": author.actor_id,
                },
            )
    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            conn.execute(
                text("DELETE FROM literature_support_snapshots WHERE id=:id"),
                {"id": UUID(second["id"])},
            )


def test_pg_credential_expiry_and_non_reviewer_cannot_verify(m3):
    service, author, reviewer, project, *_rest, engine, credentials = m3
    evidence = create(m3)
    credentials.enabled = False
    with pytest.raises(ResearchBaseError):
        service.review(
            reviewer, project, UUID(evidence["id"]), "VERIFIED", "Expired credential", uuid4()
        )
    credentials.enabled = True
    from researchbase.application.phase2_identity import CloseProjectRole
    from tests.integration.phase2.test_pr2_00_challenges import _service

    identity, _, _ = _service(str(engine.url))
    with engine.connect() as conn:
        role = conn.execute(
            text(
                "SELECT id FROM project_role_assignments WHERE actor_id=:id AND project_id=:project"
            ),
            {"id": reviewer.actor_id, "project": project},
        ).scalar_one()
    identity.close_project_role(
        CloseProjectRole(author, project, role, "Technical authority revoked", uuid4())
    )
    with pytest.raises(ResearchBaseError):
        service.review(
            reviewer, project, UUID(evidence["id"]), "VERIFIED", "Revoked project role", uuid4()
        )


def test_pg_claim_link_uses_unchanged_phase1_closure(m3):
    from researchbase.application.commands import FreezeClaimVersionCommand, LinkEvidenceCommand
    from tests.integration.test_pr12_application import seed_claim, seed_measurement

    service, author, reviewer, project, *_ = m3
    from tests.application_compat import LegacyApplicationService

    app = LegacyApplicationService(service._factory, SystemClock(), service._store)
    ctx = ExecutionContext(actor_id=author.actor_id, request_id=uuid4(), client_type="cli")
    measurement = seed_measurement(app, ProjectId(project), ctx, "m3-claim")
    claim, version = seed_claim(app, ProjectId(project), ctx)
    app.link_evidence(
        LinkEvidenceCommand(
            claim.id,
            version.id,
            measurement,
            None,
            "supports",
            "Technical Phase1 fixture",
            version.row_version,
            ctx,
        )
    )
    current = app.get_current_claim_version(claim.id)
    frozen = app.freeze_claim_version(
        FreezeClaimVersionCommand(claim.id, current.id, ctx, current.row_version)
    )
    evidence = create(m3)
    service.review(
        reviewer, project, UUID(evidence["id"]), "VERIFIED", "Technical distinct reviewer", uuid4()
    )
    snapshot = service.snapshot(
        author,
        project,
        "ClaimVersion",
        frozen.id,
        [
            {
                "evidence_id": evidence["id"],
                "relation_type": "SUPPORTS",
                "qualification": "Technical test only; no real scientific approval",
            }
        ],
        uuid4(),
    )
    assert snapshot["target"]["type"] == "ClaimVersion"
    assert app.get_claim_version(frozen.id).content_hash == frozen.content_hash


def test_pg_upstream_retraction_stales_historical_support(m3):
    service, author, reviewer, project, source, hypothesis, document, _engine, credentials = m3
    evidence = create(m3)
    eid = UUID(evidence["id"])
    service.review(reviewer, project, eid, "VERIFIED", "Technical reviewer", uuid4())
    edge = {
        "evidence_id": evidence["id"],
        "relation_type": "SUPPORTS",
        "qualification": "Technical relevance",
    }
    snapshot = service.snapshot(author, project, "HypothesisVersion", hypothesis, [edge], uuid4())
    with service._factory() as uow:
        source_row = uow.source_version.version(source)
    versions = SourceVersionService(service._factory, credentials)
    draft = versions.create(
        CreateSourceVersion(
            author,
            project,
            SourceVersionMaterial(
                source_row["literature_source_id"],
                SourceVersionKind.RETRACTED,
                FrozenSourceReference(source, source_row["content_hash"]),
                FrozenSourceReference(
                    UUID(document["artifact_version_id"]), document["content_hash"]
                ),
                "Technical retraction fixture",
                None,
                (),
                None,
                None,
                None,
                None,
                None,
            ),
            uuid4(),
        )
    )
    versions.freeze(
        TransitionSourceVersion(author, project, UUID(str(draft["source_version_id"])), uuid4())
    )
    readback = service.get_snapshot(author, project, UUID(snapshot["id"]))
    assert readback["validity"] == "STALE" and readback["content_hash"] == snapshot["content_hash"]
    assert service.get(author, project, eid)["source_validity"] == "RETRACTED"
    with pytest.raises(ResearchBaseError):
        service.snapshot(author, project, "HypothesisVersion", hypothesis, [edge], uuid4())


def test_pg_m3_migration_from_phase1_and_empty_roundtrip(phase2_database_url):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "0018_current_pointer_same_parent_integrity")
    command.upgrade(config, "0031_m3_snapshot_relation_cardinality")
    command.downgrade(config, "0029_metadata_observations")
    command.upgrade(config, "0031_m3_snapshot_relation_cardinality")
    engine = create_engine(phase2_database_url)
    with engine.connect() as connection:
        assert (
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == "0031_m3_snapshot_relation_cardinality"
        )
    engine.dispose()


def test_pg_m3_alembic_env_preserves_percent_escaped_socket_url(phase2_database_url, monkeypatch):
    from urllib.parse import quote

    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import make_url

    socket_host = make_url(phase2_database_url).query.get("host")
    assert isinstance(socket_host, str) and socket_host.startswith("/")
    encoded_url = phase2_database_url.replace(
        f"host={socket_host}", f"host={quote(socket_host, safe='')}"
    )
    assert encoded_url != phase2_database_url
    monkeypatch.setenv("DATABASE_URL", encoded_url)
    config = Config("alembic.ini")
    command.upgrade(config, "0031_m3_snapshot_relation_cardinality")
    assert config.get_main_option("sqlalchemy.url") == encoded_url
    engine = create_engine(encoded_url)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT current_database()")).scalar_one() == (
            engine.url.database
        )
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0031_m3_snapshot_relation_cardinality"
        )
    engine.dispose()


def test_pg_authority_expiring_during_document_storage_rolls_back(m3, monkeypatch):
    service, author, _reviewer, project, _source, _hypothesis, _document, engine, credentials = m3
    original = service._store.put_verified

    def put_and_expire(*args):
        result = original(*args)
        credentials.enabled = False
        return result

    monkeypatch.setattr(service._store, "put_verified", put_and_expire)
    with engine.connect() as connection:
        before = connection.execute(text("SELECT count(*) FROM artifact_versions")).scalar_one()
    with pytest.raises(ResearchBaseError):
        service.import_document(
            author,
            project,
            b"Technical expiry during storage",
            "text/plain",
            "Technical unrestricted",
            uuid4(),
        )
    with engine.connect() as connection:
        assert (
            connection.execute(text("SELECT count(*) FROM artifact_versions")).scalar_one()
            == before
        )
