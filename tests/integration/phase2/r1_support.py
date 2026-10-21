"""Shared R1 fixtures and helpers, registered through Phase 2 conftest."""

from datetime import UTC, datetime
from threading import Event
from time import monotonic
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from researchbase.application.phase2_identity import (
    AssignProjectRole,
    BootstrapAuthority,
    CloseProjectRole,
    ProvisionActor,
    ProvisioningAttestation,
    VerifiedSubject,
)
from researchbase.domain.phase2_identity import VerifiedPrincipal
from tests.integration.phase2.test_pr2_00_challenges import (
    _ExpiringCredentialVerifier as _ExpiringCredentialVerifier,
)
from tests.integration.phase2.test_pr2_00_challenges import (
    _service as _service,
)


class _BootstrapProofVerifier:
    def verify(self, authority: BootstrapAuthority) -> bool:
        return True

    def invalidate(self, authority: BootstrapAuthority) -> None:
        return None


@pytest.fixture
def role_expiry_env(phase2_database_url):
    """Build R1 identities through the existing Application ceremonies."""
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "0019_phase2_bootstrap_membership")
    engine = create_engine(phase2_database_url)
    service, _unused_operator, _unused_subject = _service(
        phase2_database_url, bootstrap_proof_verifier=_BootstrapProofVerifier()
    )
    # Bootstrap requires a verified local operator, independently of provisioning's subject.
    operator = VerifiedPrincipal(
        uuid4(), "r1-expiry", "OS_UID", "701", "r1-owner", datetime.now(UTC)
    )
    first = service.bootstrap_first_owner(
        BootstrapAuthority(
            operator.deployment_id,
            operator,
            701,
            operator.credential_id,
            "r1-secret",
            "a" * 64,
            "audit://r1-bootstrap",
        ),
        request_id=uuid4(),
        display_name="R1 owner",
        project_name="R1 project",
    )
    principal = VerifiedPrincipal(
        first.actor_id,
        operator.deployment_id,
        operator.subject_kind,
        operator.subject_value,
        operator.credential_id,
        operator.verified_at,
    )
    subject = VerifiedSubject(operator.deployment_id, "OS_UID", "702", "r1-member")
    actor = uuid4()
    service.provision_actor(
        ProvisionActor(
            principal,
            subject,
            actor,
            "R1 member",
            ProvisioningAttestation(
                actor,
                subject.deployment_id,
                subject.subject_kind,
                subject.subject_value,
                subject.credential_id,
                operator,
                "b" * 64,
                "audit://r1-provision",
                "independent proof",
            ),
            uuid4(),
        )
    )
    try:
        yield {
            "service": service,
            "engine": engine,
            "first": first,
            "principal": principal,
            "actor": actor,
            "url": phase2_database_url,
        }
    finally:
        engine.dispose()


def _expiry_role(e, role="VIEWER", *, request_id=None):
    return e["service"].assign_project_role(
        AssignProjectRole(
            e["principal"],
            e["first"].project_id,
            e["actor"],
            role,
            "R1 assignment",
            request_id or uuid4(),
        )
    )


def _schedule_expiry(e, role_id, *, seconds=60, request_id=None):
    with e["engine"].connect() as connection:
        expiry = connection.execute(
            text("SELECT clock_timestamp() + make_interval(secs => :seconds)"),
            {"seconds": seconds},
        ).scalar_one()
    e["service"].close_project_role(
        CloseProjectRole(
            e["principal"],
            e["first"].project_id,
            role_id,
            "R1 scheduled expiry",
            request_id or uuid4(),
            effective_until=expiry,
        )
    )
    return expiry


def _witness(engine, blocker_pid, before):
    """Observe a real backend wait before the scheduled expiry."""
    deadline = monotonic() + 10
    while monotonic() < deadline:
        with engine.connect() as observer:
            row = observer.execute(
                text(
                    "SELECT pid,xact_start,clock_timestamp() AS observed_at "
                    "FROM pg_stat_activity WHERE :blocker=ANY(pg_blocking_pids(pid))"
                ),
                {"blocker": blocker_pid},
            ).first()
            if row:
                assert row.pid != blocker_pid
                assert row.xact_start < before and row.observed_at < before
                return row.pid
        Event().wait(0.01)
    pytest.fail("no PostgreSQL lock witness before scheduled expiry")
