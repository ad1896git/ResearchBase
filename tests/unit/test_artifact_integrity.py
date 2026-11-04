"""Unit tests for the full-text integrity check (no database, no network)."""

from __future__ import annotations

import hashlib
from pathlib import Path

from researchbase.foundation.artifact_integrity import (
    PROBLEM_HASH_MISMATCH,
    PROBLEM_INVALID_HASH,
    PROBLEM_MISSING,
    PROBLEM_SIZE_MISMATCH,
    FulltextRecord,
    blob_path,
    check_fulltext_records,
)


def _store_blob(root: Path, content: bytes) -> str:
    digest = hashlib.sha256(content).hexdigest()
    path = blob_path(root, digest)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return digest


def test_matching_records_pass(tmp_path: Path) -> None:
    digest = _store_blob(tmp_path, b"full text")
    report = check_fulltext_records([FulltextRecord("v1", digest, len(b"full text"))], tmp_path)
    assert report.ok
    assert report.checked_records == 1
    assert report.checked_files == 1


def test_missing_file_is_reported(tmp_path: Path) -> None:
    digest = hashlib.sha256(b"never stored").hexdigest()
    report = check_fulltext_records([FulltextRecord("v1", digest, 12)], tmp_path)
    assert [(p.artifact_version_id, p.kind) for p in report.problems] == [("v1", PROBLEM_MISSING)]


def test_altered_content_is_a_hash_mismatch(tmp_path: Path) -> None:
    digest = _store_blob(tmp_path, b"original")
    blob_path(tmp_path, digest).write_bytes(b"tampered")
    report = check_fulltext_records([FulltextRecord("v1", digest, 8)], tmp_path)
    assert [p.kind for p in report.problems] == [PROBLEM_HASH_MISMATCH]


def test_recorded_size_must_match_the_file(tmp_path: Path) -> None:
    digest = _store_blob(tmp_path, b"abc")
    report = check_fulltext_records([FulltextRecord("v1", digest, 99)], tmp_path)
    assert [p.kind for p in report.problems] == [PROBLEM_SIZE_MISMATCH]


def test_unknown_size_is_not_a_problem(tmp_path: Path) -> None:
    digest = _store_blob(tmp_path, b"abc")
    assert check_fulltext_records([FulltextRecord("v1", digest, None)], tmp_path).ok


def test_malformed_hash_is_reported_without_touching_disk(tmp_path: Path) -> None:
    report = check_fulltext_records([FulltextRecord("v1", "not-a-hash", 3)], tmp_path)
    assert [p.kind for p in report.problems] == [PROBLEM_INVALID_HASH]
    assert not (tmp_path / "sha256").exists()


def test_several_records_sharing_one_file_are_each_checked(tmp_path: Path) -> None:
    digest = _store_blob(tmp_path, b"shared")
    report = check_fulltext_records(
        [FulltextRecord("v1", digest, 6), FulltextRecord("v2", digest, 6)], tmp_path
    )
    assert report.ok
    assert report.checked_records == 2
    assert report.checked_files == 1


def test_no_records_is_ok_and_creates_nothing(tmp_path: Path) -> None:
    root = tmp_path / "not-yet-created"
    report = check_fulltext_records([], root)
    assert report.ok
    assert report.checked_records == 0
    assert not root.exists()
