from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier, Event
from time import monotonic, sleep
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from tests.integration.phase2.test_pr2_00_challenges import (
    _service,
)

from researchbase.application.phase2_identity import (
    AssignProjectRole,
    BootstrapAuthority,
    CloseProjectRole,
    EnrollLegacyProjectOwner,
    ProvisionActor,
    ProvisioningAttestation,
    ReactivateProjectMembership,
    RevokeActorSubjectBinding,
    SuspendProjectMembership,
    VerifiedSubject,
)
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


class _BootstrapProofVerifier:
    def verify(self, authority: BootstrapAuthority) -> bool:
        return True

    def invalidate(self, authority: BootstrapAuthority) -> None:
        return None


def test_first_owner_bootstrap_is_atomic_and_permanently_closes(
    phase2_database_url: str,
) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "0019_phase2_bootstrap_membership")
    engine = create_engine(phase2_database_url)
    service, _principal, _subject = _service(
        phase2_database_url, bootstrap_proof_verifier=_BootstrapProofVerifier()
    )
    uid = 701
    verified_operator = VerifiedPrincipal(
        actor_id=uuid4(),
        deployment_id="deployment-bootstrap",
        subject_kind="OS_UID",
        subject_value=str(uid),
        credential_id="os-credential-701",
        verified_at=datetime.now(UTC),
    )
    authority = BootstrapAuthority(
        deployment_id="deployment-bootstrap",
        operator=verified_operator,
        verified_os_uid=uid,
        subject_credential_id="os-credential-701",
        secret_digest_id="secret-digest-ref",
        proof_sha256="f" * 64,
        proof_record_ref="audit/sha256/bootstrap-record",
    )
    request_id = uuid4()
    try:
        result = service.bootstrap_first_owner(
            authority,
            request_id=request_id,
            display_name="  First Owner  ",
            project_name="  Initial Project  ",
        )
        with engine.connect() as connection:
            assert connection.execute(text("SELECT count(*) FROM actors")).scalar_one() == 1
            assert connection.execute(text("SELECT count(*) FROM projects")).scalar_one() == 1
            assert (
                connection.execute(text("SELECT count(*) FROM bootstrap_records")).scalar_one() == 1
            )
            assert (
                connection.execute(
                    text("SELECT count(*) FROM project_role_assignments WHERE role = 'OWNER'")
                ).scalar_one()
                == 1
            )
            assert (
                connection.execute(
                    text("SELECT display_name FROM actors WHERE id = :id"),
                    {"id": result.actor_id},
                ).scalar_one()
                == "First Owner"
            )
            assert (
                connection.execute(
                    text("SELECT name FROM projects WHERE id = :id"),
                    {"id": result.project_id},
                ).scalar_one()
                == "Initial Project"
            )

        try:
            service.bootstrap_first_owner(
                authority,
                request_id=request_id,
                display_name="First Owner",
                project_name="Initial Project",
            )
        except ResearchBaseError as exc:
            assert exc.code is ErrorCode.BOOTSTRAP_CLOSED
        else:
            raise AssertionError("successful bootstrap must permanently close the ceremony")
    finally:
        engine.dispose()


def test_concurrent_first_owner_bootstrap_has_one_committed_result(
    phase2_database_url: str,
) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "0019_phase2_bootstrap_membership")
    service, _principal, _subject = _service(
        phase2_database_url, bootstrap_proof_verifier=_BootstrapProofVerifier()
    )
    uid = 710
    operator = VerifiedPrincipal(
        actor_id=uuid4(),
        deployment_id="deployment-bootstrap-race",
        subject_kind="OS_UID",
        subject_value=str(uid),
        credential_id="os-credential-710",
        verified_at=datetime.now(UTC),
    )
    authority = BootstrapAuthority(
        deployment_id=operator.deployment_id,
        operator=operator,
        verified_os_uid=uid,
        subject_credential_id=operator.credential_id,
        secret_digest_id="secret-digest-ref",
        proof_sha256="7" * 64,
        proof_record_ref="audit/sha256/bootstrap-race",
    )
    gate = Barrier(2)

    def attempt() -> str:
        gate.wait(timeout=5)
        try:
            service.bootstrap_first_owner(
                authority,
                request_id=uuid4(),
                display_name="Race Owner",
                project_name="Race Project",
            )
        except ResearchBaseError as exc:
            return exc.code.value
        return "SUCCESS"

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(attempt), pool.submit(attempt)]
        outcomes = sorted(future.result(timeout=10) for future in futures)
    assert outcomes == ["BOOTSTRAP_CLOSED", "SUCCESS"]


