import json
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from tests.unit.phase3.agent_vectors import VECTORS
from typer.testing import CliRunner

from researchbase.agent_runtime.application.agent_contracts import (
    AgentCommandResult,
    ProvisionProjectAgent,
)
from researchbase.api.app import create_app as http_app
from researchbase.cli.app import create_app as cli_app
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.time import SystemClock

PRINCIPAL = VerifiedPrincipal(
    UUID(VECTORS[1][0]["caller_actor_id"]),
    "test",
    "MTLS_URI",
    "spiffe://test/owner",
    "test",
    SystemClock().now(),
)


class Service:
    def __init__(self, error=None):
        self.error = error
        self.commands = []

    def execute(self, command):
        assert command.caller == PRINCIPAL
        self.commands.append(command)
        if self.error:
            raise self.error
        provision = isinstance(command.arguments, ProvisionProjectAgent)
        identities = [UUID(f"01900000-0000-7000-8000-{index:012x}") for index in range(100, 109)]
        return AgentCommandResult(
            receipt_id=identities[0],
            project_id=command.project_id,
            caller_actor_id=command.caller.actor_id,
            command_id=command.command_id,
            operation=command.operation,
            result_actor_id=command.arguments.actor_id if provision else None,
            result_binding_id=identities[1] if provision else None,
            result_membership_id=identities[2] if provision else None,
            result_role_assignment_id=identities[3] if provision else None,
            result_binding_event_id=identities[4] if provision else None,
            result_membership_event_id=identities[5] if provision else None,
            result_role_event_id=identities[6] if provision else None,
            result_agent_version_id=None if provision else command.arguments.agent_version_id,
            result_availability_event_id=None if provision else identities[7],
            resulting_revision=(command.expected_revision or 0) + 1,
            recorded_at=PRINCIPAL.verified_at,
            replayed=False,
        )


def bundle(service) -> Any:
    return SimpleNamespace(
        application=None,
        provenance=None,
        governance=None,
        governance_queries=None,
        agents=service,
        verified_principal=PRINCIPAL,
    )


def client(service, authenticated=True, raise_errors=True):
    app = http_app(bundle(service))
    if authenticated:

        @app.middleware("http")
        async def authenticate(request, call_next):
            request.state.verified_principal = PRINCIPAL
            return await call_next(request)

    return TestClient(app, raise_server_exceptions=raise_errors)


def request():
    return {
        k: VECTORS[1][0][k] for k in ("project_id", "command_id", "expected_revision", "arguments")
    }


def test_http_cli_same_application_command():
    service = Service()
    body = request()
    http = {k: v for k, v in body.items() if k != "project_id"}
    response = client(service).post(
        "/v1/projects/" + body["project_id"] + "/agent-versions",
        json=http,
        headers={"X-Request-ID": str(PRINCIPAL.actor_id)},
    )
    assert response.status_code == 201
    assert response.headers["X-Request-ID"] == str(PRINCIPAL.actor_id)
    result = CliRunner().invoke(
        cli_app(bundle(service)),
        ["agents", "register-version", "--request-json", json.dumps(body), "--json"],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == response.json()
    assert service.commands[0] == service.commands[1]


@pytest.mark.parametrize(
    "code,http,exit_code",
    [
        ("VALIDATION_ERROR", 422, 2),
        ("AUTHENTICATION_REQUIRED", 401, 3),
        ("FORBIDDEN", 403, 3),
        ("SUBJECT_BINDING_UNPROVEN", 403, 3),
        ("SUBJECT_ALREADY_BOUND", 409, 4),
        ("OWNER_CREDENTIAL_UNAVAILABLE", 409, 4),
        ("NOT_FOUND", 404, 3),
        ("INVALID_STATE_TRANSITION", 409, 4),
        ("IMMUTABLE_RECORD", 409, 4),
        ("VERSION_NOT_FROZEN", 409, 4),
        ("FROZEN_REFERENCE_REQUIRED", 409, 5),
        ("PROVENANCE_CLOSURE_VIOLATION", 409, 5),
        ("REFERENTIAL_INTEGRITY_ERROR", 409, 5),
        ("IDEMPOTENCY_CONFLICT", 409, 4),
        ("CONCURRENT_MODIFICATION", 409, 4),
    ],
)
def test_all_error_mappings(code, http, exit_code):
    service = Service(ResearchBaseError(ErrorCode(code), "sanitized"))
    body = request()
    response = client(service).post(
        "/v1/projects/" + body["project_id"] + "/agent-versions",
        json={k: v for k, v in body.items() if k != "project_id"},
    )
    assert response.status_code == http
    assert response.json()["error"]["code"] == code
    result = CliRunner().invoke(
        cli_app(bundle(service)),
        ["agents", "register-version", "--request-json", json.dumps(body), "--json"],
    )
    assert result.exit_code == exit_code
    assert json.loads(result.output)["error"]["code"] == code


def test_auth_before_existence_body_principal_and_internal_sanitization():
    service = Service()
    body = request()
    response = client(service, False).get(
        "/v1/projects/" + body["project_id"] + "/agent-versions/" + str(PRINCIPAL.actor_id)
    )
    assert response.status_code == 401
    response = client(service).post(
        "/v1/projects/" + body["project_id"] + "/agent-versions",
        json={**{k: v for k, v in body.items() if k != "project_id"}, "caller": "private"},
    )
    assert response.status_code == 422 and not service.commands
    service = Service(RuntimeError("private SQL credential"))
    response = client(service, raise_errors=False).post(
        "/v1/projects/" + body["project_id"] + "/agent-versions",
        json={k: v for k, v in body.items() if k != "project_id"},
    )
    assert response.status_code == 500 and "private" not in response.text
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"


def test_enrollment_trusted_context_and_default_denial():
    from tests.unit.phase3.test_agent_identity_contracts import enrollment_vector

    original = enrollment_vector()
    assert isinstance(original.arguments, ProvisionProjectAgent)
    args = original.arguments
    trusted = {
        "subject": args.subject,
        "attestation": args.attestation,
        "enrollment_proof": args.enrollment_proof,
    }
    body = {
        "project_id": str(original.project_id),
        "command_id": str(original.command_id),
        "expected_revision": None,
        "arguments": {"actor_id": str(args.actor_id), "display_name": args.display_name},
    }
    service = Service()
    response = client(service).post(
        "/v1/projects/" + body["project_id"] + "/agents",
        json={k: v for k, v in body.items() if k != "project_id"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "SUBJECT_BINDING_UNPROVEN"
    denied = CliRunner().invoke(
        cli_app(bundle(service)),
        ["agents", "provision", "--request-json", json.dumps(body), "--json"],
    )
    assert denied.exit_code == 3
    assert json.loads(denied.output)["error"]["code"] == "SUBJECT_BINDING_UNPROVEN"
    services = bundle(service)
    services.agent_enrollment = trusted
    app = http_app(services)

    @app.middleware("http")
    async def inject(request, call_next):
        request.state.verified_principal = PRINCIPAL
        request.state.agent_enrollment = trusted
        return await call_next(request)

    response = TestClient(app).post(
        "/v1/projects/" + body["project_id"] + "/agents",
        json={k: v for k, v in body.items() if k != "project_id"},
    )
    assert response.status_code == 201
    result = CliRunner().invoke(
        cli_app(services), ["agents", "provision", "--request-json", json.dumps(body), "--json"]
    )
    assert result.exit_code == 0, result.output
    assert service.commands[-1] == service.commands[-2]
    assert "proof_sha256" not in response.text and "credential" not in response.text
