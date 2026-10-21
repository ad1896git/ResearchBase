"""Runner ceremony must bind B and C to separate kernel UIDs before writes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from researchbase.application.phase2_identity import VerifiedSubject
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.hg1_ceremony import HG1Coordinator
from researchbase.runner import Denied

A, B, C = uuid4(), uuid4(), uuid4()
DEPLOYMENT = "test-deployment"
NOW = datetime.now(UTC)


def _principal(actor, uid, credential):
    return VerifiedPrincipal(actor, DEPLOYMENT, "OS_UID", str(uid), credential, NOW)


@dataclass
class Policy:
    signed_digest: str | None = None
    valid: bool = True
    operator_uid: int = 503

    def record(self, uid):
        return {
            501: SimpleNamespace(actor_id=A, credential_id="a"),
            502: SimpleNamespace(actor_id=B, credential_id="b"),
            503: SimpleNamespace(actor_id=C, credential_id="c"),
        }[uid]

    def subject(self, uid):
        if not self.valid:
            raise Denied("credential expired")
        return VerifiedSubject(DEPLOYMENT, "OS_UID", str(uid), self.record(uid).credential_id)

    def authenticate_subject(self, uid):
        if uid != 502 or not self.valid:
            raise Denied("no current B binding")
        return _principal(B, 502, "b")

    def is_valid(self, principal, _at):
        return (
            self.valid
            and principal.credential_id == self.record(int(principal.subject_value)).credential_id
        )

    def is_allowlisted(self, principal):
        return principal.actor_id == C and principal.subject_value == "503"

    def verify(self, attestation):
        return self.valid and attestation.proof_sha256 == "a" * 64

    def proof_material(self, attestation):
        if not self.verify(attestation):
            return None
        return {
            "subject_live_proof_sha256": self.signed_digest,
            "signed_at": datetime.now(UTC).isoformat(),
        }

    @property
    def deployment_id(self):
        return DEPLOYMENT

    @property
    def audit_root(self):
        from pathlib import Path

        return Path("/approved/audit")


class Identity:
    def __init__(self):
        self.provisioned = []
        self.assigned = []

    def provision_actor(self, command):
        self.provisioned.append(command)
        return command.actor_id

    def assign_project_role(self, command):
        self.assigned.append(command)
        return uuid4()


class Reviews:
    def __init__(self):
        self.calls = []

    def inspect(self, principal, payload):
        self.calls.append(("inspect", principal.actor_id))
        return {"ok": "read"}

    def review_verified(self, principal, payload):
        self.calls.append(("review", principal.actor_id))
        return {"ok": "review"}

    def create_support(self, principal, payload):
        self.calls.append(("support", principal.actor_id))
        return {"ok": "support"}


def _coordinator():
    policy, identity, reviews = Policy(), Identity(), Reviews()
    owner = SimpleNamespace(authenticate=lambda: _principal(A, 501, "a"))
    return (
        HG1Coordinator(policy, identity, reviews, owner, owner_uid=501),
        policy,
        identity,
        reviews,
    )


def test_b_live_proof_c_signed_attestation_a_provisions_and_assigns_reviewer():
    coordinator, policy, identity, _ = _coordinator()
    challenge = coordinator.execute(502, {"v": 2, "op": "enrollment.challenge"})
    proved = coordinator.execute(
        502,
        {
            "v": 2,
            "op": "enrollment.prove",
            "challenge_id": challenge["challenge_id"],
            "nonce": challenge["nonce"],
        },
    )
    policy.signed_digest = proved["live_proof_sha256"]
    coordinator.execute(
        503,
        {
            "v": 2,
            "op": "enrollment.attest",
            "subject_uid": 502,
            "proof_sha256": "a" * 64,
            "reason": "independent identity evidence",
        },
    )
    provisioned = coordinator.execute(
        501,
        {
            "v": 2,
            "op": "enrollment.provision",
            "subject_uid": 502,
            "display_name": "B",
            "request_id": str(uuid4()),
        },
    )
    assert provisioned["actor_id"] == str(B)
    assert identity.provisioned[0].owner.actor_id == A
    assert identity.provisioned[0].subject.subject_value == "502"
    assert identity.provisioned[0].attestation.operator.actor_id == C
    coordinator.execute(
        501,
        {
            "v": 2,
            "op": "reviewer.assign",
            "subject_uid": 502,
            "project_id": str(uuid4()),
            "reason": "review duty",
            "request_id": str(uuid4()),
        },
    )
    assert identity.assigned[0].role == "REVIEWER"
    assert identity.assigned[0].actor_id == B


def test_cross_uid_replay_and_unsigned_proof_fail_before_application_write():
    coordinator, policy, identity, _ = _coordinator()
    challenge = coordinator.execute(502, {"v": 2, "op": "enrollment.challenge"})
    with pytest.raises(Denied):
        coordinator.execute(
            503,
            {
                "v": 2,
                "op": "enrollment.prove",
                "challenge_id": challenge["challenge_id"],
                "nonce": challenge["nonce"],
            },
        )
    proved = coordinator.execute(
        502,
        {
            "v": 2,
            "op": "enrollment.prove",
            "challenge_id": challenge["challenge_id"],
            "nonce": challenge["nonce"],
        },
    )
    with pytest.raises(Denied):
        coordinator.execute(
            502,
            {
                "v": 2,
                "op": "enrollment.prove",
                "challenge_id": challenge["challenge_id"],
                "nonce": challenge["nonce"],
            },
        )
    policy.signed_digest = "0" * 64
    with pytest.raises(Denied):
        coordinator.execute(
            503,
            {
                "v": 2,
                "op": "enrollment.attest",
                "subject_uid": 502,
                "proof_sha256": "a" * 64,
                "reason": "independent identity evidence",
            },
        )
    with pytest.raises(Denied):
        coordinator.execute(
            501,
            {
                "v": 2,
                "op": "enrollment.provision",
                "subject_uid": 502,
                "display_name": "B",
                "request_id": str(uuid4()),
            },
        )
    assert proved["live_proof_sha256"] != policy.signed_digest
    assert identity.provisioned == []


def test_review_is_b_only_support_is_a_only_and_current_binding_required():
    coordinator, policy, _identity, reviews = _coordinator()
    assert coordinator.execute(502, {"v": 2, "op": "evidence.review"}) == {"ok": "review"}
    assert coordinator.execute(501, {"v": 2, "op": "support.create"}) == {"ok": "support"}
    with pytest.raises(Denied):
        coordinator.execute(501, {"v": 2, "op": "evidence.review"})
    with pytest.raises(Denied):
        coordinator.execute(502, {"v": 2, "op": "support.create"})
    policy.valid = False
    assert not coordinator.allowed_uid(502)
    with pytest.raises(Denied):
        coordinator.execute(502, {"v": 2, "op": "source.inspect"})
    assert reviews.calls == [("review", B), ("support", A)]