def test_invalid_legacy_state_rejects_bootstrap_without_protected_writes(
    phase2_database_url: str,
) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "0019_phase2_bootstrap_membership")
    engine = create_engine(phase2_database_url)
    service, _principal, _subject = _service(
        phase2_database_url, bootstrap_proof_verifier=_BootstrapProofVerifier()
    )
    actor_id = uuid4()
    with engine.begin() as connection:
        now = connection.execute(text("SELECT clock_timestamp()")).scalar_one()
        connection.execute(
            text(
                "INSERT INTO actors (id, actor_type, display_name, created_at) "
                "VALUES (:id, 'HUMAN', 'legacy', :now)"
            ),
            {"id": actor_id, "now": now},
        )
        connection.execute(text("DROP INDEX uq_actors_external_key"))
        connection.execute(
            text("UPDATE actors SET external_key = 'duplicate' WHERE id = :id"),
            {"id": actor_id},
        )
        connection.execute(
            text(
                "INSERT INTO actors (id, actor_type, display_name, external_key, created_at) "
                "VALUES (:id, 'HUMAN', 'duplicate', 'duplicate', :now)"
            ),
            {"id": uuid4(), "now": now},
        )
    operator = VerifiedPrincipal(
        actor_id=uuid4(),
        deployment_id="deployment-invalid-legacy",
        subject_kind="OS_UID",
        subject_value="740",
        credential_id="os-credential-740",
        verified_at=datetime.now(UTC),
    )
    authority = BootstrapAuthority(
        deployment_id=operator.deployment_id,
        operator=operator,
        verified_os_uid=740,
        subject_credential_id=operator.credential_id,
        secret_digest_id="secret-digest-ref",
        proof_sha256="a" * 64,
        proof_record_ref="audit/sha256/invalid-legacy",
    )
    try:
        errors = []
        for _ in range(2):
            try:
                service.bootstrap_first_owner(
                    authority,
                    request_id=uuid4(),
                    display_name="Must not be created",
                    project_name="Must not be created",
                )
            except ResearchBaseError as exc:
                assert exc.code is ErrorCode.LEGACY_STATE_INVALID
                errors.append(exc.to_dict())
            else:
                raise AssertionError("invalid legacy state must fail closed")
        assert errors[0] == errors[1]
        with engine.connect() as connection:
            assert connection.execute(text("SELECT count(*) FROM actors")).scalar_one() == 2
            assert connection.execute(text("SELECT count(*) FROM projects")).scalar_one() == 0
            assert (
                connection.execute(text("SELECT count(*) FROM bootstrap_records")).scalar_one() == 0
            )
            assert (
                connection.execute(text("SELECT count(*) FROM project_memberships")).scalar_one()
                == 0
            )
            assert (
                connection.execute(text("SELECT count(*) FROM project_role_events")).scalar_one()
                == 0
            )
    finally:
        engine.dispose()


@pytest.mark.parametrize("invalid_column", ["actor_type", "lifecycle_status"])
def test_null_legacy_state_rejects_bootstrap_without_protected_writes(
    phase2_database_url: str, invalid_column: str
) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "0019_phase2_bootstrap_membership")
    engine = create_engine(phase2_database_url)
    service, _principal, _subject = _service(
        phase2_database_url, bootstrap_proof_verifier=_BootstrapProofVerifier()
    )
    actor_id, project_id = uuid4(), uuid4()
    with engine.begin() as connection:
        now = connection.execute(text("SELECT clock_timestamp()")).scalar_one()
        connection.execute(
            text(
                "INSERT INTO actors (id, actor_type, display_name, created_at) "
                "VALUES (:id, 'HUMAN', 'legacy', :now)"
            ),
            {"id": actor_id, "now": now},
        )
        if invalid_column == "lifecycle_status":
            connection.execute(
                text(
                    "INSERT INTO projects (id, name, created_by, created_at) "
                    "VALUES (:id, 'legacy', :actor, :now)"
                ),
                {"id": project_id, "actor": actor_id, "now": now},
            )
    with engine.begin() as connection:
        if invalid_column == "actor_type":
            connection.execute(text("ALTER TABLE actors DROP CONSTRAINT ck_actors_actor_type"))
            connection.execute(text("ALTER TABLE actors ALTER COLUMN actor_type DROP NOT NULL"))
            connection.execute(
                text("UPDATE actors SET actor_type = NULL WHERE id = :id"), {"id": actor_id}
            )
        else:
            connection.execute(
                text("ALTER TABLE projects DROP CONSTRAINT ck_projects_lifecycle_status")
            )
            connection.execute(
                text("ALTER TABLE projects ALTER COLUMN lifecycle_status DROP NOT NULL")
            )
            connection.execute(
                text("UPDATE projects SET lifecycle_status = NULL WHERE id = :id"),
                {"id": project_id},
            )
    operator = VerifiedPrincipal(
        actor_id=uuid4(),
        deployment_id="deployment-null-legacy",
        subject_kind="OS_UID",
        subject_value="742",
        credential_id="os-credential-742",
        verified_at=datetime.now(UTC),
    )
    authority = BootstrapAuthority(
        deployment_id=operator.deployment_id,
        operator=operator,
        verified_os_uid=742,
        subject_credential_id=operator.credential_id,
        secret_digest_id="secret-digest-ref",
        proof_sha256="d" * 64,
        proof_record_ref="audit/sha256/null-legacy",
    )
    try:
        errors = []
        for _ in range(2):
            try:
                service.bootstrap_first_owner(
                    authority,
                    request_id=uuid4(),
                    display_name="Must not be created",
                    project_name="Must not be created",
                )
            except ResearchBaseError as exc:
                assert exc.code is ErrorCode.LEGACY_STATE_INVALID
                errors.append(exc.to_dict())
            else:
                raise AssertionError("NULL legacy state must fail closed")
        assert errors[0] == errors[1]
        with engine.connect() as connection:
            assert connection.execute(text("SELECT count(*) FROM actors")).scalar_one() == 1
            assert connection.execute(text("SELECT count(*) FROM projects")).scalar_one() == (
                1 if invalid_column == "lifecycle_status" else 0
            )
            assert (
                connection.execute(text("SELECT count(*) FROM bootstrap_records")).scalar_one() == 0
            )
            assert (
                connection.execute(text("SELECT count(*) FROM project_memberships")).scalar_one()
                == 0
            )
            assert (
                connection.execute(text("SELECT count(*) FROM project_role_events")).scalar_one()
                == 0
            )
    finally:
        engine.dispose()


