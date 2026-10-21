# ruff: noqa: E501
"""Atomic planning and read projection behavior on PostgreSQL 18."""

import pytest

from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.ids import new_uuid7


def test_task_plan_seal_cancel_and_snapshot(planning):
    task, command = planning.plan()
    service, p = planning.service, planning.principal
    graph = service.get_task_graph(p, planning.project, task)
    assert graph.task.row_version == 2 and len(graph.nodes) == 2
    assert len(graph.task_events) == 2 and len(graph.step_events) == 2
    service.execute(p, planning.command("seal_task_plan", task, 2))
    sealed = service.get_research_task(p, planning.project, task)
    assert sealed.plan_sealed_at is not None and not sealed.execution_enabled
    service.execute(p, planning.command("cancel_research_task", task, 3, {"reason": "Withdrawn"}))
    graph = service.get_task_graph(p, planning.project, task)
    assert graph.task.row_version == 4 and all(n.status == "CANCELLED" for n in graph.nodes)
    assert all(n.finished_at == graph.task.finished_at for n in graph.nodes)
    progress = service.get_task_progress(p, planning.project, task)
    assert progress.completion_percent == 0 and progress.counts.CANCELLED == 2


def test_add_step_and_edge(planning):
    task, _ = planning.plan()
    graph = planning.service.get_task_graph(planning.principal, planning.project, task)
    identity = new_uuid7()
    planning.service.execute(
        planning.principal,
        planning.command(
            "add_task_step",
            task,
            2,
            {
                "node": {"step_id": str(identity), "step_type": "ANALYZE", "ordinal": 3},
                "predecessor_ids": [str(graph.nodes[0].id)],
            },
        ),
    )
    planning.service.execute(
        planning.principal,
        planning.command(
            "add_task_step_dependency",
            task,
            3,
            {"predecessor_id": str(graph.nodes[1].id), "dependent_id": str(identity)},
        ),
    )
    graph = planning.service.get_task_graph(planning.principal, planning.project, task)
    assert len(graph.nodes) == 3 and len(graph.edges) == 2 and graph.task.row_version == 4


def test_failed_plan_has_zero_protected_effects(planning):
    task = planning.create()
    a, b = new_uuid7(), new_uuid7()
    cmd = planning.command(
        "create_task_plan",
        task,
        1,
        {
            "nodes": [
                {"step_id": str(a), "ordinal": 1, "step_type": "PLAN"},
                {"step_id": str(b), "ordinal": 2, "step_type": "RESEARCH"},
            ],
            "edges": [
                {"predecessor_id": str(a), "dependent_id": str(b)},
                {"predecessor_id": str(b), "dependent_id": str(a)},
            ],
        },
    )
    with pytest.raises(ResearchBaseError) as caught:
        planning.service.execute(planning.principal, cmd)
    assert caught.value.code == ErrorCode.VALIDATION_ERROR
    graph = planning.service.get_task_graph(planning.principal, planning.project, task)
    assert not graph.nodes and graph.task.row_version == 1 and len(graph.task_events) == 1


def test_planning_does_not_mutate_scientific_rows(planning, scientific_inputs):
    from tests.integration.phase3.test_pr3_00_bootstrap import _rows

    before = {
        table: rows
        for table, rows in _rows(planning.engine).items()
        if not table.startswith("research_task")
    }
    cmd = planning.command(
        arguments={
            "task_type": "OTHER",
            "objective": "Inspect all inputs",
            "strategy_id": "fixed",
            "strategy_version": "1",
            "inputs": [
                {"type": kind, "id": str(identity)} for kind, identity in scientific_inputs.items()
            ],
        }
    )
    planning.service.execute(planning.principal, cmd)
    planning.plan(cmd.task_id)
    planning.service.execute(planning.principal, planning.command("seal_task_plan", cmd.task_id, 2))
    planning.service.execute(
        planning.principal,
        planning.command("cancel_research_task", cmd.task_id, 3, {"reason": "Finished planning"}),
    )
    after = {
        table: rows
        for table, rows in _rows(planning.engine).items()
        if not table.startswith("research_task")
    }
    assert before == after


def test_unbound_agent_denied_without_human_attribution(planning):
    from dataclasses import replace

    from sqlalchemy import text

    actor = new_uuid7()
    with planning.engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO actors(id,actor_type,display_name,created_at) VALUES (:id,'AGENT','Unbound test agent',clock_timestamp())"
            ),
            {"id": actor},
        )
    agent = replace(planning.principal, actor_id=actor)
    cmd = planning.command()
    with pytest.raises(ResearchBaseError) as caught:
        planning.service.execute(agent, cmd)
    assert caught.value.code == ErrorCode.FORBIDDEN
    with planning.engine.connect() as conn:
        assert (
            conn.execute(
                text("SELECT count(*) FROM research_tasks WHERE id=:id"), {"id": cmd.task_id}
            ).scalar_one()
            == 0
        )
        assert (
            conn.execute(
                text("SELECT count(*) FROM research_task_events WHERE actor_id=:id"), {"id": actor}
            ).scalar_one()
            == 0
        )


def test_empty_progress_and_reserved_execution_denial(planning):
    task = planning.create()
    view = planning.service.get_task_progress(planning.principal, planning.project, task)
    assert view.total_steps == view.completed_steps == view.completion_percent == 0
    assert not view.execution_enabled and len(view.unmet_prerequisites) == 4
    for name in (
        "start_research_task",
        "pause_research_task",
        "resume_research_task",
        "start_task_step",
        "finish_task_step",
        "fail_task_step",
    ):
        args = {"step_id": str(new_uuid7())} if "task_step" in name else {}
        cmd = planning.command(name, task, 1, args)
        with pytest.raises(ResearchBaseError) as caught:
            getattr(planning.service, name)(planning.principal, cmd)
        assert caught.value.code == ErrorCode.INVALID_STATE_TRANSITION
        assert caught.value.details == {"reason": "EXECUTION_PREREQUISITES_UNMET"}
    assert (
        planning.service.get_research_task(planning.principal, planning.project, task).row_version
        == 1
    )


def test_frozen_input_validation_never_calls_external_store_under_locks(
    planning, scientific_inputs
):
    from tests.integration.phase3.conftest import Credentials

    from researchbase.agent_runtime.application.research_task import ResearchTaskService

    class NoExternalIO:
        def verify(self, *args):
            raise AssertionError("external I/O under planning locks")

        def open(self, *args):
            raise AssertionError("external I/O under planning locks")

    service = ResearchTaskService(planning.factory, Credentials(), NoExternalIO())
    cmd = planning.command(
        arguments={
            "task_type": "OTHER",
            "objective": "Snapshot references",
            "strategy_id": "fixed",
            "strategy_version": "1",
            "inputs": [
                {"type": kind, "id": str(identity)} for kind, identity in scientific_inputs.items()
            ],
        }
    )
    service.execute(planning.principal, cmd)
    assert (
        len(service.get_research_task(planning.principal, planning.project, cmd.task_id).inputs)
        == 6
    )
