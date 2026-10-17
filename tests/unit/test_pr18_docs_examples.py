# pyright: reportArgumentType=false, reportOptionalSubscript=false, reportIndexIssue=false, reportAttributeAccessIssue=false

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from researchbase.api.app import create_app as create_http_app
from researchbase.application.commands import WriteProjectionTarget
from researchbase.application.dto import (
    ArtifactVersionReadModel,
    ProjectReadModel,
    WriteResult,
    write_result,
)
from researchbase.application.governance_queries import DownstreamImpactTarget
from researchbase.application.provenance_queries import (
    ClaimToRunsTraceDTO,
    ClosureReportDTO,
    RunProvenanceDTO,
)
from researchbase.cli.app import create_app
from researchbase.domain.organization import LifecycleStatus
from researchbase.domain.run import RunStatus
from researchbase.foundation.hashing import ContentHash
from researchbase.foundation.versioning import VersionStatus


def test_phase1_examples_use_only_registered_routes_and_commands() -> None:
    document = Path("docs/phase1_api_cli_examples.md").read_text(encoding="utf-8")
    for route in (
        "/v1/projects",
        "/v1/runs/RUN_ID/provenance",
        "/v1/claim-versions/CLAIM_VERSION_ID/trace",
        "/v1/impact/artifact_version/ARTIFACT_VERSION_ID",
    ):
        assert route in document
    for command in (
        "project create",
        "run provenance",
        "claim trace",
        "impact show",
    ):
        assert command in document
    assert "phase2" not in document.lower()
    assert "orchestrate" not in document.lower()


class AnyServices:
    application = object()
    provenance = object()
    governance = object()
    governance_queries = object()


def test_phase1_cli_examples_are_registered() -> None:
    runner = CliRunner()
    # Inject services to inspect the legacy command tree without deployment authentication.
    app = create_app(AnyServices())
    for command in (
        ["project", "create", "--help"],
        ["run", "provenance", "--help"],
        ["claim", "trace", "--help"],
        ["impact", "show", "--help"],
    ):
        result = runner.invoke(app, command)
        assert result.exit_code == 0, result.stderr


def _json_contracts(document: str, heading: str) -> list[dict[str, Any]]:
    section = document.split(heading, 1)[1]
    section = section.split("\n## ", 1)[0]
    return [json.loads(block) for block in re.findall(r"```json\n(.*?)\n```", section, re.S)]


def _openapi_path(paths: dict[str, Any], concrete_path: str, method: str) -> dict[str, Any]:
    concrete = concrete_path.split("?", 1)[0].split("/")
    for route, operations in paths.items():
        route_parts = route.split("/")
        if len(route_parts) == len(concrete) and all(
            expected == actual or expected.startswith("{")
            for expected, actual in zip(route_parts, concrete, strict=True)
        ):
            return operations[method.lower()]
    raise AssertionError(f"documented route is not in OpenAPI: {concrete_path}")


def test_documented_api_contracts_are_structured_and_cover_frozen_operations() -> None:
    document = Path("docs/phase1_api_cli_examples.md").read_text(encoding="utf-8")
    examples = _json_contracts(document, "## HTTP API")
    assert {item["id"] for item in examples} >= {
        "create_project",
        "freeze_artifact_version",
        "read_run_provenance",
        "trace_claim",
        "downstream_impact",
        "create_project_failure",
    }
    for example in examples:
        assert example["method"] in {"GET", "POST"}
        assert example["path"].startswith("/v1/")
        assert isinstance(example["success" if "failure" not in example["id"] else "failure"], dict)
        contract = example.get("success") or example.get("failure")
        assert isinstance(contract, dict)
        assert isinstance(contract.get("status"), int)
        assert "request" in example or "query" in example
        if "success" in example:
            assert contract.get("response_keys") or contract.get("response_type")
        else:
            assert contract.get("error_code")