def test_bootstrap_preflight_reads_state_after_required_table_lock_wait(
    phase2_database_url: str,
) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "0019_phase2_bootstrap_membership")
    engine = create_engine(phase2_database_url)
    service, _principal, _subject = _service(
        phase2_database_url, bootstrap_proof_verifier=_BootstrapProofVerifier()
    )
    with engine.begin() as connection:
        connection.execute(text("DROP INDEX uq_actors_external_key"))
    holder = engine.connect()
    transaction = holder.begin()
    holder.execute(text("LOCK TABLE actors IN ROW EXCLUSIVE MODE"))
    actor_ids = uuid4(), uuid4()
    now = datetime.now(UTC)
    holder.execute(
        text(
            "INSERT INTO actors (id, actor_type, display_name, external_key, created_at) "
            "VALUES (:a, 'HUMAN', 'concurrent legacy A', 'duplicate', :now), "
            "(:b, 'HUMAN', 'concurrent legacy B', 'duplicate', :now)"
        ),
        {"a": actor_ids[0], "b": actor_ids[1], "now": now},
    )
    operator = VerifiedPrincipal(
        actor_id=uuid4(),
        deployment_id="deployment-legacy-race",
        subject_kind="OS_UID",
        subject_value="742",
        credential_id="os-credential-742",
        verified_at=datetime.now(UTC),
    )
    authority = BootstrapAuthority(
        deployment_id=operator.deployment_id,
        operator=operator,
        verified_os_uid=742,
        subject_credential_id=operator.credential_id,
        secret_digest_id="secret-digest-ref",
        proof_sha256="d" * 64,
        proof_record_ref="audit/sha256/bootstrap-legacy-race",
    )
    started = Event()

    def attempt() -> ErrorCode | None:
        started.set()
        try:
            service.bootstrap_first_owner(
                authority,
                request_id=uuid4(),
                display_name="Must remain absent",
                project_name="Must remain absent",
            )
        except ResearchBaseError as exc:
            return exc.code
        return None

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(attempt)
            assert started.wait(timeout=2)
            deadline = monotonic() + 5
            blocked = False
            while monotonic() < deadline:
                with engine.connect() as connection:
                    blocked = bool(
                        connection.execute(
                            text(
                                "SELECT EXISTS (SELECT 1 FROM pg_stat_activity "
                                "WHERE wait_event_type='Lock' "
                                "AND query ILIKE '%LOCK TABLE actors, projects%')"
                            )
                        ).scalar_one()
                    )
                if blocked:
                    break
                sleep(0.01)
            assert blocked, "bootstrap must block on the legacy tables before its preflight read"
            transaction.commit()
            assert future.result(timeout=5) is ErrorCode.LEGACY_STATE_INVALID
        with engine.connect() as connection:
            assert connection.execute(text("SELECT count(*) FROM actors")).scalar_one() == 2
            assert connection.execute(text("SELECT count(*) FROM projects")).scalar_one() == 0
            assert (
                connection.execute(text("SELECT count(*) FROM bootstrap_records")).scalar_one() == 0
            )
    finally:
        if transaction.is_active:
            transaction.rollback()
        holder.close()
        engine.dispose()


