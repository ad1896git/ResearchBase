"""Authenticated manual evidence workflow; review is an explicit command."""

# ruff: noqa: B008
from __future__ import annotations

import json
from pathlib import Path

import typer

from researchbase.adapters.source_document import MAX_BYTES
from researchbase.foundation.errors import ErrorCode, ResearchBaseError

from ..transport import add_command, command_group
from .literature_search_execution import _principal, _request_id, _run, _runtime, _uuid


def _service(runtime):
    service = getattr(runtime.services, "literature_evidence", None)
    if service is None:
        raise ResearchBaseError(ErrorCode.ADAPTER_UNAVAILABLE, "literature evidence unavailable")
    return service


def import_document(
    ctx: typer.Context,
    project_id: str = typer.Option(...),
    path: Path = typer.Option(...),
    media_type: str = typer.Option(...),
    rights_basis: str = typer.Option(...),
    json_mode: bool = typer.Option(False, "--json"),
):
    runtime = _runtime(ctx)

    def operation():
        try:
            with path.open("rb") as stream:
                content = stream.read(MAX_BYTES + 1)
        except OSError as exc:
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR, "source document cannot be read"
            ) from exc
        return _service(runtime).import_document(
            _principal(runtime),
            _uuid(project_id, "project"),
            content,
            media_type,
            rights_basis,
            _request_id(runtime),
        )

    _run(runtime, json_mode, operation)


def inspect(
    ctx: typer.Context,
    project_id: str = typer.Option(...),
    source_version_id: str = typer.Option(...),
    paragraph: int = typer.Option(1),
    json_mode: bool = typer.Option(False, "--json"),
):
    runtime = _runtime(ctx)
    _run(
        runtime,
        json_mode,
        lambda: _service(runtime).inspect(
            _principal(runtime),
            _uuid(project_id, "project"),
            _uuid(source_version_id, "source-version"),
            paragraph,
        ),
    )


def create(
    ctx: typer.Context,
    project_id: str = typer.Option(...),
    source_version_id: str = typer.Option(...),
    quotation: str = typer.Option(...),
    paragraph: int | None = typer.Option(None),
    start: int | None = typer.Option(None),
    end: int | None = typer.Option(None),
    artifact_version_id: str = typer.Option(...),
    json_mode: bool = typer.Option(False, "--json"),
):
    runtime = _runtime(ctx)
    _run(
        runtime,
        json_mode,
        lambda: _service(runtime).create(
            _principal(runtime),
            _uuid(project_id, "project"),
            _uuid(source_version_id, "source-version"),
            quotation,
            _request_id(runtime),
            paragraph=paragraph,
            start=start,
            end=end,
            artifact_version_id=_uuid(artifact_version_id, "artifact-version"),
        ),
    )


def show(
    ctx: typer.Context,
    project_id: str = typer.Option(...),
    evidence_id: str = typer.Option(...),
    json_mode: bool = typer.Option(False, "--json"),
):
    runtime = _runtime(ctx)
    _run(
        runtime,
        json_mode,
        lambda: _service(runtime).get(
            _principal(runtime), _uuid(project_id, "project"), _uuid(evidence_id, "evidence")
        ),
    )


def review(
    ctx: typer.Context,
    project_id: str = typer.Option(...),
    evidence_id: str = typer.Option(...),
    status: str = typer.Option(..., help="Explicit VERIFIED, DISPUTED or REJECTED assessment."),
    basis: str = typer.Option(
        ..., help="What you inspected in the exact source and why this status applies."
    ),
    json_mode: bool = typer.Option(False, "--json"),
):
    runtime = _runtime(ctx)
    _run(
        runtime,
        json_mode,
        lambda: _service(runtime).review(
            _principal(runtime),
            _uuid(project_id, "project"),
            _uuid(evidence_id, "evidence"),
            status,
            basis,
            _request_id(runtime),
        ),
    )


def support_create(
    ctx: typer.Context,
    project_id: str = typer.Option(...),
    target_type: str = typer.Option(...),
    target_version_id: str = typer.Option(...),
    inputs_json: str = typer.Option(...),
    json_mode: bool = typer.Option(False, "--json"),
):
    runtime = _runtime(ctx)

    def operation():
        try:
            inputs = json.loads(inputs_json)
        except ValueError as exc:
            raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, "invalid relation JSON") from exc
        return _service(runtime).snapshot(
            _principal(runtime),
            _uuid(project_id, "project"),
            target_type,
            _uuid(target_version_id, "target-version"),
            inputs,
            _request_id(runtime),
        )

    _run(runtime, json_mode, operation)


def support_show(
    ctx: typer.Context,
    project_id: str = typer.Option(...),
    snapshot_id: str = typer.Option(...),
    json_mode: bool = typer.Option(False, "--json"),
):
    runtime = _runtime(ctx)
    _run(
        runtime,
        json_mode,
        lambda: _service(runtime).get_snapshot(
            _principal(runtime), _uuid(project_id, "project"), _uuid(snapshot_id, "snapshot")
        ),
    )


def register(app):
    group = command_group("Inspect exact source passages and explicitly review manual evidence.")
    for name, function in (
        ("import-document", import_document),
        ("inspect", inspect),
        ("create", create),
        ("get", show),
        ("review", review),
        ("support-create", support_create),
        ("support-get", support_show),
    ):
        add_command(group, name, function.__doc__ or name, function)
    app.add_typer(group, name="literature-evidence")
