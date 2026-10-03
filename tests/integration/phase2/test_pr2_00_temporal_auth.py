from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from tests.integration.phase2.test_pr2_00_bootstrap import _BootstrapProofVerifier
from tests.integration.phase2.test_pr2_00_challenges import (
    _ExpiringCredentialVerifier,
    _service,
)

from researchbase.application.phase2_identity import BootstrapAuthority
from researchbase.domain.phase2_identity import VerifiedPrincipal, effective_owner


def test_owner_credential_expiry_changes_effective_authority_without_database_mutation(
    phase2_database_url: str,
) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "0019_phase2_bootstrap_membership")
    engine = create_engine(phase2_database_url)
    with engine.connect() as connection:
        expires_at = connection.execute(
            text("SELECT clock_timestamp() + interval '2 minutes'")
        ).scalar_one()

    operator = VerifiedPrincipal(
        actor_id=uuid4(),
        deployment_id="deployment-temporal-owner",
        subject_kind="OS_UID",
        subject_value="901",
        credential_id="os-credential-901",
        verified_at=datetime.now(UTC),
    )
    verifier = _ExpiringCredentialVerifier(expires_at)
    service, _unused_operator, _unused_subject = _service(
        phase2_database_url,
        credential_verifier=verifier,
        bootstrap_proof_verifier=_BootstrapProofVerifier(),
    )
    try:
        result = service.bootstrap_first_owner(
            BootstrapAuthority(
                deployment_id=operator.deployment_id,
                operator=operator,
                verified_os_uid=901,
                subject_credential_id=operator.credential_id,
                secret_digest_id="secret-digest-ref",
                proof_sha256="1" * 64,
                proof_record_ref="audit/sha256/temporal-owner",
            ),
            request_id=uuid4(),
            display_name="Temporal Owner",
            project_name="Temporal project",
        )
        principal = VerifiedPrincipal(
            actor_id=result.actor_id,
            deployment_id=operator.deployment_id,
            subject_kind=operator.subject_kind,
            subject_value=operator.subject_value,
            credential_id=operator.credential_id,
            verified_at=operator.verified_at,
        )
        with engine.connect() as connection:
            role = (
                connection.execute(
                    text(
                        "SELECT r.effective_from, r.effective_until, m.started_at, m.status, "
                        "a.retired_at, b.status AS binding_status, b.bound_at, b.revoked_at "
                        "FROM project_role_assignments r "
                        "JOIN project_memberships m ON m.id = r.membership_id "
                        "JOIN actors a ON a.id = r.actor_id "
                        "JOIN actor_subject_bindings b ON b.actor_id = a.id "
                        "WHERE r.id = :id"
                    ),
                    {"id": result.role_assignment_id},
                )
                .mappings()
                .one()
            )
            before = connection.execute(
                text(
                    "SELECT (SELECT count(*) FROM project_role_assignments), "
                    "(SELECT count(*) FROM project_role_events)"
                )
            ).one()

        def role_valid_at(at: datetime) -> bool:
            return bool(
                role["effective_from"] <= at
                and (role["effective_until"] is None or role["effective_until"] > at)
                and role["status"] == "ACTIVE"
                and role["started_at"] <= at
                and role["binding_status"] == "ACTIVE"
                and role["bound_at"] <= at
                and (role["revoked_at"] is None or role["revoked_at"] > at)
                and role["retired_at"] is None
            )

        assert effective_owner(
            role_valid=role_valid_at(expires_at - timedelta(microseconds=1)),
            membership_valid=True,
            actor_retired=False,
            principal=principal,
            verifier=verifier,
            at=expires_at - timedelta(microseconds=1),
        )
        assert not effective_owner(
            role_valid=role_valid_at(expires_at + timedelta(microseconds=1)),
            membership_valid=True,
            actor_retired=False,
            principal=principal,
            verifier=verifier,
            at=expires_at + timedelta(microseconds=1),
        )
        with engine.connect() as connection:
            after = connection.execute(
                text(
                    "SELECT (SELECT count(*) FROM project_role_assignments), "
                    "(SELECT count(*) FROM project_role_events)"
                )
            ).one()
            assert after == before
            assert (
                connection.execute(
                    text("SELECT effective_until FROM project_role_assignments WHERE id = :id"),
                    {"id": result.role_assignment_id},
                ).scalar_one()
                is None
            )
    finally:
        engine.dispose()
