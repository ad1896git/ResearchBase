"""Offline adapter tests; injected HTTP observations are never live evidence."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from researchbase.adapters.literature_http import HttpObservation
from researchbase.adapters.openalex import OpenAlexSearchCapability
from researchbase.application.literature_search_provider import (
    ProviderError,
    SearchCallContext,
    SearchRequest,
)
from researchbase.domain.literature_search_execution import DeliveryCertainty


def request():
    return SearchRequest(
        uuid4(),
        uuid4(),
        uuid4(),
        uuid4(),
        "a" * 64,
        {
            "source_scope": "BIBLIOGRAPHIC",
            "time_range": None,
            "language_scope": [],
            "inclusion_criteria": None,
            "exclusion_criteria": None,
        },
        0,
        "CRISPR Cas9",
        None,
        "TEXT",
        "openalex",
        "works-v1",
        2,
    )


def context(cancel=False):
    return SearchCallContext(uuid4(), datetime.now(UTC) + timedelta(seconds=10), 10, lambda: cancel)


def test_bounded_request_preserves_provider_identity_and_order():
    calls = []

    def get(url, headers, timeout):
        calls.append((url, headers, timeout))
        return HttpObservation(
            200,
            {},
            {
                "meta": {"count": 3},
                "results": [
                    {
                        "id": "https://openalex.org/W1",
                        "title": "First",
                        "doi": "https://doi.org/10.1234/a",
                    },
                    {"id": "https://openalex.org/W2", "title": "Second", "doi": None},
                ],
            },
        )

    result = OpenAlexSearchCapability(get=get).search(request(), context())
    assert [h.external_identifier for h in result.hits] == ["W1", "W2"]
    assert result.hits[0].url == "https://doi.org/10.1234/a"
    assert result.provider_request_id is None
    assert result.delivery_certainty is DeliveryCertainty.RESPONSE_RECEIVED
    assert result.warning_codes == ("RESULTS_TRUNCATED",)
    assert "per_page=2" in calls[0][0] and "search=CRISPR+Cas9" in calls[0][0]
    assert calls[0][2] <= 10


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"results": []},
        {"meta": {"count": 1}, "results": [{"id": "W1", "title": ""}]},
        {"meta": {"count": 1}, "results": [{"id": "A1", "title": "Wrong entity"}]},
    ],
)
def test_invalid_payload_rejected_without_partial_salvage(payload):
    with pytest.raises(ProviderError) as error:
        OpenAlexSearchCapability(get=lambda *args: HttpObservation(200, {}, payload)).search(
            request(), context()
        )
    assert error.value.code == "PROVIDER_MALFORMED"


def test_empty_result_is_success():
    result = OpenAlexSearchCapability(
        get=lambda *args: HttpObservation(200, {}, {"meta": {"count": 0}, "results": []})
    ).search(request(), context())
    assert result.hits == () and result.failure_code is None


def test_rate_limit_is_observed_and_not_retried_inside_adapter():
    calls = []

    def get(*args):
        calls.append(args)
        return HttpObservation(429, {"retry-after": "3"}, None)

    with pytest.raises(ProviderError) as error:
        OpenAlexSearchCapability(get=get).search(request(), context())
    assert len(calls) == 1 and error.value.retry_after_seconds == 3
    assert error.value.delivery_certainty is DeliveryCertainty.RESPONSE_RECEIVED


def test_timeout_is_uncertain_and_never_fabricates_cancellation():
    def get(*args):
        raise TimeoutError

    with pytest.raises(ProviderError) as error:
        OpenAlexSearchCapability(get=get).search(request(), context())
    assert error.value.delivery_certainty is DeliveryCertainty.MAY_HAVE_BEEN_SENT


def test_pre_dispatch_cancellation_proves_not_sent_only():
    def get(*args):
        pytest.fail("cancelled invocation dispatched")

    with pytest.raises(ProviderError) as error:
        OpenAlexSearchCapability(get=get).search(request(), context(True))
    assert error.value.delivery_certainty is DeliveryCertainty.NOT_SENT
    assert error.value.code != "PROVIDER_CANCELLED"
