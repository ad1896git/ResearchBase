"""CLI transport for PR2-01 LiteratureSource and SourceIdentifier commands."""

# Typer command declarations use Option descriptors as parameter defaults.
# ruff: noqa: B008

from __future__ import annotations

from uuid import UUID

import typer

from researchbase.application.source_identity import (
    AddSourceIdentifier,
    RegisterLiteratureSource,
    RejectSourceIdentifier,
    VerifySourceIdentifier,
)
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.domain.source_identity import IdentifierType, SourceKind
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
            ErrorCode.AUTHENTICATION_REQUIRED,
            "a trusted verified principal is unavailable to the CLI",
        )
    if runtime.actor_id is not None and runtime.actor_id != principal.actor_id:
        raise ResearchBaseError(
            ErrorCode.FORBIDDEN, "--actor-id does not match the authenticated principal"
        )
    return principal


def _literature(runtime: CliRuntime):
    service = getattr(runtime.services, "literature", None)
    if service is None:
        raise ResearchBaseError(ErrorCode.AUTHENTICATION_REQUIRED, "literature service unavailable")
    return service


def _request_id(runtime: CliRuntime) -> UUID:
    if not runtime.request_id_supplied:
        raise ResearchBaseError(
            ErrorCode.VALIDATION_ERROR, "--request-id is required for literature writes"
        )
    return runtime.request_id


def _uuid(value: str | None, option: str) -> UUID:
    try:
        if value is None:
            raise ValueError
        return UUID(value)
    except (TypeError, ValueError) as exc:
        raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, f"{option} must be a UUID") from exc


def _run(runtime: CliRuntime, json_mode: bool, operation):
    try:
        emit_success(operation(), json_mode)
    except ResearchBaseError as exc:
        emit_error(exc, runtime.request_id, json_mode)
        raise typer.Exit(code=cli_exit_code(exc)) from None


def source_create(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    kind: SourceKind = typer.Option(..., "--kind"),
    title: str = typer.Option(..., "--title"),
    initial_identifier_type: IdentifierType | None = typer.Option(
        None, "--initial-identifier-type"
    ),
    initial_identifier_value: str | None = typer.Option(None, "--initial-identifier-value"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    runtime = _runtime(ctx)
    _run(
        runtime,
        json_mode,
        lambda: _literature(runtime).register_literature_source(
            RegisterLiteratureSource(
                _principal(runtime),
                _uuid(project_id, "--project-id"),
                kind,
                title,
                _request_id(runtime),
                initial_identifier_type,
                initial_identifier_value,
            )
        ),
    )


def source_show(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    source_id: str = typer.Option(..., "--source-id"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    runtime = _runtime(ctx)
    _run(
        runtime,
        json_mode,
        lambda: _literature(runtime).get_literature_source(
            _principal(runtime), _uuid(project_id, "--project-id"), _uuid(source_id, "--source-id")
        ),
    )


def source_resolve(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    identifier_type: IdentifierType = typer.Option(..., "--identifier-type"),
    value: str = typer.Option(..., "--value"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    runtime = _runtime(ctx)
    _run(
        runtime,
        json_mode,
        lambda: _literature(runtime).find_source_by_identifier(
            _principal(runtime), _uuid(project_id, "--project-id"), identifier_type, value
        ),
    )


def identifier_add(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    source_id: str = typer.Option(..., "--source-id"),
    identifier_type: IdentifierType = typer.Option(..., "--identifier-type"),
    identifier_value: str = typer.Option(..., "--value"),
    is_primary: bool = typer.Option(False, "--primary"),
    binding_basis_artifact_version_id: str | None = typer.Option(
        None, "--binding-basis-artifact-version-id"
    ),
    supersedes_rejected_identifier_id: str | None = typer.Option(
        None, "--supersedes-rejected-identifier-id"
    ),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    runtime = _runtime(ctx)
    _run(
        runtime,
        json_mode,
        lambda: _literature(runtime).add_source_identifier(
            AddSourceIdentifier(
                _principal(runtime),
                _uuid(project_id, "--project-id"),
                _uuid(source_id, "--source-id"),
                identifier_type,
                identifier_value,
                is_primary,
                _request_id(runtime),
                UUID(binding_basis_artifact_version_id)
                if binding_basis_artifact_version_id
                else None,
                UUID(supersedes_rejected_identifier_id)
                if supersedes_rejected_identifier_id
                else None,
            )
        ),
    )


def _status_command(
    ctx: typer.Context,
    project_id: str,
    identifier_id: str,
    basis_id: str,
    reason: str,
    json_mode: bool,
    *,
    reject: bool,
) -> None:
    runtime = _runtime(ctx)
    command_type = RejectSourceIdentifier if reject else VerifySourceIdentifier
    _run(
        runtime,
        json_mode,
        lambda: getattr(
            _literature(runtime),
            "reject_source_identifier" if reject else "verify_source_identifier",
        )(
            command_type(
                _principal(runtime),
                _uuid(project_id, "--project-id"),
                _uuid(identifier_id, "--identifier-id"),
                _uuid(basis_id, "--basis-artifact-version-id"),
                reason,
                _request_id(runtime),
            )
        ),
    )


def identifier_verify(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    identifier_id: str = typer.Option(..., "--identifier-id"),
    basis_artifact_version_id: str = typer.Option(..., "--basis-artifact-version-id"),
    reason: str = typer.Option(..., "--reason"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    _status_command(
        ctx, project_id, identifier_id, basis_artifact_version_id, reason, json_mode, reject=False
    )


def identifier_reject(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    identifier_id: str = typer.Option(..., "--identifier-id"),
    basis_artifact_version_id: str = typer.Option(..., "--basis-artifact-version-id"),
    reason: str = typer.Option(..., "--reason"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    _status_command(
        ctx, project_id, identifier_id, basis_artifact_version_id, reason, json_mode, reject=True
    )


def identifier_list(
    ctx: typer.Context,
    project_id: str = typer.Option(..., "--project-id"),
    source_id: str = typer.Option(..., "--source-id"),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    runtime = _runtime(ctx)
    _run(
        runtime,
        json_mode,
        lambda: _literature(runtime).list_source_identifiers(
            _principal(runtime), _uuid(project_id, "--project-id"), _uuid(source_id, "--source-id")
        ),
    )


def register(app: typer.Typer) -> None:
    literature = command_group("Public literature source identity and identifiers.")
    source = command_group("Literature source commands.")
    identifier = command_group("Source identifier commands.")
    add_command(source, "create", "Register a public literature source.", source_create)
    add_command(source, "show", "Read a project-linked literature source.", source_show)
    add_command(source, "resolve", "Resolve a source by a typed identifier.", source_resolve)
    add_command(identifier, "add", "Add a source identifier.", identifier_add)
    add_command(identifier, "verify", "Verify an identifier using frozen basis.", identifier_verify)
    add_command(identifier, "reject", "Reject an identifier using frozen basis.", identifier_reject)
    add_command(identifier, "list", "List linked source identifier history.", identifier_list)
    literature.add_typer(source, name="source")
    literature.add_typer(identifier, name="identifier")
    app.add_typer(literature, name="literature")
