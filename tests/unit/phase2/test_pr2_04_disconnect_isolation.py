"""Frozen §17/CANCEL-04: actual concurrent requests own their disconnect signals."""

import asyncio
import json
from threading import Event
from uuid import UUID, uuid4

import pytest
from tests.unit.phase2.test_pr2_04_transport_coverage import _body, _transport

from researchbase.application.literature_search_provider import ProviderError, ProviderFailureKind


@pytest.mark.pr204_requirements("PR204-CANCEL-04")
@pytest.mark.parametrize("companion_failure", [False, True])
def test_disconnect_signal_is_request_owned_and_watchers_finish(
    monkeypatch, pr204_trace, companion_failure
):
    client, _, repository, provider, services = _transport()
    body = _body()
    ids = [
        UUID(client.post("/literature/search-executions", json=body,
                         headers={"Idempotency-Key": str(uuid4())}).json()["execution_id"])
        for _ in range(2)
    ]
    entered = {id: Event() for id in ids}
    release = Event()
    observed = {}
    original = type(provider).search

    def outstanding(self, request, context):
        entered[request.execution_id].set()
        assert release.wait(5)
        observed[request.execution_id] = context.cancellation_requested()
        if request.execution_id == ids[0]:
            self.calls.append(request)
            raise ProviderError(ProviderFailureKind.UNCERTAIN, "disconnect")
        if companion_failure:
            self.calls.append(request)
            raise RuntimeError("unclassified adapter failure")
        return original(self, request, context)

    monkeypatch.setattr(type(provider), "search", outstanding)

    async def run():
        before = set(asyncio.all_tasks())
        disconnected = asyncio.Event()

        async def request(id):
            sent = False
            async def receive():
                nonlocal sent
                if not sent:
                    sent = True
                    return {"type": "http.request", "body": json.dumps(
                        {"project_id": body["project_id"]}).encode(), "more_body": False}
                if id == ids[0]:
                    await disconnected.wait()
                    return {"type": "http.disconnect"}
                await asyncio.Event().wait()
                raise AssertionError("unreachable")

            async def send(message):
                assert message["type"] in {"http.response.start", "http.response.body"}

            path = f"/v1/literature/search-executions/{id}:execute"
            scope = dict(type="http", asgi={"version": "3.0", "spec_version": "2.3"},
                         http_version="1.1", method="POST", scheme="http", path=path,
                         raw_path=path.encode(), query_string=b"", root_path="",
                         headers=[(b"content-type", b"application/json"),
                                  (b"idempotency-key", str(uuid4()).encode())],
                         client=("127.0.0.1", 12345), server=("testserver", 80))
            await client.app(scope, receive, send)

        async def close():
            for event in entered.values():
                assert await asyncio.to_thread(event.wait, 5)
            disconnected.set()
            await asyncio.sleep(0.05)
            release.set()

        await asyncio.wait_for(asyncio.gather(request(ids[0]), request(ids[1]), close()), 10)
        await asyncio.sleep(0)
        assert set(asyncio.all_tasks()) == before

    asyncio.run(run())
    commands = [key[3] for key in repository.receipts]
    kinds = [event["kind"] for event in repository.events]
    durable_tokens = [services.literature_search_executions._cancellation_event(id).is_set()
                      for id in ids]
    pr204_trace.record(observed_tokens={str(k): v for k,v in observed.items()},
                       durable_tokens=durable_tokens, receipt_commands=commands,
                       event_kinds=kinds, calls=len(provider.calls),
                       companion_failure=companion_failure, watchers_finished=True)
    assert observed == {ids[0]: True, ids[1]: False}
    assert durable_tokens == [False, False]
    assert "CANCEL_LITERATURE_SEARCH_EXECUTION" not in commands
    assert "CANCEL_REQUESTED" not in kinds
    assert len(provider.calls) == 2
    assert repository.executions[ids[0]].status.value == "UNKNOWN"
    assert repository.executions[ids[1]].status.value == ("UNKNOWN" if companion_failure else "SUCCEEDED")
