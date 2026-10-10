"""Content-addressed artifact storage infrastructure for the PR-00 smoke gate."""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path
from typing import Protocol


class ArtifactStore(Protocol):
    """Port for immutable byte storage addressed by content identity."""

    def put_verified(self, data: bytes, expected_hash: str | None = None) -> str:
        """Store bytes and return their ``sha256:<hex>`` identity."""
        ...

    def open(self, identity: str) -> bytes:
        """Read the exact bytes associated with an identity."""
        ...

    def exists(self, identity: str) -> bool:
        """Return whether an identity is present."""
        ...

    def verify(self, identity: str) -> bool:
        """Verify stored bytes against their content identity."""
        ...


class ContentAddressedFilesystemArtifactStore:
    """Small immutable filesystem backend used by the PR-00 infrastructure smoke test."""

    def __init__(self, root: Path) -> None:
        self.root = root
        (self.root / "sha256").mkdir(parents=True, exist_ok=True)

    def put(self, data: bytes, expected_hash: str | None = None) -> str:
        """Compatibility convenience for the PR-00 ``put(bytes)`` smoke contract."""
        return self.put_verified(data, expected_hash)

    def put_verified(self, data: bytes, expected_hash: str | None = None) -> str:
        digest = hashlib.sha256(data).hexdigest()
        identity = f"sha256:{digest}"
        if expected_hash is not None and self._normalise_identity(expected_hash) != identity:
            raise ValueError("provided hash does not match content")

        target = self._path_for(identity)
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(dir=target.parent, prefix=".tmp-")
        temporary = Path(temporary_name)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(temporary, target)
            except FileExistsError:
                if not self.verify(identity):
                    raise OSError("existing content-addressed object failed verification") from None
            finally:
                temporary.unlink(missing_ok=True)
            # File data fsync alone does not make the new CAS directory entry durable.
            # Sync the object path and newly-created ancestor entries before DB commit.
            directory = target.parent
            stop = self.root.parent
            while True:
                directory_fd = os.open(directory, os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
                if directory == stop:
                    break
                directory = directory.parent
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
        return identity

    def open(self, identity: str) -> bytes:
        return self._path_for(identity).read_bytes()

    def exists(self, identity: str) -> bool:
        return self._path_for(identity).is_file()

    def verify(self, identity: str) -> bool:
        try:
            expected = self._normalise_identity(identity)
            content = self.open(expected)
        except (FileNotFoundError, ValueError):
            return False
        return hashlib.sha256(content).hexdigest() == expected.removeprefix("sha256:")

    def _path_for(self, identity: str) -> Path:
        normalised = self._normalise_identity(identity)
        digest = normalised.removeprefix("sha256:")
        return self.root / "sha256" / digest[:2] / digest[2:4] / digest

    @staticmethod
    def _normalise_identity(identity: str) -> str:
        digest = identity.removeprefix("sha256:")
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
            raise ValueError("identity must be a SHA-256 digest")
        return f"sha256:{digest}"
