from __future__ import annotations

import json
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime
from threading import Barrier
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from tests.integration.phase2.test_pr2_00_challenges import _service as _identity_service
from typer.testing import CliRunner

from researchbase.api.app import create_app as create_http_app
from researchbase.application.phase2_identity import BootstrapAuthority
from researchbase.application.source_identity import (
    AddSourceIdentifier,
    RegisterLiteratureSource,
    RejectSourceIdentifier,
    SourceIdentityService,
    VerifySourceIdentifier,
)
from researchbase.cli.app import create_app as create_cli_app
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.domain.source_identity import IdentifierType, SourceKind
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.source_identity_repository import SqlAlchemySourceIdentityRepository
from researchbase.persistence.uow import SqlAlchemyUnitOfWork


class _BootstrapProofVerifier:
    def verify(self, authority: BootstrapAuthority) -> bool:
        return True

    def invalidate(self, authority: BootstrapAuthority) -> None:
        return None


def _authorized_service(database_url: str, credential_verifier=None):
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
    engine = create_engine(database_url)
    identity, _, _ = _identity_service(
        database_url, bootstrap_proof_verifier=_BootstrapProofVerifier()
    )
    deployment = "pr2-01-test-deployment"
    uid = 501
    operator = VerifiedPrincipal(
        actor_id=uuid4(),
        deployment_id=deployment,
        subject_kind="OS_UID",
        subject_value=str(uid),
        credential_id="os-credential-test",
        verified_at=datetime.now(UTC),
    )
    authority = BootstrapAuthority(
        deployment_id=deployment,
        operator=operator,
        verified_os_uid=uid,
        subject_credential_id=operator.credential_id,
        secret_digest_id="test-secret-digest",
        proof_sha256="a" * 64,
        proof_record_ref="audit/test-bootstrap",
    )
    bootstrap = identity.bootstrap_first_owner(
        authority,
        request_id=uuid4(),
        display_name="Test owner",
        project_name="Test project",
    )
    principal = VerifiedPrincipal(
        actor_id=bootstrap.actor_id,
        deployment_id=deployment,
        subject_kind="OS_UID",
        subject_value=str(uid),
        credential_id=operator.credential_id,
        verified_at=datetime.now(UTC),
    )
    factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

    class _AlwaysValidCredential:
        def is_valid(self, principal: VerifiedPrincipal, at: datetime) -> bool:
            return True

    literature = SourceIdentityService(
        lambda: SqlAlchemyUnitOfWork(factory),
        credential_verifier or _AlwaysValidCredential(),
    )
    return engine, identity, literature, principal, bootstrap.project_id


def _frozen_basis(engine, project_id: UUID, actor_id: UUID) -> UUID:
    artifact_id = uuid4()
    version_id = uuid4()
    now = datetime.now(UTC)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO artifacts(id,project_id,artifact_type,name,created_by,created_at) "
                "VALUES (:id,:project,'DOCUMENT','basis',:actor,:now)"
            ),
            {"id": artifact_id, "project": project_id, "actor": actor_id, "now": now},
        )
        connection.execute(
            text(
                "INSERT INTO artifact_versions("
                "id,artifact_id,version_number,status,content_hash,created_by,"
                "created_at,frozen_at) "
                "VALUES (:id,:artifact,1,'FROZEN',:hash,:actor,:now,:now)"
            ),
            {
                "id": version_id,
                "artifact": artifact_id,
                "hash": uuid4().hex * 2,
                "actor": actor_id,
                "now": now,
            },
        )
    return version_id


