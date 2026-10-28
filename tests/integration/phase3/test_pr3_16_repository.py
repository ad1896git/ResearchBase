"""Real PG18 S2 mappings/UoW/storage compatibility, with production guards enabled.

These tests use the admitted S1 fixtures. They do not supply a production
CredentialVerifier, activate D1, or establish the later S8 race/expiry gate.
"""

from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlalchemy import (
    CheckConstraint,
    UniqueConstraint,
    create_engine,
    event,
    inspect,
    select,
    text,
)
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from tests.integration.phase3.search_fixtures import (
    TABLES,
)
from tests.integration.phase3.search_fixtures import (
    _search_env as _search_env,
)
from tests.integration.phase3.test_pr3_16_schema import COLUMNS, CONSTRAINTS

from researchbase.foundation.hashing import sha256_canonical_json
from researchbase.foundation.ids import new_uuid7
from researchbase.persistence.database import Base
from researchbase.persistence.experiment_search_repository import (
    SqlAlchemyExperimentSearchRepository,
)
from researchbase.persistence.models import (
    ExperimentSearchEventModel,
    ExperimentSearchNodeModel,
    ExperimentSearchNodeRunModel,
    ExperimentSearchSessionModel,
    ResearchTaskCommandReceiptsModel,
)


def create_effect(uow, env, *, callback=None, omit_event=False):
    """Assemble S1's raw create effect through S2 storage, without a new service."""
    project, actor, task = env.p.project, env.p.principal.actor_id, env.task
    saved = SimpleNamespace(
        **dict(
            zip(
                ("command", "receipt", "session", "event", "task_event"),
                (new_uuid7() for _ in range(5)),
                strict=True,
            )
        )
    )
    repo = uow.experiment_search
    stages = []

    def after_stage(stage):
        stages.append(stage)
        # This transaction's receipt never substitutes for a committed replay,
        # including after its own DML, FK waits, forced checks, or final boundary.
        assert repo.committed_receipt(project, actor, saved.command) is None
        if callback is not None:
            callback(stage)

    repo.lock_write(
        project, actor, saved.command, task, caller_kind="HUMAN", after_stage=after_stage
    )
    task_row = repo.task(task)
    assert task_row is not None
    revision = task_row["row_version"] + 1
    material = dict(
        type="ExperimentSearchCommand",
        material_version=1,
        command_name="create_search_session",
        project_id=str(project),
        actor_id=str(actor),
        command_id=str(saved.command),
        task_id=str(task),
        expected_row_version=revision - 1,
        arguments=dict(
            session_id=str(saved.session),
            root_hypothesis_version_id=None,
            root_experiment_spec_version_id=None,
        ),
    )
    saved.request_hash = str(sha256_canonical_json(material))
    at = repo.snapshot_at()
    repo.update_task(task, revision - 1)
    repo.insert(
        "research_task_command_receipts",
        dict(
            id=saved.receipt,
            project_id=project,
            actor_id=actor,
            command_id=saved.command,
            research_task_id=task,
            command_name="create_search_session",
            request_hash=saved.request_hash,
            hash_scheme="sha256-cjson-v1",
            material_version=1,
            resulting_row_version=revision,
            completed_at=at,
            result_search_session_id=saved.session,
            result_search_event_id=saved.event,
        ),
    )
    repo.insert(
        "experiment_search_sessions",
        dict(
            id=saved.session,
            project_id=project,
            research_task_id=task,
            budget_id=task_row["budget_policy_id"],
            created_by=actor,
            created_at=at,
            receipt_id=saved.receipt,
        ),
    )
    if not omit_event:
        repo.insert(
            "experiment_search_events",
            dict(
                id=saved.event,
                research_task_id=task,
                search_session_id=saved.session,
                sequence=1,
                event_type="SESSION_CREATED",
                reason="Search session created.",
                actor_id=actor,
                occurred_at=at,
                receipt_id=saved.receipt,
            ),
        )
    repo.insert(
        "research_task_events",
        dict(
            id=saved.task_event,
            research_task_id=task,
            actor_id=actor,
            command_id=saved.command,
            event_type="SEARCH_SESSION_CREATED",
            sequence=revision,
            task_row_version=revision,
            prior_status=task_row["status"],
            new_status=task_row["status"],
            reason="Search session created.",
            occurred_at=at,
        ),
    )
    repo.insert(
        "research_task_receipt_events",
        dict(
            receipt_id=saved.receipt,
            research_task_id=task,
            event_id=saved.task_event,
        ),
    )
    saved.stages = stages
    return saved


