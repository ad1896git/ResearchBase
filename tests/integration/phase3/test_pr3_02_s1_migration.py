import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from tests.disposable_postgres import disposable_database
from tests.integration.phase3.agent_fixtures import enrollment, register


def test_populated_upgrade_and_downgrade_refusal(agents, monkeypatch):
    cmd = enrollment(agents)
    agents.service.execute(cmd)
    agents.service.execute(register(agents, cmd.arguments.actor_id))
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", agents.url.replace("%", "%%"))
    monkeypatch.setenv("DATABASE_URL", agents.url)
    with pytest.raises(RuntimeError, match="forward-only"):
        command.downgrade(config, "0078_task_safety_policies")
    with agents.engine.connect() as conn:
        assert (
            conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == "0079_agent_identity_versions"
        )
        assert conn.execute(text("SELECT count(*) FROM agent_versions")).scalar_one() == 1
        assert (
            conn.execute(
                text(
                    "SELECT count(*) FROM pg_tables WHERE schemaname='public' AND tablename IN "
                    "('agent_execution_instances','agent_promotion_records','capability_invocations')"
                )
            ).scalar_one()
            == 0
        )


def test_empty_upgrade_and_refusal(monkeypatch):
    with disposable_database("researchbase_pr212_test_") as url:
        monkeypatch.setenv("DATABASE_URL", url)
        config = Config("alembic.ini")
        config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
        command.upgrade(config, "0078_task_safety_policies")
        engine = create_engine(url)
        try:
            with engine.connect() as conn:
                before = (
                    conn.execute(
                        text(
                            "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY "
                            "tablename"
                        )
                    )
                    .scalars()
                    .all()
                )
            command.upgrade(config, "head")
            assert ScriptDirectory.from_config(config).get_heads() == [
                "0079_agent_identity_versions"
            ]
            with pytest.raises(RuntimeError, match="forward-only"):
                command.downgrade(config, "0078_task_safety_policies")
            with engine.connect() as conn:
                after = (
                    conn.execute(
                        text(
                            "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY "
                            "tablename"
                        )
                    )
                    .scalars()
                    .all()
                )
                assert set(after) - set(before) == {
                    "agent_versions",
                    "agent_availability",
                    "agent_command_receipts",
                    "agent_availability_events",
                }
                assert (
                    conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                    == "0079_agent_identity_versions"
                )
        finally:
            engine.dispose()


def test_populated_0077_upgrade_preserves_exact_rows_and_hashes(monkeypatch, tmp_path):
    from tests.integration.phase2.test_pr2_03_review_guards import _freeze, _setup
    from tests.integration.phase3.agent_fixtures import Credentials
    from tests.integration.phase3.test_pr3_00_bootstrap import _rows

    from researchbase.agent_runtime.application.contracts import parse_command
    from researchbase.agent_runtime.application.research_task import ResearchTaskService
    from researchbase.foundation.ids import new_uuid7
    from researchbase.persistence.uow import research_task_uow_factory

    with disposable_database("researchbase_pr212_test_") as url:
        monkeypatch.setenv("DATABASE_URL", url)
        engine, service, principal, project, plan, version = _setup(
            url, migration_revision="0078_task_safety_policies"
        )
        try:
            _freeze(engine, service, principal, project, plan, version)
            readback = service.get(principal, project, plan)
            tasks = ResearchTaskService(research_task_uow_factory(url), Credentials())
            cmd = parse_command(
                "create_research_task",
                {
                    "project_id": str(project),
                    "command_id": str(new_uuid7()),
                    "task_id": str(new_uuid7()),
                    "expected_row_version": None,
                    "arguments": {
                        "task_type": "LITERATURE_RESEARCH",
                        "objective": "retained upgrade task",
                        "strategy_id": "human_guided_research",
                        "strategy_version": "1.0.0",
                    },
                },
            )
            tasks.execute(principal, cmd)
            task_before = tasks.get_task_graph(principal, project, cmd.task_id)
            before = _rows(engine)
            config = Config("alembic.ini")
            config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
            command.upgrade(config, "0079_agent_identity_versions")
            after = _rows(engine)
            assert all(after[table] == rows for table, rows in before.items())
            assert set(after) - set(before) == {
                "agent_versions",
                "agent_availability",
                "agent_command_receipts",
                "agent_availability_events",
            }
            assert service.get(principal, project, plan) == readback
            assert tasks.get_task_graph(principal, project, cmd.task_id) == task_before
            assert not task_before.task.execution_enabled
        finally:
            engine.dispose()
