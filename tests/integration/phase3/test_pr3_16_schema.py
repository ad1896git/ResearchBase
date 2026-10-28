"""Frozen four-table catalog and hostile SQL tests; all guards remain enabled."""

import re
from pathlib import Path
from typing import Any, cast

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from tests.integration.phase3.search_fixtures import (
    TABLES,
    catalog_snapshot,
    create_rows,
    insert,
)
from tests.integration.phase3.search_fixtures import (
    _search_env as _search_env,
)

from researchbase.foundation.ids import new_uuid7

# Independent inventory transcribed from the admitted SQL, including PG18 NOT NULL names.
COLUMNS = {
    "experiment_search_events": [
        ("id", "uuid", False),
        ("research_task_id", "uuid", False),
        ("search_session_id", "uuid", False),
        ("node_id", "uuid", True),
        ("sequence", "integer", False),
        ("event_type", "text", False),
        ("reason", "text", False),
        ("actor_id", "uuid", False),
        ("occurred_at", "timestamp with time zone", False),
        ("receipt_id", "uuid", False),
    ],
    "experiment_search_node_runs": [
        ("id", "uuid", False),
        ("project_id", "uuid", False),
        ("research_task_id", "uuid", False),
        ("search_session_id", "uuid", False),
        ("node_id", "uuid", False),
        ("run_id", "uuid", False),
        ("created_by", "uuid", False),
        ("created_at", "timestamp with time zone", False),
        ("receipt_id", "uuid", False),
    ],
    "experiment_search_nodes": [
        ("id", "uuid", False),
        ("research_task_id", "uuid", False),
        ("search_session_id", "uuid", False),
        ("parent_node_id", "uuid", True),
        ("depth", "integer", False),
        ("branch_kind", "text", False),
        ("mutation_reason", "text", False),
        ("hypothesis_version_id", "uuid", True),
        ("hypothesis_content_hash", "text", True),
        ("experiment_spec_version_id", "uuid", True),
        ("experiment_spec_content_hash", "text", True),
        ("reservation_id", "uuid", False),
        ("created_by", "uuid", False),
        ("created_at", "timestamp with time zone", False),
        ("receipt_id", "uuid", False),
    ],
    "experiment_search_sessions": [
        ("id", "uuid", False),
        ("project_id", "uuid", False),
        ("research_task_id", "uuid", False),
        ("budget_id", "uuid", False),
        ("root_hypothesis_version_id", "uuid", True),
        ("root_hypothesis_content_hash", "text", True),
        ("root_experiment_spec_version_id", "uuid", True),
        ("root_experiment_spec_content_hash", "text", True),
        ("created_by", "uuid", False),
        ("created_at", "timestamp with time zone", False),
        ("receipt_id", "uuid", False),
    ],
}

