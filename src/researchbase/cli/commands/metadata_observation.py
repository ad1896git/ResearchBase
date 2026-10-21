"""Local-first M2 CLI; all canonical writes use Application services."""

# ruff: noqa: B008
from __future__ import annotations

import typer

from researchbase.foundation.errors import ErrorCode, ResearchBaseError

from ..transport import add_command, command_group
from .literature_search_execution import _principal, _request_id, _run, _runtime, _uuid


def _service(runtime):
    service = getattr(runtime.services, "metadata_observations", None)
    if service is None:
        raise ResearchBaseError(ErrorCode.ADAPTER_UNAVAILABLE, "metadata service unavailable")
    return service


def observe(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    result_id: str = typer.Option(..., "--result-id"),
    timeout_seconds: int = typer.Option(15, "--timeout-seconds", min=1, max=30),
    json_mode: bool = typer.Option(False, "--json"),
):
    runtime = _runtime(ctx)
    _run(
        runtime,
        json_mode,
        lambda: _service(runtime).observe(
            _principal(runtime),
            _uuid(project_id, "--project-id"),
            _uuid(result_id, "--result-id"),
            _request_id(runtime),
            timeout_seconds,
        ),
    )


def resolve(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    observation_id: str = typer.Option(..., "--observation-id"),
    json_mode: bool = typer.Option(False, "--json"),
):
    runtime = _runtime(ctx)
    _run(
        runtime,
        json_mode,
        lambda: _service(runtime).resolve(
            _principal(runtime),
            _uuid(project_id, "--project-id"),
            _uuid(observation_id, "--observation-id"),
        ),
    )


def show(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    observation_id: str = typer.Option(..., "--observation-id"),
    json_mode: bool = typer.Option(False, "--json"),
):
    runtime = _runtime(ctx)
    _run(
        runtime,
        json_mode,
        lambda: _service(runtime).get(
            _principal(runtime),
            _uuid(project_id, "--project-id"),
            _uuid(observation_id, "--observation-id"),
        ),
    )


def list_for_result(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    result_id: str = typer.Option(..., "--result-id"),
    json_mode: bool = typer.Option(False, "--json"),
):
    runtime = _runtime(ctx)
    _run(
        runtime,
        json_mode,
        lambda: _service(runtime).list_for_result(
            _principal(runtime), _uuid(project_id, "--project-id"), _uuid(result_id, "--result-id")
        ),
    )


def register(app: typer.Typer):
    group = command_group("Bibliographic observations and result-to-source resolution.")
    add_command(group, "observe", "Verify DOI metadata with Crossref.", observe)
    add_command(group, "resolve", "Resolve a matching observation to a source/version.", resolve)
    add_command(group, "get", "Read exact observation and evidence.", show)
    add_command(
        group,
        "list",
        "Read observations and established resolutions for a result.",
        list_for_result,
    )
    app.add_typer(group, name="literature-metadata")
