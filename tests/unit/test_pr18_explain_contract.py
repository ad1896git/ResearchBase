from __future__ import annotations

import pytest
from scripts.pr18_evidence import PR18EvidenceError, validate_query_contract
from tests.contracts.pr18_manifest import FROZEN_QUERY_EXPECTATIONS


def _statement(
    sql: str, *, relations: list[str], nodes: list[str] | None = None
) -> dict[str, object]:
    return {
        "sql": sql,
        "plan": {
            "relations": relations,
            "node_types": nodes or ["Index Scan"],
            "join_types": [],
        },
    }


def test_query_contract_is_frozen_independently_of_observed_plan() -> None:
    expectation = FROZEN_QUERY_EXPECTATIONS["audit_findings"]

    assert expectation["application_method"] == "GovernanceQueryService.list_audit_findings"
    assert expectation["required_relations"] == ("audit_findings",)
    assert expectation["required_predicates"]
    assert expectation["topology"]["mode"] == "batched_single_relation_selects"  # type: ignore[index]


def test_query_contract_rejects_missing_required_relation() -> None:
    expectation = FROZEN_QUERY_EXPECTATIONS["audit_findings"]
    statements = [
        _statement(
            (
                "SELECT audit_findings.id FROM audit_findings "
                "WHERE audit_findings.project_id = :project"
            ),
            relations=[],
        )
    ]

    with pytest.raises(PR18EvidenceError, match="required relation"):
        validate_query_contract(expectation, statements)


def test_query_contract_rejects_missing_frozen_predicate() -> None:
    expectation = FROZEN_QUERY_EXPECTATIONS["audit_findings"]
    statements = [
        _statement(
            (
                "SELECT audit_findings.id FROM audit_findings "
                "WHERE audit_findings.project_id = :project"
            ),
            relations=["audit_findings"],
        )
    ]

    with pytest.raises(PR18EvidenceError, match="predicate"):
        validate_query_contract(expectation, statements)


def test_query_contract_rejects_wrong_join_topology() -> None:
    expectation = FROZEN_QUERY_EXPECTATIONS["downstream_impact"]
    statements = [
        _statement(
            "SELECT * FROM run_artifact_inputs JOIN runs ON true",
            relations=["run_artifact_inputs", "runs"],
            nodes=["Nested Loop"],
        )
    ]

    with pytest.raises(PR18EvidenceError, match="required relation|predicate|topology"):
        validate_query_contract(expectation, statements)
