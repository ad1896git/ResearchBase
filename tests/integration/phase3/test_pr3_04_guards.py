"""Direct SQL under a non-superuser role; immutable history and fresh owners."""

from time import perf_counter
from typing import Any, cast
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker
from tests.integration.phase3.conftest import Credentials
from tests.integration.phase3.test_pr3_04_application import bind, command

from researchbase.agent_runtime.application.task_safety import TaskSafetyService
from researchbase.foundation.ids import new_uuid7
from researchbase.persistence.research_task_repository import SHARE_SQL
from researchbase.persistence.uow import SqlAlchemyUnitOfWork


@pytest.fixture
def normal_engine(planning):
    role = "pr304_test_" + uuid4().hex
    with planning.engine.begin() as conn:
        conn.exec_driver_sql(f"CREATE ROLE {role} NOSUPERUSER NOCREATEDB NOCREATEROLE NOLOGIN")
        conn.exec_driver_sql(f"GRANT USAGE ON SCHEMA public TO {role}")
        conn.exec_driver_sql(
            f"GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO {role}"
        )
    engine = create_engine(
        planning.url,
        connect_args={
            "options": f"-c track_functions=pl -c role={role} -c lock_timeout=10s -c statement_timeout=30s"  # noqa: E501
        },
    )
    try:
        with engine.connect() as conn:
            assert (
                conn.execute(
                    text("SELECT rolsuper FROM pg_roles WHERE rolname=current_user")
                ).scalar_one()
                is False
            )
        yield engine
    finally:
        engine.dispose()
        with planning.engine.begin() as conn:
            conn.exec_driver_sql(f"DROP OWNED BY {role}")
            conn.exec_driver_sql(f"DROP ROLE {role}")


def protocol(conn, p, task):
    conn.execute(text(SHARE_SQL))
    conn.execute(text("SELECT rb_phase2_lock_project(:id)"), {"id": p.project})
    for key in (
        f"pr301:command:{p.project}:{p.principal.actor_id}:{new_uuid7()}",
        f"pr301:task:{task}",
    ):
        conn.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"), {"key": key})
    conn.execute(text("SELECT id FROM research_tasks WHERE id=:id FOR UPDATE"), {"id": task})


@pytest.mark.parametrize(
    "table", ("execution_budgets", "termination_policies", "checkpoint_policies")
)
@pytest.mark.parametrize("operation", ("UPDATE", "DELETE"))
def test_normal_role_noop_policy_mutation_rejected(planning, normal_engine, table, operation):
    p = planning
    task = p.create()
    bind(p, task)
    with normal_engine.connect() as conn:
        protocol(conn, p, task)
        with pytest.raises(DBAPIError) as exc:
            conn.execute(
                text(
                    f"{operation} {'FROM ' if operation == 'DELETE' else ''}{table} "
                    + ("SET content_hash=content_hash " if operation == "UPDATE" else "")
                    + "WHERE research_task_id=:id"
                ),
                {"id": task},
            )
        assert cast(Any, exc.value.orig).sqlstate == "23514"
        assert cast(Any, exc.value.orig).diag.constraint_name == "pr301_immutable"


def test_committed_receipt_child_attach_and_forged_guc_rejected(planning, normal_engine):
    p = planning
    task = p.create()
    _, bound = bind(p, task)
    with normal_engine.connect() as conn:
        protocol(conn, p, task)
        conn.execute(text("SELECT set_config('researchbase.trusted_consumer','true',true)"))
        with pytest.raises(DBAPIError) as exc:
            conn.execute(
                text(
                    "INSERT INTO execution_budgets SELECT :new_id,research_task_id,created_at,receipt_id,max_wall_time_seconds,max_agent_steps,max_llm_calls,max_search_calls,max_code_iterations,max_experiment_runs,max_tree_nodes,max_tree_depth,max_parallel_branches,max_gpu_hours,max_token_cost,currency,pricing_basis,hard_stop,content_hash,hash_scheme FROM execution_budgets WHERE id=:id"  # noqa: E501
                ),
                {"new_id": new_uuid7(), "id": bound.budget_ids[0]},
            )
        assert cast(Any, exc.value.orig).diag.constraint_name == "pr301_immutable"


