from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Event
from time import monotonic, sleep
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from researchbase.application.phase2_identity import (
    AssignProjectRole,
    BindLegacyActorSubject,
    BootstrapProofVerifier,
    IssueEnrollmentChallenge,
    OnboardingAttestation,
    Phase2CredentialVerifier,
    Phase2IdentityService,
    RevokeActorSubjectBinding,
    VerifiedSubject,
)
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.uow import SqlAlchemyUnitOfWork


class _NonceIssuer:
    def issue(self) -> bytes:
        return b"n" * 32


class _OperatorPolicy:
    def is_allowlisted(self, principal: VerifiedPrincipal) -> bool:
        return True


class _CredentialVerifier:
    def is_valid(self, principal: VerifiedPrincipal, at: datetime) -> bool:
        return True


class _ExpiringCredentialVerifier:
    def __init__(self, expires_at: datetime) -> None:
        self.expires_at = expires_at

    def is_valid(self, principal: VerifiedPrincipal, at: datetime) -> bool:
        return at < self.expires_at


class _SubjectCredentialVerifier:
    def is_valid(self, subject: VerifiedSubject, at: datetime) -> bool:
        return True


class _AttestationVerifier:
    def verify(self, attestation: OnboardingAttestation) -> bool:
        return True


def _service(
    database_url: str,
    credential_verifier: Phase2CredentialVerifier | None = None,
    bootstrap_proof_verifier: BootstrapProofVerifier | None = None,
) -> tuple[Phase2IdentityService, VerifiedPrincipal, VerifiedSubject]:
    engine = create_engine(database_url)
    factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    service = Phase2IdentityService(
        lambda: SqlAlchemyUnitOfWork(factory),
        nonce_issuer=_NonceIssuer(),
        operator_policy=_OperatorPolicy(),
        credential_verifier=credential_verifier or _CredentialVerifier(),
        subject_credential_verifier=_SubjectCredentialVerifier(),
        attestation_verifier=_AttestationVerifier(),
        bootstrap_proof_verifier=bootstrap_proof_verifier,
    )
    operator = VerifiedPrincipal(
        actor_id=uuid4(),
        deployment_id="deployment-c1",
        subject_kind="MTLS_URI",
        subject_value="spiffe://example.org/operators/1",
        credential_id="operator-cert-1",
        verified_at=datetime.now(UTC),
    )
    subject = VerifiedSubject(
        deployment_id=operator.deployment_id,
        subject_kind="OS_UID",
        subject_value="1001",
        credential_id="os-peer-1001",
    )
    return service, operator, subject


def _challenge_consumers_have_one_winner(
    phase2_database_url: str,
) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "0019_phase2_bootstrap_membership")
    engine = create_engine(phase2_database_url)
    service, operator, subject = _service(phase2_database_url)
    actor_id = uuid4()
    now = datetime.now(UTC)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO actors (id, actor_type, display_name, created_at) "
                "VALUES (:id, 'HUMAN', 'legacy subject', :created_at)"
            ),
            {"id": actor_id, "created_at": now},
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
    import hashlib

    attestation = OnboardingAttestation(
        challenge_id=ticket.challenge_id,
        actor_id=actor_id,
        deployment_id=subject.deployment_id,
        subject_kind=subject.subject_kind,
        subject_value=subject.subject_value,
        subject_credential_id=subject.credential_id,
        operator=operator,
        proof_method="OS_PEER",
        nonce_digest=hashlib.sha256(ticket.nonce).hexdigest(),
        proof_sha256="a" * 64,
        proof_record_ref="audit/sha256/onboarding-record",
        reason="legacy identity evidence verified",
    )
    bind_command = BindLegacyActorSubject(
        challenge_id=ticket.challenge_id,
        nonce=ticket.nonce,
        subject=subject,
        attestation=attestation,
        request_id=uuid4(),
    )

    def consume() -> bool:
        try:
            service.bind_legacy_actor_subject(bind_command)
        except ResearchBaseError:
            return False
        return True

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: consume(), range(2)))
        assert sum(results) == 1
        with engine.connect() as connection:
            assert (
                connection.execute(
                    text("SELECT status FROM actor_enrollment_challenges WHERE id = :id"),
                    {"id": ticket.challenge_id},
                ).scalar_one()
                == "CONSUMED"
            )
            assert (
                connection.execute(
                    text(
                        "SELECT count(*) FROM actor_subject_bindings "
                        "WHERE enrollment_challenge_id = :id"
                    ),
                    {"id": ticket.challenge_id},
                ).scalar_one()
                == 1
            )
    finally:
        engine.dispose()


