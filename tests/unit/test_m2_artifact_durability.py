"""Evidence durability must precede the database transaction."""

import os
import stat

import pytest

from researchbase.foundation.artifact_store import ContentAddressedFilesystemArtifactStore


def test_directory_sync_failure_propagates_and_same_bytes_can_recover(tmp_path, monkeypatch):
    store = ContentAddressedFilesystemArtifactStore(tmp_path / "cas")
    original = os.fsync
    synced_directories = []

    def fail_directory(fd):
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            raise OSError("injected directory durability failure")
        return original(fd)

    monkeypatch.setattr(os, "fsync", fail_directory)
    with pytest.raises(OSError, match="durability failure"):
        store.put_verified(b"retained permitted evidence")

    def record_directory(fd):
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            synced_directories.append(fd)
        return original(fd)

    monkeypatch.setattr(os, "fsync", record_directory)
    identity = store.put_verified(b"retained permitted evidence")
    assert store.verify(identity)
    assert len(synced_directories) == 5  # shard directories, sha256, CAS root, root parent
