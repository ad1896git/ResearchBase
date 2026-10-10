"""Bounded synchronous JSON GET transport, without response caching or redirects."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener


@dataclass(frozen=True, slots=True)
class HttpObservation:
    status: int
    headers: dict[str, str]
    body: Any


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
        if status != 200:
            return HttpObservation(status, observed_headers, None)
        chunks = []
        size = 0
        while True:
            if time.monotonic() - started >= timeout:
                raise TimeoutError
            chunk = response.read(65536)
            if not chunk:
                break
            size += len(chunk)
            if size > 4 * 1024 * 1024:
                raise ValueError("provider response exceeds byte limit")
            chunks.append(chunk)
        return HttpObservation(status, observed_headers, json.loads(b"".join(chunks)))