def _challenge_expiry_after_required_lock_wait_is_denied(phase2_database_url: str) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "0019_phase2_bootstrap_membership")
    engine = create_engine(phase2_database_url)
    service, operator, subject = _service(phase2_database_url)
    actor_id = uuid4()
    now = datetime.now(UTC)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO actors (id, actor_type, display_name, created_at) "
                    "VALUES (:id, 'HUMAN', 'legacy subject', :created_at)"
                ),
                {"id": actor_id, "created_at": now},
            )
        ticket = service.issue_legacy_enrollment_challenge(
            IssueEnrollmentChallenge(
                actor_id=actor_id,
                subject=subject,
                operator=operator,
                proof_method="OS_PEER",
                request_id=uuid4(),
                lifetime=timedelta(seconds=3),
            )
        )
        import hashlib

        attestation = OnboardingAttestation(
            challenge_id=ticket.challenge_id,
            actor_id=actor_id,
            deployment_id=subject.deployment_id,
            subject_kind=subject.subject_kind,
            subject_value=subject.subject_value,
            subject_credential_id=subject.credential_id,
            operator=operator,
            proof_method="OS_PEER",
            nonce_digest=hashlib.sha256(ticket.nonce).hexdigest(),
            proof_sha256="c" * 64,
            proof_record_ref="audit/sha256/expiry-record",
            reason="legacy identity evidence verified",
        )
        bind_command = BindLegacyActorSubject(
            challenge_id=ticket.challenge_id,
            nonce=ticket.nonce,
            subject=subject,
            attestation=attestation,
            request_id=uuid4(),
        )
        holder = engine.connect()
        holding_transaction = holder.begin()
        holder.execute(
            text("SELECT id FROM actor_enrollment_challenges WHERE id = :id FOR UPDATE"),
            {"id": ticket.challenge_id},
        ).scalar_one()

        waiting = Event()

        def consume() -> ErrorCode | None:
            waiting.set()
            try:
                service.bind_legacy_actor_subject(bind_command)
            except ResearchBaseError as exc:
                return exc.code
            return None

        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(consume)
            assert waiting.wait(timeout=2)
            lock_deadline = monotonic() + 5
            blocked = False
            while monotonic() < lock_deadline:
                with engine.connect() as connection:
                    blocked = bool(
                        connection.execute(
                            text(
                                "SELECT EXISTS (SELECT 1 FROM pg_stat_activity "
                                "WHERE wait_event_type = 'Lock' "
                                "AND query ILIKE '%actor_enrollment_challenges%')"
                            )
                        ).scalar_one()
                    )
                    expired = bool(
                        connection.execute(
                            text(
                                "SELECT clock_timestamp() >= expires_at "
                                "FROM actor_enrollment_challenges WHERE id = :id"
                            ),
                            {"id": ticket.challenge_id},
                        ).scalar_one()
                    )
                if blocked and expired:
                    break
                sleep(0.02)
            assert blocked, "consumer must wait on the challenge row lock"
            assert expired, "test must release the required lock after challenge expiry"
            holding_transaction.rollback()
            assert future.result(timeout=5) is ErrorCode.ENROLLMENT_CHALLENGE_EXPIRED
        holder.close()
        with engine.connect() as connection:
            assert (
                connection.execute(
                    text("SELECT status FROM actor_enrollment_challenges WHERE id = :id"),
                    {"id": ticket.challenge_id},
                ).scalar_one()
                == "ISSUED"
            )
            assert (
                connection.execute(
                    text(
                        "SELECT count(*) FROM actor_subject_bindings "
                        "WHERE enrollment_challenge_id = :id"
                    ),
                    {"id": ticket.challenge_id},
                ).scalar_one()
                == 0
            )
    finally:
        engine.dispose()


