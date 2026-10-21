"""HTTP and CLI share the closed command decoder and existing error envelope."""

import json
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from tests.unit.phase3.test_research_task_transports import PRINCIPAL
from tests.unit.phase3.test_task_safety_contracts import VECTORS
from typer.testing import CliRunner

from researchbase.agent_runtime.application.contracts import CommandResult
from researchbase.agent_runtime.application.safety_contracts import SafetyCommandResult
from researchbase.api.app import create_app as http_app
from researchbase.cli.app import create_app as cli_app
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


class Service:
    def __init__(self, error=None):
        self.commands = []
        self.error = error

    def execute(self, principal, command):
        assert principal == PRINCIPAL
        self.commands.append(command)
        if self.error:
            raise self.error
        return SafetyCommandResult(
            CommandResult(command.task_id, 2, (command.command_id,), (), False)
        )

    bind_task_policies = execute
    reserve_task_budget = execute
    settle_task_budget = execute
    evaluate_task_termination = execute
    request_human_checkpoint = execute
    respond_human_checkpoint = execute


def bundle(service) -> Any:
    return SimpleNamespace(
        application=None,
        provenance=None,
        governance=None,
        governance_queries=None,
        task_safety=service,
        verified_principal=PRINCIPAL,
    )


def client(service, *, authenticated=True):
    app = http_app(bundle(service))
    if authenticated:

        @app.middleware("http")
        async def authenticate(request, call_next):
            request.state.verified_principal = PRINCIPAL
            return await call_next(request)

    return TestClient(app, raise_server_exceptions=False)


def body():
    material = json.loads(VECTORS[0][0])
    return {
        k: material[k]
        for k in ("project_id", "task_id", "command_id", "expected_row_version", "arguments")
    }


def test_shared_http_cli_decoder_and_result():
    s = Service()
    request = body()
    response = client(s).post(
        "/v1/research-tasks/" + request["task_id"] + ":bind-policies",
        json=request,
        headers={"X-Request-ID": str(PRINCIPAL.actor_id)},
    )
    result = CliRunner().invoke(
        cli_app(bundle(s)),
        ["research-tasks", "bind-policies", "--request-json", json.dumps(request), "--json"],
    )
    assert response.status_code == 200 and result.exit_code == 0, result.output
    assert response.json() == json.loads(result.output)
    assert s.commands[0] == s.commands[1]
    assert response.headers["X-Request-ID"] == str(PRINCIPAL.actor_id)


@pytest.mark.parametrize(
    "code,http,exit_code",
    (
        ("FORBIDDEN", 403, 3),
        ("INVALID_STATE_TRANSITION", 409, 4),
        ("VALIDATION_ERROR", 422, 2),
        ("NOT_FOUND", 404, 3),
        ("IMMUTABLE_RECORD", 409, 4),
        ("IDEMPOTENCY_CONFLICT", 409, 4),
    ),
)
def test_error_parity(code, http, exit_code):
    s = Service(ResearchBaseError(ErrorCode(code), "sanitized"))
    b = body()
    response = client(s).post("/v1/research-tasks/" + b["task_id"] + ":bind-policies", json=b)
    result = CliRunner().invoke(
        cli_app(bundle(s)),
        ["research-tasks", "bind-policies", "--request-json", json.dumps(b), "--json"],
    )
    assert response.status_code == http and result.exit_code == exit_code
    assert response.json()["error"]["code"] == json.loads(result.output)["error"]["code"] == code


def test_authentication_and_extra_trust_field():
    s = Service()
    b = body()
    path = "/v1/research-tasks/" + b["task_id"] + ":bind-policies"
    assert client(s, authenticated=False).post(path, json=b).status_code == 401
    b["arguments"]["trusted"] = True
    assert client(s).post(path, json=b).status_code == 422
    assert not s.commands


@pytest.mark.parametrize("retryable,expected", ((True, 3), (False, 1)))
def test_only_explicit_transient_retry_uses_three_total_attempts(monkeypatch, retryable, expected):
    from tests.unit.phase3.test_task_safety_contracts import decoded

    from researchbase.agent_runtime.application.task_safety import TaskSafetyService

    _, command = decoded(VECTORS[0][0])
    service = TaskSafetyService(None, None)
    calls = []

    def fail_once(principal, request, capability):
        calls.append(request.request_hash(principal.actor_id))
        raise ResearchBaseError(
            ErrorCode.CONCURRENT_MODIFICATION, "sanitized", {"retryable_pr301": retryable}
        )

    monkeypatch.setattr(service, "_execute_safety", fail_once)
    with pytest.raises(ResearchBaseError):
        service.execute(PRINCIPAL, command)
    assert len(calls) == expected and len(set(calls)) == 1
