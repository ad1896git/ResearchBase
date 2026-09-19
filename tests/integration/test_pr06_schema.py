from __future__ import annotations

import os
from collections.abc import Iterator
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from researchbase.persistence.database import create_database_engine

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def engine() -> Iterator[Engine]:
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL is not set; run against the real PostgreSQL service")
    value = create_database_engine()
    try:
        yield value
    finally:
        value.dispose()


def test_pr06_schema_columns_constraints_and_restrict_foreign_keys(engine: Engine) -> None:
    with engine.connect() as connection:
        assert {
            connection.execute(
                text("SELECT to_regclass(:name)"), {"name": f"public.{table}"}
            ).scalar_one()
            for table in ("datasets", "dataset_snapshots")
        } == {"datasets", "dataset_snapshots"}
        rows = connection.execute(
            text(
                """
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name IN ('datasets', 'dataset_snapshots')
                """
            )
        ).all()
        columns: dict[str, set[str]] = {}
        for row in rows:
            columns.setdefault(row.table_name, set()).add(row.column_name)
        assert columns["datasets"] == {
            "id",
            "project_id",
            "name",
            "description",
            "source_locator",
            "lifecycle_status",
            "created_by",
            "created_at",
            "row_version",
        }
        assert columns["dataset_snapshots"] == {
            "id",
            "dataset_id",
            "manifest_hash",
            "selection_definition",
            "manifest_locator",
            "content_hash",
            "created_by",
            "created_at",
        }
        foreign_keys = connection.execute(
            text(
                """
                SELECT tc.table_name, kcu.column_name, rc.delete_rule
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.table_schema = kcu.table_schema
                JOIN information_schema.referential_constraints rc
                  ON tc.constraint_name = rc.constraint_name
                 AND tc.constraint_schema = rc.constraint_schema
                WHERE tc.table_schema = 'public'
                  AND tc.table_name IN ('datasets', 'dataset_snapshots')
                """
            )
        ).all()
        assert all(row.delete_rule == "RESTRICT" for row in foreign_keys)
        assert {(row.table_name, row.column_name) for row in foreign_keys} >= {
            ("datasets", "project_id"),
            ("datasets", "created_by"),
            ("dataset_snapshots", "dataset_id"),
            ("dataset_snapshots", "created_by"),
        }


def test_dataset_snapshot_unique_dataset_content_constraint(engine: Engine) -> None:
    with engine.connect() as connection:
        transaction = connection.begin()
        actor_id = uuid4()
        dataset_id = uuid4()
        connection.execute(
            text(
                "INSERT INTO actors "
                "(id, actor_type, display_name, created_at, row_version) "
                "VALUES (:id, 'HUMAN', 'PR-06 unique test', now(), 1)"
            ),
            {"id": actor_id},
        )
        connection.execute(
            text(
                "INSERT INTO datasets "
                "(id, name, created_by, created_at, row_version) "
                "VALUES (:id, 'PR-06 unique test', :actor_id, now(), 1)"
            ),
            {"id": dataset_id, "actor_id": actor_id},
        )
        with pytest.raises(IntegrityError):
            connection.execute(
                text(
                    """
                    INSERT INTO dataset_snapshots
                    (id, dataset_id, manifest_hash, selection_definition, content_hash,
                     created_by, created_at)
                    VALUES
                    ('00000000-0000-0000-0000-000000000101',
                     :dataset_id,
                     repeat('a', 64), '{}', repeat('b', 64),
                     :actor_id, now()),
                    ('00000000-0000-0000-0000-000000000104',
                     :dataset_id,
                     repeat('a', 64), '{}', repeat('b', 64),
                     :actor_id, now())
                    """
                ),
                {"dataset_id": dataset_id, "actor_id": actor_id},
            )
        transaction.rollback()
