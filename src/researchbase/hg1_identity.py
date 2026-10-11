"""Trusted, deployment-scoped peer and independent operator proof adapter.

The Runner supplies the kernel UID. These records are trusted deployment inputs,
never fields from a client request. The operator private signing key is absent.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import stat
import subprocess
import tempfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

from researchbase.application.phase2_identity import (
    OnboardingAttestation,
    ProvisioningAttestation,
    VerifiedSubject,
)
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


def _denied() -> ResearchBaseError:
    return ResearchBaseError(
        ErrorCode.AUTHENTICATION_REQUIRED, "trusted peer authority unavailable"
    )


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


@dataclass(frozen=True, slots=True)
class PeerCredential:
    uid: int
    actor_id: UUID
    credential_id: str
    not_before: datetime
    not_after: datetime | None

    def __post_init__(self) -> None:
        if self.uid <= 0 or isinstance(self.uid, bool) or not self.credential_id.strip():
            raise ValueError("invalid trusted peer credential")
        if self.not_before.tzinfo is None or (self.not_after and self.not_after.tzinfo is None):
            raise ValueError("credential dates require a timezone")
        if self.not_after is not None and self.not_after <= self.not_before:
            raise ValueError("credential validity interval is empty")


class TrustedPeerIdentity:
    """Implements Phase2 credential, subject, operator and attestation ports."""

    def __init__(
        self,
        deployment_id: str,
        peers: Iterable[PeerCredential],
        *,
        operator_uid: int,
        operator_public_key: Path,
        operator_public_key_sha256: str,
        audit_root: Path,
        binding_lookup: Callable[[VerifiedSubject], tuple[dict[str, Any] | None, datetime]],
    ) -> None:
        records = tuple(peers)
        by_uid = {record.uid: record for record in records}
        if (
            not deployment_id.strip()
            or len(by_uid) != len(records)
            or len({r.actor_id for r in records}) != len(records)
            or len({r.credential_id for r in records}) != len(records)
            or operator_uid not in by_uid
            or len(operator_public_key_sha256) != 64
            or any(c not in "0123456789abcdef" for c in operator_public_key_sha256)
        ):
            raise ValueError("ambiguous trusted peer policy")
        self.deployment_id = deployment_id
        self._peers = by_uid
        self._operator_uid = operator_uid
        self._operator_public_key = operator_public_key.absolute()
        self._operator_public_key_sha256 = operator_public_key_sha256
        self._audit_root = audit_root.absolute()
        self._binding_lookup = binding_lookup

    def subject(self, peer_uid: int) -> VerifiedSubject:
        if isinstance(peer_uid, bool) or peer_uid not in self._peers:
            raise _denied()
        record = self._peers[peer_uid]
        subject = VerifiedSubject(self.deployment_id, "OS_UID", str(peer_uid), record.credential_id)
        if not self.is_valid(subject, datetime.now(UTC)):
            raise _denied()
        return subject

    def authenticate_subject(self, peer_uid: int) -> VerifiedPrincipal:
        subject = self.subject(peer_uid)
        facts, at = self._binding_lookup(subject)
        record = self._peers[peer_uid]
        if (
            facts is None
            or facts.get("actor_id") != record.actor_id
            or facts.get("retired_at") is not None
            or facts.get("bound_at") is None
            or facts["bound_at"] > at
            or (facts.get("revoked_at") is not None and facts["revoked_at"] <= at)
            or not self.is_valid(subject, at)
        ):
            raise _denied()
        return VerifiedPrincipal(
            record.actor_id, self.deployment_id, "OS_UID", str(peer_uid), record.credential_id, at
        )

    def is_valid(self, principal: VerifiedPrincipal | VerifiedSubject, at: datetime) -> bool:
        try:
            if principal.deployment_id != self.deployment_id or principal.subject_kind != "OS_UID":
                return False
            uid = int(principal.subject_value)
            record = self._peers[uid]
            return (
                str(uid) == principal.subject_value
                and principal.credential_id == record.credential_id
                and (
                    not isinstance(principal, VerifiedPrincipal)
                    or (principal.actor_id == record.actor_id and principal.verified_at <= at)
                )
                and record.not_before <= at
                and (record.not_after is None or at < record.not_after)
            )
        except (KeyError, ValueError, TypeError):
            return False

    def is_allowlisted(self, principal: VerifiedPrincipal) -> bool:
        return principal.subject_value == str(self._operator_uid) and self.is_valid(
            principal, datetime.now(UTC)
        )

    def verify(self, attestation: object) -> bool:
        if not isinstance(attestation, OnboardingAttestation | ProvisioningAttestation):
            return False
        try:
            if not self.is_allowlisted(attestation.operator):
                return False
            digest = attestation.proof_sha256
            if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                return False
            root = self._audit_root
            if root.resolve() != root or not self._private_dir(root):
                return False
            path = root / f"proof-{digest}.json"
            if attestation.proof_record_ref != str(path):
                return False
            raw = self._read_proof(path)
            if not hmac.compare_digest(hashlib.sha256(raw).hexdigest(), digest):
                return False
            record = json.loads(raw)
            if set(record) != {"material", "signature_hex"}:
                return False
            material = record["material"]
            signature = bytes.fromhex(record["signature_hex"])
            if len(signature) != 64 or not self._matching_material(attestation, material):
                return False
            return self._verify_signature(_canonical(material), signature)
        except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError):
            return False

    @staticmethod
    def _private_dir(path: Path) -> bool:
        info = path.lstat()
        return (
            stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o077
        )

    @staticmethod
    def _read_proof(path: Path) -> bytes:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            info = os.fstat(fd)
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.getuid()
                or info.st_mode & 0o077
                or info.st_nlink != 1
            ):
                raise ValueError("unsafe audit proof")
            with os.fdopen(fd, "rb", closefd=False) as stream:
                raw = stream.read(8193)
            if len(raw) > 8192:
                raise ValueError("oversized audit proof")
            return raw
        finally:
            os.close(fd)

    def _matching_material(
        self, attestation: OnboardingAttestation | ProvisioningAttestation, material: Any
    ) -> bool:
        if not isinstance(material, dict):
            return False
        common = {
            "version": 1,
            "actor_id": str(attestation.actor_id),
            "deployment_id": attestation.deployment_id,
            "subject_kind": attestation.subject_kind,
            "subject_value": attestation.subject_value,
            "subject_credential_id": attestation.subject_credential_id,
            "operator_actor_id": str(attestation.operator.actor_id),
            "operator_subject_kind": attestation.operator.subject_kind,
            "operator_subject_value": attestation.operator.subject_value,
            "operator_credential_id": attestation.operator.credential_id,
            "reason": attestation.reason,
        }
        if any(material.get(k) != v for k, v in common.items()):
            return False
        if (
            attestation.deployment_id != self.deployment_id
            or attestation.operator.actor_id == attestation.actor_id
            or (
                attestation.subject_kind == "OS_UID"
                and attestation.subject_value == str(self._operator_uid)
            )
        ):
            return False
        if (
            not isinstance(material.get("evidence_source"), str)
            or not material["evidence_source"].strip()
        ):
            return False
        try:
            signed_at = datetime.fromisoformat(material["signed_at"])
            if signed_at.tzinfo is None or not timedelta(0) <= datetime.now(
                UTC
            ) - signed_at <= timedelta(minutes=15):
                return False
        except (KeyError, ValueError, TypeError):
            return False
        if isinstance(attestation, ProvisioningAttestation):
            expected = set(common) | {
                "ceremony",
                "evidence_source",
                "signed_at",
                "subject_live_proof_sha256",
            }
            proof = material.get("subject_live_proof_sha256")
            return (
                set(material) == expected
                and material["ceremony"] == "PROVISION_ACTOR"
                and isinstance(proof, str)
                and len(proof) == 64
                and all(c in "0123456789abcdef" for c in proof)
            )
        expected = set(common) | {
            "ceremony",
            "evidence_source",
            "signed_at",
            "challenge_id",
            "nonce_digest",
            "proof_method",
        }
        return (
            set(material) == expected
            and material["ceremony"] == "BIND_LEGACY_SUBJECT"
            and material["challenge_id"] == str(attestation.challenge_id)
            and material["nonce_digest"] == attestation.nonce_digest
            and material["proof_method"] == attestation.proof_method
        )

    def _verify_signature(self, body: bytes, signature: bytes) -> bool:
        key = self._operator_public_key
        info = key.lstat()
        if (
            key.resolve() != key
            or not stat.S_ISREG(info.st_mode)
            or info.st_uid not in {0, os.getuid()}
            or info.st_mode & 0o022
        ):
            return False
        key_bytes = key.read_bytes()
        if len(key_bytes) > 4096 or not hmac.compare_digest(
            hashlib.sha256(key_bytes).hexdigest(), self._operator_public_key_sha256
        ):
            return False
        with tempfile.TemporaryDirectory(prefix="rb-hg1-proof-verify-") as scratch:
            signature_path = Path(scratch) / "signature"
            material_path = Path(scratch) / "material"
            key_path = Path(scratch) / "operator-public.pem"
            signature_path.write_bytes(signature)
            material_path.write_bytes(body)
            key_path.write_bytes(key_bytes)
            result = subprocess.run(
                [
                    "/opt/homebrew/bin/openssl",
                    "pkeyutl",
                    "-verify",
                    "-pubin",
                    "-inkey",
                    str(key_path),
                    "-rawin",
                    "-sigfile",
                    str(signature_path),
                    "-in",
                    str(material_path),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                check=False,
            )
            return result.returncode == 0
