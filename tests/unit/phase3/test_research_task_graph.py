"""Pure DAG/forest and planning state matrices; display order is independent."""

from itertools import product

import pytest

from researchbase.agent_runtime.application.contracts import PlanEdge, PlanNode
from researchbase.agent_runtime.domain.research_task import (
    COMMAND_EVENTS,
    EXECUTION_COMMANDS,
    TaskStatus,
    require_transition,
)
from researchbase.agent_runtime.domain.task_graph import validate_graph
from researchbase.agent_runtime.domain.task_step import StepType, predecessors_succeeded
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.ids import new_uuid7


def node(ordinal, **kwargs):
    return PlanNode(new_uuid7(), StepType.PLAN, ordinal, **kwargs)


@pytest.mark.parametrize(
    "command,status,sealed",
    product(
        tuple(COMMAND_EVENTS)[1:] + tuple(EXECUTION_COMMANDS), tuple(TaskStatus), (False, True)
    ),
)
def test_transition_matrix(command, status, sealed):
    allowed = (command == "cancel_research_task" and status != "CANCELLED") or (
        not sealed
        and (
            (command == "create_task_plan" and status == "CREATED")
            or (
                command in {"add_task_step", "add_task_step_dependency", "seal_task_plan"}
                and status == "PLANNING"
            )
        )
    )
    if allowed:
        require_transition(command, status, sealed)
    else:
        with pytest.raises(ResearchBaseError) as caught:
            require_transition(command, status, sealed)
        expected = (
            ErrorCode.INVALID_STATE_TRANSITION
            if command in EXECUTION_COMMANDS
            or (status != "CANCELLED" and not sealed)
            or (command == "cancel_research_task" and status == "CANCELLED")
            or (command == "seal_task_plan" and sealed)
            else ErrorCode.IMMUTABLE_RECORD
        )
        assert caught.value.code == expected
        if command in EXECUTION_COMMANDS:
            assert caught.value.details == {"reason": "EXECUTION_PREREQUISITES_UNMET"}


@pytest.mark.parametrize("kind", tuple(StepType))
def test_declared_steps(kind):
    assert PlanNode(new_uuid7(), kind, 1).step_type == kind


def test_diamond_disconnected_and_ordinal_not_dependency():
    nodes = tuple(node(i) for i in (5, 4, 3, 2, 1))
    a, b, c, d, _ = [n.step_id for n in nodes]
    edges = tuple(PlanEdge(x, y) for x, y in ((a, b), (a, c), (b, d), (c, d)))
    validate_graph(nodes, edges)
    validate_graph(tuple(reversed(nodes)), tuple(reversed(edges)))


@pytest.mark.parametrize(
    "case",
    (
        "self",
        "duplicate",
        "foreign",
        "cycle",
        "parent_self",
        "parent_cycle",
        "parent_foreign",
        "ordinal",
        "node",
    ),
)
def test_reject_bad_graph(case):
    a, b = node(1), node(2)
    edges = ()
    if case == "self":
        edges = (PlanEdge(a.step_id, a.step_id),)
    elif case == "duplicate":
        edges = (PlanEdge(a.step_id, b.step_id),) * 2
    elif case == "foreign":
        edges = (PlanEdge(a.step_id, new_uuid7()),)
    elif case == "cycle":
        edges = (PlanEdge(a.step_id, b.step_id), PlanEdge(b.step_id, a.step_id))
    elif case == "parent_self":
        a = PlanNode(a.step_id, StepType.PLAN, 1, parent_step_id=a.step_id)
    elif case == "parent_cycle":
        a = PlanNode(a.step_id, StepType.PLAN, 1, parent_step_id=b.step_id)
        b = PlanNode(b.step_id, StepType.PLAN, 2, parent_step_id=a.step_id)
    elif case == "parent_foreign":
        a = PlanNode(a.step_id, StepType.PLAN, 1, parent_step_id=new_uuid7())
    elif case == "ordinal":
        b = PlanNode(b.step_id, StepType.PLAN, 1)
    elif case == "node":
        b = a
    with pytest.raises(ResearchBaseError):
        validate_graph((a, b), edges)


@pytest.mark.parametrize(
    "status", ("FAILED", "SKIPPED", "CANCELLED", "WAITING", "READY", "RUNNING", "PENDING")
)
def test_failed_or_skipped_is_never_readiness(status):
    assert not predecessors_succeeded(("SUCCEEDED", status))


def test_maximum_graph_and_limits():
    nodes = tuple(node(i + 1) for i in range(256))
    edges = tuple(
        PlanEdge(nodes[i].step_id, nodes[j].step_id) for i in range(256) for j in range(i + 1, 256)
    )[:1024]
    validate_graph(nodes, edges, 256)
    for ns, es, count in (
        (nodes + (node(257),), edges, 256),
        (nodes, edges + (PlanEdge(nodes[200].step_id, nodes[201].step_id),), 256),
        (nodes, edges, 257),
    ):
        with pytest.raises(ResearchBaseError):
            validate_graph(ns, es, count)
