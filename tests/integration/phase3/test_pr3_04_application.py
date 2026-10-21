"""Atomic commands against disposable PostgreSQL 18; no fake persistence."""

from typing import Any

import pytest
from sqlalchemy import text
from tests.integration.phase3.conftest import Credentials

from researchbase.agent_runtime.application.safety_contracts import (
    RequestCheckpointArguments,
    parse_safety_command,
)
from researchbase.agent_runtime.application.task_safety import TaskSafetyService
from researchbase.agent_runtime.services.fake_consumer import TrustedFakeConsumer
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.ids import new_uuid7


def command(p, task, revision, name, args):
    return parse_safety_command(
        name,
        dict(
            project_id=str(p.project),
            task_id=str(task),
            command_id=str(new_uuid7()),
            expected_row_version=revision,
            arguments=args,
        ),
    )


def service(p):
    return TaskSafetyService(p.factory, Credentials(), p.store)


def bind(p, task, revision=1, *, budget=None, checkpoint=None):
    c = command(
        p,
        task,
        revision,
        "bind_task_policies",
        dict(
            budget_id=str(new_uuid7()),
            budget=budget or {"pricing_basis": "fake-usd-v1"},
            termination_policy_id=str(new_uuid7()),
            termination={},
            checkpoint_policy_id=str(new_uuid7()),
            checkpoint=checkpoint or {},
            reason="Bound pilot policies.",
        ),
    )
    return c, service(p).execute(p.principal, c)


def approve(p, task, revision, *, kind="plan_review", step=None):
    c = command(
        p,
        task,
        revision,
        "request_human_checkpoint",
        dict(
            checkpoint_id=str(new_uuid7()),
            step_id=str(step) if step else None,
            checkpoint_type=kind,
            reason="Review bounded work.",
        ),
    )
    service(p).execute(p.principal, c)
    assert isinstance(c.arguments, RequestCheckpointArguments)
    response = command(
        p,
        task,
        revision + 1,
        "respond_human_checkpoint",
        dict(
            checkpoint_id=str(c.arguments.checkpoint_id),
            expected_checkpoint_row_version=1,
            response="APPROVED",
            reason="Approved bounded work.",
        ),
    )
    service(p).execute(p.principal, response)
    return response


def resources(**changes):
    return (
        dict(
            wall_time_seconds=60,
            agent_steps=1,
            llm_calls=1,
            search_calls=0,
            code_iterations=0,
            experiment_runs=0,
            tree_nodes=0,
            gpu_hours="0.000000",
            token_cost="0.100000",
            **changes,
        )
        if not changes
        else {**resources(), **changes}
    )


def reserve(p, task, revision, **changes):
    return command(
        p,
        task,
        revision,
        "reserve_task_budget",
        dict(
            operation_id=str(new_uuid7()),
            step_id=None,
            resources=resources(**changes),
            observed_depth=0,
            observed_parallel_branches=1,
            deadline_seconds=1,
            reason="Bound fake work.",
        ),
    )


def settle(p, task, revision, reservation, *, outcome="SUCCEEDED", measured=None):
    return command(
        p,
        task,
        revision,
        "settle_task_budget",
        dict(
            reservation_id=str(reservation),
            measured=measured or resources(),
            outcome=outcome,
            score=None,
            evaluator_version=None,
            reason="Attributable fake observation.",
        ),
    )


