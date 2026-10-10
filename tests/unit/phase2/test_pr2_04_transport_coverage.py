"""Actual HTTP/CLI adapters and Application policy; deterministic test persistence only."""

from datetime import UTC, datetime
import json
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
import pytest
from scripts.pr2_04_pytest_evidence import FactRecorder
from typer.testing import CliRunner

from researchbase.api.app import create_app as http_app
from researchbase.cli.app import create_app as cli_app
from researchbase.application.literature_search_execution import LiteratureSearchExecutionService
from researchbase.application.literature_search_provider import FakeSearchCapability
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.persistence.in_memory_literature_search_execution import (
    InMemoryExecutionUnitOfWork,
    InMemoryLiteratureSearchExecutionRepository,
)


class _Authority:
    """Test repository port supplying current authority facts to the real policy."""
    def lock_project(self, project_id):
        pass

    def lock_literature_search_execution_command(self, *key):
        pass

    def at(self):
        return datetime.now(UTC)

    def authorize(self, principal, project_id):
        return [{"actor_type": "HUMAN", "retired_at": None, "membership_status": "ACTIVE",
                 "role": "OWNER", "effective_from": principal.verified_at,
                 "effective_until": None, "binding_status": "ACTIVE",
                 "bound_at": principal.verified_at, "revoked_at": None}]


class _Credential:
    def is_valid(self, principal, at):
        return True


def _transport(service=None, principal=None):
    principal = principal or VerifiedPrincipal(
        uuid4(), "unit-transport", "OS_UID", "501", "test-credential", datetime.now(UTC)
    )
    repository = InMemoryLiteratureSearchExecutionRepository()
    provider = FakeSearchCapability()
    def uow():
        result = InMemoryExecutionUnitOfWork(repository)
        result.literature_search_plan = cast(Any, _Authority())
        return result
    service = service or LiteratureSearchExecutionService(uow, provider,
                                                        credential_verifier=_Credential())
    services = SimpleNamespace(application=object(), provenance=object(), governance=object(),
                               governance_queries=object(), literature_search_executions=service,
                               verified_principal=principal)
    app = http_app(cast(Any, services))
    @app.middleware("http")
    async def authenticated(request, call_next):
        request.state.verified_principal = services.verified_principal
        return await call_next(request)
    # The established adapter root prefixes every frozen resource with /v1.
    class VersionedClient(TestClient):
        def request(self, method, url, **kwargs):
            return super().request(method, "/v1" + str(url), **kwargs)
    return VersionedClient(app), cli_app(cast(Any, services)), repository, provider, services


def _body():
    return {"project_id": str(uuid4()), "search_plan_version_id": str(uuid4()),
            "provider_id": "fake", "provider_version": "1",
            "queries": [{"query_text": "  bounded query  "}]}


def _cli(app, principal, request_id, action, body, execution_id=None):
    args = ["--actor-id", str(principal.actor_id)]
    if request_id is not None:
        args += ["--request-id", str(request_id)]
    args += ["literature-search-execution", action, "--project-id", body["project_id"]]
    if execution_id:
        args += ["--execution-id", execution_id]
    if action == "create":
        args += ["--plan-version-id", body["search_plan_version_id"], "--provider-id",
                 body["provider_id"], "--provider-version", body["provider_version"],
                 "--queries-json", json.dumps(body["queries"])]
    return CliRunner().invoke(app, args + ["--json"])


