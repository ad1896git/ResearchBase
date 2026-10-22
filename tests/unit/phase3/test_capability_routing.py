"""Pure registry/routing exclusions with supplied retained snapshots only."""

import json
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

import pytest
from tests.unit.phase3.test_agent_tool_policy import PROJECT, REGISTRY, permission, policy
from tests.unit.phase3.test_capability_gateway_contracts import ID, request

from researchbase.agent_runtime.application.agent_contracts import (
    AgentAvailabilityDTO,
    AgentVersionDTO,
)
from researchbase.agent_runtime.application.gateway_contracts import AgentExecutionContext
from researchbase.agent_runtime.application.routing import (
    CapabilityPolicy,
    FrozenArtifactPin,
    RegistryEntry,
    RegistryManifest,
    RoutingPolicy,
    SkillRegistryLoader,
    SkillRouter,
)
from researchbase.agent_runtime.domain.capability_invocation import material
from researchbase.agent_runtime.domain.harness_manifest import HarnessManifest, ManifestEntry
from researchbase.agent_runtime.domain.tool_policy import FAKE_KEY
from researchbase.agent_runtime.ports.task_safety_repository import FakeConsumerCapability
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.canonical_json import canonical_json_bytes
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


def entry():
    return RegistryEntry(
        **material(FAKE_KEY),
        skill_id="echo-skill",
        skill_version="1.0.0",
        strategy_id="echo-strategy",
        strategy_version="1.0.0",
        executable=True,
        allowed_phases=(3,),
        license_id="MIT",
        intake_artifact_version_id=ID,
        intake_content_hash="e" * 64,
    )


def route_inputs() -> dict[str, Any]:
    p = policy((permission(),))
    r = replace(request(), policy_content_hash=p.digest(PROJECT))
    now = datetime(2026, 10, 22, tzinfo=UTC)
    # This principal is a supplied trusted object. Routing receives the authority result,
    # and never derives authority from a role string or configuration description.
    principal = object.__new__(VerifiedPrincipal)
    consumer = FakeConsumerCapability()
    context = AgentExecutionContext(principal, PROJECT, ID, None, ID, ID, "b" * 64, consumer)
    version = AgentVersionDTO(
        ID,
        PROJECT,
        ID,
        "general",
        "native",
        "prompt-v1",
        "model-v1",
        p.version,
        p.capability_set_hash,
        ID,
        "b" * 64,
        "f" * 64,
        "sha256-cjson-v1",
        ID,
        now,
        AgentAvailabilityDTO("ACTIVE", 1, ID, now),
    )
    manifest = HarnessManifest(
        1,
        "rev1",
        "rev1",
        "model-v1",
        "prompt-v1",
        "f" * 64,
        "f" * 64,
        "echo-strategy",
        "1.0.0",
        (ManifestEntry("echo-skill", "1.0.0", "f" * 64, 1),),
        (),
        (ManifestEntry("fake_in_process", "1.0.0", "f" * 64, 1),),
        (),
        (),
        (),
    )
    return dict(
        request=r,
        context=context,
        version=version,
        binding=CapabilityPolicy(PROJECT, ID, p.digest(PROJECT), p),
        registry=RegistryManifest(1, (entry(),)),
        registry_pin=FrozenArtifactPin(REGISTRY, PROJECT, "a" * 64, True),
        intake_pins=(FrozenArtifactPin(ID, PROJECT, "e" * 64, True),),
        manifest=manifest,
        routing=RoutingPolicy(3, True, True, True, 0, 0),
        expected_consumer=consumer,
    )


def test_exact_route_and_supplied_byte_loader():
    args = route_inputs()
    assert SkillRouter().select(**args) == entry()
    raw = canonical_json_bytes(material(args["registry"]))
    assert SkillRegistryLoader(len(raw)).load(raw) == args["registry"]
    with pytest.raises(ResearchBaseError):
        SkillRegistryLoader(len(raw) - 1).load(raw)


@pytest.mark.parametrize(
    "changes",
    [
        {"phase": 2},
        {"authority_allowed": False},
        {"project_disclosure_allowed": False},
        {"task_safety_allowed": False},
        {"task_total_calls": 50},
        {"task_parallel_invocations": 1},
        {"self_install": True},
        {"governing_file_edits": True},
        {"changing_pins": True},
        {"same_execution_weakening": True},
    ],
)
def test_routing_exclusions(changes):
    args = route_inputs()
    args["routing"] = replace(args["routing"], **changes)
    with pytest.raises(ResearchBaseError):
        SkillRouter().select(**args)


