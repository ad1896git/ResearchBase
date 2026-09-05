from __future__ import annotations

import os
from collections.abc import Iterator
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError, IntegrityError

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


def test_pr07_schema_columns_constraints_and_restrict_foreign_keys(engine: Engine) -> None:
    with engine.connect() as connection:
        assert {
            connection.execute(
                text("SELECT to_regclass(:name)"), {"name": f"public.{table}"}
            ).scalar_one()
            for table in ("artifacts", "artifact_versions")
        } == {"artifacts", "artifact_versions"}
        rows = connection.execute(
            text(
                """
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name IN ('artifacts', 'artifact_versions')
                """
            )
        ).all()
        columns: dict[str, set[str]] = {}
        for row in rows:
            columns.setdefault(row.table_name, set()).add(row.column_name)
        assert columns["artifacts"] == {
            "id",
            "project_id",
            "artifact_type",
            "name",
            "description",
            "current_version_id",
            "created_by",
            "created_at",
            "row_version",
        }
        assert columns["artifact_versions"] == {
            "id",
            "artifact_id",
            "version_number",
            "status",
            "locator",
            "media_type",
            "byte_size",
            "content_hash",
            "metadata",
            "created_by",
            "created_at",
            "frozen_at",
            "row_version",
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
                  AND tc.table_name IN ('artifacts', 'artifact_versions')
                """
            )
        ).all()
        assert all(row.delete_rule == "RESTRICT" for row in foreign_keys)
        assert {(row.table_name, row.column_name) for row in foreign_keys} >= {
            ("artifacts", "project_id"),
            ("artifacts", "created_by"),
            ("artifacts", "current_version_id"),
            ("artifact_versions", "artifact_id"),
            ("artifact_versions", "created_by"),
        }


def test_pr07_schema_has_version_uniques_and_status_checks(engine: Engine) -> None:
    with engine.connect() as connection:
        unique_columns = connection.execute(
            text(
                """
                SELECT tc.constraint_name, kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.table_schema = kcu.table_schema
                WHERE tc.table_schema = 'public'
                  AND tc.table_name = 'artifact_versions'
                  AND tc.constraint_type = 'UNIQUE'
                """
            )
        ).all()
        grouped: dict[str, set[str]] = {}
        for row in unique_columns:
            grouped.setdefault(row.constraint_name, set()).add(row.column_name)
        assert {frozenset(values) for values in grouped.values()} >= {
            frozenset({"artifact_id", "version_number"}),
            frozenset({"artifact_id", "content_hash"}),
        }
        checks = {
            row.check_clause
            for row in connection.execute(
                text(
                    """
                    SELECT cc.check_clause
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.check_constraints cc
                      ON tc.constraint_name = cc.constraint_name
                     AND tc.constraint_schema = cc.constraint_schema
                    WHERE tc.table_schema = 'public'
                      AND tc.table_name = 'artifact_versions'
                    """
                )
            )
        }
        assert any("version_number" in value and "> 0" in value for value in checks)
        assert any("byte_size" in value and ">= 0" in value for value in checks)
        assert any("status" in value and "DRAFT" in value for value in checks)


def test_pr07_restrict_foreign_keys_block_referenced_deletes(engine: Engine) -> None:
    with engine.begin() as connection:
        actor_id = uuid4()
        project_id = uuid4()
        artifact_id = uuid4()
        version_id = uuid4()
        connection.execute(
            text(
                "INSERT INTO actors (id, actor_type, display_name, created_at, row_version) "
                "VALUES (:id, 'human', 'PR-07 schema actor', now(), 1)"
            ),
            {"id": actor_id},
        )
        connection.execute(
            text(
                "INSERT INTO projects (id, name, created_by, created_at, row_version) "
                "VALUES (:id, 'PR-07 schema project', :actor_id, now(), 1)"
            ),
            {"id": project_id, "actor_id": actor_id},
        )
        connection.execute(
            text(
                "INSERT INTO artifacts (id, project_id, artifact_type, name, created_by, "
                "created_at, row_version) VALUES (:id, :project_id, 'text', 'schema artifact', "
                ":actor_id, now(), 1)"
            ),
            {"id": artifact_id, "project_id": project_id, "actor_id": actor_id},
        )
        connection.execute(
            text(
                "INSERT INTO artifact_versions (id, artifact_id, version_number, status, "
                "content_hash, created_by, created_at, row_version) VALUES "
                "(:id, :artifact_id, 1, 'DRAFT', repeat('a', 64), :actor_id, now(), 1)"
            ),
            {"id": version_id, "artifact_id": artifact_id, "actor_id": actor_id},
        )
        connection.execute(
            text("UPDATE artifacts SET current_version_id = :version_id WHERE id = :id"),
            {"version_id": version_id, "id": artifact_id},
        )
    with engine.connect() as connection:
        transaction = connection.begin()
        with pytest.raises(IntegrityError):
            connection.execute(text("DELETE FROM artifacts WHERE id = :id"), {"id": artifact_id})
        transaction.rollback()
    with engine.connect() as connection:
        transaction = connection.begin()
        with pytest.raises(IntegrityError):
            connection.execute(text("DELETE FROM actors WHERE id = :id"), {"id": actor_id})
        transaction.rollback()
    with engine.connect() as connection:
        transaction = connection.begin()
        connection.execute(
            text("UPDATE artifacts SET current_version_id = NULL WHERE id = :id"),
            {"id": artifact_id},
        )
        with pytest.raises(DBAPIError):
            connection.execute(
                text("DELETE FROM artifact_versions WHERE id = :id"), {"id": version_id}
            )
        transaction.rollback()
