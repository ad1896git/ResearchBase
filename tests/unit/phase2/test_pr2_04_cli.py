from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

from typer.testing import CliRunner

from researchbase.cli.app import create_app
from researchbase.cli.commands.literature_search_execution import _queries
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


class CapturingExecutionService:
    command = None

    def create(self, command):
        self.command = command
        return {"execution_id": str(uuid4())}


def test_cli_create_forwards_every_frozen_execution_bound() -> None:
    actor_id, project_id, plan_version_id, request_id = (uuid4() for _ in range(4))
    principal = VerifiedPrincipal(
        actor_id, "deployment", "OS_UID", "subject", "credential", datetime.now(UTC)
    )
    execution_service = CapturingExecutionService()
    services = SimpleNamespace(
        application=object(),
        provenance=object(),
        governance=object(),
        governance_queries=object(),
        literature_search_executions=execution_service,
        verified_principal=principal,
    )

    result = CliRunner().invoke(
        create_app(cast(Any, services)),
        [
            "--actor-id",
            str(actor_id),
            "--request-id",
            str(request_id),
            "literature-search-execution",
            "create",
            "--project-id",
            str(project_id),
            "--plan-version-id",
            str(plan_version_id),
            "--provider-id",
            "fake",
            "--provider-version",
            "1",
            "--queries-json",
            '[{"query_text":"query"}]',
            "--max-results",
            "10",
            "--max-provider-attempts",
            "2",
            "--timeout-seconds",
            "7",
            "--execution-budget-seconds",
            "23",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    assert execution_service.command is not None
    assert execution_service.command.max_results == 10
    assert execution_service.command.max_provider_attempts == 2
    assert execution_service.command.timeout_seconds == 7
    assert execution_service.command.execution_budget_seconds == 23


def test_cli_query_json_rejects_unknown_fields() -> None:
    try:
        _queries('[{"query_text":"query","provider_token":"secret"}]')
    except ResearchBaseError as exc:
        assert exc.code is ErrorCode.VALIDATION_ERROR
    else:
        raise AssertionError("query JSON must reject fields outside the frozen DTO")
