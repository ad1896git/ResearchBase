"""Durable last-unit, UNKNOWN and nonrefundable admission counters."""

from decimal import Decimal

import pytest
from tests.integration.phase3.conftest import Credentials
from tests.integration.phase3.test_pr3_04_application import (
    approve,
    bind,
    command,
    reserve,
    resources,
    service,
    settle,
)

from researchbase.agent_runtime.services.fake_consumer import TrustedFakeConsumer
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


def setup(p, **limits):
    task = p.create()
    bind(p, task, budget={"pricing_basis": "fake-usd-v1", **limits})
    approve(p, task, 2)
    return task, TrustedFakeConsumer(p.factory, Credentials(), p.store)


def test_last_unit_and_sticky_stop_after_refund(planning):
    p = planning
    task, fake = setup(p, max_token_cost="0.100000")
    result = fake.execute(p.principal, reserve(p, task, 4))
    assert service(p).get_task_safety(p.principal, p.project, task).stop_causes == (
        "BUDGET_EXHAUSTED",
    )
    fake.execute(
        p.principal,
        settle(p, task, 5, result.reservation_ids[0], measured=resources(token_cost="0.000001")),
    )
    view = fake.reconstruct(p.principal, p.project, task)
    assert view.remaining.token_cost == Decimal("0.099999")
    assert view.stop_causes == ("BUDGET_EXHAUSTED",)
    with pytest.raises(ResearchBaseError) as exc:
        fake.execute(p.principal, reserve(p, task, 6))
    assert exc.value.code == ErrorCode.INVALID_STATE_TRANSITION


def test_unknown_retains_vector_and_occupancy_until_final(planning):
    p = planning
    task, fake = setup(p)
    result = fake.execute(p.principal, reserve(p, task, 4))
    for revision in (5, 6):
        fake.execute(
            p.principal, settle(p, task, revision, result.reservation_ids[0], outcome="UNKNOWN")
        )
    view = fake.reconstruct(p.principal, p.project, task)
    assert (
        view.reserved.llm_calls == 1
        and view.consumed.llm_calls == 0
        and view.parallel_branches == 1
    )
    with pytest.raises(ResearchBaseError):
        fake.execute(p.principal, reserve(p, task, 7))
    fake.execute(p.principal, settle(p, task, 7, result.reservation_ids[0], outcome="FAILED"))
    view = fake.reconstruct(p.principal, p.project, task)
    assert view.parallel_branches == 0 and view.consumed.llm_calls == 1
    with pytest.raises(ResearchBaseError):
        fake.execute(p.principal, settle(p, task, 8, result.reservation_ids[0], outcome="UNKNOWN"))


@pytest.mark.parametrize("outcome", ("FAILED", "CANCELLED", "PRUNED"))
def test_attempts_retain_call_charge(planning, outcome):
    p = planning
    task, fake = setup(p)
    reservation = fake.execute(p.principal, reserve(p, task, 4))
    fake.execute(p.principal, settle(p, task, 5, reservation.reservation_ids[0], outcome=outcome))
    assert fake.reconstruct(p.principal, p.project, task).consumed.llm_calls == 1
    next_attempt = fake.execute(p.principal, reserve(p, task, 6))
    assert next_attempt.reservation_ids != reservation.reservation_ids


@pytest.mark.parametrize(
    "field,value", (("gpu_hours", "0.000001"), ("agent_steps", 51), ("token_cost", "5.000001"))
)
def test_excess_reservation_has_no_effects(planning, field, value):
    p = planning
    task, fake = setup(p)
    with pytest.raises(ResearchBaseError):
        fake.execute(p.principal, reserve(p, task, 4, **{field: value}))
    view = fake.reconstruct(p.principal, p.project, task)
    assert view.task_row_version == 4 and view.reserved.llm_calls == 0


def test_stop_allows_final_bookkeeping_after_cancel(planning):
    p = planning
    task, fake = setup(p)
    reserved = fake.execute(p.principal, reserve(p, task, 4))
    p.service.execute(
        p.principal, p.command("cancel_research_task", task, 5, {"reason": "Stop task."})
    )
    fake.execute(p.principal, settle(p, task, 6, reserved.reservation_ids[0]))
    service(p).execute(
        p.principal,
        command(
            p, task, 7, "evaluate_task_termination", {"reason": "Bookkeeping after cancellation."}
        ),
    )
    assert p.service.get_research_task(p.principal, p.project, task).status == "CANCELLED"


