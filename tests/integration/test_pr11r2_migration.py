# Historical schema fixtures preserve literal SQL for migration-boundary review.

from __future__ import annotations

import os
import subprocess
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError

from researchbase.domain.organization import ProjectId
from researchbase.foundation.execution_context import ExecutionContext
from researchbase.persistence.database import create_database_engine
from tests.integration.phase2.conftest import phase2_database_url as phase2_database_url

pytestmark = pytest.mark.integration

REPOSITORY_ROOT = Path(__file__).parents[2]
PREVIOUS_HEAD = "0012_statistical_result_input_guard"
PR11_FINAL_HEAD = "0013_statistical_result_legacy_input_precheck"


def _migration_db_url() -> str:
    value = os.getenv("PR11R2_MIGRATION_DB_URL")
    assert value is not None
    return value


def _repository_head() -> str:
    config = Config(str(REPOSITORY_ROOT / "alembic.ini"))
    head = ScriptDirectory.from_config(config).get_current_head()
    assert head is not None
    return head


@pytest.fixture(autouse=True)
def restore_migration_database_to_repository_head(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> Iterator[None]:
    # Use a fresh, owned DB for each destructive historical migration matrix.
    database_url = request.getfixturevalue("phase2_database_url")
    assert isinstance(database_url, str)
    monkeypatch.setenv("PR11R2_MIGRATION_DB_URL", database_url)
    yield
    head = _repository_head()
    restored = _alembic("upgrade", head)
    assert restored.returncode == 0, restored.stdout + restored.stderr
    current = _alembic("current")
    assert current.returncode == 0, current.stdout + current.stderr
    assert head in current.stdout


def _alembic(*arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = _migration_db_url()
    environment["UV_CACHE_DIR"] = str(REPOSITORY_ROOT / ".uv-cache")
    return subprocess.run(
        ["uv", "run", "alembic", *arguments],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )


def _reset_to_previous_head() -> Engine:
    database_url = _migration_db_url()
    downgrade = _alembic("downgrade", "base")
    assert downgrade.returncode == 0, downgrade.stdout + downgrade.stderr
    upgrade = _alembic("upgrade", PREVIOUS_HEAD)
    assert upgrade.returncode == 0, upgrade.stdout + upgrade.stderr
    return create_database_engine(database_url)


def _seed_historical_project(engine: Engine, label: str):
    actor_id, project_id = uuid4(), uuid4()
    created_at = datetime(2026, 8, 29, tzinfo=UTC)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO actors(id,actor_type,display_name,created_at) "
                "VALUES (:id,'human',:name,:at)"
            ),
            {"id": actor_id, "name": f"{label}-actor", "at": created_at},
        )
        connection.execute(
            text(
                "INSERT INTO projects(id,name,lifecycle_status,created_by,created_at) "
                "VALUES (:id,:name,'active',:actor,:at)"
            ),
            {
                "id": project_id,
                "name": f"{label}-project",
                "actor": actor_id,
                "at": created_at,
            },
        )
    return (
        actor_id,
        ProjectId(project_id),
        ExecutionContext(actor_id=actor_id, request_id=uuid4(), client_type="test"),
    )


