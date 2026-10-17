"""Owner-approved B27 extension to the unchanged Phase 1 query-plan contract.

This inventory follows B27's required owning-identity resolution, independently
of captured SQL. Existing purity, topology and predicate requirements remain.
"""

from copy import deepcopy
from typing import Final, cast

from tests.contracts.pr18_manifest import FROZEN_QUERY_EXPECTATIONS

_OWNER_RELATIONS: Final = ("experiment_specs", "datasets", "artifacts", "metric_definitions")
_OWNER_METHODS: Final = tuple(f"{name}.get_many" for name in _OWNER_RELATIONS)
_OWNER_PREDICATES: Final = tuple(
    (f"B27 {name} owner identity batch", rf"\b{name}\.id\s+IN\s*\(") for name in _OWNER_RELATIONS
)


def _expectations() -> dict[str, dict[str, object]]:
    current = deepcopy(FROZEN_QUERY_EXPECTATIONS)
    for name in ("run_provenance", "claim_trace"):
        expectation = current[name]
        expectation["repository_methods"] = (
            *cast(tuple[str, ...], expectation["repository_methods"]),
            *_OWNER_METHODS,
        )
        expectation["required_relations"] = (
            *cast(tuple[str, ...], expectation["required_relations"]),
            *_OWNER_RELATIONS,
        )
        expectation["required_predicates"] = (
            *cast(tuple[tuple[str, str], ...], expectation["required_predicates"]),
            *_OWNER_PREDICATES,
        )
        topology = cast(dict[str, object], expectation["topology"])
        topology["allowed_relations"] = (
            *cast(tuple[str, ...], topology["allowed_relations"]),
            *_OWNER_RELATIONS,
        )
    return current


B27_QUERY_EXPECTATIONS: Final = _expectations()