CONSTRAINTS = {
    "experiment_search_events": [
        "pr316_event_pk",
        "pr316_event_id_ck",
        "pr316_event_time_ck",
        "pr316_event_receipt_uq",
        "pr316_event_actor_fk",
        "pr316_event_receipt_fk",
        "pr316_event_scope_uq",
        "pr316_event_sequence_uq",
        "pr316_event_sequence_ck",
        "pr316_event_kind_ck",
        "pr316_event_reason_ck",
        "pr316_event_shape_ck",
        "pr316_event_session_fk",
        "pr316_event_node_fk",
        "pr316_event_id_nn",
        "pr316_event_research_task_id_nn",
        "pr316_event_search_session_id_nn",
        "pr316_event_sequence_nn",
        "pr316_event_event_type_nn",
        "pr316_event_reason_nn",
        "pr316_event_actor_id_nn",
        "pr316_event_occurred_at_nn",
        "pr316_event_receipt_id_nn",
    ],
    "experiment_search_node_runs": [
        "pr316_link_pk",
        "pr316_link_id_ck",
        "pr316_link_time_ck",
        "pr316_link_receipt_uq",
        "pr316_link_actor_fk",
        "pr316_link_receipt_fk",
        "pr316_link_scope_uq",
        "pr316_link_pair_uq",
        "pr316_link_session_fk",
        "pr316_link_node_fk",
        "pr316_link_run_fk",
        "pr316_link_id_nn",
        "pr316_link_project_id_nn",
        "pr316_link_research_task_id_nn",
        "pr316_link_search_session_id_nn",
        "pr316_link_node_id_nn",
        "pr316_link_run_id_nn",
        "pr316_link_created_by_nn",
        "pr316_link_created_at_nn",
        "pr316_link_receipt_id_nn",
    ],
    "experiment_search_nodes": [
        "pr316_node_pk",
        "pr316_node_id_ck",
        "pr316_node_time_ck",
        "pr316_node_receipt_uq",
        "pr316_node_actor_fk",
        "pr316_node_receipt_fk",
        "pr316_node_scope_uq",
        "pr316_node_session_fk",
        "pr316_node_parent_fk",
        "pr316_node_reservation_fk",
        "pr316_node_reservation_uq",
        "pr316_node_depth_ck",
        "pr316_node_branch_ck",
        "pr316_node_reason_ck",
        "pr316_node_hypothesis_fk",
        "pr316_node_hypothesis_pair_ck",
        "pr316_node_experiment_spec_fk",
        "pr316_node_experiment_spec_pair_ck",
        "pr316_node_id_nn",
        "pr316_node_research_task_id_nn",
        "pr316_node_search_session_id_nn",
        "pr316_node_depth_nn",
        "pr316_node_branch_kind_nn",
        "pr316_node_mutation_reason_nn",
        "pr316_node_reservation_id_nn",
        "pr316_node_created_by_nn",
        "pr316_node_created_at_nn",
        "pr316_node_receipt_id_nn",
    ],
    "experiment_search_sessions": [
        "pr316_session_pk",
        "pr316_session_id_ck",
        "pr316_session_time_ck",
        "pr316_session_receipt_uq",
        "pr316_session_actor_fk",
        "pr316_session_receipt_fk",
        "pr316_session_scope_uq",
        "pr316_session_project_uq",
        "pr316_session_task_fk",
        "pr316_session_budget_fk",
        "pr316_session_hypothesis_fk",
        "pr316_session_hypothesis_pair_ck",
        "pr316_session_experiment_spec_fk",
        "pr316_session_experiment_spec_pair_ck",
        "pr316_session_id_nn",
        "pr316_session_project_id_nn",
        "pr316_session_research_task_id_nn",
        "pr316_session_budget_id_nn",
        "pr316_session_created_by_nn",
        "pr316_session_created_at_nn",
        "pr316_session_receipt_id_nn",
    ],
    "research_task_command_receipts": [
        "pr316_command_names",
        "pr316_receipt_session_fk",
        "pr316_receipt_node_fk",
        "pr316_receipt_event_fk",
        "pr316_receipt_shape_ck",
    ],
    "research_task_events": [
        "pr316_task_event_names",
        "pr316_task_event_states",
        "pr316_task_event_reason",
    ],
    "runs": ["pr316_run_project_uq"],
}

INDEXES = {
    "experiment_search_events": [
        "pr316_event_pk",
        "pr316_event_receipt_uq",
        "pr316_event_scope_uq",
        "pr316_event_sequence_uq",
        "pr316_event_one_creation",
        "pr316_event_one_node_creation",
        "pr316_event_node",
        "pr316_event_actor",
        "pr316_event_receipt",
    ],
    "experiment_search_node_runs": [
        "pr316_link_pk",
        "pr316_link_receipt_uq",
        "pr316_link_scope_uq",
        "pr316_link_pair_uq",
        "pr316_link_session_project",
        "pr316_link_run",
        "pr316_link_order",
        "pr316_link_actor",
        "pr316_link_receipt",
    ],
    "experiment_search_nodes": [
        "pr316_node_pk",
        "pr316_node_receipt_uq",
        "pr316_node_scope_uq",
        "pr316_node_reservation_uq",
        "pr316_node_one_root",
        "pr316_node_parent",
        "pr316_node_order",
        "pr316_node_hypothesis",
        "pr316_node_spec",
        "pr316_node_reservation",
        "pr316_node_actor",
        "pr316_node_receipt",
    ],
    "experiment_search_sessions": [
        "pr316_session_pk",
        "pr316_session_receipt_uq",
        "pr316_session_scope_uq",
        "pr316_session_project_uq",
        "pr316_session_task_project",
        "pr316_session_budget",
        "pr316_session_project",
        "pr316_session_hypothesis",
        "pr316_session_spec",
        "pr316_session_actor",
        "pr316_session_receipt",
    ],
    "research_task_command_receipts": [
        "pr316_receipt_session",
        "pr316_receipt_node",
        "pr316_receipt_event_scope",
        "pr316_receipt_event_uq",
    ],
    "runs": ["pr316_run_project_uq"],
}

FUNCTIONS = [
    "pr316_uuid7",
    "pr316_reason",
    "pr316_command_event",
    "pr316_immutable",
    "pr316_preheld",
    "pr316_live",
    "pr316_receipt_insert",
    "pr316_refs",
    "pr316_chain",
    "pr316_admission",
    "pr316_node_proof",
    "pr316_state",
    "pr316_link_write_disabled",
    "pr316_lineage_insert",
    "pr316_validate_receipt",
    "pr316_effect_complete",
]