def test_documented_api_contracts_match_openapi_and_execute_success_and_failure() -> None:
    document = Path("docs/phase1_api_cli_examples.md").read_text(encoding="utf-8")
    examples = _json_contracts(document, "## HTTP API")

    @dataclass
    class FakeApplication:
        project: ProjectReadModel
        error: Exception | None = None
        artifact_version: ArtifactVersionReadModel | None = None

        def create_project(self, command: object) -> WriteResult:
            if self.error is not None:
                raise self.error
            return write_result(self.project, self.project.created_at)

        def project_write_result(
            self, result: WriteResult, target: WriteProjectionTarget
        ) -> object:
            if target is WriteProjectionTarget.PROJECT:
                return self.project
            assert target is WriteProjectionTarget.ARTIFACT_VERSION
            assert self.artifact_version is not None
            return self.artifact_version

        def freeze_artifact_version(self, command: object) -> WriteResult:
            assert self.artifact_version is not None
            return write_result(self.artifact_version, self.artifact_version.created_at)

    @dataclass
    class FakeProvenance:
        run: RunProvenanceDTO
        trace: ClaimToRunsTraceDTO

        def get_run_provenance(self, _run_id: object) -> RunProvenanceDTO:
            return self.run

        def trace_claim_to_runs(self, _claim_version_id: object) -> ClaimToRunsTraceDTO:
            return self.trace

    @dataclass
    class FakeGovernanceQueries:
        def downstream_impact(self, *_args: object) -> tuple[DownstreamImpactTarget, ...]:
            return ()

    @dataclass
    class Services:
        application: Any
        provenance: Any
        governance_queries: Any
        governance: Any = object()

    actor_id = uuid4()
    project = ProjectReadModel(
        id=uuid4(),
        name="example-project",
        description="Phase 1 example",
        lifecycle_status=LifecycleStatus.ACTIVE,
        created_by=actor_id,
        created_at=datetime(2026, 9, 1, tzinfo=UTC),
        row_version=1,
    )
    artifact_id = uuid4()
    artifact_version = ArtifactVersionReadModel(
        id=uuid4(),
        artifact_id=artifact_id,
        version_number=1,
        status=VersionStatus.FROZEN,
        locator=None,
        media_type="text/plain",
        byte_size=3,
        content_hash=ContentHash("0" * 64),
        metadata=None,
        created_by=actor_id,
        created_at=project.created_at,
        frozen_at=project.created_at,
        row_version=2,
    )
    closure = ClosureReportDTO(complete=True, visited_count=0, violations=())
    run = RunProvenanceDTO(
        run_id=str(uuid4()),
        project_id=str(project.id),
        run_type="example",
        status=RunStatus.SUCCEEDED.value,
        inputs_sealed_at=project.created_at,
        started_at=project.created_at,
        finished_at=project.created_at,
        experiment_spec_version_id=str(uuid4()),
        experiment_spec_content_hash=None,
        dataset_inputs=(),
        artifact_inputs=(),
        measurements=(),
        closure=closure,
    )
    trace = ClaimToRunsTraceDTO(
        claim_version_id=str(uuid4()),
        project_id=str(project.id),
        runs=(run,),
        paths=(),
        closure=closure,
    )
    application = FakeApplication(project, artifact_version=artifact_version)
    client = TestClient(
        create_http_app(
            Services(
                application=application,
                provenance=FakeProvenance(run, trace),
                governance_queries=FakeGovernanceQueries(),
            )
        )
    )
    openapi = client.get("/openapi.json").json()

    for example in examples:
        path = example["path"].replace("RUN_ID", str(uuid4()))
        path = path.replace("CLAIM_VERSION_ID", str(uuid4()))
        path = path.replace("ARTIFACT_VERSION_ID", str(uuid4()))
        path = path.replace("PROJECT_ID", str(project.id))
        operation = _openapi_path(openapi["paths"], path, example["method"])
        expected = example.get("success", example.get("failure"))
        assert str(expected["status"]) in operation["responses"]
        if example["id"] == "create_project":
            response = client.post(
                path,
                json=example["request"],
                headers={"X-Actor-ID": str(actor_id)},
            )
            assert response.status_code == expected["status"]
            assert set(expected["response_keys"]) <= response.json().keys()
        elif example["id"] == "freeze_artifact_version":
            response = client.post(
                path,
                json={
                    "artifact_id": str(artifact_id),
                    "expected_row_version": 1,
                },
                headers={"X-Actor-ID": str(actor_id)},
            )
            assert response.status_code == expected["status"]
            assert set(expected["response_keys"]) <= response.json().keys()
        elif example["id"] == "read_run_provenance":
            response = client.get(path)
            assert response.status_code == expected["status"]
            assert set(expected["response_keys"]) <= response.json().keys()
        elif example["id"] == "trace_claim":
            response = client.get(path)
            assert response.status_code == expected["status"]
            assert set(expected["response_keys"]) <= response.json().keys()
        elif example["id"] == "downstream_impact":
            response = client.get(path)
            assert response.status_code == expected["status"]
            assert isinstance(response.json(), list)
        elif example["id"] == "create_project_failure":
            response = client.post(
                path,
                json=example["request"],
                headers={"X-Actor-ID": str(actor_id)},
            )
            assert response.status_code == expected["status"]
            assert response.json()["error"]["code"] == expected["error_code"]
            assert set(expected["error_response_keys"]) <= response.json().keys()


