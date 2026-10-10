"""Real PostgreSQL proof for the narrowly authorized recovery corrections."""

import time
from datetime import datetime
from uuid import UUID, uuid4

import pytest
from scripts.pr2_04_pytest_evidence import FactRecorder
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from tests.integration.phase2.test_pr2_03_literature_search_plan_application import (
    _AlwaysValidCredential,
)
from tests.integration.phase2.test_pr2_03_review_guards import _freeze, _setup

from researchbase.application.literature_search_execution import (
    CreateLiteratureSearchExecution,
    ExecuteLiteratureSearchExecution,
    LiteratureSearchExecutionService,
    RecoverLiteratureSearchExecution,
)
from researchbase.application.literature_search_provider import FakeSearchCapability
from researchbase.domain.literature_search_execution import DeliveryCertainty, SearchResponse
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.literature_search_execution_uow import (
    literature_search_execution_uow_factory,
)


class ReservedBeforeInvocation(LiteratureSearchExecutionService):
    def _drive(self, execution_id, actor_id, principal=None, reserved=None, project_id=None):
        # Test-owned crash boundary after the actual reservation transaction committed.
        return None


class OutcomeBeforeFinalization(LiteratureSearchExecutionService):
    def _finalize_execution(self, execution_id, actor_id, status, principal=None, project_id=None):
        # Preserve actual TX B and interrupt only the subsequent TX C.
        return None


@pytest.mark.pr204_requirements("PR204-UNKNOWN-03", "PR204-CRASH-03")
def test_pg_expired_reservation_records_recovery_unknown_without_invented_observations(
    phase2_database_url: str, pr204_trace: FactRecorder,
) -> None:
    engine, plans, principal, project, plan, version = _setup(phase2_database_url)
    try:
        _freeze(engine, plans, principal, project, plan, version)
        provider = FakeSearchCapability(capability_id="provider-a")
        factory = literature_search_execution_uow_factory(
            sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        )
        driver = ReservedBeforeInvocation(factory, provider, credential_verifier=_AlwaysValidCredential())
        created = driver.create(CreateLiteratureSearchExecution(
            project, version, principal.actor_id, principal.deployment_id, uuid4(),
            "provider-a", "1", ("normalization evidence",), timeout_seconds=1,
            execution_budget_seconds=120, principal=principal,
        ))
        execution_id = UUID(created["execution_id"])
        driver.execute(ExecuteLiteratureSearchExecution(
            execution_id, principal.actor_id, principal.deployment_id, uuid4(),
            project_id=project, principal=principal,
        ))
        recovery = LiteratureSearchExecutionService(factory, provider, credential_verifier=_AlwaysValidCredential())
        before = recovery.get_provenance(principal, project, execution_id)
        attempt = before["attempts"][0]
        recovery_after = attempt["recovery_after"]
        assert isinstance(recovery_after, datetime)
        assert attempt["status"] == "RESERVED"
        assert before["execution"]["status"] == "RUNNING"
        with engine.connect() as connection:
            early_db_time = connection.execute(text("SELECT clock_timestamp()")).scalar_one()
        assert early_db_time < recovery_after
        denied = RecoverLiteratureSearchExecution(
            execution_id, principal.actor_id, principal.deployment_id, uuid4(),
            project_id=project, principal=principal,
        )
        with pytest.raises(ResearchBaseError) as caught:
            recovery.recover(denied)
        after_denial = recovery.get_provenance(principal, project, execution_id)
        pr204_trace.record(phase="before_recovery_deadline", database_time=early_db_time,
                           recovery_after=recovery_after, before=before, after=after_denial,
                           error_code=caught.value.code.value, provider_calls=len(provider.calls))
        assert caught.value.code is ErrorCode.CONCURRENT_MODIFICATION
        assert after_denial == before
        assert provider.calls == []

        # Observe the real DB clock crossing the contractual deadline. No clock/retry
        # policy or deadline is patched, and the observer closes each transaction before sleeping.
        wait_limit = time.monotonic() + 40
        while True:
            with engine.connect() as connection:
                ready_at = connection.execute(text("SELECT clock_timestamp()")).scalar_one()
            if ready_at >= recovery_after:
                break
            assert time.monotonic() < wait_limit, "PostgreSQL recovery deadline wait timed out"
            time.sleep(min(0.25, (recovery_after - ready_at).total_seconds()))
        command = RecoverLiteratureSearchExecution(
            execution_id, principal.actor_id, principal.deployment_id, uuid4(),
            project_id=project, principal=principal,
        )
        admission = recovery.recover(command)
        after = recovery.get_provenance(principal, project, execution_id)
        pr204_trace.record(phase="after_real_deadline_recovery", database_time=ready_at,
                           provenance=after, admission=admission, provider_calls=len(provider.calls))
        assert after["execution"]["status"] == "UNKNOWN"
        assert after["execution"]["failure_code"] == "RECOVERY_OUTCOME_UNKNOWN"
        assert after["execution"]["row_version"] == 4
        assert len(after["attempts"]) == 1
        sealed = after["attempts"][0]
        assert sealed["id"] == attempt["id"]
        assert sealed["status"] == "UNKNOWN" and sealed["row_version"] == 2
        assert sealed["failure_code"] == "RECOVERY_OUTCOME_UNKNOWN"
        assert sealed["delivery_certainty"] == "MAY_HAVE_BEEN_SENT"
        assert sealed["invoked_at"] is None and sealed["returned_at"] is None
        assert sealed["query_record_id"] is None and sealed["result_count"] == 0
        assert after["queries"] == [] and after["results"] == []
        assert sum(event["kind"] == "FINISHED" for event in after["events"]) == 1
        assert recovery.recover(command) == admission
        assert recovery.get_provenance(principal, project, execution_id) == after
        assert provider.calls == []
    finally:
        engine.dispose()


