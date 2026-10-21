"""HG1-01 Runner contract and native peer security tests."""

from __future__ import annotations

import json
import os
import socket
import struct
import sys
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from researchbase.runner import (
    BadRequest,
    Denied,
    RunnerServer,
    dispatch,
    peer_credentials,
    read_request,
    request,
)

PROJECT = UUID("3a850c58-07b2-47e7-a425-750409a920b1")
ACTOR = UUID("c1dcc0ef-6bc4-4627-9a9c-96ffce30f3cf")


@dataclass
class Local:
    calls: int = 0

    def authenticate(self):
        self.calls += 1
        return SimpleNamespace(
            actor_id=ACTOR,
            deployment_id="local-test",
            subject_kind="OS_UID",
            subject_value=str(os.geteuid()),
            credential_id="os-test",
        )


@dataclass
class Application:
    calls: int = 0

    def get_project(self, project_id):
        self.calls += 1
        assert project_id == PROJECT
        return SimpleNamespace(
            id=PROJECT, name="Test", lifecycle_status=SimpleNamespace(value="ACTIVE")
        )


def services():
    return SimpleNamespace(local_identity=Local(), application=Application())


def frame(payload: bytes) -> bytes:
    return struct.pack("!I", len(payload)) + payload


@pytest.mark.skipif(
    sys.platform != "darwin",
    reason="HG1-01 native peer credentials require the trusted macOS host (getpeereid).",
)
def test_kernel_peer_credentials_are_real_for_socketpair():
    left, right = socket.socketpair()
    try:
        assert peer_credentials(left) == (os.geteuid(), os.getegid())
    finally:
        left.close()
        right.close()


def test_invalid_peer_socket_fails_closed():
    left, right = socket.socketpair()
    left.close()
    right.close()
    with pytest.raises(Denied):
        peer_credentials(left)


@pytest.mark.parametrize(
    "payload",
    [
        b'{"v":1,"op":"whoami","actor_id":"spoof"}',
        b'{"v":1,"op":"whoami","uid":502}',
        b'{"v":1,"op":"whoami","principal":"owner"}',
        b'{"v":1,"op":"whoami","credential_id":"os-forged"}',
        b'{"v":1,"op":"whoami","deployment_id":"forged"}',
        b'{"v":1,"op":"whoami","role":"OWNER"}',
        b'{"v":1,"op":"whoami","op":"project.get"}',
        b'{"v":true,"op":"whoami"}',
        b'{"v":2,"op":"whoami"}',
        b'{"v":1,"op":"unknown"}',
        b'{"v":1,"op":"project.get","project_id":"../../../etc/passwd"}',
    ],
)
def test_protocol_rejects_untrusted_authority_and_invalid_messages(payload):
    left, right = socket.socketpair()
    try:
        right.sendall(frame(payload))
        with pytest.raises(BadRequest):
            read_request(left)
    finally:
        left.close()
        right.close()


def test_protocol_rejects_oversize_before_reading_body():
    left, right = socket.socketpair()
    try:
        right.sendall(struct.pack("!I", 4097))
        with pytest.raises(BadRequest):
            read_request(left)
    finally:
        left.close()
        right.close()


def test_v2_protocol_has_exact_bounded_operations_and_no_identity_claims():
    accepted = {"v": 2, "op": "enrollment.challenge"}
    left, right = socket.socketpair()
    try:
        right.sendall(frame(json.dumps(accepted).encode()))
        assert read_request(left) == accepted
    finally:
        left.close()
        right.close()
    for bad in (
        {"v": 2, "op": "enrollment.challenge", "actor_id": str(ACTOR)},
        {
            "v": 2,
            "op": "enrollment.attest",
            "subject_uid": 502,
            "proof_sha256": "a" * 64,
            "reason": "proof",
            "operator_actor_id": str(ACTOR),
        },
        {
            "v": 2,
            "op": "evidence.review",
            "project_id": str(PROJECT),
            "evidence_id": str(ACTOR),
            "basis": "basis",
            "request_id": str(PROJECT),
            "principal": "owner",
        },
    ):
        left, right = socket.socketpair()
        try:
            right.sendall(frame(json.dumps(bad).encode()))
            with pytest.raises(BadRequest):
                read_request(left)
        finally:
            left.close()
            right.close()


def test_v2_dispatch_uses_server_coordinator_and_never_owner_fallback():
    class Coordinator:
        def __init__(self):
            self.calls = []

        def execute(self, uid, value):
            self.calls.append((uid, value))
            return {"accepted_uid": uid}

    coordinator = Coordinator()
    payload = {"v": 2, "op": "enrollment.challenge"}
    assert dispatch(payload, 60001, services(), os.geteuid(), coordinator) == {
        "accepted_uid": 60001
    }
    assert coordinator.calls == [(60001, payload)]
    with pytest.raises(Denied):
        dispatch(payload, os.geteuid(), services(), os.geteuid())


