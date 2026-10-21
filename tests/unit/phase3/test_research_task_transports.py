"""HTTP/CLI closed DTO parity, stable envelopes and error maps."""

import json
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from tests.unit.phase3.test_research_task_contracts import VECTORS
from typer.testing import CliRunner

from researchbase.agent_runtime.application.contracts import CommandResult
from researchbase.api.app import create_app as http_app
from researchbase.api.errors import _STATUS
from researchbase.cli.app import create_app as cli_app
from researchbase.cli.errors import CLI_EXIT_CODES
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.time import SystemClock

PRINCIPAL = VerifiedPrincipal(
    UUID("01900000-0000-7000-8000-000000000002"),
    "test",
    "OS_UID",
    "501",
    "test",
    SystemClock().now(),
)


class Service:
    def __init__(self, error=None):
        self.commands = []
        self.error = error

    def execute(self, principal, command):
        assert principal == PRINCIPAL
        self.commands.append(command)
        if self.error:
            raise self.error
        return CommandResult(command.task_id, 1, (command.command_id,), (), False)

    create_research_task = execute


def bundle(service) -> Any:
    return SimpleNamespace(
        application=None,
        provenance=None,
        governance=None,
        governance_queries=None,
        research_tasks=service,
        verified_principal=PRINCIPAL,
    )


def client(service, *, authenticated=True, raise_server_exceptions=True):
    app = http_app(bundle(service))
    if authenticated:

        @app.middleware("http")
        async def authenticate(request, call_next):
            request.state.verified_principal = PRINCIPAL
            return await call_next(request)

    return TestClient(app, raise_server_exceptions=raise_server_exceptions)


def request():
    material = json.loads(VECTORS[0][0])
    return {
        k: material[k]
        for k in ("project_id", "command_id", "task_id", "expected_row_version", "arguments")
    }


def test_http_cli_same_command_and_result():
    service = Service()
    body = request()
    response = client(service).post(
        "/v1/research-tasks", json=body, headers={"X-Request-ID": str(PRINCIPAL.actor_id)}
    )
    assert response.status_code == 201 and response.headers["X-Request-ID"] == str(
        PRINCIPAL.actor_id
    )
    result = CliRunner().invoke(
        cli_app(bundle(service)),
        ["research-tasks", "create", "--request-json", json.dumps(body), "--json"],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == response.json()
    assert len(service.commands) == 2 and service.commands[0] == service.commands[1]


@pytest.mark.parametrize(
    "code,http,exit_code",
    [
        ("VALIDATION_ERROR", 422, 2),
        ("AUTHENTICATION_REQUIRED", 401, 3),
        ("FORBIDDEN", 403, 3),
        ("NOT_FOUND", 404, 3),
        ("INVALID_STATE_TRANSITION", 409, 4),
        ("VERSION_NOT_FROZEN", 409, 4),
        ("FROZEN_REFERENCE_REQUIRED", 409, 5),
        ("IMMUTABLE_RECORD", 409, 4),
        ("CONCURRENT_MODIFICATION", 409, 4),
        ("IDEMPOTENCY_CONFLICT", 409, 4),
        ("REFERENTIAL_INTEGRITY_ERROR", 409, 5),
        ("PROVENANCE_CLOSURE_VIOLATION", 409, 5),
    ],
)
def test_every_error_maps_to_existing_envelope(code, http, exit_code):
    enum = ErrorCode(code)
    service = Service(ResearchBaseError(enum, "sanitized", {"reason": "TEST"}))
    response = client(service).post("/v1/research-tasks", json=request())
    assert response.status_code == http and response.json()["error"]["code"] == code
    result = CliRunner().invoke(
        cli_app(bundle(service)),
        ["research-tasks", "create", "--request-json", json.dumps(request()), "--json"],
    )
    assert result.exit_code == exit_code and json.loads(result.output)["error"]["code"] == code
    assert _STATUS[enum] == http and CLI_EXIT_CODES[enum] == exit_code


@pytest.mark.parametrize(
    "field", ("actor_id", "requested_by", "status", "policy_id", "outputs", "timestamps")
)
def test_closed_unknown_field_diagnostics(field):
    service = Service()
    body = request()
    body[field] = "private"
    response = client(service).post("/v1/research-tasks", json=body)
    assert response.status_code == 422 and not service.commands
    result = CliRunner().invoke(
        cli_app(bundle(service)),
        ["research-tasks", "create", "--request-json", json.dumps(body), "--json"],
    )
    assert result.exit_code == 2 and "private" not in result.output and not service.commands


def test_authentication_before_existence_and_internal_error_fallback():
    service = Service()
    response = client(service, authenticated=False).get(
        "/v1/research-tasks/01900000-0000-7000-8000-000000000003",
        params={"project_id": str(PRINCIPAL.actor_id)},
    )
    assert response.status_code == 401 and not service.commands
    service = Service(RuntimeError("private SQL password"))
    with client(service, raise_server_exceptions=False) as c:
        response = c.post("/v1/research-tasks", json=request())
    assert response.status_code == 500 and response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "private" not in response.text
    result = CliRunner().invoke(
        cli_app(bundle(service)),
        ["research-tasks", "create", "--request-json", json.dumps(request()), "--json"],
    )
    assert result.exit_code == 1 and json.loads(result.output)["error"]["code"] == "INTERNAL_ERROR"
    assert "private" not in result.output
