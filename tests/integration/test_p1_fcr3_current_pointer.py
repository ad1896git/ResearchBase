from __future__ import annotations

import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.repositories import (
    SqlAlchemyClaimRepository,
    SqlAlchemyExperimentSpecRepository,
    SqlAlchemyHypothesisRepository,
    SqlAlchemyResearchQuestionRepository,
)

pytestmark = pytest.mark.integration

REPOSITORY_ROOT = Path(__file__).parents[2]
TARGET_REVISION = "0017_persisted_canonical_enum_normalization"
CURRENT_REVISION = "0018_current_pointer_same_parent_integrity"
COMPOSITE_FK_NAMES = {
    "fk_research_questions_current_version_same_parent",
    "fk_hypotheses_current_version_same_parent",
    "fk_experiment_specs_current_version_same_parent",
    "fk_artifacts_current_version_same_parent",
    "fk_metric_definitions_current_version_same_parent",
    "fk_claims_current_version_same_parent",
}
UNIQUE_NAMES = {
    "uq_research_question_versions_parent_id_id",
    "uq_hypothesis_versions_parent_id_id",
    "uq_experiment_spec_versions_parent_id_id",
    "uq_artifact_versions_parent_id_id",
    "uq_metric_definition_versions_parent_id_id",
    "uq_claim_versions_parent_id_id",
}

REPOSITORIES = {
    "research_question": SqlAlchemyResearchQuestionRepository,
    "hypothesis": SqlAlchemyHypothesisRepository,
    "experiment_spec": SqlAlchemyExperimentSpecRepository,
    "claim": SqlAlchemyClaimRepository,
}


@dataclass(frozen=True, slots=True)
class PointerFamily:
    name: str
    identity_table: str
    version_table: str
    parent_column: str
    identity_insert: str
    version_insert: str


FAMILIES = (
    PointerFamily(
        "research_question",
        "research_questions",
        "research_question_versions",
        "research_question_id",
        "INSERT INTO research_questions (id, project_id, created_by, created_at) "
        "VALUES (:id, :project, :actor, :now)",
        "INSERT INTO research_question_versions "
        "(id, research_question_id, version_number, status, question_text, created_by, created_at) "
        "VALUES (:id, :parent, 1, 'DRAFT', :text, :actor, :now)",
    ),
    PointerFamily(
        "hypothesis",
        "hypotheses",
        "hypothesis_versions",
        "hypothesis_id",
        "INSERT INTO hypotheses (id, project_id, created_by, created_at) "
        "VALUES (:id, :project, :actor, :now)",
        "INSERT INTO hypothesis_versions "
        "(id, hypothesis_id, version_number, status, statement, created_by, created_at) "
        "VALUES (:id, :parent, 1, 'DRAFT', :text, :actor, :now)",
    ),
    PointerFamily(
        "experiment_spec",
        "experiment_specs",
        "experiment_spec_versions",
        "experiment_spec_id",
        "INSERT INTO experiment_specs (id, project_id, created_by, created_at) "
        "VALUES (:id, :project, :actor, :now)",
        "INSERT INTO experiment_spec_versions "
        "(id, experiment_spec_id, version_number, status, title, objective, protocol, "
        "created_by, created_at) VALUES (:id, :parent, 1, 'DRAFT', :title, :objective, "
        "'{}'::jsonb, "
        ":actor, :now)",
    ),
    PointerFamily(
        "artifact",
        "artifacts",
        "artifact_versions",
        "artifact_id",
        "INSERT INTO artifacts (id, project_id, artifact_type, name, created_by, created_at) "
        "VALUES (:id, :project, 'text/plain', :text, :actor, :now)",
        "INSERT INTO artifact_versions "
        "(id, artifact_id, version_number, status, content_hash, created_by, created_at) "
        "VALUES (:id, :parent, 1, 'DRAFT', :hash, :actor, :now)",
    ),
    PointerFamily(
        "metric_definition",
        "metric_definitions",
        "metric_definition_versions",
        "metric_definition_id",
        "INSERT INTO metric_definitions (id, project_id, name, created_by, created_at) "
        "VALUES (:id, :project, :text, :actor, :now)",
        "INSERT INTO metric_definition_versions "
        "(id, metric_definition_id, version_number, status, definition, created_by, created_at) "
        "VALUES (:id, :parent, 1, 'DRAFT', CAST(:definition AS jsonb), :actor, :now)",
    ),
    PointerFamily(
        "claim",
        "claims",
        "claim_versions",
        "claim_id",
        "INSERT INTO claims (id, project_id, created_by, created_at) "
        "VALUES (:id, :project, :actor, :now)",
        "INSERT INTO claim_versions "
        "(id, claim_id, version_number, status, statement, created_by, created_at) "
        "VALUES (:id, :parent, 1, 'DRAFT', :text, :actor, :now)",
    ),
)
CURRENT_READ_FAMILIES = tuple(family for family in FAMILIES if family.name in REPOSITORIES)


