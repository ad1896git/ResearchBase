import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from tests.disposable_postgres import disposable_database
from tests.integration.phase2.pr2_20_support import catalog, upgrade
from tests.integration.phase3.intent_fixtures import _intent_env as _intent_env

HEAD = "0081_agent_execution_intents"

# Frozen Q3.2/Q3.3 names, independent of the migration's DDL/constants.
ADDED_CONSTRAINTS = {
    "agent_execution_instances": """
        pr302s2_exec_pk pr302s2_exec_project_fk pr302s2_exec_task_fk
        pr302s2_exec_step_fk pr302s2_exec_version_fk pr302s2_exec_actor_fk
        pr302s2_exec_harness_fk pr302s2_exec_id_ck pr302s2_exec_status_ck
        pr302s2_exec_revision_ck pr302s2_exec_task_revision_ck pr302s2_exec_time_ck
        pr302s2_exec_hashes_ck pr302s2_exec_schemes_ck
    """.split(),
    "agent_execution_events": """
        pr302s2_event_pk pr302s2_event_execution_uq pr302s2_event_receipt_uq
        pr302s2_event_execution_fk pr302s2_event_actor_fk pr302s2_event_receipt_fk
        pr302s2_event_id_ck pr302s2_event_initial_ck pr302s2_event_time_ck
        pr302s2_event_reason_ck
    """.split(),
    "agent_command_receipts": """
        pr302s2_receipt_execution_fk pr302s2_receipt_event_fk
        pr302s2_receipt_operation_ck pr302s2_receipt_shape_ck
    """.split(),
}
# PostgreSQL 18 also catalogs a named NOT NULL constraint for each required column.
NOT_NULL_COLUMNS = {
    "agent_execution_instances": """
        id project_id research_task_id task_revision_at_creation agent_version_id
        actor_id status revision created_at input_ref_hash input_ref_hash_scheme
        harness_artifact_version_id harness_content_hash harness_hash_scheme
    """.split(),
    "agent_execution_events": """
        id execution_id sequence new_status actor_id occurred_at reason receipt_id
    """.split(),
}
ADDED_INDEXES = {
    "agent_execution_instances": """
        pr302s2_exec_pk pr302s2_exec_project_task pr302s2_exec_task_step
        pr302s2_exec_version pr302s2_exec_actor pr302s2_exec_harness
    """.split(),
    "agent_execution_events": """
        pr302s2_event_pk pr302s2_event_execution_uq pr302s2_event_receipt_uq
        pr302s2_event_actor
    """.split(),
    "agent_command_receipts": "pr302s2_receipt_execution_uq pr302s2_receipt_event_uq".split(),
}


def assert_exact_catalog_delta(before, after):
    expected_constraints = {
        (table, name) for table, names in ADDED_CONSTRAINTS.items() for name in names
    } | {
        (table, f"{table}_{column}_not_null")
        for table, columns in NOT_NULL_COLUMNS.items()
        for column in columns
    }
    expected_indexes = {(table, name) for table, names in ADDED_INDEXES.items() for name in names}
    for kind, additions, removals in (
        (
            "constraints",
            expected_constraints,
            {
                ("agent_command_receipts", "agent_command_receipts_operation_check"),
                ("agent_command_receipts", "agent_command_receipts_check"),
            },
        ),
        ("indexes", expected_indexes, set()),
    ):
        old = {(table, name): definition for table, name, definition in before[kind]}
        new = {(table, name): definition for table, name, definition in after[kind]}
        assert sorted(new.keys() - old.keys()) == sorted(additions), kind
        assert sorted(old.keys() - new.keys()) == sorted(removals), kind
        # A correct count/name delta must not hide a changed pre-existing definition.
        assert {key: new[key] for key in old.keys() & new.keys()} == {
            key: old[key] for key in old.keys() & new.keys()
        }, kind


@pytest.mark.parametrize(
    "constraint",
    ["agent_command_receipts_operation_check", "agent_command_receipts_check"],
)
def test_upgrade_refuses_receipt_check_drift(constraint):
    with disposable_database("researchbase_pr212_test_") as url:
        upgrade(url, "0080_capability_gateway")
        engine = create_engine(url)
        try:
            with engine.begin() as conn:
                receipt_checks = text(
                    "SELECT conname,pg_get_constraintdef(oid) FROM pg_constraint "
                    "WHERE conrelid='agent_command_receipts'::regclass AND contype='c'"
                )
                baseline_checks = {
                    name: definition for name, definition in conn.execute(receipt_checks)
                }
                assert constraint in baseline_checks
                conn.execute(
                    text(f"ALTER TABLE agent_command_receipts DROP CONSTRAINT {constraint}")
                )
                conn.execute(
                    text(
                        "ALTER TABLE agent_command_receipts "
                        f"ADD CONSTRAINT {constraint} CHECK (true)"
                    )
                )
                drifted_checks = {
                    name: definition for name, definition in conn.execute(receipt_checks)
                }
                assert drifted_checks == {**baseline_checks, constraint: "CHECK (true)"}
                assert drifted_checks != baseline_checks
            before = catalog(engine)
            # The frozen migration raises a Python diagnostic, not a SQLSTATE.
            with pytest.raises(
                RuntimeError,
                match="^S2 receipt CHECK catalog drift; forward migration refused$",
            ):
                upgrade(url)
            assert catalog(engine) == before
            with engine.connect() as conn:
                assert {
                    name: definition for name, definition in conn.execute(receipt_checks)
                } == drifted_checks
                assert conn.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar_one() == ("0080_capability_gateway")
                assert (
                    conn.execute(text("SELECT count(*) FROM agent_command_receipts")).scalar_one()
                    == 0
                )
                assert (
                    conn.execute(
                        text("SELECT to_regclass('agent_execution_instances')")
                    ).scalar_one()
                    is None
                )
                assert (
                    conn.execute(text("SELECT to_regclass('agent_execution_events')")).scalar_one()
                    is None
                )
        finally:
            engine.dispose()


