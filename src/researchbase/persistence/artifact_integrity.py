"""Read-only query for stored artifact records used by `rb doctor`.

Every artifact version is checked, not only those linked to literature full text:
a stored file that any record points to must still be intact.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine

from researchbase.foundation.artifact_integrity import FulltextRecord

_ARTIFACT_RECORDS_SQL = text(
    """
    SELECT av.id::text AS artifact_version_id, av.content_hash, av.byte_size
    FROM artifact_versions AS av
    ORDER BY artifact_version_id
    """
)


def load_fulltext_records(engine: Engine) -> list[FulltextRecord]:
    with engine.connect() as connection:
        rows = connection.execute(_ARTIFACT_RECORDS_SQL).all()
    return [
        FulltextRecord(
            artifact_version_id=row.artifact_version_id,
            content_hash=row.content_hash,
            byte_size=row.byte_size,
        )
        for row in rows
    ]