def test_bind_checkpoint_reserve_settle_and_read(planning):
    p = planning
    task = p.create()
    c, result = bind(p, task)
    assert (
        len(result.budget_ids)
        == len(result.termination_policy_ids)
        == len(result.checkpoint_policy_ids)
        == 1
    )
    assert service(p).execute(p.principal, c).command_result.replayed
    approve(p, task, 2)
    fake = TrustedFakeConsumer(p.factory, Credentials(), p.store)
    reservation = fake.execute(p.principal, reserve(p, task, 4))
    assert len(reservation.reservation_ids) == 1
    result = fake.execute(p.principal, settle(p, task, 5, reservation.reservation_ids[0]))
    assert len(result.usage_record_ids) == 1
    view = service(p).get_task_safety(p.principal, p.project, task)
    assert (
        view.task_row_version == 6 and view.consumed.llm_calls == 1 and view.reserved.llm_calls == 0
    )
    assert view.execution_enabled is False
    history = service(p).get_task_checkpoint_history(p.principal, p.project, task)
    assert history.checkpoints[0].status == "APPROVED"
    assert history.checkpoints[0].receipt_id != history.checkpoints[0].response_receipt_id


@pytest.mark.parametrize("sealed", (False, True))
def test_binding_preserves_plan_and_cancel_bookkeeping(planning, sealed):
    p = planning
    task, _ = p.plan()
    revision = 2
    if sealed:
        p.service.execute(p.principal, p.command("seal_task_plan", task, revision))
        revision += 1
    before = p.service.get_task_graph(p.principal, p.project, task)
    bind(p, task, revision)
    after = p.service.get_task_graph(p.principal, p.project, task)
    assert before.nodes == after.nodes and before.edges == after.edges
    assert before.task.plan_sealed_at == after.task.plan_sealed_at
    p.service.execute(
        p.principal,
        p.command("cancel_research_task", task, revision + 1, {"reason": "Stop planning."}),
    )
    evaluation = command(
        p,
        task,
        revision + 2,
        "evaluate_task_termination",
        {"reason": "Retained terminal accounting."},
    )
    service(p).execute(p.principal, evaluation)
    assert p.service.get_research_task(p.principal, p.project, task).status == "CANCELLED"


def test_public_reserve_denies_without_effects(planning):
    task = planning.create()
    c = reserve(planning, task, 1)
    with pytest.raises(ResearchBaseError) as exc:
        service(planning).execute(planning.principal, c)
    assert exc.value.code == ErrorCode.FORBIDDEN
    assert (
        planning.service.get_research_task(planning.principal, planning.project, task).row_version
        == 1
    )


def test_evaluation_records_stop_and_nostop(planning):
    p = planning
    task = p.create()
    bind(p, task)
    for revision, human in ((2, False), (3, True)):
        service(p).execute(
            p.principal,
            command(
                p,
                task,
                revision,
                "evaluate_task_termination",
                {"human_stop": human, "reason": "Evaluate limits."},
            ),
        )
    view = service(p).get_task_safety(p.principal, p.project, task)
    assert view.stop_causes == ("HUMAN_STOP",)
    assert view.task_row_version == 4
    with p.engine.connect() as conn:
        assert (
            conn.execute(
                text("SELECT count(*) FROM research_task_events WHERE research_task_id=:id"),
                {"id": task},
            ).scalar_one()
            == 4
        )


