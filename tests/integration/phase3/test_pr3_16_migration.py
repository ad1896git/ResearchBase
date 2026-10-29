"""Forward-only S1 upgrade, exact accepted catalog preservation and drift refusal."""

import re
from contextlib import nullcontext

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from tests.disposable_postgres import disposable_database
from tests.integration.phase2.pr2_20_support import upgrade
from tests.integration.phase3.agent_fixtures import enrollment, register
from tests.integration.phase3.search_fixtures import HEAD, PARENT, TABLES, catalog_snapshot
from tests.integration.phase3.test_pr3_16_schema import CONSTRAINTS, FUNCTIONS, INDEXES

REMOVED_CONSTRAINTS = {
    ("research_task_command_receipts", "pr303_command_names"),
    ("research_task_events", "pr303_event_names"),
    ("research_task_events", "pr303_event_states"),
    ("research_task_events", "pr303_event_reason"),
}


def sql_tokens(sql):
    """Ignore SQL formatting and comments, preserving every literal and operator."""
    return re.findall(r"'(?:''|[^'])*'|\w+|[^\s]", re.sub(r"--[^\n]*", "", sql))


def assert_catalog_delta(before, after):
    for kind, width, additions, removals, changed in (
        (
            "constraints",
            2,
            {(t, n) for t, names in CONSTRAINTS.items() for n in names},
            REMOVED_CONSTRAINTS,
            set(),
        ),
        ("indexes", 2, {(t, n) for t, names in INDEXES.items() for n in names}, set(), set()),
        (
            "triggers",
            2,
            {
                ("experiment_search_sessions", "pr316_session_insert"),
                ("experiment_search_sessions", "pr316_session_immutable"),
                ("experiment_search_sessions", "pr316_session_complete"),
                ("experiment_search_sessions", "pr316_session_no_truncate"),
                ("experiment_search_nodes", "pr316_node_insert"),
                ("experiment_search_nodes", "pr316_node_immutable"),
                ("experiment_search_nodes", "pr316_node_complete"),
                ("experiment_search_nodes", "pr316_node_no_truncate"),
                ("experiment_search_node_runs", "pr316_link_insert_disabled"),
                ("experiment_search_node_runs", "pr316_link_immutable"),
                ("experiment_search_node_runs", "pr316_link_no_truncate"),
                ("experiment_search_events", "pr316_event_insert"),
                ("experiment_search_events", "pr316_event_immutable"),
                ("experiment_search_events", "pr316_event_complete"),
                ("experiment_search_events", "pr316_event_no_truncate"),
                ("research_task_command_receipts", "pr316_receipt_insert"),
            },
            set(),
            set(),
        ),
    ):
        old = {r[:width]: r[width:] for r in before[kind]}
        new = {r[:width]: r[width:] for r in after[kind]}
        assert new.keys() - old.keys() == additions, kind
        assert old.keys() - new.keys() == removals, kind
        assert {k for k in old.keys() & new.keys() if old[k] != new[k]} == changed, kind
    old_functions = {r[0]: r[1:] for r in before["functions"]}
    new_functions = {r[0]: r[1:] for r in after["functions"]}
    assert not old_functions.keys() - new_functions.keys()
    assert {name.split("(")[0] for name in new_functions.keys() - old_functions.keys()} == (
        set(FUNCTIONS)
    )
    assert len(new_functions) - len(old_functions) == 16
    assert {name for name in old_functions if old_functions[name] != new_functions[name]} == {
        "pr301_receipt_complete()"
    }
    original, acl = old_functions["pr301_receipt_complete()"]
    replacement, new_acl = new_functions["pr301_receipt_complete()"]
    assert acl == new_acl
    replacement = replacement.replace(
        "WHEN 'create_search_session' THEN 'SEARCH_SESSION_CREATED'", ""
    ).replace("WHEN 'append_search_node' THEN 'SEARCH_NODE_APPENDED'", "")
    replacement = re.sub(r"PERFORM pr316_validate_receipt\(r.id\);", "", replacement)
    assert sql_tokens(original) == sql_tokens(replacement)
    old_columns = {r[:2]: r[2:] for r in before["columns"]}
    new_columns = {r[:2]: r[2:] for r in after["columns"]}
    assert {k: new_columns[k] for k in old_columns} == old_columns
    assert {k for k in new_columns.keys() - old_columns.keys() if k[0] not in TABLES} == {
        ("research_task_command_receipts", "result_search_session_id"),
        ("research_task_command_receipts", "result_search_node_id"),
        ("research_task_command_receipts", "result_search_event_id"),
    }
    assert {r[0] for r in after["privileges"]} - {r[0] for r in before["privileges"]} == set(TABLES)
    assert {r for r in after["privileges"] if r[0] not in TABLES} == set(before["privileges"])


def row_snapshot(engine, tables):
    with engine.connect() as conn:
        return {
            table: conn.execute(
                text(
                    "SELECT coalesce(jsonb_agg("
                    + (
                        "to_jsonb(t)-'result_search_session_id'-'result_search_node_id'"
                        "-'result_search_event_id'"
                        if table == "research_task_command_receipts"
                        else "to_jsonb(t)"
                    )
                    + f" ORDER BY to_jsonb(t)::text),'[]'::jsonb) FROM {table} t"
                )
            ).scalar_one()
            for table in tables
        }