@pytest.mark.parametrize("action", ["create", "execute", "cancel", "recover"])
@pytest.mark.pr204_requirements("PR204-API-01", "PR204-IDEM-01")
def test_http_cli_same_admission_and_read_only_replay(action, pr204_trace: FactRecorder):
    client, cli, repository, provider, services = _transport()
    body, request_id = _body(), uuid4()
    created = client.post("/literature/search-executions", json=body,
                          headers={"Idempotency-Key": str(request_id)})
    assert created.status_code == 201
    execution_id = created.json()["execution_id"]
    if action == "create":
        response = created
    else:
        request_id = uuid4()
        response = client.post(f"/literature/search-executions/{execution_id}:{action}",
                               json={"project_id": body["project_id"]},
                               headers={"Idempotency-Key": str(request_id)})
        assert response.status_code == 202
    before = (len(repository.receipts), len(repository.events), len(repository.attempt_rows),
              len(repository.queries), len(repository.results), len(provider.calls))
    result = _cli(cli, services.verified_principal, request_id, action, body,
                  execution_id if action != "create" else None)
    assert result.exit_code == 0, result.output
    admission = response.json()
    assert json.loads(result.output) == admission
    assert set(admission) == {"execution_id", "command_name", "accepted_at", "accepted_row_version"}
    assert admission["command_name"] == f"{action.upper()}_LITERATURE_SEARCH_EXECUTION"
    assert before == (len(repository.receipts), len(repository.events), len(repository.attempt_rows),
                      len(repository.queries), len(repository.results), len(provider.calls))
    current = client.get(f"/literature/search-executions/{execution_id}",
                         params={"project_id": body["project_id"]})
    assert current.status_code == 200
    if action == "execute":
        assert admission["accepted_row_version"] == 2
        assert current.json()["status"] == "SUCCEEDED"
        assert current.json()["row_version"] > admission["accepted_row_version"]
    if action == "cancel":
        assert admission["accepted_row_version"] == 2
        assert current.json()["status"] == "CANCELLED"
        assert current.json()["row_version"] == 3
    pr204_trace.record(storage_kind="deterministic_in_memory", action=action,
                       http_status=response.status_code, http_admission=admission,
                       cli_admission=json.loads(result.output), current=current.json(), counts=before)


@pytest.mark.parametrize("invalid", ["missing_key", "bad_key", "extra_body", "extra_query",
                                     "actor_override", "result_injection"])
@pytest.mark.pr204_requirements("PR204-API-01")
def test_http_closed_create_rejects_without_effects(invalid, pr204_trace: FactRecorder):
    client, _, repository, provider, _ = _transport()
    body = _body()
    headers = {"Idempotency-Key": str(uuid4())}
    if invalid == "missing_key":
        headers = {}
    elif invalid == "bad_key":
        headers["Idempotency-Key"] = "not-a-uuid"
    elif invalid == "extra_query":
        body["queries"][0]["provider_result"] = "forged"
    else:
        body[{"extra_body": "unexpected", "actor_override": "actor_id",
              "result_injection": "results"}[invalid]] = "forged"
    response = client.post("/literature/search-executions", json=body, headers=headers)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert repository.executions == {} and repository.receipts == {}
    assert repository.events == [] and provider.calls == []
    pr204_trace.record(case=invalid, http_status=response.status_code, error=response.json(),
                       execution_count=0, receipt_count=0, provider_calls=len(provider.calls))


@pytest.mark.parametrize("action", ["execute", "cancel", "recover"])
@pytest.mark.pr204_requirements("PR204-API-01")
def test_http_scope_body_rejects_client_selected_outcome(action, pr204_trace: FactRecorder):
    client, _, repository, provider, _ = _transport()
    response = client.post(f"/literature/search-executions/{uuid4()}:{action}",
                           json={"project_id": str(uuid4()), "status": "SUCCEEDED",
                                 "provider_response": {"hits": []}},
                           headers={"Idempotency-Key": str(uuid4())})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert repository.receipts == {} and provider.calls == []


@pytest.mark.pr204_requirements("PR204-API-01", "PR204-IDEM-04")
def test_http_running_admission_replay_never_drives_existing_reservation(monkeypatch, pr204_trace):
    client, cli, repository, provider, services = _transport()
    body = _body()
    created = client.post("/literature/search-executions", json=body,
                          headers={"Idempotency-Key": str(uuid4())})
    assert created.status_code == 201
    execution_id = created.json()["execution_id"]
    # Crash boundary after canonical TX A admission, before local provider invocation.
    monkeypatch.setattr(services.literature_search_executions, "_drive", lambda *args, **kwargs: None)
    request_id = uuid4()
    response = client.post(f"/literature/search-executions/{execution_id}:execute",
                           json={"project_id": body["project_id"]},
                           headers={"Idempotency-Key": str(request_id)})
    assert response.status_code == 202
    current = client.get(f"/literature/search-executions/{execution_id}",
                         params={"project_id": body["project_id"]})
    assert current.json()["status"] == "RUNNING" and current.json()["row_version"] == 2
    result = _cli(cli, services.verified_principal, request_id, "execute", body, execution_id)
    assert result.exit_code == 0 and json.loads(result.output) == response.json()
    assert len(repository.receipts) == 2 and len(repository.attempt_rows) == 1
    assert repository.queries == [] and repository.results == [] and provider.calls == []
    pr204_trace.record(storage_kind="deterministic_in_memory", admission=response.json(),
                       current=current.json(), cli_admission=json.loads(result.output),
                       receipt_count=len(repository.receipts), attempt_count=len(repository.attempt_rows),
                       provider_calls=len(provider.calls))


