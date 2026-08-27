from __future__ import annotations

import os

import pytest

from researchbase.persistence.database import check_database_connection, create_database_engine


@pytest.mark.integration
def test_postgresql_connection_smoke() -> None:
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL is not set; run against the real PostgreSQL service")

    engine = create_database_engine()
    try:
        assert check_database_connection(engine)
    finally:
        engine.dispose()
