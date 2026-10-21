"""Technical C/B/A ceremony against a disposable database, not human acceptance."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from researchbase.application.phase2_identity import Phase2IdentityService, VerifiedSubject
from researchbase.hg1_ceremony import HG1Coordinator
from researchbase.hg1_identity import PeerCredential, TrustedPeerIdentity
from researchbase.hg1_runtime import _SubjectCredentials, build_hg1_coordinator
from researchbase.persistence.uow import SqlAlchemyUnitOfWork
from tests.integration.phase2.test_pr2_01_source_identity import _authorized_service


class _NonceIssuer:
    def issue(self):
        return b"n" * 32


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


@pytest.mark.skipif(
    sys.platform != "darwin",
    reason="HG1 signature verification uses the trusted macOS host /opt/homebrew/bin/openssl.",
)
def test_live_peer_proof_c_signature_provision_and_reviewer_role(
    phase2_database_url: str, tmp_path: Path
):
    engine, _initial_identity, _sources, owner, project = _authorized_service(phase2_database_url)
    sf = sessionmaker(engine, expire_on_commit=False, autoflush=False)

    def uow_factory():
        return SqlAlchemyUnitOfWork(sf)

    def binding_lookup(subject: VerifiedSubject):
        with uow_factory() as uow:
            return (
                uow.phase2_identity.resolve_bound_subject(subject),
                uow.phase2_identity.database_time(),
            )

    b_uid, c_uid = 60002, 60003
    b_actor, c_actor = uuid4(), uuid4()
    now = datetime.now(UTC)
    key = tmp_path / "c-private.pem"
    public = tmp_path / "c-public.pem"
    subprocess.run(["openssl", "genpkey", "-algorithm", "ED25519", "-out", str(key)], check=True)
    with public.open("wb") as stream:
        subprocess.run(["openssl", "pkey", "-in", str(key), "-pubout"], stdout=stream, check=True)
    audit = tmp_path / "audit"
    audit.mkdir(mode=0o700)
    policy = TrustedPeerIdentity(
        owner.deployment_id,
        (
            PeerCredential(501, owner.actor_id, owner.credential_id, now - timedelta(days=1), None),
            PeerCredential(b_uid, b_actor, "credential-b", now - timedelta(days=1), None),
            PeerCredential(c_uid, c_actor, "credential-c", now - timedelta(days=1), None),
        ),
        operator_uid=c_uid,
        operator_public_key=public,
        operator_public_key_sha256=hashlib.sha256(public.read_bytes()).hexdigest(),
        audit_root=audit,
        binding_lookup=binding_lookup,
    )
    identity = Phase2IdentityService(
        uow_factory,
        nonce_issuer=_NonceIssuer(),
        operator_policy=policy,
        credential_verifier=policy,
        subject_credential_verifier=_SubjectCredentials(policy),
        attestation_verifier=policy,
    )
    coordinator = HG1Coordinator(
        policy,
        identity,
        SimpleNamespace(),
        SimpleNamespace(authenticate=lambda: owner),
        owner_uid=501,
    )
    challenge = coordinator.execute(b_uid, {"v": 2, "op": "enrollment.challenge"})
    proof = coordinator.execute(
        b_uid,
        {"v": 2, "op": "enrollment.prove", **challenge},
    )
    material = {
        "version": 1,
        "ceremony": "PROVISION_ACTOR",
        "actor_id": str(b_actor),
        "deployment_id": owner.deployment_id,
        "subject_kind": "OS_UID",
        "subject_value": str(b_uid),
        "subject_credential_id": "credential-b",
        "operator_actor_id": str(c_actor),
        "operator_subject_kind": "OS_UID",
        "operator_subject_value": str(c_uid),
        "operator_credential_id": "credential-c",
        "reason": "C inspected independent test identity evidence",
        "evidence_source": "disposable technical fixture only",
        "signed_at": datetime.now(UTC).isoformat(),
        "subject_live_proof_sha256": proof["live_proof_sha256"],
    }
    signed = tmp_path / "material"
    signature = tmp_path / "signature"
    signed.write_bytes(_canonical(material))
    subprocess.run(
        [
            "openssl",
            "pkeyutl",
            "-sign",
            "-inkey",
            str(key),
            "-rawin",
            "-in",
            str(signed),
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
    coordinator.execute(
        c_uid,
        {
            "v": 2,
            "op": "enrollment.attest",
            "subject_uid": b_uid,
            "proof_sha256": digest,
            "reason": material["reason"],
        },
    )
    result = coordinator.execute(
        501,
        {
            "v": 2,
            "op": "enrollment.provision",
            "subject_uid": b_uid,
            "display_name": "Technical B",
            "request_id": str(uuid4()),
        },
    )
    assert result["actor_id"] == str(b_actor)
    assigned = coordinator.execute(
        501,
        {
            "v": 2,
            "op": "reviewer.assign",
            "subject_uid": b_uid,
            "project_id": str(project),
            "reason": "Technical reviewer duty",
            "request_id": str(uuid4()),
        },
    )
    assert assigned["role_assignment_id"]
    assert policy.authenticate_subject(b_uid).actor_id == b_actor
    with engine.connect() as connection:
        assert (
            connection.execute(
                text(
                    "SELECT count(*) FROM actor_subject_binding_events "
                    "WHERE actor_id=:actor AND event_kind='PROVISIONED'"
                ),
                {"actor": b_actor},
            ).scalar_one()
            == 1
        )
        assert (
            connection.execute(
                text(
                    "SELECT count(*) FROM project_role_assignments "
                    "WHERE actor_id=:actor AND project_id=:project AND role='REVIEWER'"
                ),
                {"actor": b_actor, "project": project},
            ).scalar_one()
            == 1
        )
    engine.dispose()


def test_admin_policy_composes_live_runner_services_on_disposable_db(
    phase2_database_url: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    engine, _identity, _sources, owner, _project = _authorized_service(phase2_database_url)
    from researchbase import hg1_runtime

    durable = tmp_path / "durable"
    audit = durable / "migration-evidence" / "hg1-02-audit"
    audit.mkdir(parents=True, mode=0o700)
    public = tmp_path / "operator-public.pem"
    public.write_text("test public key is not used until attestation")
    owner_uid = os.geteuid()
    host_owner = replace(owner, subject_value=str(owner_uid))
    policy = {
        "version": 1,
        "deployment_id": owner.deployment_id,
        "operator_uid": 60003,
        "operator_public_key": str(public),
        "operator_public_key_sha256": hashlib.sha256(public.read_bytes()).hexdigest(),
        "audit_root": str(audit),
        "peers": [
            {
                "uid": uid,
                "actor_id": str(actor),
                "credential_id": credential,
                "not_before": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
                "not_after": None,
            }
            for uid, actor, credential in (
                (owner_uid, owner.actor_id, owner.credential_id),
                (60002, uuid4(), "credential-b"),
                (60003, uuid4(), "credential-c"),
            )
        ],
    }
    monkeypatch.setenv("RB_HOST_DURABLE_ROOT", str(durable))
    # Model a configured trusted host on either OS while checking the real process UID.
    monkeypatch.setenv("RB_HOST_OWNER_UID", str(owner_uid))
    monkeypatch.setattr(hg1_runtime, "read_trusted_config", lambda _path: policy)
    services = SimpleNamespace(
        local_identity=SimpleNamespace(authenticate=lambda: host_owner),
        local_credentials=_NonceIssuer(),
    )
    settings = SimpleNamespace(
        database_url=phase2_database_url, artifact_store_root=str(tmp_path / "cas")
    )
    monkeypatch.setenv("RB_HOST_OWNER_UID", str(owner_uid + 1))
    with pytest.raises(ValueError, match="trusted owner/operator boundary changed"):
        build_hg1_coordinator("final", services, settings)
    monkeypatch.setenv("RB_HOST_OWNER_UID", str(owner_uid))
    policy["operator_uid"] = owner_uid
    with pytest.raises(ValueError, match="trusted owner/operator boundary changed"):
        build_hg1_coordinator("final", services, settings)
    policy["operator_uid"] = 60003
    coordinator = build_hg1_coordinator("final", services, settings)
    assert coordinator is not None
    assert coordinator.allowed_uid(owner_uid)
    assert coordinator.allowed_uid(60002)
    assert coordinator.allowed_uid(60003)
    engine.dispose()
