from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from tests.contracts.pr17dr_manifest import PR17D_FUNCTIONS, PR17D_TRIGGERS

pytestmark = pytest.mark.integration


@contextmanager
def _temporary_database(base_url: str) -> Iterator[tuple[str, Engine]]:
    base = make_url(base_url)
    database = f"researchbase_pr17dr_{uuid4().hex[:12]}"
    admin = create_engine(base.set(database="postgres"), isolation_level="AUTOCOMMIT")
    target = base.set(database=database)
    try:
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{database}"'))
        database_engine = create_engine(target)
        try:
            yield target.render_as_string(hide_password=False), database_engine
        finally:
            database_engine.dispose()
    finally:
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{database}" WITH (FORCE)'))
        admin.dispose()


def _run_alembic(
    database_url: str, *arguments: str, pgoptions: str | None = None
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = database_url
    environment.setdefault("UV_CACHE_DIR", "/tmp/researchbase-uv-cache")
    if pgoptions is not None:
        environment["PGOPTIONS"] = pgoptions
    return subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def _assert_alembic_ok(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, f"Alembic failed:\n{result.stdout}\n{result.stderr}"


def _catalog(engine: Engine) -> tuple[set[str], set[str], set[str], str]:
    with engine.connect() as connection:
        functions = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT p.proname FROM pg_proc AS p "
                    "JOIN pg_namespace AS n ON n.oid = p.pronamespace "
                    "WHERE n.nspname='public' AND left(p.proname, 6)='pr17d_'"
                )
            )
        }
        triggers = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT t.tgname FROM pg_trigger AS t "
                    "JOIN pg_class AS c ON c.oid=t.tgrelid "
                    "JOIN pg_namespace AS n ON n.oid=c.relnamespace "
                    "WHERE n.nspname='public' AND NOT t.tgisinternal "
                    "AND left(t.tgname, 6)='pr17d_'"
                )
            )
        }
        constraints = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT c.conname FROM pg_constraint AS c "
                    "JOIN pg_namespace AS n ON n.oid=c.connamespace "
                    "WHERE n.nspname='public' AND left(c.conname, 6)='pr17d_'"
                )
            )
        }
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    return functions, triggers, constraints, revision


def _assert_0016_catalog(engine: Engine) -> None:
    functions, triggers, constraints, revision = _catalog(engine)
    assert functions == set(PR17D_FUNCTIONS)
    assert triggers == {name for name, _table, _event, _function in PR17D_TRIGGERS}
    assert constraints == set()
    assert revision == "0016_pr17d_history_protection"


def _assert_0015_empty_catalog(engine: Engine) -> None:
    functions, triggers, constraints, revision = _catalog(engine)
    assert functions == set()
    assert triggers == set()
    assert constraints == set()
    assert revision == "0015_governance_audit"


def _seed_conforming_0015(engine: Engine) -> None:
    actor_id, project_id = (uuid4() for _ in range(2))
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO actors(id, actor_type, display_name, created_at) "
                "VALUES (:id, 'human', 'migration actor', now())"
            ),
            {"id": actor_id},
        )
        connection.execute(
            text(
                "INSERT INTO projects(id, name, created_by, created_at) "
                "VALUES (:id, 'migration project', :actor, now())"
            ),
            {"id": project_id, "actor": actor_id},
        )


def _seed_nonconforming_0015(engine: Engine) -> tuple[UUID, int]:
    actor_id, project_id, spec_id, spec_version_id, run_id = (uuid4() for _ in range(5))
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO actors(id, actor_type, display_name, created_at) "
                "VALUES (:id, 'human', 'bad migration actor', now())"
            ),
            {"id": actor_id},
        )
        connection.execute(
            text(
                "INSERT INTO projects(id, name, created_by, created_at) "
                "VALUES (:id, 'bad migration project', :actor, now())"
            ),
            {"id": project_id, "actor": actor_id},
        )
        connection.execute(
            text(
                "INSERT INTO experiment_specs(id, project_id, created_by, created_at) "
                "VALUES (:id, :project, :actor, now())"
            ),
            {"id": spec_id, "project": project_id, "actor": actor_id},
        )
        connection.execute(
            text(
                "INSERT INTO experiment_spec_versions "
                "(id, experiment_spec_id, version_number, status, title, objective, protocol, "
                "created_by, created_at) VALUES (:id, :spec, 1, 'DRAFT', 'title', 'objective', "
                "'{}'::jsonb, :actor, now())"
            ),
            {"id": spec_version_id, "spec": spec_id, "actor": actor_id},
        )
        connection.execute(
            text(
                "INSERT INTO runs "
                "(id, project_id, experiment_spec_version_id, run_type, status, "
                "created_by, created_at) "
                "VALUES (:id, :project, :spec, '', 'PLANNED', :actor, now())"
            ),
            {"id": run_id, "project": project_id, "spec": spec_version_id, "actor": actor_id},
        )
        count = connection.execute(text("SELECT count(*) FROM runs")).scalar_one()
    return run_id, count


