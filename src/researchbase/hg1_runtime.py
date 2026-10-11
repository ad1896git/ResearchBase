"""Opt-in HG1-02 composition from a host-admin-controlled local policy."""

from __future__ import annotations

import json
import os
import stat
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from researchbase.application.literature_evidence import LiteratureEvidenceService
from researchbase.application.phase2_identity import Phase2IdentityService, VerifiedSubject
from researchbase.foundation.artifact_store import ContentAddressedFilesystemArtifactStore
from researchbase.hg1_ceremony import HG1Coordinator
from researchbase.hg1_identity import PeerCredential, TrustedPeerIdentity
from researchbase.hg1_review_ops import HG1ReviewOperations
from researchbase.persistence.database import create_database_engine, create_session_factory
from researchbase.persistence.uow import SqlAlchemyUnitOfWork

TRUST_ROOT = Path("/Library/Application Support/ResearchBase")
DURABLE_ROOT = Path("/Users/onephone/ResearchBaseData")
REQUIRED_M3_HBA = (
    ("local", "all", "onephone", None, None, "peer", None),
    ("local", "all", "all", None, None, "reject", None),
    ("local", "replication", "all", None, None, "reject", None),
    ("host", "all", "all", "127.0.0.1", "255.255.255.255", "reject", None),
    ("host", "all", "all", "::1", "ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff", "reject", None),
    ("host", "replication", "all", "127.0.0.1", "255.255.255.255", "reject", None),
    (
        "host",
        "replication",
        "all",
        "::1",
        "ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff",
        "reject",
        None,
    ),
)


def verify_m3_server(settings: Any) -> None:
    """Fail closed if the retained M3 target or effective authentication drifts."""
    from sqlalchemy import text

    engine = create_database_engine(settings.database_url)
    try:
        with engine.connect() as connection:
            connection.execute(text("SET TRANSACTION READ ONLY"))
            facts = connection.execute(
                text("""
                SELECT current_database(), current_user, current_setting('data_directory'),
                       current_setting('port'), current_setting('unix_socket_directories'),
                       current_setting('hba_file'), current_setting('listen_addresses'),
                       (SELECT system_identifier::text FROM pg_control_system()),
                       (SELECT version_num FROM alembic_version)
            """)
            ).one()
            expected = (
                "researchbase_m3_retained_20261011",
                "onephone",
                str(DURABLE_ROOT / "rb-m2-pg"),
                "55440",
                "/private/tmp",
                str(DURABLE_ROOT / "rb-m2-pg" / "pg_hba.conf"),
                facts[6],
                "7695048034454027996",
                "0031_m3_snapshot_relation_cardinality",
            )
            listeners = {item.strip() for item in facts[6].split(",")}
            if tuple(facts) != expected or not listeners <= {"localhost", "127.0.0.1", "::1"}:
                raise ValueError("retained M3 PostgreSQL identity changed")
            rules = connection.execute(
                text("""
                SELECT type, array_to_string(database, ','), array_to_string(user_name, ','),
                       address, netmask, auth_method, error
                  FROM pg_hba_file_rules ORDER BY rule_number
            """)
            ).all()
            if tuple(tuple(rule) for rule in rules) != REQUIRED_M3_HBA:
                raise ValueError("retained M3 PostgreSQL HBA changed")
    finally:
        engine.dispose()


class _SubjectCredentials:
    def __init__(self, policy: TrustedPeerIdentity) -> None:
        self.policy = policy

    def is_valid(self, subject: VerifiedSubject, at: datetime) -> bool:
        return self.policy.is_valid(subject, at)


def read_trusted_config(path: Path) -> dict[str, Any] | None:
    """Read a root-owned policy with no user-writable path component."""
    if not path.exists() and not path.is_symlink():
        return None
    if not path.is_absolute() or path.resolve() != path:
        raise PermissionError("unsafe HG1 host policy path")
    for parent in path.parents:
        info = parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise PermissionError("HG1 host policy parent is not protected")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != 0
            or info.st_mode & 0o022
            or info.st_nlink != 1
        ):
            raise PermissionError("HG1 host policy is not root controlled")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(16385)
        if len(raw) > 16384:
            raise ValueError("HG1 host policy is too large")
    finally:
        os.close(fd)
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("HG1 host policy must be an object")
    return value