def test_empty_upgrade_and_single_head():
    scripts = ScriptDirectory.from_config(Config("alembic.ini"))
    assert scripts.get_heads() == [HEAD]
    assert scripts.get_revision(HEAD).down_revision == "0080_capability_gateway"
    with disposable_database("researchbase_pr212_test_") as url:
        upgrade(url, "0080_capability_gateway")
        engine = create_engine(url)
        before = catalog(engine)
        upgrade(url)
        after = catalog(engine)
        assert_exact_catalog_delta(before, after)
        with engine.connect() as conn:
            assert (
                conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == HEAD
            )
            assert (
                conn.execute(text("SELECT count(*) FROM agent_execution_instances")).scalar_one()
                == 0
            )
        import os
        from unittest.mock import patch

        frozen_catalog = catalog(engine)
        with patch.dict(os.environ, {"DATABASE_URL": url}):
            with pytest.raises(RuntimeError, match="forward-only"):
                command.downgrade(Config("alembic.ini"), "0080_capability_gateway")
        assert catalog(engine) == frozen_catalog
        engine.dispose()


def test_populated_upgrade_preserves_history(agents):
    from dataclasses import replace

    from sqlalchemy import inspect
    from tests.integration.phase3.agent_fixtures import enrollment, register

    from researchbase.agent_runtime.application.agent_contracts import ChangeAgentAvailability
    from researchbase.foundation.ids import new_uuid7

    first = enrollment(agents)
    agents.service.execute(first)
    agents.service.execute(register(agents, first.arguments.actor_id))
    owning = create_engine(agents.url)
    tables = [table for table in inspect(owning).get_table_names() if table != "alembic_version"]

    def snapshot():
        result = {}
        with owning.connect() as conn:
            for table in tables:
                projection = (
                    "to_jsonb(t)-'result_execution_id'-'result_execution_event_id'"
                    if table == "agent_command_receipts"
                    else "to_jsonb(t)"
                )
                result[table] = conn.execute(
                    text(
                        f"SELECT COALESCE(jsonb_agg({projection} ORDER BY to_jsonb(t)::text),"
                        f"'[]'::jsonb) FROM {table} t"
                    )
                ).scalar_one()
        return result

    try:
        before = snapshot()
        upgrade(agents.url)
        assert snapshot() == before
        with owning.connect() as conn:
            assert (
                conn.execute(text("SELECT count(*) FROM agent_execution_instances")).scalar_one()
                == 0
            )
        # Exercise all three retained S1 operations against the new function bodies.
        enrolled = enrollment(agents)
        agents.service.execute(enrolled)
        version = register(agents, enrolled.arguments.actor_id)
        agents.service.execute(version)
        changed = replace(
            version,
            command_id=new_uuid7(),
            operation="change_agent_availability",
            expected_revision=1,
            arguments=ChangeAgentAvailability(
                version.arguments.agent_version_id, "DISABLED", "S1 compatibility"
            ),
        )
        assert agents.service.execute(changed).resulting_revision == 2
    finally:
        owning.dispose()


@pytest.mark.parametrize("populated", [False, True])
def test_downgrade_refuses_before_change(intent_env, populated, monkeypatch):
    env = intent_env
    if populated:
        env.intents.execute(env.intent)
    before = catalog(env.owning_engine)
    with env.owning_engine.connect() as conn:
        count = conn.execute(text("SELECT count(*) FROM agent_execution_instances")).scalar_one()
    config = Config("alembic.ini")
    monkeypatch.setenv("DATABASE_URL", env.url)
    with pytest.raises(RuntimeError, match="forward-only"):
        command.downgrade(config, "0080_capability_gateway")
    assert before == catalog(env.owning_engine)
    with env.owning_engine.connect() as conn:
        assert (
            conn.execute(text("SELECT count(*) FROM agent_execution_instances")).scalar_one()
            == count
        )
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == HEAD