@pytest.mark.parametrize("reason", ["PROVIDER_PERMANENT", "PROVIDER_MALFORMED", "PROVIDER_OUTCOME_UNKNOWN"])
@pytest.mark.pr204_requirements("PR204-CRASH-06")
def test_pg_recovery_preserves_sealed_provider_reason_and_terminal_outcome(
    phase2_database_url: str, reason: str, pr204_trace: FactRecorder,
) -> None:
    engine, plans, principal, project, plan, version = _setup(phase2_database_url)
    try:
        _freeze(engine, plans, principal, project, plan, version)
        certainty = (DeliveryCertainty.MAY_HAVE_BEEN_SENT
                     if reason == "PROVIDER_OUTCOME_UNKNOWN"
                     else DeliveryCertainty.RESPONSE_RECEIVED)
        provider = FakeSearchCapability(capability_id="provider-a", responses=[SearchResponse(
            "provider-a", "1", "normalization evidence", "known-provider-response",
            certainty, failure_code=reason,
        )])
        factory = literature_search_execution_uow_factory(
            sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        )
        driver = OutcomeBeforeFinalization(factory, provider, credential_verifier=_AlwaysValidCredential())
        created = driver.create(CreateLiteratureSearchExecution(
            project, version, principal.actor_id, principal.deployment_id, uuid4(),
            "provider-a", "1", ("normalization evidence",), principal=principal,
        ))
        execution_id = UUID(created["execution_id"])
        driver.execute(ExecuteLiteratureSearchExecution(
            execution_id, principal.actor_id, principal.deployment_id, uuid4(),
            project_id=project, principal=principal,
        ))
        recovery = LiteratureSearchExecutionService(factory, provider, credential_verifier=_AlwaysValidCredential())
        before = recovery.get_provenance(principal, project, execution_id)
        assert before["execution"]["status"] == "RUNNING"
        assert before["execution"]["row_version"] == 3
        assert before["attempts"][0]["failure_code"] == reason
        command = RecoverLiteratureSearchExecution(
            execution_id, principal.actor_id, principal.deployment_id, uuid4(),
            project_id=project, principal=principal,
        )
        admission = recovery.recover(command)
        after = recovery.get_provenance(principal, project, execution_id)
        pr204_trace.record(before=before, after=after, admission=admission,
                           provider_calls=len(provider.calls))
        expected_status = "UNKNOWN" if reason == "PROVIDER_OUTCOME_UNKNOWN" else "FAILED"
        assert after["execution"]["status"] == expected_status
        assert after["execution"]["failure_code"] == reason
        assert after["execution"]["row_version"] == 4
        assert after["attempts"] == before["attempts"]
        assert after["queries"] == before["queries"] and after["results"] == before["results"]
        assert after["results"] == []
        assert len(provider.calls) == 1
        assert sum(event["kind"] == "FINISHED" for event in after["events"]) == 1
        assert recovery.recover(command) == admission
        assert recovery.get_provenance(principal, project, execution_id) == after
        recovery.recover(RecoverLiteratureSearchExecution(
            execution_id, principal.actor_id, principal.deployment_id, uuid4(),
            project_id=project, principal=principal,
        ))
        final = recovery.get_provenance(principal, project, execution_id)
        for field in ("execution", "attempts", "queries", "results", "events"):
            assert final[field] == after[field]
        assert len(final["receipts"]) == len(after["receipts"]) + 1
        assert len(provider.calls) == 1
        pr204_trace.record(phase="terminal_noop_and_replay", provenance=final,
                           provider_calls=len(provider.calls))
    finally:
        engine.dispose()