def test_new_project_is_created_with_continuous_owner_coverage(
    phase2_database_url: str,
) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "0019_phase2_bootstrap_membership")
    engine = create_engine(phase2_database_url)
    service, _principal, _subject = _service(
        phase2_database_url, bootstrap_proof_verifier=_BootstrapProofVerifier()
    )
    uid = 702
    operator = VerifiedPrincipal(
        actor_id=uuid4(),
        deployment_id="deployment-project-create",
        subject_kind="OS_UID",
        subject_value=str(uid),
        credential_id="os-credential-702",
        verified_at=datetime.now(UTC),
    )
    authority = BootstrapAuthority(
        deployment_id=operator.deployment_id,
        operator=operator,
        verified_os_uid=uid,
        subject_credential_id=operator.credential_id,
        secret_digest_id="secret-digest-ref",
        proof_sha256="b" * 64,
        proof_record_ref="audit/sha256/project-owner-bootstrap",
    )
    try:
        first = service.bootstrap_first_owner(
            authority,
            request_id=uuid4(),
            display_name="Project Owner",
            project_name="First project",
        )
        principal = VerifiedPrincipal(
            actor_id=first.actor_id,
            deployment_id=operator.deployment_id,
            subject_kind=operator.subject_kind,
            subject_value=operator.subject_value,
            credential_id=operator.credential_id,
            verified_at=datetime.now(UTC),
        )
        new_project_id = service.create_project_with_owner(
            principal,
            name="Second project",
            request_id=uuid4(),
        )
        with engine.connect() as connection:
            assert (
                connection.execute(
                    text("SELECT name FROM projects WHERE id = :id"),
                    {"id": new_project_id},
                ).scalar_one()
                == "Second project"
            )
            assert (
                connection.execute(
                    text(
                        "SELECT count(*) FROM project_memberships "
                        "WHERE project_id = :project AND actor_id = :actor AND status = 'ACTIVE'"
                    ),
                    {"project": new_project_id, "actor": first.actor_id},
                ).scalar_one()
                == 1
            )
            assert (
                connection.execute(
                    text(
                        "SELECT count(*) FROM project_role_assignments "
                        "WHERE project_id = :project AND actor_id = :actor AND role = 'OWNER' "
                        "AND effective_until IS NULL"
                    ),
                    {"project": new_project_id, "actor": first.actor_id},
                ).scalar_one()
                == 1
            )
    finally:
        engine.dispose()


def test_closing_last_owner_role_is_denied_without_history_loss(
    phase2_database_url: str,
) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "0019_phase2_bootstrap_membership")
    engine = create_engine(phase2_database_url)
    service, _principal, _subject = _service(
        phase2_database_url, bootstrap_proof_verifier=_BootstrapProofVerifier()
    )
    uid = 703
    operator = VerifiedPrincipal(
        actor_id=uuid4(),
        deployment_id="deployment-last-owner",
        subject_kind="OS_UID",
        subject_value=str(uid),
        credential_id="os-credential-703",
        verified_at=datetime.now(UTC),
    )
    authority = BootstrapAuthority(
        deployment_id=operator.deployment_id,
        operator=operator,
        verified_os_uid=uid,
        subject_credential_id=operator.credential_id,
        secret_digest_id="secret-digest-ref",
        proof_sha256="c" * 64,
        proof_record_ref="audit/sha256/last-owner-bootstrap",
    )
    try:
        first = service.bootstrap_first_owner(
            authority,
            request_id=uuid4(),
            display_name="Last Owner",
            project_name="Protected project",
        )
        with engine.connect() as connection:
            verified_at = connection.execute(
                text("SELECT clock_timestamp() - interval '1 second'")
            ).scalar_one()
        principal = VerifiedPrincipal(
            actor_id=first.actor_id,
            deployment_id=operator.deployment_id,
            subject_kind=operator.subject_kind,
            subject_value=operator.subject_value,
            credential_id=operator.credential_id,
            verified_at=verified_at,
        )
        with engine.connect() as connection:
            role_id = connection.execute(
                text(
                    "SELECT id FROM project_role_assignments "
                    "WHERE project_id = :project AND actor_id = :actor AND role = 'OWNER'"
                ),
                {"project": first.project_id, "actor": first.actor_id},
            ).scalar_one()
            role_count = connection.execute(
                text("SELECT count(*) FROM project_role_assignments")
            ).scalar_one()
        try:
            service.close_project_role(
                CloseProjectRole(
                    principal=principal,
                    project_id=first.project_id,
                    role_assignment_id=role_id,
                    reason="attempt to remove final owner",
                    request_id=uuid4(),
                )
            )
        except ResearchBaseError as exc:
            assert exc.code is ErrorCode.OWNER_COVERAGE_GAP
        else:
            raise AssertionError("closing the final OWNER role must fail")
        with engine.connect() as connection:
            assert (
                connection.execute(
                    text("SELECT effective_until FROM project_role_assignments WHERE id = :id"),
                    {"id": role_id},
                ).scalar_one()
                is None
            )
            assert (
                connection.execute(
                    text("SELECT count(*) FROM project_role_assignments")
                ).scalar_one()
                == role_count
            )
    finally:
        engine.dispose()


