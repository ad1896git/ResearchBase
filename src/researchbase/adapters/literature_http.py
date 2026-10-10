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


@dataclass(frozen=True, slots=True)
class HttpObservation:
    status: int
    headers: dict[str, str]
    body: Any
    payload_sha256: str | None = None
    payload_truncated: bool = False
    payload_failure: str | None = None


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def get_json(url: str, headers: dict[str, str], timeout: float) -> HttpObservation:
    """No retries. A read timeout after dispatch cannot prove absence of processing."""
    started = time.monotonic()
    opener = build_opener(_NoRedirect())
    request = Request(
        url, headers={"Accept": "application/json", "User-Agent": "ResearchBase-M2/1", **headers}
    )
    try:
        response = opener.open(request, timeout=timeout)
    except HTTPError as exc:
        response = exc
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
