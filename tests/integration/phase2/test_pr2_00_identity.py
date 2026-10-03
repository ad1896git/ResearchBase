from __future__ import annotations

import hashlib
from datetime import timedelta
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from tests.integration.phase2.test_pr2_00_challenges import _service

from researchbase.application.phase2_identity import (
    BindLegacyActorSubject,
    IssueEnrollmentChallenge,
    OnboardingAttestation,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


def _upgrade(database_url: str) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "0019_phase2_bootstrap_membership")


def test_operator_and_subject_must_be_independent(phase2_database_url: str) -> None:
    _upgrade(phase2_database_url)
    engine = create_engine(phase2_database_url)
    service, operator, subject = _service(phase2_database_url)
    actor_id = uuid4()
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO actors (id, actor_type, display_name, created_at) "
                "VALUES (:id, 'HUMAN', 'legacy actor', clock_timestamp())"
            ),
            {"id": actor_id},
        )
    same_principal_subject = subject.__class__(
        deployment_id=operator.deployment_id,
        subject_kind=operator.subject_kind,
        subject_value=operator.subject_value,
        credential_id=operator.credential_id,
    )

    try:
        with pytest.raises(ResearchBaseError) as exc_info:
            service.issue_legacy_enrollment_challenge(
                IssueEnrollmentChallenge(
                    actor_id=actor_id,
                    subject=same_principal_subject,
                    operator=operator,
                    proof_method="MTLS_CHALLENGE",
                    request_id=uuid4(),
                    lifetime=timedelta(minutes=5),
                )
            )
        assert exc_info.value.code is ErrorCode.SUBJECT_BINDING_UNPROVEN
        with engine.connect() as connection:
            assert (
                connection.execute(
                    text("SELECT count(*) FROM actor_enrollment_challenges")
                ).scalar_one()
                == 0
            )
    finally:
        engine.dispose()


def test_mismatched_live_challenge_proof_is_refused_without_consumption(
    phase2_database_url: str,
) -> None:
    _upgrade(phase2_database_url)
    engine = create_engine(phase2_database_url)
    service, operator, subject = _service(phase2_database_url)
    actor_id = uuid4()
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO actors (id, actor_type, display_name, created_at) "
                "VALUES (:id, 'HUMAN', 'legacy actor', clock_timestamp())"
            ),
            {"id": actor_id},
        )
    ticket = service.issue_legacy_enrollment_challenge(
        IssueEnrollmentChallenge(
            actor_id=actor_id,
            subject=subject,
            operator=operator,
            proof_method="OS_PEER",
            request_id=uuid4(),
            lifetime=timedelta(minutes=5),
        )
    )
    attestation = OnboardingAttestation(
        challenge_id=ticket.challenge_id,
        actor_id=actor_id,
        deployment_id=subject.deployment_id,
        subject_kind=subject.subject_kind,
        subject_value=subject.subject_value,
        subject_credential_id=subject.credential_id,
        operator=operator,
        proof_method="OS_PEER",
        nonce_digest=hashlib.sha256(b"different nonce").hexdigest(),
        proof_sha256="a" * 64,
        proof_record_ref="audit/sha256/mismatched-proof",
        reason="test malformed live proof",
    )

    try:
        with pytest.raises(ResearchBaseError) as exc_info:
            service.bind_legacy_actor_subject(
                BindLegacyActorSubject(
                    challenge_id=ticket.challenge_id,
                    nonce=ticket.nonce,
                    subject=subject,
                    attestation=attestation,
                    request_id=uuid4(),
                )
            )
        assert exc_info.value.code is ErrorCode.SUBJECT_BINDING_UNPROVEN
        with engine.connect() as connection:
            assert (
                connection.execute(
                    text("SELECT status FROM actor_enrollment_challenges WHERE id = :challenge"),
                    {"challenge": ticket.challenge_id},
                ).scalar_one()
                == "ISSUED"
            )
            assert (
                connection.execute(text("SELECT count(*) FROM actor_subject_bindings")).scalar_one()
                == 0
            )
    finally:
        engine.dispose()
