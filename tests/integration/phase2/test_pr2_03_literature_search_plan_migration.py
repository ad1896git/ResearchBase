from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

TABLES = {
    "literature_search_plans",
    "literature_search_plan_versions",
    "search_plan_question_inputs",
    "literature_search_plan_command_receipts",
}


def _upgrade(database_url: str, revision: str = "head") -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    with patch.dict("os.environ", {"DATABASE_URL": database_url}):
        command.upgrade(config, revision)


def test_pr2_03_fresh_install_adds_exact_four_tables_and_unique_head(
    phase2_database_url: str,
) -> None:
    _upgrade(phase2_database_url)
    engine = create_engine(phase2_database_url)
    with engine.connect() as connection:
        tables = set(
            connection.execute(
                text(
                    "SELECT tablename FROM pg_tables WHERE schemaname='public' "
                    "AND tablename = ANY(:names)"
                ),
                {"names": sorted(TABLES)},
            ).scalars()
        )
        assert tables == TABLES
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0049_b05_manuscript_review"
        )
        assert (
            connection.execute(
                text(
                    "SELECT count(*) FROM pg_trigger "
                    "WHERE NOT tgisinternal AND tgname LIKE 'trg_lsp%'"
                )
            ).scalar_one()
            >= 3
        )
    engine.dispose()


def test_pr2_03_upgrade_from_0022_and_empty_downgrade(phase2_database_url: str) -> None:
    _upgrade(phase2_database_url, "0022_source_version_and_merge_lineage")
    _upgrade(phase2_database_url, "head")
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    with patch.dict("os.environ", {"DATABASE_URL": phase2_database_url}):
        command.downgrade(config, "0022_source_version_and_merge_lineage")
        command.upgrade(config, "0023_literature_search_plan")


def test_pr2_03_populated_downgrade_refuses_before_dropping_tables(
    phase2_database_url: str,
) -> None:
    _upgrade(phase2_database_url)
    engine = create_engine(phase2_database_url)
    actor_id, project_id, plan_id = uuid4(), uuid4(), uuid4()
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO actors(id,actor_type,display_name,created_at) "
                "VALUES (:id,'HUMAN','test',clock_timestamp())"
            ),
            {"id": actor_id},
        )
        connection.execute(
            text(
                "INSERT INTO projects(id,name,created_by,created_at) "
                "VALUES (:id,'test',:actor,clock_timestamp())"
            ),
            {"id": project_id, "actor": actor_id},
        )
        connection.execute(
            text(
                "INSERT INTO literature_search_plans(id,project_id,created_by,created_at) "
                "VALUES (:id,:project,:actor,clock_timestamp())"
            ),
            {"id": plan_id, "project": project_id, "actor": actor_id},
        )
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    with patch.dict("os.environ", {"DATABASE_URL": phase2_database_url}):
        with pytest.raises(DBAPIError, match="downgrade refused"):
            command.downgrade(config, "0022_source_version_and_merge_lineage")
    with engine.connect() as connection:
        assert (
            connection.execute(text("SELECT count(*) FROM literature_search_plans")).scalar_one()
            == 1
        )
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0049_b05_manuscript_review"
        )
    engine.dispose()
