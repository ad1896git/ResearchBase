"""Current-project selection for the single-user local CLI.

The current project is one UUID stored in the local profile directory. Commands
accept an explicit --project-id that overrides it.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from researchbase.foundation.errors import ErrorCode, ResearchBaseError

from .context import CliRuntime

_FILE = "current_project"


def _path(runtime: CliRuntime) -> Path:
    credentials = getattr(runtime.services, "local_credentials", None)
    root = getattr(credentials, "root", None)
    if root is None:
        raise ResearchBaseError(ErrorCode.AUTHENTICATION_REQUIRED, "本地配置不可用")
    return Path(root) / _FILE


def set_current_project(runtime: CliRuntime, project: UUID) -> None:
    path = _path(runtime)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(project) + "\n", encoding="utf-8")


def current_project_id(runtime: CliRuntime) -> UUID | None:
    try:
        raw = _path(runtime).read_text(encoding="utf-8").strip()
    except (FileNotFoundError, ResearchBaseError):
        return None
    try:
        return UUID(raw)
    except ValueError:
        return None


def resolve_project(runtime: CliRuntime, explicit: str | None) -> UUID:
    """Explicit --project-id wins; otherwise use the current project."""

    if explicit is not None:
        try:
            return UUID(explicit)
        except ValueError as exc:
            raise ResearchBaseError(
                ErrorCode.VALIDATION_ERROR,
                "项目 ID 格式不对，应为完整 UUID",
                details={"option": "--project-id"},
            ) from exc
    current = current_project_id(runtime)
    if current is None:
        raise ResearchBaseError(
            ErrorCode.VALIDATION_ERROR,
            "还没有设置当前项目。请先运行：researchbase project use <项目ID>",
            details={"option": "project"},
        )
    return current


def current_project_id_from_root(root: object) -> UUID | None:
    """Read the stored current project from a local profile root (used before a runtime exists)."""
    try:
        raw = (Path(str(root)) / _FILE).read_text(encoding="utf-8").strip()
        return UUID(raw)
    except (OSError, ValueError):
        return None


def local_root(runtime: CliRuntime) -> Path:
    """The local profile directory; command output that belongs to the owner lives beneath it."""
    credentials = getattr(runtime.services, "local_credentials", None)
    root = getattr(credentials, "root", None)
    if root is None:
        raise ResearchBaseError(ErrorCode.AUTHENTICATION_REQUIRED, "本地配置不可用")
    return Path(root)