@pytest.mark.skipif(
    sys.platform != "darwin",
    reason="HG1-01 native peer credentials require the trusted macOS host (getpeereid).",
)
def test_v2_denial_keeps_versioned_fail_closed_response():
    class Coordinator:
        def allowed_uid(self, uid):
            return uid == os.geteuid()

        def execute(self, _uid, _value):
            raise Denied("no current authority")

    server = RunnerServer(
        services(), coordinator=Coordinator(), parent=Path("/private/tmp"), max_requests=1
    )
    path = server.start()
    thread = threading.Thread(target=server.serve)
    thread.start()
    try:
        result = request(path, {"v": 2, "op": "enrollment.challenge"})
        assert result == {"v": 2, "ok": False, "error": "DENIED"}
    finally:
        thread.join(timeout=3)
        server.stop()


def test_other_peer_uid_never_reaches_application():
    bundle = services()
    with pytest.raises(Denied):
        dispatch({"v": 1, "op": "whoami"}, os.geteuid() + 1, bundle, os.geteuid())
    assert bundle.local_identity.calls == 0
    assert bundle.application.calls == 0


def test_authenticated_owner_uses_existing_application_services():
    bundle = services()
    who = dispatch({"v": 1, "op": "whoami"}, os.geteuid(), bundle, os.geteuid())
    project = dispatch(
        {"v": 1, "op": "project.get", "project_id": str(PROJECT)},
        os.geteuid(),
        bundle,
        os.geteuid(),
    )
    assert who == {"actor_id": str(ACTOR), "deployment_id": "local-test"}
    assert project == {"id": str(PROJECT), "name": "Test", "lifecycle_status": "ACTIVE"}
    assert bundle.local_identity.calls == 2
    assert bundle.application.calls == 1


@pytest.mark.skipif(
    sys.platform != "darwin",
    reason="HG1-01 native peer credentials require the trusted macOS host (getpeereid).",
)
def test_socket_lifecycle_one_request_and_cleanup():
    server = RunnerServer(
        services(), parent=Path("/private/tmp"), max_requests=1, lifetime_seconds=5
    )
    path = server.start()
    assert path.is_socket()
    assert path.parent.stat().st_mode & 0o777 == 0o711
    assert path.stat().st_mode & 0o777 == 0o666
    thread = threading.Thread(target=server.serve)
    thread.start()
    result = request(path, {"v": 1, "op": "whoami"})
    thread.join(timeout=5)
    assert not thread.is_alive()
    assert result["ok"] is True
    assert not path.exists()
    assert not path.parent.exists()


def test_foreign_peer_policy_denies_before_frame_without_using_request_slot(monkeypatch):
    # Policy test only: this does not replace a real distinct-UID host test.
    import researchbase.runner as runner

    peers = iter(((os.geteuid() + 1, os.getegid()), (os.geteuid(), os.getegid())))
    monkeypatch.setattr(runner, "peer_credentials", lambda _connection: next(peers))
    server = RunnerServer(
        services(), parent=Path(tempfile.gettempdir()).resolve(), max_requests=1, lifetime_seconds=5
    )
    path = server.start()
    thread = threading.Thread(target=server.serve)
    thread.start()
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as foreign:
            foreign.settimeout(0.5)
            foreign.connect(str(path))
            size = struct.unpack("!I", foreign.recv(4))[0]
            denied = json.loads(foreign.recv(size))
            assert denied == {"v": 1, "ok": False, "error": "DENIED"}
        allowed = request(path, {"v": 1, "op": "whoami"})
        assert allowed["ok"] is True
        thread.join(timeout=2)
        assert not thread.is_alive()
    finally:
        server.stop()
        thread.join(timeout=4)


@pytest.mark.skipif(
    sys.platform != "darwin",
    reason="HG1-01 native peer credentials require the trusted macOS host (getpeereid).",
)
def test_incomplete_owner_frame_cannot_extend_runner_past_deadline():
    server = RunnerServer(
        services(), parent=Path("/private/tmp"), max_requests=1, lifetime_seconds=1
    )
    path = server.start()
    thread = threading.Thread(target=server.serve)
    thread.start()
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as stalled:
            stalled.connect(str(path))
            thread.join(timeout=1.8)
            assert not thread.is_alive()
    finally:
        server.stop()
        thread.join(timeout=4)
