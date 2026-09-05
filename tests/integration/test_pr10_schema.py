from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine

from researchbase.persistence.database import create_database_engine

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def engine() -> Iterator[Engine]:
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL is not set; run against the real PostgreSQL service")
    database_engine = create_database_engine()
    try:
        yield database_engine
    finally:
        database_engine.dispose()


def test_measurements_has_exact_frozen_columns(engine: Engine) -> None:
    with engine.connect() as connection:
        columns = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema='public' AND table_name='measurements'"
                )
            )
        }
    assert columns == {
        "id",
        "run_id",
        "metric_definition_version_id",
        "numeric_value",
        "structured_value",
        "unit",
        "evaluation_scope",
        "content_hash",
        "created_by",
        "created_at",
    }


def test_measurements_constraints_are_restrictive_and_xor(engine: Engine) -> None:
    with engine.connect() as connection:
        constraints = {
            row[0]: row[1]
            for row in connection.execute(
                text(
                    "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
                    "WHERE conrelid = 'measurements'::regclass"
                )
            )
        }
    assert "measurements_pkey" in constraints
    assert "ck_measurements_value_xor" in constraints
    assert "numeric_value IS NOT NULL" in constraints["ck_measurements_value_xor"]
    foreign_keys = {
        name: definition for name, definition in constraints.items() if name.endswith("_fkey")
    }
    assert len(foreign_keys) == 3
    assert all("ON DELETE RESTRICT" in definition for definition in foreign_keys.values())


def test_measurements_have_no_content_uniqueness_or_lifecycle_columns(engine: Engine) -> None:
    with engine.connect() as connection:
        indexes = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT indexname FROM pg_indexes "
                    "WHERE schemaname='public' AND tablename='measurements'"
                )
            )
        }
        columns = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema='public' AND table_name='measurements'"
                )
            )
        }
    assert indexes == {"measurements_pkey"}
    assert not {"row_version", "status", "updated_at", "current_version_id"} & columns


def test_measurements_expose_database_immutability_triggers(engine: Engine) -> None:
    with engine.connect() as connection:
        triggers = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT tgname FROM pg_trigger "
                    "WHERE tgrelid='measurements'::regclass AND NOT tgisinternal"
                )
            )
        }
    assert triggers == {
        "measurements_immutable",
        "pr17d_measurement_update",
        "pr17d_measurement_delete",
    }