@pytest.mark.parametrize("case", ["unavailable", "unknown_query_field", "terminal_cancel", "not_found"])
@pytest.mark.pr204_requirements("PR204-API-01")
def test_http_cli_canonical_application_error_parity(case, pr204_trace):
    client, cli, repository, provider, services = _transport()
    body, request_id = _body(), uuid4()
    action, execution_id = "create", None
    expected_status, expected_code = 422, "VALIDATION_ERROR"
    if case == "unavailable":
        body["provider_id"] = "missing-provider"
        expected_status, expected_code = 503, "ADAPTER_UNAVAILABLE"
    elif case == "unknown_query_field":
        body["queries"][0]["provider_token"] = "forged"
    else:
        action = "cancel"
        execution_id = str(uuid4())
        expected_status, expected_code = 404, "NOT_FOUND"
        if case == "terminal_cancel":
            created = client.post("/literature/search-executions", json=body,
                                  headers={"Idempotency-Key": str(uuid4())})
            assert created.status_code == 201
            execution_id = created.json()["execution_id"]
            finished = client.post(f"/literature/search-executions/{execution_id}:execute",
                                   json={"project_id": body["project_id"]},
                                   headers={"Idempotency-Key": str(uuid4())})
            assert finished.status_code == 202
            expected_status, expected_code = 409, "INVALID_STATE_TRANSITION"
    before = (len(repository.receipts), len(repository.events), len(provider.calls))
    path = "/literature/search-executions" if action == "create" else f"/literature/search-executions/{execution_id}:{action}"
    response = client.post(path, json=body if action == "create" else {"project_id": body["project_id"]},
                           headers={"Idempotency-Key": str(request_id)})
    result = _cli(cli, services.verified_principal, request_id, action, body, execution_id)
    assert response.status_code == expected_status and result.exit_code != 0
    assert response.json()["error"]["code"] == expected_code
    assert json.loads(result.output)["error"]["code"] == expected_code
    assert before == (len(repository.receipts), len(repository.events), len(provider.calls))
    pr204_trace.record(case=case, http_status=response.status_code, http_error=response.json(),
                       cli_error=json.loads(result.output), unchanged_counts=before)
    pr204_trace.record(action=action, status=response.status_code, error=response.json(),
                       receipt_count=len(repository.receipts), provider_calls=len(provider.calls))


@pytest.mark.pr204_requirements("PR204-API-02")
def test_http_cli_projection_and_stable_cursor_parity(pr204_trace: FactRecorder):
    client, cli, repository, provider, services = _transport()
    body = _body()
    ids = []
    for _ in range(3):
        response = client.post("/literature/search-executions", json=body,
                               headers={"Idempotency-Key": str(uuid4())})
        assert response.status_code == 201
        ids.append(response.json()["execution_id"])
    first = client.get("/literature/search-executions",
                       params={"project_id": body["project_id"], "limit": 1})
    second = client.get("/literature/search-executions",
                        params={"project_id": body["project_id"], "limit": 100, "after": ids[0]})
    assert [r["execution_id"] for r in first.json()] == ids[:1]
    assert [r["execution_id"] for r in second.json()] == ids[1:]
    all_rows = client.get("/literature/search-executions", params={"project_id": body["project_id"]})
    cli_rows = _cli(cli, services.verified_principal, None, "list", body)
    assert cli_rows.exit_code == 0 and json.loads(cli_rows.output) == all_rows.json()
    for action in ("get", "provenance"):
        suffix = "/provenance" if action == "provenance" else ""
        response = client.get(f"/literature/search-executions/{ids[0]}{suffix}",
                              params={"project_id": body["project_id"]})
        result = _cli(cli, services.verified_principal, None, action, body, ids[0])
        assert response.status_code == 200 and result.exit_code == 0
        assert response.json() == json.loads(result.output)
        pr204_trace.record(action=action, projection=response.json(), cli=json.loads(result.output))
    for limit in (0, 101):
        assert client.get("/literature/search-executions",
                          params={"project_id": body["project_id"], "limit": limit}).status_code == 422
    foreign_body = {**body, "project_id": str(uuid4())}
    foreign = client.post("/literature/search-executions", json=foreign_body,
                          headers={"Idempotency-Key": str(uuid4())})
    foreign_cursor = client.get("/literature/search-executions", params={
        "project_id": body["project_id"], "after": foreign.json()["execution_id"]})
    assert foreign_cursor.status_code == 404
    assert foreign_cursor.json()["error"]["code"] == "NOT_FOUND"
    assert provider.calls == [] and len(repository.executions) == 4
    pr204_trace.record(first_page=first.json(), second_page=second.json(),
                       foreign_cursor_error=foreign_cursor.json(), provider_calls=len(provider.calls))


