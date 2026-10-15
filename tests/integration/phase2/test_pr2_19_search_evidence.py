"""G1 runnable search prefix; no invented search-to-source resolution bridge."""

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