def test_naked_revision_and_second_task_write_rejected(planning, normal_engine):
    p = planning
    task = p.create()
    with normal_engine.connect() as conn:
        protocol(conn, p, task)
        conn.execute(
            text("UPDATE research_tasks SET row_version=row_version+1 WHERE id=:id"), {"id": task}
        )
        with pytest.raises(DBAPIError):
            conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    with normal_engine.connect() as conn:
        protocol(conn, p, task)
        conn.execute(
            text("UPDATE research_tasks SET row_version=row_version+1 WHERE id=:id"), {"id": task}
        )
        with pytest.raises(DBAPIError) as exc:
            conn.execute(
                text("UPDATE research_tasks SET row_version=row_version+1 WHERE id=:id"),
                {"id": task},
            )
        assert cast(Any, exc.value.orig).diag.constraint_name == "pr301_immutable"


def test_normal_role_valid_command_and_exact_final_firing_count(
    planning, normal_engine, monkeypatch
):
    from tests.integration.phase3.test_pr3_04_application import reserve, settle

    from researchbase.agent_runtime.services.fake_consumer import TrustedFakeConsumer
    from researchbase.persistence.task_safety_repository import SqlAlchemyTaskSafetyRepository

    p = planning
    task = p.create()
    sessions = sessionmaker(normal_engine, expire_on_commit=False, autoflush=False)
    observed = []
    original = SqlAlchemyTaskSafetyRepository.force_constraints

    def force(repo):
        prior = dict(
            repo._session.execute(
                text(
                    "SELECT funcname,calls FROM pg_stat_xact_user_functions WHERE funcname IN ('pr301_graph_final_guard','pr301_receipt_complete')"  # noqa: E501
                )
            ).all()
        )  # noqa: E501
        started = perf_counter()
        original(repo)
        elapsed = perf_counter() - started
        counts = dict(
            repo._session.execute(
                text(
                    "SELECT funcname,calls FROM pg_stat_xact_user_functions WHERE funcname IN ('pr301_graph_final_guard','pr301_receipt_complete')"  # noqa: E501
                )
            ).all()
        )
        observed.append(
            ({name: value - prior.get(name, 0) for name, value in counts.items()}, elapsed)
        )

    monkeypatch.setattr(SqlAlchemyTaskSafetyRepository, "force_constraints", force)

    def factory():
        return SqlAlchemyUnitOfWork(sessions)

    normal = TaskSafetyService(factory, Credentials(), p.store)
    fake = TrustedFakeConsumer(factory, Credentials(), p.store)
    bind_command = command(
        p,
        task,
        1,
        "bind_task_policies",
        dict(
            budget_id=str(new_uuid7()),
            budget={"pricing_basis": "fake-usd-v1"},
            termination_policy_id=str(new_uuid7()),
            termination={},
            checkpoint_policy_id=str(new_uuid7()),
            checkpoint={"timeout_seconds": 1},
            reason="Count final checks.",
        ),
    )
    normal.execute(p.principal, bind_command)
    checkpoint_id = new_uuid7()
    normal.execute(
        p.principal,
        command(
            p,
            task,
            2,
            "request_human_checkpoint",
            dict(
                checkpoint_id=str(checkpoint_id),
                step_id=None,
                checkpoint_type="plan_review",
                reason="Plan gate.",
            ),
        ),
    )
    normal.execute(
        p.principal,
        command(
            p,
            task,
            3,
            "respond_human_checkpoint",
            dict(
                checkpoint_id=str(checkpoint_id),
                expected_checkpoint_row_version=1,
                response="APPROVED",
                reason="Approve fake work.",
            ),
        ),
    )
    result = fake.execute(p.principal, reserve(p, task, 4))
    fake.execute(p.principal, settle(p, task, 5, result.reservation_ids[0]))
    normal.execute(
        p.principal, command(p, task, 6, "evaluate_task_termination", {"reason": "No stop."})
    )
    for revision, kind in ((7, "exception"), (8, "code_risk")):
        normal.execute(
            p.principal,
            command(
                p,
                task,
                revision,
                "request_human_checkpoint",
                dict(
                    checkpoint_id=str(new_uuid7()),
                    step_id=None,
                    checkpoint_type=kind,
                    reason="Batch expiry.",
                ),
            ),
        )
    with p.engine.connect() as conn:
        conn.execute(
            text(
                "SELECT pg_sleep(greatest(0,extract(epoch FROM (max(expires_at)-clock_timestamp())))) FROM human_checkpoints WHERE research_task_id=:id"  # noqa: E501
            ),
            {"id": task},
        )
    result = normal.execute(
        p.principal,
        command(p, task, 9, "evaluate_task_termination", {"reason": "Expire two requests."}),
    )
    assert len(result.responded_checkpoint_ids) == 2
    assert len(observed) == 9
    assert all(
        counts == {"pr301_graph_final_guard": 1, "pr301_receipt_complete": 1}
        for counts, _ in observed
    ), observed
    print(
        f"FINAL_GUARDS: commands=9 all_counts=1+1 constraint_seconds={[round(t, 6) for _, t in observed]} batch_expired=2"  # noqa: E501
    )


