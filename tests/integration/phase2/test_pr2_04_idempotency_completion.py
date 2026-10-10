"""Additional reachable receipt replay and durable new-key stop cases."""

from dataclasses import replace
from datetime import timedelta
from uuid import UUID

import pytest
from sqlalchemy import text

from researchbase.application.literature_search_execution import LiteratureSearchExecutionService
from researchbase.application.literature_search_provider import ProviderError, ProviderFailureKind
from researchbase.domain.literature_search_execution import DeliveryCertainty
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.test_pr2_04_execution_recovery import ReservedBeforeInvocation
from tests.integration.phase2.test_pr2_04_idempotency_coverage import (
    _command,
    _execution_setup,
    _service,
    _snapshot,
)
from tests.unit.phase2.test_pr2_04_provider_coverage import ScriptedProvider, success


@pytest.fixture
def idem_case(phase2_database_url):
    yield from _execution_setup(phase2_database_url)


class InterruptedAfterCommit(RuntimeError):
    pass


def _interrupt():
    raise InterruptedAfterCommit("test-owned post-commit interruption")


class StopAfterOutcome(LiteratureSearchExecutionService):
    """Let TX B commit normally, then interrupt orchestration outside its UoW."""

    stop_query_index = 0

    def _persist_outcome(self, *args, **kwargs):
        outcome = super()._persist_outcome(*args, **kwargs)
        query_index = args[3] if len(args) > 3 else kwargs["query_index"]
        if query_index == self.stop_query_index:
            _interrupt()
        return outcome


class StopRecoveryBeforeFinalization(LiteratureSearchExecutionService):
    def _finalize_recovery(self, *args, **kwargs):
        _interrupt()


class InvalidCredential:
    def is_valid(self, principal, at):
        return False


def _saved_admission(rows, command):
    matches = [
        row
        for row in rows["receipts"]
        if row["deployment_id"] == command.deployment_id
        and row["actor_id"] == command.actor_id
        and row["project_id"] == command.project_id
        and row["request_id"] == command.request_id
        and row["command_name"]
        == {
            "ExecuteLiteratureSearchExecution": "EXECUTE_LITERATURE_SEARCH_EXECUTION",
            "CancelLiteratureSearchExecution": "CANCEL_LITERATURE_SEARCH_EXECUTION",
            "RecoverLiteratureSearchExecution": "RECOVER_LITERATURE_SEARCH_EXECUTION",
        }[type(command).__name__]
    ]
    assert len(matches) == 1
    return matches[0]["result_dto"]


def _script_step(status, query="normalization evidence"):
    if status == "SUCCEEDED":
        return success(query, "provider-a", hits=2)
    if status == "FAILED":
        return ProviderError(
            ProviderFailureKind.PERMANENT,
            "PROVIDER_PERMANENT",
            delivery_certainty=DeliveryCertainty.RESPONSE_RECEIVED,
        )
    if status == "UNKNOWN":
        return ProviderError(
            ProviderFailureKind.UNCERTAIN,
            "PROVIDER_TIMEOUT",
            delivery_certainty=DeliveryCertainty.MAY_HAVE_BEEN_SENT,
        )
    if status == "CANCELLED":
        # A confirmed response echoes this actual invocation; an exception alone
        # no longer establishes provider-origin cancellation (M0-CANCEL-002).
        from tests.integration.phase2.test_m0_provider_cancellation import confirmation

        return confirmation
    raise AssertionError(status)


REPLAY_CASES = [
    *(
        pytest.param("recover", state, id=f"recover-planned-origin-{state}")
        for state in ("PLANNED", "RUNNING", "FAILED", "CANCELLED", "UNKNOWN", "SUCCEEDED")
    ),
    *(
        pytest.param("execute", state, id=f"execute-{state}")
        for state in ("RUNNING", "FAILED", "CANCELLED", "UNKNOWN", "SUCCEEDED")
    ),
    *(
        pytest.param("cancel", state, id=f"cancel-{state}")
        for state in ("PLANNED", "RUNNING", "CANCELLED", "UNKNOWN")
    ),
]


