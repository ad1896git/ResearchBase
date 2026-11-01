"""Notification diagnostics must preserve history and never claim live status."""

import hashlib
import json
from pathlib import Path

import pytest
from scripts import pipeline_notifications as notifications


def event(folder, value):
    data = json.dumps(value).encode()
    path = folder / (hashlib.sha256(data).hexdigest() + ".json")
    path.write_bytes(data)
    return path


def test_inventory_keeps_conflicting_history_and_does_not_claim_current_state(tmp_path):
    first = event(tmp_path, dict(entry="task", status="blocked", reason="old failure"))
    second = event(tmp_path, dict(entry="task", status="done"))
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    result = notifications.inventory(tmp_path)
    assert result["counts"] == {"blocked": 1, "done": 1}
    assert result["event_count"] == 2
    assert result["live_task_state_verified"] is False
    assert {e["event_file"] for e in result["events"]} == {first.name, second.name}
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before


def test_empty_inventory_is_valid(tmp_path):
    assert notifications.inventory(tmp_path)["events"] == []


@pytest.mark.parametrize("mode", ["digest", "json", "status", "large", "symlink", "directory"])
def test_untrusted_or_corrupt_event_never_yields_partial_success(tmp_path, mode):
    event(tmp_path, dict(status="done"))
    if mode == "digest":
        (tmp_path / ("0" * 64 + ".json")).write_text("{}")
    elif mode == "json":
        data = b"invalid json"
        (tmp_path / (hashlib.sha256(data).hexdigest() + ".json")).write_bytes(data)
    elif mode == "status":
        event(tmp_path, dict(status=1))
    elif mode == "large":
        event(tmp_path, dict(status="x" * notifications.MAX_BYTES))
    elif mode == "symlink":
        (tmp_path / ("0" * 64 + ".json")).symlink_to(next(tmp_path.iterdir()))
    else:
        (tmp_path / "unexpected").mkdir()
    with pytest.raises(ValueError):
        notifications.inventory(tmp_path)


def test_noncanonical_or_missing_directory_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        notifications.inventory(Path("relative"))
    with pytest.raises(ValueError):
        notifications.inventory(tmp_path / "missing")
    link = tmp_path / "link"
    link.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError):
        notifications.inventory(link)


def test_limit_failure_does_not_hide_events(tmp_path, monkeypatch):
    event(tmp_path, dict(status="done"))
    monkeypatch.setattr(notifications, "MAX_EVENTS", 0)
    with pytest.raises(ValueError, match="limit exceeded"):
        notifications.inventory(tmp_path)


def test_concurrent_arrival_requires_retry(tmp_path, monkeypatch):
    event(tmp_path, dict(status="done"))
    original = Path.iterdir
    calls = 0

    def changed(folder):
        nonlocal calls
        calls += 1
        if calls == 2:
            event(folder, dict(status="blocked"))
        return original(folder)

    monkeypatch.setattr(Path, "iterdir", changed)
    with pytest.raises(ValueError, match="changed"):
        notifications.inventory(tmp_path)


def test_cli_failure_is_explicit_and_has_no_success_output(tmp_path, capsys):
    (tmp_path / "unexpected").write_text("bad")
    assert notifications.main(["--directory", str(tmp_path)]) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert json.loads(output.err)["status"] == "blocked"


def test_cli_success_labels_historical_events(tmp_path, capsys):
    event(tmp_path, dict(status="awaiting_merge"))
    assert notifications.main(["--directory", str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out)["kind"] == "historical_notification_inventory"