def _run_alembic(database_url: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = database_url
    environment.setdefault("UV_CACHE_DIR", "/tmp/researchbase-uv-cache")
    return subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=REPOSITORY_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def _create_database_at(base_url: str, revision: str) -> tuple[str, Engine, Engine, str]:
    base = make_url(base_url)
    database = f"researchbase_p1_fcr3_{uuid4().hex[:16]}"
    admin = create_engine(base.set(database="postgres"), isolation_level="AUTOCOMMIT")
    database_url = base.set(database=database).render_as_string(hide_password=False)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE DATABASE "{database}"'))
    result = _run_alembic(database_url, "upgrade", revision)
    if result.returncode != 0:
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{database}" WITH (FORCE)'))
        admin.dispose()
        raise AssertionError(f"Alembic setup failed:\n{result.stdout}\n{result.stderr}")
    return database_url, create_engine(database_url), admin, database


@pytest.fixture(scope="module")
def base_url() -> str:
    value = os.getenv("DATABASE_URL")
    if not value:
        pytest.skip("DATABASE_URL is not set; P1-FCR3 requires PostgreSQL")
    return value


@pytest.fixture(scope="module")
def head_database(base_url: str):
    url, engine, admin, database = _create_database_at(base_url, "head")
    yield url, engine
    engine.dispose()
    with admin.connect() as connection:
        connection.execute(text(f'DROP DATABASE IF EXISTS "{database}" WITH (FORCE)'))
    admin.dispose()


@pytest.fixture(scope="module")
def previous_head_database(base_url: str):
    url, engine, admin, database = _create_database_at(base_url, TARGET_REVISION)
    yield url, engine
    engine.dispose()
    with admin.connect() as connection:
        connection.execute(text(f'DROP DATABASE IF EXISTS "{database}" WITH (FORCE)'))
    admin.dispose()


@pytest.fixture(scope="module")
def populated_previous_head_database(base_url: str):
    url, engine, admin, database = _create_database_at(base_url, TARGET_REVISION)
    yield url, engine
    engine.dispose()
    with admin.connect() as connection:
        connection.execute(text(f'DROP DATABASE IF EXISTS "{database}" WITH (FORCE)'))
    admin.dispose()


@pytest.fixture(scope="module")
def roundtrip_database(base_url: str):
    url, engine, admin, database = _create_database_at(base_url, "head")
    yield url, engine
    engine.dispose()
    with admin.connect() as connection:
        connection.execute(text(f'DROP DATABASE IF EXISTS "{database}" WITH (FORCE)'))
    admin.dispose()


def _seed_family(engine: Engine, family: PointerFamily) -> dict[str, UUID]:
    actor_id, project_id, identity_a, identity_b, version_a, version_b = (uuid4() for _ in range(6))
    now = datetime(2026, 9, 21, tzinfo=UTC)
    common = {"actor": actor_id, "project": project_id, "now": now, "text": family.name}
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO actors (id, actor_type, display_name, created_at) "
                "VALUES (:id, 'HUMAN', :name, :now)"
            ),
            {"id": actor_id, "name": f"P1-FCR3-{family.name}", "now": now},
        )
        connection.execute(
            text(
                "INSERT INTO projects (id, name, created_by, created_at) "
                "VALUES (:id, :name, :actor, :now)"
            ),
            {"id": project_id, "name": f"P1-FCR3-{family.name}", **common},
        )
        for identity_id in (identity_a, identity_b):
            connection.execute(
                text(family.identity_insert),
                {"id": identity_id, **common},
            )
        for version_id, parent_id in ((version_a, identity_a), (version_b, identity_b)):
            connection.execute(
                text(family.version_insert),
                {
                    "id": version_id,
                    "parent": parent_id,
                    "actor": actor_id,
                    "now": now,
                    "text": family.name,
                    "title": family.name,
                    "objective": family.name,
                    "definition": '{"kind":"audit"}',
                    "hash": "a" * 64,
                },
            )
    return {"identity_a": identity_a, "version_a": version_a, "version_b": version_b}