def test_fresh_install_reaches_0016_with_exact_catalog() -> None:
    base_url = os.getenv("DATABASE_URL")
    if not base_url:
        pytest.skip("DATABASE_URL is not set; run against PostgreSQL 18")
    with _temporary_database(base_url) as (database_url, engine):
        _assert_alembic_ok(_run_alembic(database_url, "upgrade", "head"))
        _assert_0016_catalog(engine)


def test_populated_0015_upgrade_preserves_rows_and_installs_catalog() -> None:
    base_url = os.getenv("DATABASE_URL")
    if not base_url:
        pytest.skip("DATABASE_URL is not set; run against PostgreSQL 18")
    with _temporary_database(base_url) as (database_url, engine):
        _assert_alembic_ok(_run_alembic(database_url, "upgrade", "0015_governance_audit"))
        _seed_conforming_0015(engine)
        with engine.connect() as connection:
            before = connection.execute(text("SELECT count(*) FROM projects")).scalar_one()
        _assert_alembic_ok(_run_alembic(database_url, "upgrade", "0016_pr17d_history_protection"))
        with engine.connect() as connection:
            after = connection.execute(text("SELECT count(*) FROM projects")).scalar_one()
        assert after == before
        _assert_0016_catalog(engine)


def test_0016_targets_public_with_a_restricted_search_path() -> None:
    base_url = os.getenv("DATABASE_URL")
    if not base_url:
        pytest.skip("DATABASE_URL is not set; run against PostgreSQL 18")
    with _temporary_database(base_url) as (database_url, engine):
        _assert_alembic_ok(_run_alembic(database_url, "upgrade", "0015_governance_audit"))
        _assert_alembic_ok(
            _run_alembic(
                database_url,
                "upgrade",
                "0016_pr17d_history_protection",
                pgoptions="-csearch_path=pg_catalog,public",
            )
        )
        _assert_0016_catalog(engine)


def test_downgrade_removes_all_pr17d_owned_objects() -> None:
    base_url = os.getenv("DATABASE_URL")
    if not base_url:
        pytest.skip("DATABASE_URL is not set; run against PostgreSQL 18")
    with _temporary_database(base_url) as (database_url, engine):
        _assert_alembic_ok(_run_alembic(database_url, "upgrade", "head"))
        _assert_alembic_ok(_run_alembic(database_url, "downgrade", "0015_governance_audit"))
        _assert_0015_empty_catalog(engine)


def test_upgrade_downgrade_upgrade_has_same_semantic_catalog() -> None:
    base_url = os.getenv("DATABASE_URL")
    if not base_url:
        pytest.skip("DATABASE_URL is not set; run against PostgreSQL 18")
    with _temporary_database(base_url) as (database_url, engine):
        _assert_alembic_ok(_run_alembic(database_url, "upgrade", "head"))
        first = _catalog(engine)[:3]
        _assert_alembic_ok(_run_alembic(database_url, "downgrade", "0015_governance_audit"))
        _assert_alembic_ok(_run_alembic(database_url, "upgrade", "head"))
        assert _catalog(engine)[:3] == first
        _assert_0016_catalog(engine)


def test_preflight_failure_rolls_back_revision_objects_and_preserves_rows() -> None:
    base_url = os.getenv("DATABASE_URL")
    if not base_url:
        pytest.skip("DATABASE_URL is not set; run against PostgreSQL 18")
    with _temporary_database(base_url) as (database_url, engine):
        _assert_alembic_ok(_run_alembic(database_url, "upgrade", "0015_governance_audit"))
        run_id, before_count = _seed_nonconforming_0015(engine)
        failed = _run_alembic(database_url, "upgrade", "0016_pr17d_history_protection")
        assert failed.returncode != 0
        _assert_0015_empty_catalog(engine)
        with engine.connect() as connection:
            assert (
                connection.execute(text("SELECT count(*) FROM runs")).scalar_one() == before_count
            )
            assert (
                connection.execute(
                    text("SELECT run_type FROM runs WHERE id=:id"), {"id": run_id}
                ).scalar_one()
                == ""
            )
