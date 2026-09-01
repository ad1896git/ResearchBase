"""PR-15R route-family and malformed-transport behavior matrices."""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from researchbase.api.app import create_app
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.execution_context import ExecutionContext


class Recorder:
    def __init__(self, result: object | None = None, *, error: bool = True) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.result = result
        self.error = error

    def __getattr__(self, name: str) -> Any:
        def invoke(*args: object) -> object:
            self.calls.append((name, args))
            if self.error:
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "family-probe")
            return self.result

        return invoke


@dataclass
class Services:
    application: Recorder
    provenance: Recorder
    governance: Recorder
    governance_queries: Recorder


@dataclass(frozen=True, slots=True)
class FamilyCase:
    family: str
    method: str
    path: str
    body: dict[str, object] | None
    service: str
    handler: str


ID = "00000000-0000-4000-8000-000000000001"
OTHER_ID = "00000000-0000-4000-8000-000000000002"

FAMILIES = (
    FamilyCase("Project", "post", "/v1/projects", {"name": "P"}, "application", "create_project"),
    FamilyCase(
        "ResearchQuestion",
        "post",
        "/v1/research-questions",
        {"project_id": ID, "question_text": "Q"},
        "application",
        "create_research_question",
    ),
    FamilyCase(
        "Hypothesis",
        "post",
        "/v1/hypotheses",
        {"project_id": ID, "statement": "H"},
        "application",
        "create_hypothesis",
    ),
    FamilyCase(
        "ExperimentSpec",
        "post",
        "/v1/experiment-specs",
        {"project_id": ID, "title": "E", "objective": "O", "protocol": {}},
        "application",
        "create_experiment_spec",
    ),
    FamilyCase(
        "Dataset",
        "post",
        "/v1/datasets",
        {"project_id": ID, "name": "D"},
        "application",
        "register_dataset",
    ),
    FamilyCase(
        "Artifact",
        "post",
        "/v1/artifacts",
        {"project_id": ID, "artifact_type": "code", "name": "A"},
        "application",
        "create_artifact",
    ),
    FamilyCase(
        "MetricDefinition",
        "post",
        "/v1/metric-definitions",
        {"project_id": ID, "name": "M", "definition": {}},
        "application",
        "create_metric_definition",
    ),
    FamilyCase(
        "Run",
        "post",
        "/v1/runs",
        {"project_id": ID, "experiment_spec_version_id": OTHER_ID},
        "application",
        "create_run",
    ),
    FamilyCase(
        "Measurement",
        "post",
        "/v1/measurements",
        {"run_id": ID, "metric_definition_version_id": OTHER_ID, "numeric_value": 1.0},
        "application",
        "record_measurement",
    ),
    FamilyCase(
        "StatisticalResult",
        "post",
        "/v1/statistical-results",
        {
            "project_id": ID,
            "analysis_type": "mean",
            "result_payload": {},
            "analysis_definition": {},
            "inputs": [{"measurement_id": OTHER_ID}],
        },
        "application",
        "record_statistical_result",
    ),
    FamilyCase(
        "Claim",
        "post",
        "/v1/claims",
        {"project_id": ID, "statement": "C"},
        "application",
        "create_claim",
    ),
    FamilyCase(
        "ClaimEvidence",
        "post",
        f"/v1/claim-versions/{ID}/evidence",
        {
            "claim_id": OTHER_ID,
            "measurement_id": ID,
            "relation_type": "supports",
            "expected_row_version": 1,
        },
        "application",
        "link_evidence",
    ),
    FamilyCase(
        "Governance",
        "post",
        "/v1/audit-findings",
        {
            "project_id": ID,
            "finding_type": "test",
            "severity": "minor",
            "title": "T",
            "description": "D",
            "target_type": "run",
            "target_id": OTHER_ID,
        },
        "governance",
        "create_audit_finding",
    ),
    FamilyCase(
        "RunQuery", "get", f"/v1/runs/{ID}/provenance", None, "provenance", "get_run_provenance"
    ),
    FamilyCase(
        "ClaimQuery",
        "get",
        f"/v1/claim-versions/{ID}/trace",
        None,
        "provenance",
        "trace_claim_to_runs",
    ),
    FamilyCase(
        "ImpactQuery",
        "get",
        f"/v1/impact/run/{ID}?project_id={OTHER_ID}",
        None,
        "governance_queries",
        "downstream_impact",
    ),
)


def _services() -> Services:
    return Services(Recorder(), Recorder(), Recorder(), Recorder())


def _success_services(service_name: str, result: object) -> Services:
    services = _services()
    setattr(services, service_name, Recorder(result, error=False))
    return services


