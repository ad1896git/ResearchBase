import json
from pathlib import Path
from typing import cast

import pytest
from psycopg import Error as PostgresError
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from tests.disposable_postgres import disposable_database
from tests.integration.phase2.pr2_20_support import upgrade
from tests.integration.phase3.intent_fixtures import _intent_env as _intent_env
from tests.integration.phase3.intent_fixtures import intent_rows

from researchbase.foundation.ids import new_uuid7
from researchbase.persistence.agent_execution_repository import SqlAlchemyExecutionRepository


@pytest.mark.parametrize("grantee", ["PUBLIC", "normal_role"])
def test_normal_role_cannot_write_intent_tables(grantee):
    # Both revocation paths must remove privileges that really would be inherited.
    # A role created without these defaults cannot demonstrate a migration REVOKE.
    with disposable_database("researchbase_pr212_test_") as url:
        upgrade(url, "0080_capability_gateway")
        engine = create_engine(url)
        role = "pr302s2_revoke_" + new_uuid7().hex
        target = "PUBLIC" if grantee == "PUBLIC" else role
        privileges = ("INSERT", "UPDATE", "DELETE", "TRUNCATE")
        with engine.begin() as conn:
            conn.execute(text(f"CREATE ROLE {role} NOSUPERUSER NOCREATEDB NOCREATEROLE NOLOGIN"))
        try:
            with engine.begin() as conn:
                conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {role}"))
                conn.execute(
                    text(
                        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
                        f"GRANT INSERT,UPDATE,DELETE,TRUNCATE ON TABLES TO {target}"
                    )
                )
                conn.execute(text("CREATE TABLE intent_privilege_probe (id integer)"))
                for privilege in privileges:
                    assert conn.execute(
                        text(
                            "SELECT has_table_privilege(:role, "
                            "'intent_privilege_probe', :privilege)"
                        ),
                        {"role": role, "privilege": privilege},
                    ).scalar_one()
                conn.execute(text("DROP TABLE intent_privilege_probe"))
            upgrade(url)
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "GRANT SELECT ON agent_execution_instances,agent_execution_events "
                        f"TO {role}"
                    )
                )
            for table in ("agent_execution_instances", "agent_execution_events"):
                for operation in privileges:
                    sql = {
                        "INSERT": f"INSERT INTO {table} DEFAULT VALUES",
                        "UPDATE": f"UPDATE {table} SET id=id",
                        "DELETE": f"DELETE FROM {table}",
                        "TRUNCATE": f"TRUNCATE {table}",
                    }[operation]
                    with pytest.raises(DBAPIError) as exc, engine.begin() as conn:
                        conn.execute(text(f"SET LOCAL ROLE {role}"))
                        conn.execute(text(sql))
                    assert cast(PostgresError, exc.value.orig).sqlstate == "42501", (
                        grantee,
                        table,
                        operation,
                    )
        finally:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
                        f"REVOKE INSERT,UPDATE,DELETE,TRUNCATE ON TABLES FROM {target}"
                    )
                )
                conn.execute(text(f"DROP OWNED BY {role}"))
                conn.execute(text(f"DROP ROLE {role}"))
            engine.dispose()


