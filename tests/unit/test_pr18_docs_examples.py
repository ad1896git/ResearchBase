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
from researchbase.application.dto import ProjectReadModel, WriteResult, write_result
from researchbase.cli.app import create_app
from researchbase.domain.organization import LifecycleStatus


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


def test_phase1_cli_examples_are_registered() -> None:
    runner = CliRunner()
    app = create_app()
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


def test_documented_api_contracts_match_openapi_and_execute_success_and_failure() -> None:
    document = Path("docs/phase1_api_cli_examples.md").read_text(encoding="utf-8")
    examples = _json_contracts(document, "## HTTP API")

    @dataclass
    class FakeApplication:
        project: ProjectReadModel
        error: Exception | None = None

        def create_project(self, command: object) -> WriteResult:
            if self.error is not None:
                raise self.error
            return write_result(self.project, self.project.created_at)

        def project_write_result(
            self, result: WriteResult, target: WriteProjectionTarget
        ) -> object:
            assert target is WriteProjectionTarget.PROJECT
            return self.project

    @dataclass
    class Services:
        application: Any
        provenance: Any = object()
        governance: Any = object()
        governance_queries: Any = object()

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
    client = TestClient(create_http_app(Services(FakeApplication(project))))
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
        elif example["id"] == "create_project_failure":
            response = client.post(
                path,
                json=example["request"],
                headers={"X-Actor-ID": str(actor_id)},
            )
            assert response.status_code == expected["status"]
            assert response.json()["error"]["code"] == expected["error_code"]


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
    class Services:
        application: Any
        provenance: Any = None
        governance: Any = None
        governance_queries: Any = None

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
    app = create_app(Services(FakeApplication(project)))
    for example in examples:
        tokens = [
            token.replace("ACTOR_ID", str(actor_id)).replace("PROJECT_ID", str(project.id))
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
            assert "VALIDATION_ERROR" in result.output or "Missing option" in result.output
        if example["id"] not in {"project_create", "project_create_failure"}:
            help_result = runner.invoke(app, [*tokens[:-1], "--help"])
            assert help_result.exit_code == expected["exit_code"]
