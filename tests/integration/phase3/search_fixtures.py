"""S1 raw ordinary-role protocol on disposable PG18; no search Application API."""

from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from tests.disposable_postgres import disposable_database
from tests.integration.phase2.pr2_20_support import upgrade
from tests.integration.phase2.test_pr2_01_source_identity import _authorized_service
from tests.integration.phase3.conftest import Credentials, PlanningFixture
from tests.integration.phase3.test_pr3_04_application import approve, bind

from researchbase.agent_runtime.application.research_task import ResearchTaskService
from researchbase.foundation.artifact_store import ContentAddressedFilesystemArtifactStore
from researchbase.foundation.hashing import sha256_canonical_json
from researchbase.foundation.ids import new_uuid7
from researchbase.persistence.research_task_repository import SHARE_SQL
from researchbase.persistence.uow import SqlAlchemyUnitOfWork

PARENT = "0081_agent_execution_intents"
HEAD = "0082_experiment_search_core"
TABLES = (
    "experiment_search_sessions",
    "experiment_search_nodes",
    "experiment_search_node_runs",
    "experiment_search_events",
)


def insert(conn, table, row):
    conn.execute(
        text(f"INSERT INTO {table} ({','.join(row)}) VALUES ({','.join(':' + k for k in row)})"),
        row,
    )


def lock(conn, project, actor, command, task, *, agent=False, missing=None):
    conn.execute(text(SHARE_SQL))
    conn.execute(text("SELECT rb_phase2_lock_project(:id)"), {"id": project})
    keys = [f"pr301:command:{project}:{actor}:{command}", f"pr301:task:{task}"]
    if agent:
        keys.append(f"pr302:actor:{actor}")
    for key in keys:
        if missing is None or not key.startswith(missing):
            conn.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:k,0))"), {"k": key})
    conn.execute(text("SELECT id FROM research_tasks WHERE id=:id FOR UPDATE"), {"id": task})


def create_rows(
    conn, env, *, task=None, missing=None, omit=None, bad_hash=False, session_changes=None
):
    """One complete create effect; callers can omit an effect to test closure."""
    task = task or env.task
    actor, project = env.p.principal.actor_id, env.p.project
    command, receipt, session, event, task_event = (new_uuid7() for _ in range(5))
    lock(conn, project, actor, command, task, missing=missing)
    t = (
        conn.execute(text("SELECT * FROM research_tasks WHERE id=:id"), {"id": task})
        .mappings()
        .one()
    )
    revision = t["row_version"] + 1
    conn.execute(
        text("UPDATE research_tasks SET row_version=:v WHERE id=:id"), {"id": task, "v": revision}
    )
    at = conn.execute(text("SELECT transaction_timestamp()")).scalar_one()
    material = dict(
        type="ExperimentSearchCommand",
        material_version=1,
        command_name="create_search_session",
        project_id=str(project),
        actor_id=str(actor),
        command_id=str(command),
        task_id=str(task),
        expected_row_version=revision - 1,
        arguments=dict(
            session_id=str(session),
            root_hypothesis_version_id=None,
            root_experiment_spec_version_id=None,
        ),
    )
    insert(
        conn,
        "research_task_command_receipts",
        dict(
            id=receipt,
            project_id=project,
            actor_id=actor,
            command_id=command,
            research_task_id=task,
            command_name="create_search_session",
            request_hash="a" * 64 if bad_hash else str(sha256_canonical_json(material)),
            hash_scheme="sha256-cjson-v1",
            material_version=1,
            resulting_row_version=revision,
            completed_at=at,
            result_search_session_id=session,
            result_search_event_id=event,
        ),
    )
    if omit != "session":
        insert(
            conn,
            "experiment_search_sessions",
            {
                **dict(
                    id=session,
                    project_id=project,
                    research_task_id=task,
                    budget_id=t["budget_policy_id"],
                    created_by=actor,
                    created_at=at,
                    receipt_id=receipt,
                ),
                **(session_changes or {}),
            },
        )
    if omit not in ("event", "session"):
        insert(
            conn,
            "experiment_search_events",
            dict(
                id=event,
                research_task_id=task,
                search_session_id=session,
                sequence=1,
                event_type="SESSION_CREATED",
                reason="Search session created.",
                actor_id=actor,
                occurred_at=at,
                receipt_id=receipt,
            ),
        )
    if omit != "task_event":
        insert(
            conn,
            "research_task_events",
            dict(
                id=task_event,
                research_task_id=task,
                actor_id=actor,
                command_id=command,
                event_type="SEARCH_SESSION_CREATED",
                sequence=revision,
                task_row_version=revision,
                prior_status=t["status"],
                new_status=t["status"],
                reason="Search session created.",
                occurred_at=at,
            ),
        )
        insert(
            conn,
            "research_task_receipt_events",
            dict(
                receipt_id=receipt,
                research_task_id=task,
                event_id=task_event,
            ),
        )
    return SimpleNamespace(receipt=receipt, session=session, event=event, task_event=task_event)