@pytest.mark.parametrize(
    "case,tag",
    [
        ("prefix", "pr302s2_preheld"),
        ("advisory", "pr302s2_preheld"),
        ("missing_receipt", "pr302s2_completeness"),
        ("actor", "pr302s2_scope"),
        ("state", "pr302s2_state"),
        ("cas", "pr302s2_cas"),
        ("binding", "pr302s2_binding"),
        ("not_frozen", "pr302s2_not_frozen"),
        ("hash", "pr302s2_provenance"),
        ("event", "pr302s2_completeness"),
        ("partial", "pr302s2_completeness"),
        ("request_hash", "pr302s2_provenance"),
    ],
)
def test_named_insertion_and_receipt_guards(intent_env, case, tag):
    env = intent_env
    receipt, intent, event = intent_rows(env)
    if case == "state":
        env.planning.service.execute(
            env.owner,
            env.planning.command(
                "cancel_research_task",
                env.intent.arguments.research_task_id,
                3,
                {"reason": "cancel"},
            ),
        )
    if case == "not_frozen":
        from tests.application_compat import LegacyApplicationService

        from researchbase.application.commands import CreateArtifactVersionCommand
        from researchbase.domain.artifact import ArtifactId
        from researchbase.foundation.execution_context import ExecutionContext
        from researchbase.foundation.time import SystemClock

        with env.owning_factory() as preflight:
            artifact = preflight.agents.configuration(
                env.intent.arguments.harness_artifact_version_id
            )
        # Draft creation needs the owning Application; perform it before raw locks instead.
        assert artifact is not None
        draft = LegacyApplicationService(
            env.owning_factory, SystemClock(), env.store
        ).create_artifact_version(
            CreateArtifactVersionCommand(
                ArtifactId(artifact["artifact_id"]),
                b"draft",
                None,
                None,
                "text/plain",
                5,
                None,
                ExecutionContext(
                    actor_id=env.owner.actor_id, request_id=new_uuid7(), client_type="test"
                ),
            )
        )
        intent["harness_artifact_version_id"] = draft.id

    with pytest.raises(DBAPIError) as exc, Session(env.owning_engine) as session, session.begin():
        repo = SqlAlchemyExecutionRepository(session)
        if case != "prefix":
            if case == "advisory":
                from researchbase.persistence.agent_execution_repository import INTENT_SHARE_SQL

                session.execute(text(INTENT_SHARE_SQL))
            else:
                repo.lock_write(env.intent, lambda: None)
        if case == "request_hash":
            receipt["request_hash"] = "f" * 64
        if case != "missing_receipt":
            saved = repo.insert("agent_command_receipts", receipt)
            intent["created_at"] = event["occurred_at"] = saved["recorded_at"]
        if case == "actor":
            intent["actor_id"] = env.owner.actor_id
            repo.advisory(f"pr302:actor:{env.owner.actor_id}")
        if case == "cas":
            intent["task_revision_at_creation"] = 2
        if case == "binding":
            intent["research_task_step_id"] = new_uuid7()
        if case == "hash":
            intent["input_ref_hash"] = "f" * 64
        repo.insert("agent_execution_instances", intent)
        if case != "partial":
            if case == "event":
                event["reason"] = "wrong"
            repo.insert("agent_execution_events", event)
        if case == "partial":
            session.execute(text("SET CONSTRAINTS pr302_receipt_complete_commit IMMEDIATE"))
        repo.force_constraints()
    assert cast(PostgresError, exc.value.orig).sqlstate == "23514"
    assert cast(PostgresError, exc.value.orig).diag.constraint_name == tag


@pytest.mark.parametrize("table", ["agent_execution_instances", "agent_execution_events"])
@pytest.mark.parametrize("operation", ["UPDATE", "DELETE"])
def test_owning_role_immutable_including_noop(intent_env, table, operation):
    env = intent_env
    env.intents.execute(env.intent)
    sql = f"UPDATE {table} SET id=id" if operation == "UPDATE" else f"DELETE FROM {table}"
    with pytest.raises(DBAPIError) as exc, env.owning_engine.begin() as conn:
        conn.execute(text(sql))
    assert cast(PostgresError, exc.value.orig).diag.constraint_name == "pr302s2_immutable"


def test_python_postgresql_intent_material_parity(intent_env):
    env = intent_env
    vectors = json.loads(Path("tests/fixtures/phase3/intent_vectors.json").read_text())
    with env.engine.connect() as conn:
        for key, v in vectors.items():
            if key == "source_sha256":
                continue
            result = conn.execute(
                text(
                    "SELECT pr302s2_cjson(CAST(:value AS jsonb)),pr302s2_value_digest(CAST(:value AS jsonb))"  # noqa: E501
                ),
                {"value": json.dumps(v["value"], ensure_ascii=False)},
            ).one()
            assert tuple(result) == (v["utf8"], v["sha256"])
    with pytest.raises(DBAPIError) as exc, env.engine.begin() as conn:
        conn.execute(text("SELECT pr302s2_cjson(NULL::jsonb)"))
    assert cast(PostgresError, exc.value.orig).sqlstate == "22023"
    assert cast(PostgresError, exc.value.orig).diag.constraint_name == "pr302s2_value_type"


@pytest.mark.parametrize("table", ["agent_execution_instances", "agent_execution_events"])
def test_historical_receipt_cannot_attach_new_history(intent_env, table):
    env = intent_env
    receipt, intent, event = intent_rows(env)
    result = env.intents.execute(env.intent)
    if table == "agent_execution_events":
        event["receipt_id"] = result.receipt_id
        event["id"] = new_uuid7()
    with pytest.raises(DBAPIError) as exc, Session(env.owning_engine) as session, session.begin():
        repo = SqlAlchemyExecutionRepository(session)
        repo.lock_write(env.intent, lambda: None)
        repo.insert(table, event if table == "agent_execution_events" else intent)
    assert cast(PostgresError, exc.value.orig).diag.constraint_name == "pr302s2_late_history"


def test_unresolved_input_material_diagnostic(intent_env):
    with pytest.raises(DBAPIError) as exc, intent_env.owning_engine.begin() as conn:
        conn.execute(text("SELECT pr302s2_input_material(:id)"), {"id": new_uuid7()})
    assert cast(PostgresError, exc.value.orig).diag.constraint_name == "pr302s2_unresolved"