@pytest.mark.parametrize("family", FAMILIES, ids=lambda family: family.name)
def test_cross_parent_current_pointer_is_rejected_by_postgresql(
    head_database: tuple[str, Engine], family: PointerFamily
) -> None:
    _url, engine = head_database
    ids = _seed_family(engine, family)

    with pytest.raises(IntegrityError) as raised:
        with engine.begin() as connection:
            connection.execute(
                text(
                    f"UPDATE {family.identity_table} "
                    "SET current_version_id=:version WHERE id=:identity"
                ),
                {"version": ids["version_b"], "identity": ids["identity_a"]},
            )

    assert getattr(raised.value.orig, "sqlstate", None) == "23503"
    assert f"{family.identity_table}_current_version_same_parent" in str(raised.value.orig)


@pytest.mark.parametrize("family", FAMILIES, ids=lambda family: family.name)
def test_same_parent_current_pointer_remains_valid(
    head_database: tuple[str, Engine], family: PointerFamily
) -> None:
    _url, engine = head_database
    ids = _seed_family(engine, family)
    with engine.begin() as connection:
        connection.execute(
            text(
                f"UPDATE {family.identity_table} SET current_version_id=:version WHERE id=:identity"
            ),
            {"version": ids["version_a"], "identity": ids["identity_a"]},
        )


@pytest.mark.parametrize("family", FAMILIES, ids=lambda family: family.name)
def test_null_current_pointer_remains_valid(
    head_database: tuple[str, Engine], family: PointerFamily
) -> None:
    _url, engine = head_database
    ids = _seed_family(engine, family)
    with engine.begin() as connection:
        connection.execute(
            text(f"UPDATE {family.identity_table} SET current_version_id=NULL WHERE id=:identity"),
            {"identity": ids["identity_a"]},
        )
        assert (
            connection.execute(
                text(f"SELECT current_version_id FROM {family.identity_table} WHERE id=:identity"),
                {"identity": ids["identity_a"]},
            ).scalar_one()
            is None
        )


@pytest.mark.parametrize("family", FAMILIES, ids=lambda family: family.name)
def test_nonexistent_current_pointer_is_rejected_by_postgresql(
    head_database: tuple[str, Engine], family: PointerFamily
) -> None:
    _url, engine = head_database
    ids = _seed_family(engine, family)
    with pytest.raises(IntegrityError) as raised:
        with engine.begin() as connection:
            connection.execute(
                text(
                    f"UPDATE {family.identity_table} "
                    "SET current_version_id=:version WHERE id=:identity"
                ),
                {"version": uuid4(), "identity": ids["identity_a"]},
            )
    assert getattr(raised.value.orig, "sqlstate", None) == "23503"


def test_cross_family_version_id_is_rejected_by_postgresql(
    head_database: tuple[str, Engine],
) -> None:
    _url, engine = head_database
    seeded = {family: _seed_family(engine, family) for family in FAMILIES}
    for index, family in enumerate(FAMILIES):
        other = FAMILIES[(index + 1) % len(FAMILIES)]
        with pytest.raises(IntegrityError) as raised:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        f"UPDATE {family.identity_table} "
                        "SET current_version_id=:version WHERE id=:identity"
                    ),
                    {
                        "version": seeded[other]["version_a"],
                        "identity": seeded[family]["identity_a"],
                    },
                )
        assert getattr(raised.value.orig, "sqlstate", None) == "23503"


