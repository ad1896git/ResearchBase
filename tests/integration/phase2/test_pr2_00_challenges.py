from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from time import monotonic, sleep
from typing import Any
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


class _TemporalTrace:
    def __init__(self) -> None:
        self.values: dict[str, object] = {"authorization_times": []}

    def clear(self) -> None:
        self.values = {"authorization_times": []}

    def wrap(self, repository: Any) -> Any:
        trace = self

        class ObservedRepository:
            def __getattr__(self, name: str) -> Any:
                return getattr(repository, name)

            def lock_deployment(self, deployment_id: str) -> None:
                tx_started_at, backend_pid, isolation_level, database_timezone = (
                    repository._session.execute(
                        text(
                            "SELECT transaction_timestamp(), pg_backend_pid(), "
                            "current_setting('transaction_isolation'), current_setting('TimeZone')"
                        )
                    ).one()
                )
                trace.values.update(
                    tx_started_at=tx_started_at,
                    backend_pid=backend_pid,
                    isolation_level=isolation_level,
                    database_timezone=database_timezone,
                )
                return repository.lock_deployment(deployment_id)

            def lock_project(self, project_id: object) -> None:
                tx_started_at, backend_pid = repository._session.execute(
                    text("SELECT transaction_timestamp(), pg_backend_pid()")
                ).one()
                trace.values.update(tx_started_at=tx_started_at, backend_pid=backend_pid)
                repository.lock_project(project_id)
                trace.values["lock_acquired_at"] = repository.database_time()

            def database_time(self) -> datetime:
                value = repository.database_time()
                cast_times = trace.values["authorization_times"]
                assert isinstance(cast_times, list)
                cast_times.append(value)
                return value

            def enrollment_challenge_for_update(self, challenge_id: object) -> Any:
                result = repository.enrollment_challenge_for_update(challenge_id)
                trace.values["lock_acquired_at"] = repository.database_time()
                if result is not None:
                    trace.values["challenge_after_lock"] = {
                        "id": str(result["id"]),
                        "issued_at": result["issued_at"],
                        "expires_at": result["expires_at"],
                        "status": result["status"],
                    }
                return result

            def active_membership_for_update(self, actor_id: object, project_id: object) -> Any:
                result = repository.active_membership_for_update(actor_id, project_id)
                trace.values["lock_acquired_at"] = repository.database_time()
                return result

        return ObservedRepository()