def test_maximum_scope_bundle_on_bounded_graph(planning, normal_engine, monkeypatch):
    """Measure the two final sites with 512 typed scope rows and maximum graph."""
    from tests.application_compat import LegacyApplicationService
    from tests.integration.test_pr06_application import register_command, snapshot_command
    from tests.integration.test_pr08_application import create_command

    from researchbase.application.commands import FreezeMetricDefinitionCommand
    from researchbase.domain.evidence import DatasetId
    from researchbase.domain.organization import ProjectId
    from researchbase.foundation.execution_context import ExecutionContext
    from researchbase.foundation.time import SystemClock

    p = planning
    app = LegacyApplicationService(p.factory, SystemClock(), p.store)
    context = ExecutionContext(
        actor_id=p.principal.actor_id, request_id=new_uuid7(), client_type="test"
    )
    dataset = app.register_dataset(register_command(ProjectId(p.project), context))
    snapshots = []
    metrics = []
    for i in range(256):
        snapshots.append(
            app.create_dataset_snapshot(
                snapshot_command(
                    DatasetId(dataset.id), context, selection_definition={"partition": i}
                )
            ).id
        )
        metric = app.create_metric_definition(create_command(context, ProjectId(p.project)))
        frozen = app.freeze_metric_definition(
            FreezeMetricDefinitionCommand(metric.id, metric.current_version_id, context, 1)
        )
        metrics.append(frozen.id)
    nodes = [
        {"step_id": str(new_uuid7()), "step_type": "PLAN", "ordinal": i + 1} for i in range(256)
    ]
    edges = [
        {"predecessor_id": nodes[i]["step_id"], "dependent_id": nodes[j]["step_id"]}
        for i in range(256)
        for j in range(i + 1, 256)
    ][:1024]
    task, _ = p.plan(nodes=nodes, edges=edges)
    sessions = sessionmaker(normal_engine, expire_on_commit=False, autoflush=False)

    def factory():
        return SqlAlchemyUnitOfWork(sessions)

    observed = []
    original = SqlAlchemyUnitOfWork.commit

    def commit(uow):
        session = uow._require_session()
        observed.append(
            dict(
                session.execute(
                    text(
                        "SELECT funcname,calls FROM pg_stat_xact_user_functions WHERE funcname IN ('pr301_graph_final_guard','pr301_receipt_complete')"  # noqa: E501
                    )
                ).all()
            )
        )
        original(uow)

    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", commit)
    c = command(
        p,
        task,
        2,
        "bind_task_policies",
        dict(
            budget_id=str(new_uuid7()),
            budget={"pricing_basis": "fake-usd-v1"},
            termination_policy_id=str(new_uuid7()),
            termination={},
            checkpoint_policy_id=str(new_uuid7()),
            checkpoint={
                "maximum_autonomy": "A3",
                "a3_authorized": True,
                "allowed_dataset_snapshot_ids": [str(i) for i in snapshots],
                "allowed_metric_version_ids": [str(i) for i in metrics],
                "allowed_code_paths": [f"src/file{i}.py" for i in range(256)],
                "network_mode": "ALLOWLIST",
                "allowed_network_hosts": [f"host{i}.example" for i in range(256)],
            },
            reason="Maximum admitted bounded policy.",
        ),
    )
    started = perf_counter()
    result = TaskSafetyService(factory, Credentials(), p.store).execute(p.principal, c)
    elapsed = perf_counter() - started
    assert len(result.dataset_scope_ids) == len(result.metric_scope_ids) == 256
    assert observed == [{"pr301_graph_final_guard": 1, "pr301_receipt_complete": 1}]
    print(
        f"MAX_BOUND: scopes=256+256 nodes=256 edges=1024 command_seconds={elapsed:.6f} final_counts={observed[0]}"  # noqa: E501
    )