@pytest.mark.parametrize("family", FAMILIES, ids=lambda family: family.name)
def test_concurrent_same_parent_and_cross_parent_updates_are_safe(
    head_database: tuple[str, Engine], family: PointerFamily
) -> None:
    _url, engine = head_database
    ids = _seed_family(engine, family)
    barrier = Barrier(2)

    def update(version_id: UUID) -> str:
        try:
            with engine.begin() as connection:
                barrier.wait()
                connection.execute(
                    text(
                        f"UPDATE {family.identity_table} "
                        "SET current_version_id=:version WHERE id=:identity"
                    ),
                    {"version": version_id, "identity": ids["identity_a"]},
                )
            return "committed"
        except IntegrityError as exc:
            return str(getattr(exc.orig, "sqlstate", ""))

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(update, (ids["version_a"], ids["version_b"])))

    assert sorted(outcomes) == ["23503", "committed"]
    with engine.connect() as connection:
        assert (
            connection.execute(
                text(f"SELECT current_version_id FROM {family.identity_table} WHERE id=:identity"),
                {"identity": ids["identity_a"]},
            ).scalar_one()
            == ids["version_a"]
        )


def test_migration_preflight_rejects_multiple_corrupt_families_before_ddl(
    previous_head_database: tuple[str, Engine],
) -> None:
    database_url, engine = previous_head_database
    seeded = {family: _seed_family(engine, family) for family in FAMILIES}
    with engine.begin() as connection:
        for family, ids in seeded.items():
            connection.execute(
                text(
                    f"UPDATE {family.identity_table} "
                    "SET current_version_id=:version WHERE id=:identity"
                ),
                {"version": ids["version_b"], "identity": ids["identity_a"]},
            )

    result = _run_alembic(database_url, "upgrade", "head")
    assert result.returncode != 0
    with engine.connect() as connection:
        assert (
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == TARGET_REVISION
        )
        names = {
            row[0]
            for row in connection.execute(
                text("SELECT conname FROM pg_constraint WHERE conname = ANY(:names)"),
                {"names": list(COMPOSITE_FK_NAMES | UNIQUE_NAMES)},
            )
        }
        assert names == set()
        for family, ids in seeded.items():
            assert (
                connection.execute(
                    text(
                        f"SELECT current_version_id FROM {family.identity_table} WHERE id=:identity"
                    ),
                    {"identity": ids["identity_a"]},
                ).scalar_one()
                == ids["version_b"]
            )


def test_catalog_contains_exact_p1_fcr3_constraints(
    head_database: tuple[str, Engine],
) -> None:
    _url, engine = head_database
    with engine.connect() as connection:
        rows = (
            connection.execute(
                text(
                    "SELECT conname, contype, convalidated, "
                    "pg_get_constraintdef(oid) AS definition "
                    "FROM pg_constraint WHERE conname = ANY(:names) ORDER BY conname"
                ),
                {"names": list(COMPOSITE_FK_NAMES | UNIQUE_NAMES)},
            )
            .mappings()
            .all()
        )
    assert {row["conname"] for row in rows} == COMPOSITE_FK_NAMES | UNIQUE_NAMES
    assert len(rows) == 12
    assert all(row["convalidated"] for row in rows)
    for row in rows:
        if row["conname"] in UNIQUE_NAMES:
            assert row["contype"] == "u"
            assert "UNIQUE" in row["definition"]
        else:
            assert row["contype"] == "f"
            assert "FOREIGN KEY (id, current_version_id)" in row["definition"]