@pytest.mark.parametrize("table", TABLES)
def test_real_pg_mapping_matches_admitted_columns_keys_and_indexes(search_env, table):
    with search_env.engine.connect() as connection:
        assert int(connection.execute(text("SHOW server_version_num")).scalar_one()) // 10000 == 18
        inspector = inspect(connection)
        mapped = Base.metadata.tables[table]
        actual = inspector.get_columns(table)
        assert [(c["name"], str(c["type"]).lower(), c["nullable"]) for c in actual] == [
            (
                name,
                {"timestamp with time zone": "timestamp", "integer": "integer"}.get(typ, typ),
                nullable,
            )
            for name, typ, nullable in COLUMNS[table]
        ]
        assert list(mapped.columns.keys()) == [c["name"] for c in actual]
        for column in actual:
            local = mapped.c[column["name"]]
            assert str(local.type.compile(dialect=connection.dialect)) == str(
                column["type"].compile(dialect=connection.dialect)
            )
            assert local.nullable == column["nullable"]
            assert (
                local.default is None and local.server_default is None and column["default"] is None
            )
        assert mapped.primary_key.name == inspector.get_pk_constraint(table)["name"]
        assert (
            list(mapped.primary_key.columns.keys())
            == inspector.get_pk_constraint(table)["constrained_columns"]
        )
        assert {
            c.name: tuple(c.columns.keys())
            for c in mapped.constraints
            if isinstance(c, UniqueConstraint)
        } == {c["name"]: tuple(c["column_names"]) for c in inspector.get_unique_constraints(table)}
        assert {c.name for c in mapped.constraints if isinstance(c, CheckConstraint)} == {
            c["name"] for c in inspector.get_check_constraints(table)
        }
        assert {c.name for c in mapped.constraints} == {
            name for name in CONSTRAINTS[table] if not name.endswith("_nn")
        } - {"pr316_session_complete", "pr316_node_complete", "pr316_event_complete"}
        actual_fks = {fk["name"]: fk for fk in inspector.get_foreign_keys(table)}
        for fk in mapped.foreign_key_constraints:
            actual_fk = actual_fks.pop(fk.name)
            assert list(fk.column_keys) == actual_fk["constrained_columns"]
            assert [element.target_fullname for element in fk.elements] == [
                actual_fk["referred_table"] + "." + c for c in actual_fk["referred_columns"]
            ]
            assert fk.ondelete == actual_fk["options"]["ondelete"] == "RESTRICT"
            assert not fk.deferrable and not actual_fk["options"].get("deferrable", False)
        assert not actual_fks
        actual_indexes = {
            i["name"]: i for i in inspector.get_indexes(table) if not i.get("duplicates_constraint")
        }
        assert set(actual_indexes) == {i.name for i in mapped.indexes}
        for index in mapped.indexes:
            actual_index = actual_indexes[index.name]
            assert index.unique == actual_index["unique"]
            assert list(index.columns.keys()) == actual_index["column_names"]
            assert bool(index.dialect_options["postgresql"].get("where") is not None) == bool(
                actual_index.get("dialect_options", {}).get("postgresql_where")
            )


