"""Authenticated planning CLI; shares the closed Application decoder with HTTP."""

# ruff: noqa: B008
from __future__ import annotations

import json
from typing import Any, cast

import typer

from researchbase.agent_runtime.application.contracts import parse_command
from researchbase.foundation.errors import ErrorCode, ResearchBaseError

from ..errors import cli_exit_code
from ..output import emit_error, emit_success
from ..transport import add_command, command_group
from .literature_search_execution import _principal, _runtime, _uuid


def _run(runtime, json_mode, operation):
    try:
        emit_success(operation(), json_mode)
    except ResearchBaseError as exc:
        emit_error(exc, runtime.request_id, json_mode)
        raise typer.Exit(code=cli_exit_code(exc)) from None
    except Exception as exc:
        emit_error(exc, runtime.request_id, json_mode)
        raise typer.Exit(code=1) from None


def _mutation(name):
    def mutate(
        ctx: typer.Context,
        request_json: str = typer.Option(..., "--request-json"),
        json_mode: bool = typer.Option(False, "--json"),
    ):
        runtime = _runtime(ctx)

        def operation():
            try:
                data = json.loads(request_json)
                if not isinstance(data, dict):
                    raise ValueError
            except (ValueError, TypeError):
                raise ResearchBaseError(
                    ErrorCode.VALIDATION_ERROR, "invalid request JSON"
                ) from None
            command = parse_command(name, data)
            return cast(Any, runtime.services).research_tasks.execute(_principal(runtime), command)

        _run(runtime, json_mode, operation)

    return mutate


def _query(name):
    def query(
        ctx: typer.Context,
        project_id: str = typer.Option(...),
        task_id: str = typer.Option(...),
        json_mode: bool = typer.Option(False, "--json"),
    ):
        runtime = _runtime(ctx)
        _run(
            runtime,
            json_mode,
            lambda: getattr(cast(Any, runtime.services).research_tasks, name)(
                _principal(runtime), _uuid(project_id, "project-id"), _uuid(task_id, "task-id")
            ),
        )

    return query


def register(app: typer.Typer):
    group = command_group("ResearchTask planning; execution remains disabled.")
    for label, name in (
        ("create", "create_research_task"),
        ("plan", "create_task_plan"),
        ("add-step", "add_task_step"),
        ("add-dependency", "add_task_step_dependency"),
        ("seal-plan", "seal_task_plan"),
        ("cancel", "cancel_research_task"),
        ("start", "start_research_task"),
        ("pause", "pause_research_task"),
        ("resume", "resume_research_task"),
        ("start-step", "start_task_step"),
        ("finish-step", "finish_task_step"),
        ("fail-step", "fail_task_step"),
    ):
        add_command(group, label, name, _mutation(name))
    for label, name in (
        ("show", "get_research_task"),
        ("graph", "get_task_graph"),
        ("progress", "get_task_progress"),
    ):
        add_command(group, label, name, _query(name))
    app.add_typer(group, name="research-tasks")