def test_valid_populated_0017_upgrade_succeeds(
    populated_previous_head_database: tuple[str, Engine],
) -> None:
    database_url, engine = populated_previous_head_database
    seeded = {family: _seed_family(engine, family) for family in FAMILIES}
    with engine.begin() as connection:
        for family, ids in seeded.items():
            connection.execute(
                text(
                    f"UPDATE {family.identity_table} "
                    "SET current_version_id=:version WHERE id=:identity"
                ),
                {"version": ids["version_a"], "identity": ids["identity_a"]},
            )

    result = _run_alembic(database_url, "upgrade", CURRENT_REVISION)
    assert result.returncode == 0, f"Alembic upgrade failed:\n{result.stdout}\n{result.stderr}"
    with engine.connect() as connection:
        assert (
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == CURRENT_REVISION
        )
        assert (
            connection.execute(
                text("SELECT count(*) FROM pg_constraint WHERE conname = ANY(:names)"),
                {"names": list(COMPOSITE_FK_NAMES | UNIQUE_NAMES)},
            ).scalar_one()
            == 12
        )


def test_missing_target_preflight_fails_before_ddl(
    previous_head_database: tuple[str, Engine],
) -> None:
    database_url, engine = previous_head_database
    family = FAMILIES[0]
    ids = _seed_family(engine, family)
    with engine.begin() as connection:
        old_fk = connection.execute(
            text(
                "SELECT conname FROM pg_constraint "
                "WHERE conrelid = CAST(:table_name AS regclass) "
                "AND contype = 'f' "
                "AND pg_get_constraintdef(oid) LIKE '%current_version_id%'"
            ),
            {"table_name": family.identity_table},
        ).scalar_one()
        connection.execute(text(f'ALTER TABLE {family.identity_table} DROP CONSTRAINT "{old_fk}"'))
        connection.execute(
            text(
                f"UPDATE {family.identity_table} SET current_version_id=:version WHERE id=:identity"
            ),
            {"version": uuid4(), "identity": ids["identity_a"]},
        )

    result = _run_alembic(database_url, "upgrade", "head")
    assert result.returncode != 0
    assert "MISSING_TARGET" in f"{result.stdout}\n{result.stderr}"
    with engine.connect() as connection:
        assert (
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == TARGET_REVISION
        )
        assert (
            connection.execute(
                text("SELECT count(*) FROM pg_constraint WHERE conname = ANY(:names)"),
                {"names": list(COMPOSITE_FK_NAMES | UNIQUE_NAMES)},
            ).scalar_one()
            == 0
        )


def test_downgrade_removes_only_p1_fcr3_objects(
    roundtrip_database: tuple[str, Engine],
) -> None:
    database_url, engine = roundtrip_database
    result = _run_alembic(database_url, "downgrade", TARGET_REVISION)
    assert result.returncode == 0, f"Alembic downgrade failed:\n{result.stdout}\n{result.stderr}"
    with engine.connect() as connection:
        assert (
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == TARGET_REVISION
        )
        assert (
            connection.execute(
                text("SELECT count(*) FROM pg_constraint WHERE conname = ANY(:names)"),
                {"names": list(COMPOSITE_FK_NAMES | UNIQUE_NAMES)},
            ).scalar_one()
            == 0
        )
        assert (
            connection.execute(
                text(
                    "SELECT count(*) FROM pg_constraint WHERE conname IN "
                    "('fk_research_questions_current_version', 'fk_claim_current_version')"
                )
            ).scalar_one()
            == 2
        )

    result = _run_alembic(database_url, "upgrade", "head")
    assert result.returncode == 0, f"Alembic re-upgrade failed:\n{result.stdout}\n{result.stderr}"


@pytest.mark.parametrize("family", CURRENT_READ_FAMILIES, ids=lambda family: family.name)
def test_repository_read_fails_closed_on_legacy_cross_parent_pointer(
    previous_head_database: tuple[str, Engine], family: PointerFamily
) -> None:
    _url, engine = previous_head_database
    ids = _seed_family(engine, family)
    with engine.begin() as connection:
        connection.execute(
            text(
                f"UPDATE {family.identity_table} SET current_version_id=:version WHERE id=:identity"
            ),
            {"version": ids["version_b"], "identity": ids["identity_a"]},
        )

    with Session(engine) as session:
        repository = REPOSITORIES[family.name](session)
        with pytest.raises(ResearchBaseError) as raised:
            repository.get_current_version(ids["identity_a"])

    assert raised.value.code is ErrorCode.REFERENTIAL_INTEGRITY_ERROR