def build_hg1_coordinator(tag: str, services: Any, settings: Any) -> HG1Coordinator | None:
    """Keep HG1-01 A-only behavior until host-admin policy is installed."""
    if tag not in {"final", "live", "live2", "live3", "m3-retained"}:
        raise ValueError("unsupported retained deployment")
    config_path = TRUST_ROOT / f"hg1-02-{tag}.json"
    config = read_trusted_config(config_path)
    if config is None:
        return None
    if (
        set(config)
        != {
            "version",
            "deployment_id",
            "operator_uid",
            "operator_public_key",
            "operator_public_key_sha256",
            "audit_root",
            "peers",
        }
        or config["version"] != 1
    ):
        raise ValueError("invalid HG1 host policy fields")
    if type(config["operator_uid"]) is not int or not isinstance(config["peers"], list):
        raise ValueError("invalid HG1 host policy principals")
    if len(config["peers"]) != 3:
        raise ValueError("HG1-02 requires exactly A, B and C")
    records = []
    for item in config["peers"]:
        if not isinstance(item, dict) or set(item) != {
            "uid",
            "actor_id",
            "credential_id",
            "not_before",
            "not_after",
        }:
            raise ValueError("invalid HG1 peer record")
        records.append(
            PeerCredential(
                item["uid"],
                UUID(item["actor_id"]),
                item["credential_id"],
                datetime.fromisoformat(item["not_before"]),
                datetime.fromisoformat(item["not_after"]) if item["not_after"] else None,
            )
        )
    owner_uid = os.geteuid()
    if owner_uid != 502 or owner_uid == config["operator_uid"]:
        raise ValueError("HG1 trusted owner/operator boundary changed")
    audit = Path(config["audit_root"])
    if (
        not audit.is_absolute()
        or audit.resolve() != audit
        or audit.parent != DURABLE_ROOT / "migration-evidence"
        or not audit.is_dir()
    ):
        raise ValueError("HG1 audit root is not approved durable storage")
    engine = create_database_engine(settings.database_url)
    session_factory = create_session_factory(engine)

    def uow_factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory)

    def lookup(subject: VerifiedSubject) -> tuple[dict[str, Any] | None, datetime]:
        with uow_factory() as uow:
            facts = uow.phase2_identity.resolve_bound_subject(subject)
            return facts, uow.phase2_identity.database_time()

    policy = TrustedPeerIdentity(
        config["deployment_id"],
        records,
        operator_uid=config["operator_uid"],
        operator_public_key=Path(config["operator_public_key"]),
        operator_public_key_sha256=config["operator_public_key_sha256"],
        audit_root=audit,
        binding_lookup=lookup,
        config_guard=lambda: read_trusted_config(config_path) == config,
    )
    owner = services.local_identity.authenticate()
    owner_record = policy.record(owner_uid)
    if (
        owner.deployment_id != policy.deployment_id
        or owner.actor_id != owner_record.actor_id
        or owner.credential_id != owner_record.credential_id
        or not policy.is_valid(owner, datetime.now(owner.verified_at.tzinfo))
    ):
        raise ValueError("HG1 policy does not match canonical A installation")
    subject_uids = {record.uid for record in records} - {owner_uid, config["operator_uid"]}
    if len(subject_uids) != 1:
        raise ValueError("ambiguous B subject")
    store = ContentAddressedFilesystemArtifactStore(Path(settings.artifact_store_root))
    identity = Phase2IdentityService(
        uow_factory,
        nonce_issuer=services.local_credentials,
        operator_policy=policy,
        credential_verifier=policy,
        subject_credential_verifier=_SubjectCredentials(policy),
        attestation_verifier=policy,
    )
    reviews = HG1ReviewOperations(LiteratureEvidenceService(uow_factory, policy, store))
    return HG1Coordinator(policy, identity, reviews, services.local_identity, owner_uid=owner_uid)
