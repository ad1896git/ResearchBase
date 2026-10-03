# pyright: reportArgumentType=false, reportAttributeAccessIssue=false

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from typer.testing import CliRunner

from researchbase.application.commands import WriteProjectionTarget
from researchbase.application.dto import ProjectReadModel, WriteResult, write_result
from researchbase.cli import context as cli_context
from researchbase.cli.app import create_app
from researchbase.domain.organization import LifecycleStatus
from researchbase.domain.phase2_identity import VerifiedPrincipal


@dataclass
class FakeApplication:
    project: ProjectReadModel | None = None
    commands: list[object] | None = None

    def __post_init__(self) -> None:
        self.commands = []

    def create_project(self, command: object) -> WriteResult:
        assert self.commands is not None
        self.commands.append(command)
        assert self.project is not None
        return write_result(self.project, self.project.created_at)

    def project_write_result(self, result: WriteResult, target: WriteProjectionTarget) -> object:
        assert target is WriteProjectionTarget.PROJECT
        assert self.project is not None
        return self.project


@dataclass
class FakeServices:
    application: Any
    provenance: Any = None
    governance: Any = None
    governance_queries: Any = None
    source_merge: Any = None
    verified_principal: VerifiedPrincipal | None = None


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


def test_literature_merge_proposal_help_lists_frozen_governance_commands() -> None:
    result = CliRunner().invoke(
        create_app(FakeServices(FakeApplication())),
        ["literature", "merge-proposal", "--help"],
    )

    assert result.exit_code == 0
    for command in ("create", "show", "approve", "reject", "revoke", "supersede"):
        assert command in result.stdout


def test_literature_merge_proposal_commands_forward_typed_operations() -> None:
    class SourceMerge:
        def __init__(self) -> None:
            self.commands: list[object] = []

        def propose(self, command: object) -> dict[str, str]:
            self.commands.append(command)
            return {"operation": "propose"}

        def get(self, principal: object, project_id: object, proposal_id: object) -> dict[str, str]:
            self.commands.append((principal, project_id, proposal_id))
            return {"operation": "get"}

        def decide(self, command: object) -> dict[str, str]:
            self.commands.append(command)
            return {"operation": "decide"}

        def revoke(self, command: object) -> None:
            self.commands.append(command)

    actor_id = uuid4()
    project_id = uuid4()
    proposal_id = uuid4()
    source_a_id = uuid4()
    source_b_id = uuid4()
    service = SourceMerge()
    services = FakeServices(
        FakeApplication(),
        source_merge=service,
        verified_principal=VerifiedPrincipal(
            actor_id, "deployment", "OS_UID", "user:1", "credential", datetime.now(UTC)
        ),
    )
    common = [
        "--request-id",
        str(uuid4()),
        "literature",
        "merge-proposal",
    ]
    runner = CliRunner()
    for operation, extra in (
        (
            "create",
            [
                "--source-a-id",
                str(source_a_id),
                "--source-b-id",
                str(source_b_id),
                "--canonical-survivor-id",
                str(source_b_id),
                "--rationale",
                "duplicate",
            ],
        ),
        (
            "supersede",
            [
                "--prior-proposal-id",
                str(proposal_id),
                "--source-a-id",
                str(source_a_id),
                "--source-b-id",
                str(source_b_id),
                "--canonical-survivor-id",
                str(source_b_id),
                "--rationale",
                "reconsidered",
            ],
        ),
    ):
        result = runner.invoke(
            create_app(services),
            [*common, operation, "--project-id", str(project_id), *extra, "--json"],
        )
        assert result.exit_code == 0
    shown = runner.invoke(
        create_app(services),
        [
            "literature",
            "merge-proposal",
            "show",
            "--project-id",
            str(project_id),
            "--proposal-id",
            str(proposal_id),
            "--json",
        ],
    )
    assert shown.exit_code == 0
    for operation, extra, expected in (
        ("approve", [], "APPROVE"),
        ("reject", ["--reason", "distinct records"], "REJECT"),
    ):
        result = runner.invoke(
            create_app(services),
            [
                "--request-id",
                str(uuid4()),
                "literature",
                "merge-proposal",
                operation,
                "--project-id",
                str(project_id),
                "--proposal-id",
                str(proposal_id),
                *extra,
                "--json",
            ],
        )
        assert result.exit_code == 0
        assert service.commands[-1].decision == expected


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
