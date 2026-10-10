"""Existing CLI validators must emit canonical errors through the write wrapper."""

import json
from uuid import uuid4

import pytest
from scripts.pr2_04_pytest_evidence import FactRecorder
from tests.unit.phase2.test_pr2_04_transport_coverage import _body, _cli, _transport


@pytest.mark.parametrize("action", ["execute", "cancel", "recover"])
@pytest.mark.parametrize("invalid", ["missing_request", "execution_uuid", "project_uuid"])
@pytest.mark.pr204_requirements("PR204-API-01")
def test_cli_write_validation_uses_canonical_json_and_exit_without_effects(
    action, invalid, pr204_trace: FactRecorder
):
    _, cli, repo, provider, services = _transport()
    body = _body()
    request_id = None if invalid == "missing_request" else uuid4()
    execution_id = "invalid-uuid" if invalid == "execution_uuid" else str(uuid4())
    if invalid == "project_uuid":
        body["project_id"] = "invalid-uuid"
    result = _cli(cli, services.verified_principal, request_id, action, body, execution_id)
    pr204_trace.record(
        action=action, invalid=invalid, exit_code=result.exit_code, output=result.output,
        executions=len(repo.executions), receipts=len(repo.receipts), events=len(repo.events),
        attempts=len(repo.attempt_rows), queries=len(repo.queries), results=len(repo.results),
        provider_calls=len(provider.calls),
    )
    assert result.exit_code == 2
    error = json.loads(result.output)["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert set(error) == {"code", "message", "details", "request_id"}
    assert repo.executions == repo.receipts == repo.attempt_rows == {}
    assert repo.events == repo.queries == repo.results == []
    assert provider.calls == []
