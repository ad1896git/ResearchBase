from __future__ import annotations

import logging
from datetime import UTC, datetime
from unittest.mock import patch
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

PHASE2_TABLES = {
    "project_memberships",
    "project_role_assignments",
    "project_membership_events",
    "project_role_events",
    "actor_subject_bindings",
    "actor_subject_binding_events",
    "bootstrap_records",
    "actor_enrollment_challenges",
}


def _alembic_config(database_url: str) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _upgrade(config: Config, revision: str) -> None:
    with patch.dict("os.environ", {"DATABASE_URL": config.get_main_option("sqlalchemy.url")}):
        command.upgrade(config, revision)


def _downgrade(config: Config, revision: str) -> None:
    with patch.dict("os.environ", {"DATABASE_URL": config.get_main_option("sqlalchemy.url")}):
        command.downgrade(config, revision)


def test_alembic_migration_preserves_existing_application_logger(
    phase2_database_url: str,
) -> None:
    logger = logging.getLogger("researchbase.commands")
    previous_disabled = logger.disabled
    previous_level = logger.level
    previous_handlers = tuple(logger.handlers)
    previous_propagate = logger.propagate
    logger.disabled = False
    try:
        _upgrade(_alembic_config(phase2_database_url), "0019_phase2_bootstrap_membership")
        assert logger.disabled is False
        assert logger.level == previous_level
        assert tuple(logger.handlers) == previous_handlers
        assert logger.propagate is previous_propagate
    finally:
        logger.disabled = previous_disabled


def _phase1_snapshot(connection) -> tuple[object, ...]:
    excluded = PHASE2_TABLES | {"alembic_version"}
    columns = tuple(
        row
        for row in connection.execute(
            text(
                "SELECT table_name, ordinal_position, column_name, data_type, is_nullable, "
                "column_default FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name <> ALL(:excluded) "
                "ORDER BY table_name, ordinal_position"
            ),
            {"excluded": list(excluded)},
        ).all()
        if row.table_name not in excluded
    )
    constraints = tuple(
        row
        for row in connection.execute(
            text(
                "SELECT c.conrelid::regclass::text, c.conname, pg_get_constraintdef(c.oid), "
                "c.convalidated FROM pg_constraint c JOIN pg_namespace n ON n.oid = c.connamespace "
                "WHERE n.nspname = 'public' AND c.contype <> 't' "
                "AND c.conrelid::regclass::text <> ALL(:excluded) "
                "ORDER BY 1, 2"
            ),
            {"excluded": list(excluded)},
        ).all()
        if str(row[0]).split(".")[-1].strip('"') not in excluded
    )
    indexes = tuple(
        row
        for row in connection.execute(
            text(
                "SELECT tablename, indexname, indexdef FROM pg_indexes "
                "WHERE schemaname = 'public' AND tablename <> ALL(:excluded) "
                "ORDER BY tablename, indexname"
            ),
            {"excluded": list(excluded)},
        ).all()
        if row.tablename not in excluded
    )
    table_names = connection.execute(
        text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' "
            "AND table_name <> ALL(:excluded) ORDER BY table_name"
        ),
        {"excluded": list(excluded)},
    ).scalars()
    row_digests: list[tuple[str, int, str | None]] = []
    preparer = connection.dialect.identifier_preparer
    for table_name in table_names:
        if table_name in excluded:
            continue
        quoted_table = preparer.quote(table_name)
        row_count, digest = connection.execute(
            text(
                "SELECT count(*), md5(coalesce(string_agg(row_to_json(t)::text, "
                "E'\\n' ORDER BY row_to_json(t)::text), '')) "
                f"FROM {quoted_table} AS t"
            )
        ).one()
        row_digests.append((table_name, row_count, digest))
    return columns, constraints, indexes, tuple(row_digests)


