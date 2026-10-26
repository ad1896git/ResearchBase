import json
import re
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


@pytest.fixture(scope="module", params=["PUBLIC", "normal_role"])
def default_granted_intent_tables(request):
    # Both revocation paths must remove privileges that really would be inherited.
    # A role created without these defaults cannot demonstrate a migration REVOKE.
    with disposable_database("researchbase_pr212_test_") as url:
        upgrade(url, "0080_capability_gateway")
        engine = create_engine(url)
        role = "pr302s2_revoke_" + new_uuid7().hex
        target = "PUBLIC" if request.param == "PUBLIC" else role
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
            yield engine, role
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


@pytest.mark.parametrize("table", ["agent_execution_instances", "agent_execution_events"])
@pytest.mark.parametrize("operation", ["INSERT", "UPDATE", "DELETE", "TRUNCATE"])
def test_normal_role_cannot_write_intent_tables(default_granted_intent_tables, table, operation):
    engine, role = default_granted_intent_tables
    sql = {
        "INSERT": f"INSERT INTO {table} DEFAULT VALUES",
        "UPDATE": f"UPDATE {table} SET id=id",
        "DELETE": f"DELETE FROM {table}",
        "TRUNCATE": f"TRUNCATE {table}",
    }[operation]
    with pytest.raises(DBAPIError) as exc, engine.begin() as conn:
        conn.execute(text(f"SET LOCAL ROLE {role}"))
        assert conn.execute(text("SELECT current_user")).scalar_one() == role
        assert conn.execute(
            text("SELECT NOT rolsuper FROM pg_roles WHERE rolname=current_user")
        ).scalar_one()
        conn.execute(text(sql))
    assert cast(PostgresError, exc.value.orig).sqlstate == "42501"


