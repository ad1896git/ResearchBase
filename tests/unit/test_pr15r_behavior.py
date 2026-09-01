"""PR-15R route-family and malformed-transport behavior matrices."""

from __future__ import annotations

# pyright: reportArgumentType=false, reportIndexIssue=false
from dataclasses import asdict, dataclass, fields, is_dataclass
from datetime import UTC, datetime
from enum import Enum
from types import UnionType
from typing import Any, Union, get_args, get_origin, get_type_hints
from uuid import UUID, uuid4

import pytest
from fastapi.encoders import jsonable_encoder
from fastapi.testclient import TestClient

from researchbase.api.app import create_app
from researchbase.application import dto
from researchbase.application.governance_queries import DownstreamImpactTarget
from researchbase.application.provenance_queries import ClaimToRunsTraceDTO, RunProvenanceDTO
from researchbase.domain import governance as governance_domain
from researchbase.domain.claim import EvidenceRelationType
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


def _normalize_json(value: object) -> object:
    if isinstance(value, dict):
        return {key: _normalize_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_json(item) for item in value]
    if isinstance(value, str) and value.endswith("+00:00"):
        return f"{value[:-6]}Z"
    return value


def _assert_exact_forwarding(case: FamilyCase, args: tuple[object, ...]) -> None:
    if case.method == "get":
        if case.family in {"RunQuery", "ClaimQuery"}:
            assert args == (UUID(ID),)
        else:
            assert args == (UUID(OTHER_ID), governance_domain.GovernanceTargetType.RUN, UUID(ID))
        return
    command = args[0]
    assert is_dataclass(command)
    values = asdict(command)
    for name, expected in (case.body or {}).items():
        actual = values[name]
        if name == "inputs":
            assert len(actual) == 1
            assert actual[0]["measurement_id"] == UUID(expected[0]["measurement_id"])
            assert actual[0]["input_role"] == expected[0].get("input_role", "input")
            assert actual[0]["ordinal"] == expected[0].get("ordinal", 0)
        elif name == "relation_type":
            assert actual == EvidenceRelationType(expected)
        elif name in {"severity"}:
            assert actual.value == expected
        elif name in {"target_type"}:
            assert actual == governance_domain.GovernanceTargetType(expected)
        elif isinstance(expected, str):
            try:
                assert actual == UUID(expected)
            except ValueError:
                assert actual == expected
        else:
            assert actual == expected
    if case.family == "ClaimEvidence":
        assert values["claim_version_id"] == UUID(ID)


_RESPONSE_TYPES: dict[str, type[Any]] = {
    "ProjectReadModelResponse": dto.ProjectReadModel,
    "ResearchQuestionReadModelResponse": dto.ResearchQuestionReadModel,
    "ResearchQuestionVersionReadModelResponse": dto.ResearchQuestionVersionReadModel,
    "HypothesisReadModelResponse": dto.HypothesisReadModel,
    "HypothesisVersionReadModelResponse": dto.HypothesisVersionReadModel,
    "ExperimentSpecReadModelResponse": dto.ExperimentSpecReadModel,
    "ExperimentSpecVersionReadModelResponse": dto.ExperimentSpecVersionReadModel,
    "DatasetReadModelResponse": dto.DatasetReadModel,
    "DatasetSnapshotReadModelResponse": dto.DatasetSnapshotReadModel,
    "ArtifactReadModelResponse": dto.ArtifactReadModel,
    "ArtifactVersionReadModelResponse": dto.ArtifactVersionReadModel,
    "MetricDefinitionReadModelResponse": dto.MetricDefinitionReadModel,
    "MetricDefinitionVersionReadModelResponse": dto.MetricDefinitionVersionReadModel,
    "RunReadModelResponse": dto.RunReadModel,
    "RunProvenanceDTOResponse": RunProvenanceDTO,
    "MeasurementReadModelResponse": dto.MeasurementReadModel,
    "StatisticalResultReadModelResponse": dto.StatisticalResultReadModel,
    "ClaimReadModelResponse": dto.ClaimReadModel,
    "ClaimVersionReadModelResponse": dto.ClaimVersionReadModel,
    "EvidenceRelationReadModelResponse": dto.EvidenceRelationReadModel,
    "ClaimToRunsTraceDTOResponse": ClaimToRunsTraceDTO,
    "AuditFindingResponse": governance_domain.AuditFinding,
    "ImpactAssessmentResponse": governance_domain.ImpactAssessment,
    "CorrectionRecordResponse": governance_domain.CorrectionRecord,
    "DownstreamImpactTargetResponse": DownstreamImpactTarget,
}


