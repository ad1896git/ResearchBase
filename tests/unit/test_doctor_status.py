"""Unit tests for the persisted doctor status and the next-command warning."""

from __future__ import annotations

import json
from pathlib import Path

from researchbase.foundation.doctor_status import default_status_path, pending_warning, write_status


def test_default_status_path_can_be_overridden(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "status.json"
    monkeypatch.setenv("RESEARCHBASE_DOCTOR_STATUS", str(target))
    assert default_status_path() == target


def test_failed_check_produces_a_chinese_warning(tmp_path: Path) -> None:
    path = tmp_path / "status.json"
    write_status(path, ok=False, records=3, problems=2, database="researchbase")
    warning = pending_warning(path)
    assert warning is not None
    assert "发现 2 个问题" in warning
    assert "rb doctor" in warning


def test_passing_check_is_silent(tmp_path: Path) -> None:
    path = tmp_path / "status.json"
    write_status(path, ok=True, records=3, problems=0, database="researchbase")
    assert pending_warning(path) is None


def test_missing_or_corrupt_status_is_silent(tmp_path: Path) -> None:
    assert pending_warning(tmp_path / "absent.json") is None
    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("{not json", encoding="utf-8")
    assert pending_warning(corrupt) is None


def test_status_file_records_no_credentials(tmp_path: Path) -> None:
    path = tmp_path / "status.json"
    write_status(path, ok=True, records=0, problems=0, database="researchbase")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert set(payload) == {"checked_at", "ok", "records", "problems", "database"}
    assert payload["database"] == "researchbase"
