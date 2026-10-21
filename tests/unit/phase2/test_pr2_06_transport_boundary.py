"""Disconnected transport certainty and secret-boundary regressions."""

import asyncio
import traceback
from urllib.error import URLError

import pytest

from researchbase.adapters import literature_http
from researchbase.adapters.crossref import CrossrefVerifier
from researchbase.adapters.literature_http import HttpObservation, HttpTransportFailure
from researchbase.adapters.openalex import OpenAlexSearchCapability
from researchbase.application.literature_search_provider import (
    ProviderError,
    ProviderFailureKind,
)
from researchbase.domain.literature_search_execution import DeliveryCertainty
from tests.unit.test_m2_openalex import context, request

SECRET = "synthetic-token-never-log"


@pytest.fixture(autouse=True)
def public_dns(monkeypatch):
    monkeypatch.setattr(
        literature_http.socket,
        "getaddrinfo",
        lambda *_a, **_kw: [
            (2, 1, 6, "", ("8.8.8.8", 443)),
        ],
    )


def _raising(error):
    def get(*_):
        raise error

    return get


@pytest.mark.parametrize(
    "certainty,kind,code",
    [
        (DeliveryCertainty.NOT_SENT, ProviderFailureKind.RETRYABLE, "PROVIDER_TRANSIENT"),
        (
            DeliveryCertainty.MAY_HAVE_BEEN_SENT,
            ProviderFailureKind.UNCERTAIN,
            "PROVIDER_OUTCOME_UNKNOWN",
        ),
        (
            DeliveryCertainty.RESPONSE_RECEIVED,
            ProviderFailureKind.RETRYABLE,
            "PROVIDER_TRANSIENT",
        ),
    ],
)
def test_confirmed_transport_phase_maps_to_safe_provider_failure(certainty, kind, code):
    capability = OpenAlexSearchCapability(
        api_key=SECRET, get=_raising(HttpTransportFailure(certainty))
    )
    with pytest.raises(ProviderError) as caught:
        capability.search(request(), context())
    error = caught.value
    assert (error.delivery_certainty, error.kind, error.code) == (certainty, kind, code)
    assert error.__cause__ is None and error.__context__ is None
    assert SECRET not in "".join(traceback.format_exception(error))


@pytest.mark.parametrize("error", [ValueError(SECRET), UnicodeError(SECRET), TimeoutError(SECRET)])
def test_unclassified_transport_exception_is_unknown_and_has_no_raw_chain(error):
    capability = OpenAlexSearchCapability(api_key=SECRET, get=_raising(error))
    with pytest.raises(ProviderError) as caught:
        capability.search(request(), context())
    normalized = caught.value
    assert normalized.kind is ProviderFailureKind.UNCERTAIN
    assert normalized.delivery_certainty is DeliveryCertainty.MAY_HAVE_BEEN_SENT
    assert normalized.code == "PROVIDER_OUTCOME_UNKNOWN"
    assert normalized.__cause__ is None and normalized.__context__ is None
    assert SECRET not in "".join(traceback.format_exception(normalized))


def test_confirmed_response_parse_failure_has_no_raw_secret_chain():
    capability = OpenAlexSearchCapability(
        api_key=SECRET,
        get=lambda *_: HttpObservation(
            200, {"x-request-id": "safe-id"}, {"meta": {"count": 1}, "results": [{"id": SECRET}]}
        ),
    )
    with pytest.raises(ProviderError) as caught:
        capability.search(request(), context())
    error = caught.value
    assert error.code == "PROVIDER_MALFORMED"
    assert error.delivery_certainty is DeliveryCertainty.RESPONSE_RECEIVED
    assert error.provider_request_id == "safe-id"
    assert error.__cause__ is None and error.__context__ is None
    assert SECRET not in "".join(traceback.format_exception(error))


def test_request_id_cannot_carry_sensitive_url_into_public_diagnostics():
    capability = OpenAlexSearchCapability(
        get=lambda *_: HttpObservation(
            429,
            {"x-request-id": "https://example.invalid/?api_key=" + SECRET},
            None,
        )
    )
    with pytest.raises(ProviderError) as caught:
        capability.search(request(), context())
    assert caught.value.provider_request_id is None
    assert SECRET not in repr(caught.value)


def test_confirmed_http_503_remains_retryable_with_response_receipt():
    capability = OpenAlexSearchCapability(
        get=lambda *_: HttpObservation(503, {"x-request-id": "safe-id"}, None)
    )
    with pytest.raises(ProviderError) as caught:
        capability.search(request(), context())
    assert caught.value.code == "PROVIDER_TRANSIENT"
    assert caught.value.kind is ProviderFailureKind.RETRYABLE
    assert caught.value.delivery_certainty is DeliveryCertainty.RESPONSE_RECEIVED
    assert caught.value.provider_request_id == "safe-id"


def test_cancelled_transport_task_propagates_without_false_confirmation():
    capability = OpenAlexSearchCapability(get=_raising(asyncio.CancelledError()))
    with pytest.raises(asyncio.CancelledError):
        capability.search(request(), context())


def test_local_request_construction_failure_is_not_sent_and_secret_free(monkeypatch):
    def fail_request(*_, **__):
        raise ValueError(SECRET)

    monkeypatch.setattr(literature_http, "Request", fail_request)
    with pytest.raises(HttpTransportFailure) as caught:
        literature_http.get_json("https://api.openalex.org/works", {"Authorization": SECRET}, 1)
    assert caught.value.delivery_certainty is DeliveryCertainty.NOT_SENT
    assert caught.value.__cause__ is None and caught.value.__context__ is None
    assert SECRET not in "".join(traceback.format_exception(caught.value))


def test_open_failure_without_response_is_uncertain_and_secret_free(monkeypatch):
    class FakeOpener:
        def open(self, *_args, **_kwargs):
            raise URLError(SECRET)

    monkeypatch.setattr(literature_http, "build_opener", lambda *_: FakeOpener())
    with pytest.raises(HttpTransportFailure) as caught:
        literature_http.get_json("https://api.openalex.org/works", {"Authorization": SECRET}, 1)
    assert caught.value.delivery_certainty is DeliveryCertainty.MAY_HAVE_BEEN_SENT
    assert caught.value.__cause__ is None and caught.value.__context__ is None
    assert SECRET not in "".join(traceback.format_exception(caught.value))


def test_confirmed_headers_followed_by_body_interruption_keep_receipt(monkeypatch):
    class FakeResponse:
        code = 200
        headers = {"Content-Type": "application/json"}

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self, _size):
            raise ConnectionError(SECRET)

    class FakeOpener:
        def open(self, *_args, **_kwargs):
            return FakeResponse()

    monkeypatch.setattr(literature_http, "build_opener", lambda *_: FakeOpener())
    observation = literature_http.get_json("https://api.openalex.org/works", {}, 1)
    assert observation.payload_failure == "INCOMPLETE_BODY"
    assert observation.status == 200
    assert observation.body is None


def test_crossref_m2_timeout_classification_is_preserved(monkeypatch):
    class FakeOpener:
        def open(self, *_args, **_kwargs):
            raise TimeoutError(SECRET)

    monkeypatch.setattr(literature_http, "build_opener", lambda *_: FakeOpener())
    result = CrossrefVerifier().observe("10.1234/example", "Example")
    assert result["failure_code"] == "TRANSPORT_TIMEOUT"
    assert SECRET not in repr(result)
