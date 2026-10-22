"""Exact immutable AgentVersion reads within the caller's existing snapshot."""

from datetime import datetime

from sqlalchemy import text

from researchbase.foundation.time import to_utc


def version(session, identity):
    row = (
        session.execute(text("SELECT * FROM agent_versions WHERE id=:id"), {"id": identity})
        .mappings()
        .first()
    )
    return {k: to_utc(v) if isinstance(v, datetime) else v for k, v in row.items()} if row else None