def test_provision_actor_creates_bound_human_without_project_role(
    phase2_database_url: str,
) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "0019_phase2_bootstrap_membership")
    engine = create_engine(phase2_database_url)
    service, _principal, _subject = _service(
        phase2_database_url, bootstrap_proof_verifier=_BootstrapProofVerifier()
    )
    uid = 704
    operator = VerifiedPrincipal(
        actor_id=uuid4(),
        deployment_id="deployment-provisioning",
        subject_kind="OS_UID",
        subject_value=str(uid),
        credential_id="bootstrap-os-credential-704",
        verified_at=datetime.now(UTC),
    )
    authority = BootstrapAuthority(
        deployment_id=operator.deployment_id,
        operator=operator,
        verified_os_uid=uid,
        subject_credential_id=operator.credential_id,
        secret_digest_id="secret-digest-ref",
        proof_sha256="d" * 64,
        proof_record_ref="audit/sha256/provisioning-bootstrap",
    )
    verified_subject = VerifiedSubject(
        deployment_id=operator.deployment_id,
        subject_kind="OS_UID",
        subject_value="705",
        credential_id="os-credential-705",
    )
    try:
        first = service.bootstrap_first_owner(
            authority,
            request_id=uuid4(),
            display_name="Provisioning Owner",
            project_name="Provisioning project",
        )
        owner = VerifiedPrincipal(
            actor_id=first.actor_id,
            deployment_id=operator.deployment_id,
            subject_kind=operator.subject_kind,
            subject_value=operator.subject_value,
            credential_id=operator.credential_id,
            verified_at=datetime.now(UTC),
        )
        new_actor_id = uuid4()
        provisioned = service.provision_actor(
            ProvisionActor(
                owner=owner,
                subject=verified_subject,
                actor_id=new_actor_id,
                display_name="  New Member  ",
                attestation=ProvisioningAttestation(
                    actor_id=new_actor_id,
                    deployment_id=operator.deployment_id,
                    subject_kind=verified_subject.subject_kind,
                    subject_value=verified_subject.subject_value,
                    subject_credential_id=verified_subject.credential_id,
                    operator=VerifiedPrincipal(
                        actor_id=uuid4(),
                        deployment_id=operator.deployment_id,
                        subject_kind="MTLS_URI",
                        subject_value="spiffe://example.org/operators/provisioner",
                        credential_id="operator-provisioner-cert",
                        verified_at=datetime.now(UTC),
                    ),
                    proof_sha256="e" * 64,
                    proof_record_ref="audit/sha256/new-member",
                    reason="identity proof inspected",
                ),
                request_id=uuid4(),
            )
        )
        assert provisioned == new_actor_id
        with engine.connect() as connection:
            assert (
                connection.execute(
                    text("SELECT display_name FROM actors WHERE id = :id"), {"id": new_actor_id}
                ).scalar_one()
                == "New Member"
            )
            assert (
                connection.execute(
                    text("SELECT count(*) FROM project_memberships WHERE actor_id = :id"),
                    {"id": new_actor_id},
                ).scalar_one()
                == 0
            )
            assert (
                connection.execute(
                    text(
                        "SELECT count(*) FROM actor_subject_binding_events "
                        "WHERE actor_id = :id AND event_kind = 'PROVISIONED'"
                    ),
                    {"id": new_actor_id},
                ).scalar_one()
                == 1
            )
    finally:
        engine.dispose()


def test_suspending_last_owner_membership_is_denied(phase2_database_url: str) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "0019_phase2_bootstrap_membership")
    engine = create_engine(phase2_database_url)
    service, _principal, _subject = _service(
        phase2_database_url, bootstrap_proof_verifier=_BootstrapProofVerifier()
    )
    uid = 706
    operator = VerifiedPrincipal(
        actor_id=uuid4(),
        deployment_id="deployment-suspend-owner",
        subject_kind="OS_UID",
        subject_value=str(uid),
        credential_id="os-credential-706",
        verified_at=datetime.now(UTC),
    )
    authority = BootstrapAuthority(
        deployment_id=operator.deployment_id,
        operator=operator,
        verified_os_uid=uid,
        subject_credential_id=operator.credential_id,
        secret_digest_id="secret-digest-ref",
        proof_sha256="a" * 64,
        proof_record_ref="audit/sha256/suspend-owner-bootstrap",
    )
    try:
        first = service.bootstrap_first_owner(
            authority,
            request_id=uuid4(),
            display_name="Membership Owner",
            project_name="Membership project",
        )
        principal = VerifiedPrincipal(
            actor_id=first.actor_id,
            deployment_id=operator.deployment_id,
            subject_kind=operator.subject_kind,
            subject_value=operator.subject_value,
            credential_id=operator.credential_id,
            verified_at=datetime.now(UTC),
        )
        with engine.connect() as connection:
            membership_id = connection.execute(
                text(
                    "SELECT id FROM project_memberships "
                    "WHERE project_id = :project AND actor_id = :actor"
                ),
                {"project": first.project_id, "actor": first.actor_id},
            ).scalar_one()
        try:
            service.suspend_project_membership(
                SuspendProjectMembership(
                    principal=principal,
                    project_id=first.project_id,
                    membership_id=membership_id,
                    reason="attempt to suspend final owner",
                    request_id=uuid4(),
                )
            )
        except ResearchBaseError as exc:
            assert exc.code is ErrorCode.OWNER_COVERAGE_GAP
        else:
            raise AssertionError("suspending the final OWNER must fail")
        with engine.connect() as connection:
            assert (
                connection.execute(
                    text("SELECT status FROM project_memberships WHERE id = :id"),
                    {"id": membership_id},
                ).scalar_one()
                == "ACTIVE"
            )
    finally:
        engine.dispose()


