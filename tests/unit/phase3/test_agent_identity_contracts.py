from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import pytest
from tests.unit.phase3.agent_vectors import VECTORS

from researchbase.agent_runtime.application.agent_contracts import (
    AgentCommand,
    AgentEnrollmentProof,
    DenyAgentVerifier,
    ProvisionProjectAgent,
)
from researchbase.application.phase2_identity import ProvisioningAttestation, VerifiedSubject
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.errors import ResearchBaseError


def enrollment_vector() -> Any:
    material = VECTORS[0][0]
    args = material["arguments"]
    now = datetime.now(UTC)
    caller = VerifiedPrincipal(
        UUID(material["caller_actor_id"]),
        "researchbase-test",
        "MTLS_URI",
        "spiffe://test/owner",
        "owner-cert",
        now,
    )
    att = dict(args["attestation"])
    op = VerifiedPrincipal(
        UUID(att.pop("operator_actor_id")),
        "researchbase-test",
        "MTLS_URI",
        "spiffe://test/operator",
        "operator-cert",
        now,
    )
    att["actor_id"] = UUID(att["actor_id"])
    att = ProvisioningAttestation(**att, operator=op)
    proof = dict(args["enrollment_proof"])
    for key in ("project_id", "command_id", "actor_id", "owner_actor_id", "operator_actor_id"):
        proof[key] = UUID(proof[key])
    proof = AgentEnrollmentProof(**proof, verified_at=now, expires_at=now + timedelta(minutes=5))
    return AgentCommand(
        UUID(material["project_id"]),
        caller,
        UUID(material["command_id"]),
        "provision_project_agent",
        None,
        ProvisionProjectAgent(
            UUID(args["actor_id"]),
            args["display_name"],
            VerifiedSubject(**args["subject"]),
            att,
            proof,
        ),
    )


def test_enrollment_vector_freshness_and_default_deny():
    command = enrollment_vector()
    assert command.material() == VECTORS[0][0]
    assert command.request_hash() == VECTORS[0][1]
    assert not DenyAgentVerifier().verify(command, None)
    proof = command.arguments.enrollment_proof
    refreshed = replace(proof, verified_at=proof.verified_at + timedelta(seconds=1))
    assert (
        replace(
            command, arguments=replace(command.arguments, enrollment_proof=refreshed)
        ).request_hash()
        == command.request_hash()
    )
    with pytest.raises(FrozenInstanceError):
        proof.proof_record_ref = "altered"
    with pytest.raises(ResearchBaseError):
        replace(proof, subject_kind="OS_UID")
