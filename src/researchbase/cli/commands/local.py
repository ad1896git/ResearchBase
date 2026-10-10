"""Authenticated local workbench commands; all canonical work uses Application services."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

import typer

from researchbase.application.commands import (
    CreateResearchQuestionCommand,
    CreateWorkspaceCommand,
    WriteProjectionTarget,
)
from researchbase.domain.organization import ProjectId
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.execution_context import ExecutionContext
from researchbase.local_identity import LocalIdentityAdapter

from ..common import application_write, invoke
from ..context import CliRuntime
from ..transport import add_command, command_group


def _runtime(ctx: typer.Context) -> CliRuntime:
    return ctx.find_root().obj


def _local(runtime: CliRuntime):
    service = getattr(runtime.services, "local_identity", None)
    if service is None:
        raise ResearchBaseError(ErrorCode.AUTHENTICATION_REQUIRED, "local profile is unavailable")
    return service


def _context(runtime: CliRuntime) -> ExecutionContext:
    principal = _local(runtime).authenticate()
    if runtime.actor_id is not None and runtime.actor_id != principal.actor_id:
        raise ResearchBaseError(ErrorCode.FORBIDDEN, "actor override is forbidden")
    return ExecutionContext(
        actor_id=principal.actor_id, request_id=runtime.request_id, client_type="cli"
    )


def initialize(ctx: typer.Context, json_mode: bool = typer.Option(False, "--json")) -> None:
    runtime = _runtime(ctx)

    def operation():
        _local(runtime)
        adapter = getattr(runtime.services, "local_credentials", None)
        if adapter is None:
            raise ResearchBaseError(ErrorCode.AUTHENTICATION_REQUIRED, "local profile unavailable")
        LocalIdentityAdapter.initialize(adapter.root)
        return {"installation": str(adapter.root), "profile": "LOCAL_FIRST"}

    invoke(runtime, json_mode, operation)


def bootstrap(
    ctx: typer.Context,
    display_name: str = typer.Option(..., "--display-name"),
    project_name: str = typer.Option(..., "--project-name"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    runtime = _runtime(ctx)
    invoke(
        runtime,
        json_mode,
        lambda: _local(runtime).bootstrap(runtime.request_id, display_name, project_name),
    )


def whoami(ctx: typer.Context, json_mode: bool = typer.Option(False, "--json")) -> None:
    runtime = _runtime(ctx)
    invoke(runtime, json_mode, lambda: _local(runtime).authenticate())


def project_show(
    ctx: typer.Context,
    project_id: Annotated[UUID, typer.Option("--project-id")],
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    runtime = _runtime(ctx)

    def operation():
        _context(runtime)
        return runtime.services.application.get_project(project_id)

    invoke(runtime, json_mode, operation)


def workspace_create(
    ctx: typer.Context,
    project_id: Annotated[UUID, typer.Option("--project-id")],
    name: str = typer.Option(..., "--name"),
    locator: str = typer.Option(..., "--locator"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    runtime = _runtime(ctx)
    invoke(
        runtime,
        json_mode,
        lambda: application_write(
            runtime.services.application,
            WriteProjectionTarget.WORKSPACE,
            lambda: runtime.services.application.create_workspace(
                CreateWorkspaceCommand(ProjectId(project_id), name, locator, _context(runtime))
            ),
        ),
    )


def question_create(
    ctx: typer.Context,
    project_id: Annotated[UUID, typer.Option("--project-id")],
    question_text: str = typer.Option(..., "--question-text"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    runtime = _runtime(ctx)
    invoke(
        runtime,
        json_mode,
        lambda: application_write(
            runtime.services.application,
            WriteProjectionTarget.RESEARCH_QUESTION,
            lambda: runtime.services.application.create_research_question(
                CreateResearchQuestionCommand(
                    ProjectId(project_id), question_text, None, None, _context(runtime)
                )
            ),
        ),
    )


def question_show(
    ctx: typer.Context,
    question_id: Annotated[UUID, typer.Option("--question-id")],
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    runtime = _runtime(ctx)

    def operation():
        _context(runtime)
        return runtime.services.application.get_research_question(question_id)

    invoke(runtime, json_mode, operation)


def register(app: typer.Typer) -> None:
    local = command_group("Trusted single-user local workbench.")
    for name, fn in (
        ("init", initialize),
        ("bootstrap", bootstrap),
        ("whoami", whoami),
        ("project-show", project_show),
        ("workspace-create", workspace_create),
        ("question-create", question_create),
        ("question-show", question_show),
    ):
        add_command(local, name, fn.__doc__ or name, fn)
    app.add_typer(local, name="local")