def _example(schema: dict[str, Any], components: dict[str, Any]) -> object:
    if "$ref" in schema:
        return _example(components[schema["$ref"].rsplit("/", 1)[-1]], components)
    if "anyOf" in schema:
        choice = next(item for item in schema["anyOf"] if item.get("type") != "null")
        return _example(choice, components)
    if "enum" in schema:
        return schema["enum"][0]
    kind = schema.get("type")
    if kind == "object" or "properties" in schema:
        required = schema.get("required", [])
        return {name: _example(schema["properties"][name], components) for name in required}
    if kind == "array":
        return []
    if kind == "integer":
        return 1
    if kind == "number":
        return 1.0
    if kind == "boolean":
        return True
    if kind == "string":
        if schema.get("format") == "uuid":
            return ID
        if schema.get("format") == "date-time":
            return "2026-09-01T00:00:00Z"
        return "value"
    return {}


def _context_from_call(call: tuple[str, tuple[object, ...]]) -> ExecutionContext:
    command = call[1][0]
    assert is_dataclass(command)
    context_field = next(field for field in fields(command) if field.name == "context")
    return getattr(command, context_field.name)


@pytest.mark.parametrize("case", FAMILIES, ids=lambda item: item.family)
def test_every_route_family_forwards_to_expected_service_with_normalized_error(
    case: FamilyCase,
) -> None:
    services = _services()
    request_id = uuid4()
    actor_id = uuid4()
    response = TestClient(create_app(services)).request(
        case.method,
        case.path,
        json=case.body,
        headers={"X-Actor-ID": str(actor_id), "X-Request-ID": str(request_id)},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
    assert response.headers["X-Request-ID"] == str(request_id)
    recorder = getattr(services, case.service)
    assert len(recorder.calls) == 1
    assert recorder.calls[0][0] == case.handler
    if case.method == "post":
        context = _context_from_call(recorder.calls[0])
        assert context.actor_id == actor_id
        assert context.request_id == request_id


@pytest.mark.parametrize("case", FAMILIES, ids=lambda item: item.family)
def test_every_route_family_maps_application_output_through_finite_response_schema(
    case: FamilyCase,
) -> None:
    probe = create_app(_services())
    schema = probe.openapi()
    schema_path = case.path.split("?", 1)[0].replace(ID, "{id}")
    if case.family == "ImpactQuery":
        schema_path = "/v1/impact/{target_type}/{target_id}"
    operation = schema["paths"][schema_path][case.method]
    status, response_spec = next(
        (status, response)
        for status, response in operation["responses"].items()
        if status.startswith("2")
    )
    response_schema = response_spec["content"]["application/json"]["schema"]
    result = _example(response_schema, schema["components"]["schemas"])
    services = _success_services(case.service, result)
    response = TestClient(create_app(services)).request(
        case.method,
        case.path,
        json=case.body,
        headers={"X-Actor-ID": str(uuid4())},
    )

    assert response.status_code == int(status)
    assert response.json() == result
    assert getattr(services, case.service).calls[0][0] == case.handler


@pytest.mark.parametrize(
    ("label", "method", "path", "body", "headers"),
    [
        ("invalid path UUID", "post", "/v1/runs/not-a-uuid:start", {"expected_row_version": 1}, {}),
        (
            "invalid body UUID",
            "post",
            "/v1/runs",
            {"project_id": "bad", "experiment_spec_version_id": OTHER_ID},
            {},
        ),
        ("invalid actor", "post", "/v1/projects", {"name": "P"}, {"X-Actor-ID": "bad"}),
        ("missing actor", "post", "/v1/projects", {"name": "P"}, {"X-Actor-ID": ""}),
        ("invalid request", "post", "/v1/projects", {"name": "P"}, {"X-Request-ID": "bad"}),
        ("invalid correlation", "post", "/v1/projects", {"name": "P"}, {"X-Correlation-ID": "bad"}),
        ("invalid causation", "post", "/v1/projects", {"name": "P"}, {"X-Causation-ID": "bad"}),
        (
            "wrong enum",
            "post",
            f"/v1/runs/{ID}:finish",
            {"expected_row_version": 1, "outcome": "BOGUS"},
            {},
        ),
        ("missing required", "post", "/v1/projects", {}, {}),
        ("wrong scalar", "post", "/v1/projects", {"name": ["P"]}, {}),
        ("extra field", "post", "/v1/projects", {"name": "P", "extra": True}, {}),
    ],
)
def test_transport_attack_matrix_never_calls_application(
    label: str,
    method: str,
    path: str,
    body: dict[str, object],
    headers: dict[str, str],
) -> None:
    services = _services()
    merged_headers = {"X-Actor-ID": str(uuid4()), **headers}
    response = TestClient(create_app(services)).request(
        method, path, json=body, headers=merged_headers
    )
    assert response.status_code == 422, label
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert sum(len(getattr(services, name).calls) for name in vars(services)) == 0


def test_malformed_json_is_normalized_and_does_not_call_application() -> None:
    services = _services()
    response = TestClient(create_app(services)).post(
        "/v1/projects",
        content=b'{"name":',
        headers={"Content-Type": "application/json", "X-Actor-ID": str(uuid4())},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert services.application.calls == []
