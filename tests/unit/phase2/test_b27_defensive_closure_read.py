"""Exact saved-dependency errors and unchanged diagnostic batch semantics."""

from uuid import UUID

import pytest

from researchbase.api.errors import _STATUS
from researchbase.application.closure import BatchLookup, BatchLookupState
from researchbase.application.saved_provenance import MESSAGE, saved_dependency
from researchbase.cli.errors import CLI_EXIT_CODES
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


@pytest.mark.parametrize("values", [{}, {UUID(int=1): "found"}])
def test_all_missing_and_mixed_batches_keep_requested_membership(values):
    batch = BatchLookup(values, frozenset({UUID(int=1), UUID(int=2)}))
    assert batch.resolve(UUID(int=2)) == (BatchLookupState.MISSING, None)
    assert batch.resolve(UUID(int=3)) == (BatchLookupState.NEVER_REQUESTED, None)
    assert batch.missing_ids == frozenset({UUID(int=1), UUID(int=2)}) - values.keys()


@pytest.mark.parametrize(
    "code",
    [
        ErrorCode.NOT_FOUND,
        ErrorCode.FROZEN_REFERENCE_REQUIRED,
        ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
    ],
)
def test_known_saved_failures_are_sanitized(code):
    with pytest.raises(ResearchBaseError) as denied, saved_dependency():
        raise ResearchBaseError(code, "secret dependency UUID", {"id": "secret"})
    assert denied.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    assert denied.value.message == MESSAGE
    assert denied.value.details is None
    assert _STATUS[denied.value.code] == 409
    assert CLI_EXIT_CODES[denied.value.code] == 5


@pytest.mark.parametrize(
    "error",
    [
        RuntimeError("programming"),
        TimeoutError("timeout"),
        ResearchBaseError(ErrorCode.FORBIDDEN, "authorization"),
    ],
)
def test_unexpected_errors_are_not_relabelled(error):
    with pytest.raises(type(error)) as denied, saved_dependency():
        raise error
    assert denied.value is error


def test_root_not_found_remains_not_found_outside_saved_boundary():
    with pytest.raises(ResearchBaseError) as denied:
        raise ResearchBaseError(ErrorCode.NOT_FOUND, "root not found")
    assert denied.value.code is ErrorCode.NOT_FOUND


def test_existing_transport_adapters_emit_sanitized_closure():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from researchbase.api.errors import install_error_handlers
    from researchbase.cli.errors import cli_exit_code, error_code, error_details

    app = FastAPI()
    install_error_handlers(app)
    failure = ResearchBaseError(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, MESSAGE)

    @app.get("/test-saved-read")
    def read():
        raise failure

    response = TestClient(app).get("/test-saved-read")
    assert response.status_code == 409
    assert response.json()["error"] == {
        "code": "PROVENANCE_CLOSURE_VIOLATION",
        "message": MESSAGE,
        "details": None,
    }
    assert cli_exit_code(failure) == 5
    assert error_code(failure) == response.json()["error"]["code"]
    assert error_details(failure) is None


def test_required_trace_dtos_remain_nonnullable():
    from typing import get_type_hints

    from researchbase.application.manuscript_scientific_trace import (
        ClaimExperimentEvidenceTrace,
        LiteratureEvidenceTrace,
        PlacementTraceItem,
    )

    for dto, field, expected in [
        (ClaimExperimentEvidenceTrace, "measurement_id", UUID),
        (ClaimExperimentEvidenceTrace, "run_id", UUID),
        (LiteratureEvidenceTrace, "evidence_content_hash", str),
        (LiteratureEvidenceTrace, "source_version_id", UUID),
        (PlacementTraceItem, "target_content_hash", str),
    ]:
        assert get_type_hints(dto)[field] is expected


@pytest.mark.parametrize("kind", ["Dataset", "Artifact", "MetricDefinition", "ExperimentSpec"])
def test_owner_validation_preserves_existing_global_scope_policy(kind):
    from types import SimpleNamespace

    from researchbase.application.closure import ProvenanceClosureValidator

    violations = []
    repository = SimpleNamespace(get=lambda identity: SimpleNamespace(project_id=None))
    ProvenanceClosureValidator._owner(
        repository, None, UUID(int=1), kind, UUID(int=2), ["owner"], violations
    )
    assert len(violations) == (1 if kind == "ExperimentSpec" else 0)
    repository.get = lambda identity: None
    violations = []
    ProvenanceClosureValidator._owner(
        repository, None, UUID(int=1), kind, UUID(int=2), ["owner"], violations
    )
    assert len(violations) == 1 and violations[0].code == "NOT_FOUND"


@pytest.mark.parametrize("name", ["run_provenance", "claim_trace"])
def test_b27_plan_contract_adds_only_required_batched_owner_reads(name):
    from typing import cast

    from tests.contracts.b27_query_contract import B27_QUERY_EXPECTATIONS
    from tests.contracts.pr18_manifest import FROZEN_QUERY_EXPECTATIONS

    baseline = FROZEN_QUERY_EXPECTATIONS[name]
    current = B27_QUERY_EXPECTATIONS[name]
    owners = {"experiment_specs", "datasets", "artifacts", "metric_definitions"}
    baseline_relations = cast(tuple[str, ...], baseline["required_relations"])
    current_relations = cast(tuple[str, ...], current["required_relations"])
    assert set(current_relations) - set(baseline_relations) == owners
    baseline_topology = cast(dict[str, object], baseline["topology"])
    current_topology = cast(dict[str, object], current["topology"])
    assert baseline_topology is not current_topology
    for key in baseline_topology:
        if key != "allowed_relations":
            assert current_topology[key] == baseline_topology[key]
    assert set(cast(tuple[str, ...], current_topology["allowed_relations"])) == set(
        current_relations
    )
    predicates = dict(cast(tuple[tuple[str, str], ...], current["required_predicates"]))
    for owner in owners:
        assert predicates[f"B27 {owner} owner identity batch"] == rf"\b{owner}\.id\s+IN\s*\("
        assert f"{owner}.get_many" in cast(tuple[str, ...], current["repository_methods"])
    for untouched in ("downstream_impact", "audit_findings"):
        assert B27_QUERY_EXPECTATIONS[untouched] == FROZEN_QUERY_EXPECTATIONS[untouched]
