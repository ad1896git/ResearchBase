from __future__ import annotations

from copy import deepcopy
from typing import cast

import pytest
from scripts.pr18_evidence import PR18EvidenceError, validate_query_contract
from tests.contracts.pr18_manifest import FROZEN_QUERY_EXPECTATIONS


def _statement(
    sql: str,
    *,
    relations: list[str],
    nodes: list[str] | None = None,
    join_types: list[str] | None = None,
) -> dict[str, object]:
    return {
        "sql": sql,
        "plan": {
            "relations": relations,
            "node_types": nodes or ["Index Scan"],
            "join_types": join_types or [],
        },
    }


def _downstream_expectation() -> dict[str, object]:
    expectation = deepcopy(FROZEN_QUERY_EXPECTATIONS["downstream_impact"])
    topology = dict(cast(dict[str, object], expectation["topology"]))
    topology.update(
        {
            "allowed_relations": expectation["required_relations"],
            "closed_relation_set": True,
            "allow_single_relation_reads": True,
            "allow_cartesian_joins": False,
            "required_join_edges": (
                (
                    "artifact belongs to project",
                    ("artifacts", "artifact_versions"),
                    r"\bartifact_versions\.artifact_id\s*=\s*artifacts\.id\b",
                ),
                (
                    "run input reaches run",
                    ("run_artifact_inputs", "runs"),
                    r"\bruns\.id\s*=\s*run_artifact_inputs\.run_id\b",
                ),
                (
                    "measurement reaches statistical input",
                    ("measurements", "statistical_result_inputs"),
                    r"\bmeasurements\.id\s*=\s*statistical_result_inputs\.measurement_id\b",
                ),
                (
                    "statistical input reaches result",
                    ("statistical_result_inputs", "statistical_results"),
                    r"\bstatistical_results\.id\s*=\s*statistical_result_inputs\.statistical_result_id\b",
                ),
                (
                    "measurement reaches claim evidence",
                    ("evidence_relations", "claim_versions"),
                    r"\bclaim_versions\.id\s*=\s*evidence_relations\.claim_version_id\b",
                ),
                (
                    "claim version reaches claim",
                    ("claim_versions", "claims"),
                    r"\bclaims\.id\s*=\s*claim_versions\.claim_id\b",
                ),
            ),
            "allowed_join_edges": (),
        }
    )
    topology["allowed_join_edges"] = topology["required_join_edges"]
    expectation["topology"] = topology
    return expectation


def _valid_downstream_statements() -> list[dict[str, object]]:
    return [
        _statement(
            "SELECT artifacts.project_id, artifact_versions.content_hash "
            "FROM artifacts JOIN artifact_versions "
            "ON artifact_versions.artifact_id = artifacts.id "
            "WHERE artifact_versions.id = :id AND artifacts.project_id = :project",
            relations=["artifacts", "artifact_versions"],
            nodes=["Nested Loop", "Index Scan"],
            join_types=["Inner"],
        ),
        _statement(
            "SELECT run_artifact_inputs.run_id FROM run_artifact_inputs JOIN runs "
            "ON runs.id = run_artifact_inputs.run_id "
            "WHERE run_artifact_inputs.artifact_version_id = :artifact "
            "AND runs.project_id = :project",
            relations=["run_artifact_inputs", "runs"],
            nodes=["Nested Loop", "Index Scan"],
            join_types=["Inner"],
        ),
        _statement(
            "SELECT measurements.run_id, measurements.id FROM measurements "
            "WHERE measurements.run_id IN (:run_id)",
            relations=["measurements"],
        ),
        _statement(
            "SELECT statistical_result_inputs.measurement_id "
            "FROM statistical_result_inputs JOIN measurements "
            "ON measurements.id = statistical_result_inputs.measurement_id "
            "JOIN statistical_results "
            "ON statistical_results.id = statistical_result_inputs.statistical_result_id "
            "WHERE statistical_result_inputs.measurement_id IN (:measurement) "
            "AND statistical_results.project_id = :project",
            relations=["statistical_result_inputs", "measurements", "statistical_results"],
            nodes=["Nested Loop", "Index Scan"],
            join_types=["Inner"],
        ),
        _statement(
            "SELECT evidence_relations.id FROM evidence_relations JOIN claim_versions "
            "ON claim_versions.id = evidence_relations.claim_version_id "
            "JOIN claims ON claims.id = claim_versions.claim_id "
            "WHERE evidence_relations.measurement_id IN (:measurement) "
            "AND claims.project_id = :project",
            relations=["evidence_relations", "claim_versions", "claims"],
            nodes=["Nested Loop", "Index Scan"],
            join_types=["Inner"],
        ),
        _statement(
            "SELECT evidence_relations.id FROM evidence_relations JOIN claim_versions "
            "ON claim_versions.id = evidence_relations.claim_version_id "
            "JOIN claims ON claims.id = claim_versions.claim_id "
            "WHERE evidence_relations.statistical_result_id IN (:statistical) "
            "AND claims.project_id = :project",
            relations=["evidence_relations", "claim_versions", "claims"],
            nodes=["Nested Loop", "Index Scan"],
            join_types=["Inner"],
        ),
    ]


