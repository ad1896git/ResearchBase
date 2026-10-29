import hashlib
import os
from pathlib import Path

import pytest

from researchbase.agent_runtime.application.bearing_evidence import (
    BearingEvidenceHashes,
    evaluate_bytes,
)
from researchbase.foundation.artifact_store import ContentAddressedFilesystemArtifactStore


@pytest.mark.parametrize("data", [b"", b"abc"])
def test_read_forms_and_boundary(tmp_path: Path, data: bytes) -> None:
    store = ContentAddressedFilesystemArtifactStore(tmp_path)
    identity = store.put_verified(data)
    for value in (identity, identity.removeprefix("sha256:")):
        assert store.open_bounded(value, max_bytes=max(1, len(data))) == data


@pytest.mark.parametrize("identity", [None, 1, b"a" * 64, "A" * 64, "a" * 63, "sha256:" + "g" * 64])
def test_invalid_identity(tmp_path: Path, identity: object) -> None:
    store = ContentAddressedFilesystemArtifactStore(tmp_path)
    with pytest.raises(ValueError):
        store.open_bounded(identity, max_bytes=1)  # type: ignore[arg-type]


@pytest.mark.parametrize("limit", [True, False, 0, -1, 16777217, 1.0, "1", None])
def test_invalid_limit(tmp_path: Path, limit: object) -> None:
    store = ContentAddressedFilesystemArtifactStore(tmp_path)
    with pytest.raises(ValueError):
        store.open_bounded("a" * 64, max_bytes=limit)  # type: ignore[arg-type]


def test_corruption_truncation_and_oversize(tmp_path: Path) -> None:
    store = ContentAddressedFilesystemArtifactStore(tmp_path)
    identity = store.put_verified(b"abc")
    path = store._path_for(identity)
    with pytest.raises(ValueError):
        store.open_bounded(identity, max_bytes=2)
    for data in (b"abd", b"ab"):
        path.write_bytes(data)
        with pytest.raises(ValueError, match="verification"):
            store.open_bounded(identity, max_bytes=3)
    path.unlink()
    with pytest.raises(FileNotFoundError):
        store.open_bounded(identity, max_bytes=3)


def test_growth_after_stat_is_bounded_and_closes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = ContentAddressedFilesystemArtifactStore(tmp_path)
    identity = store.put_verified(b"abc")
    original_stat, original_read, original_close = os.fstat, os.read, os.close
    reads: list[int] = []
    closed: list[int] = []

    def grow(fd: int) -> os.stat_result:
        result = original_stat(fd)
        store._path_for(identity).write_bytes(b"abcdefgh")
        return result

    def read(fd: int, count: int) -> bytes:
        reads.append(count)
        return original_read(fd, count)

    def close(fd: int) -> None:
        closed.append(fd)
        original_close(fd)

    monkeypatch.setattr(os, "fstat", grow)
    monkeypatch.setattr(os, "read", read)
    monkeypatch.setattr(os, "close", close)
    with pytest.raises(ValueError, match="limit"):
        store.open_bounded(identity, max_bytes=3)
    assert reads == [4]
    assert len(closed) == 1


@pytest.mark.parametrize("kind", ["symlink", "directory", "fifo"])
def test_special_files_rejected(tmp_path: Path, kind: str) -> None:
    store = ContentAddressedFilesystemArtifactStore(tmp_path)
    identity = store.put_verified(b"abc")
    path = store._path_for(identity)
    path.unlink()
    if kind == "symlink":
        path.symlink_to(tmp_path / "missing")
    elif kind == "directory":
        path.mkdir()
    else:
        os.mkfifo(path)
    with pytest.raises(ValueError):
        store.open_bounded(identity, max_bytes=3)


def test_real_cas_to_codec(tmp_path: Path) -> None:
    values = (
        b"sample_id,group_id,split,label\n1,g,eval,a\n2,g,eval,a\n3,g,eval,b\n4,g,eval,b\n",
        b"sample_id,prediction\n1,a\n2,b\n3,a\n4,b\n",
        b"sample_id,prediction\n1,a\n2,a\n3,a\n4,b\n",
        b'{"evaluation_split":"eval","classes":["a","b"],"groups":[{"group_id":"g","split":"eval"}]}',
    )
    store = ContentAddressedFilesystemArtifactStore(tmp_path)
    identities = tuple(store.put_verified(value) for value in values)
    labels, baseline, candidate, protocol = tuple(
        store.open_bounded(identity, max_bytes=16777216) for identity in identities
    )
    result = evaluate_bytes(
        labels=labels,
        baseline_predictions=baseline,
        candidate_predictions=candidate,
        protocol=protocol,
        expected_hashes=BearingEvidenceHashes(
            *(hashlib.sha256(value).hexdigest() for value in values)
        ),
    )
    assert result.baseline.confusion == ((1, 1), (1, 1))
    assert result.candidate.confusion == ((2, 0), (1, 1))
    assert (result.baseline.accuracy, result.candidate.accuracy, result.accuracy_delta) == (
        "0.500000",
        "0.750000",
        "0.250000",
    )
