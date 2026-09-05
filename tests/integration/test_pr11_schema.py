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


def test_statistical_result_tables_have_exact_columns(engine: Engine) -> None:
    with engine.connect() as connection:
        result_columns = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema='public' AND table_name='statistical_results'"
                )
            )
        }
        input_columns = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema='public' AND table_name='statistical_result_inputs'"
                )
            )
        }

    assert result_columns == {
        "id",
        "project_id",
        "analysis_type",
        "result_payload",
        "analysis_definition",
        "content_hash",
        "created_by",
        "created_at",
    }
    assert input_columns == {
        "statistical_result_id",
        "measurement_id",
        "input_role",
        "ordinal",
    }


def test_statistical_result_constraints_are_exact_and_restrictive(engine: Engine) -> None:
    with engine.connect() as connection:
        result_constraints = {
            row[0]: row[1]
            for row in connection.execute(
                text(
                    "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
                    "WHERE conrelid='statistical_results'::regclass "
                    "AND contype IN ('p', 'f', 'u', 'c')"
                )
            )
        }
        input_constraints = {
            row[0]: row[1]
            for row in connection.execute(
                text(
                    "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
                    "WHERE conrelid='statistical_result_inputs'::regclass "
                    "AND contype IN ('p', 'f', 'u', 'c')"
                )
            )
        }

    assert set(result_constraints) == {
        "statistical_results_pkey",
        "statistical_results_project_id_fkey",
        "statistical_results_created_by_fkey",
    }
    assert set(input_constraints) == {
        "statistical_result_inputs_pkey",
        "statistical_result_inputs_statistical_result_id_fkey",
        "statistical_result_inputs_measurement_id_fkey",
    }
    assert all(
        "ON DELETE RESTRICT" in definition
        for name, definition in result_constraints.items()
        if name.endswith("_fkey")
    )
    assert all(
        "ON DELETE RESTRICT" in definition
        for name, definition in input_constraints.items()
        if name.endswith("_fkey")
    )
    assert (
        "statistical_result_id, measurement_id, input_role"
        in input_constraints["statistical_result_inputs_pkey"]
    )


def test_statistical_results_have_no_unauthorized_lifecycle_or_content_uniqueness(
    engine: Engine,
) -> None:
    with engine.connect() as connection:
        result_indexes = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT indexname FROM pg_indexes "
                    "WHERE schemaname='public' AND tablename='statistical_results'"
                )
            )
        }
        input_indexes = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT indexname FROM pg_indexes "
                    "WHERE schemaname='public' AND tablename='statistical_result_inputs'"
                )
            )
        }
        result_columns = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema='public' AND table_name='statistical_results'"
                )
            )
        }

    assert result_indexes == {"statistical_results_pkey"}
    assert input_indexes == {"statistical_result_inputs_pkey"}
    assert (
        not {
            "row_version",
            "status",
            "updated_at",
            "current_version_id",
        }
        & result_columns
    )


def test_statistical_result_tables_expose_immutability_triggers(engine: Engine) -> None:
    with engine.connect() as connection:
        result_triggers = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT tgname FROM pg_trigger "
                    "WHERE tgrelid='statistical_results'::regclass AND NOT tgisinternal"
                )
            )
        }
        input_triggers = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT tgname FROM pg_trigger "
                    "WHERE tgrelid='statistical_result_inputs'::regclass AND NOT tgisinternal"
                )
            )
        }

    assert result_triggers == {
        "statistical_results_immutable",
        "statistical_result_requires_input",
        "pr17d_statistical_result_update",
        "pr17d_statistical_result_delete",
    }
    assert input_triggers == {
        "statistical_result_inputs_immutable",
        "pr17d_statistical_result_input_update",
        "pr17d_statistical_result_input_delete",
    }


def test_statistical_result_input_guard_is_deferred_and_transaction_safe(engine: Engine) -> None:
    with engine.connect() as connection:
        guard = connection.execute(
            text(
                "SELECT tgdeferrable, tginitdeferred, tgtype "
                "FROM pg_trigger WHERE tgname='statistical_result_requires_input'"
            )
        ).one()

    assert guard.tgdeferrable is True
    assert guard.tginitdeferred is True