def test_revoking_last_owner_binding_is_denied_without_mutation(
    phase2_database_url: str,
) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "0019_phase2_bootstrap_membership")
    engine = create_engine(phase2_database_url)
    service, _principal, _subject = _service(
        phase2_database_url, bootstrap_proof_verifier=_BootstrapProofVerifier()
    )
    uid = 711
    operator = VerifiedPrincipal(
        actor_id=uuid4(),
        deployment_id="deployment-binding-revocation",
        subject_kind="OS_UID",
        subject_value=str(uid),
        credential_id="os-credential-711",
        verified_at=datetime.now(UTC),
    )
    authority = BootstrapAuthority(
        deployment_id=operator.deployment_id,
        operator=operator,
        verified_os_uid=uid,
        subject_credential_id=operator.credential_id,
        secret_digest_id="secret-digest-ref",
        proof_sha256="2" * 64,
        proof_record_ref="audit/sha256/revoke-binding-bootstrap",
    )
    try:
        first = service.bootstrap_first_owner(
            authority,
            request_id=uuid4(),
            display_name="Bound Owner",
            project_name="Protected binding project",
        )
        with engine.connect() as connection:
            binding_id = connection.execute(
                text("SELECT first_binding_id FROM bootstrap_records WHERE first_actor_id = :id"),
                {"id": first.actor_id},
            ).scalar_one()
        try:
            service.revoke_actor_subject_binding(
                RevokeActorSubjectBinding(
                    operator=operator,
                    binding_id=binding_id,
                    reason="attempt to revoke final OWNER credential",
                    request_id=uuid4(),
                )
            )
        except ResearchBaseError as exc:
            assert exc.code is ErrorCode.OWNER_COVERAGE_GAP
        else:
            raise AssertionError("revoking the last OWNER binding must fail")
        with engine.connect() as connection:
            assert (
                connection.execute(
                    text("SELECT status FROM actor_subject_bindings WHERE id = :id"),
                    {"id": binding_id},
                ).scalar_one()
                == "ACTIVE"
            )
    finally:
        engine.dispose()


def test_legacy_project_enrollment_starts_owner_coverage_without_backfill(
    phase2_database_url: str,
) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "0019_phase2_bootstrap_membership")
    engine = create_engine(phase2_database_url)
    service, _principal, _subject = _service(
        phase2_database_url, bootstrap_proof_verifier=_BootstrapProofVerifier()
    )
    uid = 707
    operator = VerifiedPrincipal(
        actor_id=uuid4(),
        deployment_id="deployment-legacy-project",
        subject_kind="OS_UID",
        subject_value=str(uid),
        credential_id="os-credential-707",
        verified_at=datetime.now(UTC),
    )
    authority = BootstrapAuthority(
        deployment_id=operator.deployment_id,
        operator=operator,
        verified_os_uid=uid,
        subject_credential_id=operator.credential_id,
        secret_digest_id="secret-digest-ref",
        proof_sha256="f" * 64,
        proof_record_ref="audit/sha256/legacy-project-bootstrap",
    )
    try:
        first = service.bootstrap_first_owner(
            authority,
            request_id=uuid4(),
            display_name="Legacy Project Creator",
            project_name="Initial project",
        )
        legacy_project_id = uuid4()
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO projects (id, name, created_by, created_at) "
                    "VALUES (:id, 'Pre-Phase-2 project', :actor, clock_timestamp())"
                ),
                {"id": legacy_project_id, "actor": first.actor_id},
            )
        principal = VerifiedPrincipal(
            actor_id=first.actor_id,
            deployment_id=operator.deployment_id,
            subject_kind=operator.subject_kind,
            subject_value=operator.subject_value,
            credential_id=operator.credential_id,
            verified_at=datetime.now(UTC),
        )
        attestation = ProvisioningAttestation(
            actor_id=first.actor_id,
            deployment_id=operator.deployment_id,
            subject_kind=operator.subject_kind,
            subject_value=operator.subject_value,
            subject_credential_id=operator.credential_id,
            operator=VerifiedPrincipal(
                actor_id=uuid4(),
                deployment_id=operator.deployment_id,
                subject_kind="MTLS_URI",
                subject_value="spiffe://example.org/operators/legacy-enrollment",
                credential_id="operator-legacy-project-cert",
                verified_at=datetime.now(UTC),
            ),
            proof_sha256="0" * 64,
            proof_record_ref="audit/sha256/legacy-project-enrollment",
            reason="reviewed historic project creator evidence",
        )
        membership_id = service.enroll_legacy_project_owner(
            EnrollLegacyProjectOwner(
                principal=principal,
                project_id=legacy_project_id,
                attestation=attestation,
                request_id=uuid4(),
            )
        )
        with engine.connect() as connection:
            assert (
                connection.execute(
                    text("SELECT status FROM project_memberships WHERE id = :id"),
                    {"id": membership_id},
                ).scalar_one()
                == "ACTIVE"
            )
            assert (
                connection.execute(
                    text(
                        "SELECT count(*) FROM project_role_assignments "
                        "WHERE project_id = :project AND role = 'OWNER' AND effective_until IS NULL"
                    ),
                    {"project": legacy_project_id},
                ).scalar_one()
                == 1
            )
    finally:
        engine.dispose()


