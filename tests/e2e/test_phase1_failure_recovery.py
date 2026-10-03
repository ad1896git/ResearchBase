"""PR-17 adapter recovery and complete error-registry acceptance."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from tests.e2e.support import _request_headers, fresh_fixture, run_workflow

from researchbase.api.app import create_app as create_http_app
from researchbase.api.errors import _STATUS
from researchbase.cli.app import create_app as create_cli_app
from researchbase.cli.composition import ServiceBundle
from researchbase.cli.errors import CLI_EXIT_CODES, cli_exit_code
from researchbase.foundation.errors import ErrorCode, ResearchBaseError

pytestmark = [pytest.mark.integration, pytest.mark.phase1_golden]


@dataclass
class _OneShotFailureApplication:
    delegate: object
    fail_next_project: bool = False

    def __getattr__(self, name: str) -> object:
        return getattr(self.delegate, name)

    def create_project(self, command: object) -> object:
        if self.fail_next_project:
            self.fail_next_project = False
            raise RuntimeError("private psycopg detail must remain private")
        return self.delegate.create_project(command)  # type: ignore[attr-defined]


def _cli_invoke(fixture: object, *args: str, request_id: UUID | None = None):
    fixture_value = fixture  # type: ignore[assignment]
    selected_request_id = request_id or uuid4()
    return fixture_value.cli_runner.invoke(  # type: ignore[attr-defined]
        fixture_value.cli_app,  # type: ignore[attr-defined]
        [
            "--actor-id",
            str(fixture_value.actor_id),  # type: ignore[attr-defined]
            "--request-id",
            str(selected_request_id),
            "--correlation-id",
            str(fixture_value.context.correlation_id),  # type: ignore[attr-defined]
            "--causation-id",
            str(fixture_value.context.causation_id),  # type: ignore[attr-defined]
            "--client-name",
            "pr17-recovery",
            "--client-version",
            "1",
            *args,
            "--json",
        ],
    )


def test_http_recovery_sequence_has_no_poisoned_context_or_partial_write(tmp_path: Path) -> None:
    with fresh_fixture(tmp_path, "gsas-http-recovery") as fixture:
        ids = run_workflow(fixture, "application")
        valid_headers = _request_headers(fixture)
        valid_headers["X-Request-ID"] = str(uuid4())
        first = fixture.client.post(
            "/v1/projects", json={"name": "recovery-http-1"}, headers=valid_headers
        )
        assert first.status_code == 201

        handled = fixture.client.get(
            "/v1/runs/00000000-0000-0000-0000-000000000000/provenance",
            headers={**valid_headers, "X-Request-ID": str(uuid4())},
        )
        assert handled.status_code == 404
        recovered_query = fixture.client.get(
            f"/v1/runs/{ids.run_id}/provenance",
            headers={**valid_headers, "X-Request-ID": str(uuid4())},
        )
        assert recovered_query.status_code == 200

        transport = fixture.client.post(
            "/v1/projects",
            json={},
            headers={**valid_headers, "X-Request-ID": str(uuid4())},
        )
        assert transport.status_code == 422
        recovered_after_transport = fixture.client.get(
            f"/v1/runs/{ids.run_id}/provenance",
            headers={**valid_headers, "X-Request-ID": str(uuid4())},
        )
        assert recovered_after_transport.status_code == 200

        failing_application = _OneShotFailureApplication(fixture.application)
        services = ServiceBundle(
            failing_application,  # type: ignore[arg-type]
            fixture.provenance,
            fixture.governance,
            fixture.governance_queries,
        )
        failing_client = TestClient(create_http_app(services), raise_server_exceptions=False)
        failing_application.fail_next_project = True
        unexpected = failing_client.post(
            "/v1/projects",
            json={"name": "recovery-http-internal"},
            headers={**valid_headers, "X-Request-ID": str(uuid4())},
        )
        assert unexpected.status_code == 500
        assert "private psycopg detail" not in unexpected.text
        recovered_after_internal = failing_client.get(
            f"/v1/runs/{ids.run_id}/provenance",
            headers={**valid_headers, "X-Request-ID": str(uuid4())},
        )
        failing_client.close()

    assert recovered_after_internal.status_code == 200
    assert "traceback" not in unexpected.text.lower()


def test_cli_recovery_sequence_has_no_stale_request_id_or_context(tmp_path: Path) -> None:
    with fresh_fixture(tmp_path, "gsas-cli-recovery") as fixture:
        ids = run_workflow(fixture, "application")
        success_id = uuid4()
        success = _cli_invoke(
            fixture,
            "project",
            "create",
            "--name",
            "recovery-cli-1",
            request_id=success_id,
        )
        assert success.exit_code == 0
        assert success.stderr == ""
        assert json.loads(success.stdout)["name"] == "recovery-cli-1"

        handled_id = uuid4()
        handled = _cli_invoke(
            fixture,
            "run",
            "provenance",
            "--run-id",
            str(UUID(int=0)),
            request_id=handled_id,
        )
        assert handled.exit_code == 3
        assert str(handled_id) in handled.stderr
        recovered = _cli_invoke(
            fixture,
            "run",
            "provenance",
            "--run-id",
            str(ids.run_id),
            request_id=uuid4(),
        )
        assert recovered.exit_code == 0
        assert json.loads(recovered.stdout)["run_id"] == str(ids.run_id)

        transport_id = uuid4()
        transport = _cli_invoke(
            fixture,
            "run",
            "provenance",
            "--run-id",
            "not-a-uuid",
            request_id=transport_id,
        )
        assert transport.exit_code == 2
        assert str(transport_id) in transport.stderr
        recovered_after_transport = _cli_invoke(
            fixture,
            "run",
            "provenance",
            "--run-id",
            str(ids.run_id),
            request_id=uuid4(),
        )
        assert recovered_after_transport.exit_code == 0

        failing_application = _OneShotFailureApplication(fixture.application)
        services = ServiceBundle(
            failing_application,  # type: ignore[arg-type]
            fixture.provenance,
            fixture.governance,
            fixture.governance_queries,
        )
        failing_app = create_cli_app(services)
        internal_id = uuid4()
        failing_application.fail_next_project = True
        internal = fixture.cli_runner.invoke(
            failing_app,
            [
                "--actor-id",
                str(fixture.actor_id),
                "--request-id",
                str(internal_id),
                "project",
                "create",
                "--name",
                "recovery-cli-internal",
                "--json",
            ],
        )
        assert internal.exit_code == 70
        assert "private psycopg detail" not in internal.stderr
        recovered_after_internal = fixture.cli_runner.invoke(
            failing_app,
            [
                "--actor-id",
                str(fixture.actor_id),
                "--request-id",
                str(uuid4()),
                "run",
                "provenance",
                "--run-id",
                str(ids.run_id),
                "--json",
            ],
        )

    assert recovered_after_internal.exit_code == 0
    assert str(internal_id) in internal.stderr
    assert "traceback" not in internal.stderr.lower()


def test_every_stable_researchbase_error_has_explicit_http_and_cli_mapping() -> None:
    expected_http = {
        ErrorCode.VALIDATION_ERROR: 422,
        ErrorCode.NOT_FOUND: 404,
        ErrorCode.AUTHENTICATION_REQUIRED: 401,
        ErrorCode.FORBIDDEN: 403,
        ErrorCode.SUBJECT_BINDING_UNPROVEN: 403,
        ErrorCode.INVALID_STATE_TRANSITION: 409,
        ErrorCode.VERSION_NOT_FROZEN: 409,
        ErrorCode.IMMUTABLE_RECORD: 409,
        ErrorCode.CONCURRENT_MODIFICATION: 409,
        ErrorCode.DUPLICATE_CONTENT: 409,
        ErrorCode.FROZEN_REFERENCE_REQUIRED: 409,
        ErrorCode.PROVENANCE_CLOSURE_VIOLATION: 409,
        ErrorCode.REFERENTIAL_INTEGRITY_ERROR: 409,
        ErrorCode.SUBJECT_ALREADY_BOUND: 409,
        ErrorCode.OWNER_COVERAGE_GAP: 409,
        ErrorCode.OWNER_CREDENTIAL_UNAVAILABLE: 409,
        ErrorCode.ENROLLMENT_CHALLENGE_EXPIRED: 409,
        ErrorCode.BOOTSTRAP_CLOSED: 409,
        ErrorCode.IDEMPOTENCY_CONFLICT: 409,
    }
    expected_cli = {
        ErrorCode.VALIDATION_ERROR: 2,
        ErrorCode.NOT_FOUND: 3,
        ErrorCode.AUTHENTICATION_REQUIRED: 3,
        ErrorCode.FORBIDDEN: 3,
        ErrorCode.SUBJECT_BINDING_UNPROVEN: 3,
        ErrorCode.INVALID_STATE_TRANSITION: 4,
        ErrorCode.VERSION_NOT_FROZEN: 4,
        ErrorCode.IMMUTABLE_RECORD: 4,
        ErrorCode.CONCURRENT_MODIFICATION: 4,
        ErrorCode.DUPLICATE_CONTENT: 4,
        ErrorCode.FROZEN_REFERENCE_REQUIRED: 5,
        ErrorCode.PROVENANCE_CLOSURE_VIOLATION: 5,
        ErrorCode.REFERENTIAL_INTEGRITY_ERROR: 5,
        ErrorCode.SUBJECT_ALREADY_BOUND: 4,
        ErrorCode.OWNER_COVERAGE_GAP: 4,
        ErrorCode.OWNER_CREDENTIAL_UNAVAILABLE: 4,
        ErrorCode.ENROLLMENT_CHALLENGE_EXPIRED: 4,
        ErrorCode.BOOTSTRAP_CLOSED: 4,
        ErrorCode.IDEMPOTENCY_CONFLICT: 4,
    }
    assert set(expected_http) == set(ErrorCode)
    assert _STATUS == expected_http
    assert CLI_EXIT_CODES == expected_cli
    assert {
        code: cli_exit_code(ResearchBaseError(code, "matrix")) for code in ErrorCode
    } == expected_cli
    assert 70 not in expected_cli.values()
