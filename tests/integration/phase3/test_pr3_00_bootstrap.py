"""Empty bootstrap verified on isolated real PostgreSQL 18 databases."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine, make_url
from tests.disposable_postgres import disposable_database
from tests.integration.phase2.test_pr2_03_review_guards import _freeze, _setup

ROOT = Path(__file__).resolve().parents[3]
PARENT = "0075_m1_reconsideration"
REVISION = "0076_agent_runtime_bootstrap"
pytestmark = pytest.mark.integration


@pytest.fixture
def database(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[str, Config, Engine]]:
    # Reuse an approved disposable prefix and the existing explicit local-admin opt-in.
    with disposable_database("researchbase_pr212_test_") as url:
        monkeypatch.setenv("DATABASE_URL", url)
        config = Config(str(ROOT / "alembic.ini"))
        config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
        engine = create_engine(url)
        try:
            with engine.connect() as conn:
                version = int(conn.execute(text("SHOW server_version_num")).scalar_one())
                assert version // 10000 == 18
                print("PostgreSQL server_version_num:", version)
            yield url, config, engine
        finally:
            engine.dispose()


def _revision(engine: Engine) -> str:
    with engine.connect() as conn:
        return str(conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one())


def _catalog(url: str) -> str:
    executable = shutil.which("pg_dump")
    assert executable is not None, "PostgreSQL 18 pg_dump is required"
    result = subprocess.run(
        [
            executable,
            "--schema-only",
            "--no-owner",
            "--no-privileges",
            "--dbname",
            make_url(url).set(drivername="postgresql").render_as_string(hide_password=False),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    # pg_dump 18 randomizes only these psql guard tokens on each invocation.
    return re.sub(r"^\\(?:un)?restrict .*\n", "", result.stdout, flags=re.MULTILINE)


def _rows(engine: Engine) -> dict[str, list[str]]:
    with engine.connect().execution_options(isolation_level="REPEATABLE READ") as conn:
        conn.execute(text("SET TRANSACTION READ ONLY"))
        return {
            table: sorted(
                conn.execute(text(f'SELECT to_jsonb(t)::text FROM public."{table}" t')).scalars()
            )
            for table in sorted(inspect(conn).get_table_names(schema="public"))
            if table != "alembic_version"
        }


def _save(tmp_path: Path, label: str, catalog: str, rows: dict[str, list[str]]) -> None:
    (tmp_path / f"{label}-catalog.sql").write_text(catalog)
    (tmp_path / f"{label}-rows.json").write_text(json.dumps(rows, sort_keys=True))
    print(
        label,
        "tables=",
        len(rows),
        "rows=",
        sum(map(len, rows.values())),
        "catalog_sha256=",
        hashlib.sha256(catalog.encode()).hexdigest(),
        "rows_sha256=",
        hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest(),
    )


def test_single_head_and_exact_parent() -> None:
    scripts = ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini")))
    assert scripts.get_heads() == [REVISION]
    revision = scripts.get_revision(REVISION)
    assert revision is not None and revision.down_revision == PARENT


def test_clean_upgrade(database: tuple[str, Config, Engine], tmp_path: Path) -> None:
    url, config, engine = database
    with engine.connect() as conn:
        assert inspect(conn).get_table_names(schema="public") == []
    command.upgrade(config, "head")
    assert _revision(engine) == REVISION
    catalog, rows = _catalog(url), _rows(engine)
    _save(tmp_path, "clean", catalog, rows)
    command.upgrade(config, "head")
    assert _catalog(url) == catalog
    assert _rows(engine) == rows
    assert _revision(engine) == REVISION


@pytest.mark.parametrize("populated", [False, True], ids=["empty", "frozen-history"])
def test_upgrade_from_phase2_preserves_catalog_and_history(
    database: tuple[str, Config, Engine], tmp_path: Path, populated: bool
) -> None:
    url, config, engine = database
    command.upgrade(config, PARENT)
    assert _revision(engine) == PARENT
    setup_engine = None
    try:
        if populated:
            setup_engine, service, principal, project, plan, version = _setup(
                url, migration_revision=PARENT
            )
            _freeze(setup_engine, service, principal, project, plan, version)
            readback = service.get(principal, project, plan)
        before_catalog, before_rows = _catalog(url), _rows(engine)
        if populated:
            assert before_rows["literature_search_plan_versions"]
            assert before_rows["research_question_versions"]
            assert before_rows["search_plan_question_inputs"]
        _save(tmp_path, "parent", before_catalog, before_rows)
        command.upgrade(config, "head")
        assert _revision(engine) == REVISION
        after_catalog, after_rows = _catalog(url), _rows(engine)
        _save(tmp_path, "bootstrap", after_catalog, after_rows)
        assert after_catalog == before_catalog
        assert after_rows == before_rows
        if populated:
            assert service.get(principal, project, plan) == readback
    finally:
        if setup_engine is not None:
            setup_engine.dispose()


@pytest.mark.parametrize("target", [PARENT, "base"])
def test_downgrade_refused_without_revision_catalog_or_data_change(
    database: tuple[str, Config, Engine], tmp_path: Path, target: str
) -> None:
    url, config, engine = database
    setup_engine, service, principal, project, plan, version = _setup(
        url, migration_revision=PARENT
    )
    try:
        _freeze(setup_engine, service, principal, project, plan, version)
        readback = service.get(principal, project, plan)
        command.upgrade(config, "head")
        before_catalog, before_rows = _catalog(url), _rows(engine)
        assert before_rows["literature_search_plan_versions"]
        _save(tmp_path, "before-refusal", before_catalog, before_rows)
        with pytest.raises(
            RuntimeError, match="forward-only migration; use a reviewed forward repair"
        ):
            command.downgrade(config, target)
        assert _revision(engine) == REVISION
        assert _catalog(url) == before_catalog
        assert _rows(engine) == before_rows
        assert service.get(principal, project, plan) == readback
        _save(tmp_path, "after-refusal", _catalog(url), _rows(engine))
    finally:
        setup_engine.dispose()