def test_literal_first_share_and_no_sql_before_it(planning):
    from sqlalchemy import event

    from researchbase.persistence.research_task_repository import SHARE_SQL

    p = planning
    task = p.create()
    statements = []

    def capture(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(p.engine, "before_cursor_execute", capture)
    try:
        bind(p, task)
    finally:
        event.remove(p.engine, "before_cursor_execute", capture)
    assert statements[0] == SHARE_SQL
    assert len(statements[0].split("LOCK TABLE ")[1].split(" IN SHARE MODE")[0].split(", ")) == 18


@pytest.mark.parametrize(
    "point",
    (
        "execution_budgets",
        "checkpoint_policies",
        "human_checkpoints",
        "research_task_events",
        "research_task_receipt_events",
    ),
)
def test_injected_failure_rolls_back_task_and_all_results(planning, monkeypatch, point):
    from researchbase.persistence.task_safety_repository import SqlAlchemyTaskSafetyRepository

    p = planning
    task = p.create()
    if point == "human_checkpoints":
        bind(p, task)
    revision = 2 if point == "human_checkpoints" else 1
    before = p.service.get_task_graph(p.principal, p.project, task)
    original = SqlAlchemyTaskSafetyRepository.insert

    def insert(repo, table, row):
        if table == point:
            raise RuntimeError("injected failure")
        return original(repo, table, row)

    monkeypatch.setattr(SqlAlchemyTaskSafetyRepository, "insert", insert)
    with pytest.raises(RuntimeError, match="injected failure"):
        if point == "human_checkpoints":
            service(p).execute(
                p.principal,
                command(
                    p,
                    task,
                    revision,
                    "request_human_checkpoint",
                    dict(
                        checkpoint_id=str(new_uuid7()),
                        step_id=None,
                        checkpoint_type="exception",
                        reason="Rollback request.",
                    ),
                ),
            )
        else:
            bind(p, task)
    assert p.service.get_task_graph(p.principal, p.project, task) == before


@pytest.mark.parametrize(
    "kind",
    (
        "plan_review",
        "hypothesis_selection",
        "experiment_approval",
        "budget_extension",
        "code_risk",
        "claim_freeze",
        "manuscript_release",
        "exception",
    ),
)
def test_all_checkpoint_types_and_extension_intent(planning, kind):
    p = planning
    task = p.create()
    _, bound = bind(p, task)
    args: dict[str, Any] = dict(
        checkpoint_id=str(new_uuid7()),
        step_id=None,
        checkpoint_type=kind,
        reason="Explicit Human gate.",
    )
    if kind == "budget_extension":
        args.update(
            proposed_budget_id=str(new_uuid7()),
            proposed_budget={"pricing_basis": "fake-usd-v1", "max_agent_steps": 100},
        )
    request = command(p, task, 2, "request_human_checkpoint", args)
    saved = service(p).execute(p.principal, request)
    assert len(saved.budget_ids) == int(kind == "budget_extension")
    response = command(
        p,
        task,
        3,
        "respond_human_checkpoint",
        {
            "checkpoint_id": args["checkpoint_id"],
            "expected_checkpoint_row_version": 1,
            "response": "APPROVED",
            "reason": "Intent approved.",
        },
    )
    service(p).execute(p.principal, response)
    view = service(p).get_task_safety(p.principal, p.project, task)
    assert view.budget_policy_id == bound.budget_ids[0]
    assert view.budget is not None
    assert view.budget.max_agent_steps == 50
    history = service(p).get_task_checkpoint_history(p.principal, p.project, task)
    assert history.checkpoints[0].checkpoint_type == kind
    if kind == "budget_extension":
        assert history.checkpoints[0].proposed_budget is not None
        assert history.checkpoints[0].proposed_budget.id == saved.budget_ids[0]
        assert history.checkpoints[0].proposed_budget.id != view.budget_policy_id


@pytest.mark.parametrize("autonomy", ("A0", "A1", "A2"))
def test_autonomy_requires_independent_prerequisites(planning, autonomy):
    from researchbase.agent_runtime.services.fake_consumer import TrustedFakeConsumer

    p = planning
    create = p.command(
        arguments={
            "task_type": "OTHER",
            "objective": "Bounded autonomy.",
            "strategy_id": "human_guided_research",
            "strategy_version": "1.0.0",
            "autonomy_level": autonomy,
        }
    )
    p.service.execute(p.principal, create)
    task = create.task_id
    bind(p, task)
    approve(p, task, 2)
    fake = TrustedFakeConsumer(p.factory, Credentials(), p.store)
    if autonomy == "A2":
        with pytest.raises(ResearchBaseError) as exc:
            fake.execute(p.principal, reserve(p, task, 4))
        assert exc.value.code == ErrorCode.INVALID_STATE_TRANSITION
    else:
        fake.execute(p.principal, reserve(p, task, 4))
    with pytest.raises(ResearchBaseError):
        p.service.execute(
            p.principal, p.command("start_research_task", task, 4 if autonomy == "A2" else 5)
        )
