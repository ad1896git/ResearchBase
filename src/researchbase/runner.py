"""HG1-01 short-lived local Runner; clients never receive database credentials."""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import signal
import socket
import struct
import sys
import tempfile
import time
from pathlib import Path
from typing import Any
from uuid import UUID

from researchbase.local_identity import process_uid

MAX_MESSAGE = 4096
PROTOCOL_VERSION = 1


class BadRequest(Exception):
    """A bounded client frame does not match the versioned protocol."""


class Denied(Exception):
    """Kernel identity or canonical application authority is unavailable."""


def peer_credentials(connection: socket.socket) -> tuple[int, int]:
    """Read peer effective UID/GID from macOS getpeereid(2), never from JSON."""
    if sys.platform != "darwin" or connection.family != socket.AF_UNIX:
        raise Denied("native Unix peer credentials unavailable")
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        getpeereid = libc.getpeereid
        getpeereid.argtypes = [
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_uint),
            ctypes.POINTER(ctypes.c_uint),
        ]
        getpeereid.restype = ctypes.c_int
        uid = ctypes.c_uint()
        gid = ctypes.c_uint()
        if getpeereid(connection.fileno(), ctypes.byref(uid), ctypes.byref(gid)) != 0:
            raise Denied("native Unix peer credentials unavailable")
        return uid.value, gid.value
    except (AttributeError, OSError, ValueError) as exc:
        raise Denied("native Unix peer credentials unavailable") from exc


def _exact(connection: socket.socket, size: int, deadline: float | None = None) -> bytes:
    chunks = bytearray()
    while len(chunks) < size:
        if deadline is not None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Runner request deadline reached")
            connection.settimeout(min(3, remaining))
        part = connection.recv(size - len(chunks))
        if not part:
            raise BadRequest("incomplete frame")
        chunks.extend(part)
    return bytes(chunks)


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise BadRequest("duplicate JSON key")
        result[key] = value
    return result