def test_real_pg_receipt_pointers_and_support_keys(search_env):
    with search_env.engine.connect() as connection:
        inspector = inspect(connection)
        mapped = Base.metadata.tables["research_task_command_receipts"]
        actual = {c["name"]: c for c in inspector.get_columns(mapped.name)}
        assert set(mapped.columns.keys()) == set(actual)
        for name in ("result_search_session_id", "result_search_node_id", "result_search_event_id"):
            assert actual[name]["nullable"] and mapped.c[name].nullable
            assert actual[name]["default"] is None and mapped.c[name].default is None
        for fk in mapped.foreign_key_constraints:
            if isinstance(fk.name, str) and fk.name.startswith("pr316_"):
                actual_fk = next(
                    f for f in inspector.get_foreign_keys(mapped.name) if f["name"] == fk.name
                )
                assert fk.deferrable and fk.initially == "DEFERRED"
                assert (
                    actual_fk["options"]["deferrable"]
                    and actual_fk["options"]["initially"] == "DEFERRED"
                )
        for table, name, columns in (
            ("runs", "pr316_run_project_uq", ["id", "project_id"]),
            (
                "budget_reservations",
                "pr303_reservation_operation_key",
                ["research_task_id", "id", "operation_id"],
            ),
        ):
            assert any(
                isinstance(c, UniqueConstraint)
                and c.name == name
                and list(c.columns.keys()) == columns
                for c in Base.metadata.tables[table].constraints
            )
            assert any(
                c["name"] == name and c["column_names"] == columns
                for c in inspector.get_unique_constraints(table)
            )


def test_ordinary_role_create_uow_commit_and_committed_receipt_replay(search_env):
    env = search_env
    trace = []

    def record(conn, cursor, statement, parameters, context, executemany):
        trace.append(" ".join(statement.split()))

    event.listen(env.engine, "before_cursor_execute", record)
    try:
        with env.p.factory() as uow:
            uow.begin_experiment_search()
            assert trace == []
            saved = create_effect(uow, env)
            assert trace[0].startswith("LOCK TABLE actor_subject_bindings, actors,")
            uow.commit()
    finally:
        event.remove(env.engine, "before_cursor_execute", record)
    assert [s.operation for s in saved.stages[-3:]] == ["flush", "constraints", "final"]
    with env.p.factory() as uow:
        uow.begin_research_task()
        repo = uow.experiment_search
        receipt = repo.committed_receipt(env.p.project, env.p.principal.actor_id, saved.command)
        assert receipt is not None and receipt["id"] == saved.receipt
        assert receipt["request_hash"] == saved.request_hash
        assert receipt["result_search_session_id"] == saved.session
        assert receipt["result_search_event_id"] == saved.event
        assert receipt["result_search_node_id"] is None
        assert repo.nodes(env.task, saved.session) == []
        assert repo.node_runs(env.p.project, env.task, saved.session) == []
    # Detached values survive Session closure and mutation does not edit history.
    receipt["request_hash"] = "b" * 64
    with env.p.factory() as uow:
        assert (
            uow.experiment_search.committed_receipt(
                env.p.project, env.p.principal.actor_id, saved.command
            )["request_hash"]
            == saved.request_hash
        )
    with env.engine.connect() as connection:
        assert connection.execute(
            text(
                "SELECT NOT rolsuper AND NOT rolbypassrls FROM pg_roles WHERE rolname=current_user"
            )
        ).scalar_one()
        for table in (
            "experiment_search_sessions",
            "experiment_search_events",
            "research_task_command_receipts",
        ):
            column = "id" if table == "research_task_command_receipts" else "receipt_id"
            assert (
                connection.execute(
                    text(f"SELECT count(*) FROM {table} WHERE {column}=:id"), {"id": saved.receipt}
                ).scalar_one()
                == 1
            )


