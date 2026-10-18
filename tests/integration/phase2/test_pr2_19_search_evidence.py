"""G1 retrieval boundary and persisted exact-resolution literature provenance."""

import pytest
from sqlalchemy import text

from researchbase.domain.literature_search_execution import SearchHit, SearchResponse
from tests.integration.phase2.pr2_19_support import phase2_database_url as _phase2_database_url
from tests.integration.phase2.test_pr2_04_provider_pg_coverage import QUERY, setup_case
from tests.pr2_04_provider_observations import PROVIDER_RETRIEVED_AT

phase2_database_url = _phase2_database_url


pytestmark = pytest.mark.integration


def test_persisted_search_result_is_not_verified_evidence(phase2_database_url):
    response = SearchResponse.success(
        provider_id="provider-a",
        provider_version="1",
        normalized_query=QUERY,
        provider_request_id="pr219-fixed",
        retrieved_at=PROVIDER_RETRIEVED_AT,
        hits=(SearchHit("pr219-paper", "Recall experiment", None, None, None),),
    )
    engine, provider, service, principal, project, command, _ = setup_case(
        phase2_database_url, [response]
    )
    try:
        with engine.connect() as conn:
            before = tuple(
                conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
                for table in (
                    "literature_sources",
                    "source_versions",
                    "literature_evidence",
                    "literature_evidence_review_events",
                )
            )
        service.execute(command)
        saved = service.get_provenance(principal, project, command.execution_id)
        assert saved["execution"]["status"] == "SUCCEEDED"
        assert len(provider.calls) == 1
        with engine.connect() as conn:
            assert (
                conn.execute(text("SELECT count(*) FROM search_result_records")).scalar_one() == 1
            )
            assert (
                tuple(
                    conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
                    for table in (
                        "literature_sources",
                        "source_versions",
                        "literature_evidence",
                        "literature_evidence_review_events",
                    )
                )
                == before
            )
        assert (
            type(service)(
                service._uow_factory, provider, credential_verifier=service._credential_verifier
            ).get_provenance(principal, project, command.execution_id)
            == saved
        )
    finally:
        engine.dispose()


# B01 uses its existing-command fixture; head upgrade is explicit in setup_m2.
pytest_plugins = ("tests.integration.phase2.b01_support",)


def test_persisted_resolution_exact_source_verified_evidence_conclusion_path(b01_env):
    from dataclasses import replace
    from datetime import UTC, datetime
    from uuid import UUID, uuid4

    from researchbase.application.literature_evidence import LiteratureEvidenceService
    from researchbase.application.scientific_conclusion import (
        LiteratureInputRequest,
        ScientificConclusionService,
    )
    from researchbase.domain.source_version import FrozenSourceReference
    from tests.integration.phase2.b01_support import create_version, record
    from tests.integration.phase2.test_m3_evidence import TechnicalCredentials
    from tests.integration.phase2.test_pr2_00_ownership import _add_owner
    from tests.integration.phase2.test_pr2_11_r2_persistence import SCOPE

    e = b01_env
    original = e["bundle"].literature_evidence
    author = e["principal"]
    reviewer_id = uuid4()
    with e["engine"].begin() as conn:
        _add_owner(
            conn,
            actor_id=reviewer_id,
            project_id=e["project"],
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
    literature = LiteratureEvidenceService(original._factory, credentials, original._store)
    document = literature.import_document(
        author,
        e["project"],
        b"A measured effect improved recall.",
        "text/plain",
        "Unrestricted test fixture",
        uuid4(),
    )
    material = replace(
        e["material"],
        fulltext_artifact=FrozenSourceReference(
            UUID(document["artifact_version_id"]), document["content_hash"]
        ),
    )
    version = create_version(e["bundle"], author, e["project"], material)
    resolution = record(e, source_version_id=version)
    evidence = literature.create(author, e["project"], version, "improved recall", uuid4())
    reviewed = literature.review(
        reviewer,
        e["project"],
        UUID(evidence["id"]),
        "VERIFIED",
        "Independent exact retained passage inspection",
        uuid4(),
    )
    assert reviewed["content_hash"] == evidence["content_hash"]
    conclusion = ScientificConclusionService(original._factory, credentials, literature)
    created = conclusion.create(
        author,
        e["project"],
        "The bounded source reports improved recall.",
        SCOPE,
        "MODERATE",
        "Fixture only",
        (),
        (LiteratureInputRequest(UUID(evidence["id"]), "SUPPORTS"),),
        uuid4(),
    )
    conclusion.freeze(author, e["project"], created.conclusion_id, created.version_id, uuid4())
    saved = conclusion.read(author, e["project"], created.conclusion_id, created.version_id)
    assert saved.status == "FROZEN" and saved.content_hash and saved.support_set_hash
    with e["engine"].connect() as conn:
        bridge = conn.execute(
            text("""SELECT r.id,r.content_hash,s.id,s.content_hash,v.id,v.content_hash,
            e.id,e.content_hash,e.review_status FROM search_result_records r
            JOIN search_result_resolutions s ON s.search_result_record_id=r.id
            JOIN source_versions v ON v.id=s.source_version_id
            JOIN literature_evidence e ON e.source_version_id=v.id
            JOIN scientific_conclusion_literature_inputs i ON i.literature_evidence_id=e.id
            WHERE s.id=:resolution AND i.conclusion_version_id=:conclusion"""),
            {"resolution": resolution.id, "conclusion": created.version_id},
        ).one()
    assert bridge[0] == e["results"][0]
    assert bridge[2] == resolution.id and bridge[3] == resolution.content_hash
    assert bridge[4] == version == resolution.source_version_id
    assert bridge[6] == UUID(evidence["id"]) and bridge[7] == evidence["content_hash"]
    assert bridge[8] == "VERIFIED" and all(bridge[i] for i in (1, 3, 5, 7))

    from sqlalchemy.orm import sessionmaker

    from researchbase.application.search_result_resolution import (
        ExactResolutionQuery,
        SearchResultResolutionService,
    )
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork
    from tests.integration.phase2.b30_observations import assert_snapshot_read, sql_protocol

    sessions = sessionmaker(e["engine"], expire_on_commit=False, autoflush=False)

    def observed_factory():
        return SqlAlchemyUnitOfWork(sessions)

    fresh = ScientificConclusionService(observed_factory, credentials, literature)
    resolver = SearchResultResolutionService(observed_factory, credentials, original._store)
    with sql_protocol(e["engine"]) as statements:
        assert fresh.read(author, e["project"], created.conclusion_id, created.version_id) == saved
        assert (
            resolver.get_search_result_resolution(
                author, ExactResolutionQuery(e["project"], resolution.id)
            )
            == resolution
        )
    assert_snapshot_read(statements)
    assert record(e, source_version_id=version) == resolution