@pytest.mark.parametrize(
    "table", ("budget_reservations", "budget_usage_records", "human_checkpoints")
)
@pytest.mark.parametrize("operation", ("UPDATE", "DELETE"))
def test_accounting_and_response_history_are_immutable(planning, normal_engine, table, operation):
    from tests.integration.phase3.test_pr3_04_accounting import setup
    from tests.integration.phase3.test_pr3_04_application import reserve, settle

    p = planning
    task, fake = setup(p)
    reserved = fake.execute(p.principal, reserve(p, task, 4))
    fake.execute(p.principal, settle(p, task, 5, reserved.reservation_ids[0]))
    with normal_engine.connect() as conn:
        protocol(conn, p, task)
        sql = f"UPDATE {table} SET id=id" if operation == "UPDATE" else f"DELETE FROM {table}"
        with pytest.raises(DBAPIError) as exc:
            conn.execute(text(sql + " WHERE research_task_id=:id"), {"id": task})
        assert cast(Any, exc.value.orig).diag.constraint_name == "pr301_immutable"


@pytest.mark.parametrize("counterfeit", (False, True))
def test_direct_normal_role_evaluation_recomputes_flags(planning, normal_engine, counterfeit):
    p = planning
    task = p.create()
    bind(p, task)
    c = command(
        p, task, 2, "evaluate_task_termination", {"reason": "Direct deterministic evaluation."}
    )
    receipt_id, event_id = new_uuid7(), new_uuid7()
    with normal_engine.connect() as conn:
        conn.execute(text(SHARE_SQL))
        conn.execute(text("SELECT rb_phase2_lock_project(:id)"), {"id": p.project})
        for key in (
            f"pr301:command:{p.project}:{p.principal.actor_id}:{c.command_id}",
            f"pr301:task:{task}",
        ):
            conn.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"), {"key": key}
            )
        conn.execute(text("SELECT id FROM research_tasks WHERE id=:id FOR UPDATE"), {"id": task})
        at = conn.execute(text("SELECT clock_timestamp()")).scalar_one()
        conn.execute(text("UPDATE research_tasks SET row_version=3 WHERE id=:id"), {"id": task})
        receipt = dict(
            id=receipt_id,
            project_id=p.project,
            actor_id=p.principal.actor_id,
            command_id=c.command_id,
            command_name=c.command_name,
            research_task_id=task,
            request_hash=c.request_hash(p.principal.actor_id),
            hash_scheme="sha256-cjson-v1",
            material_version=1,
            resulting_row_version=3,
            completed_at=at,
        )
        event = dict(
            id=event_id,
            research_task_id=task,
            actor_id=p.principal.actor_id,
            command_id=c.command_id,
            event_type="TERMINATION_EVALUATED",
            sequence=3,
            task_row_version=3,
            prior_status="CREATED",
            new_status="CREATED",
            reason="Direct deterministic evaluation.",
            occurred_at=at,
            stop_budget=counterfeit,
        )
        for table, row in (
            ("research_task_command_receipts", receipt),
            ("research_task_events", event),
            (
                "research_task_receipt_events",
                dict(receipt_id=receipt_id, research_task_id=task, event_id=event_id),
            ),
        ):
            conn.execute(
                text(
                    f"INSERT INTO {table} ({','.join(row)}) VALUES ({','.join(':' + k for k in row)})"  # noqa: E501
                ),
                row,
            )
        if counterfeit:
            with pytest.raises(DBAPIError) as exc:
                conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
            assert cast(Any, exc.value.orig).diag.constraint_name == "pr301_validation"
            conn.rollback()
        else:
            conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
            conn.commit()
    assert p.service.get_research_task(p.principal, p.project, task).row_version == (
        2 if counterfeit else 3
    )