def test_consumed_challenge_stays_unusable_after_binding_revocation(
    phase2_database_url: str,
) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "0019_phase2_bootstrap_membership")
    engine = create_engine(phase2_database_url)
    service, operator, subject = _service(phase2_database_url)
    actor_id = uuid4()
    now = datetime.now(UTC)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO actors (id, actor_type, display_name, created_at) "
                    "VALUES (:id, 'HUMAN', 'legacy subject', :created_at)"
                ),
                {"id": actor_id, "created_at": now},
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
        import hashlib

        attestation = OnboardingAttestation(
            challenge_id=ticket.challenge_id,
            actor_id=actor_id,
            deployment_id=subject.deployment_id,
            subject_kind=subject.subject_kind,
            subject_value=subject.subject_value,
            subject_credential_id=subject.credential_id,
            operator=operator,
            proof_method="OS_PEER",
            nonce_digest=hashlib.sha256(ticket.nonce).hexdigest(),
            proof_sha256="d" * 64,
            proof_record_ref="audit/sha256/revocation-record",
            reason="legacy identity evidence verified",
        )
        bind_command = BindLegacyActorSubject(
            challenge_id=ticket.challenge_id,
            nonce=ticket.nonce,
            subject=subject,
            attestation=attestation,
            request_id=uuid4(),
        )
        service.bind_legacy_actor_subject(bind_command)
        with engine.connect() as connection:
            binding_id = connection.execute(
                text("SELECT result_binding_id FROM actor_enrollment_challenges WHERE id = :id"),
                {"id": ticket.challenge_id},
            ).scalar_one()
        service.revoke_actor_subject_binding(
            RevokeActorSubjectBinding(
                operator=operator,
                binding_id=binding_id,
                reason="credential revoked for test",
                request_id=uuid4(),
            )
        )

        try:
            service.bind_legacy_actor_subject(bind_command)
        except ResearchBaseError as exc:
            assert exc.code is ErrorCode.SUBJECT_BINDING_UNPROVEN
        else:
            raise AssertionError("revoked binding must not make its challenge reusable")
        with engine.connect() as connection:
            assert (
                connection.execute(
                    text("SELECT status FROM actor_enrollment_challenges WHERE id = :id"),
                    {"id": ticket.challenge_id},
                ).scalar_one()
                == "CONSUMED"
            )
            assert (
                connection.execute(
                    text(
                        "SELECT count(*) FROM actor_subject_bindings "
                        "WHERE enrollment_challenge_id = :id"
                    ),
                    {"id": ticket.challenge_id},
                ).scalar_one()
                == 1
            )
    finally:
        engine.dispose()


