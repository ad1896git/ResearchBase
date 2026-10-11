"""A provisioned human subject resolves without bootstrap ownership."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from researchbase.application.phase2_identity import VerifiedSubject
from researchbase.persistence.phase2_identity_repository import SqlAlchemyPhase2IdentityRepository


def test_provisioned_subject_resolution_is_unique_and_revocation_sensitive(
    phase2_database_url: str,
) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url.replace("%", "%%"))
    command.upgrade(config, "0019_phase2_bootstrap_membership")
    engine = create_engine(phase2_database_url)
    actor_id, binding_id = uuid4(), uuid4()
    now = datetime.now(UTC)
    subject = VerifiedSubject("test-deployment", "OS_UID", "60001", "credential-b")
    revoked_at = datetime.now(UTC)
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO actors (id, actor_type, display_name, external_key, created_at) "
                 "VALUES (:id, 'HUMAN', 'B', :key, clock_timestamp())"),
            {"id": actor_id, "key": "local-os:test-deployment:60001"},
        )
        connection.execute(
            text("INSERT INTO actor_subject_bindings "
                 "(id, actor_id, deployment_id, subject_kind, subject_value, status, bound_at, "
                 "operator_credential_id, subject_credential_id, proof_sha256, proof_record_ref, "
                 "proof_kind, created_at, row_version) VALUES "
                 "(:id, :actor, 'test-deployment', 'OS_UID', '60001', 'ACTIVE', "
                 ":at, 'credential-c', 'credential-b', :digest, "
                 "'audit/sha256/test', 'OS_PEER', :at, 1)"),
            {"id": binding_id, "actor": actor_id, "digest": "a" * 64, "at": now},
        )
        connection.execute(
            text("INSERT INTO actor_subject_binding_events "
                 "(id, binding_id, actor_id, event_kind, operator_credential_id, "
                 "subject_credential_id, proof_sha256, proof_record_ref, proof_kind, "
                 "request_id, reason, occurred_at) VALUES "
                 "(:id, :binding, :actor, 'PROVISIONED', 'credential-c', "
                 "'credential-b', :digest, 'audit/sha256/test', 'OS_PEER', "
                 ":request, 'verified fixture', :at)"),
            {"id": uuid4(), "binding": binding_id, "actor": actor_id,
             "digest": "a" * 64, "request": uuid4(), "at": now},
        )
    with Session(engine) as session:
        repo = SqlAlchemyPhase2IdentityRepository(session)
        assert repo.resolve_bound_subject(subject)["actor_id"] == actor_id
        assert repo.resolve_bound_subject(
            VerifiedSubject("test-deployment", "OS_UID", "60001", "wrong")
        ) is None
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE actor_subject_bindings SET status='REVOKED', revoked_at=:at, "
                 "row_version=row_version+1 "
                 "WHERE id=:id"),
            {"id": binding_id, "at": revoked_at},
        )
        connection.execute(
            text("INSERT INTO actor_subject_binding_events "
                 "(id, binding_id, actor_id, event_kind, operator_credential_id, "
                 "subject_credential_id, proof_sha256, proof_record_ref, proof_kind, "
                 "request_id, reason, occurred_at) VALUES "
                 "(:id, :binding, :actor, 'REVOKED', 'credential-c', "
                 "'credential-b', :digest, 'audit/sha256/test', 'OS_PEER', "
                 ":request, 'fixture revocation', :at)"),
            {"id": uuid4(), "binding": binding_id, "actor": actor_id,
             "digest": "a" * 64, "request": uuid4(), "at": revoked_at},
        )
    with Session(engine) as session:
        assert SqlAlchemyPhase2IdentityRepository(session).resolve_bound_subject(subject) is None
    engine.dispose()
