"""Frozen pack §§9/11/19: fresh keyed drivers obey sealed durable work."""

from dataclasses import replace
from uuid import UUID

import pytest
from scripts.pr2_04_pytest_evidence import FactRecorder
from sqlalchemy import text

from researchbase.application.literature_search_execution import LiteratureSearchExecutionService
from researchbase.application.literature_search_provider import ProviderError, ProviderFailureKind
from researchbase.domain.literature_search_execution import DeliveryCertainty
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.test_pr2_04_idempotency_coverage import (
    _command,
    _execution_setup,
    _service,
    _snapshot,
)
from tests.unit.phase2.test_pr2_04_provider_coverage import ScriptedProvider, success


@pytest.fixture
def restart_case(phase2_database_url):
    yield from _execution_setup(phase2_database_url)


class CrashAfterOutcome(RuntimeError):
    pass


@pytest.mark.pr204_requirements("PR204-PROV-02", "PR204-IDEM-05", "PR204-CRASH-06")
def test_pg_restart_cannot_reset_persisted_retry_after_or_invoke_early(
    restart_case, pr204_trace: FactRecorder
):
    engine, _, _, principal, project, create = restart_case
    provider = ScriptedProvider(
        [
            ProviderError(
                ProviderFailureKind.RETRYABLE,
                "PROVIDER_RATE_LIMIT",
                delivery_certainty=DeliveryCertainty.RESPONSE_RECEIVED,
                retry_after_seconds=1,
            ),
            success("normalization evidence", "provider-a"),
        ],
        "provider-a",
    )

    def interrupt_backoff(seconds):
        assert seconds == 1.0
        raise CrashAfterOutcome("test crash after durable outcome, outside DB")

    original = _service(engine, provider, sleep=interrupt_backoff)
    execution = UUID(original.create(replace(create, timeout_seconds=1))["execution_id"])
    first = _command("execute", principal, project, execution)
    with pytest.raises(CrashAfterOutcome):
        original.execute(first)
    before = _snapshot(engine, project)
    assert len(provider.calls) == len(before["attempts"]) == len(before["queries"]) == 1
    assert before["attempts"][0]["status"] == "RETRYABLE_FAILURE"
    assert before["attempts"][0]["retry_after_seconds"] == 1
    assert before["executions"][0]["status"] == "RUNNING"
    assert len(before["receipts"]) == 2 and before["results"] == []
    attempt = before["attempts"][0]
    restarted = _service(engine, provider)
    early = _command("execute", principal, project, execution)
    with engine.connect() as connection:
        early_at = connection.execute(text("SELECT clock_timestamp()")).scalar_one()
    from datetime import timedelta

    minimum = attempt["completed_at"] + timedelta(seconds=1)
    assert early_at < minimum
    with pytest.raises(ResearchBaseError) as caught:
        restarted.execute(early)
    assert caught.value.code is ErrorCode.CONCURRENT_MODIFICATION
    assert _snapshot(engine, project) == before and len(provider.calls) == 1
    with engine.connect() as connection:
        remaining = connection.execute(
            text("SELECT greatest(0,extract(epoch FROM (:minimum-clock_timestamp())))"),
            {"minimum": minimum},
        ).scalar_one()
        connection.execute(text("SELECT pg_sleep(:seconds)"), {"seconds": float(remaining) + 0.02})
    resumed = restarted.execute(_command("execute", principal, project, execution))
    after = _snapshot(engine, project)
    attempts = sorted(after["attempts"], key=lambda row: row["attempt_number"])
    assert len(provider.calls) == len(attempts) == len(after["queries"]) == 2
    assert attempts[1]["reserved_at"] >= minimum
    assert attempts[0] == before["attempts"][0]
    assert [a["attempt_number"] for a in attempts] == [1, 2]
    assert [a["status"] for a in attempts] == ["RETRYABLE_FAILURE", "SUCCEEDED"]
    assert after["executions"][0]["started_at"] == before["executions"][0]["started_at"]
    assert (
        after["executions"][0]["execution_context"] == before["executions"][0]["execution_context"]
    )
    assert after["executions"][0]["status"] == "SUCCEEDED" and len(after["receipts"]) == 3
    assert resumed["accepted_row_version"] > 1
    pr204_trace.record(
        minimum_retry_at=minimum,
        early_database_time=early_at,
        early_error=caught.value.code.value,
        successor_reserved_at=attempts[1]["reserved_at"],
        provider_calls=2,
        original_attempt_unchanged=True,
        receipt_count=3,
    )


@pytest.mark.pr204_requirements("PR204-IDEM-05", "PR204-CRASH-06")
def test_pg_new_execute_key_continues_next_query_and_retains_prior_hits(
    restart_case, pr204_trace: FactRecorder
):
    engine, _, _, principal, project, create = restart_case
    provider = ScriptedProvider(
        [success("first query", "provider-a", hits=2), success("second query", "provider-a")],
        "provider-a",
    )

    class StopBeforeNextReservation(LiteratureSearchExecutionService):
        calls = 0

        def _drive(self, *args, **kwargs):
            self.calls += 1
            if self.calls == 2:
                raise CrashAfterOutcome("test crash before next reservation")
            return super()._drive(*args, **kwargs)

    original = _service(engine, provider, StopBeforeNextReservation)
    execution = UUID(
        original.create(replace(create, queries=("first query", "second query")))["execution_id"]
    )
    with pytest.raises(CrashAfterOutcome):
        original.execute(_command("execute", principal, project, execution))
    before = _snapshot(engine, project)
    assert before["executions"][0]["status"] == "RUNNING"
    assert len(before["attempts"]) == len(before["queries"]) == len(provider.calls) == 1
    assert before["attempts"][0]["status"] == "SUCCEEDED" and len(before["results"]) == 2
    restarted = _service(engine, provider)
    command = _command("execute", principal, project, execution)
    admission = restarted.execute(command)
    after = _snapshot(engine, project)
    attempts = sorted(after["attempts"], key=lambda row: row["query_index"])
    assert [a["query_index"] for a in attempts] == [0, 1]
    assert [a["attempt_number"] for a in attempts] == [1, 1]
    assert [a["status"] for a in attempts] == ["SUCCEEDED", "SUCCEEDED"]
    assert attempts[0] == before["attempts"][0]
    assert after["results"] == before["results"]
    assert len(after["queries"]) == len(provider.calls) == 2
    assert after["executions"][0]["status"] == "SUCCEEDED"
    assert len(after["receipts"]) == 3
    assert restarted.execute(command) == admission
    assert _snapshot(engine, project) == after and len(provider.calls) == 2
    pr204_trace.record(
        input_indices=[0, 1],
        per_input_attempt_numbers=[1, 1],
        provider_calls=2,
        preserved_prior_hits=len(before["results"]),
        exact_replay_unchanged=True,
    )