def _validate(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or type(value.get("v")) is not int:
        raise BadRequest("invalid request")
    if value["v"] != PROTOCOL_VERSION:
        raise BadRequest("unsupported protocol version")
    if value.get("op") == "whoami" and set(value) == {"v", "op"}:
        return value
    if value.get("op") == "project.get" and set(value) == {"v", "op", "project_id"}:
        identity = value["project_id"]
        if not isinstance(identity, str) or len(identity) != 36:
            raise BadRequest("invalid project ID")
        try:
            if str(UUID(identity)) != identity:
                raise BadRequest("invalid project ID")
        except ValueError as exc:
            raise BadRequest("invalid project ID") from exc
        return value
    raise BadRequest("unknown operation or fields")


def read_request(connection: socket.socket, *, deadline: float | None = None) -> dict[str, Any]:
    size = struct.unpack("!I", _exact(connection, 4, deadline))[0]
    if not 1 <= size <= MAX_MESSAGE:
        raise BadRequest("request too large or empty")
    try:
        value = json.loads(
            _exact(connection, size, deadline).decode("utf-8"), object_pairs_hook=_unique_pairs
        )
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise BadRequest("invalid JSON") from exc
    return _validate(value)


def _send(connection: socket.socket, value: dict[str, Any]) -> None:
    body = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(body) > MAX_MESSAGE:
        raise BadRequest("response too large")
    connection.sendall(struct.pack("!I", len(body)) + body)


def dispatch(value: dict[str, Any], peer_uid: int, services: Any, owner_uid: int) -> dict[str, str]:
    request_value = _validate(value)
    if peer_uid != owner_uid or peer_uid == 0:
        raise Denied("peer is not the bound installation owner")
    local = getattr(services, "local_identity", None)
    if local is None:
        raise Denied("local identity unavailable")
    try:
        principal = local.authenticate()  # Canonical binding and current credential check.
        if principal.subject_kind != "OS_UID" or principal.subject_value != str(peer_uid):
            raise Denied("peer and canonical binding differ")
        if request_value["op"] == "whoami":
            return {
                "actor_id": str(principal.actor_id),
                "deployment_id": principal.deployment_id,
            }
        project = services.application.get_project(UUID(request_value["project_id"]))
        # Application.get_project rechecks current membership/role in its transaction.
        return {
            "id": str(project.id),
            "name": project.name,
            "lifecycle_status": project.lifecycle_status.value,
        }
    except Denied:
        raise
    except Exception as exc:
        raise Denied("current canonical authority unavailable") from exc


class RunnerServer:
    """Foreground single-process server with one request per accepted connection."""

    def __init__(
        self,
        services: Any,
        *,
        parent: Path = Path("/private/tmp"),
        max_requests: int = 32,
        lifetime_seconds: int = 60,
    ) -> None:
        if not 1 <= max_requests <= 32 or not 1 <= lifetime_seconds <= 60:
            raise ValueError("Runner lifetime or request count outside HG1-01 bounds")
        self.services = services
        self.parent = parent
        self.max_requests = max_requests
        self.lifetime_seconds = lifetime_seconds
        self.owner_uid = process_uid()
        self.path: Path | None = None
        self._listener: socket.socket | None = None
        self._stopping = False

    def start(self) -> Path:
        if self.path is not None:
            raise RuntimeError("Runner already started")
        parent = self.parent.absolute()
        if parent.resolve() != parent or not parent.is_dir():
            raise Denied("unsafe socket parent")
        directory = Path(tempfile.mkdtemp(prefix="rb-hg1-01-", dir=parent))
        connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        path = directory / "runner.sock"
        try:
            connection.bind(str(path))
            connection.listen(8)
            connection.settimeout(0.2)
            path.chmod(0o666)
            directory.chmod(0o711)
            self.path = path
            self._listener = connection
            return path
        except Exception:
            connection.close()
            if path.exists():
                path.unlink()
            directory.rmdir()
            raise

    def serve(self) -> None:
        if self._listener is None:
            raise RuntimeError("Runner not started")
        deadline = time.monotonic() + self.lifetime_seconds
        handled = 0
        try:
            while (
                not self._stopping and handled < self.max_requests and time.monotonic() < deadline
            ):
                try:
                    connection, _ = self._listener.accept()
                except TimeoutError:
                    continue
                with connection:
                    try:
                        uid, _gid = peer_credentials(connection)
                        if uid != self.owner_uid or uid == 0:
                            self._safe_error(connection, "DENIED")
                            continue
                        handled += 1
                        value = read_request(connection, deadline=deadline)
                        if time.monotonic() >= deadline:
                            raise TimeoutError("Runner request deadline reached")
                        result = dispatch(value, uid, self.services, self.owner_uid)
                        _send(connection, {"v": PROTOCOL_VERSION, "ok": True, "result": result})
                    except BadRequest:
                        self._safe_error(connection, "BAD_REQUEST")
                    except (Denied, OSError, TimeoutError):
                        self._safe_error(connection, "DENIED")
        finally:
            self.close()

    @staticmethod
    def _safe_error(connection: socket.socket, code: str) -> None:
        try:
            _send(connection, {"v": PROTOCOL_VERSION, "ok": False, "error": code})
        except (OSError, TimeoutError):
            pass

    def stop(self) -> None:
        self._stopping = True

    def close(self) -> None:
        self._stopping = True
        if self._listener is not None:
            self._listener.close()
            self._listener = None
        if self.path is not None:
            if self.path.is_socket():
                self.path.unlink()
            self.path.parent.rmdir()
            self.path = None


def request(path: Path, value: dict[str, Any]) -> dict[str, Any]:
    """Unprivileged client: socket path and bounded JSON only, no database settings."""
    body = json.dumps(value, separators=(",", ":")).encode("utf-8")
    if not 1 <= len(body) <= MAX_MESSAGE:
        raise BadRequest("request too large or empty")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(3)
        connection.connect(str(path))
        connection.sendall(struct.pack("!I", len(body)) + body)
        size = struct.unpack("!I", _exact(connection, 4))[0]
        if not 1 <= size <= MAX_MESSAGE:
            raise BadRequest("invalid response size")
        result = json.loads(_exact(connection, size).decode("utf-8"))
        if not isinstance(result, dict) or result.get("v") != PROTOCOL_VERSION:
            raise BadRequest("invalid response")
        return result


def main() -> int:
    """Launch as trusted onephone only; no remote listener or daemonization."""
    parser = argparse.ArgumentParser(description="Short-lived HG1-01 local Runner")
    parser.add_argument("--max-requests", type=int, default=32)
    parser.add_argument("--lifetime-seconds", type=int, default=60)
    args = parser.parse_args()
    if sys.platform != "darwin" or process_uid() != 502:
        raise SystemExit("HG1-01 requires the trusted macOS onephone account")
    from sqlalchemy.engine import make_url

    from researchbase.cli.composition import build_services
    from researchbase.persistence.config import load_settings

    settings = load_settings()
    url = make_url(settings.database_url)
    if (
        url.drivername != "postgresql+psycopg"
        or url.username != "onephone"
        or url.password is not None
        or url.host is not None
        or url.query.get("host") != "/private/tmp"
        or url.query.get("port") != "55440"
        or url.database
        not in {f"researchbase_m2_{tag}" for tag in ("final", "live", "live2", "live3")}
    ):
        raise SystemExit("HG1-01 requires the existing M2 Unix-socket peer database")
    tag = url.database.removeprefix("researchbase_m2_")
    durable = Path("/Users/onephone/ResearchBaseData")
    if os.environ.get("RESEARCHBASE_LOCAL_ROOT") != str(
        durable / f"rb-m2-{tag}-installation"
    ) or settings.artifact_store_root != str(durable / f"rb-m2-{tag}-artifacts"):
        raise SystemExit("HG1-01 requires the durable matching M2 installation and CAS roots")
    services = build_services()
    server = RunnerServer(
        services, max_requests=args.max_requests, lifetime_seconds=args.lifetime_seconds
    )
    path = server.start()
    print(path, flush=True)
    signal.signal(signal.SIGTERM, lambda _signum, _frame: server.stop())
    signal.signal(signal.SIGINT, lambda _signum, _frame: server.stop())
    server.serve()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
