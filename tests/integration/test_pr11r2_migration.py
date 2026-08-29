from __future__ import annotations

import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError
from tests.integration.test_pr11_application import (
    record_result,
    seed_measurement,
    seed_project,
)

from researchbase.application.commands import StatisticalResultInputCommand
from researchbase.persistence.database import create_database_engine

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.getenv("PR11R2_MIGRATION_DB_URL"),
        reason=(
            "PR11R2_MIGRATION_DB_URL is not set; run migration matrix against disposable PostgreSQL"
        ),
    ),
]

REPOSITORY_ROOT = Path(__file__).parents[2]
PREVIOUS_HEAD = "0012_statistical_result_input_guard"
FINAL_HEAD = "0013_statistical_result_legacy_input_precheck"


def _migration_db_url() -> str:
    value = os.getenv("PR11R2_MIGRATION_DB_URL")
    assert value is not None
    return value


def _alembic(*arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = _migration_db_url()
    environment["UV_CACHE_DIR"] = "/private/tmp/researchbase-uv-cache"
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


def _insert_parent_only(
    engine: Engine,
    result_id: UUID,
    project_id: UUID,
    actor_id: UUID,
) -> None:
    with engine.begin() as connection:
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


def test_clean_previous_head_upgrade_and_roundtrip_reaches_fail_closed_head() -> None:
    engine = _reset_to_previous_head()
    try:
        upgrade = _alembic("upgrade", "head")
        assert upgrade.returncode == 0, upgrade.stdout + upgrade.stderr
        current = _alembic("current")
        assert current.returncode == 0, current.stdout + current.stderr
        assert FINAL_HEAD in current.stdout

        downgrade = _alembic("downgrade", PREVIOUS_HEAD)
        assert downgrade.returncode == 0, downgrade.stdout + downgrade.stderr
        retry = _alembic("upgrade", FINAL_HEAD)
        assert retry.returncode == 0, retry.stdout + retry.stderr
    finally:
        engine.dispose()


def test_invalid_legacy_upgrade_fails_closed_and_manual_remediation_retries() -> None:
    engine = _reset_to_previous_head()
    try:
        from researchbase.application.commands import ApplicationService
        from researchbase.foundation.time import FixedClock
        from researchbase.persistence.database import create_session_factory
        from researchbase.persistence.uow import SqlAlchemyUnitOfWork

        sessions = create_session_factory(engine)
        service = ApplicationService(
            lambda: SqlAlchemyUnitOfWork(sessions),
            FixedClock(datetime(2026, 8, 29, tzinfo=UTC)),
        )
        actor_id, project_id, actor_context = seed_project(service, "pr11r2-legacy")

        downgrade = _alembic("downgrade", "0011_statistical_result")
        assert downgrade.returncode == 0, downgrade.stdout + downgrade.stderr
        legacy_result_id = uuid4()
        _insert_parent_only(engine, legacy_result_id, project_id, actor_id)
        upgrade_previous = _alembic("upgrade", PREVIOUS_HEAD)
        assert upgrade_previous.returncode == 0, upgrade_previous.stdout + upgrade_previous.stderr

        failed = _alembic("upgrade", "head")
        failure_text = failed.stdout + failed.stderr
        assert failed.returncode != 0
        assert "zero-input statisticalresult" in failure_text.lower()
        assert "manual remediation required" in failure_text.lower()
        current = _alembic("current")
        assert PREVIOUS_HEAD in current.stdout
        assert FINAL_HEAD not in current.stdout
        assert _counts(engine, legacy_result_id) == (1, 0)

        measurement_id, _ = seed_measurement(
            service,
            project_id,
            actor_context,
            "pr11r2-manual-remediation",
        )
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

        retry = _alembic("upgrade", "head")
        assert retry.returncode == 0, retry.stdout + retry.stderr
        current = _alembic("current")
        assert FINAL_HEAD in current.stdout

        future_parent_id = uuid4()
        with pytest.raises(DBAPIError):
            _insert_parent_only(engine, future_parent_id, project_id, actor_id)
        assert _counts(engine, future_parent_id) == (0, 0)

        one_input = record_result(
            service,
            project_id,
            actor_context,
            (StatisticalResultInputCommand(measurement_id),),
        )
        second_measurement_id, _ = seed_measurement(
            service,
            project_id,
            actor_context,
            "pr11r2-normal-multi",
        )
        multi_input = record_result(
            service,
            project_id,
            actor_context,
            (
                StatisticalResultInputCommand(measurement_id),
                StatisticalResultInputCommand(second_measurement_id, "secondary", 1),
            ),
        )
        assert one_input.id != multi_input.id
    finally:
        engine.dispose()
