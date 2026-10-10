"""Frozen pack §§16/20: canonical error taxonomy and closed HTTP surface."""

import json
from uuid import uuid4

import pytest
from scripts.pr2_04_pytest_evidence import FactRecorder
from tests.unit.phase2.test_pr2_04_transport_coverage import _body, _cli, _transport

from researchbase.foundation.errors import ErrorCode, ResearchBaseError

# Literal frozen-policy expectations: do not derive expected values from adapter mappings.
ERRORS = [
    (ErrorCode.VALIDATION_ERROR, 422, 2),
    (ErrorCode.AUTHENTICATION_REQUIRED, 401, 3),
    (ErrorCode.FORBIDDEN, 403, 3),
    (ErrorCode.NOT_FOUND, 404, 3),
    (ErrorCode.INVALID_STATE_TRANSITION, 409, 4),
    (ErrorCode.IMMUTABLE_RECORD, 409, 4),
    (ErrorCode.CONCURRENT_MODIFICATION, 409, 4),
    (ErrorCode.IDEMPOTENCY_CONFLICT, 409, 4),
    (ErrorCode.PROVENANCE_CLOSURE_VIOLATION, 409, 5),
    (ErrorCode.SEARCH_PLAN_NOT_FROZEN, 409, 4),
    (ErrorCode.ADAPTER_UNAVAILABLE, 503, 5),
    (ErrorCode.ADAPTER_VERSION_MISMATCH, 409, 4),
]


@pytest.mark.pr204_requirements('PR204-API-01')
@pytest.mark.parametrize('action', ['create', 'execute', 'cancel', 'recover'])
@pytest.mark.parametrize('code,status,exit_code', ERRORS, ids=[x[0].value for x in ERRORS])
def test_every_frozen_application_error_maps_through_actual_http_and_cli(
    action, code, status, exit_code, pr204_trace: FactRecorder
):
    class RejectedApplicationBoundary:
        # Only the Application result is injected: this test owns adapter conversion,
        # not the authorization/concurrency/provider behavior producing the error.
        def __getattr__(self, name):
            assert name in {'create', 'execute', 'cancel', 'recover'}

            def operation(command):
                assert command.principal is not None
                raise ResearchBaseError(code, 'canonical safe message')

            return operation

    client, cli, repository, provider, services = _transport(service=RejectedApplicationBoundary())
    body, request_id, execution_id = _body(), uuid4(), str(uuid4())
    path = ('/literature/search-executions' if action == 'create' else
            f'/literature/search-executions/{execution_id}:{action}')
    response = client.post(path, json=body if action == 'create' else
                           {'project_id': body['project_id']},
                           headers={'Idempotency-Key': str(request_id)})
    result = _cli(cli, services.verified_principal, request_id, action, body, execution_id)
    assert response.status_code == status
    assert result.exit_code == exit_code
    http_error, cli_error = response.json(), json.loads(result.output)
    assert http_error['error']['code'] == cli_error['error']['code'] == code.value
    assert http_error['error']['message'] == cli_error['error']['message'] == 'canonical safe message'
    assert repository.executions == repository.receipts == repository.attempt_rows == {}
    assert repository.events == repository.queries == repository.results == provider.calls == []
    pr204_trace.record(action=action, application_error=code.value, http_status=status,
                       cli_exit=exit_code, http_envelope=http_error, cli_envelope=cli_error,
                       application_effect_count=0, provider_calls=0)


@pytest.mark.pr204_requirements('PR204-API-01')
def test_frozen_search_http_surface_contains_only_admitted_methods_and_routes(pr204_trace):
    client, _, _, _, _ = _transport()
    schema = client.get('/openapi.json')
    # Versioned test client prefixes /v1; the app's schema endpoint is rooted.
    schema = client.get('/../openapi.json') if schema.status_code == 404 else schema
    assert schema.status_code == 200
    paths = schema.json()['paths']
    actual = {(path, method) for path, methods in paths.items()
              if '/literature/search-executions' in path for method in methods}
    root = '/v1/literature/search-executions'
    assert actual == {
        (root, 'post'), (root, 'get'), (root + '/{execution_id}', 'get'),
        (root + '/{execution_id}:execute', 'post'),
        (root + '/{execution_id}:cancel', 'post'),
        (root + '/{execution_id}:recover', 'post'),
        (root + '/{execution_id}/provenance', 'get'),
    }
    assert all(method not in {'patch', 'put', 'delete'} for _, method in actual)
    assert not any('reconcile' in path or 'takeover' in path for path, _ in actual)
    pr204_trace.record(admitted_routes=[list(item) for item in sorted(actual)],
                       update_delete_reconcile_takeover_routes=0)


@pytest.mark.pr204_requirements("PR204-API-01", "PR204-SEC-01")
def test_unexpected_http_failure_is_redacted_internal_error(pr204_trace):
    secret = "PR204_TRANSPORT_SECRET_MUST_NOT_ESCAPE"

    class FailedApplicationBoundary:
        def create(self, command):
            raise RuntimeError(secret)

    original, _, repository, provider, _ = _transport(service=FailedApplicationBoundary())
    client = type(original)(original.app, raise_server_exceptions=False)
    response = client.post(
        "/literature/search-executions", json=_body(),
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert secret not in response.text
    assert "RuntimeError" not in response.text and "Traceback" not in response.text
    assert repository.executions == repository.receipts == {} and provider.calls == []
    pr204_trace.record(http_status=500, redacted_error=response.json(),
                       exception_text_absent=True, provider_calls=0)