def _seed_historical_measurement(engine: Engine, project_id: UUID, actor_id: UUID) -> UUID:
    metric, metric_version = uuid4(), uuid4()
    spec, spec_version = uuid4(), uuid4()
    run, measurement = uuid4(), uuid4()
    at = datetime(2026, 8, 29, tzinfo=UTC)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO "
                "metric_definitions(id,project_id,name,current_version_id,created_by,created_at) "
                "VALUES (:id,:project,'historical metric',NULL,:actor,:at)"
            ),
            {"id": metric, "project": project_id, "actor": actor_id, "at": at},
        )
        connection.execute(
            text(
                "INSERT INTO "
                "metric_definition_versions(id,metric_definition_id,"
                "version_number,status,definition,unit,aggregation,"
                "content_hash,created_by,created_at,frozen_at) "
                "VALUES "
                "(:id,:parent,1,'FROZEN','{\"kind\":\"mean\"}'::jsonb,'ms','mean',:hash,:actor,:at,:at)"
            ),
            {
                "id": metric_version,
                "parent": metric,
                "hash": "1" * 64,
                "actor": actor_id,
                "at": at,
            },
        )
        connection.execute(
            text("UPDATE metric_definitions SET current_version_id=:version WHERE id=:id"),
            {"version": metric_version, "id": metric},
        )
        connection.execute(
            text(
                "INSERT INTO "
                "experiment_specs(id,project_id,current_version_id,created_by,created_at) "
                "VALUES (:id,:project,NULL,:actor,:at)"
            ),
            {"id": spec, "project": project_id, "actor": actor_id, "at": at},
        )
        connection.execute(
            text(
                "INSERT INTO "
                "experiment_spec_versions(id,experiment_spec_id,"
                "version_number,status,title,objective,protocol,content_hash,"
                "created_by,created_at,frozen_at) "
                "VALUES (:id,:parent,1,'FROZEN','historical spec','historical "
                'objective\',\'{"steps":["execute"]}\'::jsonb,:hash,:actor,:at,:at)'
            ),
            {
                "id": spec_version,
                "parent": spec,
                "hash": "2" * 64,
                "actor": actor_id,
                "at": at,
            },
        )
        connection.execute(
            text("UPDATE experiment_specs SET current_version_id=:version WHERE id=:id"),
            {"version": spec_version, "id": spec},
        )
        connection.execute(
            text(
                "INSERT INTO "
                "runs(id,project_id,experiment_spec_version_id,status,"
                "inputs_sealed_at,started_at,finished_at,exit_code,"
                "created_by,created_at) "
                "VALUES (:id,:project,:spec,'SUCCEEDED',:at,:at,:at,0,:actor,:at)"
            ),
            {
                "id": run,
                "project": project_id,
                "spec": spec_version,
                "actor": actor_id,
                "at": at,
            },
        )
        connection.execute(
            text(
                "INSERT INTO "
                "measurements(id,run_id,metric_definition_version_id,"
                "numeric_value,unit,evaluation_scope,content_hash,created_by,"
                "created_at) "
                "VALUES (:id,:run,:metric,1.25,'ms','{\"split\":\"test\"}'::jsonb,:hash,:actor,:at)"
            ),
            {
                "id": measurement,
                "run": run,
                "metric": metric_version,
                "hash": "3" * 64,
                "actor": actor_id,
                "at": at,
            },
        )
    return measurement


def _insert_valid_result(
    engine: Engine, result_id: UUID, project_id: UUID, actor_id: UUID, measurement_id: UUID
) -> None:
    _insert_result_with_inputs(
        engine, result_id, project_id, actor_id, ((measurement_id, "input", 0),)
    )


def _insert_result_with_inputs(
    engine: Engine,
    result_id: UUID,
    project_id: UUID,
    actor_id: UUID,
    inputs: tuple[tuple[UUID, str, int], ...],
) -> None:
    with engine.begin() as connection:
        _insert_parent(connection, result_id, project_id, actor_id)
        for measurement_id, role, ordinal in inputs:
            connection.execute(
                text(
                    "INSERT INTO statistical_result_inputs"
                    "(statistical_result_id,measurement_id,input_role,ordinal) "
                    "VALUES (:result,:measurement,:role,:ordinal)"
                ),
                {
                    "result": result_id,
                    "measurement": measurement_id,
                    "role": role,
                    "ordinal": ordinal,
                },
            )


def _insert_parent(connection, result_id: UUID, project_id: UUID, actor_id: UUID) -> None:
    connection.execute(
        text(
            "INSERT INTO statistical_results "
            "(id, project_id, analysis_type, result_payload, analysis_definition, "
            "content_hash, created_by, created_at) VALUES "
            "(:id, :project_id, 't_test', CAST(:payload AS jsonb), "
            "CAST(:definition AS jsonb), :content_hash, :created_by, :created_at)"
        ),
        {
            "id": result_id,
            "project_id": project_id,
            "payload": '{"p_value":0.01}',
            "definition": '{"method":"student"}',
            "content_hash": "0" * 64,
            "created_by": actor_id,
            "created_at": datetime(2026, 8, 29, tzinfo=UTC),
        },
    )


def _insert_parent_only(
    engine: Engine,
    result_id: UUID,
    project_id: UUID,
    actor_id: UUID,
) -> None:
    with engine.begin() as connection:
        _insert_parent(connection, result_id, project_id, actor_id)