for _table, _name in (
    ("experiment_search_sessions", "pr316_session_complete"),
    ("experiment_search_nodes", "pr316_node_complete"),
    ("experiment_search_events", "pr316_event_complete"),
):
    CONSTRAINTS[_table].append(_name)


def error_constraint(error):
    return cast(Any, error.value.orig).diag.constraint_name


def test_all_frozen_sql_definitions_compile_on_pg18(search_env):
    with search_env.engine.connect() as conn:
        assert int(conn.execute(text("SHOW server_version_num")).scalar_one()) // 10000 == 18
        names = set(
            conn.execute(text("SELECT proname FROM pg_proc WHERE proname LIKE 'pr316_%'")).scalars()
        )
        assert names == set(FUNCTIONS)
        assert len(names) == 16
        triggers = conn.execute(
            text("""
            SELECT tgname,tgenabled,pg_get_triggerdef(oid) FROM pg_trigger
            WHERE tgname LIKE 'pr316_%' ORDER BY tgname
        """)
        ).all()
        expected = set(
            re.findall(
                r"CREATE (?:CONSTRAINT )?TRIGGER (pr316_\w+)",
                Path("docs/phase3/design/PR3-16-ddl-guards-events.md").read_text(),
            )
        )
        assert {row[0] for row in triggers} == expected
        assert len(triggers) == 16
        assert all(enabled == "O" for _, enabled, _ in triggers)
        for name, _, definition in triggers:
            assert ("DEFERRABLE INITIALLY DEFERRED" in definition) == name.endswith("_complete")
        assert conn.execute(text("SHOW check_function_bodies")).scalar_one() == "on"


def test_frozen_columns_keys_indexes_and_no_json_or_cascade(search_env):
    catalog = catalog_snapshot(search_env.engine)
    actual_columns = {
        table: [
            (column, kind, nullable == "YES")
            for t, column, kind, nullable, _ in catalog["columns"]
            if t == table
        ]
        for table in TABLES
    }
    assert actual_columns == {table: sorted(columns) for table, columns in COLUMNS.items()}
    assert all(default is None for table, _, _, _, default in catalog["columns"] if table in TABLES)
    actual_constraints = {
        (table, name) for table, name, _ in catalog["constraints"] if name.startswith("pr316_")
    }
    assert actual_constraints == {
        (table, name) for table, names in CONSTRAINTS.items() for name in names
    }
    assert {(t, n) for t, n, _ in catalog["indexes"] if n.startswith("pr316_")} == {
        (table, name) for table, names in INDEXES.items() for name in names
    }
    with search_env.engine.connect() as conn:
        fks = conn.execute(
            text("""
            SELECT conname,confdeltype,confupdtype,confmatchtype,condeferrable,condeferred
            FROM pg_constraint WHERE conname LIKE 'pr316_%' AND contype='f'
        """)
        ).all()
        assert len(fks) == 25
        for name, delete, update, match, deferred, initially in fks:
            assert (delete, update, match) == ("r", "a", "s")
            assert deferred == initially == name.startswith("pr316_receipt_")
        assert not conn.execute(
            text("""
            SELECT 1 FROM information_schema.columns WHERE table_schema='public'
            AND table_name LIKE 'experiment_search_%' AND data_type IN ('json','jsonb')
        """)
        ).all()


