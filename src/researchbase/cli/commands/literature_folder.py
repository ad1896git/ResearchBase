"""Literature folder scans: `literature-folder scan` and `literature-folder status`."""

# ruff: noqa: B008
from __future__ import annotations

from pathlib import Path

import typer

from researchbase.adapters.literature_folder import FolderScanError, scan_folder
from researchbase.foundation.errors import ErrorCode, ResearchBaseError

from ..transport import add_command, command_group
from .literature_search_execution import _principal, _request_id, _run, _runtime, _uuid


def _service(runtime):
    service = getattr(runtime.services, "literature_folder", None)
    if service is None:
        raise ResearchBaseError(ErrorCode.ADAPTER_UNAVAILABLE, "literature folder unavailable")
    return service


def _folder(path: Path) -> Path:
    try:
        return path.expanduser().resolve(strict=True)
    except OSError as exc:
        raise ResearchBaseError(ErrorCode.NOT_FOUND, f"找不到文件夹：{path}") from exc


def scan(
    ctx: typer.Context,
    project_id: str = typer.Option(...),
    path: Path = typer.Option(...),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    runtime = _runtime(ctx)

    def operation():
        folder = _folder(path)
        try:
            files = scan_folder(folder)
        except FolderScanError as exc:
            raise ResearchBaseError(ErrorCode.VALIDATION_ERROR, str(exc)) from exc
        return _service(runtime).scan(
            project_id=_uuid(project_id, "--project-id"),
            folder=str(folder),
            files=files,
            actor_id=_principal(runtime).actor_id,
            request_id=_request_id(runtime),
        )

    _run(runtime, json_mode, operation)


def status(
    ctx: typer.Context,
    project_id: str = typer.Option(...),
    path: Path = typer.Option(...),
    json_mode: bool = typer.Option(False, "--json"),
) -> None:
    runtime = _runtime(ctx)

    def operation():
        folder = _folder(path)
        return _service(runtime).status(
            project_id=_uuid(project_id, "--project-id"),
            folder=str(folder),
            actor_id=_principal(runtime).actor_id,
        )

    _run(runtime, json_mode, operation)


def register(app: typer.Typer) -> None:
    group = command_group("扫描本地文献文件夹，记录变化（只读文件，不修改文件夹）。")
    add_command(group, "scan", "扫描文件夹并记录观察结果。", scan)
    add_command(group, "status", "显示文件夹最近一次的状态。", status)
    app.add_typer(group, name="literature-folder")