def _counts(engine: Engine, result_id: UUID) -> tuple[int, int]:
    with engine.connect() as connection:
        parent_count = connection.execute(
            text("SELECT count(*) FROM statistical_results WHERE id=:id"),
            {"id": result_id},
        ).scalar_one()
        input_count = connection.execute(
            text("SELECT count(*) FROM statistical_result_inputs WHERE statistical_result_id=:id"),
            {"id": result_id},
        ).scalar_one()
    return int(parent_count), int(input_count)


def _result_snapshot(engine: Engine, result_id: UUID) -> tuple[object, ...]:
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT id, project_id, analysis_type, result_payload, "
                "analysis_definition, content_hash, created_by, created_at "
                "FROM statistical_results WHERE id=:id"
            ),
            {"id": result_id},
        ).one()
    return tuple(row)


def _input_snapshot(engine: Engine, result_id: UUID) -> tuple[tuple[object, ...], ...]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT statistical_result_id, measurement_id, input_role, ordinal "
                "FROM statistical_result_inputs "
                "WHERE statistical_result_id=:id "
                "ORDER BY ordinal, input_role, measurement_id"
            ),
            {"id": result_id},
        ).all()
    return tuple(tuple(row) for row in rows)


def _catalog_snapshot(engine: Engine) -> dict[str, tuple[tuple[object, ...], ...]]:
    with engine.connect() as connection:
        functions = connection.execute(
            text(
                "SELECT n.nspname, p.proname, "
                "pg_get_function_identity_arguments(p.oid), pg_get_functiondef(p.oid) "
                "FROM pg_proc AS p "
                "JOIN pg_namespace AS n ON n.oid=p.pronamespace "
                "WHERE n.nspname='public' "
                "ORDER BY n.nspname, p.proname, pg_get_function_identity_arguments(p.oid)"
            )
        ).all()
        triggers = connection.execute(
            text(
                "SELECT n.nspname, c.relname, t.tgname, pg_get_triggerdef(t.oid) "
                "FROM pg_trigger AS t "
                "JOIN pg_class AS c ON c.oid=t.tgrelid "
                "JOIN pg_namespace AS n ON n.oid=c.relnamespace "
                "WHERE n.nspname='public' AND NOT t.tgisinternal "
                "ORDER BY n.nspname, c.relname, t.tgname"
            )
        ).all()
        constraints = connection.execute(
            text(
                "SELECT n.nspname, c.relname, con.conname, con.contype, "
                "pg_get_constraintdef(con.oid) "
                "FROM pg_constraint AS con "
                "JOIN pg_class AS c ON c.oid=con.conrelid "
                "JOIN pg_namespace AS n ON n.oid=c.relnamespace "
                "WHERE n.nspname='public' "
                "ORDER BY n.nspname, c.relname, con.conname"
            )
        ).all()
        relations = connection.execute(
            text(
                "SELECT n.nspname, c.relname, c.relkind "
                "FROM pg_class AS c "
                "JOIN pg_namespace AS n ON n.oid=c.relnamespace "
                "WHERE n.nspname='public' "
                "ORDER BY n.nspname, c.relname, c.relkind"
            )
        ).all()
    return {
        "functions": tuple(tuple(row) for row in functions),
        "triggers": tuple(tuple(row) for row in triggers),
        "constraints": tuple(tuple(row) for row in constraints),
        "relations": tuple(tuple(row) for row in relations),
    }


def test_clean_previous_head_upgrade_and_roundtrip_reaches_fail_closed_head() -> None:
    engine = _reset_to_previous_head()
    try:
        actor_id, project_id, actor_context = _seed_historical_project(engine, "pr11r3-clean")
        assert actor_context.actor_id == actor_id
        measurement_id = _seed_historical_measurement(engine, project_id, actor_id)
        result_id = uuid4()
        _insert_valid_result(engine, result_id, project_id, actor_id, measurement_id)
        before_result = _result_snapshot(engine, result_id)
        before_inputs = _input_snapshot(engine, result_id)
        assert _counts(engine, result_id) == (1, 1)
        assert before_inputs == ((result_id, measurement_id, "input", 0),)

        upgrade = _alembic("upgrade", PR11_FINAL_HEAD)
        assert upgrade.returncode == 0, upgrade.stdout + upgrade.stderr
        current = _alembic("current")
        assert current.returncode == 0, current.stdout + current.stderr
        assert PR11_FINAL_HEAD in current.stdout
        assert _result_snapshot(engine, result_id) == before_result
        assert _input_snapshot(engine, result_id) == before_inputs

        downgrade = _alembic("downgrade", PREVIOUS_HEAD)
        assert downgrade.returncode == 0, downgrade.stdout + downgrade.stderr
        retry = _alembic("upgrade", PR11_FINAL_HEAD)
        assert retry.returncode == 0, retry.stdout + retry.stderr
    finally:
        engine.dispose()


