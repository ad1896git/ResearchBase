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
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from researchbase.local_identity import process_uid

MAX_MESSAGE = 4096
PROTOCOL_VERSION = 1
_DURABLE = Path("/Users/onephone/ResearchBaseData")


@dataclass(frozen=True)
class RunnerProfile:
    tag: str
    installation_root: Path
    cas_root: Path
    policy_required: bool


def resolve_runner_profile(
    database_url: str, local_root: str | None, cas_root: str
) -> RunnerProfile:
    """Bind a trusted process to one exact retained deployment."""
    from sqlalchemy.engine import make_url

    url = make_url(database_url)
    if (
        url.drivername != "postgresql+psycopg"
        or url.username != "onephone"
        or url.password is not None
        or url.host is not None
        or url.port is not None
        or url.query.get("host") != "/private/tmp"
        or url.query.get("port") != "55440"
    ):
        raise ValueError("Runner requires the approved Unix-socket peer database")
    if url.database == "researchbase_m3_retained_20261011":
        if set(url.query) != {"host", "port"}:
            raise ValueError("M3 database URL contains unapproved options")
        profile = RunnerProfile(
            "m3-retained",
            _DURABLE / "rb-m3-retained-installation",
            _DURABLE / "rb-m3-retained-artifacts",
            True,
        )
    elif url.database in {f"researchbase_m2_{tag}" for tag in ("final", "live", "live2", "live3")}:
        tag = url.database.removeprefix("researchbase_m2_")
        profile = RunnerProfile(
            tag, _DURABLE / f"rb-m2-{tag}-installation", _DURABLE / f"rb-m2-{tag}-artifacts", False
        )
    else:
        raise ValueError("unsupported retained deployment")
    if local_root != str(profile.installation_root) or cas_root != str(profile.cas_root):
        raise ValueError("Runner installation and CAS roots do not match deployment")
    return profile


def verify_m3_storage(profile: RunnerProfile) -> None:
    """Reject path substitution before loading M3 installation secrets or CAS."""
    import stat

    for path in (_DURABLE, profile.installation_root, profile.cas_root):
        info = path.lstat()
        if (
            not stat.S_ISDIR(info.st_mode)
            or path.resolve() != path
            or info.st_uid != os.geteuid()
            or info.st_mode & 0o077
        ):
            raise ValueError("M3 storage is not private approved durable storage")


def require_coordinator(profile: RunnerProfile, coordinator: Any) -> Any:
    if profile.policy_required and coordinator is None:
        raise ValueError("M3 requires installed root-controlled HG1 policy")
    return coordinator


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
    if value["v"] == 2:
        return _validate_v2(value)
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


def _validate_v2(value: dict[str, Any]) -> dict[str, Any]:
    op = value.get("op")
    required = {
        "enrollment.challenge": set(),
        "enrollment.prove": {"challenge_id", "nonce"},
        "enrollment.attest": {"subject_uid", "proof_sha256", "reason"},
        "enrollment.provision": {"subject_uid", "display_name", "request_id"},
        "reviewer.assign": {"subject_uid", "project_id", "reason", "request_id"},
        "source.inspect": {"project_id", "source_version_id"},
        "evidence.get": {"project_id", "evidence_id"},
        "evidence.review": {"project_id", "evidence_id", "basis", "request_id"},
        "support.create": {
            "project_id",
            "target_type",
            "target_id",
            "evidence_id",
            "qualification",
            "request_id",
        },
    }
    optional = {"source.inspect": {"paragraph"}}
    if not isinstance(op, str) or op not in required:
        raise BadRequest("unknown operation")
    if not {"v", "op", *required[op]} <= value.keys() or value.keys() - {
        "v",
        "op",
        *required[op],
        *optional.get(op, set()),
    }:
        raise BadRequest("unknown or missing operation fields")
    for key in (
        "project_id",
        "source_version_id",
        "evidence_id",
        "request_id",
        "target_id",
        "challenge_id",
    ):
        if key in value:
            raw = value[key]
            if not isinstance(raw, str) or len(raw) != 36:
                raise BadRequest("invalid UUID")
            try:
                if str(UUID(raw)) != raw:
                    raise BadRequest("noncanonical UUID")
            except ValueError as exc:
                raise BadRequest("invalid UUID") from exc
    if "subject_uid" in value and (
        type(value["subject_uid"]) is not int or value["subject_uid"] <= 0
    ):
        raise BadRequest("invalid subject UID")
    for key, limit in (
        ("reason", 512),
        ("display_name", 200),
        ("basis", 4096),
        ("qualification", 4096),
    ):
        if key in value and (
            not isinstance(value[key], str) or not 1 <= len(value[key].strip()) <= limit
        ):
            raise BadRequest("invalid bounded text")
    for key in ("nonce", "proof_sha256"):
        if key in value and (
            not isinstance(value[key], str)
            or len(value[key]) != 64
            or any(char not in "0123456789abcdef" for char in value[key])
        ):
            raise BadRequest("invalid digest")
    if "paragraph" in value and (
        type(value["paragraph"]) is not int or not 1 <= value["paragraph"] <= 100000
    ):
        raise BadRequest("invalid paragraph")
    if "target_type" in value and (
        not isinstance(value["target_type"], str)
        or value["target_type"]
        not in {"ClaimVersion", "HypothesisVersion", "ResearchQuestionVersion"}
    ):
        raise BadRequest("invalid target type")
    return value


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


