from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

# pyright: reportArgumentType=false
from dataclasses import dataclass
from typing import Any, cast
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from researchbase.api.app import create_app
from researchbase.application.commands import WriteProjectionTarget
from researchbase.application.dto import ProjectReadModel, WriteResult, write_result
from researchbase.domain.organization import LifecycleStatus
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.execution_context import ExecutionContext


@dataclass
class FakeApplication:
    result: object | None = None
    error: ResearchBaseError | None = None
    command: object | None = None

    def create_project(self, command: object) -> object:
        self.command = command
        if self.error is not None:
            raise self.error
        assert isinstance(self.result, ProjectReadModel)
        return write_result(self.result, self.result.created_at)

    def project_write_result(self, result: WriteResult, target: WriteProjectionTarget) -> object:
        assert target is WriteProjectionTarget.PROJECT
        assert isinstance(result, WriteResult)
        assert isinstance(self.result, ProjectReadModel)
        return self.result


@dataclass
class Services:
    application: object
    provenance: object = object()
    governance: object = object()
    governance_queries: object = object()


def test_project_route_forwards_exact_execution_context_and_maps_response() -> None:
    actor_id = uuid4()
    request_id = uuid4()
    correlation_id = uuid4()
    causation_id = uuid4()
    project_id = uuid4()
    fake = FakeApplication(
        ProjectReadModel(
            id=project_id,
            name="P",
            description=None,
            lifecycle_status=LifecycleStatus.ACTIVE,
            created_by=actor_id,
            created_at=__import__("datetime").datetime(
                2026, 9, 1, tzinfo=__import__("datetime").UTC
            ),
            row_version=1,
        )
    )
    client = TestClient(create_app(Services(fake)))

    response = client.post(
        "/v1/projects",
        json={"name": "P", "description": None},
        headers={
            "X-Actor-ID": str(actor_id),
            "X-Request-ID": str(request_id),
            "X-Correlation-ID": str(correlation_id),
            "X-Causation-ID": str(causation_id),
            "X-Client-Name": "browser",
            "X-Client-Version": "1.2",
        },
    )

    assert response.status_code == 201
    assert response.headers["X-Request-ID"] == str(request_id)
    assert response.json()["id"] == str(project_id)
    assert response.json()["created_at"].endswith("Z")
    context = cast(Any, fake.command).context
    assert context == ExecutionContext(
        actor_id=actor_id,
        request_id=request_id,
        correlation_id=correlation_id,
        causation_id=causation_id,
        client_type="human_ui",
        client_name="browser",
        client_version="1.2",
    )