def test_query_contract_is_frozen_independently_of_observed_plan() -> None:
    expectation = FROZEN_QUERY_EXPECTATIONS["audit_findings"]

    assert expectation["application_method"] == "GovernanceQueryService.list_audit_findings"
    assert expectation["required_relations"] == ("audit_findings",)
    assert expectation["required_predicates"]
    assert expectation["topology"]["mode"] == "batched_single_relation_selects"  # type: ignore[index]


def test_each_production_query_has_an_explicit_topology_contract() -> None:
    assert set(FROZEN_QUERY_EXPECTATIONS) == {
        "run_provenance",
        "claim_trace",
        "downstream_impact",
        "audit_findings",
    }
    for expectation in FROZEN_QUERY_EXPECTATIONS.values():
        topology = expectation["topology"]
        assert isinstance(topology, dict)
        assert topology["closed_relation_set"] is True
        required_relations = cast(tuple[str, ...], expectation["required_relations"])
        allowed_relations = cast(tuple[str, ...], topology["allowed_relations"])
        assert set(required_relations) <= set(allowed_relations)
        assert topology["forbidden_join_edges"] == "all_unlisted"
        assert topology["allow_cartesian_joins"] is False
        assert topology["forbidden_cartesian_joins"] is True


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

    with pytest.raises(PR18EvidenceError, match="MISSING_REQUIRED_RELATION"):
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

    with pytest.raises(PR18EvidenceError, match="MISSING_REQUIRED_PREDICATE"):
        validate_query_contract(expectation, statements)


def test_query_contract_rejects_wrong_join_topology() -> None:
    expectation = _downstream_expectation()
    statements = _valid_downstream_statements()
    statements[1] = _statement(
        "SELECT run_artifact_inputs.run_id FROM run_artifact_inputs JOIN runs "
        "ON runs.project_id = run_artifact_inputs.artifact_version_id "
        "WHERE run_artifact_inputs.artifact_version_id = :artifact "
        "AND runs.project_id = :project",
        relations=["run_artifact_inputs", "runs"],
        nodes=["Nested Loop", "Index Scan"],
        join_types=["Inner"],
    )

    with pytest.raises(PR18EvidenceError, match="INVALID_JOIN_TOPOLOGY"):
        validate_query_contract(expectation, statements)


def test_query_contract_rejects_unexpected_extra_relation_in_isolation() -> None:
    expectation = _downstream_expectation()
    statements = _valid_downstream_statements()
    statements.append(
        _statement(
            "SELECT unauthorized_relation.id FROM unauthorized_relation "
            "WHERE unauthorized_relation.id = :id",
            relations=["unauthorized_relation"],
        )
    )

    with pytest.raises(PR18EvidenceError, match="UNEXPECTED_RELATION"):
        validate_query_contract(expectation, statements)


def test_query_contract_rejects_cartesian_join_in_isolation() -> None:
    expectation = _downstream_expectation()
    statements = _valid_downstream_statements()
    statements[1] = _statement(
        "SELECT run_artifact_inputs.run_id FROM run_artifact_inputs JOIN runs ON true "
        "WHERE run_artifact_inputs.artifact_version_id = :artifact "
        "AND runs.project_id = :project",
        relations=["run_artifact_inputs", "runs"],
        nodes=["Nested Loop", "Index Scan"],
        join_types=["Inner"],
    )

    with pytest.raises(PR18EvidenceError, match="CARTESIAN_JOIN"):
        validate_query_contract(expectation, statements)


def test_query_contract_rejects_disconnected_join_graph_in_isolation() -> None:
    expectation = _downstream_expectation()
    statements = _valid_downstream_statements()
    statements[1] = _statement(
        "SELECT run_artifact_inputs.run_id FROM run_artifact_inputs, runs "
        "WHERE run_artifact_inputs.artifact_version_id = :artifact "
        "AND runs.project_id = :project",
        relations=["run_artifact_inputs", "runs"],
    )

    with pytest.raises(PR18EvidenceError, match="INVALID_JOIN_TOPOLOGY"):
        validate_query_contract(expectation, statements)


def test_query_contract_accepts_legal_production_topology_control() -> None:
    projection = validate_query_contract(_downstream_expectation(), _valid_downstream_statements())

    assert projection["unexpected_relations"] == []
    assert projection["missing_relations"] == []
    assert projection["predicate_verdict"] == "PASS"
    assert projection["topology_verdict"] == "PASS"
    assert projection["cartesian_verdict"] == "PASS"
    assert projection["overall_verdict"] == "PASS"


def test_query_contract_rejects_unparseable_topology_fail_closed() -> None:
    expectation = _downstream_expectation()
    statements = _valid_downstream_statements()
    statements[1]["sql"] = (
        "SELECT run_artifact_inputs.run_id FROM run_artifact_inputs JOIN runs "
        "WHERE run_artifact_inputs.artifact_version_id = :artifact "
        "AND runs.project_id = :project"
    )

    with pytest.raises(PR18EvidenceError, match="CARTESIAN_JOIN|INVALID_JOIN_TOPOLOGY"):
        validate_query_contract(expectation, statements)