def test_exact_intent_schema_and_scoped_foreign_keys(intent_env):
    from sqlalchemy import inspect

    env = intent_env
    inspector = inspect(env.owning_engine)
    expected = {
        "agent_execution_instances": {
            "id",
            "project_id",
            "research_task_id",
            "research_task_step_id",
            "task_revision_at_creation",
            "agent_version_id",
            "actor_id",
            "status",
            "revision",
            "created_at",
            "input_ref_hash",
            "input_ref_hash_scheme",
            "harness_artifact_version_id",
            "harness_content_hash",
            "harness_hash_scheme",
        },
        "agent_execution_events": {
            "id",
            "execution_id",
            "sequence",
            "prior_status",
            "new_status",
            "actor_id",
            "occurred_at",
            "reason",
            "receipt_id",
        },
    }
    for table, columns in expected.items():
        actual = inspector.get_columns(table)
        assert {c["name"] for c in actual} == columns
        assert all(c["default"] is None for c in actual)
        assert {c["name"] for c in actual if c["nullable"]} == (
            {"research_task_step_id"} if table.endswith("instances") else {"prior_status"}
        )
        assert all(
            fk["options"]["ondelete"] == "RESTRICT" for fk in inspector.get_foreign_keys(table)
        )
    foreign = {fk["name"]: fk for fk in inspector.get_foreign_keys("agent_execution_instances")}
    assert foreign["pr302s2_exec_version_fk"]["constrained_columns"] == [
        "agent_version_id",
        "project_id",
        "actor_id",
    ]
    assert foreign["pr302s2_exec_task_fk"]["referred_columns"] == ["id", "project_id"]
    assert foreign["pr302s2_exec_step_fk"]["referred_columns"] == ["research_task_id", "id"]
    assert not any(
        inspector.has_table(t) for t in ("agent_promotion_records", "agent_promotion_outputs")
    )


def test_literal_checks_indexes_and_receipt_deferral(intent_env):
    env = intent_env
    expected_checks = {
        "pr302s2_exec_id_ck",
        "pr302s2_exec_status_ck",
        "pr302s2_exec_revision_ck",
        "pr302s2_exec_task_revision_ck",
        "pr302s2_exec_time_ck",
        "pr302s2_exec_hashes_ck",
        "pr302s2_exec_schemes_ck",
        "pr302s2_event_id_ck",
        "pr302s2_event_initial_ck",
        "pr302s2_event_time_ck",
        "pr302s2_event_reason_ck",
        "pr302s2_receipt_operation_ck",
        "pr302s2_receipt_shape_ck",
    }
    expected_indexes = {
        "pr302s2_exec_pk",
        "pr302s2_exec_project_task",
        "pr302s2_exec_task_step",
        "pr302s2_exec_version",
        "pr302s2_exec_actor",
        "pr302s2_exec_harness",
        "pr302s2_event_pk",
        "pr302s2_event_execution_uq",
        "pr302s2_event_receipt_uq",
        "pr302s2_event_actor",
        "pr302s2_receipt_execution_uq",
        "pr302s2_receipt_event_uq",
    }
    with env.owning_engine.connect() as conn:
        checks = conn.execute(
            text(
                "SELECT conname,convalidated,pg_get_constraintdef(oid) FROM pg_constraint WHERE conname LIKE 'pr302s2_%' AND contype='c'"  # noqa: E501
            )
        ).all()
        assert {r[0] for r in checks} == expected_checks
        assert all(r[1] for r in checks)
        definitions = {r[0]: r[2] for r in checks}
        assert "'CREATED'::text" in definitions["pr302s2_exec_status_ck"]
        assert "(revision = 1)" in definitions["pr302s2_exec_revision_ck"]
        assert "isfinite(created_at)" in definitions["pr302s2_exec_time_ck"]
        assert "Execution intent created." in definitions["pr302s2_event_reason_ck"]
        indexes = (
            conn.execute(
                text(
                    "SELECT indexname FROM pg_indexes WHERE schemaname='public' AND indexname LIKE 'pr302s2_%'"  # noqa: E501
                )
            )
            .scalars()
            .all()
        )
        assert set(indexes) == expected_indexes
        fks = conn.execute(
            text(
                "SELECT conname,condeferrable,condeferred,confupdtype,confdeltype,confmatchtype FROM pg_constraint WHERE conname LIKE 'pr302s2_%' AND contype='f'"  # noqa: E501
            )
        ).all()
        assert all(tuple(r[3:]) == ("a", "r", "s") for r in fks)
        for r in fks:
            assert tuple(r[1:3]) == (
                (True, True)
                if r[0] in {"pr302s2_receipt_execution_fk", "pr302s2_receipt_event_fk"}
                else (False, False)
            )