def test_eight_table_catalog_and_phase1_non_drift(phase2_database_url: str) -> None:
    database_url = phase2_database_url
    engine = create_engine(database_url)
    config = _alembic_config(database_url)
    try:
        _upgrade(config, "0018_current_pointer_same_parent_integrity")
        actor_id, project_id = uuid4(), uuid4()
        now = datetime.now(UTC)
        with engine.connect() as connection:
            with connection.begin():
                connection.execute(
                    text(
                        "INSERT INTO actors (id, actor_type, display_name, created_at) "
                        "VALUES (:id, 'HUMAN', 'Frozen baseline actor', :now)"
                    ),
                    {"id": actor_id, "now": now},
                )
                connection.execute(
                    text(
                        "INSERT INTO projects (id, name, created_by, created_at) "
                        "VALUES (:id, 'Frozen baseline project', :actor, :now)"
                    ),
                    {"id": project_id, "actor": actor_id, "now": now},
                )
            before_phase1 = _phase1_snapshot(connection)
            before = set(
                connection.execute(
                    text(
                        "SELECT table_name FROM information_schema.tables "
                        "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
                    )
                ).scalars()
            )

        _upgrade(config, "0019_phase2_bootstrap_membership")

        with engine.connect() as connection:
            after_phase1 = _phase1_snapshot(connection)
            after = set(
                connection.execute(
                    text(
                        "SELECT table_name FROM information_schema.tables "
                        "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
                    )
                ).scalars()
            )
            assert after - before == PHASE2_TABLES
            assert after_phase1 == before_phase1
            assert connection.execute(
                text(
                    "SELECT EXISTS (SELECT 1 FROM pg_trigger "
                    "WHERE tgname = 'trg_actors_owner_coverage' AND NOT tgisinternal)"
                )
            ).scalar_one()
            assert (
                connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                == "0019_phase2_bootstrap_membership"
            )
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    ("violation", "expected_code"),
    [
        ("orphan_creator", "PROJECT_CREATOR_ORPHAN"),
        ("duplicate_external_key", "DUPLICATE_ACTOR_EXTERNAL_KEY"),
        ("actor_type", "INVALID_ACTOR_TYPE"),
        ("project_lifecycle", "INVALID_PROJECT_LIFECYCLE"),
    ],
)
def test_legacy_state_preflight_fails_before_phase2_ddl_and_is_deterministic(
    phase2_database_url: str, violation: str, expected_code: str
) -> None:
    database_url = phase2_database_url
    engine = create_engine(database_url)
    config = _alembic_config(database_url)
    actor_id, project_id = uuid4(), uuid4()
    now = datetime.now(UTC)
    try:
        _upgrade(config, "0018_current_pointer_same_parent_integrity")
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO actors (id, actor_type, display_name, created_at) "
                    "VALUES (:id, 'HUMAN', 'preflight actor', :now)"
                ),
                {"id": actor_id, "now": now},
            )
            connection.execute(
                text(
                    "INSERT INTO projects (id, name, created_by, created_at) "
                    "VALUES (:id, 'preflight project', :actor, :now)"
                ),
                {"id": project_id, "actor": actor_id, "now": now},
            )
            if violation == "orphan_creator":
                connection.execute(
                    text("ALTER TABLE projects DROP CONSTRAINT projects_created_by_fkey")
                )
                connection.execute(
                    text("UPDATE projects SET created_by = :missing WHERE id = :id"),
                    {"missing": uuid4(), "id": project_id},
                )
            elif violation == "duplicate_external_key":
                connection.execute(text("DROP INDEX uq_actors_external_key"))
                connection.execute(
                    text("UPDATE actors SET external_key = 'duplicate-key' WHERE id = :id"),
                    {"id": actor_id},
                )
                connection.execute(
                    text(
                        "INSERT INTO actors (id, actor_type, display_name, "
                        "external_key, created_at) "
                        "VALUES (:id, 'HUMAN', 'duplicate actor', 'duplicate-key', :now)"
                    ),
                    {"id": uuid4(), "now": now},
                )
            elif violation == "actor_type":
                connection.execute(text("ALTER TABLE actors DROP CONSTRAINT ck_actors_actor_type"))
                connection.execute(
                    text("UPDATE actors SET actor_type = 'UNKNOWN' WHERE id = :id"),
                    {"id": actor_id},
                )
            else:
                connection.execute(
                    text("ALTER TABLE projects DROP CONSTRAINT ck_projects_lifecycle_status")
                )
                connection.execute(
                    text("UPDATE projects SET lifecycle_status = 'unknown' WHERE id = :id"),
                    {"id": project_id},
                )

        errors: list[str] = []
        for _ in range(2):
            with pytest.raises(Exception, match="LEGACY_STATE_INVALID") as raised:
                _upgrade(config, "0019_phase2_bootstrap_membership")
            errors.append(str(raised.value))
        assert errors[0] == errors[1]
        assert expected_code in errors[0]
        with engine.connect() as connection:
            assert connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one() == ("0018_current_pointer_same_parent_integrity")
            tables = set(
                connection.execute(
                    text(
                        "SELECT table_name FROM information_schema.tables "
                        "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
                    )
                ).scalars()
            )
            assert not (tables & PHASE2_TABLES)
            assert connection.execute(text("SELECT count(*) FROM actors")).scalar_one() == (
                2 if violation == "duplicate_external_key" else 1
            )
            assert connection.execute(text("SELECT count(*) FROM projects")).scalar_one() == 1
    finally:
        engine.dispose()