@pytest.fixture(name="search_env", scope="module")
def _search_env(tmp_path_factory):
    yield from search_environment(tmp_path_factory)


def search_environment(tmp_path_factory, *, revision=HEAD):
    """Isolated support for later upgrades; historical fixtures retain HEAD=0082."""
    with disposable_database("researchbase_pr212_test_") as url:
        with pytest.MonkeyPatch.context() as patch:
            patch.setenv("DATABASE_URL", url)
            admin, _, _, principal, project = _authorized_service(url, migration_revision=PARENT)
        role = "pr316_" + new_uuid7().hex
        engine = None
        try:
            upgrade(url, revision)
            with admin.begin() as conn:
                conn.execute(
                    text(f"CREATE ROLE {role} NOSUPERUSER NOCREATEDB NOCREATEROLE NOLOGIN")
                )
                conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {role}"))
                conn.execute(
                    text(
                        "GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public "
                        f"TO {role}"
                    )
                )
                # Even an accidental TRUNCATE grant cannot remove immutable history.
                conn.execute(text(f"GRANT TRUNCATE ON {','.join(TABLES)} TO {role}"))
            engine = create_engine(
                url,
                connect_args={
                    "options": f"-c role={role} -c lock_timeout=10s -c statement_timeout=30s"
                },
            )
            sessions = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

            def factory():
                return SqlAlchemyUnitOfWork(sessions)

            store = ContentAddressedFilesystemArtifactStore(tmp_path_factory.mktemp("search-cas"))
            p = PlanningFixture(
                engine,
                factory,
                ResearchTaskService(factory, Credentials(), store),
                principal,
                project,
                url,
                store,
            )
            task = p.create()
            bind(p, task)
            approve(p, task, 2)
            env = SimpleNamespace(engine=engine, admin=admin, url=url, p=p, task=task, role=role)
            with engine.begin() as conn:
                env.saved = create_rows(conn, env)
                conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
            yield env
        finally:
            if engine is not None:
                engine.dispose()
            with admin.begin() as conn:
                conn.execute(text(f"DROP OWNED BY {role}"))
                conn.execute(text(f"DROP ROLE IF EXISTS {role}"))
            admin.dispose()


def catalog_snapshot(engine):
    """Independent catalog observer, including full ACLs and trigger attachment flags."""
    queries = {
        "constraints": """SELECT c.conrelid::regclass::text,c.conname,
            pg_get_constraintdef(c.oid) FROM pg_constraint c
            JOIN pg_namespace n ON n.oid=c.connamespace WHERE n.nspname='public'""",
        "indexes": """SELECT tablename,indexname,indexdef FROM pg_indexes
            WHERE schemaname='public'""",
        "functions": """SELECT p.oid::regprocedure::text,pg_get_functiondef(p.oid),p.proacl::text
            FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
            WHERE n.nspname='public' AND p.prokind='f'""",
        "triggers": """SELECT t.tgrelid::regclass::text,t.tgname,
            pg_get_triggerdef(t.oid),t.tgenabled FROM pg_trigger t
            JOIN pg_class r ON r.oid=t.tgrelid JOIN pg_namespace n ON n.oid=r.relnamespace
            WHERE n.nspname='public' AND NOT t.tgisinternal""",
        "columns": """SELECT table_name,column_name,data_type,is_nullable,column_default
            FROM information_schema.columns WHERE table_schema='public'""",
        "privileges": """SELECT r.relname,r.relacl::text FROM pg_class r
            JOIN pg_namespace n ON n.oid=r.relnamespace
            WHERE n.nspname='public' AND r.relkind IN ('r','p')""",
    }
    with engine.connect() as conn:
        return {
            kind: sorted(tuple(row) for row in conn.execute(text(sql)))
            for kind, sql in queries.items()
        }
