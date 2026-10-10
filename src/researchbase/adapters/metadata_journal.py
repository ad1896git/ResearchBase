"""Local operational dispatch journal; never canonical scientific persistence."""

from __future__ import annotations

import fcntl
import json
import os
import tempfile
from pathlib import Path

from researchbase.application.metadata_observation import BibliographicMetadataProvider
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


class MetadataDispatchJournal:
    def __init__(self, root: Path, provider: BibliographicMetadataProvider):
        self.root = root
        self.provider = provider

    def obtain(self, key: str, fingerprint: str, doi: str | None, title: str, timeout: int):
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        path = self.root / (key + ".json")
        with (self.root / (key + ".lock")).open("a+b") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if path.exists():
                value = json.loads(path.read_text())
                if value["fingerprint"] != fingerprint:
                    raise ResearchBaseError(
                        ErrorCode.IDEMPOTENCY_CONFLICT, "invocation input changed"
                    )
                if "observation" not in value:
                    raise ResearchBaseError(
                        ErrorCode.INVALID_STATE_TRANSITION,
                        "dispatch outcome is uncertain; use a distinct invocation ID",
                    )
                return value["observation"]
            self._save(path, {"fingerprint": fingerprint})
            observation = self.provider.observe(doi, title, timeout)
            # A journal/storage failure propagates. It is not provider unavailability.
            self._save(path, {"fingerprint": fingerprint, "observation": observation})
            return observation

    def _save(self, path, value):
        fd, name = tempfile.mkstemp(dir=self.root)
        try:
            with os.fdopen(fd, "w") as stream:
                json.dump(value, stream, ensure_ascii=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, path)
            directory = os.open(self.root, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if os.path.exists(name):
                os.unlink(name)
