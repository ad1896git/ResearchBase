from __future__ import annotations

import hashlib

import pytest

from researchbase.foundation.artifact_store import ContentAddressedFilesystemArtifactStore


def test_content_addressed_store_put_open_verify_and_idempotence(tmp_path) -> None:
    store = ContentAddressedFilesystemArtifactStore(tmp_path)
    payload = b"ResearchBase PR-00 smoke payload"

    identity = store.put(payload)

    assert identity == f"sha256:{hashlib.sha256(payload).hexdigest()}"
    assert store.exists(identity)
    assert store.open(identity) == payload
    assert store.verify(identity)
    assert store.put(payload) == identity


def test_content_addressed_store_rejects_wrong_expected_hash(tmp_path) -> None:
    store = ContentAddressedFilesystemArtifactStore(tmp_path)

    with pytest.raises(ValueError, match="does not match"):
        store.put_verified(b"payload", "sha256:" + "0" * 64)


def test_content_addressed_store_does_not_overwrite_existing_identity(tmp_path) -> None:
    store = ContentAddressedFilesystemArtifactStore(tmp_path)
    identity = store.put(b"first")

    target = store._path_for(identity)
    target.write_bytes(b"tampered")

    with pytest.raises(OSError, match="failed verification"):
        store.put(b"first")