@pytest.mark.pr204_requirements("PR204-AUTH-01")
def test_http_bare_actor_id_and_mismatch_cannot_supply_principal(pr204_trace: FactRecorder):
    client, _, repository, provider, services = _transport()
    body = _body()
    mismatch = client.post("/literature/search-executions", json=body,
                           headers={"Idempotency-Key": str(uuid4()), "X-Actor-ID": str(uuid4())})
    assert mismatch.status_code == 403
    services.verified_principal = None
    bare = client.post("/literature/search-executions", json=body,
                       headers={"Idempotency-Key": str(uuid4()), "X-Actor-ID": str(uuid4())})
    assert bare.status_code == 401
    assert repository.executions == {} and repository.receipts == {} and provider.calls == []
    pr204_trace.record(mismatch=mismatch.json(), bare_actor=bare.json(),
                       receipt_count=len(repository.receipts), provider_calls=len(provider.calls))


@pytest.mark.parametrize("code,http_status,cli_exit", [
    ("AUTHENTICATION_REQUIRED",401,3), ("FORBIDDEN",403,3), ("NOT_FOUND",404,3),
    ("INVALID_STATE_TRANSITION",409,4), ("IMMUTABLE_RECORD",409,4),
    ("IDEMPOTENCY_CONFLICT",409,4), ("CONCURRENT_MODIFICATION",409,4),
    ("SEARCH_PLAN_NOT_FROZEN",409,4), ("ADAPTER_VERSION_MISMATCH",409,4),
    ("VALIDATION_ERROR",422,2), ("ADAPTER_UNAVAILABLE",503,5),
])
@pytest.mark.pr204_requirements("PR204-API-01")
def test_execution_transports_preserve_every_canonical_error_category(code,http_status,cli_exit,pr204_trace):
    from researchbase.foundation.errors import ErrorCode, ResearchBaseError

    class RejectedApplication:
        def create(self, command):
            raise ResearchBaseError(ErrorCode(code), "safe test rejection")

    client, cli, repository, provider, services = _transport(service=RejectedApplication())
    body, request_id = _body(), uuid4()
    response=client.post("/literature/search-executions",json=body,
                         headers={"Idempotency-Key":str(request_id)})
    result=_cli(cli,services.verified_principal,request_id,"create",body)
    pr204_trace.record(code=code,http_status=response.status_code,http_body=response.json(),
                       cli_exit=result.exit_code,cli_output=result.output)
    assert response.status_code==http_status and result.exit_code==cli_exit
    assert response.json()["error"]["code"]==code
    assert json.loads(result.output)["error"]["code"]==code
    assert repository.executions=={} and repository.receipts=={} and provider.calls==[]


@pytest.mark.pr204_requirements("PR204-API-01", "PR204-REG-01")
def test_execution_route_and_cli_surface_has_no_result_injection_or_later_pr_commands(pr204_trace):
    from typer.main import get_command

    client, cli, *_ = _transport()
    prefix="/v1/literature/search-executions"
    paths=client.app.openapi()["paths"]
    actual={(p,method) for p,operations in paths.items() if p.startswith(prefix)
            for method in operations if method in {"get","post","put","patch","delete"}}
    expected={(prefix,"post"),(prefix,"get"),
              (prefix+"/{execution_id}","get"),(prefix+"/{execution_id}/provenance","get"),
              *{(prefix+"/{execution_id}:"+action,"post") for action in ("execute","cancel","recover")}}
    root=get_command(cli)
    group=root.commands["literature-search-execution"]
    commands=set(group.commands)
    pr204_trace.record(http_operations=sorted(actual),cli_commands=sorted(commands))
    assert actual==expected
    assert commands=={"create","execute","cancel","recover","get","list","provenance"}
    assert not any("search-runs" in p for p in paths)
