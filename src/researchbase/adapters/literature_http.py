"""Bounded synchronous JSON GET transport, without response caching or redirects."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from http.client import HTTPException
from typing import Any
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from researchbase.domain.literature_search_execution import DeliveryCertainty


@dataclass(frozen=True, slots=True)
class HttpObservation:
    status: int
    headers: dict[str, str]
    body: Any
    payload_sha256: str | None = None
    payload_truncated: bool = False
    payload_failure: str | None = None


class HttpTransportFailure(Exception):
    """Sanitized transport failure with only the observed delivery fact."""

    def __init__(self, delivery_certainty: DeliveryCertainty) -> None:
        self.delivery_certainty = delivery_certainty
        super().__init__("HTTP_TRANSPORT_FAILURE")


class HttpTimeoutFailure(HttpTransportFailure, TimeoutError):
    """Sanitized timeout retaining the existing M2 timeout classification."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def get_json(url: str, headers: dict[str, str], timeout: float) -> HttpObservation:
    """No retries. A read timeout after dispatch cannot prove absence of processing."""
    started = time.monotonic()
    opener = None
    request = None
    local_failure = False
    try:
        opener = build_opener(_NoRedirect())
        request = Request(
            url,
            headers={"Accept": "application/json", "User-Agent": "ResearchBase-M2/1", **headers},
        )
    except Exception:
        local_failure = True
    if local_failure:
        raise HttpTransportFailure(DeliveryCertainty.NOT_SENT)
    assert opener is not None and request is not None
    open_failure = False
    open_timed_out = False
    response = None
    try:
        response = opener.open(request, timeout=timeout)
    except HTTPError as exc:
        response = exc
    except TimeoutError:
        open_timed_out = True
    except Exception:
        open_failure = True
    if open_timed_out:
        raise HttpTimeoutFailure(DeliveryCertainty.MAY_HAVE_BEEN_SENT)
    if open_failure:
        raise HttpTransportFailure(DeliveryCertainty.MAY_HAVE_BEEN_SENT)
    assert response is not None
    try:
        with response:
            status = response.code
            observed_headers = {key.lower(): value for key, value in response.headers.items()}
            chunks = []
            size = 0
            while True:
                try:
                    if time.monotonic() - started >= timeout:
                        raise TimeoutError
                    chunk = response.read(65536)
                except (OSError, HTTPException):
                    # Headers already arrived: this is never a response-less observation.
                    return HttpObservation(
                        status,
                        observed_headers,
                        None,
                        hashlib.sha256(b"".join(chunks)).hexdigest(),
                        True,
                        "INCOMPLETE_BODY",
                    )
                if not chunk:
                    break
                size += len(chunk)
                if size > 4 * 1024 * 1024:
                    return HttpObservation(
                        status,
                        observed_headers,
                        None,
                        hashlib.sha256(b"".join(chunks) + chunk).hexdigest(),
                        True,
                    )
                chunks.append(chunk)
            try:
                body = json.loads(b"".join(chunks))
            except (ValueError, UnicodeError):
                body = None
            return HttpObservation(
                status, observed_headers, body, hashlib.sha256(b"".join(chunks)).hexdigest()
            )
    except Exception:
        pass
    raise HttpTransportFailure(DeliveryCertainty.RESPONSE_RECEIVED)
