# pyright: reportArgumentType=false, reportAttributeAccessIssue=false

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from typer.testing import CliRunner

from researchbase.application.dto import ProjectReadModel
from researchbase.cli import context as cli_context
from researchbase.cli.app import create_app
from researchbase.domain.organization import LifecycleStatus


@dataclass
class FakeApplication:
    project: ProjectReadModel | None = None
    commands: list[object] | None = None

    def __post_init__(self) -> None:
        self.commands = []

    def create_project(self, command: object) -> ProjectReadModel:
        assert self.commands is not None
        self.commands.append(command)
        assert self.project is not None
        return self.project


@dataclass
class FakeServices:
    application: Any
    provenance: Any = None
    governance: Any = None
    governance_queries: Any = None


def test_root_help_lists_frozen_command_groups() -> None:
    result = CliRunner().invoke(create_app(FakeServices(FakeApplication())))

    assert result.exit_code == 0
    for group in (
        "project",
        "rq",
        "hypothesis",
        "spec",
        "dataset",
        "artifact",
        "metric",
        "run",
        "measurement",
        "stats",
        "claim",
        "audit",
        "impact",
        "correction",
    ):
        assert group in result.stdout


def test_project_create_forwards_exact_execution_context_and_json_serializes_result() -> None:
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
            created_at=datetime(2026, 9, 1, tzinfo=UTC),
            row_version=1,
        )
    )
    result = CliRunner().invoke(
        create_app(FakeServices(fake)),
        [
            "--actor-id",
            str(actor_id),
            "--request-id",
            str(request_id),
            "--correlation-id",
            str(correlation_id),
            "--causation-id",
            str(causation_id),
            "--client-name",
            "test-cli",
            "--client-version",
            "9.9",
            "project",
            "create",
            "--name",
            "P",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert result.stderr == ""
    assert json.loads(result.stdout) == {
        "id": str(project_id),
        "name": "P",
        "description": None,
        "lifecycle_status": "active",
        "created_by": str(actor_id),
        "created_at": "2026-09-01T00:00:00Z",
        "row_version": 1,
    }
    assert fake.commands is not None
    assert len(fake.commands) == 1
    command = fake.commands[0]
    context = getattr(command, "context")  # noqa: B009
    assert context.actor_id == actor_id
    assert context.request_id == request_id
    assert context.correlation_id == correlation_id
    assert context.causation_id == causation_id
    assert context.client_type == "cli"
    assert context.client_name == "test-cli"
    assert context.client_version == "9.9"


def test_project_help_identifies_required_options_and_json_mode() -> None:
    result = CliRunner().invoke(
        create_app(FakeServices(FakeApplication())), ["project", "create", "--help"]
    )

    assert result.exit_code == 0
    assert "--name" in result.stdout
    assert "--json" in result.stdout


def test_request_id_isolation_across_successive_invocations() -> None:
    actor_id = uuid4()
    supplied_request_id = uuid4()
    fake = FakeApplication(
        ProjectReadModel(
            id=uuid4(),
            name="P",
            description=None,
            lifecycle_status=LifecycleStatus.ACTIVE,
            created_by=actor_id,
            created_at=datetime(2026, 9, 1, tzinfo=UTC),
            row_version=1,
        )
    )
    app = create_app(FakeServices(fake))
    runner = CliRunner()

    first = runner.invoke(
        app,
        [
            "--actor-id",
            str(actor_id),
            "--request-id",
            str(supplied_request_id),
            "project",
            "create",
            "--name",
            "P",
        ],
    )
    second = runner.invoke(
        app,
        ["--actor-id", str(actor_id), "project", "create", "--name", "P"],
    )

    assert first.exit_code == 0
    assert second.exit_code == 0
    assert fake.commands is not None
    first_context = fake.commands[-2].context
    second_context = fake.commands[-1].context
    assert first_context.request_id == supplied_request_id
    assert second_context.request_id != supplied_request_id
    assert second_context.actor_id == actor_id


def test_valid_supplied_request_id_is_not_regenerated(
    monkeypatch: Any,
) -> None:
    supplied_request_id = uuid4()

    def fail_generation() -> object:
        raise AssertionError("valid supplied request IDs must not be regenerated")

    monkeypatch.setattr(cli_context, "new_uuid7", fail_generation)
    runtime = cli_context.create_runtime(
        FakeServices(FakeApplication()),
        str(uuid4()),
        str(supplied_request_id),
        None,
        None,
        None,
        None,
    )
    assert runtime.request_id == supplied_request_id
