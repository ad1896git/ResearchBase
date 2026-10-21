"""Deterministic verifier intake for disposable tests only; no deployed mTLS claim."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from tests.disposable_postgres import disposable_database
from tests.integration.phase2.test_pr2_01_source_identity import _authorized_service
from tests.integration.phase2.test_pr2_10_binding_contract import _artifact

from researchbase.agent_runtime.application.agent_contracts import (
    AgentCommand,
    AgentEnrollmentProof,
    ProvisionProjectAgent,
    RegisterAgentVersion,
)
from researchbase.agent_runtime.application.agent_versions import AgentVersionService
from researchbase.application.phase2_identity import (
    Phase2IdentityService,
    ProvisioningAttestation,
    VerifiedSubject,
)
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.artifact_store import ContentAddressedFilesystemArtifactStore
from researchbase.foundation.ids import new_uuid7
from researchbase.persistence.uow import SqlAlchemyUnitOfWork


class Credentials:
    def is_valid(self, principal=None, at=None, **kwargs):
        return True

    def is_allowlisted(self, principal):
        return True

    def verify(self, *args, **kwargs):
        return True

    def issue(self):
        return b"test-only-nonce"


class SubjectCredentials:
    def is_valid(self, subject, at):
        return True


class RetainedPins:
    """Test-only retained pin resolver; all byte reads happen before lock acquisition."""

    def __init__(self, root, configuration, store):
        self.configuration = configuration
        self.store = store
        self.paths = {}
        for ordinal, pin in enumerate(
            ("café-研究@1.0.0", "modèle-模型@1.0.0", "outils-策略@1.0.0")
        ):
            path = root / f"pin-{ordinal}"
            payload = pin.encode("utf-8")
            path.write_bytes(payload)
            self.paths[pin] = (path, payload)

    def verify(self, arguments):
        from researchbase.foundation.hashing import sha256_bytes

        content = b'{"test":"configuration"}'
        if (
            arguments.configuration_artifact_version_id != self.configuration
            or self.store.open("sha256:" + str(sha256_bytes(content))) != content
        ):
            return False
        for pin in (
            arguments.prompt_template_version,
            arguments.model_profile_id,
            arguments.tool_policy_version,
        ):
            if pin not in self.paths:
                return False
            path, payload = self.paths[pin]
            if path.read_bytes() != payload:
                return False
        return True


class EnrollmentVerifier:
    def __init__(self):
        self.accepted = {}

    def verify(self, command, at):
        return self.accepted.get(command.command_id) == command.material()


@pytest.fixture
def agents(tmp_path, monkeypatch):
    with disposable_database("researchbase_pr212_test_") as url:
        monkeypatch.setenv("DATABASE_URL", url)
        engine, _, _, owner, project = _authorized_service(
            url, migration_revision="0079_agent_identity_versions"
        )
        engine.dispose()
        engine = create_engine(
            url,
            connect_args={
                "options": "-c lock_timeout=10s -c statement_timeout=30s -c track_functions=all"
            },
        )
        sessions = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

        def factory():
            return SqlAlchemyUnitOfWork(sessions)

        credentials = Credentials()
        verifier = EnrollmentVerifier()
        identity = Phase2IdentityService(
            factory,
            nonce_issuer=credentials,
            operator_policy=credentials,
            credential_verifier=credentials,
            subject_credential_verifier=SubjectCredentials(),
            attestation_verifier=credentials,
            agent_enrollment_verifier=verifier,
            agent_mtls_resolver=credentials,
        )
        # Independent HUMAN operator, never an AGENT fixture mutation.
        operator_id = new_uuid7()
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO actors(id,actor_type,display_name,created_at) "
                    "VALUES (:id,'HUMAN','test operator',clock_timestamp())"
                ),
                {"id": operator_id},
            )
        operator = VerifiedPrincipal(
            operator_id,
            owner.deployment_id,
            "MTLS_URI",
            "spiffe://test/operator",
            "test-operator",
            datetime.now(UTC),
        )
        store = ContentAddressedFilesystemArtifactStore(tmp_path / "cas")
        config = _artifact(
            factory, store, owner, project, b'{"test":"configuration"}', "configuration"
        )
        service = AgentVersionService(
            factory,
            credentials,
            pins=RetainedPins(tmp_path, config, store),
            identity=identity,
            enrollment_verifier=verifier,
        )
        env = SimpleNamespace(
            engine=engine,
            url=url,
            factory=factory,
            owner=owner,
            project=project,
            operator=operator,
            identity=identity,
            service=service,
            verifier=verifier,
            config=config,
            store=store,
            credentials=credentials,
        )
        role = "pr302_" + new_uuid7().hex
        with engine.begin() as conn:
            conn.execute(text(f"CREATE ROLE {role} NOSUPERUSER NOCREATEDB NOCREATEROLE NOLOGIN"))
            conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {role}"))
            conn.execute(
                text(f"GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO {role}")
            )
        engine.dispose()

        @event.listens_for(engine, "connect")
        def normal_role(dbapi, record):
            dbapi.autocommit = True
            dbapi.execute(f"SET ROLE {role}")
            dbapi.autocommit = False

        try:
            yield env
        finally:
            engine.dispose()
            admin = create_engine(url)
            try:
                with admin.begin() as conn:
                    conn.execute(text(f"DROP OWNED BY {role}"))
                    conn.execute(text(f"DROP ROLE {role}"))
            finally:
                admin.dispose()


def enrollment(env, **changes) -> Any:
    actor = new_uuid7()
    cid = new_uuid7()
    subject = VerifiedSubject(
        env.owner.deployment_id,
        "MTLS_URI",
        f"spiffe://test/agents/{actor}",
        "test-agent-cert-" + str(actor),
    )
    attestation = ProvisioningAttestation(
        actor,
        subject.deployment_id,
        subject.subject_kind,
        subject.subject_value,
        subject.credential_id,
        env.operator,
        "a" * 64,
        "test-only:attestation",
        "Enroll test Agent",
    )
    proof = AgentEnrollmentProof(
        env.project,
        cid,
        actor,
        env.owner.actor_id,
        env.operator.actor_id,
        subject.deployment_id,
        subject.subject_kind,
        subject.subject_value,
        subject.credential_id,
        "b" * 64,
        "test-only:enrollment",
        datetime.now(UTC) - timedelta(seconds=1),
        datetime.now(UTC) + timedelta(minutes=5),
    )
    args = ProvisionProjectAgent(actor, "Café researcher", subject, attestation, proof)
    command = AgentCommand(env.project, env.owner, cid, "provision_project_agent", None, args)
    command = replace(command, **changes)
    env.verifier.accepted[command.command_id] = command.material()
    return command


def register(env, actor, **changes) -> Any:
    args = RegisterAgentVersion(
        new_uuid7(),
        actor,
        "research",
        "native",
        "café-研究@1.0.0",
        "modèle-模型@1.0.0",
        "outils-策略@1.0.0",
        "c" * 64,
        env.config,
    )
    args = replace(args, **changes)
    return AgentCommand(env.project, env.owner, new_uuid7(), "register_agent_version", None, args)