def test_register_verify_reject_rebind_and_replay_are_durable(
    phase2_database_url: str,
) -> None:
    engine, _, service, principal, project_id = _authorized_service(phase2_database_url)
    register_id = uuid4()
    registered = service.register_literature_source(
        RegisterLiteratureSource(
            principal,
            project_id,
            SourceKind.PAPER,
            "  A public study  ",
            register_id,
            IdentifierType.DOI,
            "doi:10.1234/Example%7Eone",
        )
    )
    assert (
        service.register_literature_source(
            RegisterLiteratureSource(
                principal,
                project_id,
                SourceKind.PAPER,
                "A public study",
                register_id,
                IdentifierType.DOI,
                "https://doi.org/10.1234/example~one",
            )
        )
        == registered
    )
    with pytest.raises(ResearchBaseError) as conflict:
        service.register_literature_source(
            RegisterLiteratureSource(
                principal,
                project_id,
                SourceKind.PAPER,
                "Changed title",
                register_id,
                IdentifierType.DOI,
                "10.1234/example~one",
            )
        )
    assert conflict.value.code is ErrorCode.IDEMPOTENCY_CONFLICT

    with pytest.raises(ResearchBaseError) as unverified_collision:
        service.register_literature_source(
            RegisterLiteratureSource(
                principal,
                project_id,
                SourceKind.PAPER,
                "A public study",
                uuid4(),
                IdentifierType.DOI,
                "10.1234/example~one",
            )
        )
    assert unverified_collision.value.code is ErrorCode.SOURCE_IDENTITY_CONFLICT

    identifier_id = UUID(str(registered["identifier_id"]))
    verify_basis = _frozen_basis(engine, project_id, principal.actor_id)
    verify = VerifySourceIdentifier(
        principal,
        project_id,
        identifier_id,
        verify_basis,
        "Confirmed against frozen basis",
        uuid4(),
    )
    verified = service.verify_source_identifier(verify)
    assert service.verify_source_identifier(verify) == verified
    with pytest.raises(ResearchBaseError) as verify_conflict:
        service.verify_source_identifier(replace(verify, reason="Changed reason"))
    assert verify_conflict.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    compatible_duplicate = service.register_literature_source(
        RegisterLiteratureSource(
            principal,
            project_id,
            SourceKind.PAPER,
            "A public study",
            uuid4(),
            IdentifierType.DOI,
            "10.1234/example~one",
        )
    )
    assert compatible_duplicate == registered
    with pytest.raises(ResearchBaseError) as incompatible_verified:
        service.register_literature_source(
            RegisterLiteratureSource(
                principal,
                project_id,
                SourceKind.PAPER,
                "Different title",
                uuid4(),
                IdentifierType.DOI,
                "10.1234/example~one",
            )
        )
    assert incompatible_verified.value.code is ErrorCode.SOURCE_IDENTITY_CONFLICT
    reject_command = RejectSourceIdentifier(
        principal,
        project_id,
        identifier_id,
        _frozen_basis(engine, project_id, principal.actor_id),
        "The identifier was associated with the wrong record",
        uuid4(),
    )
    rejected = service.reject_source_identifier(reject_command)
    assert service.reject_source_identifier(reject_command) == rejected
    with pytest.raises(ResearchBaseError) as reject_conflict:
        service.reject_source_identifier(replace(reject_command, reason="Changed reason"))
    assert reject_conflict.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    assert rejected["identifier_id"] == str(identifier_id)

    correction_basis = _frozen_basis(engine, project_id, principal.actor_id)
    add_command = AddSourceIdentifier(
        principal,
        project_id,
        UUID(str(registered["source_id"])),
        IdentifierType.DOI,
        "10.1234/example~one",
        True,
        uuid4(),
        correction_basis,
        identifier_id,
    )
    rebound = service.add_source_identifier(add_command)
    assert service.add_source_identifier(add_command) == rebound
    with pytest.raises(ResearchBaseError) as add_conflict:
        service.add_source_identifier(replace(add_command, is_primary=False))
    assert add_conflict.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    rebound_id = UUID(str(rebound["identifier_id"]))
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT verification_status,binding_basis_artifact_version_id,"
                "supersedes_rejected_identifier_id "
                "FROM source_identifiers WHERE id=:id"
            ),
            {"id": rebound_id},
        ).one()
        assert row.verification_status == "UNVERIFIED"
        assert row.binding_basis_artifact_version_id == correction_basis
        assert row.supersedes_rejected_identifier_id == identifier_id
        assert (
            connection.execute(
                text(
                    "SELECT count(*) FROM source_identifier_verification_events "
                    "WHERE source_identifier_id=:id"
                ),
                {"id": identifier_id},
            ).scalar_one()
            == 2
        )
    engine.dispose()


