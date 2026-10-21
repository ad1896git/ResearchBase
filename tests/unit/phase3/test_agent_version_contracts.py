from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

import pytest
from tests.unit.phase3.agent_vectors import VECTORS

from researchbase.agent_runtime.application.agent_contracts import (
    AgentCommand,
    ChangeAgentAvailability,
    RegisterAgentVersion,
    parse_agent_command,
)
from researchbase.agent_runtime.domain.agent_version import AgentRole, RuntimeType, transition
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.errors import ResearchBaseError
from researchbase.foundation.hashing import sha256_canonical_json


@pytest.mark.parametrize("material,expected", VECTORS)
def test_literal_vectors(material, expected):
    assert str(sha256_canonical_json(material)) == expected
    if material["operation"] != "provision_project_agent":
        caller = VerifiedPrincipal(
            UUID(material["caller_actor_id"]),
            "test",
            "MTLS_URI",
            "spiffe://test/owner",
            "test",
            datetime.now(UTC),
        )
        data = {
            k: material[k] for k in ("project_id", "command_id", "expected_revision", "arguments")
        }
        command = parse_agent_command(material["operation"], data, caller)
        assert command.material() == material
        assert command.request_hash() == expected


@pytest.mark.parametrize("role", AgentRole)
@pytest.mark.parametrize("runtime", RuntimeType)
def test_closed_role_runtime_and_nfc(role, runtime):
    material = VECTORS[1][0]
    args = {
        **material["arguments"],
        "agent_role": role,
        "runtime_type": runtime,
        "prompt_template_version": "cafe\u0301@1",
    }
    for name in ("agent_version_id", "actor_id", "configuration_artifact_version_id"):
        args[name] = UUID(args[name])
    command = RegisterAgentVersion(**args)
    assert command.prompt_template_version == "café@1"
    assert command.version_material(UUID(material["project_id"]), "a" * 64) == replace(
        command, agent_version_id=UUID(int=1)
    ).version_material(UUID(material["project_id"]), "a" * 64)


@pytest.mark.parametrize("status", ["ACTIVE", "DISABLED", "RETIRED"])
@pytest.mark.parametrize("prior", ["ACTIVE", "DISABLED", "RETIRED"])
def test_availability_matrix(prior, status):
    if prior == "RETIRED" or prior == status:
        with pytest.raises(ResearchBaseError):
            transition(prior, status)
    else:
        transition(prior, status)


@pytest.mark.parametrize(
    "field,value",
    [
        ("model_profile_id", "latest"),
        ("tool_policy_version", "https://test/repo/main"),
        ("prompt_template_version", ""),
        ("capability_set_hash", "A" * 64),
        ("actor_id", "bad"),
        ("agent_role", "OWNER"),
        ("runtime_type", "vendor"),
    ],
)
def test_invalid_arguments(field, value):
    args = {**VECTORS[1][0]["arguments"]}
    for name in ("agent_version_id", "actor_id", "configuration_artifact_version_id"):
        args[name] = UUID(args[name])
    args[field] = value
    with pytest.raises((ResearchBaseError, ValueError, TypeError)):
        RegisterAgentVersion(**args)


def test_recursive_closed_and_cas():
    material = VECTORS[1][0]
    caller = VerifiedPrincipal(
        UUID(material["caller_actor_id"]),
        "test",
        "MTLS_URI",
        "spiffe://test",
        "test",
        datetime.now(UTC),
    )
    data = {k: material[k] for k in ("project_id", "command_id", "expected_revision", "arguments")}
    with pytest.raises(ResearchBaseError):
        parse_agent_command("register_agent_version", {**data, "caller": caller}, caller)
    with pytest.raises(ResearchBaseError):
        parse_agent_command(
            "register_agent_version",
            {**data, "arguments": {**data["arguments"], "hidden": "secret"}},
            caller,
        )
    with pytest.raises(ResearchBaseError):
        AgentCommand(
            UUID(material["project_id"]),
            caller,
            UUID(material["command_id"]),
            "change_agent_availability",
            None,
            ChangeAgentAvailability(UUID(int=1), "ACTIVE", "reason"),  # type: ignore[arg-type],
        )