def test_invalid_legacy_upgrade_fails_closed_and_manual_remediation_retries() -> None:
    engine = _reset_to_previous_head()
    try:
        actor_id, project_id, actor_context = _seed_historical_project(engine, "pr11r2-legacy")
        assert actor_context.actor_id == actor_id

        downgrade = _alembic("downgrade", "0011_statistical_result")
        assert downgrade.returncode == 0, downgrade.stdout + downgrade.stderr
        legacy_result_id = uuid4()
        _insert_parent_only(engine, legacy_result_id, project_id, actor_id)
        upgrade_previous = _alembic("upgrade", PREVIOUS_HEAD)
        assert upgrade_previous.returncode == 0, upgrade_previous.stdout + upgrade_previous.stderr
        before_result = _result_snapshot(engine, legacy_result_id)
        before_catalog = _catalog_snapshot(engine)

        failed = _alembic("upgrade", "head")
        failure_text = failed.stdout + failed.stderr
        assert failed.returncode != 0
        assert "zero-input statisticalresult" in failure_text.lower()
        assert "manual remediation required" in failure_text.lower()
        current = _alembic("current")
        assert PREVIOUS_HEAD in current.stdout
        assert PR11_FINAL_HEAD not in current.stdout
        assert _counts(engine, legacy_result_id) == (1, 0)
        after_catalog = _catalog_snapshot(engine)
        assert after_catalog["functions"] == before_catalog["functions"]
        assert after_catalog["triggers"] == before_catalog["triggers"]
        assert after_catalog["constraints"] == before_catalog["constraints"]
        assert after_catalog["relations"] == before_catalog["relations"]
        assert _result_snapshot(engine, legacy_result_id) == before_result
        assert _input_snapshot(engine, legacy_result_id) == ()

        measurement_id = _seed_historical_measurement(engine, project_id, actor_id)
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "ALTER TABLE statistical_result_inputs DISABLE TRIGGER "
                "statistical_result_inputs_immutable"
            )
            connection.execute(
                text(
                    "INSERT INTO statistical_result_inputs "
                    "(statistical_result_id, measurement_id, input_role, ordinal) "
                    "VALUES (:result_id, :measurement_id, 'input', 0)"
                ),
                {"result_id": legacy_result_id, "measurement_id": measurement_id},
            )
            connection.exec_driver_sql(
                "ALTER TABLE statistical_result_inputs ENABLE TRIGGER "
                "statistical_result_inputs_immutable"
            )
        assert _counts(engine, legacy_result_id) == (1, 1)

        retry = _alembic("upgrade", PR11_FINAL_HEAD)
        assert retry.returncode == 0, retry.stdout + retry.stderr
        current = _alembic("current")
        assert PR11_FINAL_HEAD in current.stdout

        future_parent_id = uuid4()
        with pytest.raises(DBAPIError):
            _insert_parent_only(engine, future_parent_id, project_id, actor_id)
        assert _counts(engine, future_parent_id) == (0, 0)

        one_input = uuid4()
        _insert_valid_result(engine, one_input, project_id, actor_id, measurement_id)
        second_measurement_id = _seed_historical_measurement(engine, project_id, actor_id)
        multi_input = uuid4()
        _insert_result_with_inputs(
            engine,
            multi_input,
            project_id,
            actor_id,
            ((measurement_id, "input", 0), (second_measurement_id, "secondary", 1)),
        )
        assert _counts(engine, one_input) == (1, 1)
        assert _counts(engine, multi_input) == (1, 2)
    finally:
        engine.dispose()
