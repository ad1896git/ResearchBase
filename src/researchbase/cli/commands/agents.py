"""S1 CLI uses the same closed Application decoder as HTTP."""

# ruff: noqa: B008
import json
from typing import Any, cast

import typer

from researchbase.agent_runtime.application.agent_contracts import (
    GetAgentVersion,
    parse_agent_command,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError

from ..transport import add_command, command_group
from .literature_search_execution import _principal, _runtime, _uuid
from .research_tasks import _run


def _mutation(name):
    def mutate(
        ctx: typer.Context,
        request_json: str = typer.Option(..., "--request-json"),
        json_mode: bool = typer.Option(False, "--json"),
    ):
        runtime = _runtime(ctx)

        def operation():
            caller = _principal(runtime)
            try:
                data = json.loads(request_json)
                if not isinstance(data, dict):
                    raise ValueError
            except (TypeError, ValueError):
                raise ResearchBaseError(
                    ErrorCode.VALIDATION_ERROR, "invalid request JSON"
                ) from None
            trusted = getattr(runtime.services, "agent_enrollment", None)
            return cast(Any, runtime.services).agents.execute(
                parse_agent_command(name, data, caller, trusted)
            )

        _run(runtime, json_mode, operation)

    return mutate


def _get(
    ctx: typer.Context,
    project_id: str = typer.Option(...),
    agent_version_id: str = typer.Option(...),
    json_mode: bool = typer.Option(False, "--json"),
):
    runtime = _runtime(ctx)
    _run(
        runtime,
        json_mode,
        lambda: cast(Any, runtime.services).agents.get_agent_version(
            GetAgentVersion(
                _uuid(project_id, "project-id"),
                _uuid(agent_version_id, "agent-version-id"),
                _principal(runtime),
            )
        ),
    )


def register(app):
    group = command_group("Project Agent identities and immutable versions.")
    for label, name in (
        ("provision", "provision_project_agent"),
        ("register-version", "register_agent_version"),
        ("change-availability", "change_agent_availability"),
    ):
        add_command(group, label, name, _mutation(name))
    add_command(group, "get-version", "get_agent_version", _get)
    app.add_typer(group, name="agents")