def test_register_without_identifier_replay_and_changed_input_conflict(
    phase2_database_url: str,
) -> None:
    engine, _, service, principal, project_id = _authorized_service(phase2_database_url)
    command = RegisterLiteratureSource(
        principal, project_id, SourceKind.WEB, "No identifier", uuid4()
    )
    created = service.register_literature_source(command)
    assert service.register_literature_source(command) == created
    with pytest.raises(ResearchBaseError) as conflict:
        service.register_literature_source(replace(command, title="Different title"))
    assert conflict.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    engine.dispose()


def test_concurrent_same_key_add_verify_and_reject_replay_one_result(
    phase2_database_url: str,
) -> None:
    engine, _, service, principal, project_id = _authorized_service(phase2_database_url)
    source = service.register_literature_source(
        RegisterLiteratureSource(principal, project_id, SourceKind.PAPER, "Concurrent", uuid4())
    )
    basis = _frozen_basis(engine, project_id, principal.actor_id)

    def concurrent(call: Callable[[], dict[str, object]]) -> list[dict[str, object]]:
        barrier = Barrier(2)

        def invoke():
            barrier.wait(timeout=10)
            return call()

        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(lambda _: invoke(), range(2)))

    add_command = AddSourceIdentifier(
        principal,
        project_id,
        UUID(str(source["source_id"])),
        IdentifierType.DOI,
        "10.7777/concurrent-replay",
        True,
        uuid4(),
    )
    added = concurrent(lambda: service.add_source_identifier(add_command))
    assert added[0] == added[1]
    identifier_id = UUID(str(added[0]["identifier_id"]))
    verify_command = VerifySourceIdentifier(
        principal, project_id, identifier_id, basis, "Verify once", uuid4()
    )
    verified = concurrent(lambda: service.verify_source_identifier(verify_command))
    assert verified[0] == verified[1]
    reject_command = RejectSourceIdentifier(
        principal, project_id, identifier_id, basis, "Reject once", uuid4()
    )
    rejected = concurrent(lambda: service.reject_source_identifier(reject_command))
    assert rejected[0] == rejected[1]
    engine.dispose()


def test_unlinked_source_is_not_disclosed_and_shared_source_cannot_be_rejected(
    phase2_database_url: str,
) -> None:
    engine, identity, service, principal, project_id = _authorized_service(phase2_database_url)
    basis = _frozen_basis(engine, project_id, principal.actor_id)
    created = service.register_literature_source(
        RegisterLiteratureSource(
            principal,
            project_id,
            SourceKind.WEB,
            "Public page",
            uuid4(),
            IdentifierType.URL,
            "https://example.org/public",
        )
    )
    identifier_id = UUID(str(created["identifier_id"]))
    service.verify_source_identifier(
        VerifySourceIdentifier(principal, project_id, identifier_id, basis, "Verified", uuid4())
    )
    foreign_project_id = identity.create_project_with_owner(
        principal, name="Second project", request_id=uuid4()
    )
    linked = service.register_literature_source(
        RegisterLiteratureSource(
            principal,
            foreign_project_id,
            SourceKind.WEB,
            "Public page",
            uuid4(),
            IdentifierType.URL,
            "https://example.org/public",
        )
    )
    assert linked["source_id"] == created["source_id"]
    with pytest.raises(ResearchBaseError) as shared:
        service.reject_source_identifier(
            RejectSourceIdentifier(
                principal,
                project_id,
                identifier_id,
                _frozen_basis(engine, project_id, principal.actor_id),
                "Reject shared identity",
                uuid4(),
            )
        )
    assert shared.value.code is ErrorCode.SHARED_SOURCE_REJECTION_REQUIRES_REVIEW
    unlinked_project_id = identity.create_project_with_owner(
        principal, name="Unlinked project", request_id=uuid4()
    )
    with pytest.raises(ResearchBaseError) as cross_project_read:
        service.get_literature_source(
            principal, unlinked_project_id, UUID(str(created["source_id"]))
        )
    assert cross_project_read.value.code is ErrorCode.SOURCE_NOT_FOUND
    missing = uuid4()
    with pytest.raises(ResearchBaseError) as undisclosed:
        service.get_literature_source(principal, project_id, missing)
    assert undisclosed.value.code is ErrorCode.SOURCE_NOT_FOUND
    engine.dispose()


