"""Bounded supplied-byte registry loading and pure, exclusion-first routing."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import NoReturn
from uuid import UUID

from researchbase.agent_runtime.application.agent_contracts import AgentVersionDTO
from researchbase.agent_runtime.application.gateway_contracts import (
    AgentExecutionContext,
    RequestInvocationArguments,
)
from researchbase.agent_runtime.domain.agent_version import digest_value
from researchbase.agent_runtime.domain.capability_invocation import (
    ClosedValue,
    material,
    pin,
    typed,
)
from researchbase.agent_runtime.domain.harness_manifest import HarnessManifest
from researchbase.agent_runtime.domain.research_task import invalid
from researchbase.agent_runtime.domain.task_safety import integer
from researchbase.agent_runtime.domain.tool_policy import (
    FAKE_KEY,
    PermissionKey,
    ToolPolicySpec,
)
from researchbase.foundation.canonical_json import canonical_json_bytes
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


@dataclass(frozen=True, slots=True)
class RegistryEntry(PermissionKey):
    skill_id: str
    skill_version: str
    strategy_id: str
    strategy_version: str
    executable: bool
    allowed_phases: tuple[int, ...]
    license_id: str
    intake_artifact_version_id: UUID
    intake_content_hash: str

    def __post_init__(self):
        PermissionKey.__post_init__(self)
        for name in ("skill_id", "skill_version", "strategy_id", "strategy_version", "license_id"):
            object.__setattr__(
                self, name, pin(getattr(self, name), 128 if name.endswith("_id") else 512)
            )
        for phase in self.allowed_phases:
            integer(phase, minimum=1)
        if not self.allowed_phases or len(set(self.allowed_phases)) != len(self.allowed_phases):
            invalid("unique nonempty phases required")
        object.__setattr__(self, "allowed_phases", tuple(sorted(self.allowed_phases)))
        digest_value(self.intake_content_hash)
        if self.executable and self.key() != FAKE_KEY.key():
            raise ResearchBaseError(ErrorCode.ADAPTER_UNAVAILABLE, "only exact fake tuple admitted")

    def entry_key(self):
        return (
            self.skill_id,
            self.skill_version,
            self.strategy_id,
            self.strategy_version,
            *self.key(),
        )


@dataclass(frozen=True, slots=True)
class RegistryManifest(ClosedValue):
    schema_version: int
    entries: tuple[RegistryEntry, ...]

    def __post_init__(self):
        ClosedValue.__post_init__(self)
        if self.schema_version != 1 or len(self.entries) > 256:
            invalid("bounded registry schema 1 required")
        keys = [v.entry_key() for v in self.entries]
        if len(keys) != len(set(keys)):
            invalid("duplicate registry entries")
        object.__setattr__(
            self, "entries", tuple(sorted(self.entries, key=lambda v: v.entry_key()))
        )


class SkillRegistryLoader:
    """No discovery or byte acquisition. Caller supplies retained bytes before locks."""

    def __init__(self, max_bytes: int = 1048576):
        self.max_bytes = integer(max_bytes, minimum=1, maximum=1048576)

    def load(self, supplied: bytes) -> RegistryManifest:
        if type(supplied) is not bytes or len(supplied) > self.max_bytes:
            invalid("registry byte admission limit exceeded")

        def pairs(items):
            result = {}
            for key, value in items:
                if key in result:
                    invalid("duplicate JSON object key")
                result[key] = value
            return result

        def constant(_):
            invalid("nonfinite JSON forbidden")

        try:
            raw = json.loads(
                supplied.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant
            )
            registry = typed(RegistryManifest, raw, decode=True)
            if canonical_json_bytes(material(registry)) != supplied:
                invalid("retained registry must be normalized canonical JSON")
            return registry
        except (ValueError, UnicodeError, RecursionError):
            invalid("invalid registry bytes")


@dataclass(frozen=True, slots=True)
class RoutingPolicy(ClosedValue):
    phase: int
    authority_allowed: bool
    project_disclosure_allowed: bool
    task_safety_allowed: bool
    task_total_calls: int
    task_parallel_invocations: int
    self_install: bool = False
    governing_file_edits: bool = False
    changing_pins: bool = False
    same_execution_weakening: bool = False

    def __post_init__(self):
        ClosedValue.__post_init__(self)
        integer(self.phase, minimum=1)
        integer(self.task_total_calls)
        integer(self.task_parallel_invocations)


@dataclass(frozen=True, slots=True)
class CapabilityPolicy:
    project_id: UUID
    policy_id: UUID
    policy_content_hash: str
    policy: ToolPolicySpec

    def __post_init__(self):
        from researchbase.agent_runtime.domain.research_task import exact_uuid

        exact_uuid(self.project_id)
        exact_uuid(self.policy_id)
        if type(self.policy) is not ToolPolicySpec:
            invalid("closed policy binding required")
        digest_value(self.policy_content_hash)
        if self.policy.digest(self.project_id) != self.policy_content_hash:
            invalid("saved policy digest disagrees")


@dataclass(frozen=True, slots=True)
class FrozenArtifactPin(ClosedValue):
    """Owning-domain verified snapshot, with owning hash distinct from byte digest."""

    id: UUID
    project_id: UUID
    content_hash: str
    historically_frozen: bool

    def __post_init__(self):
        ClosedValue.__post_init__(self)
        digest_value(self.content_hash)


class SkillRouter:
    def select(
        self,
        request: RequestInvocationArguments,
        context: AgentExecutionContext,
        version: AgentVersionDTO | None,
        binding: CapabilityPolicy | None,
        registry: RegistryManifest,
        registry_pin: FrozenArtifactPin,
        intake_pins: tuple[FrozenArtifactPin, ...],
        manifest: HarnessManifest,
        routing: RoutingPolicy,
        expected_consumer,
    ) -> RegistryEntry:
        """All arguments are supplied snapshots; this predicate does no reads or dispatch."""

        def deny(message) -> NoReturn:
            raise ResearchBaseError(ErrorCode.FORBIDDEN, message)

        # Absence must be checked before relying on S2's derived actor lock.
        if version is None:
            raise ResearchBaseError(ErrorCode.NOT_FOUND, "AgentVersion unavailable")
        if binding is None:
            deny("exact policy binding required")
        if (
            context.consumer_capability is not expected_consumer
            or not routing.authority_allowed
            or not routing.project_disclosure_allowed
            or not routing.task_safety_allowed
            or routing.phase != 3
            or routing.self_install
            or routing.governing_file_edits
            or routing.changing_pins
            or routing.same_execution_weakening
        ):
            deny("routing exclusion")
        if (
            context.project_id != version.project_id
            or context.agent_version_id != version.id
            or request.agent_version_id != version.id
            or context.step_id != request.step_id
            or version.current_availability.status != "ACTIVE"
            or binding.project_id != context.project_id
            or binding.policy_id != request.policy_id
            or binding.policy_content_hash != request.policy_content_hash
            or binding.policy.version != version.tool_policy_version
            or binding.policy.capability_set_hash != version.capability_set_hash
            or registry_pin.id != binding.policy.registry_artifact_version_id
            or registry_pin.project_id != context.project_id
            or registry_pin.content_hash != binding.policy.registry_content_hash
            or not registry_pin.historically_frozen
        ):
            deny("version, registry or policy pins disagree")
        if (
            context.harness_artifact_version_id != version.configuration_artifact_version_id
            or request.harness_artifact_version_id != version.configuration_artifact_version_id
            or context.harness_content_hash != version.configuration_content_hash
            or request.harness_content_hash != version.configuration_content_hash
            or manifest.model_profile_id != version.model_profile_id
            or manifest.prompt_template_version != version.prompt_template_version
            or manifest.strategy_id != request.strategy_id
            or manifest.strategy_revision != request.strategy_version
        ):
            deny("retained harness pins disagree")
        if not any(
            v.id == request.skill_id and v.revision == request.skill_version
            for v in manifest.skills
        ) or not any(
            v.id == request.adapter_id and v.revision == request.adapter_version
            for v in manifest.adapters
        ):
            deny("harness skill or adapter pins disagree")
        key = request.permission_key()
        if key.key() != FAKE_KEY.key():
            raise ResearchBaseError(ErrorCode.ADAPTER_VERSION_MISMATCH, "exact fake pin required")
        if not binding.policy.allows(key) or not binding.policy.within_caps(
            task_total_calls=routing.task_total_calls,
            task_parallel_invocations=routing.task_parallel_invocations,
        ):
            deny("policy denies or task-wide cap reached")
        matches = [
            v
            for v in registry.entries
            if v.entry_key()
            == (
                request.skill_id,
                request.skill_version,
                request.strategy_id,
                request.strategy_version,
                *key.key(),
            )
        ]
        if len(matches) != 1:
            deny("exact unique registry entry required")
        entry = matches[0]
        if not entry.executable or routing.phase not in entry.allowed_phases:
            deny("entry is reference-only or excluded in current phase")
        pins = [p for p in intake_pins if p.id == entry.intake_artifact_version_id]
        if len(pins) != 1 or (
            pins[0].project_id != context.project_id
            or not pins[0].historically_frozen
            or pins[0].content_hash != entry.intake_content_hash
        ):
            deny("same-project frozen intake required")
        return entry


def finite_fake_echo(parameters):
    """One finite pure in-process call; accepts only the closed fake arguments."""
    from researchbase.agent_runtime.domain.capability_invocation import FakeParameters

    if type(parameters) is not FakeParameters:
        invalid("closed fake parameters required")
    summary = {
        "SUCCEEDED": parameters.message,
        "FAILED": "Fake failure.",
        "UNKNOWN_OUTCOME": "Fake outcome unknown.",
        "CANCELLED": "Fake cancelled.",
    }[parameters.outcome]
    error = {
        "FAILED": "ADAPTER_UNAVAILABLE",
        "UNKNOWN_OUTCOME": "INVALID_STATE_TRANSITION",
    }.get(parameters.outcome)
    return summary, error
