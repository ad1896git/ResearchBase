"""CLI surface for PR2-04 literature search execution."""

# Typer command declarations use Option descriptors as parameter defaults.
# ruff: noqa: B008

from __future__ import annotations

import json
from uuid import UUID

import typer

from researchbase.application.literature_search_execution import (
    CancelLiteratureSearchExecution,
    CreateLiteratureSearchExecution,
    ExecuteLiteratureSearchExecution,
    RecoverLiteratureSearchExecution,
    SearchQueryInput,
)
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.errors import ErrorCode, ResearchBaseError

from ..context import CliRuntime
from ..errors import cli_exit_code
from ..output import emit_error, emit_success
from ..transport import add_command, command_group


def _runtime(ctx: typer.Context) -> CliRuntime:
    runtime = ctx.find_root().obj
    if not isinstance(runtime, CliRuntime):
        raise RuntimeError("CLI runtime is not initialized")
    return runtime


def _principal(runtime: CliRuntime) -> VerifiedPrincipal:
    principal = getattr(runtime.services, "verified_principal", None)
    if not isinstance(principal, VerifiedPrincipal):
        raise ResearchBaseError(
            ErrorCode.AUTHENTICATION_REQUIRED, "a trusted verified principal is unavailable"
        )
    return principal


def _service(runtime: CliRuntime):
    service = getattr(runtime.services, "literature_search_executions", None)
    if service is None:
        raise ResearchBaseError(ErrorCode.ADAPTER_UNAVAILABLE, "search adapter unavailable")
    return service


def _uuid(value: str, option: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, f"{option} must be a UUID") from exc


def _request_id(runtime: CliRuntime) -> UUID:
    if not runtime.request_id_supplied:
        raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, "--request-id is required")
    return runtime.request_id


def _run(runtime: CliRuntime, json_mode: bool, operation) -> None:
    try:
        emit_success(operation(), json_mode)
    except ResearchBaseError as exc:
        emit_error(exc, runtime.request_id, json_mode)
        raise typer.Exit(code=cli_exit_code(exc)) from None


def _queries(raw: str) -> tuple[SearchQueryInput, ...]:
    try:
        value = json.loads(raw)
        if not isinstance(value, list):
            raise TypeError
        if any(
            not isinstance(item, dict)
            or "query_text" not in item
            or not set(item).issubset({"query_text", "perspective", "query_type"})
            for item in value
        ):
            raise TypeError
        return tuple(
            SearchQueryInput(
                query_text=item["query_text"],
                perspective=item.get("perspective"),
                query_type=item.get("query_type", "TEXT"),
            )
            for item in value
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, "invalid queries JSON") from exc


def create(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    plan_version_id: str = typer.Option(..., "--plan-version-id"),
    provider_id: str = typer.Option(..., "--provider-id"),
    provider_version: str = typer.Option(..., "--provider-version"),
    queries_json: str = typer.Option(..., "--queries-json"),
    max_results: int = typer.Option(20, "--max-results", min=1, max=100),
    max_provider_attempts: int = typer.Option(3, "--max-provider-attempts", min=1, max=3),
    timeout_seconds: int = typer.Option(30, "--timeout-seconds", min=1, max=30),
    execution_budget_seconds: int = typer.Option(300, "--execution-budget-seconds", min=1, max=600),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    runtime = _runtime(ctx)
    principal = _principal(runtime)
    _run(
        runtime,
        json_mode,
        lambda: _service(runtime).create(
            CreateLiteratureSearchExecution(
                project_id=_uuid(project_id, "--project-id"),
                plan_version_id=_uuid(plan_version_id, "--plan-version-id"),
                actor_id=principal.actor_id,
                deployment_id=principal.deployment_id,
                request_id=_request_id(runtime),
                provider_id=provider_id,
                provider_version=provider_version,
                queries=_queries(queries_json),
                max_results=max_results,
                max_provider_attempts=max_provider_attempts,
                timeout_seconds=timeout_seconds,
                execution_budget_seconds=execution_budget_seconds,
                principal=principal,
            )
        ),
    )


def _write(ctx, project_id, execution_id, json_mode, command_type, method_name) -> None:
    runtime = _runtime(ctx)
    principal = _principal(runtime)
    _run(
        runtime,
        json_mode,
        lambda: getattr(_service(runtime), method_name)(
            command_type(
                execution_id=_uuid(execution_id, "--execution-id"),
                actor_id=principal.actor_id,
                deployment_id=principal.deployment_id,
                request_id=_request_id(runtime),
                project_id=_uuid(project_id, "--project-id"),
                principal=principal,
            )
        ),
    )


def execute(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    execution_id: str = typer.Option(..., "--execution-id"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    _write(ctx, project_id, execution_id, json_mode, ExecuteLiteratureSearchExecution, "execute")


def cancel(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    execution_id: str = typer.Option(..., "--execution-id"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    _write(ctx, project_id, execution_id, json_mode, CancelLiteratureSearchExecution, "cancel")


def recover(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    execution_id: str = typer.Option(..., "--execution-id"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    _write(ctx, project_id, execution_id, json_mode, RecoverLiteratureSearchExecution, "recover")


def show(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    execution_id: str = typer.Option(..., "--execution-id"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    runtime = _runtime(ctx)
    _run(
        runtime,
        json_mode,
        lambda: _service(runtime).get(
            _principal(runtime),
            _uuid(project_id, "--project-id"),
            _uuid(execution_id, "--execution-id"),
        ),
    )


def list_executions(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    limit: int = typer.Option(50, "--limit", min=1, max=100),
    after: str | None = typer.Option(None, "--after"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    runtime = _runtime(ctx)
    _run(
        runtime,
        json_mode,
        lambda: _service(runtime).list(
            _principal(runtime),
            _uuid(project_id, "--project-id"),
            limit,
            _uuid(after, "--after") if after is not None else None,
        ),
    )


def provenance(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    execution_id: str = typer.Option(..., "--execution-id"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    runtime = _runtime(ctx)
    _run(
        runtime,
        json_mode,
        lambda: _service(runtime).get_provenance(
            _principal(runtime),
            _uuid(project_id, "--project-id"),
            _uuid(execution_id, "--execution-id"),
        ),
    )


def register(app: typer.Typer) -> None:
    group = command_group("Literature search execution and provenance.")
    add_command(group, "create", "Create a search execution.", create)
    add_command(group, "execute", "Execute admitted search work.", execute)
    add_command(group, "cancel", "Request cancellation.", cancel)
    add_command(group, "recover", "Recover safe database bookkeeping.", recover)
    add_command(group, "get", "Read an execution.", show)
    add_command(group, "list", "List executions.", list_executions)
    add_command(group, "provenance", "Read execution provenance.", provenance)
    app.add_typer(group, name="literature-search-execution")