def test_documented_cli_contracts_execute_against_the_real_typer_app() -> None:
    document = Path("docs/phase1_api_cli_examples.md").read_text(encoding="utf-8")
    examples = _json_contracts(document, "## CLI")

    @dataclass
    class FakeApplication:
        project: ProjectReadModel

        def create_project(self, command: object) -> WriteResult:
            return write_result(self.project, self.project.created_at)

        def project_write_result(
            self, result: WriteResult, target: WriteProjectionTarget
        ) -> object:
            return self.project

    @dataclass
    class FakeProvenance:
        def get_run_provenance(self, run_id: object) -> dict[str, object]:
            return {"run_id": str(run_id), "status": "SUCCEEDED"}

        def trace_claim_to_runs(self, claim_version_id: object) -> dict[str, object]:
            return {"claim_version_id": str(claim_version_id), "runs": [], "paths": []}

    @dataclass
    class FakeGovernanceQueries:
        def downstream_impact(self, *_args: object) -> list[object]:
            return []

    @dataclass
    class Services:
        application: Any
        provenance: Any
        governance_queries: Any
        governance: Any = None

    actor_id = uuid4()
    project = ProjectReadModel(
        id=uuid4(),
        name="example-project",
        description=None,
        lifecycle_status=LifecycleStatus.ACTIVE,
        created_by=actor_id,
        created_at=datetime(2026, 9, 1, tzinfo=UTC),
        row_version=1,
    )
    runner = CliRunner()
    app = create_app(
        Services(
            application=FakeApplication(project),
            provenance=FakeProvenance(),
            governance_queries=FakeGovernanceQueries(),
        )
    )
    for example in examples:
        tokens = [
            token.replace("ACTOR_ID", str(actor_id))
            .replace("PROJECT_ID", str(project.id))
            .replace("RUN_ID", str(uuid4()))
            .replace("CLAIM_VERSION_ID", str(uuid4()))
            .replace("ARTIFACT_VERSION_ID", str(uuid4()))
            for token in example["command"]
        ]
        expected = example.get("success", example.get("failure"))
        if example["id"] == "project_create":
            result = runner.invoke(app, tokens)
            assert result.exit_code == expected["exit_code"]
            assert json.loads(result.stdout)["id"] == str(project.id)
        if example["id"] == "project_create_failure":
            result = runner.invoke(app, tokens)
            assert result.exit_code == expected["exit_code"]
            assert "VALIDATION_ERROR" in result.output
            assert "error" in result.output
        if example["id"] == "run_provenance":
            result = runner.invoke(app, tokens)
            assert result.exit_code == expected["exit_code"]
            assert json.loads(result.stdout)["status"] == "SUCCEEDED"
        if example["id"] == "claim_trace":
            result = runner.invoke(app, tokens)
            assert result.exit_code == expected["exit_code"]
            assert json.loads(result.stdout)["runs"] == []
        if example["id"] == "impact_show":
            result = runner.invoke(app, tokens)
            assert result.exit_code == expected["exit_code"]
            assert json.loads(result.stdout) == []
