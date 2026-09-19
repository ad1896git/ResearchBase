from __future__ import annotations

import os
from collections.abc import Iterator
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from tests.integration.test_pr17dr_migration import _run_alembic, _temporary_database

pytestmark = pytest.mark.integration


@pytest.fixture
def migration_database() -> Iterator[tuple[str, Engine]]:
    base_url = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase",
    )
    with _temporary_database(base_url) as (database_url, engine):
        result = _run_alembic(database_url, "upgrade", "0016_pr17d_history_protection")
        assert result.returncode == 0, result.stdout + result.stderr
        yield database_url, engine


def _seed_governance_rows(engine: Engine) -> tuple[object, ...]:
    actor_id, project_id, finding_id, assessment_id, target_id, correction_id = (
        uuid4() for _ in range(6)
    )
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
        connection.execute(
            text(
                "INSERT INTO audit_findings(id, project_id, finding_type, severity, title, "
                "description, "
                "target_type, target_id, status, created_by, created_at) VALUES "
                "(:id, :project, 'review', 'major', 'title', 'description', 'run', :target, "
                "'open', :actor, now())"
            ),
            {"id": finding_id, "project": project_id, "target": target_id, "actor": actor_id},
        )
        connection.execute(
            text(
                "INSERT INTO impact_assessments(id, project_id, assessment_payload, conclusion, "
                "created_by, created_at, content_hash) VALUES (:id, :project, "
                "CAST(:payload AS jsonb), "
                "'requires_review', :actor, now(), :hash)"
            ),
            {
                "id": assessment_id,
                "project": project_id,
                "payload": "{}",
                "actor": actor_id,
                "hash": "1" * 64,
            },
        )
        connection.execute(
            text(
                "INSERT INTO impact_targets(impact_assessment_id, target_type, target_id, "
                "impact_kind) "
                "VALUES (:assessment, 'run', :target, 'downstream')"
            ),
            {"assessment": assessment_id, "target": target_id},
        )
        connection.execute(
            text(
                "INSERT INTO correction_records(id, project_id, target_type, target_id, "
                "correction_type, "
                "corrected_assertion, reason, created_by, created_at, content_hash) VALUES "
                "(:id, :project, 'run', :target, 'metadata', CAST(:assertion AS jsonb), 'reason', "
                ":actor, now(), :hash)"
            ),
            {
                "id": correction_id,
                "project": project_id,
                "target": target_id,
                "assertion": "{}",
                "actor": actor_id,
                "hash": "2" * 64,
            },
        )
    return actor_id, project_id


def test_0016_to_0017_normalizes_populated_rows_and_adds_target_checks(
    migration_database: tuple[str, Engine],
) -> None:
    database_url, engine = migration_database
    actor_id, project_id = _seed_governance_rows(engine)
    result = _run_alembic(database_url, "upgrade", "0017_persisted_canonical_enum_normalization")
    assert result.returncode == 0, result.stdout + result.stderr
    with engine.connect() as connection:
        values = connection.execute(
            text(
                "SELECT a.actor_type, p.lifecycle_status, f.severity, f.target_type, f.status, "
                "ia.conclusion, it.target_type, it.impact_kind, cr.target_type, cr.correction_type "
                "FROM actors a JOIN projects p ON p.created_by=a.id "
                "JOIN audit_findings f ON f.project_id=p.id "
                "JOIN impact_assessments ia ON ia.project_id=p.id "
                "JOIN impact_targets it ON it.impact_assessment_id=ia.id "
                "JOIN correction_records cr ON cr.project_id=p.id WHERE a.id=:actor"
            ),
            {"actor": actor_id},
        ).one()
        constraints = (
            connection.execute(
                text(
                    "SELECT conname FROM pg_constraint WHERE conrelid IN "
                    "('audit_findings'::regclass, 'impact_targets'::regclass, "
                    "'correction_records'::regclass) "
                    "AND conname LIKE '%target_type' ORDER BY conname"
                )
            )
            .scalars()
            .all()
        )
    assert tuple(values) == (
        "HUMAN",
        "ACTIVE",
        "MAJOR",
        "RUN",
        "OPEN",
        "REQUIRES_REVIEW",
        "RUN",
        "DOWNSTREAM",
        "RUN",
        "METADATA",
    )
    assert constraints == [
        "ck_audit_findings_target_type",
        "ck_correction_records_target_type",
        "ck_impact_targets_target_type",
    ]
    assert project_id is not None