@pytest.mark.parametrize("populated", [False, True])
def test_clean_and_populated_upgrade_preserve_accepted_rows(agents, populated):
    if populated:
        enrolled = enrollment(agents)
        agents.service.execute(enrolled)
        agents.service.execute(register(agents, enrolled.arguments.actor_id))
    context = (
        nullcontext(agents.url) if populated else disposable_database("researchbase_pr212_test_")
    )
    with context as url:
        upgrade(url, PARENT)
        planning = None
        if populated:
            from tests.integration.phase3.conftest import PlanningFixture
            from tests.integration.phase3.test_pr3_04_application import approve, bind

            from researchbase.agent_runtime.application.research_task import ResearchTaskService

            # As in the accepted gateway fixture, extend the disposable role's
            # table grants after migrating its 0079 database to the 0081 subject.
            with agents.engine.connect() as conn:
                role = conn.execute(text("SELECT current_user")).scalar_one()
            grant_engine = create_engine(url)
            try:
                with grant_engine.begin() as conn:
                    conn.execute(
                        text(
                            "GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public "
                            f"TO {role}"
                        )
                    )
            finally:
                grant_engine.dispose()
            planning = PlanningFixture(
                agents.engine,
                agents.factory,
                ResearchTaskService(agents.factory, agents.credentials, agents.store),
                agents.owner,
                agents.project,
                url,
                agents.store,
            )
            task, _ = planning.plan()
            bind(planning, task, revision=2)
            approve(planning, task, 3)
            planning.service.execute(
                planning.principal, planning.command("seal_task_plan", task, 5)
            )
        engine = create_engine(url)
        try:
            tables = [t for t in inspect(engine).get_table_names() if t != "alembic_version"]
            rows = row_snapshot(engine, tables)
            if populated:
                assert len(rows["research_tasks"]) == 1
                assert len(rows["research_task_steps"]) == 2
                assert len(rows["research_task_command_receipts"]) == 6
                assert rows["execution_budgets"] and rows["human_checkpoints"]
            before = catalog_snapshot(engine)
            upgrade(url, HEAD)
            assert row_snapshot(engine, tables) == rows
            assert_catalog_delta(before, catalog_snapshot(engine))
            with engine.connect() as conn:
                assert (
                    conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                    == HEAD
                )
                assert all(
                    conn.execute(text(f"SELECT count(*) FROM {t}")).scalar_one() == 0
                    for t in TABLES
                )
            if populated:
                # Reconnect across additive receipt-column DDL: psycopg prepared
                # SELECT * results retain the pre-upgrade row type until reconnect.
                agents.engine.dispose()
                # Retained guards execute, rather than relying on catalog comparison alone.
                another = enrollment(agents)
                agents.service.execute(another)
                agents.service.execute(register(agents, another.arguments.actor_id))
                assert planning is not None

                # Legacy commands must work with their original grants only.
                # Granting SELECT on new tables here would mask a guard regression.
                def has_search_select():
                    with engine.connect() as conn:
                        return [
                            conn.execute(
                                text("SELECT has_table_privilege(:role, :table, 'SELECT')"),
                                {"role": role, "table": f"public.{table}"},
                            ).scalar_one()
                            for table in TABLES
                        ]

                assert not any(has_search_select())
                created = planning.create()
                assert created is not None
                assert not any(has_search_select())
        finally:
            engine.dispose()


def test_forward_only_migration_and_single_head(monkeypatch):
    scripts = ScriptDirectory.from_config(Config("alembic.ini"))
    assert scripts.get_heads() == ["0083_bearing_evaluation_guards"]
    assert scripts.get_revision("0083_bearing_evaluation_guards").down_revision == HEAD
    assert scripts.get_revision(HEAD).down_revision == PARENT
    with disposable_database("researchbase_pr212_test_") as url:
        upgrade(url, HEAD)
        engine = create_engine(url)
        try:
            before = catalog_snapshot(engine)
            monkeypatch.setenv("DATABASE_URL", url)
            with pytest.raises(RuntimeError, match="0082 is forward-only"):
                command.downgrade(Config("alembic.ini"), PARENT)
            assert catalog_snapshot(engine) == before
            with engine.connect() as conn:
                assert (
                    conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                    == HEAD
                )
        finally:
            engine.dispose()


@pytest.mark.parametrize(
    "drift",
    [
        "ALTER TABLE research_task_command_receipts DROP CONSTRAINT pr303_command_names",
        "ALTER FUNCTION pr302_receipt_guard() SET search_path=public",
        "ALTER TABLE runs ADD COLUMN unexpected_search_pointer uuid",
        "CREATE TABLE experiment_search_sessions(id uuid)",
        "CREATE FUNCTION pr316_surprise() RETURNS integer LANGUAGE sql AS 'SELECT 1'",
        "ALTER TABLE research_task_events DISABLE TRIGGER pr301_task_event_insert",
        "CREATE TYPE pr316_unexpected AS ENUM ('UNEXPECTED')",
        "DROP INDEX pr302s2_exec_actor",
        "REVOKE EXECUTE ON FUNCTION pr302_receipt_guard() FROM PUBLIC",
    ],
)
def test_preflight_refuses_catalog_drift_before_any_change(drift):
    with disposable_database("researchbase_pr212_test_") as url:
        upgrade(url, PARENT)
        engine = create_engine(url)
        try:
            with engine.begin() as conn:
                conn.execute(text(drift))
            before = catalog_snapshot(engine)
            with pytest.raises(RuntimeError, match="0082 accepted 0081 catalog drift"):
                upgrade(url, HEAD)
            assert catalog_snapshot(engine) == before
            with engine.connect() as conn:
                assert (
                    conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                    == PARENT
                )
        finally:
            engine.dispose()