def _sample(annotation: Any) -> Any:
    if annotation is Any or annotation is object:
        return {}
    supertype = getattr(annotation, "__supertype__", None)
    if supertype is not None:
        if getattr(annotation, "__name__", "") == "ContentHash":
            return "0" * 64
        return _sample(supertype)
    origin = get_origin(annotation)
    if origin in (Union, UnionType):
        non_none = [item for item in get_args(annotation) if item is not type(None)]
        return None if not non_none else _sample(non_none[0])
    if origin in (tuple, list, set, frozenset):
        return () if origin is tuple else []
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return next(iter(annotation))
    if getattr(annotation, "__name__", "") == "ContentHash":
        return "0" * 64
    if annotation is UUID:
        return uuid4()
    if annotation is datetime:
        return datetime(2026, 9, 1, tzinfo=UTC)
    if annotation is str:
        return "value"
    if annotation is int:
        return 1
    if annotation is float:
        return 1.0
    if annotation is bool:
        return True
    if annotation is bytes:
        return b"x"
    if isinstance(annotation, type) and is_dataclass(annotation):
        hints = get_type_hints(annotation)
        return annotation(
            **{field.name: _sample(hints[field.name]) for field in fields(annotation)}
        )
    return "value"


def _actual_result(schema: dict[str, Any], components: dict[str, Any]) -> object:
    ref = schema.get("$ref")
    if ref is None and schema.get("type") == "array":
        return (_actual_result(schema["items"], components),)
    name = ref.rsplit("/", 1)[-1] if ref else ""
    model = _RESPONSE_TYPES[name]
    return _sample(model)


@pytest.mark.parametrize("case", FAMILIES, ids=lambda item: item.family)
def test_every_route_family_forwards_to_expected_service_with_normalized_error(
    case: FamilyCase,
) -> None:
    services = _services()
    request_id = uuid4()
    actor_id = uuid4()
    correlation_id = uuid4()
    causation_id = uuid4()
    response = TestClient(create_app(services)).request(
        case.method,
        case.path,
        json=case.body,
        headers={
            "X-Actor-ID": str(actor_id),
            "X-Request-ID": str(request_id),
            "X-Correlation-ID": str(correlation_id),
            "X-Causation-ID": str(causation_id),
            "X-Client-Name": "pr15r-tests",
            "X-Client-Version": "1",
        },
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
        assert context.correlation_id == correlation_id
        assert context.causation_id == causation_id
        assert context.client_type == "human_ui"
        assert context.client_name == "pr15r-tests"
        assert context.client_version == "1"
        _assert_exact_forwarding(case, recorder.calls[0][1])


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
    result = _actual_result(response_schema, schema["components"]["schemas"])
    services = _success_services(case.service, result)
    actor_id = uuid4()
    request_id = uuid4()
    correlation_id = uuid4()
    causation_id = uuid4()
    response = TestClient(create_app(services)).request(
        case.method,
        case.path,
        json=case.body,
        headers={
            "X-Actor-ID": str(actor_id),
            "X-Request-ID": str(request_id),
            "X-Correlation-ID": str(correlation_id),
            "X-Causation-ID": str(causation_id),
            "X-Client-Name": "pr15r-tests",
            "X-Client-Version": "1",
        },
    )

    assert response.status_code == int(status)
    assert response.json() == _normalize_json(jsonable_encoder(result))
    assert getattr(services, case.service).calls[0][0] == case.handler

    if case.method == "post":
        context = _context_from_call(getattr(services, case.service).calls[0])
        assert context.actor_id == actor_id
        assert context.request_id == request_id
        assert context.client_type == "human_ui"
        assert context.client_name == "pr15r-tests"
        assert context.client_version == "1"
        assert context.correlation_id == correlation_id
        assert context.causation_id == causation_id
        _assert_exact_forwarding(case, getattr(services, case.service).calls[0][1])
    else:
        _assert_exact_forwarding(case, getattr(services, case.service).calls[0][1])


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
