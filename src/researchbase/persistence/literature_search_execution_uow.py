"""PR2-04-only database error normalization boundary."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.uow import SqlAlchemyUnitOfWork, _normalize_database_error


def literature_search_execution_uow_factory(
    session_factory: Callable[[], Session] | Any,
) -> Callable[[], SqlAlchemyUnitOfWork]:
    """Create PR2-04 transactions with its narrowly scoped deadlock mapping."""
    return lambda: SqlAlchemyUnitOfWork(session_factory, pr204_error_normalization=True)


def normalize_literature_search_execution_error(
    exc: BaseException,
) -> ResearchBaseError | None:
    """Normalize PR2-04 SQLSTATEs without changing historical UoW behavior."""
    existing = _normalize_database_error(exc)
    if existing is not None:
        return existing
    if isinstance(exc, DBAPIError) and getattr(exc.orig, "sqlstate", None) == "40P01":
        return ResearchBaseError(
            ErrorCode.CONCURRENT_MODIFICATION,
            "deadlocked literature-search execution transaction must be retried",
        )
    if isinstance(exc, DBAPIError) and exc.connection_invalidated:
        return ResearchBaseError(
            ErrorCode.CONCURRENT_MODIFICATION,
            "literature-search execution transaction connection was lost; reread before retry",
        )
    return None
