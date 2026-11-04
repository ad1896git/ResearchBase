"""Literature folder scans: append observations, classify changes, never mutate history.

The filesystem is read by the adapter before this service runs; the service only
receives the facts. Authority is checked inside the transaction, before any write.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable
from typing import Any
from uuid import UUID, uuid4

from researchbase.adapters.literature_folder import FolderFile
from researchbase.application.ports import UnitOfWork
from researchbase.foundation.time import Clock

ProjectAuthorizer = Callable[[UnitOfWork, UUID, bool, UUID | None], None]


def classify(previous: dict[str, dict[str, Any]], files: Iterable[FolderFile]) -> dict[str, Any]:
    """Compare the last known PRESENT files with this scan's files."""

    present = {item.file_path: item for item in files}
    gone = sorted(path for path in previous if path not in present)
    new_paths = sorted(path for path in present if path not in previous)

    gone_by_hash: dict[str, list[str]] = defaultdict(list)
    for path in gone:
        gone_by_hash[previous[path]["content_sha256"]].append(path)
    moved: list[dict[str, str]] = []
    still_new: list[str] = []
    for path in new_paths:
        candidates = gone_by_hash.get(present[path].content_sha256)
        if candidates:
            moved.append({"from": candidates.pop(0), "to": path})
        else:
            still_new.append(path)
    moved_from = {item["from"] for item in moved}

    modified = sorted(
        path
        for path in present
        if path in previous and previous[path]["content_sha256"] != present[path].content_sha256
    )
    unchanged = len(present) - len(modified) - len(still_new) - len(moved)

    by_hash: dict[str, list[str]] = defaultdict(list)
    for item in present.values():
        by_hash[item.content_sha256].append(item.file_path)
    duplicates = sorted(sorted(paths) for paths in by_hash.values() if len(paths) > 1)

    return {
        "file_count": len(present),
        "new": still_new,
        "moved": moved,
        "modified": modified,
        "missing": [path for path in gone if path not in moved_from],
        "unchanged": unchanged,
        "duplicates": duplicates,
    }


class LiteratureFolderService:
    def __init__(
        self, uow_factory: Callable[[], UnitOfWork], clock: Clock, authorizer: ProjectAuthorizer
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._authorizer = authorizer

    def scan(
        self,
        *,
        project_id: UUID,
        folder: str,
        files: list[FolderFile],
        actor_id: UUID,
        request_id: UUID,
    ) -> dict[str, Any]:
        scan_id = uuid4()
        with self._uow_factory() as uow:
            uow.begin_serializable()
            self._authorizer(uow, project_id, True, actor_id)
            observed_at = self._clock.now()
            previous = {
                row["file_path"]: row
                for row in uow.literature_folder.latest(project_id, folder)
                if row["observation_status"] == "PRESENT"
            }
            rows: list[dict[str, Any]] = [
                {
                    "id": uuid4(),
                    "project_id": project_id,
                    "scan_id": scan_id,
                    "folder_path": folder,
                    "file_path": item.file_path,
                    "observation_status": "PRESENT",
                    "content_sha256": item.content_sha256,
                    "size_bytes": item.size_bytes,
                    "file_mtime": item.file_mtime,
                    "title": item.title,
                    "doi": item.doi,
                    "observed_by": actor_id,
                    "request_id": request_id,
                    "observed_at": observed_at,
                }
                for item in files
            ]
            present = {item.file_path for item in files}
            for path, last in previous.items():
                if path in present:
                    continue
                rows.append(
                    {
                        **{k: last[k] for k in ("content_sha256", "size_bytes", "file_mtime")},
                        "title": last["title"],
                        "doi": last["doi"],
                        "id": uuid4(),
                        "project_id": project_id,
                        "scan_id": scan_id,
                        "folder_path": folder,
                        "file_path": path,
                        "observation_status": "MISSING",
                        "observed_by": actor_id,
                        "request_id": request_id,
                        "observed_at": observed_at,
                    }
                )
            uow.literature_folder.append(rows)
            uow.commit()
        return {"scan_id": str(scan_id), "folder": folder, **classify(previous, files)}

    def status(self, *, project_id: UUID, folder: str, actor_id: UUID) -> dict[str, Any]:
        with self._uow_factory() as uow:
            self._authorizer(uow, project_id, False, actor_id)
            latest = uow.literature_folder.latest(project_id, folder)
        present = sorted(
            (row for row in latest if row["observation_status"] == "PRESENT"),
            key=lambda row: row["file_path"],
        )
        missing = sorted(
            row["file_path"] for row in latest if row["observation_status"] == "MISSING"
        )
        return {
            "folder": folder,
            "files": [
                {
                    "file_path": row["file_path"],
                    "content_sha256": row["content_sha256"],
                    "title": row["title"],
                    "doi": row["doi"],
                }
                for row in present
            ],
            "missing": missing,
        }
