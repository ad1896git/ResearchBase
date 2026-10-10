import json
import os
import stat
from concurrent.futures import ThreadPoolExecutor

import pytest

from researchbase.adapters.metadata_journal import MetadataDispatchJournal
from researchbase.foundation.errors import ResearchBaseError


class Provider:
    provider_id = "test"
    provider_version = "1"
    adapter_version = "1"
    endpoint = "https://example.org"

    def __init__(self):
        self.calls = 0

    def observe(self, doi: str | None, title: str, timeout: int = 15):
        self.calls += 1
        return {"outcome": "MATCH"}


def test_completed_concurrent_replay_does_not_redispatch(tmp_path):
    provider = Provider()
    journal = MetadataDispatchJournal(tmp_path, provider)
    with ThreadPoolExecutor(max_workers=2) as pool:
        values = list(
            pool.map(lambda _: journal.obtain("key", "fingerprint", None, "title", 10), range(2))
        )
    assert values == [{"outcome": "MATCH"}] * 2 and provider.calls == 1
    with pytest.raises(ResearchBaseError):
        journal.obtain("key", "changed", None, "title", 10)


def test_uncertain_intent_is_not_reissued_or_fabricated(tmp_path):
    provider = Provider()
    (tmp_path / "key.json").write_text(json.dumps({"fingerprint": "same"}))
    with pytest.raises(ResearchBaseError):
        MetadataDispatchJournal(tmp_path, provider).obtain("key", "same", None, "title", 10)
    assert provider.calls == 0


@pytest.mark.parametrize("existing", [False, True])
def test_directory_chain_and_intent_are_durable_before_dispatch(tmp_path, monkeypatch, existing):
    root = tmp_path / "installation" / "cas" / "metadata-invocations"
    if existing:
        root.mkdir(parents=True)
    directories = (root, root.parent, root.parent.parent, tmp_path)
    events = []
    real_sync, real_replace = os.fsync, os.replace

    def sync(fd):
        info = os.fstat(fd)
        if stat.S_ISDIR(info.st_mode):
            path = next((p for p in directories if p.stat().st_ino == info.st_ino), None)
            events.append(("directory", path))
        else:
            events.append(("file", None))
        return real_sync(fd)

    def replace(source, target):
        real_replace(source, target)
        events.append(("replace", target))

    class RecordingProvider(Provider):
        def observe(self, doi: str | None, title: str, timeout: int = 15):
            events.append(("dispatch", None))
            assert json.loads((root / "key.json").read_text()) == {"fingerprint": "same"}
            return super().observe(doi, title, timeout)

    monkeypatch.setattr(os, "fsync", sync)
    monkeypatch.setattr(os, "replace", replace)
    provider = RecordingProvider()
    journal = MetadataDispatchJournal(root, provider)
    assert journal.obtain("key", "same", None, "title", 10) == {"outcome": "MATCH"}
    before_dispatch = events[: events.index(("dispatch", None))]
    for directory in directories:
        assert ("directory", directory) in before_dispatch
    chain_positions = [before_dispatch.index(("directory", p)) for p in directories]
    assert chain_positions == sorted(chain_positions)
    assert chain_positions[-1] < before_dispatch.index(("file", None))
    # The actual intent bytes must be synced before rename, and its entry after rename.
    assert before_dispatch[-3:] == [
        ("file", None),
        ("replace", root / "key.json"),
        ("directory", root),
    ]
    # A new journal instance reuses the completed response without external dispatch.
    assert MetadataDispatchJournal(root, provider).obtain("key", "same", None, "title", 10) == {
        "outcome": "MATCH"
    }
    assert provider.calls == 1


@pytest.mark.parametrize("failed_parent", ["cas", "installation"])
def test_parent_sync_failure_prevents_dispatch_and_can_retry(tmp_path, monkeypatch, failed_parent):
    root = tmp_path / "installation" / "cas" / "metadata-invocations"
    target = root.parent if failed_parent == "cas" else root.parent.parent
    provider = Provider()
    journal = MetadataDispatchJournal(root, provider)
    real_sync = os.fsync

    def sync(fd):
        info = os.fstat(fd)
        if stat.S_ISDIR(info.st_mode) and info.st_ino == target.stat().st_ino:
            raise OSError("injected parent sync failure")
        return real_sync(fd)

    monkeypatch.setattr(os, "fsync", sync)
    with pytest.raises(OSError, match="parent sync failure"):
        journal.obtain("key", "same", None, "title", 10)
    assert provider.calls == 0
    # Failed first creation leaves directories present; retry must still sync the chain.
    with pytest.raises(OSError, match="parent sync failure"):
        journal.obtain("key", "same", None, "title", 10)
    assert provider.calls == 0
    monkeypatch.setattr(os, "fsync", real_sync)
    assert journal.obtain("key", "same", None, "title", 10) == {"outcome": "MATCH"}
    assert provider.calls == 1


def test_intent_file_sync_failure_prevents_dispatch(tmp_path, monkeypatch):
    provider = Provider()
    real_sync = os.fsync

    def sync(fd):
        if stat.S_ISREG(os.fstat(fd).st_mode):
            raise OSError("injected intent sync failure")
        return real_sync(fd)

    monkeypatch.setattr(os, "fsync", sync)
    with pytest.raises(OSError, match="intent sync failure"):
        MetadataDispatchJournal(tmp_path / "journal", provider).obtain(
            "key", "same", None, "title", 10
        )
    assert provider.calls == 0


def test_directory_creation_failure_prevents_dispatch(tmp_path, monkeypatch):
    root = tmp_path / "journal"
    provider = Provider()
    real_mkdir = type(root).mkdir

    def mkdir(path, *args, **kwargs):
        if path == root:
            raise PermissionError("injected directory creation failure")
        return real_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(type(root), "mkdir", mkdir)
    with pytest.raises(PermissionError, match="directory creation failure"):
        MetadataDispatchJournal(root, provider).obtain("key", "same", None, "title", 10)
    assert provider.calls == 0
