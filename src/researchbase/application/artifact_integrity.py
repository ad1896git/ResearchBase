"""Application service for the read-only full-text integrity check (`rb doctor`).

The record loader is injected by the composition root, so this module depends
only on foundation types and never on persistence.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from researchbase.foundation.artifact_integrity import (
    FulltextRecord,
    IntegrityReport,
    check_fulltext_records,
)


class ArtifactIntegrityService:
    def __init__(
        self,
        *,
        load_records: Callable[[], list[FulltextRecord]],
        store_root: Path,
        database: str | None,
    ) -> None:
        self._load_records = load_records
        self.store_root = store_root
        self.database = database

    def check(self) -> IntegrityReport:
        return check_fulltext_records(self._load_records(), self.store_root)
