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
    value = create_database_engine()
    try:
        yield value
    finally:
        value.dispose()


def test_pr04_tables_columns_and_constraints_exist(engine: Engine) -> None:
    expected_tables = {
        "research_questions",
        "research_question_versions",
        "hypotheses",
        "hypothesis_versions",
    }
    with engine.connect() as connection:
        tables = {
            connection.execute(
                text("SELECT to_regclass(:name)"), {"name": f"public.{name}"}
            ).scalar_one()
            for name in expected_tables
        }
        assert tables == expected_tables
        actual_columns = connection.execute(
            text(
                """
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name IN ('research_questions', 'research_question_versions',
                                     'hypotheses', 'hypothesis_versions')
                """
            )
        ).all()
        grouped: dict[str, set[str]] = {}
        for row in actual_columns:
            grouped.setdefault(row.table_name, set()).add(row.column_name)
        assert {
            "id",
            "project_id",
            "current_version_id",
            "created_by",
            "created_at",
            "row_version",
        } <= grouped["research_questions"]
        assert {
            "id",
            "research_question_id",
            "version_number",
            "status",
            "question_text",
            "scope",
            "rationale",
            "content_hash",
            "created_by",
            "created_at",
            "frozen_at",
            "row_version",
        } == grouped["research_question_versions"]
        assert {
            "id",
            "project_id",
            "research_question_id",
            "current_version_id",
            "created_by",
            "created_at",
            "row_version",
        } == grouped["hypotheses"]
        assert {
            "id",
            "hypothesis_id",
            "version_number",
            "status",
            "statement",
            "expected_direction",
            "success_criteria",
            "rationale",
            "content_hash",
            "created_by",
            "created_at",
            "frozen_at",
            "row_version",
        } == grouped["hypothesis_versions"]

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
                  AND tc.table_name IN ('research_questions', 'research_question_versions',
                                        'hypotheses', 'hypothesis_versions')
                """
            )
        ).all()
        assert all(row.delete_rule == "RESTRICT" for row in foreign_keys)
        assert {(row.table_name, row.column_name) for row in foreign_keys} >= {
            ("research_questions", "project_id"),
            ("research_questions", "created_by"),
            ("research_questions", "current_version_id"),
            ("research_question_versions", "research_question_id"),
            ("research_question_versions", "created_by"),
            ("hypotheses", "project_id"),
            ("hypotheses", "research_question_id"),
            ("hypotheses", "created_by"),
            ("hypotheses", "current_version_id"),
            ("hypothesis_versions", "hypothesis_id"),
            ("hypothesis_versions", "created_by"),
        }