@pytest.mark.parametrize("stop", ["update", "insert", "flush", "constraints", "final"])
def test_real_pg_callback_denial_rolls_back_all_own_effects(search_env, stop):
    env = search_env
    with env.engine.connect() as connection:
        before = connection.execute(
            text("SELECT row_version FROM research_tasks WHERE id=:id"), {"id": env.task}
        ).scalar_one()
        counts = [
            connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
            for table in TABLES
        ]

    def deny(stage):
        if stage.operation == stop:
            raise PermissionError("test Application callback denies")

    with pytest.raises(PermissionError):
        with env.p.factory() as uow:
            uow.begin_experiment_search()
            create_effect(uow, env, callback=deny)
            uow.commit()
    with env.engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT row_version FROM research_tasks WHERE id=:id"), {"id": env.task}
            ).scalar_one()
            == before
        )
        assert [
            connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
            for table in TABLES
        ] == counts


def test_real_pg_deferred_failure_does_not_commit_incomplete_effects(search_env):
    from researchbase.foundation.errors import ResearchBaseError

    with pytest.raises(ResearchBaseError):
        with search_env.p.factory() as uow:
            uow.begin_experiment_search()
            saved = create_effect(uow, search_env, omit_event=True)
            uow.commit()
    with search_env.engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT count(*) FROM research_task_command_receipts WHERE id=:id"),
                {"id": saved.receipt},
            ).scalar_one()
            == 0
        )


def test_formal_read_keeps_task_safety_and_lineage_in_one_snapshot(search_env):
    from researchbase.agent_runtime.application.task_safety import safety_projection

    env = search_env
    with env.p.factory() as read:
        read.begin_formal_read()
        repo = read.experiment_search
        at = repo.snapshot_at()
        task = repo.task(env.task)
        assert task is not None
        sessions = repo.sessions(env.p.project, env.task)
        safety = safety_projection(repo, task, at, history=False)
        assert read._session is not None
        options = (
            read._session.execute(text("SHOW transaction_isolation")).scalar_one(),
            read._session.execute(text("SHOW transaction_read_only")).scalar_one(),
        )
        assert options == ("repeatable read", "on")
        assert (
            read._session.execute(
                text(
                    "SELECT count(*) FROM pg_locks WHERE pid=pg_backend_pid() "
                    "AND (locktype='advisory' OR mode IN "
                    "('ShareLock','RowShareLock','RowExclusiveLock'))"
                )
            ).scalar_one()
            == 0
        )
        with env.p.factory() as writer:
            writer.begin_experiment_search()
            saved = create_effect(writer, env)
            writer.commit()
        assert repo.task(env.task) == task
        assert repo.sessions(env.p.project, env.task) == sessions
        assert repo.snapshot_at() == at
        assert safety_projection(repo, repo.task(env.task), at, history=False) == safety
        for session in sessions:
            assert [event["sequence"] for event in repo.search_events(env.task, session["id"])] == [
                1
            ]
            assert repo.nodes(env.task, session["id"]) == []
            assert repo.node_runs(env.p.project, env.task, session["id"]) == []
        # Objective is read from its one immutable owner, without session copies.
        assert task["objective"] == repo.task(env.task)["objective"]
        assert all("objective_definition" not in session for session in sessions)
    with env.p.factory() as read:
        read.begin_formal_read()
        assert saved.session in {
            row["id"] for row in read.experiment_search.sessions(env.p.project, env.task)
        }


def test_orm_selects_are_inert_detached_reads(search_env):
    with Session(search_env.engine) as session, session.begin():
        for model in (
            ExperimentSearchSessionModel,
            ExperimentSearchNodeModel,
            ExperimentSearchNodeRunModel,
            ExperimentSearchEventModel,
        ):
            session.scalars(select(model)).all()
        receipt = session.get(ResearchTaskCommandReceiptsModel, search_env.saved.receipt)
        assert receipt is not None and receipt.result_search_session_id == search_env.saved.session
        assert receipt.result_search_node_id is None