@pytest.mark.parametrize("name,state", REPLAY_CASES)
@pytest.mark.pr204_requirements("PR204-IDEM-04")
def test_pg_reachable_saved_command_replay_preserves_all_facts_and_rechecks_entitlement(
    idem_case, name, state, pr204_trace
):
    engine, _, _, principal, project, create = idem_case
    provider = ScriptedProvider([], "provider-a")
    service = _service(engine, provider)
    execution_id = UUID(service.create(create)["execution_id"])
    command = _command(name, principal, project, execution_id)

    if name == "recover":
        service.recover(command)  # Legitimate PLANNED no-op admission survives later work.
        if state == "RUNNING":
            _service(engine, provider, ReservedBeforeInvocation).execute(
                _command("execute", principal, project, execution_id)
            )
        elif state == "CANCELLED":
            service.cancel(_command("cancel", principal, project, execution_id))
        elif state != "PLANNED":
            provider.script.append(_script_step(state))
            service.execute(_command("execute", principal, project, execution_id))
    elif name == "execute":
        if state == "RUNNING":
            _service(engine, provider, ReservedBeforeInvocation).execute(command)
        else:
            provider.script.append(_script_step(state))
            service.execute(command)
    elif state == "PLANNED":
        interrupted = _service(engine, provider, after_cancel_admission=_interrupt)
        with pytest.raises(InterruptedAfterCommit):
            interrupted.cancel(command)
    elif state == "RUNNING":
        _service(engine, provider, ReservedBeforeInvocation).execute(
            _command("execute", principal, project, execution_id)
        )
        service.cancel(command)  # Active reservation prevents C2 finalization.
    elif state == "CANCELLED":
        service.cancel(command)
    else:
        provider.script.append(_script_step("UNKNOWN"))
        provider.observer = lambda request: service.cancel(command)
        service.execute(_command("execute", principal, project, execution_id))
        provider.observer = None

    before = _snapshot(engine, project)
    calls = len(provider.calls)
    saved = _saved_admission(before, command)
    assert before["executions"][0]["status"] == state
    fresh = _service(engine, provider)
    assert getattr(fresh, name)(command) == saved
    assert _snapshot(engine, project) == before
    assert len(provider.calls) == calls
    assert set(saved) == {"execution_id", "command_name", "accepted_at", "accepted_row_version"}

    # Existing test helper supplies the verifier; replace the test-owned instance only.
    denied = _service(engine, provider)
    denied._credential_verifier = InvalidCredential()
    with pytest.raises(ResearchBaseError) as caught:
        getattr(denied, name)(command)
    assert caught.value.code is ErrorCode.FORBIDDEN
    assert _snapshot(engine, project) == before
    assert len(provider.calls) == calls
    pr204_trace.record(
        command=name,
        observed_state=state,
        admission=saved,
        before=before,
        after=_snapshot(engine, project),
        provider_calls_before=calls,
        provider_calls_after=len(provider.calls),
        fresh_credential_denial=caught.value.code.value,
    )


@pytest.mark.parametrize("terminal", ["FAILED", "CANCELLED", "UNKNOWN", "SUCCEEDED"])
@pytest.mark.pr204_requirements("PR204-IDEM-04")
def test_pg_running_recovery_receipt_replays_before_and_after_separate_finalization(
    idem_case, terminal, pr204_trace
):
    engine, _, _, principal, project, create = idem_case
    provider = ScriptedProvider([_script_step(terminal)], "provider-a")
    interrupted = _service(engine, provider, StopAfterOutcome)
    execution_id = UUID(interrupted.create(create)["execution_id"])
    if terminal == "CANCELLED":
        provider.observer = lambda request: _service(engine, provider).cancel(
            _command("cancel", principal, project, execution_id)
        )
    with pytest.raises(InterruptedAfterCommit):
        interrupted.execute(_command("execute", principal, project, execution_id))
    provider.observer = None
    recover = _command("recover", principal, project, execution_id)
    with pytest.raises(InterruptedAfterCommit):
        _service(engine, provider, StopRecoveryBeforeFinalization).recover(recover)
    service = _service(engine, provider)
    before = _snapshot(engine, project)
    assert before["executions"][0]["status"] == "RUNNING"
    admission = _saved_admission(before, recover)
    assert service.recover(recover) == admission
    assert _snapshot(engine, project) == before and len(provider.calls) == 1
    service.recover(_command("recover", principal, project, execution_id))
    after = _snapshot(engine, project)
    assert after["executions"][0]["status"] == terminal
    assert service.recover(recover) == admission
    assert _snapshot(engine, project) == after and len(provider.calls) == 1
    pr204_trace.record(
        terminal=terminal,
        running_receipt=admission,
        before_finalization=before,
        after_finalization=after,
        provider_calls=1,
        replay_finalized=False,
    )


STOP_CASES = [
    "cancel_intent",
    "permanent",
    "unknown",
    "cancelled_outcome",
    "attempt_exhausted",
    "time_budget",
    "all_queries_complete",
]


