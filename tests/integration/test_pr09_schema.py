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


@pytest.mark.parametrize(
    ("table", "expected_columns"),
    [
        (
            "runs",
            {
                "id",
                "project_id",
                "experiment_spec_version_id",
                "run_type",
                "status",
                "inputs_sealed_at",
                "started_at",
                "finished_at",
                "exit_code",
                "failure_reason",
                "created_by",
                "created_at",
                "row_version",
            },
        ),
        ("run_dataset_inputs", {"run_id", "dataset_snapshot_id", "role", "ordinal"}),
        ("run_artifact_inputs", {"run_id", "artifact_version_id", "role", "ordinal"}),
    ],
)
def test_pr09_exact_columns(engine: Engine, table: str, expected_columns: set[str]) -> None:
    with engine.connect() as connection:
        columns = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema='public' AND table_name=:table"
                ),
                {"table": table},
            )
        }
    assert columns == expected_columns


def test_pr09_constraints_are_restrictive_and_closed(engine: Engine) -> None:
    with engine.connect() as connection:
        constraints = {
            row[0]: row[1]
            for row in connection.execute(
                text(
                    "SELECT conname, pg_get_constraintdef(oid) "
                    "FROM pg_constraint WHERE conrelid IN "
                    "('runs'::regclass, 'run_dataset_inputs'::regclass, "
                    "'run_artifact_inputs'::regclass)"
                )
            )
        }
    assert {"runs_pkey", "run_dataset_inputs_pkey", "run_artifact_inputs_pkey"} <= set(constraints)
    assert "ck_runs_status" in constraints
    assert "ck_runs_inputs_sealed" in constraints
    assert "ck_run_dataset_inputs_role" in constraints
    assert "ck_run_artifact_inputs_role" in constraints
    foreign_keys = {
        name: definition for name, definition in constraints.items() if name.endswith("_fkey")
    }
    assert len(foreign_keys) == 7
    assert all("ON DELETE RESTRICT" in definition for definition in foreign_keys.values())
