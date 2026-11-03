"""Append-only literature folder observations (see migration 0084)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

_INSERT = text(
    """
    INSERT INTO literature_folder_observations (
        id, project_id, scan_id, folder_path, file_path, observation_status,
        content_sha256, size_bytes, file_mtime, title, doi,
        observed_by, request_id, observed_at
    ) VALUES (
        :id, :project_id, :scan_id, :folder_path, :file_path, :observation_status,
        :content_sha256, :size_bytes, :file_mtime, :title, :doi,
        :observed_by, :request_id, :observed_at
    )
    """
)

# Latest observation per file path in one folder; the caller keeps PRESENT rows.
_LATEST = text(
    """
    SELECT DISTINCT ON (file_path)
        file_path, observation_status, content_sha256, size_bytes,
        file_mtime, title, doi, observed_at
    FROM literature_folder_observations
    WHERE project_id = :project_id AND folder_path = :folder_path
    ORDER BY file_path, observed_at DESC
    """
)


class SqlAlchemyLiteratureFolderRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def latest(self, project_id: UUID, folder_path: str) -> list[dict[str, Any]]:
        rows = self._session.execute(
            _LATEST, {"project_id": project_id, "folder_path": folder_path}
        )
        return [dict(row) for row in rows.mappings()]

    def append(self, rows: list[dict[str, Any]]) -> None:
        for row in rows:
            self._session.execute(_INSERT, row)
