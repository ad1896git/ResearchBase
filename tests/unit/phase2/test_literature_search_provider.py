from __future__ import annotations

from tests.pr2_04_provider_observations import PROVIDER_RETRIEVED_AT

from uuid import uuid4

from researchbase.application.literature_search_provider import (
    FakeSearchCapability,
    SearchRequest,
    StaticSearchCapabilityRegistry,
    response_is_success,
)
from researchbase.domain.literature_search_execution import SearchHit, SearchResponse


def test_fake_provider_records_attempt_and_returns_typed_hits() -> None:
    provider = FakeSearchCapability(
        responses=[
            SearchResponse.success(
                provider_id="fake",
                provider_version="1",
                normalized_query="cortex",
                provider_request_id="remote-1",
                hits=(SearchHit("paper-1", "Paper", None, None, None),),
                retrieved_at=PROVIDER_RETRIEVED_AT,
            )
        ]
    )
    request = SearchRequest(
        execution_id=uuid4(),
        attempt_id=uuid4(),
        provider_request_key=uuid4(),
        plan_version_id=uuid4(),
        plan_content_hash="0" * 64,
        plan_material={},
        query_index=0,
        query_text="cortex",
        perspective=None,
        query_type="TEXT",
        provider_id="fake",
        provider_version="1",
        max_results=10,
    )

    response = provider.search(request)

    assert response_is_success(response)
    assert len(provider.calls) == 1
    assert response.hits[0].external_identifier == "paper-1"


def test_uncertain_provider_response_is_not_success() -> None:
    response = SearchResponse.uncertain(
        provider_id="fake",
        provider_version="1",
        normalized_query="cortex",
        provider_request_id=None,
    )

    assert not response_is_success(response)


def test_provider_registry_resolves_exact_version_only() -> None:
    version_one = FakeSearchCapability(capability_id="catalog", version="1")
    version_two = FakeSearchCapability(capability_id="catalog", version="2")
    registry = StaticSearchCapabilityRegistry((version_one, version_two))

    assert registry.resolve("catalog", "1") is version_one
    assert registry.resolve("catalog", "2") is version_two
    assert registry.resolve("catalog", "3") is None
    assert registry.versions("catalog") == ("1", "2")
