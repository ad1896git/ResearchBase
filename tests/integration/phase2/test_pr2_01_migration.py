from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

SOURCE_TABLES = {
    "literature_sources",
    "source_identifiers",
    "source_identifier_verification_events",
    "literature_source_project_links",
    "literature_command_receipts",
}


def _upgrade(database_url: str, revision: str = "head") -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    with patch.dict("os.environ", {"DATABASE_URL": database_url}):
        command.upgrade(config, revision)


def test_pr2_01_fresh_install_adds_exact_five_tables(phase2_database_url: str) -> None:
    _upgrade(phase2_database_url)
    engine = create_engine(phase2_database_url)
    with engine.connect() as connection:
        tables = set(
            connection.execute(
                text(
                    "SELECT tablename FROM pg_tables WHERE schemaname='public' "
                    "AND tablename = ANY(:names)"
                ),
                {"names": sorted(SOURCE_TABLES)},
            ).scalars()
        )
        assert tables == SOURCE_TABLES
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0021a_source_merge_gov_guards"
        )
        assert (
            connection.execute(text("SELECT version() ")).scalar_one().startswith("PostgreSQL 18.")
        )
    engine.dispose()


def test_pr2_01_schema_has_five_owned_tables_and_no_phase1_alters(
    phase2_database_url: str,
) -> None:
    _upgrade(phase2_database_url, "0019_phase2_bootstrap_membership")
    engine = create_engine(phase2_database_url)
    with engine.connect() as connection:
        before = _phase1_catalog(connection)
    _upgrade(phase2_database_url, "0020_literature_source_identity")
    with engine.connect() as connection:
        after = _phase1_catalog(connection)
        created = set(
            connection.execute(
                text(
                    "SELECT tablename FROM pg_tables WHERE schemaname='public' "
                    "AND tablename = ANY(:names)"
                ),
                {"names": sorted(SOURCE_TABLES)},
            ).scalars()
        )
        assert created == SOURCE_TABLES
        assert after == before
        assert connection.execute(text("SELECT count(*) FROM literature_sources")).scalar_one() == 0
    engine.dispose()


def test_populated_0020_downgrade_refuses_without_removing_identity(
    phase2_database_url: str,
) -> None:
    _upgrade(phase2_database_url)
    engine = create_engine(phase2_database_url)
    actor_id = uuid4()
    source_id = uuid4()
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
                "INSERT INTO literature_sources("
                "id,source_kind,canonical_title,lifecycle_status,created_by,created_at) "
                "VALUES (:id,'PAPER','Test source','ACTIVE',:actor,clock_timestamp())"
            ),
            {"id": source_id, "actor": actor_id},
        )
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    with patch.dict("os.environ", {"DATABASE_URL": phase2_database_url}):
        with pytest.raises(RuntimeError, match="LITERATURE_SOURCE_DATA_PRESERVATION_REQUIRED"):
            command.downgrade(config, "0019_phase2_bootstrap_membership")
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM literature_sources WHERE id=:id"), {"id": source_id}
            ).scalar_one()
            == 1
        )
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0021a_source_merge_gov_guards"
        )
    engine.dispose()


def test_live_identifier_uniqueness_and_source_immutability_are_database_enforced(
    phase2_database_url: str,
) -> None:
    _upgrade(phase2_database_url)
    engine = create_engine(phase2_database_url)
    actor_id = uuid4()
    source_ids = [uuid4(), uuid4()]
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO actors(id,actor_type,display_name,created_at) "
                "VALUES (:id,'HUMAN','test',clock_timestamp())"
            ),
            {"id": actor_id},
        )
        for source_id in source_ids:
            connection.execute(
                text(
                    "INSERT INTO literature_sources(id,source_kind,canonical_title,"
                    "lifecycle_status,created_by,created_at) "
                    "VALUES (:id,'PAPER','Test source','ACTIVE',:actor,clock_timestamp())"
                ),
                {"id": source_id, "actor": actor_id},
            )
        connection.execute(
            text(
                "INSERT INTO source_identifiers(id,literature_source_id,identifier_type,"
                "identifier_value,normalized_value,normalization_version,is_primary,"
                "verification_status,created_by,created_at) VALUES "
                "(:id,:source,'DOI','10.1234/test','10.1234/test',"
                "'source-identifier-normalization-v1',false,'UNVERIFIED',:actor,clock_timestamp())"
            ),
            {"id": uuid4(), "source": source_ids[0], "actor": actor_id},
        )
    with pytest.raises(DBAPIError) as duplicate:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO source_identifiers(id,literature_source_id,identifier_type,"
                    "identifier_value,normalized_value,normalization_version,is_primary,"
                    "verification_status,created_by,created_at) VALUES "
                    "(:id,:source,'DOI','10.1234/test','10.1234/test',"
                    "'source-identifier-normalization-v1',false,'UNVERIFIED',:actor,clock_timestamp())"
                ),
                {"id": uuid4(), "source": source_ids[1], "actor": actor_id},
            )
    assert getattr(duplicate.value.orig, "sqlstate", None) == "23505"
    with pytest.raises(DBAPIError) as immutable:
        with engine.begin() as connection:
            connection.execute(
                text("UPDATE literature_sources SET canonical_title='Changed' WHERE id=:id"),
                {"id": source_ids[0]},
            )
    assert getattr(immutable.value.orig, "sqlstate", None) == "P17D1"
    engine.dispose()


def _phase1_catalog(connection) -> tuple[object, ...]:
    exclusions = sorted(SOURCE_TABLES | {"alembic_version"})
    columns = tuple(
        connection.execute(
            text(
                "SELECT table_name,ordinal_position,column_name,data_type,is_nullable,"
                "column_default "
                "FROM information_schema.columns WHERE table_schema='public' "
                "AND table_name <> ALL(:excluded) ORDER BY table_name,ordinal_position"
            ),
            {"excluded": exclusions},
        ).all()
    )
    constraints = tuple(
        connection.execute(
            text(
                "SELECT c.conrelid::regclass::text,c.conname,pg_get_constraintdef(c.oid),"
                "c.convalidated "
                "FROM pg_constraint c JOIN pg_namespace n ON n.oid=c.connamespace "
                "WHERE n.nspname='public' AND c.conrelid::regclass::text <> ALL(:excluded) "
                "ORDER BY 1,2"
            ),
            {"excluded": exclusions},
        ).all()
    )
    indexes = tuple(
        connection.execute(
            text(
                "SELECT tablename,indexname,indexdef FROM pg_indexes "
                "WHERE schemaname='public' AND tablename <> ALL(:excluded) ORDER BY 1,2"
            ),
            {"excluded": exclusions},
        ).all()
    )
    triggers = tuple(
        connection.execute(
            text(
                "SELECT event_object_table,trigger_name,action_timing,event_manipulation,"
                "action_statement "
                "FROM information_schema.triggers WHERE trigger_schema='public' "
                "AND event_object_table <> ALL(:excluded) ORDER BY 1,2,4"
            ),
            {"excluded": exclusions},
        ).all()
    )
    return columns, constraints, indexes, triggers
