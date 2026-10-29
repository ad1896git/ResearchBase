"""Clean/populated 0077 forward upgrade retains old values and refuses downgrade."""

import json

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from tests.disposable_postgres import disposable_database
from tests.integration.phase3.test_pr3_00_bootstrap import _catalog

LEGACY_TASK_EVENTS_SQL = """
SELECT id,research_task_id,actor_id,command_id,event_type,sequence,task_row_version,
       prior_status,new_status,reason,occurred_at,
       false AS stop_human,false AS stop_policy,false AS stop_budget,
       false AS stop_repeated_failure,false AS stop_no_improvement,false AS stop_success
FROM research_task_events WHERE research_task_id=:id ORDER BY sequence
"""


@pytest.mark.parametrize("populated", (False, True))
def test_forward_upgrade_and_refusal(monkeypatch, tmp_path, populated):
    with disposable_database("researchbase_pr212_test_") as url:
        monkeypatch.setenv("DATABASE_URL", url)
        cfg = Config("alembic.ini")
        command.upgrade(cfg, "0077_research_task_graph")
        engine = create_engine(url)
        try:
            # A populated canonical identity is enough to detect accidental backfill/history writes.
            if populated:
                from tests.integration.phase2.test_pr2_01_source_identity import _authorized_service

                engine.dispose()
                engine, _, _, principal, project = _authorized_service(
                    url, migration_revision="0077_research_task_graph"
                )
                from tests.integration.phase3.conftest import Credentials, PlanningFixture

                from researchbase.agent_runtime.application.research_task import ResearchTaskService
                from researchbase.foundation.artifact_store import (
                    ContentAddressedFilesystemArtifactStore,
                )
                from researchbase.persistence.uow import SqlAlchemyUnitOfWork

                sessions = sessionmaker(engine, expire_on_commit=False, autoflush=False)

                def factory():
                    return SqlAlchemyUnitOfWork(sessions)

                store = ContentAddressedFilesystemArtifactStore(tmp_path / "artifacts")
                planning_service = ResearchTaskService(factory, Credentials(), store)
                fixture = PlanningFixture(
                    engine, factory, planning_service, principal, project, url, store
                )
                task, _ = fixture.plan()
                planning_service.execute(principal, fixture.command("seal_task_plan", task, 2))
                from researchbase.persistence.research_task_repository import (
                    SqlAlchemyResearchTaskRepository,
                )

                original_events = SqlAlchemyResearchTaskRepository.events

                def legacy_events(repo, identity, *, step=False):
                    if step:
                        return original_events(repo, identity, step=True)
                    return repo._many(LEGACY_TASK_EVENTS_SQL, {"id": identity})

                # 0077 has no safety flags. Project the six 0078 false defaults only
                # for this historical read; raw pre/post column equality below still
                # covers every stored value, and the post-upgrade reader is unpatched.
                with monkeypatch.context() as legacy:
                    legacy.setattr(SqlAlchemyResearchTaskRepository, "events", legacy_events)
                    before_graph = planning_service.get_task_graph(principal, project, task)
            with engine.connect() as conn:
                columns = {
                    t: [c["name"] for c in inspect(conn).get_columns(t)]
                    for t in inspect(conn).get_table_names()
                    if t != "alembic_version"
                }  # noqa: E501
                before = {
                    t: sorted(
                        conn.execute(
                            text(
                                f"SELECT row_to_json(x)::text FROM (SELECT {','.join(cols)} FROM {t}) x"  # noqa: E501
                            )
                        ).scalars()
                    )
                    for t, cols in columns.items()
                }  # noqa: E501
            command.upgrade(cfg, "0078_task_safety_policies")
            with engine.connect() as conn:
                after = {
                    t: sorted(
                        conn.execute(
                            text(
                                f"SELECT row_to_json(x)::text FROM (SELECT {','.join(cols)} FROM {t}) x"  # noqa: E501
                            )
                        ).scalars()
                    )
                    for t, cols in columns.items()
                }  # noqa: E501
                assert after == before
                assert len(inspect(conn).get_table_names()) == len(columns) + 9
                assert (
                    conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                    == "0078_task_safety_policies"
                )  # noqa: E501
            if populated:
                assert planning_service.get_task_graph(principal, project, task) == before_graph
            catalog = _catalog(url)
            with pytest.raises(RuntimeError, match="forward-only"):
                command.downgrade(cfg, "0077_research_task_graph")
            assert _catalog(url) == catalog
            (tmp_path / "migration-history.json").write_text(
                json.dumps({"before": before, "after": after})
            )  # noqa: E501
            scripts = ScriptDirectory.from_config(cfg)
            assert scripts.get_heads() == ["0083_bearing_evaluation_guards"]
            assert (
                scripts.get_revision("0078_task_safety_policies").down_revision
                == "0077_research_task_graph"
            )  # noqa: E501
        finally:
            engine.dispose()
