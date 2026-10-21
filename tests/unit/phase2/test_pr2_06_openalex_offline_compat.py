"""Deterministic, disconnected Works v1 adapter compatibility observations."""

import json
from pathlib import Path
from uuid import uuid4

import pytest

from researchbase.adapters.literature_http import HttpObservation
from researchbase.adapters.openalex import OpenAlexSearchCapability
from researchbase.application.literature_search_provider import ProviderError, ProviderFailureKind
from tests.unit.test_m2_openalex import context, request

FIXTURE = Path(__file__).parents[2] / "fixtures/openalex_works_v1_offline.json"


def payload():
    return json.loads(FIXTURE.read_text())


def adapter(observation):
    return OpenAlexSearchCapability(get=lambda *_: observation)


def test_offline_fixture_preserves_order_normalized_ids_dois_and_provenance():
    result = adapter(
        HttpObservation(
            200, {"content-type": "application/json", "x-request-id": "offline-1"}, payload()
        )
    ).search(request(), context())
    assert [hit.external_identifier for hit in result.hits] == ["W1", "W2"]
    assert result.hits[0].url == "https://doi.org/10.1234/abc"
    assert result.hits[1].url == "https://openalex.org/W2"
    assert (result.provider_id, result.provider_version, result.provider_request_id) == (
        "openalex",
        "works-v1",
        "offline-1",
    )
    assert result.normalized_query == "CRISPR Cas9"
    assert result.warning_codes == ()


@pytest.mark.parametrize(
    "change",
    [
        lambda p: p["results"][1].update(id="W01"),
        lambda p: p["meta"].update(page=2),
        lambda p: p["meta"].update(page=True),
        lambda p: p["meta"].update(per_page=100),
        lambda p: p["meta"].update(per_page=2.0),
        lambda p: p["meta"].update(count=True),
        lambda p: p["results"][0].update(id=None),
        lambda p: p["results"][0].update(doi="https://evil.example/10.1234/ABC"),
    ],
)
def test_duplicate_or_drifted_work_is_rejected_without_partial_results(change):
    body = payload()
    change(body)
    with pytest.raises(ProviderError) as error:
        adapter(HttpObservation(200, {"content-type": "application/json"}, body)).search(
            request(), context()
        )
    assert error.value.code == "PROVIDER_MALFORMED"


@pytest.mark.parametrize(
    "observation,code",
    [
        (
            HttpObservation(
                200, {"content-type": "text/html"}, {"meta": {"count": 0}, "results": []}
            ),
            "PROVIDER_MALFORMED",
        ),
        (HttpObservation(200, {"content-type": "application/json"}, None), "PROVIDER_MALFORMED"),
        (
            HttpObservation(
                200, {"content-type": "application/json"}, None, payload_truncated=True
            ),
            "PROVIDER_MALFORMED",
        ),
        (
            HttpObservation(
                200,
                {"content-type": "application/json"},
                None,
                payload_truncated=True,
                payload_failure="INCOMPLETE_BODY",
            ),
            "PROVIDER_TRANSIENT",
        ),
    ],
)
def test_invalid_or_incomplete_response_is_classified(observation, code):
    with pytest.raises(ProviderError) as error:
        adapter(observation).search(request(), context())
    assert error.value.code == code


def test_authentication_error_is_permanent_and_secret_free():
    with pytest.raises(ProviderError) as error:
        adapter(
            HttpObservation(401, {"content-type": "application/json"}, {"detail": "secret-canary"})
        ).search(request(), context())
    assert error.value.kind is ProviderFailureKind.PERMANENT
    assert "secret-canary" not in str(error.value)


@pytest.mark.parametrize("echo", ("secret-canary", "trace-secret-canary"))
def test_provider_request_id_cannot_echo_injected_api_key(echo):
    capability = OpenAlexSearchCapability(
        api_key="secret-canary",
        get=lambda *_: HttpObservation(
            200,
            {"x-request-id": echo},
            {"meta": {"count": 0}, "results": []},
        ),
    )
    result = capability.search(request(), context())
    assert result.provider_request_id is None


def test_oversized_search_url_is_rejected_before_dispatch():
    called = []

    def unexpected_get(*_) -> HttpObservation:
        called.append(True)
        raise AssertionError("oversized query must fail before HTTP dispatch")

    capability = OpenAlexSearchCapability(get=unexpected_get)
    asked = request()
    from dataclasses import replace

    asked = replace(asked, query_text="x" * 5000, provider_request_key=uuid4())
    with pytest.raises(ProviderError) as error:
        capability.search(asked, context())
    assert error.value.kind is ProviderFailureKind.PERMANENT
    assert called == []
