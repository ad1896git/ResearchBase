"""Exact policy matching and canonical hash material; no authority is inferred."""

from dataclasses import dataclass
from uuid import UUID

from researchbase.agent_runtime.domain.agent_version import digest_value
from researchbase.agent_runtime.domain.capability_invocation import (
    SCHEMA_HASH,
    ClosedValue,
    material,
    pin,
)
from researchbase.agent_runtime.domain.research_task import invalid
from researchbase.agent_runtime.domain.task_safety import integer
from researchbase.foundation.hashing import sha256_canonical_json

KEY_FIELDS = (
    "capability_id",
    "capability_version",
    "operation",
    "adapter_id",
    "adapter_version",
    "parameter_schema_hash",
)


@dataclass(frozen=True, slots=True)
class PermissionKey(ClosedValue):
    capability_id: str
    capability_version: str
    operation: str
    adapter_id: str
    adapter_version: str
    parameter_schema_hash: str

    def __post_init__(self):
        ClosedValue.__post_init__(self)
        for name in KEY_FIELDS[:-1]:
            object.__setattr__(
                self,
                name,
                pin(
                    getattr(self, name),
                    128 if name in ("capability_id", "operation", "adapter_id") else 512,
                ),
            )
        digest_value(self.parameter_schema_hash)

    def key(self):
        return tuple(getattr(self, name) for name in KEY_FIELDS)


FAKE_KEY = PermissionKey(
    "fake_capability", "1.0.0", "echo", "fake_in_process", "1.0.0", SCHEMA_HASH
)


@dataclass(frozen=True, slots=True)
class PermissionSpec(PermissionKey):
    effect: str

    def __post_init__(self):
        PermissionKey.__post_init__(self)
        if self.effect not in ("ALLOW", "DENY"):
            invalid("closed permission effect required")


def capability_set_material(permissions):
    keys = sorted({p.key() for p in permissions})
    return {
        "type": "CapabilitySet",
        "material_version": 1,
        "entries": [dict(zip(KEY_FIELDS, key, strict=True)) for key in keys],
    }


def capability_set_hash(permissions):
    return str(sha256_canonical_json(capability_set_material(permissions)))


@dataclass(frozen=True, slots=True)
class ToolPolicySpec(ClosedValue):
    version: str
    permissions: tuple[PermissionSpec, ...]
    registry_artifact_version_id: UUID
    registry_content_hash: str
    capability_set_hash: str
    max_tool_calls: int = 50
    max_parallel_invocations: int = 1
    filesystem_scope: str = "DENY"
    network_scope: str = "DENY"
    compute_scope: str = "DENY"
    external_effect_scope: str = "DENY"

    def __post_init__(self):
        ClosedValue.__post_init__(self)
        object.__setattr__(self, "version", pin(self.version))
        keys = [(*p.key(), p.effect) for p in self.permissions]
        if len(keys) > 256 or len(keys) != len(set(keys)):
            invalid("duplicate permissions or admission limit exceeded")
        object.__setattr__(
            self, "permissions", tuple(sorted(self.permissions, key=lambda p: (*p.key(), p.effect)))
        )
        integer(self.max_tool_calls, minimum=1, maximum=2147483647)
        integer(self.max_parallel_invocations, minimum=1, maximum=self.max_tool_calls)
        for name in ("filesystem_scope", "network_scope", "compute_scope", "external_effect_scope"):
            if getattr(self, name) != "DENY":
                invalid("CONTRACT_FAKE scope must DENY")
        digest_value(self.registry_content_hash)
        digest_value(self.capability_set_hash)
        if self.capability_set_hash != capability_set_hash(self.permissions):
            invalid("capability-set assertion disagrees")

    def material(self, project_id):
        from researchbase.agent_runtime.domain.research_task import exact_uuid

        exact_uuid(project_id)
        return {
            "type": "AgentToolPolicy",
            "material_version": 1,
            "content": {"project_id": str(project_id), **material(self)},
        }

    def digest(self, project_id):
        return str(sha256_canonical_json(self.material(project_id)))

    def allows(self, key: PermissionKey):
        effects = {p.effect for p in self.permissions if p.key() == key.key()}
        return "ALLOW" in effects and "DENY" not in effects

    def within_caps(self, *, task_total_calls: int, task_parallel_invocations: int):
        """Inputs must span the entire task, including previous policy/version bindings."""
        integer(task_total_calls)
        integer(task_parallel_invocations)
        return (
            task_total_calls < self.max_tool_calls
            and task_parallel_invocations < self.max_parallel_invocations
        )
