"""Closed caller-neutral S1 command, proof and result values."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from datetime import datetime
from typing import Any, Protocol, cast
from uuid import UUID

from researchbase.agent_runtime.application.contracts import enum_value, json_value, positive
from researchbase.agent_runtime.domain.agent_version import (
    AgentRole,
    AgentStatus,
    RuntimeType,
    digest_value,
    pinned,
)
from researchbase.agent_runtime.domain.research_task import exact_uuid, invalid, text_value
from researchbase.application.phase2_identity import ProvisioningAttestation, VerifiedSubject
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.hashing import sha256_canonical_json
from researchbase.foundation.time import to_utc


@dataclass(frozen=True, slots=True)
class AgentEnrollmentProof:
    project_id: UUID
    command_id: UUID
    actor_id: UUID
    owner_actor_id: UUID
    operator_actor_id: UUID
    deployment_id: str
    subject_kind: str
    subject_value: str
    subject_credential_id: str
    proof_sha256: str
    proof_record_ref: str
    verified_at: datetime
    expires_at: datetime

    def __post_init__(self):
        for name in ("project_id", "command_id", "actor_id", "owner_actor_id", "operator_actor_id"):
            exact_uuid(getattr(self, name))
        if self.subject_kind != "MTLS_URI":
            invalid("Agent requires MTLS_URI")
        for name in ("deployment_id", "subject_value", "subject_credential_id", "proof_record_ref"):
            object.__setattr__(self, name, text_value(getattr(self, name)))
        digest_value(self.proof_sha256)
        for name in ("verified_at", "expires_at"):
            object.__setattr__(self, name, to_utc(getattr(self, name)))
        if self.expires_at <= self.verified_at:
            invalid("proof interval must be positive")


@dataclass(frozen=True, slots=True)
class ProvisionProjectAgent:
    actor_id: UUID
    display_name: str
    subject: VerifiedSubject
    attestation: ProvisioningAttestation
    enrollment_proof: AgentEnrollmentProof

    def __post_init__(self):
        exact_uuid(self.actor_id)
        object.__setattr__(self, "display_name", text_value(self.display_name, 200))
        if (
            type(self.subject) is not VerifiedSubject
            or type(self.attestation) is not ProvisioningAttestation
            or type(self.enrollment_proof) is not AgentEnrollmentProof
        ):
            invalid("trusted typed enrollment values required")
        if self.subject.subject_kind != "MTLS_URI":
            invalid("Agent requires MTLS_URI")
        object.__setattr__(
            self,
            "subject",
            VerifiedSubject(**{k: text_value(v) for k, v in asdict(self.subject).items()}),
        )
        a = self.attestation
        object.__setattr__(
            self,
            "attestation",
            ProvisioningAttestation(
                a.actor_id,
                text_value(a.deployment_id),
                a.subject_kind,
                text_value(a.subject_value),
                text_value(a.subject_credential_id),
                a.operator,
                a.proof_sha256,
                text_value(a.proof_record_ref),
                text_value(a.reason, 8192),
            ),
        )


@dataclass(frozen=True, slots=True)
class RegisterAgentVersion:
    agent_version_id: UUID
    actor_id: UUID
    agent_role: AgentRole | str
    runtime_type: RuntimeType | str
    prompt_template_version: str
    model_profile_id: str
    tool_policy_version: str
    capability_set_hash: str
    configuration_artifact_version_id: UUID

    def __post_init__(self):
        for name in ("agent_version_id", "actor_id", "configuration_artifact_version_id"):
            exact_uuid(getattr(self, name))
        object.__setattr__(self, "agent_role", enum_value(AgentRole, self.agent_role))
        object.__setattr__(self, "runtime_type", enum_value(RuntimeType, self.runtime_type))
        for name in ("prompt_template_version", "model_profile_id", "tool_policy_version"):
            object.__setattr__(self, name, pinned(getattr(self, name)))
        digest_value(self.capability_set_hash)

    def version_material(self, project, configuration_hash):
        args = cast(dict[str, Any], json_value(self))
        del args["agent_version_id"]
        return {
            "type": "AgentVersion",
            "material_version": 1,
            "project_id": str(project),
            **args,
            "configuration_content_hash": configuration_hash,
        }


@dataclass(frozen=True, slots=True)
class ChangeAgentAvailability:
    agent_version_id: UUID
    status: AgentStatus | str
    reason: str

    def __post_init__(self):
        exact_uuid(self.agent_version_id)
        object.__setattr__(self, "status", enum_value(AgentStatus, self.status))
        object.__setattr__(self, "reason", text_value(self.reason, 8192))


_OPERATIONS = {
    "provision_project_agent": ProvisionProjectAgent,
    "register_agent_version": RegisterAgentVersion,
    "change_agent_availability": ChangeAgentAvailability,
}


@dataclass(frozen=True, slots=True)
class AgentCommand:
    project_id: UUID
    caller: VerifiedPrincipal
    command_id: UUID
    operation: str
    expected_revision: int | None
    arguments: ProvisionProjectAgent | RegisterAgentVersion | ChangeAgentAvailability

    def __post_init__(self):
        exact_uuid(self.project_id)
        exact_uuid(self.command_id)
        if type(self.caller) is not VerifiedPrincipal:
            invalid("injected verified caller required")
        if (
            self.operation not in _OPERATIONS
            or type(self.arguments) is not _OPERATIONS[self.operation]
        ):
            invalid("closed operation arguments required")
        if self.operation == "change_agent_availability":
            positive(self.expected_revision)  # type: ignore[arg-type]
        elif self.expected_revision is not None:
            invalid("create expected_revision must be NULL")

    def material(self):
        args = cast(dict[str, Any], json_value(self.arguments))
        if isinstance(self.arguments, ProvisionProjectAgent):
            a = self.arguments.attestation
            args["attestation"].pop("operator")
            args["attestation"]["operator_actor_id"] = str(a.operator.actor_id)
            args["enrollment_proof"].pop("verified_at")
            args["enrollment_proof"].pop("expires_at")
        return {
            "type": "AgentCommandMaterial",
            "material_version": 1,
            "project_id": str(self.project_id),
            "caller_actor_id": str(self.caller.actor_id),
            "command_id": str(self.command_id),
            "operation": self.operation,
            "expected_revision": self.expected_revision,
            "arguments": args,
        }

    def request_hash(self):
        return str(sha256_canonical_json(self.material()))


@dataclass(frozen=True, slots=True)
class GetAgentVersion:
    project_id: UUID
    agent_version_id: UUID
    caller: VerifiedPrincipal

    def __post_init__(self):
        exact_uuid(self.project_id)
        exact_uuid(self.agent_version_id)
        if type(self.caller) is not VerifiedPrincipal:
            invalid("injected verified caller required")


@dataclass(frozen=True, slots=True)
class AgentAvailabilityDTO:
    status: str
    revision: int
    changed_by: UUID
    changed_at: datetime


@dataclass(frozen=True, slots=True)
class AgentVersionDTO:
    id: UUID
    project_id: UUID
    actor_id: UUID
    agent_role: str
    runtime_type: str
    prompt_template_version: str
    model_profile_id: str
    tool_policy_version: str
    capability_set_hash: str
    configuration_artifact_version_id: UUID
    configuration_content_hash: str
    content_hash: str
    hash_scheme: str
    created_by: UUID
    created_at: datetime
    current_availability: AgentAvailabilityDTO


@dataclass(frozen=True, slots=True)
class AgentCommandResult:
    receipt_id: UUID
    project_id: UUID
    caller_actor_id: UUID
    command_id: UUID
    operation: str
    result_actor_id: UUID | None
    result_binding_id: UUID | None
    result_membership_id: UUID | None
    result_role_assignment_id: UUID | None
    result_binding_event_id: UUID | None
    result_membership_event_id: UUID | None
    result_role_event_id: UUID | None
    result_agent_version_id: UUID | None
    result_availability_event_id: UUID | None
    resulting_revision: int
    recorded_at: datetime
    replayed: bool
    result_execution_id: UUID | None = None
    result_execution_event_id: UUID | None = None


class AgentEnrollmentVerifier(Protocol):
    """Preflight at None; post-lock checks use local verified state, never network I/O."""

    def verify(self, command: AgentCommand, at: datetime | None) -> bool: ...


class AgentPinResolver(Protocol):
    def verify(self, arguments: RegisterAgentVersion) -> bool:
        """Verify retained immutable pins and owning configuration bytes before locks."""
        ...


class DenyAgentVerifier:
    def verify(self, *args) -> bool:
        return False


def parse_agent_command(name: str, data: dict, caller: VerifiedPrincipal, trusted_enrollment=None):
    try:
        if set(data) != {"project_id", "command_id", "expected_revision", "arguments"}:
            invalid("unknown or missing envelope fields")
        args = dict(data["arguments"])
        kind = _OPERATIONS[name]
        expected = {f.name for f in fields(kind)}
        if kind is ProvisionProjectAgent:
            expected -= {"subject", "attestation", "enrollment_proof"}
            if set(args) != expected:
                invalid("enrollment proof must come from trusted context")
            if trusted_enrollment is None:
                from researchbase.foundation.errors import ErrorCode, ResearchBaseError

                raise ResearchBaseError(
                    ErrorCode.SUBJECT_BINDING_UNPROVEN, "trusted enrollment verifier unavailable"
                )
            args.update(trusted_enrollment)
        elif set(args) != expected:
            invalid("unknown or missing argument fields")
        for key in ("actor_id", "agent_version_id", "configuration_artifact_version_id"):
            if key in args:
                args[key] = UUID(args[key])
        return AgentCommand(
            UUID(data["project_id"]),
            caller,
            UUID(data["command_id"]),
            name,
            data["expected_revision"],
            kind(**args),
        )
    except (ValueError, TypeError, KeyError, AttributeError):
        invalid("invalid closed Agent command")


class AgentMTLSResolver(Protocol):
    def verify(self, subject: VerifiedSubject, at: datetime) -> bool: ...
