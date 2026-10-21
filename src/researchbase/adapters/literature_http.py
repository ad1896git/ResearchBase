"""Bounded synchronous JSON GET transport, without response caching or redirects."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import socket
import ssl
import time
from dataclasses import dataclass
from http.client import HTTPConnection, HTTPException, HTTPSConnection
from queue import Empty, Queue
from threading import Thread
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import (
    HTTPHandler,
    HTTPRedirectHandler,
    HTTPSHandler,
    ProxyHandler,
    Request,
    build_opener,
)

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


def _public_ip(value: str) -> bool:
    address = ipaddress.ip_address(value)
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        return _public_ip(str(address.ipv4_mapped))
    return address.is_global and not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_unspecified
        or address.is_reserved
    )


def _resolve_public_peer(url: str, timeout: float) -> tuple[str, str, int, str, str]:
    """Validate the whole answer set before selecting a numeric connection peer."""
    result = None
    try:
        if timeout <= 0 or any(ord(char) <= 32 or ord(char) == 127 for char in url):
            raise ValueError
        parsed = urlsplit(url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise ValueError
        host = parsed.hostname.encode("idna").decode("ascii")
        if "%" in host or "\\" in host:
            raise ValueError
        port = parsed.port if parsed.port is not None else (443 if parsed.scheme == "https" else 80)
        if not 1 <= port <= 65535 or parsed.netloc.endswith(":"):
            raise ValueError
        try:
            literal = ipaddress.ip_address(host)
        except ValueError:
            literal = None
        if literal is not None:
            peers = [str(literal)]
        else:
            # getaddrinfo has no timeout argument. Bound waiting without leaving a
            # non-daemon executor that could hold process shutdown on stalled DNS.
            # A timed-out lookup cannot be cancelled: its daemon survives until
            # getaddrinfo returns. Repeated stalled lookups can accumulate threads.
            answers: Queue[Any] = Queue(maxsize=1)

            def resolve() -> None:
                try:
                    answers.put(socket.getaddrinfo(host, port, type=socket.SOCK_STREAM))
                except Exception:
                    answers.put(None)

            Thread(target=resolve, daemon=True).start()
            records = answers.get(timeout=timeout)
            if not records:
                raise ValueError
            peers = [record[4][0] for record in records]
        if not peers or not all(_public_ip(peer) for peer in peers):
            raise ValueError
        authority = f"[{host}]" if ":" in host else host
        if port != (443 if parsed.scheme == "https" else 80):
            authority += f":{port}"
        # Select one validated peer; retain the transport's no-retry behavior.
        # An unreachable first answer fails rather than trying another address.
        result = (parsed.scheme, host, port, peers[0], authority)
    except (ValueError, UnicodeError, OSError, Empty):
        pass
    if result is None:
        raise HttpTransportFailure(DeliveryCertainty.NOT_SENT)
    return result


def _connect_peer(peer: str, port: int, timeout: float) -> socket.socket:
    # No create_connection/getaddrinfo here: DNS must never be consulted again.
    family = socket.AF_INET6 if ":" in peer else socket.AF_INET
    connection = socket.socket(family, socket.SOCK_STREAM)
    try:
        connection.settimeout(timeout)
        connection.connect((peer, port))
        return connection
    except BaseException:
        connection.close()
        raise


class _PinnedHTTPConnection(HTTPConnection):
    def __init__(self, host, *, peer, peer_port, **kwargs):
        super().__init__(host, **kwargs)
        self.peer, self.peer_port = peer, peer_port

    def connect(self):
        assert self.timeout is not None
        self.sock = _connect_peer(self.peer, self.peer_port, self.timeout)


class _PinnedHTTPSConnection(HTTPSConnection):
    def __init__(self, host, *, peer, peer_port, **kwargs):
        self.tls_context = ssl.create_default_context()
        super().__init__(host, context=self.tls_context, **kwargs)
        self.peer, self.peer_port = peer, peer_port

    def connect(self):
        assert self.timeout is not None
        connection = _connect_peer(self.peer, self.peer_port, self.timeout)
        try:
            self.sock = self.tls_context.wrap_socket(connection, server_hostname=self.host)
        except BaseException:
            connection.close()
            raise


class _PinnedHTTPHandler(HTTPHandler):
    def __init__(self, peer: str, port: int):
        super().__init__()
        self.peer, self.port = peer, port

    def http_open(self, req):
        return self.do_open(
            lambda host, **kw: _PinnedHTTPConnection(
                host, peer=self.peer, peer_port=self.port, **kw
            ),
            req,
        )


class _PinnedHTTPSHandler(HTTPSHandler):
    def __init__(self, peer: str, port: int):
        super().__init__()
        self.peer, self.port = peer, port

    def https_open(self, req):
        return self.do_open(
            lambda host, **kw: _PinnedHTTPSConnection(
                host, peer=self.peer, peer_port=self.port, **kw
            ),
            req,
        )


def get_json(url: str, headers: dict[str, str], timeout: float) -> HttpObservation:
    """No retries. A read timeout after dispatch cannot prove absence of processing."""
    started = time.monotonic()
    opener = None
    request = None
    local_failure = False
    try:
        request = Request(
            url,
            headers={"Accept": "application/json", "User-Agent": "ResearchBase-M2/1", **headers},
        )
        _, _, port, peer, authority = _resolve_public_peer(url, timeout)
        request.remove_header("Host")
        request.add_header("Host", authority)
        opener = build_opener(
            ProxyHandler({}),
            _NoRedirect(),
            _PinnedHTTPHandler(peer, port),
            _PinnedHTTPSHandler(peer, port),
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
        remaining = timeout - (time.monotonic() - started)
        if remaining <= 0:
            raise TimeoutError
        response = opener.open(request, timeout=remaining)
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