def _service(
    database_url: str,
    credential_verifier: Phase2CredentialVerifier | None = None,
    bootstrap_proof_verifier: BootstrapProofVerifier | None = None,
    temporal_trace: _TemporalTrace | None = None,
) -> tuple[Phase2IdentityService, VerifiedPrincipal, VerifiedSubject]:
    engine = create_engine(database_url)
    factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

    class ObservedUnitOfWork(SqlAlchemyUnitOfWork):
        def __enter__(self) -> ObservedUnitOfWork:
            super().__enter__()
            if temporal_trace is not None:
                self.phase2_identity = temporal_trace.wrap(self.phase2_identity)
            return self

    service = Phase2IdentityService(
        lambda: ObservedUnitOfWork(factory),
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


def _wait_for_database_lock(engine: Any, backend_pid: int) -> dict[str, object]:
    deadline = monotonic() + 5
    while monotonic() < deadline:
        with engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT clock_timestamp(), wait_event_type, wait_event, query "
                    "FROM pg_stat_activity "
                    "WHERE pid = :pid"
                ),
                {"pid": backend_pid},
            ).one_or_none()
        if row is not None and row.wait_event_type == "Lock":
            return {
                "observed_at": row[0],
                "wait_event_type": row.wait_event_type,
                "wait_event": row.wait_event,
                "query": row.query,
            }
        sleep(0.01)
    raise AssertionError(f"PostgreSQL backend {backend_pid} did not enter a lock wait")


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
    trace = _TemporalTrace()
    service, operator, subject = _service(phase2_database_url, temporal_trace=trace)
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
        trace.clear()
        trace.values.update(
            challenge_id=str(ticket.challenge_id),
            challenge_issued_at=ticket.issued_at,
            challenge_expires_at=ticket.expires_at,
            application_timestamp_type=type(ticket.expires_at).__name__,
            application_timestamp_timezone=str(ticket.expires_at.tzinfo),
        )
        with engine.connect() as connection:
            timestamp_columns = (
                connection.execute(
                    text(
                        "SELECT column_name, data_type, datetime_precision "
                        "FROM information_schema.columns "
                        "WHERE table_schema = 'public' "
                        "AND table_name = 'actor_enrollment_challenges' "
                        "AND column_name IN ('issued_at', 'expires_at') "
                        "ORDER BY column_name"
                    )
                )
                .mappings()
                .all()
            )
        trace.values["database_timestamp_columns"] = [dict(row) for row in timestamp_columns]
        assert {row["column_name"] for row in timestamp_columns} == {
            "issued_at",
            "expires_at",
        }
        assert all(row["data_type"] == "timestamp with time zone" for row in timestamp_columns)
        assert all(row["datetime_precision"] == 6 for row in timestamp_columns)
        assert ticket.issued_at.utcoffset() == timedelta(0)
        assert ticket.expires_at.utcoffset() == timedelta(0)
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

        def consume() -> ErrorCode | None:
            try:
                service.bind_legacy_actor_subject(bind_command)
            except ResearchBaseError as exc:
                return exc.code
            return None

        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(consume)
            lock_deadline = monotonic() + 5
            while "backend_pid" not in trace.values and monotonic() < lock_deadline:
                sleep(0.005)
            backend_pid = trace.values.get("backend_pid")
            assert isinstance(backend_pid, int)
            lock_wait = _wait_for_database_lock(engine, backend_pid)
            lock_wait_started_at = lock_wait["observed_at"]
            assert isinstance(lock_wait_started_at, datetime)
            assert "actor_enrollment_challenges" in str(lock_wait["query"])
            expiry_at = ticket.expires_at
            expiry_safety_margin = timedelta(milliseconds=250)
            assert lock_wait_started_at < expiry_at
            while True:
                with engine.connect() as connection:
                    db_clock = connection.execute(text("SELECT clock_timestamp()")).scalar_one()
                if db_clock >= expiry_at + expiry_safety_margin:
                    expiry_crossed_at = db_clock
                    break
                sleep(0.005)
            holding_transaction.rollback()
            with engine.connect() as connection:
                lock_released_at = connection.execute(text("SELECT clock_timestamp()")).scalar_one()
            result = future.result(timeout=10)
        lock_acquired_at = trace.values["lock_acquired_at"]
        authorization_times = trace.values["authorization_times"]
        assert isinstance(lock_acquired_at, datetime)
        assert isinstance(authorization_times, list) and authorization_times
        authorization_checked_at = authorization_times[-1]
        tx_started_at = trace.values["tx_started_at"]
        assert isinstance(tx_started_at, datetime)
        holder.close()
        with engine.connect() as connection:
            persisted = {
                "challenge_status": connection.execute(
                    text("SELECT status FROM actor_enrollment_challenges WHERE id = :id"),
                    {"id": ticket.challenge_id},
                ).scalar_one(),
                "bindings": connection.execute(
                    text(
                        "SELECT count(*) FROM actor_subject_bindings "
                        "WHERE enrollment_challenge_id = :id"
                    ),
                    {"id": ticket.challenge_id},
                ).scalar_one(),
                "binding_events": connection.execute(
                    text(
                        "SELECT count(*) FROM actor_subject_binding_events WHERE actor_id = :actor"
                    ),
                    {"actor": actor_id},
                ).scalar_one(),
            }
        trace.values.update(
            expiry_at=expiry_at,
            lock_wait_started_at=lock_wait_started_at,
            observed_wait=lock_wait,
            expiry_crossed_at=expiry_crossed_at,
            expiry_safety_margin=expiry_safety_margin,
            lock_released_at_observed=lock_released_at,
            authorization_clock_timestamp=authorization_checked_at,
            effect_result=(
                "DENY" if result is ErrorCode.ENROLLMENT_CHALLENGE_EXPIRED else "SUCCESS"
            ),
            persisted_effects=persisted,
        )
        print("TEMP-AUTH challenge proof " + json.dumps(trace.values, default=str, sort_keys=True))
        assert result is ErrorCode.ENROLLMENT_CHALLENGE_EXPIRED
        assert persisted == {"challenge_status": "ISSUED", "bindings": 0, "binding_events": 0}
        assert tx_started_at < expiry_at
        assert lock_wait_started_at < expiry_at
        assert expiry_crossed_at >= expiry_at + expiry_safety_margin
        assert lock_released_at >= expiry_at + expiry_safety_margin
        assert lock_acquired_at >= expiry_at + expiry_safety_margin
        assert authorization_checked_at >= lock_acquired_at
        assert authorization_checked_at >= expiry_at
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
    *,
    further_wait: bool = False,
) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "0019_phase2_bootstrap_membership")
    engine = create_engine(phase2_database_url)
    target_id, project_id, owner_membership_id, target_membership_id = (uuid4() for _ in range(4))
    owner_binding_id, owner_role_id = uuid4(), uuid4()
    owner_event_id = uuid4()
    credential_verifier = _ExpiringCredentialVerifier(datetime.max.replace(tzinfo=UTC))
    trace = _TemporalTrace()
    service, owner, _subject = _service(
        phase2_database_url, credential_verifier, temporal_trace=trace
    )
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

    owner = replace(owner, verified_at=now)
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
    if further_wait:
        holder.execute(text("SELECT id FROM actors WHERE id = :id FOR UPDATE"), {"id": target_id})
    else:
        holder.execute(
            text("SELECT id FROM projects WHERE id = :id FOR UPDATE"), {"id": project_id}
        ).scalar_one()
    with engine.begin() as connection:
        expiry = connection.execute(
            text("SELECT clock_timestamp() + interval '2 seconds'")
        ).scalar_one()
    credential_verifier.expires_at = expiry
    trace.clear()

    def assign() -> ErrorCode | None:
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
            lock_deadline = monotonic() + 5
            while "backend_pid" not in trace.values and monotonic() < lock_deadline:
                sleep(0.005)
            backend_pid = trace.values.get("backend_pid")
            assert isinstance(backend_pid, int)
            lock_wait = _wait_for_database_lock(engine, backend_pid)
            lock_wait_started_at = lock_wait["observed_at"]
            assert isinstance(lock_wait_started_at, datetime)
            if further_wait:
                assert "project_memberships" in str(lock_wait["query"])
            else:
                assert "rb_phase2_lock_project" in str(lock_wait["query"])
            authorization_times = trace.values["authorization_times"]
            assert isinstance(authorization_times, list)
            if further_wait:
                assert authorization_times and authorization_times[0] < expiry
            assert lock_wait_started_at < expiry
            with engine.connect() as connection:
                while connection.execute(
                    text("SELECT clock_timestamp() < :expiry"), {"expiry": expiry}
                ).scalar_one():
                    sleep(0.01)
            holding_transaction.rollback()
            assert future.result(timeout=5) is ErrorCode.OWNER_CREDENTIAL_UNAVAILABLE
        lock_acquired_at = trace.values["lock_acquired_at"]
        authorization_times = trace.values["authorization_times"]
        assert isinstance(lock_acquired_at, datetime)
        assert isinstance(authorization_times, list) and authorization_times
        tx_started_at = trace.values["tx_started_at"]
        assert isinstance(tx_started_at, datetime) and tx_started_at < expiry
        assert lock_acquired_at >= expiry
        assert authorization_times[-1] >= lock_acquired_at
        assert authorization_times[-1] > expiry
        if further_wait:
            assert len(authorization_times) >= 2
            assert authorization_times[-1] > authorization_times[0]
        with engine.connect() as connection:
            protected_counts = {
                "memberships": connection.execute(
                    text(
                        "SELECT count(*) FROM project_memberships "
                        "WHERE project_id=:p AND actor_id=:a"
                    ),
                    {"p": project_id, "a": target_id},
                ).scalar_one(),
                "roles": connection.execute(
                    text(
                        "SELECT count(*) FROM project_role_assignments "
                        "WHERE project_id=:p AND actor_id=:a"
                    ),
                    {"p": project_id, "a": target_id},
                ).scalar_one(),
                "membership_events": connection.execute(
                    text(
                        "SELECT count(*) FROM project_membership_events e "
                        "JOIN project_memberships m ON m.id=e.membership_id "
                        "WHERE m.project_id=:p AND m.actor_id=:a"
                    ),
                    {"p": project_id, "a": target_id},
                ).scalar_one(),
                "role_events": connection.execute(
                    text(
                        "SELECT count(*) FROM project_role_events e "
                        "JOIN project_role_assignments r ON r.id=e.role_assignment_id "
                        "WHERE r.project_id=:p AND r.actor_id=:a"
                    ),
                    {"p": project_id, "a": target_id},
                ).scalar_one(),
            }
            assert protected_counts == {
                "memberships": 1,
                "roles": 1,
                "membership_events": 1,
                "role_events": 1,
            }
        trace.values.update(
            expiry_at=expiry,
            lock_wait_started_at=lock_wait_started_at,
            observed_wait=lock_wait,
            effect_result="DENY",
            protected_counts=protected_counts,
            distinct_further_wait=further_wait,
        )
        print("TEMP-AUTH OWNER proof " + json.dumps(trace.values, default=str, sort_keys=True))
    finally:
        holder.close()
        engine.dispose()
