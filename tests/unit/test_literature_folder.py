"""Literature folder: change classification and read-only scanning (no database)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from researchbase.adapters.literature_folder import (
    FolderFile,
    FolderScanError,
    doi_in,
    scan_folder,
)
from researchbase.application.literature_folder import classify


def _file(path: str, digest: str) -> FolderFile:
    return FolderFile(
        file_path=path,
        content_sha256=digest,
        size_bytes=10,
        file_mtime=datetime(2026, 11, 3, tzinfo=UTC),
        title=None,
        doi=None,
    )


def _known(path: str, digest: str) -> dict[str, object]:
    return {"file_path": path, "content_sha256": digest, "observation_status": "PRESENT"}


def test_first_scan_reports_everything_as_new():
    result = classify({}, [_file("a.pdf", "1"), _file("b.txt", "2")])
    assert result["new"] == ["a.pdf", "b.txt"]
    assert result["moved"] == [] and result["missing"] == []


def test_renamed_file_with_same_bytes_is_a_move_not_new_plus_missing():
    previous = {"old/name.pdf": _known("old/name.pdf", "h1")}
    result = classify(previous, [_file("new/name.pdf", "h1")])
    assert result["moved"] == [{"from": "old/name.pdf", "to": "new/name.pdf"}]
    assert result["new"] == [] and result["missing"] == []


def test_changed_bytes_are_modified_and_vanished_files_are_missing():
    previous = {"a.pdf": _known("a.pdf", "h1"), "b.pdf": _known("b.pdf", "h2")}
    result = classify(previous, [_file("a.pdf", "h9")])
    assert result["modified"] == ["a.pdf"]
    assert result["missing"] == ["b.pdf"]
    assert result["unchanged"] == 0


def test_unchanged_files_and_duplicate_groups_are_counted():
    previous = {"a.pdf": _known("a.pdf", "h1")}
    result = classify(previous, [_file("a.pdf", "h1"), _file("copy.pdf", "h1")])
    assert result["unchanged"] == 1
    assert result["new"] == ["copy.pdf"]
    assert result["duplicates"] == [["a.pdf", "copy.pdf"]]


def test_doi_is_found_and_trailing_punctuation_dropped():
    assert doi_in("see doi 10.1234/nap.2026.7.") == "10.1234/nap.2026.7"
    assert doi_in("nothing") is None


def test_scan_skips_hidden_unsupported_and_reads_supported(tmp_path: Path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "paper.txt").write_text("Study. DOI 10.5555/abc.1", encoding="utf-8")
    (tmp_path / "notes.md").write_text("plain", encoding="utf-8")
    (tmp_path / "image.png").write_bytes(b"not text")
    (tmp_path / ".hidden.txt").write_text("secret", encoding="utf-8")
    (tmp_path / "broken.pdf").write_bytes(b"%PDF-broken")

    files = scan_folder(tmp_path)

    assert [item.file_path for item in files] == ["broken.pdf", "notes.md", "sub/paper.txt"]
    by_path = {item.file_path: item for item in files}
    assert by_path["sub/paper.txt"].doi == "10.5555/abc.1"
    assert by_path["broken.pdf"].title is None and by_path["broken.pdf"].doi is None
    assert len(by_path["notes.md"].content_sha256) == 64


def test_scan_skips_symlinks(tmp_path: Path):
    target = tmp_path / "real.txt"
    target.write_text("x", encoding="utf-8")
    (tmp_path / "link.txt").symlink_to(target)
    assert [item.file_path for item in scan_folder(tmp_path)] == ["real.txt"]


def test_missing_folder_is_a_scan_error(tmp_path: Path):
    with pytest.raises(FolderScanError):
        scan_folder(tmp_path / "nope")