def test_0017_downgrade_restores_legacy_values_and_checks(
    migration_database: tuple[str, Engine],
) -> None:
    database_url, engine = migration_database
    actor_id, _project_id = _seed_governance_rows(engine)
    assert (
        _run_alembic(
            database_url, "upgrade", "0017_persisted_canonical_enum_normalization"
        ).returncode
        == 0
    )
    result = _run_alembic(database_url, "downgrade", "0016_pr17d_history_protection")
    assert result.returncode == 0, result.stdout + result.stderr
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT actor_type FROM actors WHERE id=:id"), {"id": actor_id}
            ).scalar_one()
            == "human"
        )
        assert (
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == "0016_pr17d_history_protection"
        )
    result = _run_alembic(database_url, "upgrade", "0017_persisted_canonical_enum_normalization")
    assert result.returncode == 0, result.stdout + result.stderr


def test_empty_database_can_reach_0017(migration_database: tuple[str, Engine]) -> None:
    database_url, _engine = migration_database
    result = _run_alembic(database_url, "downgrade", "base")
    assert result.returncode == 0, result.stdout + result.stderr
    result = _run_alembic(database_url, "upgrade", "head")
    assert result.returncode == 0, result.stdout + result.stderr


def test_0017_preserves_role_token_checks_and_open_vocabulary_columns(
    migration_database: tuple[str, Engine],
) -> None:
    database_url, engine = migration_database
    result = _run_alembic(database_url, "upgrade", "0017_persisted_canonical_enum_normalization")
    assert result.returncode == 0, result.stdout + result.stderr
    with engine.connect() as connection:
        role_checks = connection.execute(
            text(
                "SELECT conname, pg_get_constraintdef(oid) "
                "FROM pg_constraint WHERE conname IN "
                "('ck_run_dataset_inputs_role', 'ck_run_artifact_inputs_role') "
                "ORDER BY conname"
            )
        ).all()
        open_columns = connection.execute(
            text(
                "SELECT table_name, column_name FROM information_schema.columns "
                "WHERE (table_name, column_name) IN "
                "(('runs', 'run_type'), ('artifacts', 'artifact_type'), "
                "('statistical_results', 'analysis_type'), "
                "('statistical_result_inputs', 'input_role'), "
                "('audit_findings', 'finding_type'))"
            )
        ).all()
    role_checks_by_name = {str(row[0]): str(row[1]) for row in role_checks}
    dataset_role_check = role_checks_by_name["ck_run_dataset_inputs_role"]
    artifact_role_check = role_checks_by_name["ck_run_artifact_inputs_role"]
    assert dataset_role_check.lower().count("train") == 1
    assert artifact_role_check.lower().count("source_code") == 1
    assert "'TRAIN'" not in dataset_role_check
    assert "'SOURCE_CODE'" not in artifact_role_check
    assert len(open_columns) == 5


def test_0017_downgrade_rejects_unknown_canonical_before_mutation(
    migration_database: tuple[str, Engine],
) -> None:
    database_url, engine = migration_database
    result = _run_alembic(database_url, "upgrade", "0017_persisted_canonical_enum_normalization")
    assert result.returncode == 0, result.stdout + result.stderr
    actor_id = uuid4()
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE actors DROP CONSTRAINT ck_actors_actor_type"))
        connection.execute(
            text(
                "INSERT INTO actors(id, actor_type, display_name, created_at) "
                "VALUES (:id, 'BAD_CANONICAL', 'invalid canonical actor', now())"
            ),
            {"id": actor_id},
        )
    result = _run_alembic(database_url, "downgrade", "0016_pr17d_history_protection")
    assert result.returncode != 0
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT actor_type FROM actors WHERE id=:id"), {"id": actor_id}
            ).scalar_one()
            == "BAD_CANONICAL"
        )
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0017_persisted_canonical_enum_normalization"
        )


def test_0017_rejects_unknown_before_schema_mutation(
    migration_database: tuple[str, Engine],
) -> None:
    database_url, engine = migration_database
    actor_id = uuid4()
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE actors DROP CONSTRAINT ck_actors_actor_type"))
        connection.execute(
            text(
                "INSERT INTO actors(id, actor_type, display_name, created_at) "
                "VALUES (:id, 'unknown', 'invalid actor', now())"
            ),
            {"id": actor_id},
        )
    result = _run_alembic(database_url, "upgrade", "0017_persisted_canonical_enum_normalization")
    assert result.returncode != 0
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT actor_type FROM actors WHERE id=:id"), {"id": actor_id}
            ).scalar_one()
            == "unknown"
        )
        assert (
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == "0016_pr17d_history_protection"
        )