def test_comparable_iteration_scores_and_missing_observation(planning):
    from dataclasses import replace

    from tests.application_compat import LegacyApplicationService
    from tests.integration.test_pr08_application import create_command

    from researchbase.application.commands import FreezeMetricDefinitionCommand
    from researchbase.domain.organization import ProjectId
    from researchbase.foundation.execution_context import ExecutionContext
    from researchbase.foundation.ids import new_uuid7
    from researchbase.foundation.time import SystemClock

    p = planning
    app = LegacyApplicationService(p.factory, SystemClock(), p.store)
    context = ExecutionContext(
        actor_id=p.principal.actor_id, request_id=new_uuid7(), client_type="test"
    )
    metric = app.create_metric_definition(create_command(context, ProjectId(p.project)))
    frozen = app.freeze_metric_definition(
        FreezeMetricDefinitionCommand(metric.id, metric.current_version_id, context, 1)
    )
    task = p.create()
    c = command(
        p,
        task,
        1,
        "bind_task_policies",
        dict(
            budget_id=str(new_uuid7()),
            budget={"pricing_basis": "fake-usd-v1"},
            termination_policy_id=str(new_uuid7()),
            termination={
                "score_metric_version_id": str(frozen.id),
                "score_direction": "MAXIMIZE",
                "evaluator_version": "fake-score-v1",
            },
            checkpoint_policy_id=str(new_uuid7()),
            checkpoint={},
            reason="Comparable fake iterations.",
        ),
    )
    service(p).execute(p.principal, c)
    approve(p, task, 2)
    approve(p, task, 4, kind="code_risk")
    fake = TrustedFakeConsumer(p.factory, Credentials(), p.store)
    revision = 6
    for i, score in enumerate(("0.500000", "0.500000", "0.400000")):
        result = fake.execute(p.principal, reserve(p, task, revision, code_iterations=1))
        observation = settle(
            p, task, revision + 1, result.reservation_ids[0], measured=resources(code_iterations=1)
        )
        if i == 0:
            with pytest.raises(ResearchBaseError) as exc:
                fake.execute(p.principal, observation)
            assert exc.value.code == ErrorCode.INVALID_STATE_TRANSITION
        observation = replace(
            observation,
            arguments=replace(
                observation.arguments, score=Decimal(score), evaluator_version="fake-score-v1"
            ),
        )
        fake.execute(p.principal, observation)
        revision += 2
    view = fake.reconstruct(p.principal, p.project, task)
    assert view.stop_causes == ("BUDGET_EXHAUSTED", "NO_IMPROVEMENT")
    assert view.consumed.code_iterations == 3


def test_wall_budget_includes_human_wait_and_does_not_refund_unknown(planning):
    from sqlalchemy import text

    from researchbase.foundation.ids import new_uuid7

    p = planning
    task, fake = setup(p, max_wall_time_seconds=1)
    fake.execute(p.principal, reserve(p, task, 4))
    service(p).execute(
        p.principal,
        command(
            p,
            task,
            5,
            "request_human_checkpoint",
            dict(
                checkpoint_id=str(new_uuid7()),
                step_id=None,
                checkpoint_type="exception",
                reason="Human wait after admission.",
            ),
        ),
    )
    with p.engine.connect() as conn:
        conn.execute(
            text(
                "SELECT pg_sleep(greatest(0,extract(epoch FROM (min(created_at)+interval '1 second'-clock_timestamp())))) FROM budget_reservations WHERE research_task_id=:id"  # noqa: E501
            ),
            {"id": task},
        )
    service(p).execute(
        p.principal,
        command(p, task, 6, "evaluate_task_termination", {"reason": "Elapsed wall cap."}),
    )
    view = fake.reconstruct(p.principal, p.project, task)
    assert view.elapsed_wall_seconds >= 1 and view.stop_causes == ("BUDGET_EXHAUSTED",)
    assert view.reserved.llm_calls == 1 and view.parallel_branches == 1
    with pytest.raises(ResearchBaseError):
        fake.execute(p.principal, reserve(p, task, 7))