def dispatch(
    value: dict[str, Any], peer_uid: int, services: Any, owner_uid: int, coordinator: Any = None
) -> dict[str, Any]:
    request_value = _validate(value)
    if request_value["v"] == 2:
        if coordinator is None:
            raise Denied("HG1-02 authority is not configured")
        try:
            return coordinator.execute(peer_uid, request_value)
        except Denied:
            raise
        except Exception as exc:
            raise Denied("current canonical authority unavailable") from exc
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
        coordinator: Any = None,
        parent: Path = Path("/private/tmp"),
        max_requests: int = 32,
        lifetime_seconds: int = 60,
    ) -> None:
        if not 1 <= max_requests <= 32 or not 1 <= lifetime_seconds <= 60:
            raise ValueError("Runner lifetime or request count outside HG1-01 bounds")
        self.services = services
        self.coordinator = coordinator
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
                    response_version = PROTOCOL_VERSION
                    try:
                        uid, _gid = peer_credentials(connection)
                        if uid == 0 or (
                            uid != self.owner_uid
                            and (self.coordinator is None or not self.coordinator.allowed_uid(uid))
                        ):
                            self._safe_error(connection, "DENIED")
                            continue
                        handled += 1
                        value = read_request(connection, deadline=deadline)
                        response_version = value["v"]
                        if time.monotonic() >= deadline:
                            raise TimeoutError("Runner request deadline reached")
                        result = dispatch(
                            value, uid, self.services, self.owner_uid, self.coordinator
                        )
                        _send(connection, {"v": value["v"], "ok": True, "result": result})
                    except BadRequest:
                        self._safe_error(connection, "BAD_REQUEST", response_version)
                    except Exception:
                        self._safe_error(connection, "DENIED", response_version)
        finally:
            self.close()

    @staticmethod
    def _safe_error(connection: socket.socket, code: str, version: int = PROTOCOL_VERSION) -> None:
        try:
            _send(connection, {"v": version, "ok": False, "error": code})
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
        if not isinstance(result, dict) or result.get("v") != value.get("v"):
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
    from researchbase.cli.composition import build_services
    from researchbase.hg1_runtime import build_hg1_coordinator, verify_m3_server
    from researchbase.persistence.config import load_settings

    settings = load_settings()
    profile = resolve_runner_profile(
        settings.database_url,
        os.environ.get("RESEARCHBASE_LOCAL_ROOT"),
        settings.artifact_store_root,
    )
    if profile.policy_required:
        verify_m3_storage(profile)
        verify_m3_server(settings)
    services = build_services()
    coordinator = require_coordinator(
        profile, build_hg1_coordinator(profile.tag, services, settings)
    )
    server = RunnerServer(
        services,
        coordinator=coordinator,
        max_requests=args.max_requests,
        lifetime_seconds=args.lifetime_seconds,
    )
    path = server.start()
    print(path, flush=True)
    signal.signal(signal.SIGTERM, lambda _signum, _frame: server.stop())
    signal.signal(signal.SIGINT, lambda _signum, _frame: server.stop())
    server.serve()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
