"""One short-lived B/C/A ceremony over kernel-authenticated local peers."""

from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from researchbase.application.phase2_identity import (
    AssignProjectRole,
    ProvisionActor,
    ProvisioningAttestation,
)
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.runner import Denied


def _uuid(value: object) -> UUID:
    if not isinstance(value, str):
        raise Denied("invalid UUID")
    try:
        result = UUID(value)
    except ValueError as exc:
        raise Denied("invalid UUID") from exc
    if str(result) != value:
        raise Denied("noncanonical UUID")
    return result


def _bounded(value: object, limit: int) -> str:
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= limit:
        raise Denied("invalid bounded text")
    return value


@dataclass
class _Proof:
    challenge_id: UUID
    nonce: bytes
    issued_at: datetime
    live_digest: str | None = None
    attestation: ProvisioningAttestation | None = None


class HG1Coordinator:
    """Trusted orchestrator; Application remains the sole canonical write path."""

    def __init__(self, policy: Any, identity: Any, reviews: Any, owner: Any, *, owner_uid: int):
        if owner_uid <= 0 or owner_uid == policy.operator_uid:
            raise ValueError("owner and independent operator must differ")
        self.policy = policy
        self.identity = identity
        self.reviews = reviews
        self.owner = owner
        self.owner_uid = owner_uid
        self._proofs: dict[int, _Proof] = {}

    def allowed_uid(self, uid: int) -> bool:
        try:
            return uid > 0 and self.policy.subject(uid) is not None
        except Exception:
            return False

    def _owner_principal(self, uid: int) -> VerifiedPrincipal:
        if uid != self.owner_uid:
            raise Denied("owner peer required")
        principal = self.owner.authenticate()
        record = self.policy.record(uid)
        if (
            principal.actor_id != record.actor_id
            or principal.subject_kind != "OS_UID"
            or principal.subject_value != str(uid)
            or principal.deployment_id != self.policy.deployment_id
            or not self.policy.is_valid(principal, datetime.now(UTC))
        ):
            raise Denied("owner identity mismatch")
        return principal

    def _operator_principal(self, uid: int) -> VerifiedPrincipal:
        if uid != self.policy.operator_uid or uid == self.owner_uid:
            raise Denied("independent operator peer required")
        record = self.policy.record(uid)
        principal = VerifiedPrincipal(
            record.actor_id,
            self.policy.deployment_id,
            "OS_UID",
            str(uid),
            record.credential_id,
            datetime.now(UTC),
        )
        if not self.policy.is_allowlisted(principal):
            raise Denied("operator credential unavailable")
        return principal

    def _review_principal(self, uid: int) -> VerifiedPrincipal:
        if uid in {self.owner_uid, self.policy.operator_uid}:
            raise Denied("independent reviewer peer required")
        return self.policy.authenticate_subject(uid)

    def _live_proof(self, uid: int) -> _Proof:
        proof = self._proofs.get(uid)
        if (
            proof is None
            or datetime.now(UTC) - proof.issued_at > timedelta(seconds=60)
            or proof.live_digest is None
        ):
            raise Denied("fresh subject peer proof unavailable")
        return proof

    def execute(self, peer_uid: int, value: dict[str, Any]) -> dict[str, Any]:
        if not self.allowed_uid(peer_uid) or value.get("v") != 2:
            raise Denied("untrusted peer or protocol")
        op = value.get("op")
        if op == "enrollment.challenge":
            if peer_uid in {self.owner_uid, self.policy.operator_uid}:
                raise Denied("independent subject peer required")
            self.policy.subject(peer_uid)
            proof = _Proof(uuid4(), secrets.token_bytes(32), datetime.now(UTC))
            self._proofs[peer_uid] = proof
            return {"challenge_id": str(proof.challenge_id), "nonce": proof.nonce.hex()}
        if op == "enrollment.prove":
            if peer_uid in {self.owner_uid, self.policy.operator_uid}:
                raise Denied("independent subject peer required")
            proof = self._proofs.get(peer_uid)
            if (
                proof is None
                or proof.live_digest is not None
                or datetime.now(UTC) - proof.issued_at > timedelta(seconds=60)
                or _uuid(value.get("challenge_id")) != proof.challenge_id
                or value.get("nonce") != proof.nonce.hex()
            ):
                raise Denied("subject challenge response unavailable")
            subject = self.policy.subject(peer_uid)
            record = self.policy.record(peer_uid)
            material = {
                "actor_id": str(record.actor_id),
                "challenge_id": str(proof.challenge_id),
                "deployment_id": subject.deployment_id,
                "nonce": proof.nonce.hex(),
                "subject_credential_id": subject.credential_id,
                "subject_kind": subject.subject_kind,
                "subject_value": subject.subject_value,
            }
            proof.live_digest = hashlib.sha256(
                json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            return {"live_proof_sha256": proof.live_digest}
        if op == "enrollment.attest":
            operator = self._operator_principal(peer_uid)
            subject_uid = value.get("subject_uid")
            if type(subject_uid) is not int or subject_uid in {self.owner_uid, peer_uid}:
                raise Denied("invalid independent subject")
            proof = self._live_proof(subject_uid)
            subject = self.policy.subject(subject_uid)
            digest = value.get("proof_sha256")
            if (
                not isinstance(digest, str)
                or len(digest) != 64
                or any(char not in "0123456789abcdef" for char in digest)
            ):
                raise Denied("invalid signed proof digest")
            attestation = ProvisioningAttestation(
                actor_id=self.policy.record(subject_uid).actor_id,
                deployment_id=subject.deployment_id,
                subject_kind=subject.subject_kind,
                subject_value=subject.subject_value,
                subject_credential_id=subject.credential_id,
                operator=operator,
                proof_sha256=digest,
                proof_record_ref=str(self.policy.audit_root / f"proof-{digest}.json"),
                reason=_bounded(value.get("reason"), 512),
            )
            material = self.policy.proof_material(attestation)
            if (
                material is None
                or material.get("subject_live_proof_sha256") != proof.live_digest
                or datetime.fromisoformat(material["signed_at"]) < proof.issued_at
            ):
                raise Denied("C attestation does not bind the live B peer proof")
            proof.attestation = attestation
            return {"proof_sha256": digest}
        if op == "enrollment.provision":
            owner = self._owner_principal(peer_uid)
            subject_uid = value.get("subject_uid")
            if type(subject_uid) is not int or subject_uid in {
                self.owner_uid,
                self.policy.operator_uid,
            }:
                raise Denied("invalid independent subject")
            proof = self._live_proof(subject_uid)
            if proof.attestation is None:
                raise Denied("independent attestation unavailable")
            material = self.policy.proof_material(proof.attestation)
            if material is None or material.get("subject_live_proof_sha256") != proof.live_digest:
                raise Denied("attestation is no longer valid")
            record = self.policy.record(subject_uid)
            actor_id = self.identity.provision_actor(
                ProvisionActor(
                    owner=owner,
                    subject=self.policy.subject(subject_uid),
                    actor_id=record.actor_id,
                    display_name=_bounded(value.get("display_name"), 200),
                    attestation=proof.attestation,
                    request_id=_uuid(value.get("request_id")),
                )
            )
            del self._proofs[subject_uid]
            return {"actor_id": str(actor_id)}
        if op == "reviewer.assign":
            owner = self._owner_principal(peer_uid)
            subject_uid = value.get("subject_uid")
            if type(subject_uid) is not int or subject_uid in {
                self.owner_uid,
                self.policy.operator_uid,
            }:
                raise Denied("invalid reviewer")
            reviewer = self.policy.authenticate_subject(subject_uid)
            assignment_id = self.identity.assign_project_role(
                AssignProjectRole(
                    principal=owner,
                    project_id=_uuid(value.get("project_id")),
                    actor_id=reviewer.actor_id,
                    role="REVIEWER",
                    reason=_bounded(value.get("reason"), 512),
                    request_id=_uuid(value.get("request_id")),
                )
            )
            return {"role_assignment_id": str(assignment_id)}
        payload = {key: item for key, item in value.items() if key not in {"v", "op"}}
        if op in {"source.inspect", "evidence.get"}:
            principal = (
                self._owner_principal(peer_uid)
                if peer_uid == self.owner_uid
                else self._review_principal(peer_uid)
            )
            return self.reviews.inspect(principal, payload)
        if op == "evidence.review":
            return self.reviews.review_verified(self._review_principal(peer_uid), payload)
        if op == "support.create":
            return self.reviews.create_support(self._owner_principal(peer_uid), payload)
        raise Denied("unknown operation")
