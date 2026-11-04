"""Read-only integrity check for stored full-text artifacts.

The check takes plain records and a store root. It has no database dependency
and never creates directories or writes files.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

_SHA256_HEX = re.compile(r"[0-9a-f]{64}")

PROBLEM_INVALID_HASH = "invalid_hash"
PROBLEM_MISSING = "missing"
PROBLEM_HASH_MISMATCH = "hash_mismatch"
PROBLEM_SIZE_MISMATCH = "size_mismatch"


@dataclass(frozen=True, slots=True)
class FulltextRecord:
    """One full-text artifact version as recorded in the database."""

    artifact_version_id: str
    content_hash: str
    byte_size: int | None


@dataclass(frozen=True, slots=True)
class IntegrityProblem:
    artifact_version_id: str
    content_hash: str
    kind: str


@dataclass(frozen=True, slots=True)
class IntegrityReport:
    checked_records: int
    checked_files: int
    problems: tuple[IntegrityProblem, ...]

    @property
    def ok(self) -> bool:
        return not self.problems


@dataclass(frozen=True, slots=True)
class _BlobState:
    present: bool
    hash_ok: bool
    size: int | None


def blob_path(store_root: Path, content_hash: str) -> Path:
    """Path layout shared with ContentAddressedFilesystemArtifactStore."""
    return store_root / "sha256" / content_hash[:2] / content_hash[2:4] / content_hash


def _inspect_blob(store_root: Path, content_hash: str) -> _BlobState:
    path = blob_path(store_root, content_hash)
    if not path.is_file():
        return _BlobState(present=False, hash_ok=False, size=None)
    content = path.read_bytes()
    return _BlobState(
        present=True,
        hash_ok=hashlib.sha256(content).hexdigest() == content_hash,
        size=len(content),
    )


def check_fulltext_records(records: Iterable[FulltextRecord], store_root: Path) -> IntegrityReport:
    checked: list[FulltextRecord] = list(records)
    blobs: dict[str, _BlobState] = {}
    problems: list[IntegrityProblem] = []
    for record in checked:
        content_hash = record.content_hash.strip()
        if not _SHA256_HEX.fullmatch(content_hash):
            problems.append(
                IntegrityProblem(record.artifact_version_id, content_hash, PROBLEM_INVALID_HASH)
            )
            continue
        if content_hash not in blobs:
            blobs[content_hash] = _inspect_blob(store_root, content_hash)
        state = blobs[content_hash]
        if not state.present:
            kind = PROBLEM_MISSING
        elif not state.hash_ok:
            kind = PROBLEM_HASH_MISMATCH
        elif record.byte_size is not None and record.byte_size != state.size:
            kind = PROBLEM_SIZE_MISMATCH
        else:
            continue
        problems.append(IntegrityProblem(record.artifact_version_id, content_hash, kind))
    return IntegrityReport(
        checked_records=len(checked),
        checked_files=len(blobs),
        problems=tuple(problems),
    )