@pytest.mark.parametrize("prior_hits", [False, True], ids=["first-query", "later-query-prior-hits"])
@pytest.mark.parametrize("stop", STOP_CASES)
@pytest.mark.pr204_requirements("PR204-IDEM-05")
def test_pg_new_execute_key_cannot_bypass_committed_stop_or_exhaustion(
    idem_case, stop, prior_hits, pr204_trace
):
    engine, _, _, principal, project, create = idem_case
    prefix = ("first query",) if prior_hits else ()
    target = "target query"
    suffix = () if stop == "all_queries_complete" else ("never sent query",)
    script: list[object] = [success("first query", "provider-a", hits=2)] if prior_hits else []
    if stop in {"permanent", "unknown", "cancelled_outcome"}:
        terminal = {"permanent": "FAILED", "unknown": "UNKNOWN", "cancelled_outcome": "CANCELLED"}[
            stop
        ]
        script.append(_script_step(terminal, target))
    elif stop == "attempt_exhausted":
        script.append(
            ProviderError(
                ProviderFailureKind.RETRYABLE,
                "PROVIDER_TRANSIENT",
                delivery_certainty=DeliveryCertainty.NOT_SENT,
            )
        )
    else:
        script.append(success(target, "provider-a", hits=1))
    provider = ScriptedProvider(script, "provider-a")
    stopped = _service(engine, provider, StopAfterOutcome)
    stopped.stop_query_index = int(prior_hits)
    options = {"queries": prefix + (target,) + suffix}
    if stop == "attempt_exhausted":
        options["max_provider_attempts"] = 1
    if stop == "time_budget":
        options.update(timeout_seconds=1, execution_budget_seconds=5)
    execution_id = UUID(stopped.create(replace(create, **options))["execution_id"])
    original = _command("execute", principal, project, execution_id)
    with pytest.raises(InterruptedAfterCommit):
        stopped.execute(original)
    if stop == "cancel_intent":
        with pytest.raises(InterruptedAfterCommit):
            _service(engine, provider, after_cancel_admission=_interrupt).cancel(
                _command("cancel", principal, project, execution_id)
            )
    deadline = None
    observed_at = None
    if stop == "time_budget":
        snapshot = _snapshot(engine, project)
        execution = snapshot["executions"][0]
        deadline = execution["started_at"] + timedelta(seconds=5)
        with engine.connect() as connection:
            remaining = connection.execute(
                text("SELECT greatest(0,extract(epoch FROM (:deadline-clock_timestamp())))"),
                {"deadline": deadline},
            ).scalar_one()
            connection.execute(
                text("SELECT pg_sleep(:seconds)"), {"seconds": float(remaining) + 0.02}
            )
            observed_at = connection.execute(text("SELECT clock_timestamp()")).scalar_one()
        assert observed_at >= deadline
    before = _snapshot(engine, project)
    calls = len(provider.calls)
    assert before["executions"][0]["status"] == "RUNNING"
    assert all(row["status"] != "RESERVED" for row in before["attempts"])
    assert calls == len(prefix) + 1
    if prior_hits:
        first_query_ids = {
            row["id"] for row in before["queries"] if row["query_text"] == "first query"
        }
        assert (
            sum(row["search_query_record_id"] in first_query_ids for row in before["results"]) == 2
        )
    if stop == "attempt_exhausted":
        target_attempt = next(
            row for row in before["attempts"] if row["query_index"] == len(prefix)
        )
        assert (
            target_attempt["attempt_number"] == 1
            and target_attempt["status"] == "RETRYABLE_FAILURE"
        )
    service = _service(engine, provider)
    assert service.execute(original) == _saved_admission(before, original)
    assert _snapshot(engine, project) == before and len(provider.calls) == calls
    new_command = _command("execute", principal, project, execution_id)
    with pytest.raises(ResearchBaseError) as caught:
        service.execute(new_command)
    assert caught.value.code is ErrorCode.INVALID_STATE_TRANSITION
    assert _snapshot(engine, project) == before and len(provider.calls) == calls
    assert all(row["request_id"] != new_command.request_id for row in before["receipts"])
    pr204_trace.record(
        stop=stop,
        prior_hits=prior_hits,
        original_request=original.request_id,
        rejected_request=new_command.request_id,
        error_code=caught.value.code.value,
        before=before,
        after=_snapshot(engine, project),
        provider_calls_before=calls,
        provider_calls_after=len(provider.calls),
        budget_deadline=deadline,
        post_wait_database_time=observed_at,
    )
