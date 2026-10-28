"""Pure search intent values and structural predicates; no admission or execution."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from researchbase.agent_runtime.domain.research_task import exact_uuid, invalid
from researchbase.agent_runtime.domain.tool_policy import digest_value

MAX_SEARCH_NODES = 10
MAX_SEARCH_DEPTH = 3
MAX_SEARCH_EVENTS = 11
MAX_SEARCH_RUN_LINKS = 0


def search_profile_allowed(*, nodes: int, depth: int, events: int, run_links: int) -> bool:
    """Check the frozen structural response bounds, without reads or budget admission."""
    return all(
        type(value) is int and 0 <= value <= limit
        for value, limit in (
            (nodes, MAX_SEARCH_NODES),
            (depth, MAX_SEARCH_DEPTH),
            (events, MAX_SEARCH_EVENTS),
            (run_links, MAX_SEARCH_RUN_LINKS),
        )
    )


class BranchKind(StrEnum):
    NEW_DIRECTION = "NEW_DIRECTION"
    REFINEMENT = "REFINEMENT"
    ABLATION = "ABLATION"
    BASELINE = "BASELINE"
    SCALE_UP = "SCALE_UP"
    DEBUG = "DEBUG"
    REPLICATION = "REPLICATION"


@dataclass(frozen=True, slots=True)
class ExactReference:
    version_id: UUID | None
    content_hash: str | None

    def __post_init__(self) -> None:
        if (self.version_id is None) != (self.content_hash is None):
            invalid("reference and owning hash must be present together")
        if self.version_id is not None:
            exact_uuid(self.version_id)
            digest_value(self.content_hash)


@dataclass(frozen=True, slots=True)
class ObjectiveDefinition:
    research_task_id: UUID
    text: str

    def __post_init__(self) -> None:
        exact_uuid(self.research_task_id, stable=True)
        if not isinstance(self.text, str):
            invalid("owning task objective must be text")

    def projection(self) -> dict[str, str]:
        return {
            "source": "RESEARCH_TASK",
            "research_task_id": str(self.research_task_id),
            "text": self.text,
        }


def append_structure_allowed(
    *,
    parent_id: UUID | None,
    node_id: UUID,
    depth: int,
    parent_depth: int | None,
    ancestor_states: tuple[str, ...],
    session_status: str,
    task_status: str,
    has_root: bool,
) -> bool:
    """Evaluate only frozen structure/lifecycle conditions, never budget admission."""
    exact_uuid(node_id, stable=True)
    if parent_id is not None:
        exact_uuid(parent_id, stable=True)
    if type(depth) is not int or not 0 <= depth <= MAX_SEARCH_DEPTH:
        return False
    if session_status != "ACTIVE" or task_status not in {"CREATED", "PLANNING"}:
        return False
    if parent_id is None:
        return depth == 0 and parent_depth is None and not ancestor_states and not has_root
    return (
        has_root is True
        and parent_id != node_id
        and type(parent_depth) is int
        and parent_depth >= 0
        and depth == parent_depth + 1
        and len(ancestor_states) == depth
        and all(state == "PROPOSED" for state in ancestor_states)
    )
