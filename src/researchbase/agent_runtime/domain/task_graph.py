"""Bounded DAG validation with Kahn and independent three-color parent DFS."""

from collections import deque
from typing import Protocol
from uuid import UUID

from researchbase.agent_runtime.domain.research_task import invalid


class GraphNode(Protocol):
    @property
    def step_id(self) -> UUID: ...
    @property
    def ordinal(self) -> int: ...
    @property
    def parent_step_id(self) -> UUID | None: ...


class GraphEdge(Protocol):
    @property
    def predecessor_id(self) -> UUID: ...
    @property
    def dependent_id(self) -> UUID: ...


def unique(values, message: str) -> None:
    if len(values) != len(set(values)):
        invalid(message)


def validate_graph(
    nodes: tuple[GraphNode, ...], edges: tuple[GraphEdge, ...], inputs: int = 0
) -> None:
    if len(nodes) > 256 or len(edges) > 1024 or inputs > 256:
        invalid("graph admission limit exceeded")
    unique([n.step_id for n in nodes], "duplicate step")
    unique([n.ordinal for n in nodes], "duplicate ordinal")
    unique([(e.predecessor_id, e.dependent_id) for e in edges], "duplicate edge")
    by_id = {n.step_id: n for n in nodes}
    degree = dict.fromkeys(by_id, 0)
    outgoing: dict[UUID, list[UUID]] = {identity: [] for identity in by_id}
    for edge in edges:
        a, b = edge.predecessor_id, edge.dependent_id
        if a == b or a not in by_id or b not in by_id:
            invalid("dependency endpoints must be distinct nodes in this task")
        outgoing[a].append(b)
        degree[b] += 1
    queue = deque(identity for identity, count in degree.items() if count == 0)
    visited = 0
    while queue:
        identity = queue.popleft()
        visited += 1
        for child in outgoing[identity]:
            degree[child] -= 1
            if degree[child] == 0:
                queue.append(child)
    if visited != len(nodes):
        invalid("dependency cycle", "DAG_CYCLE")
    color = dict.fromkeys(by_id, 0)

    def visit(identity: UUID) -> None:
        if color[identity] == 1:
            invalid("parent cycle", "PARENT_CYCLE")
        if color[identity] == 2:
            return
        color[identity] = 1
        parent = by_id[identity].parent_step_id
        if parent is not None:
            if parent not in by_id:
                invalid("parent must belong to this task")
            visit(parent)
        color[identity] = 2

    for identity in by_id:
        visit(identity)