def test_concurrent_same_key_registration_replays_one_committed_result(
    phase2_database_url: str,
) -> None:
    engine, _, service, principal, project_id = _authorized_service(phase2_database_url)
    barrier = Barrier(2)
    request_id = uuid4()
    command = RegisterLiteratureSource(
        principal, project_id, SourceKind.PAPER, "Concurrent study", request_id
    )

    def register() -> dict[str, object]:
        barrier.wait(timeout=10)
        return service.register_literature_source(command)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: register(), range(2)))
    assert results[0] == results[1]
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM literature_sources WHERE id=:id"),
                {"id": UUID(str(results[0]["source_id"]))},
            ).scalar_one()
            == 1
        )
        assert (
            connection.execute(
                text("SELECT count(*) FROM literature_command_receipts WHERE request_id=:id"),
                {"id": request_id},
            ).scalar_one()
            == 1
        )
    engine.dispose()


def test_receipt_failure_rolls_back_each_command_and_allows_same_key_retry(
    phase2_database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine, _, service, principal, project_id = _authorized_service(phase2_database_url)
    basis = _frozen_basis(engine, project_id, principal.actor_id)
    base_source = service.register_literature_source(
        RegisterLiteratureSource(principal, project_id, SourceKind.PAPER, "Base", uuid4())
    )
    verify_source = service.register_literature_source(
        RegisterLiteratureSource(
            principal,
            project_id,
            SourceKind.PAPER,
            "Verify me",
            uuid4(),
            IdentifierType.DOI,
            "10.7777/verify",
        )
    )
    reject_source = service.register_literature_source(
        RegisterLiteratureSource(
            principal,
            project_id,
            SourceKind.PAPER,
            "Reject me",
            uuid4(),
            IdentifierType.DOI,
            "10.7777/reject",
        )
    )
    register_without = RegisterLiteratureSource(
        principal, project_id, SourceKind.WEB, "No identifier", uuid4()
    )
    register_with = RegisterLiteratureSource(
        principal,
        project_id,
        SourceKind.WEB,
        "With identifier",
        uuid4(),
        IdentifierType.URL,
        "https://rollback.example/",
    )
    add = AddSourceIdentifier(
        principal,
        project_id,
        UUID(str(base_source["source_id"])),
        IdentifierType.DOI,
        "10.7777/add",
        False,
        uuid4(),
    )
    verify = VerifySourceIdentifier(
        principal,
        project_id,
        UUID(str(verify_source["identifier_id"])),
        basis,
        "Rollback verification",
        uuid4(),
    )
    reject = RejectSourceIdentifier(
        principal,
        project_id,
        UUID(str(reject_source["identifier_id"])),
        basis,
        "Rollback rejection",
        uuid4(),
    )
    operations = [
        lambda: service.register_literature_source(register_without),
        lambda: service.register_literature_source(register_with),
        lambda: service.add_source_identifier(add),
        lambda: service.verify_source_identifier(verify),
        lambda: service.reject_source_identifier(reject),
    ]
    original = SqlAlchemySourceIdentityRepository.insert_receipt
    for operation in operations:

        def fail_receipt(self, values):
            raise RuntimeError("injected receipt persistence failure")

        monkeypatch.setattr(SqlAlchemySourceIdentityRepository, "insert_receipt", fail_receipt)
        with pytest.raises(RuntimeError, match="injected receipt persistence failure"):
            operation()
        monkeypatch.setattr(SqlAlchemySourceIdentityRepository, "insert_receipt", original)
        result = operation()
        assert isinstance(result, dict)
    engine.dispose()


def test_distinct_key_identifier_collision_has_typed_conflict(phase2_database_url: str) -> None:
    engine, _, service, principal, project_id = _authorized_service(phase2_database_url)
    first = service.register_literature_source(
        RegisterLiteratureSource(
            principal,
            project_id,
            SourceKind.PAPER,
            "First",
            uuid4(),
            IdentifierType.DOI,
            "10.8888/same",
        )
    )
    other_source = service.register_literature_source(
        RegisterLiteratureSource(principal, project_id, SourceKind.PAPER, "Second", uuid4())
    )
    with pytest.raises(ResearchBaseError) as conflict:
        service.add_source_identifier(
            AddSourceIdentifier(
                principal,
                project_id,
                UUID(str(other_source["source_id"])),
                IdentifierType.DOI,
                "10.8888/same",
                False,
                uuid4(),
            )
        )
    assert conflict.value.code is ErrorCode.IDENTIFIER_ALREADY_BOUND
    assert first["identifier_id"] is not None
    engine.dispose()


def test_http_cli_share_authenticated_application_and_idempotent_result(
    phase2_database_url: str,
) -> None:
    engine, _, service, principal, project_id = _authorized_service(phase2_database_url)
    services = SimpleNamespace(
        application=object(),
        provenance=object(),
        governance=object(),
        governance_queries=object(),
        literature=service,
        verified_principal=principal,
    )
    http_app = create_http_app(cast(Any, services))

    @http_app.middleware("http")
    async def inject_verified_principal(request, call_next):
        request.state.verified_principal = principal
        return await call_next(request)

    request_id = uuid4()
    path = f"/v1/projects/{project_id}/literature/sources"
    response = TestClient(http_app).post(
        path,
        json={"kind": "PAPER", "title": "Transport parity"},
        headers={"Idempotency-Key": str(request_id)},
    )
    assert response.status_code == 201
    cli = CliRunner().invoke(
        create_cli_app(cast(Any, services)),
        [
            "--request-id",
            str(request_id),
            "literature",
            "source",
            "create",
            "--project-id",
            str(project_id),
            "--kind",
            "PAPER",
            "--title",
            "Transport parity",
            "--json",
        ],
    )
    assert cli.exit_code == 0, cli.stderr
    assert json.loads(cli.stdout) == response.json()
    without_http_key = TestClient(http_app).post(
        path,
        json={"kind": "PAPER", "title": "Missing HTTP key"},
    )
    assert without_http_key.status_code == 422
    without_cli_key = CliRunner().invoke(
        create_cli_app(cast(Any, services)),
        [
            "literature",
            "source",
            "create",
            "--project-id",
            str(project_id),
            "--kind",
            "PAPER",
            "--title",
            "Missing CLI key",
            "--json",
        ],
    )
    assert without_cli_key.exit_code == 2
    assert "VALIDATION_ERROR" in without_cli_key.stderr
    engine.dispose()


def test_credential_expiry_during_project_lock_wait_denies_registration(
    phase2_database_url: str,
) -> None:
    authorization_times: list[datetime] = []

    class _ExpiresAtDatabaseTime:
        deadline: datetime

        def is_valid(self, principal: VerifiedPrincipal, at: datetime) -> bool:
            authorization_times.append(at)
            return at < self.deadline

    verifier = _ExpiresAtDatabaseTime()
    engine, _, service, principal, project_id = _authorized_service(phase2_database_url, verifier)
    blocker = engine.connect()
    blocker.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:resource,0))"),
        {"resource": f"researchbase-project:{project_id}"},
    )
    blocker_pid = blocker.execute(text("SELECT pg_backend_pid()")).scalar_one()
    verifier.deadline = blocker.execute(
        text("SELECT clock_timestamp() + interval '750 milliseconds'")
    ).scalar_one()
    command = RegisterLiteratureSource(
        principal, project_id, SourceKind.PAPER, "Expired while waiting", uuid4()
    )
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(service.register_literature_source, command)
        wait_confirmed = False
        timeout_at = time.monotonic() + 10
        while time.monotonic() < timeout_at:
            wait_confirmed = bool(
                blocker.execute(
                    text(
                        "SELECT EXISTS (SELECT 1 FROM pg_locks "
                        "WHERE pid<>:blocker_pid AND locktype='advisory' AND NOT granted)"
                    ),
                    {"blocker_pid": blocker_pid},
                ).scalar_one()
            )
            database_now = blocker.execute(text("SELECT clock_timestamp()")).scalar_one()
            if wait_confirmed and database_now > verifier.deadline:
                break
        blocker.commit()
        with pytest.raises(ResearchBaseError) as denied:
            future.result(timeout=10)
    assert wait_confirmed
    assert authorization_times and authorization_times[-1] > verifier.deadline
    assert denied.value.code is ErrorCode.AUTHENTICATION_REQUIRED
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM literature_sources WHERE canonical_title=:title"),
                {"title": "Expired while waiting"},
            ).scalar_one()
            == 0
        )
    engine.dispose()


