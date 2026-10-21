"""Thin S1 transport; enrollment proofs are injected by a trusted adapter."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, StrictInt

from researchbase.agent_runtime.application.agent_contracts import (
    AgentCommandResult,
    AgentVersionDTO,
    GetAgentVersion,
    parse_agent_command,
)
from researchbase.api.routes import _json, _response_schema, _services, _verified_principal
from researchbase.foundation.errors import ErrorCode, ResearchBaseError

router = APIRouter()


class AgentMutationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    command_id: UUID
    expected_revision: StrictInt | None
    arguments: dict[str, Any]


def _mutate(name, project_id, body, request, version=None):
    caller = _verified_principal(request)
    data = body.model_dump()
    data.update(project_id=str(project_id), command_id=str(body.command_id))
    if version is not None:
        if "agent_version_id" in data["arguments"]:
            raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, "target belongs in route")
        data["arguments"]["agent_version_id"] = str(version)
    trusted = getattr(request.state, "agent_enrollment", None)
    command = parse_agent_command(name, data, caller, trusted)
    return _json(_services(request).agents.execute(command))


@router.post(
    "/projects/{project_id}/agents",
    operation_id="provision_project_agent",
    status_code=201,
    response_model=_response_schema(AgentCommandResult),
)
def provision_project_agent(project_id: UUID, body: AgentMutationIn, request: Request):
    return _mutate("provision_project_agent", project_id, body, request)


@router.post(
    "/projects/{project_id}/agent-versions",
    operation_id="register_agent_version",
    status_code=201,
    response_model=_response_schema(AgentCommandResult),
)
def register_agent_version(project_id: UUID, body: AgentMutationIn, request: Request):
    return _mutate("register_agent_version", project_id, body, request)


@router.post(
    "/projects/{project_id}/agent-versions/{agent_version_id}/availability",
    operation_id="change_agent_availability",
    response_model=_response_schema(AgentCommandResult),
)
def change_agent_availability(
    project_id: UUID, agent_version_id: UUID, body: AgentMutationIn, request: Request
):
    return _mutate("change_agent_availability", project_id, body, request, agent_version_id)


@router.get(
    "/projects/{project_id}/agent-versions/{agent_version_id}",
    operation_id="get_agent_version",
    response_model=_response_schema(AgentVersionDTO),
)
def get_agent_version(project_id: UUID, agent_version_id: UUID, request: Request):
    caller = _verified_principal(request)
    return _json(
        _services(request).agents.get_agent_version(
            GetAgentVersion(project_id, agent_version_id, caller)
        )
    )
