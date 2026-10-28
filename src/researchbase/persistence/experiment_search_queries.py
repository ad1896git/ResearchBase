"""Detached complete history reads in the caller's existing formal-read snapshot."""

from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from researchbase.agent_runtime.ports.search_repository import (
    StoredSearchEvent,
    StoredSearchHistory,
    StoredSearchNode,
    StoredSearchNodeRun,
    StoredSearchSession,
)
from researchbase.foundation.time import to_utc


class SqlAlchemyExperimentSearchQueries:
    def __init__(self, session: Session):
        self._session = session

    def _rows(self, sql: str, identity: UUID):
        return [
            {k: to_utc(v) if isinstance(v, datetime) else v for k, v in row.items()}
            for row in self._session.execute(text(sql), {"id": identity}).mappings()
        ]

    def search_session(self, identity: UUID) -> StoredSearchSession | None:
        rows = self._rows("SELECT * FROM experiment_search_sessions WHERE id=:id", identity)
        return cast(StoredSearchSession, rows[0]) if rows else None

    def retained_history(self, session: UUID) -> StoredSearchHistory:
        # Read complete collections. Do not hide corrupt foreign-task rows with a
        # task predicate, or hide unsupported history with a catalog predicate.
        return StoredSearchHistory(
            tuple(
                cast(
                    list[StoredSearchNode],
                    self._rows(
                        "SELECT * FROM experiment_search_nodes WHERE search_session_id=:id "
                        "ORDER BY depth,id",
                        session,
                    ),
                )
            ),
            tuple(
                cast(
                    list[StoredSearchEvent],
                    self._rows(
                        "SELECT * FROM experiment_search_events WHERE search_session_id=:id "
                        "ORDER BY sequence,id",
                        session,
                    ),
                )
            ),
            tuple(
                cast(
                    list[StoredSearchNodeRun],
                    self._rows(
                        "SELECT * FROM experiment_search_node_runs WHERE search_session_id=:id "
                        "ORDER BY id",
                        session,
                    ),
                )
            ),
        )