def test_concurrent_rejection_and_corrected_rebinding_preserve_one_live_identity(
    phase2_database_url: str,
) -> None:
    engine, _, service, principal, project_id = _authorized_service(phase2_database_url)
    initial = service.register_literature_source(
        RegisterLiteratureSource(
            principal,
            project_id,
            SourceKind.PAPER,
            "Concurrent correction",
            uuid4(),
            IdentifierType.DOI,
            "10.9999/concurrent",
        )
    )
    identifier_id = UUID(str(initial["identifier_id"]))
    basis = _frozen_basis(engine, project_id, principal.actor_id)
    reject = RejectSourceIdentifier(
        principal, project_id, identifier_id, basis, "Incorrect initial match", uuid4()
    )
    corrected_basis = _frozen_basis(engine, project_id, principal.actor_id)
    rebind = AddSourceIdentifier(
        principal,
        project_id,
        UUID(str(initial["source_id"])),
        IdentifierType.DOI,
        "10.9999/concurrent",
        True,
        uuid4(),
        corrected_basis,
        identifier_id,
    )
    barrier = Barrier(2)

    def run_reject() -> object:
        barrier.wait(timeout=10)
        try:
            return service.reject_source_identifier(reject)
        except ResearchBaseError as exc:
            return exc

    def run_rebind() -> object:
        barrier.wait(timeout=10)
        try:
            return service.add_source_identifier(rebind)
        except ResearchBaseError as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as pool:
        rejected, rebound = list(pool.map(lambda fn: fn(), (run_reject, run_rebind)))
    if isinstance(rebound, ResearchBaseError):
        assert rebound.code is ErrorCode.IDENTIFIER_ALREADY_BOUND
        rebound = service.add_source_identifier(rebind)
    assert not isinstance(rejected, ResearchBaseError), rejected
    assert isinstance(rebound, dict)
    with engine.connect() as connection:
        statuses = (
            connection.execute(
                text(
                    "SELECT verification_status FROM source_identifiers "
                    "WHERE identifier_type='DOI' AND normalized_value='10.9999/concurrent' "
                    "ORDER BY created_at,id"
                )
            )
            .scalars()
            .all()
        )
    assert statuses == ["REJECTED", "UNVERIFIED"]
    engine.dispose()