@pytest.mark.parametrize(
    "case,tag",
    [
        ("prefix", "pr302s2_preheld"),
        ("isolation", "pr302s2_preheld"),
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
        if case == "isolation":
            session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
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
    diagnostic = cast(PostgresError, exc.value.orig).diag
    assert diagnostic.constraint_name == tag
    # Shared tags alone cannot identify which protection actually rejected the write.
    # In particular, the receipt root also raises cas, and the receipt insertion
    # guard raises preheld after the SHARE/isolation helper has returned.
    function, message = {
        "prefix": ("pr302s2_preheld", "intent SHARE protection absent"),
        "isolation": ("pr302s2_preheld", "intent isolation"),
        "advisory": ("pr302_receipt_guard", "intent command protection absent"),
        "missing_receipt": ("pr302s2_execution_guard", "intent receipt missing"),
        "actor": ("pr302s2_execution_guard", "exact live Agent required"),
        "state": ("pr302s2_execution_guard", "intent state"),
        "cas": ("pr302s2_execution_guard", "task revision"),
        "binding": ("pr302s2_execution_guard", "intent scope binding"),
        "not_frozen": ("pr302s2_execution_guard", "pin not frozen"),
        "hash": ("pr302s2_execution_guard", "intent material contradiction"),
        "event": ("pr302s2_event_guard", "initial intent event contradiction"),
        "partial": ("pr302_receipt_complete", "intent closure incomplete"),
        "request_hash": ("pr302_receipt_complete", "intent digest contradiction"),
    }[case]
    assert diagnostic.message_primary == message
    assert re.search(
        rf"^PL/pgSQL function {function}\(\) line \d+ at RAISE$",
        diagnostic.context or "",
        re.MULTILINE,
    ), diagnostic.context


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
    # Literal PostgreSQL 18 renderings of frozen Q3.3, independent of migration DDL.
    # Full equality retains every operand/cast, including all three receipt branches.
    uuid_check = (
        "CHECK (((SUBSTRING((id)::text FROM 15 FOR 1) = '7'::text) AND "
        "(SUBSTRING((id)::text FROM 20 FOR 1) = ANY "
        "(ARRAY['8'::text, '9'::text, 'a'::text, 'b'::text]))))"
    )
    expected_checks = {
        "pr302s2_exec_id_ck": uuid_check,
        "pr302s2_exec_status_ck": "CHECK ((status = 'CREATED'::text))",
        "pr302s2_exec_revision_ck": "CHECK ((revision = 1))",
        "pr302s2_exec_task_revision_ck": (
            "CHECK (((task_revision_at_creation >= 1) AND "
            "(task_revision_at_creation <= 2147483647)))"
        ),
        "pr302s2_exec_time_ck": "CHECK (isfinite(created_at))",
        "pr302s2_exec_hashes_ck": (
            "CHECK (((input_ref_hash ~ '^[0-9a-f]{64}$'::text) AND "
            "(harness_content_hash ~ '^[0-9a-f]{64}$'::text)))"
        ),
        "pr302s2_exec_schemes_ck": (
            "CHECK (((input_ref_hash_scheme = 'sha256-cjson-v1'::text) AND "
            "(harness_hash_scheme = 'sha256-bytes-v1'::text)))"
        ),
        "pr302s2_event_id_ck": uuid_check,
        "pr302s2_event_initial_ck": (
            "CHECK (((sequence = 1) AND (prior_status IS NULL) AND (new_status = 'CREATED'::text)))"
        ),
        "pr302s2_event_time_ck": "CHECK (isfinite(occurred_at))",
        "pr302s2_event_reason_ck": "CHECK ((reason = 'Execution intent created.'::text))",
        "pr302s2_receipt_operation_ck": (
            "CHECK ((operation = ANY (ARRAY['provision_project_agent'::text, "
            "'register_agent_version'::text, 'change_agent_availability'::text, "
            "'create_agent_execution'::text])))"
        ),
        "pr302s2_receipt_shape_ck": (
            "CHECK ((((operation = 'provision_project_agent'::text) AND "
            "(num_nonnulls(result_actor_id, result_binding_id, result_membership_id, "
            "result_role_assignment_id, result_binding_event_id, "
            "result_membership_event_id, result_role_event_id) = 7) AND "
            "(result_agent_version_id IS NULL) AND (result_availability_event_id IS NULL) "
            "AND (result_execution_id IS NULL) AND (result_execution_event_id IS NULL) "
            "AND (resulting_revision = 1)) OR "
            "((operation = ANY (ARRAY['register_agent_version'::text, "
            "'change_agent_availability'::text])) AND "
            "(num_nonnulls(result_actor_id, result_binding_id, result_membership_id, "
            "result_role_assignment_id, result_binding_event_id, "
            "result_membership_event_id, result_role_event_id) = 0) AND "
            "(result_agent_version_id IS NOT NULL) AND "
            "(result_availability_event_id IS NOT NULL) AND (result_execution_id IS NULL) "
            "AND (result_execution_event_id IS NULL) AND "
            "(((operation = 'register_agent_version'::text) AND (resulting_revision = 1)) "
            "OR ((operation = 'change_agent_availability'::text) AND "
            "(resulting_revision >= 2)))) OR "
            "((operation = 'create_agent_execution'::text) AND "
            "(num_nonnulls(result_actor_id, result_binding_id, result_membership_id, "
            "result_role_assignment_id, result_binding_event_id, "
            "result_membership_event_id, result_role_event_id, result_agent_version_id, "
            "result_availability_event_id) = 0) AND (result_execution_id IS NOT NULL) "
            "AND (result_execution_event_id IS NOT NULL) AND (resulting_revision = 1))))"
        ),
    }
    # Q3.2: both primary keys, both event UNIQUEs and all eight additional indexes.
    expected_indexes = {
        "pr302s2_exec_pk": (
            "CREATE UNIQUE INDEX pr302s2_exec_pk ON public.agent_execution_instances "
            "USING btree (id)"
        ),
        "pr302s2_exec_project_task": (
            "CREATE INDEX pr302s2_exec_project_task ON public.agent_execution_instances "
            "USING btree (project_id, research_task_id, id)"
        ),
        "pr302s2_exec_task_step": (
            "CREATE INDEX pr302s2_exec_task_step ON public.agent_execution_instances "
            "USING btree (research_task_id, research_task_step_id)"
        ),
        "pr302s2_exec_version": (
            "CREATE INDEX pr302s2_exec_version ON public.agent_execution_instances "
            "USING btree (agent_version_id, project_id, actor_id)"
        ),
        "pr302s2_exec_actor": (
            "CREATE INDEX pr302s2_exec_actor ON public.agent_execution_instances "
            "USING btree (actor_id)"
        ),
        "pr302s2_exec_harness": (
            "CREATE INDEX pr302s2_exec_harness ON public.agent_execution_instances "
            "USING btree (harness_artifact_version_id)"
        ),
        "pr302s2_event_pk": (
            "CREATE UNIQUE INDEX pr302s2_event_pk ON public.agent_execution_events USING btree (id)"
        ),
        "pr302s2_event_execution_uq": (
            "CREATE UNIQUE INDEX pr302s2_event_execution_uq ON public.agent_execution_events "
            "USING btree (execution_id)"
        ),
        "pr302s2_event_receipt_uq": (
            "CREATE UNIQUE INDEX pr302s2_event_receipt_uq ON public.agent_execution_events "
            "USING btree (receipt_id)"
        ),
        "pr302s2_event_actor": (
            "CREATE INDEX pr302s2_event_actor ON public.agent_execution_events "
            "USING btree (actor_id)"
        ),
        "pr302s2_receipt_execution_uq": (
            "CREATE UNIQUE INDEX pr302s2_receipt_execution_uq ON public.agent_command_receipts "
            "USING btree (result_execution_id) WHERE (result_execution_id IS NOT NULL)"
        ),
        "pr302s2_receipt_event_uq": (
            "CREATE UNIQUE INDEX pr302s2_receipt_event_uq ON public.agent_command_receipts "
            "USING btree (result_execution_event_id) WHERE (result_execution_event_id IS NOT NULL)"
        ),
    }
    with env.owning_engine.connect() as conn:
        checks = conn.execute(
            text(
                "SELECT conname,convalidated,pg_get_constraintdef(oid) FROM pg_constraint WHERE conname LIKE 'pr302s2_%' AND contype='c'"  # noqa: E501
            )
        ).all()
        assert all(r[1] for r in checks)
        assert {r[0]: r[2] for r in checks} == expected_checks
        indexes = dict(
            conn.execute(
                text(
                    "SELECT indexname,indexdef FROM pg_indexes WHERE schemaname='public' AND indexname LIKE 'pr302s2_%'"  # noqa: E501
                )
            ).all()
        )
        assert indexes == expected_indexes
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