def test_no_strategy_column(search_env):
    with search_env.engine.connect() as conn:
        names = set(
            conn.execute(
                text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema='public' AND table_name LIKE 'experiment_search_%'
        """)
            ).scalars()
        )
        assert not names & {
            "strategy_id",
            "strategy_version",
            "objective_definition",
            "objective_hash",
            "status",
            "score",
            "trusted",
            "agent_version_id",
        }


def test_ordinary_role_create_has_exact_receipt_task_event_and_effects(search_env):
    env = search_env
    with env.engine.connect() as conn:
        assert conn.execute(
            text("""
            SELECT NOT rolsuper AND NOT rolbypassrls FROM pg_roles WHERE rolname=current_user
        """)
        ).scalar_one()
        saved = create_rows(conn, env)
        conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        for table, expected in (
            ("experiment_search_sessions", 1),
            ("experiment_search_nodes", 0),
            ("experiment_search_node_runs", 0),
            ("experiment_search_events", 1),
            ("research_task_receipt_events", 1),
            ("research_task_receipt_step_events", 0),
            ("execution_budgets", 0),
            ("budget_reservations", 0),
            ("budget_usage_records", 0),
        ):
            assert (
                conn.execute(
                    text(f"SELECT count(*) FROM {table} WHERE receipt_id=:id"),
                    {"id": saved.receipt},
                ).scalar_one()
                == expected
            )
        assert (
            conn.execute(
                text("""
            SELECT count(*) FROM research_task_events WHERE id=:id
            AND event_type='SEARCH_SESSION_CREATED'
        """),
                {"id": saved.task_event},
            ).scalar_one()
            == 1
        )
        conn.rollback()


@pytest.mark.parametrize("omit", ["session", "event", "task_event"])
def test_incomplete_effect_set_cannot_commit(search_env, omit):
    with search_env.engine.connect() as conn:
        with pytest.raises(DBAPIError):
            create_rows(conn, search_env, omit=omit)
            conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        conn.rollback()


def test_wrong_v1_digest_rejected_at_forced_constraints(search_env):
    with search_env.engine.connect() as conn:
        create_rows(conn, search_env, bad_hash=True)
        with pytest.raises(DBAPIError) as exc:
            conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        assert error_constraint(exc) == "pr316_provenance"
        conn.rollback()


@pytest.mark.parametrize("missing", ["pr301:command:", "pr301:task:"])
def test_missing_preheld_common_key_denied(search_env, missing):
    with search_env.engine.connect() as conn:
        with pytest.raises(DBAPIError):
            create_rows(conn, search_env, missing=missing)
            conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        conn.rollback()


@pytest.mark.parametrize("table", ["experiment_search_sessions", "experiment_search_events"])
@pytest.mark.parametrize("operation", ["UPDATE", "DELETE"])
def test_ordinary_role_noop_and_delete_rejected(search_env, table, operation):
    with search_env.engine.connect() as conn:
        sql = f"UPDATE {table} SET id=id" if operation == "UPDATE" else f"DELETE FROM {table}"
        with pytest.raises(DBAPIError) as exc:
            conn.execute(text(sql))
        assert error_constraint(exc) == "pr316_immutable"
        conn.rollback()


def test_truncate_rejected_even_with_accidental_privilege(search_env):
    with search_env.admin.begin() as conn:
        conn.execute(text(f"GRANT TRUNCATE ON ALL TABLES IN SCHEMA public TO {search_env.role}"))
    with search_env.engine.connect() as conn:
        with pytest.raises(DBAPIError) as exc:
            conn.execute(text("TRUNCATE experiment_search_events CASCADE"))
        assert error_constraint(exc) == "pr316_immutable"
        conn.rollback()


def test_no_run_link_writer_even_with_forged_trust_flag(search_env):
    with search_env.engine.connect() as conn:
        conn.execute(text("SELECT set_config('researchbase.trusted_consumer','true',true)"))
        with pytest.raises(DBAPIError) as exc:
            insert(conn, "experiment_search_node_runs", dict(id=new_uuid7()))
        assert error_constraint(exc) == "pr316_no_link_writer"
        conn.rollback()


def test_node_activation_denied_without_committed_proof(search_env):
    with search_env.engine.connect() as conn:
        conn.execute(text("SELECT set_config('researchbase.trusted_consumer','true',true)"))
        with pytest.raises(DBAPIError) as exc:
            conn.execute(
                text("""
                SELECT pr316_node_proof(jsonb_populate_record(NULL::experiment_search_nodes,
                jsonb_build_object('id',CAST(:id AS text),'research_task_id',CAST(:task AS text),
                'search_session_id',CAST(:session AS text),'reservation_id',CAST(:r AS text),
                'depth',0)))
            """),
                dict(
                    id=new_uuid7(),
                    task=search_env.task,
                    session=search_env.saved.session,
                    r=new_uuid7(),
                ),
            )
        assert error_constraint(exc) == "pr316_state"
        conn.rollback()
    # The admitted guard has an unconditional final activation denial, with no GUC branch.
    with search_env.engine.connect() as conn:
        source = conn.execute(text("SELECT prosrc FROM pg_proc WHERE proname='pr316_node_proof'"))
        body = source.scalar_one()
        assert re.search(r"CONSTRAINT\s*=\s*'pr316_activation'", body)
        assert "current_setting" not in body


def test_committed_receipt_cannot_acquire_new_search_effects(search_env):
    with search_env.engine.connect() as conn:
        with pytest.raises(DBAPIError) as exc:
            insert(
                conn,
                "experiment_search_sessions",
                dict(
                    id=new_uuid7(),
                    research_task_id=search_env.task,
                    receipt_id=search_env.saved.receipt,
                ),
            )
        assert error_constraint(exc) == "pr316_completeness"
        conn.rollback()


FK_SHAPES = [
    ("experiment_search_events", "pr316_event_actor_fk", ("actor_id",), "actors", ("id",)),
    (
        "experiment_search_events",
        "pr316_event_node_fk",
        ("research_task_id", "search_session_id", "node_id"),
        "experiment_search_nodes",
        ("research_task_id", "search_session_id", "id"),
    ),
    (
        "experiment_search_events",
        "pr316_event_receipt_fk",
        ("research_task_id", "receipt_id"),
        "research_task_command_receipts",
        ("research_task_id", "id"),
    ),
    (
        "experiment_search_events",
        "pr316_event_session_fk",
        ("research_task_id", "search_session_id"),
        "experiment_search_sessions",
        ("research_task_id", "id"),
    ),
    ("experiment_search_node_runs", "pr316_link_actor_fk", ("created_by",), "actors", ("id",)),
    (
        "experiment_search_node_runs",
        "pr316_link_node_fk",
        ("research_task_id", "search_session_id", "node_id"),
        "experiment_search_nodes",
        ("research_task_id", "search_session_id", "id"),
    ),
    (
        "experiment_search_node_runs",
        "pr316_link_receipt_fk",
        ("research_task_id", "receipt_id"),
        "research_task_command_receipts",
        ("research_task_id", "id"),
    ),
    (
        "experiment_search_node_runs",
        "pr316_link_run_fk",
        ("run_id", "project_id"),
        "runs",
        ("id", "project_id"),
    ),
    (
        "experiment_search_node_runs",
        "pr316_link_session_fk",
        ("research_task_id", "project_id", "search_session_id"),
        "experiment_search_sessions",
        ("research_task_id", "project_id", "id"),
    ),
    ("experiment_search_nodes", "pr316_node_actor_fk", ("created_by",), "actors", ("id",)),
    (
        "experiment_search_nodes",
        "pr316_node_experiment_spec_fk",
        ("experiment_spec_version_id",),
        "experiment_spec_versions",
        ("id",),
    ),
    (
        "experiment_search_nodes",
        "pr316_node_hypothesis_fk",
        ("hypothesis_version_id",),
        "hypothesis_versions",
        ("id",),
    ),
    (
        "experiment_search_nodes",
        "pr316_node_parent_fk",
        ("research_task_id", "search_session_id", "parent_node_id"),
        "experiment_search_nodes",
        ("research_task_id", "search_session_id", "id"),
    ),
    (
        "experiment_search_nodes",
        "pr316_node_receipt_fk",
        ("research_task_id", "receipt_id"),
        "research_task_command_receipts",
        ("research_task_id", "id"),
    ),
    (
        "experiment_search_nodes",
        "pr316_node_reservation_fk",
        ("research_task_id", "reservation_id", "id"),
        "budget_reservations",
        ("research_task_id", "id", "operation_id"),
    ),
    (
        "experiment_search_nodes",
        "pr316_node_session_fk",
        ("research_task_id", "search_session_id"),
        "experiment_search_sessions",
        ("research_task_id", "id"),
    ),
    ("experiment_search_sessions", "pr316_session_actor_fk", ("created_by",), "actors", ("id",)),
    (
        "experiment_search_sessions",
        "pr316_session_budget_fk",
        ("research_task_id", "budget_id"),
        "execution_budgets",
        ("research_task_id", "id"),
    ),
    (
        "experiment_search_sessions",
        "pr316_session_experiment_spec_fk",
        ("root_experiment_spec_version_id",),
        "experiment_spec_versions",
        ("id",),
    ),
    (
        "experiment_search_sessions",
        "pr316_session_hypothesis_fk",
        ("root_hypothesis_version_id",),
        "hypothesis_versions",
        ("id",),
    ),
    (
        "experiment_search_sessions",
        "pr316_session_receipt_fk",
        ("research_task_id", "receipt_id"),
        "research_task_command_receipts",
        ("research_task_id", "id"),
    ),
    (
        "experiment_search_sessions",
        "pr316_session_task_fk",
        ("research_task_id", "project_id"),
        "research_tasks",
        ("id", "project_id"),
    ),
    (
        "research_task_command_receipts",
        "pr316_receipt_event_fk",
        ("research_task_id", "result_search_session_id", "result_search_event_id"),
        "experiment_search_events",
        ("research_task_id", "search_session_id", "id"),
    ),
    (
        "research_task_command_receipts",
        "pr316_receipt_node_fk",
        ("research_task_id", "result_search_session_id", "result_search_node_id"),
        "experiment_search_nodes",
        ("research_task_id", "search_session_id", "id"),
    ),
    (
        "research_task_command_receipts",
        "pr316_receipt_session_fk",
        ("research_task_id", "project_id", "result_search_session_id"),
        "experiment_search_sessions",
        ("research_task_id", "project_id", "id"),
    ),
]

INDEX_SHAPES = [
    ("experiment_search_events", "pr316_event_actor", False, ("actor_id",), None),
    (
        "experiment_search_events",
        "pr316_event_node",
        False,
        ("research_task_id", "search_session_id", "node_id"),
        None,
    ),
    (
        "experiment_search_events",
        "pr316_event_one_creation",
        True,
        ("search_session_id",),
        "event_type='SESSION_CREATED'",
    ),
    (
        "experiment_search_events",
        "pr316_event_one_node_creation",
        True,
        ("node_id",),
        "event_type='NODE_APPENDED'",
    ),
    ("experiment_search_events", "pr316_event_pk", True, ("id",), None),
    (
        "experiment_search_events",
        "pr316_event_receipt",
        False,
        ("research_task_id", "receipt_id"),
        None,
    ),
    ("experiment_search_events", "pr316_event_receipt_uq", True, ("receipt_id",), None),
    (
        "experiment_search_events",
        "pr316_event_scope_uq",
        True,
        ("research_task_id", "search_session_id", "id"),
        None,
    ),
    (
        "experiment_search_events",
        "pr316_event_sequence_uq",
        True,
        ("search_session_id", "sequence"),
        None,
    ),
    ("experiment_search_node_runs", "pr316_link_actor", False, ("created_by",), None),
    ("experiment_search_node_runs", "pr316_link_order", False, ("node_id", "id"), None),
    (
        "experiment_search_node_runs",
        "pr316_link_pair_uq",
        True,
        ("search_session_id", "node_id", "run_id"),
        None,
    ),
    ("experiment_search_node_runs", "pr316_link_pk", True, ("id",), None),
    (
        "experiment_search_node_runs",
        "pr316_link_receipt",
        False,
        ("research_task_id", "receipt_id"),
        None,
    ),
    ("experiment_search_node_runs", "pr316_link_receipt_uq", True, ("receipt_id",), None),
    ("experiment_search_node_runs", "pr316_link_run", False, ("run_id", "project_id"), None),
    (
        "experiment_search_node_runs",
        "pr316_link_scope_uq",
        True,
        ("research_task_id", "search_session_id", "node_id", "id"),
        None,
    ),
    (
        "experiment_search_node_runs",
        "pr316_link_session_project",
        False,
        ("research_task_id", "project_id", "search_session_id"),
        None,
    ),
    ("experiment_search_nodes", "pr316_node_actor", False, ("created_by",), None),
    ("experiment_search_nodes", "pr316_node_hypothesis", False, ("hypothesis_version_id",), None),
    (
        "experiment_search_nodes",
        "pr316_node_one_root",
        True,
        ("search_session_id",),
        "parent_node_id IS NULL",
    ),
    (
        "experiment_search_nodes",
        "pr316_node_order",
        False,
        ("search_session_id", "depth", "id"),
        None,
    ),
    (
        "experiment_search_nodes",
        "pr316_node_parent",
        False,
        ("research_task_id", "search_session_id", "parent_node_id"),
        None,
    ),
    ("experiment_search_nodes", "pr316_node_pk", True, ("id",), None),
    (
        "experiment_search_nodes",
        "pr316_node_receipt",
        False,
        ("research_task_id", "receipt_id"),
        None,
    ),
    ("experiment_search_nodes", "pr316_node_receipt_uq", True, ("receipt_id",), None),
    (
        "experiment_search_nodes",
        "pr316_node_reservation",
        False,
        ("research_task_id", "reservation_id", "id"),
        None,
    ),
    ("experiment_search_nodes", "pr316_node_reservation_uq", True, ("reservation_id",), None),
    (
        "experiment_search_nodes",
        "pr316_node_scope_uq",
        True,
        ("research_task_id", "search_session_id", "id"),
        None,
    ),
    ("experiment_search_nodes", "pr316_node_spec", False, ("experiment_spec_version_id",), None),
    ("experiment_search_sessions", "pr316_session_actor", False, ("created_by",), None),
    (
        "experiment_search_sessions",
        "pr316_session_budget",
        False,
        ("research_task_id", "budget_id"),
        None,
    ),
    (
        "experiment_search_sessions",
        "pr316_session_hypothesis",
        False,
        ("root_hypothesis_version_id",),
        None,
    ),
    ("experiment_search_sessions", "pr316_session_pk", True, ("id",), None),
    ("experiment_search_sessions", "pr316_session_project", False, ("project_id", "id"), None),
    (
        "experiment_search_sessions",
        "pr316_session_project_uq",
        True,
        ("research_task_id", "project_id", "id"),
        None,
    ),
    (
        "experiment_search_sessions",
        "pr316_session_receipt",
        False,
        ("research_task_id", "receipt_id"),
        None,
    ),
    ("experiment_search_sessions", "pr316_session_receipt_uq", True, ("receipt_id",), None),
    (
        "experiment_search_sessions",
        "pr316_session_scope_uq",
        True,
        ("research_task_id", "id"),
        None,
    ),
    (
        "experiment_search_sessions",
        "pr316_session_spec",
        False,
        ("root_experiment_spec_version_id",),
        None,
    ),
    (
        "experiment_search_sessions",
        "pr316_session_task_project",
        False,
        ("research_task_id", "project_id"),
        None,
    ),
    (
        "research_task_command_receipts",
        "pr316_receipt_event_scope",
        False,
        ("research_task_id", "result_search_session_id", "result_search_event_id"),
        None,
    ),
    (
        "research_task_command_receipts",
        "pr316_receipt_event_uq",
        True,
        ("result_search_event_id",),
        "result_search_event_id IS NOT NULL",
    ),
    (
        "research_task_command_receipts",
        "pr316_receipt_node",
        False,
        ("research_task_id", "result_search_session_id", "result_search_node_id"),
        None,
    ),
    (
        "research_task_command_receipts",
        "pr316_receipt_session",
        False,
        ("research_task_id", "project_id", "result_search_session_id"),
        None,
    ),
    ("runs", "pr316_run_project_uq", True, ("id", "project_id"), None),
]


def test_exact_fk_columns_targets_and_index_shapes(search_env):
    with search_env.engine.connect() as conn:
        fks = conn.execute(
            text("""
            SELECT c.conrelid::regclass::text,c.conname,
            ARRAY(SELECT a.attname FROM unnest(c.conkey) WITH ORDINALITY k(n,o)
             JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=k.n ORDER BY k.o),
            c.confrelid::regclass::text,
            ARRAY(SELECT a.attname FROM unnest(c.confkey) WITH ORDINALITY k(n,o)
             JOIN pg_attribute a ON a.attrelid=c.confrelid AND a.attnum=k.n ORDER BY k.o)
            FROM pg_constraint c WHERE c.conname LIKE 'pr316_%' AND c.contype='f'
            ORDER BY 1,2
        """)
        ).all()
        assert [(t, n, tuple(cols), target, tuple(refs)) for t, n, cols, target, refs in fks] == (
            FK_SHAPES
        )
        indexes = conn.execute(
            text("""
            SELECT i.indrelid::regclass::text,r.relname,i.indisunique,
            ARRAY(SELECT a.attname FROM unnest(i.indkey) WITH ORDINALITY k(n,o)
             JOIN pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=k.n ORDER BY k.o),
            pg_get_expr(i.indpred,i.indrelid),am.amname
            FROM pg_index i JOIN pg_class r ON r.oid=i.indexrelid
            JOIN pg_am am ON am.oid=r.relam WHERE r.relname LIKE 'pr316_%' ORDER BY 1,2
        """)
        ).all()

        def predicate(value):
            return None if value is None else re.sub(r"\s|[()]|::text", "", value)

        assert all(method == "btree" for *_, method in indexes)
        assert [(t, n, u, tuple(cols), predicate(p)) for t, n, u, cols, p, _ in indexes] == [
            (t, n, u, cols, predicate(p)) for t, n, u, cols, p in INDEX_SHAPES
        ]


def test_trigger_timing_and_exact_function_attachments(search_env):
    expected = set()
    for table, prefix in (
        ("experiment_search_sessions", "session"),
        ("experiment_search_nodes", "node"),
        ("experiment_search_events", "event"),
    ):
        for suffix, function, timing, deferred in (
            ("insert", "pr316_lineage_insert", 7, False),
            ("immutable", "pr316_immutable", 27, False),
            ("no_truncate", "pr316_immutable", 34, False),
            ("complete", "pr316_effect_complete", 5, True),
        ):
            expected.add((table, f"pr316_{prefix}_{suffix}", function, timing, deferred, deferred))
    expected.update(
        {
            (
                "experiment_search_node_runs",
                "pr316_link_insert_disabled",
                "pr316_link_write_disabled",
                7,
                False,
                False,
            ),
            (
                "experiment_search_node_runs",
                "pr316_link_immutable",
                "pr316_immutable",
                27,
                False,
                False,
            ),
            (
                "experiment_search_node_runs",
                "pr316_link_no_truncate",
                "pr316_immutable",
                34,
                False,
                False,
            ),
            (
                "research_task_command_receipts",
                "pr316_receipt_insert",
                "pr316_receipt_insert",
                7,
                False,
                False,
            ),
        }
    )
    with search_env.engine.connect() as conn:
        actual = conn.execute(
            text("""
            SELECT t.tgrelid::regclass::text,t.tgname,p.proname,t.tgtype,
            t.tgdeferrable,t.tginitdeferred FROM pg_trigger t JOIN pg_proc p ON p.oid=t.tgfoid
            WHERE t.tgname LIKE 'pr316_%'
        """)
        ).all()
        assert {tuple(row) for row in actual} == expected


@pytest.mark.parametrize(
    "changes,expected",
    [
        ({"project_id": new_uuid7()}, "pr316_completeness"),
        ({"budget_id": new_uuid7()}, "pr316_state"),
        ({"root_hypothesis_version_id": new_uuid7()}, "pr316_provenance"),
        ({"root_experiment_spec_content_hash": "A" * 64}, "pr316_provenance"),
    ],
)
def test_raw_session_scope_and_reference_pair_denials(search_env, changes, expected):
    with search_env.engine.connect() as conn:
        with pytest.raises(DBAPIError) as exc:
            create_rows(conn, search_env, session_changes=changes)
        assert error_constraint(exc) == expected
        conn.rollback()


def test_duplicate_search_or_task_event_effects_denied(search_env):
    for table in ("experiment_search_sessions", "experiment_search_events", "research_task_events"):
        with search_env.engine.connect() as conn:
            saved = create_rows(conn, search_env)
            row = dict(
                conn.execute(
                    text(f"SELECT * FROM {table} WHERE id=:id"),
                    {
                        "id": saved.session
                        if table.endswith("sessions")
                        else saved.event
                        if table == "experiment_search_events"
                        else saved.task_event
                    },
                )
                .mappings()
                .one()
            )
            row["id"] = new_uuid7()
            with pytest.raises(DBAPIError):
                insert(conn, table, row)
                conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
            conn.rollback()


def test_cancelled_task_search_events_rejected(search_env):
    from tests.integration.phase3.test_pr3_04_application import approve, bind

    p = search_env.p
    task = p.create()
    bind(p, task)
    approve(p, task, 2)
    p.service.execute(
        p.principal, p.command("cancel_research_task", task, 4, {"reason": "Cancel before search."})
    )
    with search_env.engine.connect() as conn:
        with pytest.raises(DBAPIError) as exc:
            create_rows(conn, search_env, task=task)
        assert error_constraint(exc) == "pr316_state"
        conn.rollback()
        assert (
            conn.execute(
                text("SELECT count(*) FROM experiment_search_sessions WHERE research_task_id=:id"),
                {"id": task},
            ).scalar_one()
            == 0
        )


@pytest.mark.parametrize("held", [False, True])
def test_enrolled_agent_requires_actor_key_without_version_prerequisite(agents, held):
    from tests.integration.phase2.pr2_20_support import upgrade
    from tests.integration.phase3.agent_fixtures import enrollment
    from tests.integration.phase3.search_fixtures import lock

    env = agents
    enrolled = enrollment(env)
    env.service.execute(enrolled)
    upgrade(env.url)
    actor, command, task = enrolled.arguments.actor_id, new_uuid7(), new_uuid7()
    with env.engine.connect() as conn:
        assert conn.execute(
            text("SELECT NOT rolsuper FROM pg_roles WHERE rolname=current_user")
        ).scalar_one()
        lock(conn, env.project, actor, command, task, agent=held)
        sql = text("""
            SELECT pr316_preheld(jsonb_populate_record(NULL::research_task_command_receipts,
            jsonb_build_object('project_id',CAST(:project AS text),'actor_id',CAST(:actor AS text),
             'command_id',CAST(:command AS text),'research_task_id',CAST(:task AS text))))
        """)
        params = dict(project=env.project, actor=actor, command=command, task=task)
        if held:
            conn.execute(sql, params)
        else:
            with pytest.raises(DBAPIError) as exc:
                conn.execute(sql, params)
            assert error_constraint(exc) == "pr316_preheld"
        conn.rollback()


@pytest.mark.parametrize(
    "reason,valid",
    [
        ("  café-研究  ", True),
        ("\t", False),
        ("e\u0301", False),
        ("x" * 8193, False),
    ],
)
def test_original_reason_and_uuid_normalization(search_env, reason, valid):
    from uuid import uuid4

    with search_env.engine.connect() as conn:
        assert conn.execute(text("SELECT pr316_reason(:r)"), {"r": reason}).scalar_one() is valid
        assert conn.execute(text("SELECT pr316_uuid7(:id)"), {"id": uuid4()}).scalar_one() is False
        assert (
            conn.execute(text("SELECT pr316_uuid7(:id)"), {"id": new_uuid7()}).scalar_one() is True
        )
