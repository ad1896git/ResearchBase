"""Forward-only upgrade from accepted PR3-00 retains exact scientific history."""

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from tests.disposable_postgres import disposable_database
from tests.integration.phase2.test_pr2_03_review_guards import _freeze, _setup
from tests.integration.phase3.test_pr3_00_bootstrap import _catalog, _rows, _save


@pytest.mark.parametrize("populated", (False, True))
def test_clean_and_populated_upgrade_and_downgrade_refusal(monkeypatch, tmp_path, populated):
    with disposable_database("researchbase_pr212_test_") as url:
        monkeypatch.setenv("DATABASE_URL", url)
        config = Config("alembic.ini")
        config.set_main_option("sqlalchemy.url", url)
        if populated:
            engine, service, principal, project, plan, version = _setup(
                url, migration_revision="0076_agent_runtime_bootstrap"
            )
            _freeze(engine, service, principal, project, plan, version)
            readback = service.get(principal, project, plan)
        else:
            command.upgrade(config, "0076_agent_runtime_bootstrap")
            engine = create_engine(url)
        try:
            before = _rows(engine)
            _save(tmp_path, "accepted-0076", _catalog(url), before)
            command.upgrade(config, "0077_research_task_graph")
            after = _rows(engine)
            assert all(after[table] == rows for table, rows in before.items())
            assert len(after) == len(before) + 10
            if populated:
                assert service.get(principal, project, plan) == readback
            assert ScriptDirectory.from_config(config).get_heads() == [
                "0082_experiment_search_core"
            ]
            revision = ScriptDirectory.from_config(config).get_revision("0077_research_task_graph")
            assert revision is not None and revision.down_revision == "0076_agent_runtime_bootstrap"
            catalog = _catalog(url)
            with pytest.raises(
                RuntimeError, match="forward-only migration; use a reviewed forward repair"
            ):
                command.downgrade(config, "0076_agent_runtime_bootstrap")
            assert _rows(engine) == after and _catalog(url) == catalog
            with engine.connect() as conn:
                assert (
                    conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                    == "0077_research_task_graph"
                )
                columns = {c["name"] for c in inspect(conn).get_columns("research_tasks")}
                assert (
                    not {"budget_policy_id", "termination_policy_id", "checkpoint_policy_id"}
                    & columns
                )
            _save(tmp_path, "forward-history-retained", catalog, after)
        finally:
            engine.dispose()


def test_planning_tables_empty_on_clean_upgrade(monkeypatch):
    with disposable_database("researchbase_pr212_test_") as url:
        monkeypatch.setenv("DATABASE_URL", url)
        config = Config("alembic.ini")
        config.set_main_option("sqlalchemy.url", url)
        command.upgrade(config, "0077_research_task_graph")
        engine = create_engine(url)
        try:
            with engine.connect() as conn:
                assert (
                    int(conn.execute(text("SHOW server_version_num")).scalar_one()) // 10000 == 18
                )
                for table in inspect(conn).get_table_names():
                    if table.startswith("research_task"):
                        assert conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() == 0
        finally:
            engine.dispose()