def _owner_credential_expiry_after_project_lock_wait_denies_role_assignment(
    phase2_database_url: str,
) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "0019_phase2_bootstrap_membership")
    engine = create_engine(phase2_database_url)
    target_id, project_id, owner_membership_id, target_membership_id = (uuid4() for _ in range(4))
    owner_binding_id, owner_role_id = uuid4(), uuid4()
    owner_event_id = uuid4()
    with engine.begin() as connection:
        expiry = connection.execute(
            text("SELECT clock_timestamp() + interval '2 seconds'")
        ).scalar_one()

    service, owner, _subject = _service(phase2_database_url, _ExpiringCredentialVerifier(expiry))
    owner_id = owner.actor_id
    with engine.begin() as connection:
        now = connection.execute(text("SELECT clock_timestamp()")).scalar_one()
        connection.execute(
            text(
                "INSERT INTO actors (id, actor_type, display_name, created_at) "
                "VALUES (:owner, 'HUMAN', 'owner', :now), (:target, 'HUMAN', 'target', :now)"
            ),
            {"owner": owner_id, "target": target_id, "now": now},
        )
        connection.execute(
            text(
                "INSERT INTO projects (id, name, created_by, created_at) "
                "VALUES (:id, 'owner expiry test', :owner, :now)"
            ),
            {"id": project_id, "owner": owner_id, "now": now},
        )
        for membership_id, actor_id in (
            (owner_membership_id, owner_id),
            (target_membership_id, target_id),
        ):
            connection.execute(
                text(
                    "INSERT INTO project_memberships ("
                    "id, project_id, actor_id, status, started_at, created_by, created_at, "
                    "row_version"
                    ") VALUES (:id, :project, :actor, 'ACTIVE', :now, :owner, :now, 1)"
                ),
                {
                    "id": membership_id,
                    "project": project_id,
                    "actor": actor_id,
                    "owner": owner_id,
                    "now": now,
                },
            )
        connection.execute(
            text(
                "INSERT INTO project_membership_events ("
                "id, membership_id, event_kind, new_status, actor_id, occurred_at, reason, "
                "request_id"
                ") VALUES (:id, :membership, :kind, 'ACTIVE', :actor, :now, "
                "'membership established', :request)"
            ),
            [
                {
                    "id": uuid4(),
                    "membership": owner_membership_id,
                    "kind": "PROJECT_ENROLLMENT",
                    "actor": owner_id,
                    "now": now,
                    "request": uuid4(),
                },
                {
                    "id": uuid4(),
                    "membership": target_membership_id,
                    "kind": "ACTIVATED",
                    "actor": target_id,
                    "now": now,
                    "request": uuid4(),
                },
            ],
        )
        connection.execute(
            text(
                "INSERT INTO actor_subject_bindings ("
                "id, actor_id, deployment_id, subject_kind, subject_value, status, bound_at, "
                "operator_credential_id, subject_credential_id, proof_sha256, proof_record_ref, "
                "proof_kind, created_at, row_version) VALUES ("
                ":id, :actor, :deployment, 'MTLS_URI', :subject, 'ACTIVE', :now, 'operator-cert', "
                "'owner-cert', :proof, 'audit/sha256/owner', 'MTLS_CHALLENGE', :now, 1)"
            ),
            {
                "id": owner_binding_id,
                "actor": owner_id,
                "deployment": owner.deployment_id,
                "subject": owner.subject_value,
                "now": now,
                "proof": "e" * 64,
            },
        )
        connection.execute(
            text(
                "INSERT INTO actor_subject_binding_events ("
                "id, binding_id, actor_id, event_kind, operator_credential_id, "
                "subject_credential_id, proof_sha256, proof_record_ref, proof_kind, "
                "request_id, reason, occurred_at) VALUES ("
                ":id, :binding, :actor, 'PROVISIONED', 'operator-cert', 'owner-cert', :proof, "
                "'audit/sha256/owner', 'MTLS_CHALLENGE', :request, 'owner provisioned', :now)"
            ),
            {
                "id": uuid4(),
                "binding": owner_binding_id,
                "actor": owner_id,
                "proof": "e" * 64,
                "request": uuid4(),
                "now": now,
            },
        )
        connection.execute(
            text(
                "INSERT INTO project_role_assignments ("
                "id, membership_id, project_id, actor_id, role, effective_from, "
                "assigned_by, created_at, row_version"
                ") VALUES (:id, :membership, :project, :actor, 'OWNER', :now, :actor, :now, 1)"
            ),
            {
                "id": owner_role_id,
                "membership": owner_membership_id,
                "project": project_id,
                "actor": owner_id,
                "now": now,
            },
        )
        connection.execute(
            text(
                "INSERT INTO project_role_events ("
                "id, role_assignment_id, actor_id, event_kind, occurred_at, reason, request_id"
                ") VALUES (:id, :role, :actor, 'ASSIGNED', :now, 'initial owner', :request)"
            ),
            {
                "id": owner_event_id,
                "role": owner_role_id,
                "actor": owner_id,
                "now": now,
                "request": uuid4(),
            },
        )
        target_binding_id = uuid4()
        target_subject_value = f"target:{target_id}"
        connection.execute(
            text(
                "INSERT INTO actor_subject_bindings ("
                "id, actor_id, deployment_id, subject_kind, subject_value, status, bound_at, "
                "operator_credential_id, subject_credential_id, proof_sha256, proof_record_ref, "
                "proof_kind, created_at, row_version) VALUES ("
                ":id, :actor, :deployment, 'OS_UID', :subject, 'ACTIVE', :now, "
                "'operator-cert', 'target-cert', :proof, 'audit/sha256/target', "
                "'OS_PEER', :now, 1)"
            ),
            {
                "id": target_binding_id,
                "actor": target_id,
                "deployment": owner.deployment_id,
                "subject": target_subject_value,
                "now": now,
                "proof": "f" * 64,
            },
        )
        connection.execute(
            text(
                "INSERT INTO actor_subject_binding_events ("
                "id, binding_id, actor_id, event_kind, operator_credential_id, "
                "subject_credential_id, proof_sha256, proof_record_ref, proof_kind, "
                "request_id, reason, occurred_at) VALUES ("
                ":id, :binding, :actor, 'PROVISIONED', 'operator-cert', 'target-cert', "
                ":proof, 'audit/sha256/target', 'OS_PEER', :request, 'target provisioned', :now)"
            ),
            {
                "id": uuid4(),
                "binding": target_binding_id,
                "actor": target_id,
                "proof": "f" * 64,
                "request": uuid4(),
                "now": now,
            },
        )

    service.assign_project_role(
        AssignProjectRole(
            principal=owner,
            project_id=project_id,
            actor_id=target_id,
            role="VIEWER",
            reason="initial read-only access",
            request_id=uuid4(),
        )
    )

    holder = engine.connect()
    holding_transaction = holder.begin()
    holder.execute(
        text("SELECT id FROM projects WHERE id = :id FOR UPDATE"), {"id": project_id}
    ).scalar_one()
    waiting = Event()

    def assign() -> ErrorCode | None:
        waiting.set()
        try:
            service.assign_project_role(
                AssignProjectRole(
                    principal=owner,
                    project_id=project_id,
                    actor_id=target_id,
                    role="REVIEWER",
                    reason="review access",
                    request_id=uuid4(),
                )
            )
        except ResearchBaseError as exc:
            return exc.code
        return None

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(assign)
            assert waiting.wait(timeout=2)
            lock_deadline = monotonic() + 5
            blocked = False
            expired = False
            while monotonic() < lock_deadline:
                with engine.connect() as connection:
                    blocked = bool(
                        connection.execute(
                            text(
                                "SELECT EXISTS (SELECT 1 FROM pg_stat_activity "
                                "WHERE wait_event_type = 'Lock' "
                                "AND query ILIKE '%rb_phase2_lock_project%')"
                            )
                        ).scalar_one()
                    )
                    expired = bool(
                        connection.execute(
                            text("SELECT clock_timestamp() >= :expiry"), {"expiry": expiry}
                        ).scalar_one()
                    )
                if blocked and expired:
                    break
                sleep(0.02)
            assert blocked, "protected action must wait on the required project lock"
            assert expired, "test must release the project lock after OWNER credential expiry"
            holding_transaction.rollback()
            assert future.result(timeout=5) is ErrorCode.OWNER_CREDENTIAL_UNAVAILABLE
        with engine.connect() as connection:
            assert (
                connection.execute(
                    text(
                        "SELECT count(*) FROM project_role_assignments "
                        "WHERE project_id = :project AND actor_id = :actor AND role = 'REVIEWER'"
                    ),
                    {"project": project_id, "actor": target_id},
                ).scalar_one()
                == 0
            )
    finally:
        holder.close()
        engine.dispose()
