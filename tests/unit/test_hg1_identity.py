from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from researchbase.application.phase2_identity import ProvisioningAttestation, VerifiedSubject
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.errors import ResearchBaseError
from researchbase.hg1_identity import PeerCredential, TrustedPeerIdentity

NOW = datetime.now(UTC)


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _fixture(tmp_path: Path):
    key = tmp_path / "c-key.pem"
    pub = tmp_path / "c-pub.pem"
    subprocess.run(["openssl", "genpkey", "-algorithm", "ED25519", "-out", str(key)], check=True)
    with pub.open("wb") as output:
        subprocess.run(["openssl", "pkey", "-in", str(key), "-pubout"], stdout=output, check=True)
    audit = tmp_path / "audit"
    audit.mkdir(mode=0o700)
    actor_a, actor_b, actor_c = uuid4(), uuid4(), uuid4()
    records = (
        PeerCredential(501, actor_a, "a-credential", NOW - timedelta(days=1), None),
        PeerCredential(502, actor_b, "b-credential", NOW - timedelta(days=1), None),
        PeerCredential(
            503, actor_c, "c-credential", NOW - timedelta(days=1), NOW + timedelta(days=1)
        ),
    )

    def lookup(subject):
        facts = (
            {
                "actor_id": actor_b,
                "bound_at": NOW - timedelta(hours=1),
                "revoked_at": None,
                "retired_at": None,
            }
            if subject.subject_value == "502"
            else None
        )
        return facts, NOW

    policy = TrustedPeerIdentity(
        "deployment-1",
        records,
        operator_uid=503,
        operator_public_key=pub,
        operator_public_key_sha256=hashlib.sha256(pub.read_bytes()).hexdigest(),
        audit_root=audit,
        binding_lookup=lookup,
    )
    operator = VerifiedPrincipal(actor_c, "deployment-1", "OS_UID", "503", "c-credential", NOW)
    return policy, key, audit, operator, actor_a, actor_b, actor_c


def _attestation(policy, key, audit, operator, actor_b, *, change=None):
    material = {
        "version": 1,
        "ceremony": "PROVISION_ACTOR",
        "actor_id": str(actor_b),
        "deployment_id": "deployment-1",
        "subject_kind": "OS_UID",
        "subject_value": "502",
        "subject_credential_id": "b-credential",
        "operator_actor_id": str(operator.actor_id),
        "operator_subject_kind": "OS_UID",
        "operator_subject_value": "503",
        "operator_credential_id": "c-credential",
        "reason": "independent verification",
        "evidence_source": "host identity document inspected by C",
        "signed_at": NOW.isoformat(),
        "subject_live_proof_sha256": "a" * 64,
    }
    if change:
        material.update(change)
    body = _canonical(material)
    # Test signing is confined to disposable fixtures; production owns no C private key.
    source = audit.parent / "material"
    signature = audit.parent / "signature"
    source.write_bytes(body)
    subprocess.run(
        [
            "openssl",
            "pkeyutl",
            "-sign",
            "-inkey",
            str(key),
            "-rawin",
            "-in",
            str(source),
            "-out",
            str(signature),
        ],
        check=True,
    )
    record = _canonical({"material": material, "signature_hex": signature.read_bytes().hex()})
    digest = hashlib.sha256(record).hexdigest()
    path = audit / f"proof-{digest}.json"
    path.write_bytes(record)
    path.chmod(0o600)
    attestation = ProvisioningAttestation(
        actor_b,
        "deployment-1",
        "OS_UID",
        "502",
        "b-credential",
        operator,
        digest,
        str(path),
        "independent verification",
    )
    return attestation, path


def test_bound_peer_authenticates_and_rechecks(tmp_path):
    policy, *_ = _fixture(tmp_path)
    principal = policy.authenticate_subject(502)
    assert principal.subject_value == "502"
    assert policy.is_valid(principal, NOW)
    assert not policy.is_allowlisted(principal)
    with pytest.raises(ResearchBaseError):
        policy.authenticate_subject(999)


def test_independent_c_signed_proof(tmp_path):
    policy, key, audit, operator, _a, b, _c = _fixture(tmp_path)
    attestation, path = _attestation(policy, key, audit, operator, b)
    assert policy.verify(attestation)
    assert policy.is_allowlisted(operator)
    path.write_bytes(path.read_bytes().replace(b"independent verification", b"forged verification"))
    assert not policy.verify(attestation)


def test_cross_identity_and_path_substitution_rejected(tmp_path):
    policy, key, audit, operator, a, b, _c = _fixture(tmp_path)
    attestation, path = _attestation(policy, key, audit, operator, b)
    wrong = ProvisioningAttestation(
        a,
        attestation.deployment_id,
        attestation.subject_kind,
        attestation.subject_value,
        attestation.subject_credential_id,
        operator,
        attestation.proof_sha256,
        attestation.proof_record_ref,
        attestation.reason,
    )
    assert not policy.verify(wrong)
    alias = audit / "alias.json"
    alias.symlink_to(path)
    wrong_path = ProvisioningAttestation(
        b,
        attestation.deployment_id,
        attestation.subject_kind,
        attestation.subject_value,
        attestation.subject_credential_id,
        operator,
        attestation.proof_sha256,
        str(alias),
        attestation.reason,
    )
    assert not policy.verify(wrong_path)


def test_expiry_and_operator_separation(tmp_path):
    policy, key, audit, operator, _a, b, _c = _fixture(tmp_path)
    attestation, _ = _attestation(
        policy, key, audit, operator, b, change={"signed_at": (NOW - timedelta(days=2)).isoformat()}
    )
    assert not policy.verify(attestation)
    assert not policy.is_valid(
        VerifiedSubject("deployment-2", "OS_UID", "502", "b-credential"), NOW
    )
    assert not policy.is_valid(operator, NOW + timedelta(days=3650))


def test_forged_signature_and_missing_proof_rejected(tmp_path):
    policy, key, audit, operator, _a, b, _c = _fixture(tmp_path)
    attestation, path = _attestation(policy, key, audit, operator, b)
    record = json.loads(path.read_bytes())
    record["signature_hex"] = "00" * 64
    forged = _canonical(record)
    forged_digest = hashlib.sha256(forged).hexdigest()
    forged_path = audit / f"proof-{forged_digest}.json"
    forged_path.write_bytes(forged)
    forged_path.chmod(0o600)
    bad = ProvisioningAttestation(
        b,
        "deployment-1",
        "OS_UID",
        "502",
        "b-credential",
        operator,
        forged_digest,
        str(forged_path),
        "independent verification",
    )
    assert not policy.verify(bad)
    path.unlink()
    assert not policy.verify(attestation)


def test_revoked_binding_and_credential_fail_closed(tmp_path):
    policy, _key, _audit, _operator, _a, b, _c = _fixture(tmp_path)
    policy._binding_lookup = lambda _subject: (
        {
            "actor_id": b,
            "bound_at": NOW - timedelta(hours=1),
            "revoked_at": NOW,
            "retired_at": None,
        },
        NOW,
    )
    with pytest.raises(ResearchBaseError):
        policy.authenticate_subject(502)
    assert not policy.is_valid(VerifiedSubject("deployment-1", "OS_UID", "502", "wrong"), NOW)


def test_host_policy_change_revokes_live_peer_authority(tmp_path):
    policy, *_ = _fixture(tmp_path)
    policy._config_guard = lambda: False
    assert not policy.is_valid(
        VerifiedSubject("deployment-1", "OS_UID", "502", "b-credential"), NOW
    )
    with pytest.raises(ResearchBaseError):
        policy.authenticate_subject(502)
