"""Read a local literature folder: file identity, PDF title and DOI (read-only).

Nothing here writes to the folder or the database. A file that cannot be read
as a PDF is still recorded by its bytes; only its title and DOI stay empty.
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

SUPPORTED_SUFFIXES = frozenset({".pdf", ".txt", ".md", ".xml"})
_DOI_PATTERN = re.compile(r"\b10\.\d{4,9}/[^\s\"<>]+")
_TEXT_LIMIT = 2_000_000  # characters searched for a DOI


class FolderScanError(Exception):
    """The folder itself cannot be scanned (missing or not a directory)."""


@dataclass(frozen=True)
class FolderFile:
    file_path: str  # relative to the folder, POSIX separators
    content_sha256: str
    size_bytes: int
    file_mtime: datetime
    title: str | None
    doi: str | None


def doi_in(text: str) -> str | None:
    match = _DOI_PATTERN.search(text)
    return match.group(0).rstrip(".,;)]") if match else None


def _pdf_title_and_text(path: Path) -> tuple[str | None, str]:
    from pypdf import PdfReader

    try:
        reader = PdfReader(str(path))
        if reader.is_encrypted:
            return None, ""
        title = str((reader.metadata or {}).get("/Title") or "").strip() or None
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:  # pypdf raises many malformed-file error types; the file is still recorded
        return None, ""
    return title, text


def _describe(root: Path, path: Path) -> FolderFile:
    data = path.read_bytes()
    stat = path.stat()
    title: str | None = None
    if path.suffix.lower() == ".pdf":
        title, text = _pdf_title_and_text(path)
    else:
        text = data[:_TEXT_LIMIT].decode("utf-8", errors="ignore")
    return FolderFile(
        file_path=path.relative_to(root).as_posix(),
        content_sha256=hashlib.sha256(data).hexdigest(),
        size_bytes=stat.st_size,
        file_mtime=datetime.fromtimestamp(stat.st_mtime, UTC),
        title=title,
        doi=doi_in(text[:_TEXT_LIMIT]) if text else None,
    )


def scan_folder(root: Path) -> list[FolderFile]:
    """Supported files under `root`, sorted; hidden entries and symlinks are skipped."""

    if not root.is_dir():
        raise FolderScanError(f"folder not found: {root}")
    files: list[FolderFile] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(name for name in dirnames if not name.startswith("."))
        for name in sorted(filenames):
            path = Path(dirpath) / name
            if name.startswith(".") or path.is_symlink() or not path.is_file():
                continue
            if path.suffix.lower() in SUPPORTED_SUFFIXES:
                files.append(_describe(root, path))
    return sorted(files, key=lambda item: item.file_path)
