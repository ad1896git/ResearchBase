"""Frozen pack §17 / PR204-CANCEL-04: disconnect requests only cooperative stop."""

import asyncio
import json
from threading import Event
from uuid import UUID, uuid4

import pytest
from scripts.pr2_04_pytest_evidence import FactRecorder

from researchbase.application.literature_search_provider import ProviderError, ProviderFailureKind
from tests.unit.phase2.test_pr2_04_transport_coverage import _body, _transport


@pytest.mark.pr204_requirements("PR204-CANCEL-04")
def test_actual_asgi_disconnect_requests_token_without_forged_cancel_receipt(
    monkeypatch, pr204_trace: FactRecorder
):
    client, _, repository, provider, _ = _transport()
    body = _body()
    created = client.post(
        "/literature/search-executions", json=body, headers={"Idempotency-Key": str(uuid4())}
    )
    assert created.status_code == 201
    execution_id = UUID(created.json()["execution_id"])
    entered, release = Event(), Event()
    token_values = []

    def outstanding_call(self, request, context):
        assert self is provider
        provider.calls.append(request)
        entered.set()
        assert release.wait(5), "ASGI disconnect driver did not release the bounded call"
        token_values.append(context.cancellation_requested())
        raise ProviderError(ProviderFailureKind.UNCERTAIN, "disconnect")

    monkeypatch.setattr(type(provider), "search", outstanding_call)
    offered = []

    async def disconnected_request():
        disconnected = asyncio.Event()
        payload_sent = False
        payload = json.dumps({"project_id": body["project_id"]}).encode()

        async def receive():
            nonlocal payload_sent
            if not payload_sent:
                payload_sent = True
                return {"type": "http.request", "body": payload, "more_body": False}
            await disconnected.wait()
            offered.append("http.disconnect")
            return {"type": "http.disconnect"}

        async def send(message):
            # The client connection is gone; transport writes cannot supply authority.
            assert message["type"] in {"http.response.start", "http.response.body"}

        async def close_connection():
            assert await asyncio.to_thread(entered.wait, 5)
            disconnected.set()
            await asyncio.sleep(0.05)
            release.set()

        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": f"/v1/literature/search-executions/{execution_id}:execute",
            "raw_path": f"/v1/literature/search-executions/{execution_id}:execute".encode(),
            "query_string": b"",
            "root_path": "",
            "headers": [
                (b"content-type", b"application/json"),
                (b"idempotency-key", str(uuid4()).encode()),
            ],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
        }
        await asyncio.wait_for(
            asyncio.gather(client.app(scope, receive, send), close_connection()), 10
        )

    asyncio.run(disconnected_request())
    execution = repository.executions[execution_id]
    receipt_commands = sorted(key[3] for key in repository.receipts)
    event_kinds = [event["kind"] for event in repository.events]
    pr204_trace.record(
        asgi_disconnect_messages=offered,
        cooperative_token_values=token_values,
        receipt_commands=receipt_commands,
        event_kinds=event_kinds,
        execution_status=execution.status.value,
        provider_calls=len(provider.calls),
    )
    assert "CANCEL_LITERATURE_SEARCH_EXECUTION" not in receipt_commands
    assert "CANCEL_REQUESTED" not in event_kinds
    assert len(provider.calls) == 1 and execution.status.value == "UNKNOWN"
    assert offered == ["http.disconnect"]
    assert token_values == [True]