@pytest.mark.parametrize(
    "change",
    [
        "reference-only",
        "entry-phase",
        "missing-entry",
        "no-version",
        "no-policy",
        "wrong-consumer",
        "foreign-registry",
        "unfrozen-intake",
        "wrong-harness",
        "availability",
        "policy-version",
        "capability-set",
        "manifest-skill",
        "manifest-adapter",
    ],
)
def test_pins_phase_and_reference_only(change):
    args = route_inputs()
    if change == "reference-only":
        args["registry"] = RegistryManifest(1, (replace(entry(), executable=False),))
    elif change == "entry-phase":
        args["registry"] = RegistryManifest(1, (replace(entry(), allowed_phases=(4,)),))
    elif change == "missing-entry":
        args["registry"] = RegistryManifest(1, ())
    elif change == "no-version":
        args["version"] = None
    elif change == "no-policy":
        args["binding"] = None
    elif change == "wrong-consumer":
        args["expected_consumer"] = FakeConsumerCapability()
    elif change == "foreign-registry":
        args["registry_pin"] = replace(args["registry_pin"], project_id=ID)
    elif change == "unfrozen-intake":
        args["intake_pins"] = (replace(args["intake_pins"][0], historically_frozen=False),)
    elif change == "wrong-harness":
        args["request"] = replace(args["request"], harness_content_hash="d" * 64)
    elif change == "availability":
        args["version"] = replace(
            args["version"],
            current_availability=replace(args["version"].current_availability, status="DISABLED"),
        )
    elif change == "policy-version":
        args["version"] = replace(args["version"], tool_policy_version="other-v1")
    elif change == "capability-set":
        args["version"] = replace(args["version"], capability_set_hash="d" * 64)
    elif change == "manifest-skill":
        args["manifest"] = replace(args["manifest"], skills=())
    elif change == "manifest-adapter":
        args["manifest"] = replace(args["manifest"], adapters=())
    with pytest.raises(ResearchBaseError) as exc:
        SkillRouter().select(**args)
    if change == "no-version":
        assert exc.value.code == ErrorCode.NOT_FOUND


@pytest.mark.parametrize(
    "raw",
    [
        {"schema_version": True, "entries": []},
        {"schema_version": 1, "entries": [], "extra": 1},
        {"schema_version": 1, "entries": [dict(material(entry()), extra="ignored?")]},
        {"schema_version": 1, "entries": [material(entry()), material(entry())]},
        {"schema_version": 1, "entries": [material(entry())] * 257},
        {"schema_version": 1, "entries": [dict(material(entry()), allowed_phases=[3, 3])]},
        {"schema_version": 1, "entries": [dict(material(entry()), allowed_phases=[True])]},
        {"schema_version": 1, "entries": [dict(material(entry()), executable=1)]},
    ],
)
def test_closed_registry_negative(raw):
    with pytest.raises(ResearchBaseError):
        SkillRegistryLoader().load(canonical_json_bytes(raw))


@pytest.mark.parametrize(
    "raw",
    [
        b'{"schema_version":1,"schema_version":1,"entries":[]}',
        b'{"schema_version":NaN,"entries":[]}',
        b"{}",
        b"\xff",
        b"[]",
        b'{ "entries":[],"schema_version":1}',
        b"[" * 2000,
    ],
)
def test_malformed_noncanonical_and_nonfinite_bytes(raw):
    with pytest.raises(ResearchBaseError):
        SkillRegistryLoader().load(raw)


def test_registry_byte_limit_and_non_executable_tuple():
    with pytest.raises(ResearchBaseError):
        SkillRegistryLoader().load(b" " * 1048577)
    with pytest.raises(ResearchBaseError):
        replace(entry(), capability_id="provider")
    reference = replace(entry(), executable=False, capability_id="provider")
    raw = canonical_json_bytes(material(RegistryManifest(1, (reference,))))
    assert SkillRegistryLoader().load(raw).entries == (reference,)


def test_loader_does_no_discovery_or_io(monkeypatch):
    raw = canonical_json_bytes(material(RegistryManifest(1, (entry(),))))

    def forbidden(*args, **kwargs):
        raise AssertionError("loader attempted I/O")

    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr("importlib.import_module", forbidden)
    result = SkillRegistryLoader().load(raw)
    assert json.loads(raw)["entries"][0]["skill_id"] == result.entries[0].skill_id