def test_enrolled_agent_lock_compatibility_without_agent_version(agents):
    from tests.integration.phase2.pr2_20_support import upgrade
    from tests.integration.phase3.agent_fixtures import enrollment

    enrolled = enrollment(agents)
    agents.service.execute(enrolled)
    upgrade(agents.url)
    with agents.engine.connect() as connection:
        role = connection.execute(text("SELECT current_user")).scalar_one()
    admin = create_engine(agents.url)
    try:
        with admin.begin() as connection:
            connection.execute(text(f'GRANT SELECT ON {",".join(TABLES)} TO "{role}"'))
        actor, command, task = enrolled.arguments.actor_id, new_uuid7(), new_uuid7()
        with agents.factory() as uow:
            uow.begin_experiment_search()
            stages = []
            uow.experiment_search.lock_write(
                agents.project,
                actor,
                command,
                task,
                caller_kind="AGENT",
                after_stage=stages.append,
            )
            assert uow._session is not None
            assert (
                uow._session.execute(
                    text("SELECT count(*) FROM agent_versions WHERE actor_id=:id"), {"id": actor}
                ).scalar_one()
                == 0
            )
            uow._session.execute(
                text("""
                SELECT pr316_preheld(jsonb_populate_record(NULL::research_task_command_receipts,
                jsonb_build_object('project_id',CAST(:project AS text),
                'actor_id',CAST(:actor AS text),
                'command_id',CAST(:command AS text),'research_task_id',CAST(:task AS text))))
            """),
                dict(project=agents.project, actor=actor, command=command, task=task),
            )
            assert [s.operation for s in stages[:5]] == [
                "share",
                "project",
                "command_key",
                "task_key",
                "actor_key",
            ]
    finally:
        admin.dispose()


def test_production_link_guard_remains_enabled_with_adapter_no_link_writer(search_env):
    with Session(search_env.engine, autoflush=False) as session:
        repo = SqlAlchemyExperimentSearchRepository(session)
        with pytest.raises(ValueError):
            repo.insert("experiment_search_node_runs", {"id": new_uuid7()})
        with pytest.raises(DBAPIError) as error:
            session.execute(
                text("INSERT INTO experiment_search_node_runs (id) VALUES (:id)"),
                {"id": new_uuid7()},
            )
        assert cast(Any, error.value.orig).diag.constraint_name == "pr316_no_link_writer"
        session.rollback()
        source = session.execute(
            text(
                "SELECT pg_get_functiondef("
                "'pr316_node_proof(experiment_search_nodes)'::regprocedure)"
            )
        ).scalar_one()
        assert "D1 activation prerequisite unavailable" in source and "pr316_activation" in source


def test_committed_replay_callback_stops_before_later_locks_or_effects(search_env):
    env = search_env
    with env.engine.connect() as connection:
        saved = (
            connection.execute(
                text(
                    "SELECT project_id,actor_id,command_id,request_hash FROM "
                    "research_task_command_receipts WHERE id=:id"
                ),
                {"id": env.saved.receipt},
            )
            .mappings()
            .one()
        )
        before = connection.execute(
            text("SELECT row_version FROM research_tasks WHERE id=:id"), {"id": env.task}
        ).scalar_one()

    class Replay(Exception):
        pass

    order = []
    with pytest.raises(Replay):
        with env.p.factory() as uow:
            uow.begin_experiment_search()
            repo = uow.experiment_search

            def after_stage(stage):
                assert stage.operation == "share"
                order.append("current read entitlement")
                assert repo.authority(env.p.principal, env.p.project)
                order.append("committed receipt and hash")
                receipt = repo.committed_receipt(
                    saved["project_id"], saved["actor_id"], saved["command_id"]
                )
                assert receipt is not None and receipt["request_hash"] == saved["request_hash"]
                assert receipt["result_search_session_id"] == env.saved.session
                raise Replay

            repo.lock_write(
                env.p.project,
                env.p.principal.actor_id,
                saved["command_id"],
                env.task,
                caller_kind="HUMAN",
                after_stage=after_stage,
            )
    assert order == ["current read entitlement", "committed receipt and hash"]
    with env.engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT row_version FROM research_tasks WHERE id=:id"), {"id": env.task}
            ).scalar_one()
            == before
        )