def test_empty_downgrade_removes_all_phase2_tables(phase2_database_url: str) -> None:
    engine = create_engine(phase2_database_url)
    config = _alembic_config(phase2_database_url)
    try:
        _upgrade(config, "0019_phase2_bootstrap_membership")
        _downgrade(config, "0018_current_pointer_same_parent_integrity")
        with engine.connect() as connection:
            remaining = set(
                connection.execute(
                    text(
                        "SELECT table_name FROM information_schema.tables "
                        "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
                    )
                ).scalars()
            )
            assert not (remaining & PHASE2_TABLES)
            assert (
                connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                == "0018_current_pointer_same_parent_integrity"
            )
    finally:
        engine.dispose()


def test_populated_downgrade_refuses_without_losing_rows(phase2_database_url: str) -> None:
    engine = create_engine(phase2_database_url)
    config = _alembic_config(phase2_database_url)
    actor_id, project_id, membership_id, request_id = (uuid4() for _ in range(4))
    now = datetime.now(UTC)
    try:
        _upgrade(config, "0019_phase2_bootstrap_membership")
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO actors (id, actor_type, display_name, created_at) "
                    "VALUES (:id, 'HUMAN', 'Migration test', :now)"
                ),
                {"id": actor_id, "now": now},
            )
            connection.execute(
                text(
                    "INSERT INTO projects (id, name, created_by, created_at) "
                    "VALUES (:id, 'Migration test', :actor, :now)"
                ),
                {"id": project_id, "actor": actor_id, "now": now},
            )
            connection.execute(
                text(
                    "INSERT INTO project_memberships "
                    "(id, project_id, actor_id, status, started_at, created_by, created_at, "
                    "row_version) "
                    "VALUES (:id, :project, :actor, 'ACTIVE', :now, :actor, :now, 1)"
                ),
                {"id": membership_id, "project": project_id, "actor": actor_id, "now": now},
            )
            connection.execute(
                text(
                    "INSERT INTO project_membership_events "
                    "(id, membership_id, event_kind, prior_status, new_status, actor_id, "
                    "occurred_at, reason, request_id) "
                    "VALUES (:id, :membership, 'ACTIVATED', NULL, 'ACTIVE', :actor, :now, "
                    "'legacy row', :request)"
                ),
                {
                    "id": uuid4(),
                    "membership": membership_id,
                    "actor": actor_id,
                    "now": now,
                    "request": request_id,
                },
            )

        with pytest.raises(RuntimeError, match="canonical rows would be lost"):
            _downgrade(config, "0018_current_pointer_same_parent_integrity")

        with engine.connect() as connection:
            assert (
                connection.execute(
                    text("SELECT count(*) FROM project_memberships WHERE id = :id"),
                    {"id": membership_id},
                ).scalar_one()
                == 1
            )
            assert (
                connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                == "0019_phase2_bootstrap_membership"
            )
    finally:
        engine.dispose()