def test_invalid_request_id_is_normalized_and_handler_is_not_called() -> None:
    fake = FakeApplication()
    response = TestClient(create_app(Services(fake))).post(
        "/v1/projects",
        json={"name": "P"},
        headers={"X-Actor-ID": str(uuid4()), "X-Request-ID": "bad"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert UUID(response.headers["X-Request-ID"])
    assert fake.command is None


def test_application_and_unexpected_errors_are_safe_and_keep_request_id() -> None:
    request_id = uuid4()
    fake = FakeApplication(error=ResearchBaseError(ErrorCode.NOT_FOUND, "project not found"))
    client = TestClient(create_app(Services(fake)), raise_server_exceptions=False)
    headers = {"X-Actor-ID": str(uuid4()), "X-Request-ID": str(request_id)}
    handled = client.post("/v1/projects", json={"name": "P"}, headers=headers)
    assert handled.status_code == 404
    assert handled.headers["X-Request-ID"] == str(request_id)
    assert handled.json() == {
        "error": {"code": "NOT_FOUND", "message": "project not found", "details": None}
    }

    fake.error = None
    fake.result = RuntimeError("psycopg secret")
    fake.create_project = lambda command: (_ for _ in ()).throw(RuntimeError("psycopg secret"))
    failed = client.post("/v1/projects", json={"name": "P"}, headers=headers)
    assert failed.status_code == 500
    assert failed.headers["X-Request-ID"] == str(request_id)
    assert "psycopg" not in failed.text


def test_openapi_contains_frozen_surface_with_unique_operation_ids() -> None:
    schema = TestClient(create_app(Services(FakeApplication()))).get("/openapi.json").json()
    required = {
        "/v1/projects",
        "/v1/research-questions",
        "/v1/runs/{id}/provenance",
        "/v1/claim-versions/{id}/trace",
        "/v1/impact/{target_type}/{target_id}",
    }
    assert required <= set(schema["paths"])
    operation_ids = [
        operation["operationId"]
        for methods in schema["paths"].values()
        for method, operation in methods.items()
        if method in {"get", "post"}
    ]
    assert len(operation_ids) == len(set(operation_ids))


def test_openapi_has_exact_frozen_v1_surface_and_is_reproducible() -> None:
    expected = {
        ("post", "/v1/projects"),
        ("post", "/v1/research-questions"),
        ("post", "/v1/research-questions/{id}/versions"),
        ("post", "/v1/research-question-versions/{id}:freeze"),
        ("post", "/v1/hypotheses"),
        ("post", "/v1/hypotheses/{id}/versions"),
        ("post", "/v1/hypothesis-versions/{id}:freeze"),
        ("post", "/v1/experiment-specs"),
        ("post", "/v1/experiment-specs/{id}/versions"),
        ("post", "/v1/experiment-spec-versions/{id}:freeze"),
        ("post", "/v1/datasets"),
        ("post", "/v1/datasets/{id}/snapshots"),
        ("post", "/v1/artifacts"),
        ("post", "/v1/artifacts/{id}/versions"),
        ("post", "/v1/artifact-versions/{id}:freeze"),
        ("post", "/v1/metric-definitions"),
        ("post", "/v1/metric-definitions/{id}/versions"),
        ("post", "/v1/metric-definition-versions/{id}:freeze"),
        ("post", "/v1/runs"),
        ("post", "/v1/runs/{id}/dataset-inputs"),
        ("post", "/v1/runs/{id}/artifact-inputs"),
        ("post", "/v1/runs/{id}:start"),
        ("post", "/v1/runs/{id}:finish"),
        ("get", "/v1/runs/{id}/provenance"),
        ("post", "/v1/measurements"),
        ("post", "/v1/statistical-results"),
        ("post", "/v1/claims"),
        ("post", "/v1/claims/{id}/versions"),
        ("post", "/v1/claim-versions/{id}/evidence"),
        ("post", "/v1/claim-versions/{id}:freeze"),
        ("get", "/v1/claim-versions/{id}/trace"),
        ("post", "/v1/audit-findings"),
        ("post", "/v1/impact-assessments"),
        ("post", "/v1/corrections"),
        ("get", "/v1/impact/{target_type}/{target_id}"),
        ("post", "/v1/projects/{project_id}/literature/sources"),
        ("post", "/v1/projects/{project_id}/literature/sources/{source_id}/identifiers"),
        ("post", "/v1/projects/{project_id}/literature/identifiers/{identifier_id}:verify"),
        ("post", "/v1/projects/{project_id}/literature/identifiers/{identifier_id}:reject"),
        ("get", "/v1/projects/{project_id}/literature/sources/{source_id}"),
        ("get", "/v1/projects/{project_id}/literature/sources:resolve"),
        ("get", "/v1/projects/{project_id}/literature/sources/{source_id}/identifiers"),
        ("post", "/v1/projects/{project_id}/literature/source-merge-proposals"),
        (
            "post",
            "/v1/projects/{project_id}/literature/source-merge-proposals/{proposal_id}:approve",
        ),
        (
            "post",
            "/v1/projects/{project_id}/literature/source-merge-proposals/{proposal_id}:reject",
        ),
        (
            "post",
            "/v1/projects/{project_id}/literature/source-merge-proposals/{proposal_id}:revoke",
        ),
        ("get", "/v1/projects/{project_id}/literature/source-merge-proposals/{proposal_id}"),
        ("post", "/v1/projects/{project_id}/literature/sources/{source_id}/versions"),
        ("post", "/v1/projects/{project_id}/literature/source-versions/{source_version_id}:freeze"),
        (
            "post",
            "/v1/projects/{project_id}/literature/source-versions/{source_version_id}:abandon",
        ),
        ("get", "/v1/projects/{project_id}/literature/sources/{source_id}/versions"),
        ("get", "/v1/projects/{project_id}/literature/source-versions/{source_version_id}"),
        (
            "post",
            "/v1/projects/{project_id}/literature/source-merge-proposals/{proposal_id}:consume",
        ),
        ("post", "/v1/projects/{project_id}/literature/search-plans"),
        ("get", "/v1/projects/{project_id}/literature/search-plans"),
        ("get", "/v1/projects/{project_id}/literature/search-plans/{plan_id}"),
        ("post", "/v1/projects/{project_id}/literature/search-plans/{plan_id}:revise"),
        (
            "post",
            "/v1/projects/{project_id}/literature/search-plans/{plan_id}/versions/{version_id}/questions",
        ),
        (
            "post",
            "/v1/projects/{project_id}/literature/search-plans/{plan_id}/versions/{version_id}:freeze",
        ),
        (
            "post",
            "/v1/projects/{project_id}/literature/search-plans/{plan_id}/versions/{version_id}:abandon",
        ),
        ("post", "/v1/literature/search-executions"),
        ("get", "/v1/literature/search-executions"),
        ("post", "/v1/literature/search-executions/{execution_id}:execute"),
        ("post", "/v1/literature/search-executions/{execution_id}:cancel"),
        ("post", "/v1/literature/search-executions/{execution_id}:recover"),
        ("get", "/v1/literature/search-executions/{execution_id}"),
        ("get", "/v1/literature/search-executions/{execution_id}/provenance"),
    }
    first = create_app(Services(FakeApplication())).openapi()
    second = create_app(Services(FakeApplication())).openapi()
    expected.update(
        {
            ("post", "/v1/projects/{project_id}/search-coverage"),
            ("get", "/v1/projects/{project_id}/search-coverage/{id}"),
            ("post", "/v1/projects/{project_id}/prior-art-relations"),
            ("get", "/v1/projects/{project_id}/prior-art-relations/{id}"),
            ("get", "/v1/projects/{project_id}/prior-art-relations/selection"),
            ("post", "/v1/projects/{project_id}/novelty-assessments"),
            ("post", "/v1/projects/{project_id}/novelty-reviews"),
            ("get", "/v1/projects/{project_id}/novelty-reviews/{id}"),
            ("post", "/v1/projects/{project_id}/novelty-revision-actions"),
            ("get", "/v1/projects/{project_id}/novelty-revision-actions/{id}"),
            (
                "post",
                "/v1/projects/{project_id}/novelty-revision-actions/{id}/re-reviews/{review_id}",
            ),
            (
                "get",
                "/v1/projects/{project_id}/novelty-revision-actions/{id}/re-reviews/{review_id}",
            ),
            ("get", "/v1/projects/{project_id}/novelty-assessments/{id}"),
        }
    )
    expected.update(
        {
            ("get", "/v1/projects/{project_id}/revision-actions/{id}"),
            ("get", "/v1/projects/{project_id}/revision-actions/{id}/re-reviews/{review_id}"),
            ("post", "/v1/projects/{project_id}/manuscript-rejection-reconsiderations"),
            ("get", "/v1/projects/{project_id}/manuscript-rejection-reconsiderations/{id}"),
            ("post", "/v1/projects/{project_id}/revision-decisions"),
            ("get", "/v1/projects/{project_id}/review-issues/{id}/history"),
            ("post", "/v1/projects/{project_id}/revision-actions"),
            ("get", "/v1/projects/{project_id}/revision-decisions/{id}"),
            ("post", "/v1/projects/{project_id}/revision-actions/{id}/re-reviews/{review_id}"),
            ("get", "/v1/projects/{project_id}/issue-dispositions/{id}"),
            ("post", "/v1/projects/{project_id}/issue-dispositions"),
            ("post", "/v1/projects/{project_id}/agents"),
            ("post", "/v1/projects/{project_id}/agent-versions"),
            ("post", "/v1/projects/{project_id}/agent-versions/{agent_version_id}/availability"),
            ("get", "/v1/projects/{project_id}/agent-versions/{agent_version_id}"),
            ("post", "/v1/research-tasks"),
            ("post", "/v1/research-tasks/{id}/plan"),
            ("post", "/v1/research-tasks/{id}/steps"),
            ("post", "/v1/research-tasks/{id}/dependencies"),
            ("post", "/v1/research-tasks/{id}:seal-plan"),
            ("post", "/v1/research-tasks/{id}:cancel"),
            ("post", "/v1/research-tasks/{id}:start"),
            ("post", "/v1/research-tasks/{id}:pause"),
            ("post", "/v1/research-tasks/{id}:resume"),
            ("post", "/v1/research-tasks/{id}/steps:start"),
            ("post", "/v1/research-tasks/{id}/steps:finish"),
            ("post", "/v1/research-tasks/{id}/steps:fail"),
            ("get", "/v1/research-tasks/{id}"),
            ("get", "/v1/research-tasks/{id}/graph"),
            ("get", "/v1/research-tasks/{id}/progress"),
        }
    )
    # PR3-04 freeze §5.1 explicitly authorizes these eight transport actions.
    # Reserve/settle expose stable fail-closed Application denials.
    expected.update(
        {
            ("post", "/v1/research-tasks/{id}:bind-policies"),
            ("post", "/v1/research-tasks/{id}:reserve-budget"),
            ("post", "/v1/research-tasks/{id}:settle-budget"),
            ("post", "/v1/research-tasks/{id}:evaluate-termination"),
            ("post", "/v1/research-tasks/{id}/checkpoints"),
            ("post", "/v1/research-tasks/{id}/checkpoints/{checkpoint_id}:respond"),
            ("get", "/v1/research-tasks/{id}/safety"),
            ("get", "/v1/research-tasks/{id}/checkpoints"),
        }
    )
    actual = {
        (method, path)
        for path, methods in first["paths"].items()
        if path.startswith("/v1/")
        for method in methods
        if method in {"get", "post"}
    }
    assert actual == expected
    assert first == second
    assert "ErrorEnvelope" in first["components"]["schemas"]
    for path, method in ((path, method) for method, path in expected):
        operation = first["paths"][path][method]
        assert any(
            "$ref" in media["schema"]
            for response in operation["responses"].values()
            for media in response.get("content", {}).values()
        )


def test_all_researchbase_error_codes_have_frozen_status_mapping() -> None:
    expected = {
        ErrorCode.APPROVAL_PURPOSE_TARGET_COMMAND_INVALID: 409,
        ErrorCode.APPROVAL_GATE_FAILED: 409,
        ErrorCode.DECISION_BASIS_INVALID: 409,
        ErrorCode.APPROVAL_TARGET_STALE: 409,
        ErrorCode.REJECTION_RECONSIDERATION_REQUIRED: 409,
        ErrorCode.GRANT_INVALID: 409,
        ErrorCode.GRANT_STALE: 409,
        ErrorCode.VALIDATION_ERROR: 422,
        ErrorCode.NOT_FOUND: 404,
        ErrorCode.AUTHENTICATION_REQUIRED: 401,
        ErrorCode.FORBIDDEN: 403,
        ErrorCode.REVIEW_TARGET_NOT_FROZEN: 409,
        ErrorCode.CONFLICT_OF_INTEREST: 403,
        ErrorCode.SUBJECT_BINDING_UNPROVEN: 403,
        ErrorCode.INVALID_STATE_TRANSITION: 409,
        ErrorCode.VERSION_NOT_FROZEN: 409,
        ErrorCode.FROZEN_REFERENCE_REQUIRED: 409,
        ErrorCode.IMMUTABLE_RECORD: 409,
        ErrorCode.CONCURRENT_MODIFICATION: 409,
        ErrorCode.DUPLICATE_CONTENT: 409,
        ErrorCode.REFERENTIAL_INTEGRITY_ERROR: 409,
        ErrorCode.PROVENANCE_CLOSURE_VIOLATION: 409,
        ErrorCode.SUBJECT_ALREADY_BOUND: 409,
        ErrorCode.OWNER_COVERAGE_GAP: 409,
        ErrorCode.OWNER_CREDENTIAL_UNAVAILABLE: 409,
        ErrorCode.ENROLLMENT_CHALLENGE_EXPIRED: 409,
        ErrorCode.BOOTSTRAP_CLOSED: 409,
        ErrorCode.IDEMPOTENCY_CONFLICT: 409,
        ErrorCode.LEGACY_STATE_INVALID: 409,
        ErrorCode.IDENTIFIER_INVALID: 422,
        ErrorCode.SOURCE_IDENTITY_CONFLICT: 409,
        ErrorCode.IDENTIFIER_ALREADY_BOUND: 409,
        ErrorCode.IDENTIFIER_BASIS_NOT_FROZEN: 409,
        ErrorCode.SOURCE_NOT_FOUND: 404,
        ErrorCode.SHARED_SOURCE_REJECTION_REQUIRES_REVIEW: 409,
        ErrorCode.SOURCE_MERGE_PROPOSAL_NOT_FOUND: 404,
        ErrorCode.SOURCE_MERGE_PROPOSAL_STALE: 409,
        ErrorCode.SOURCE_MERGE_APPROVAL_MISSING: 409,
        ErrorCode.SOURCE_MERGE_APPROVAL_FORBIDDEN: 403,
        ErrorCode.SOURCE_MERGE_REJECTED: 409,
        ErrorCode.SOURCE_MERGE_PROPOSAL_ALREADY_CONSUMED: 409,
        ErrorCode.SOURCE_MERGE_BASIS_CONFLICT: 409,
        ErrorCode.SOURCE_NOT_MERGEABLE: 409,
        ErrorCode.SOURCE_MERGE_IDENTIFIER_CONFLICT: 409,
        ErrorCode.SOURCE_VERSION_NOT_FOUND: 404,
        ErrorCode.SOURCE_VERSION_NOT_FREEZABLE: 409,
        ErrorCode.SOURCE_VERSION_ALREADY_FROZEN: 409,
        ErrorCode.SOURCE_VERSION_IMMUTABLE: 409,
        ErrorCode.INVALID_SOURCE_VERSION_LINEAGE: 409,
        ErrorCode.SEARCH_PLAN_QUESTION_REQUIRED: 422,
        ErrorCode.SEARCH_PLAN_LANGUAGE_SCOPE_REQUIRED: 422,
        ErrorCode.SEARCH_PLAN_QUESTION_INVALID: 422,
        ErrorCode.SEARCH_PLAN_QUESTION_SCOPE_MISMATCH: 403,
        ErrorCode.SEARCH_PLAN_VERSION_IMMUTABLE: 409,
        ErrorCode.SEARCH_PLAN_NOT_FROZEN: 409,
        ErrorCode.ADAPTER_UNAVAILABLE: 503,
        ErrorCode.ADAPTER_VERSION_MISMATCH: 409,
        ErrorCode.SEARCH_PLAN_QUESTION_REQUIRED: 422,
        ErrorCode.SEARCH_PLAN_LANGUAGE_SCOPE_REQUIRED: 422,
        ErrorCode.SEARCH_PLAN_QUESTION_INVALID: 422,
        ErrorCode.SEARCH_PLAN_QUESTION_SCOPE_MISMATCH: 403,
        ErrorCode.SEARCH_PLAN_VERSION_IMMUTABLE: 409,
    }
    assert set(expected) == set(ErrorCode)
    request_id = uuid4()
    actor_id = uuid4()
    for code, status in expected.items():
        fake = FakeApplication(error=ResearchBaseError(code, "safe"))
        response = TestClient(create_app(Services(fake))).post(
            "/v1/projects",
            json={"name": "P"},
            headers={"X-Actor-ID": str(actor_id), "X-Request-ID": str(request_id)},
        )
        assert response.status_code == status
        assert response.json()["error"]["code"] == code.value
        assert response.headers["X-Request-ID"] == str(request_id)


def test_generated_request_ids_are_isolated_under_concurrency() -> None:
    app = create_app(Services(FakeApplication(error=ResearchBaseError(ErrorCode.NOT_FOUND, "x"))))

    def invoke(_: int) -> str:
        response = TestClient(app).post(
            "/v1/projects", json={"name": "P"}, headers={"X-Actor-ID": str(uuid4())}
        )
        return response.headers["X-Request-ID"]

    with ThreadPoolExecutor(max_workers=8) as pool:
        values = list(pool.map(invoke, range(32)))
    assert len(set(values)) == len(values)
    assert all(UUID(value) for value in values)


def test_supplied_request_ids_are_isolated_across_concurrent_success_and_error() -> None:
    actor_id = uuid4()

    class ConcurrentApplication:
        def __init__(self) -> None:
            self.projects: dict[UUID, ProjectReadModel] = {}

        def create_project(self, command: object) -> object:
            if cast(Any, command).name.startswith("error"):
                raise ResearchBaseError(ErrorCode.NOT_FOUND, "x")
            project = ProjectReadModel(
                id=uuid4(),
                name=cast(Any, command).name,
                description=None,
                lifecycle_status=LifecycleStatus.ACTIVE,
                created_by=actor_id,
                created_at=__import__("datetime").datetime(
                    2026, 9, 1, tzinfo=__import__("datetime").UTC
                ),
                row_version=1,
            )
            self.projects[project.id] = project
            return write_result(project, project.created_at)

        def project_write_result(
            self, result: WriteResult, target: WriteProjectionTarget
        ) -> object:
            assert target is WriteProjectionTarget.PROJECT
            return self.projects[result.id]

    app = create_app(Services(ConcurrentApplication()))
    cases = [(uuid4(), "ok" if index % 2 == 0 else "error") for index in range(32)]

    def invoke(case: tuple[UUID, str]) -> tuple[str, int]:
        request_id, outcome = case
        response = TestClient(app).post(
            "/v1/projects",
            json={"name": f"{outcome}-{request_id}"},
            headers={"X-Actor-ID": str(actor_id), "X-Request-ID": str(request_id)},
        )
        return response.headers["X-Request-ID"], response.status_code

    with ThreadPoolExecutor(max_workers=8) as pool:
        actual = list(pool.map(invoke, cases))

    assert actual == [
        (str(request_id), 201 if outcome == "ok" else 404) for request_id, outcome in cases
    ]


def test_request_recovers_after_validation_handled_and_unexpected_errors() -> None:
    fake = FakeApplication(error=ResearchBaseError(ErrorCode.NOT_FOUND, "x"))
    client = TestClient(create_app(Services(fake)), raise_server_exceptions=False)
    actor = str(uuid4())
    assert (
        client.post("/v1/projects", json={"name": "P"}, headers={"X-Actor-ID": actor}).status_code
        == 404
    )
    assert client.post("/v1/projects", json={}, headers={"X-Actor-ID": actor}).status_code == 422
    fake.error = None
    original = fake.create_project
    fake.create_project = lambda command: (_ for _ in ()).throw(RuntimeError("private"))
    assert (
        client.post("/v1/projects", json={"name": "P"}, headers={"X-Actor-ID": actor}).status_code
        == 500
    )
    fake.create_project = original
    actor_id = UUID(actor)
    fake.result = ProjectReadModel(
        id=uuid4(),
        name="P",
        description=None,
        lifecycle_status=LifecycleStatus.ACTIVE,
        created_by=actor_id,
        created_at=__import__("datetime").datetime(2026, 9, 1, tzinfo=__import__("datetime").UTC),
        row_version=1,
    )
    assert (
        client.post("/v1/projects", json={"name": "P"}, headers={"X-Actor-ID": actor}).status_code
        == 201
    )