def test_invalid_legacy_project_state_rejects_enrollment_before_writes(
    phase2_database_url: str,
) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "0019_phase2_bootstrap_membership")
    engine = create_engine(phase2_database_url)
    service, _principal, _subject = _service(
        phase2_database_url, bootstrap_proof_verifier=_BootstrapProofVerifier()
    )
    operator = VerifiedPrincipal(
        actor_id=uuid4(),
        deployment_id="deployment-invalid-project",
        subject_kind="OS_UID",
        subject_value="741",
        credential_id="os-credential-741",
        verified_at=datetime.now(UTC),
    )
    authority = BootstrapAuthority(
        deployment_id=operator.deployment_id,
        operator=operator,
        verified_os_uid=741,
        subject_credential_id=operator.credential_id,
        secret_digest_id="secret-digest-ref",
        proof_sha256="b" * 64,
        proof_record_ref="audit/sha256/invalid-project-bootstrap",
    )
    try:
        first = service.bootstrap_first_owner(
            authority,
            request_id=uuid4(),
            display_name="Legacy creator",
            project_name="Initial project",
        )
        legacy_project_id = uuid4()
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO projects (id, name, created_by, created_at) "
                    "VALUES (:id, 'Invalid legacy project', :actor, clock_timestamp())"
                ),
                {"id": legacy_project_id, "actor": first.actor_id},
            )
            connection.execute(text("ALTER TABLE actors DROP CONSTRAINT ck_actors_actor_type"))
            connection.execute(
                text("UPDATE actors SET actor_type = 'UNKNOWN' WHERE id = :id"),
                {"id": first.actor_id},
            )
        principal = VerifiedPrincipal(
            actor_id=first.actor_id,
            deployment_id=operator.deployment_id,
            subject_kind=operator.subject_kind,
            subject_value=operator.subject_value,
            credential_id=operator.credential_id,
            verified_at=datetime.now(UTC),
        )
        attestation = ProvisioningAttestation(
            actor_id=first.actor_id,
            deployment_id=operator.deployment_id,
            subject_kind=operator.subject_kind,
            subject_value=operator.subject_value,
            subject_credential_id=operator.credential_id,
            operator=VerifiedPrincipal(
                actor_id=uuid4(),
                deployment_id=operator.deployment_id,
                subject_kind="MTLS_URI",
                subject_value="spiffe://example.org/operators/invalid-project",
                credential_id="operator-invalid-project-cert",
                verified_at=datetime.now(UTC),
            ),
            proof_sha256="c" * 64,
            proof_record_ref="audit/sha256/invalid-project-enrollment",
            reason="reviewed legacy project evidence",
        )
        errors = []
        for _ in range(2):
            try:
                service.enroll_legacy_project_owner(
                    EnrollLegacyProjectOwner(
                        principal=principal,
                        project_id=legacy_project_id,
                        attestation=attestation,
                        request_id=uuid4(),
                    )
                )
            except ResearchBaseError as exc:
                assert exc.code is ErrorCode.LEGACY_STATE_INVALID
                errors.append(exc.to_dict())
            else:
                raise AssertionError("invalid legacy project state must fail closed")
        assert errors[0] == errors[1]
        with engine.connect() as connection:
            assert (
                connection.execute(
                    text("SELECT count(*) FROM project_memberships WHERE project_id=:id"),
                    {"id": legacy_project_id},
                ).scalar_one()
                == 0
            )
            assert (
                connection.execute(
                    text("SELECT count(*) FROM project_role_assignments WHERE project_id=:id"),
                    {"id": legacy_project_id},
                ).scalar_one()
                == 0
            )
            assert (
                connection.execute(
                    text(
                        "SELECT count(*) FROM project_membership_events e "
                        "JOIN project_memberships m ON m.id=e.membership_id WHERE m.project_id=:id"
                    ),
                    {"id": legacy_project_id},
                ).scalar_one()
                == 0
            )
    finally:
        engine.dispose()


