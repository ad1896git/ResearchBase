from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from datetime import UTC, datetime

import pytest
from sqlalchemy.engine import Engine
from tests.application_compat import LegacyApplicationService as ApplicationService

from researchbase.foundation.time import FixedClock
from researchbase.persistence.database import create_database_engine, create_session_factory
from researchbase.persistence.uow import SqlAlchemyUnitOfWork


def postgres_resources() -> Iterator[tuple[Callable[[], ApplicationService], Engine]]:
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL is not set; run against the real PostgreSQL service")
    engine = create_database_engine()
    sessions = create_session_factory(engine)
    clock = FixedClock(datetime(2026, 8, 30, 0, 0, tzinfo=UTC))
    try:
        yield lambda: ApplicationService(lambda: SqlAlchemyUnitOfWork(sessions), clock), engine
    finally:
        engine.dispose()