def test_membership_reactivation_creates_new_rows_and_restores_prior_roles(
    phase2_database_url: str,
) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "0019_phase2_bootstrap_membership")
    engine = create_engine(phase2_database_url)
    service, _principal, _subject = _service(
        phase2_database_url, bootstrap_proof_verifier=_BootstrapProofVerifier()
    )
    uid = 708
    operator = VerifiedPrincipal(
        actor_id=uuid4(),
        deployment_id="deployment-reactivation",
        subject_kind="OS_UID",
        subject_value=str(uid),
        credential_id="os-credential-708",
        verified_at=datetime.now(UTC),
    )
    authority = BootstrapAuthority(
        deployment_id=operator.deployment_id,
        operator=operator,
        verified_os_uid=uid,
        subject_credential_id=operator.credential_id,
        secret_digest_id="secret-digest-ref",
        proof_sha256="9" * 64,
        proof_record_ref="audit/sha256/reactivation-bootstrap",
    )
    try:
        first = service.bootstrap_first_owner(
            authority,
            request_id=uuid4(),
            display_name="Primary Owner",
            project_name="Reactivation project",
        )
        owner = VerifiedPrincipal(
            actor_id=first.actor_id,
            deployment_id=operator.deployment_id,
            subject_kind=operator.subject_kind,
            subject_value=operator.subject_value,
            credential_id=operator.credential_id,
            verified_at=datetime.now(UTC),
        )
        subject = VerifiedSubject(
            deployment_id=operator.deployment_id,
            subject_kind="OS_UID",
            subject_value="709",
            credential_id="os-credential-709",
        )
        actor_id = uuid4()
        service.provision_actor(
            ProvisionActor(
                owner=owner,
                subject=subject,
                actor_id=actor_id,
                display_name="Second Owner",
                attestation=ProvisioningAttestation(
                    actor_id=actor_id,
                    deployment_id=operator.deployment_id,
                    subject_kind=subject.subject_kind,
                    subject_value=subject.subject_value,
                    subject_credential_id=subject.credential_id,
                    operator=VerifiedPrincipal(
                        actor_id=uuid4(),
                        deployment_id=operator.deployment_id,
                        subject_kind="MTLS_URI",
                        subject_value="spiffe://example.org/operators/reactivate",
                        credential_id="operator-reactivate-cert",
                        verified_at=datetime.now(UTC),
                    ),
                    proof_sha256="8" * 64,
                    proof_record_ref="audit/sha256/second-owner",
                    reason="second owner identity confirmed",
                ),
                request_id=uuid4(),
            )
        )
        service.assign_project_role(
            AssignProjectRole(
                principal=owner,
                project_id=first.project_id,
                actor_id=actor_id,
                role="OWNER",
                reason="additional owner",
                request_id=uuid4(),
            )
        )
        with engine.connect() as connection:
            old_membership_id = connection.execute(
                text(
                    "SELECT id FROM project_memberships "
                    "WHERE project_id = :project AND actor_id = :actor"
                ),
                {"project": first.project_id, "actor": actor_id},
            ).scalar_one()
        service.suspend_project_membership(
            SuspendProjectMembership(
                principal=owner,
                project_id=first.project_id,
                membership_id=old_membership_id,
                reason="planned account suspension",
                request_id=uuid4(),
            )
        )
        new_membership_id = service.reactivate_project_membership(
            ReactivateProjectMembership(
                principal=owner,
                project_id=first.project_id,
                actor_id=actor_id,
                reason="account reactivated after review",
                request_id=uuid4(),
            )
        )
        assert new_membership_id != old_membership_id
        with engine.connect() as connection:
            assert (
                connection.execute(
                    text("SELECT status FROM project_memberships WHERE id = :id"),
                    {"id": old_membership_id},
                ).scalar_one()
                == "SUSPENDED"
            )
            assert (
                connection.execute(
                    text(
                        "SELECT count(*) FROM project_role_assignments "
                        "WHERE membership_id = :id AND role = 'OWNER'"
                    ),
                    {"id": new_membership_id},
                ).scalar_one()
                == 1
            )
    finally:
        engine.dispose()
