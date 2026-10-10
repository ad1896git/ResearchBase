"""Cancellation while the fake provider is entered and between committed outcomes."""

from uuid import UUID, uuid4

import pytest
from scripts.pr2_04_pytest_evidence import FactRecorder

from researchbase.application.literature_search_execution import (
    CancelLiteratureSearchExecution,
    CreateLiteratureSearchExecution,
    ExecuteLiteratureSearchExecution,
    LiteratureSearchExecutionService,
)
from researchbase.application.literature_search_provider import FakeSearchCapability
from researchbase.domain.literature_search_execution import (
    DeliveryCertainty,
    SearchHit,
    SearchResponse,
)
from tests.integration.phase2.test_pr2_03_review_guards import _freeze, _setup
from tests.integration.phase2.test_pr2_04_execution_provenance import _execution_service
from tests.integration.phase2.test_pr2_04_transaction_coverage import ObservedTransactions
from tests.pr2_04_provider_observations import PROVIDER_RETRIEVED_AT


@pytest.mark.parametrize(
    "certainty,reason,terminal",
    [
        (DeliveryCertainty.NOT_SENT, "PROVIDER_CANCELLED", "CANCELLED"),
        (DeliveryCertainty.RESPONSE_RECEIVED, "PROVIDER_CANCELLED", "CANCELLED"),
        (DeliveryCertainty.MAY_HAVE_BEEN_SENT, "PROVIDER_OUTCOME_UNKNOWN", "UNKNOWN"),
    ],
    ids=["definitely-not-sent", "confirmed-response", "uncertain-cancellation"],
)
@pytest.mark.pr204_requirements("PR204-CANCEL-02")
def test_pg_cancellation_during_provider_distinguishes_remote_certainty(
    phase2_database_url, certainty, reason, terminal, pr204_trace: FactRecorder
):
    engine, plans, principal, project, plan, version = _setup(phase2_database_url)
    try:
        _freeze(engine, plans, principal, project, plan, version)
        provider = FakeSearchCapability(
            capability_id="provider-a",
            responses=[
                SearchResponse(
                    "provider-a",
                    "1",
                    "normalization evidence",
                    "cancellation-response",
                    certainty,
                    failure_code=reason,
                )
            ],
        )
        service = _execution_service(engine, provider)
        admission = service.create(
            CreateLiteratureSearchExecution(
                project,
                version,
                principal.actor_id,
                principal.deployment_id,
                uuid4(),
                "provider-a",
                "1",
                ("normalization evidence", "never sent query"),
                principal=principal,
            )
        )
        execution_id = UUID(admission["execution_id"])

        def cancel_during_call(request):
            from dataclasses import replace

            if reason == "PROVIDER_CANCELLED":
                provider.responses[0] = replace(
                    provider.responses[0],
                    execution_id=request.execution_id,
                    attempt_id=request.attempt_id,
                    provider_request_key=request.provider_request_key,
                )
            assert engine.pool.checkedout() == 0
            receipt = service.cancel(
                CancelLiteratureSearchExecution(
                    execution_id,
                    principal.actor_id,
                    principal.deployment_id,
                    uuid4(),
                    project_id=project,
                    principal=principal,
                )
            )
            observed = service.get_provenance(principal, project, execution_id)
            pr204_trace.record(
                phase="provider_outstanding_after_C1",
                cancellation_admission=receipt,
                provenance=observed,
                attempt_id=request.attempt_id,
            )
            assert receipt["accepted_row_version"] == 3
            assert observed["execution"]["status"] == "RUNNING"
            assert [a["status"] for a in observed["attempts"]] == ["RESERVED"]
            assert not any(e["kind"] == "FINISHED" for e in observed["events"])

        provider.observer = cancel_during_call
        service.execute(
            ExecuteLiteratureSearchExecution(
                execution_id,
                principal.actor_id,
                principal.deployment_id,
                uuid4(),
                project_id=project,
                principal=principal,
            )
        )
        after = service.get_provenance(principal, project, execution_id)
        pr204_trace.record(
            provenance=after, provider_calls=len(provider.calls), certainty=certainty.value
        )
        assert after["execution"]["status"] == terminal and after["execution"]["row_version"] == 5
        assert after["attempts"][0]["status"] == terminal
        assert after["attempts"][0]["delivery_certainty"] == certainty.value
        assert len(provider.calls) == 1 and len(after["attempts"]) == 1
        assert len(after["queries"]) == 1 and after["results"] == []
        assert sum(e["kind"] == "CANCEL_REQUESTED" for e in after["events"]) == 1
        assert sum(e["kind"] == "FINISHED" for e in after["events"]) == 1
    finally:
        engine.dispose()


@pytest.mark.pr204_requirements("PR204-CANCEL-01")
def test_pg_prestart_cancel_commits_admission_then_separate_finalization(
    phase2_database_url, pr204_trace: FactRecorder, monkeypatch: pytest.MonkeyPatch
):
    engine, plans, principal, project, plan, version = _setup(phase2_database_url)
    try:
        _freeze(engine, plans, principal, project, plan, version)
        provider = FakeSearchCapability(capability_id="provider-a")
        base = _execution_service(engine, provider)
        admitted = base.create(
            CreateLiteratureSearchExecution(
                project,
                version,
                principal.actor_id,
                principal.deployment_id,
                uuid4(),
                "provider-a",
                "1",
                ("normalization evidence",),
                principal=principal,
            )
        )
        execution_id = UUID(admitted["execution_id"])
        observations = ObservedTransactions(engine, pr204_trace)

        def observe_committed_c1():
            assert observations.active == 0 and engine.pool.checkedout() == 0
            pending = base.get_provenance(principal, project, execution_id)
            pr204_trace.record(phase="C1_COMMITTED_BEFORE_C2", provenance=pending)
            assert pending["execution"]["status"] == "PLANNED"
            assert pending["execution"]["row_version"] == 2
            assert [e["kind"] for e in pending["events"]] == ["CREATED", "CANCEL_REQUESTED"]
            assert len(pending["receipts"]) == 2
            assert (
                pending["attempts"] == [] and pending["queries"] == [] and pending["results"] == []
            )
            assert provider.calls == []
            committed = [e for e in observations.events if e.get("point") == "TX_COMMIT"]
            observations.fact(point="C1_VISIBLE", db_attempt=committed[-1]["db_attempt"])

        service = LiteratureSearchExecutionService(
            observations.factory,
            provider,
            credential_verifier=base._credential_verifier,
            after_cancel_admission=observe_committed_c1,
        )
        authorize = service._authorize
        disclose = service._authorize_disclosure

        def observe_authorization(uow, *args, **kwargs):
            authorize(uow, *args, **kwargs)
            observations.fact(
                point="CURRENT_AUTHORIZED",
                db_attempt=uow.number,
                trusted_authorization_time=uow.literature_search_plan.at(),
            )

        def observe_disclosure(*args, **kwargs):
            committed = [e for e in observations.events if e.get("point") == "TX_COMMIT"]
            observations.fact(
                point="DISCLOSURE_BEGIN", prior_commit_attempt=committed[-1]["db_attempt"]
            )
            disclose(*args, **kwargs)
            observations.fact(point="DISCLOSURE_AUTHORIZED")

        monkeypatch.setattr(service, "_authorize", observe_authorization)
        monkeypatch.setattr(service, "_authorize_disclosure", observe_disclosure)
        command = CancelLiteratureSearchExecution(
            execution_id,
            principal.actor_id,
            principal.deployment_id,
            uuid4(),
            project_id=project,
            principal=principal,
        )
        receipt = service.cancel(command)
        after = base.get_provenance(principal, project, execution_id)
        pr204_trace.record(
            phase="C2_COMMITTED",
            provenance=after,
            cancel_admission=receipt,
            provider_calls=len(provider.calls),
        )
        assert receipt["accepted_row_version"] == 2
        assert set(receipt) == {
            "execution_id",
            "command_name",
            "accepted_at",
            "accepted_row_version",
        }
        assert (
            after["execution"]["status"] == "CANCELLED" and after["execution"]["row_version"] == 3
        )
        assert (
            after["execution"]["started_at"] is None
            and after["execution"]["finished_at"] is not None
        )
        assert [e["kind"] for e in after["events"]] == ["CREATED", "CANCEL_REQUESTED", "FINISHED"]
        assert [(e["prior_row_version"], e["new_row_version"]) for e in after["events"]] == [
            (None, 1),
            (1, 2),
            (2, 3),
        ]
        assert after["attempts"] == [] and after["queries"] == [] and after["results"] == []
        assert len(after["receipts"]) == 2 and provider.calls == []
        assert service.cancel(command) == receipt
        assert base.get_provenance(principal, project, execution_id) == after
        events = observations.events
        c1 = next(e for e in events if e.get("point") == "C1_VISIBLE")
        disclosures = [i for i, e in enumerate(events) if e.get("point") == "DISCLOSURE_BEGIN"]
        assert (
            len(disclosures) == 2
        )  # Initial result and exact replay each require current entitlement.
        c2_attempt = events[disclosures[0]]["prior_commit_attempt"]
        assert c1["db_attempt"] != c2_attempt
        c2_commit = next(
            i
            for i, e in enumerate(events)
            if e.get("point") == "TX_COMMIT" and e["db_attempt"] == c2_attempt
        )
        assert events.index(c1) < c2_commit < disclosures[0]
        authorization_attempts = []
        for start in disclosures:
            end = next(
                i
                for i in range(start + 1, len(events))
                if events[i].get("point") == "DISCLOSURE_AUTHORIZED"
            )
            authorized = next(
                e for e in events[start:end] if e.get("point") == "CURRENT_AUTHORIZED"
            )
            authorization_attempts.append(authorized["db_attempt"])
            assert any(
                e.get("point") == "TX_COMMIT" and e["db_attempt"] == authorized["db_attempt"]
                for e in events[start:end]
            )
        assert authorization_attempts[0] != authorization_attempts[1]
    finally:
        engine.dispose()


@pytest.mark.pr204_requirements("PR204-CANCEL-03")
def test_pg_cancel_after_known_outcome_retains_hits_and_prevents_next_query(
    phase2_database_url, pr204_trace: FactRecorder
):
    engine, plans, principal, project, plan, version = _setup(phase2_database_url)
    try:
        _freeze(engine, plans, principal, project, plan, version)
        provider = FakeSearchCapability(
            capability_id="provider-a",
            responses=[
                SearchResponse.success(
                    provider_id="provider-a",
                    provider_version="1",
                    normalized_query="normalization evidence",
                    provider_request_id="known-response",
                    hits=(SearchHit("hit", "Paper", None, None, None),),
                    retrieved_at=PROVIDER_RETRIEVED_AT,
                )
            ],
        )
        base = _execution_service(engine, provider)

        class CancelBetweenPhases(LiteratureSearchExecutionService):
            def _persist_outcome(self, *args, **kwargs):
                result = super()._persist_outcome(*args, **kwargs)
                before = base.get_provenance(principal, project, args[0])
                self.cancel(
                    CancelLiteratureSearchExecution(
                        args[0],
                        principal.actor_id,
                        principal.deployment_id,
                        uuid4(),
                        project_id=project,
                        principal=principal,
                    )
                )
                pr204_trace.record(phase="after_TX_B_before_next_reservation", before_cancel=before)
                return result

        service = CancelBetweenPhases(
            base._uow_factory, provider, credential_verifier=base._credential_verifier
        )
        admission = service.create(
            CreateLiteratureSearchExecution(
                project,
                version,
                principal.actor_id,
                principal.deployment_id,
                uuid4(),
                "provider-a",
                "1",
                ("normalization evidence", "never sent query"),
                principal=principal,
            )
        )
        execution_id = UUID(admission["execution_id"])
        service.execute(
            ExecuteLiteratureSearchExecution(
                execution_id,
                principal.actor_id,
                principal.deployment_id,
                uuid4(),
                project_id=project,
                principal=principal,
            )
        )
        after = base.get_provenance(principal, project, execution_id)
        pr204_trace.record(provenance=after, provider_calls=len(provider.calls))
        assert after["execution"]["status"] == "CANCELLED"
        assert len(provider.calls) == 1 and len(after["attempts"]) == 1
        assert after["attempts"][0]["status"] == "SUCCEEDED"
        assert len(after["queries"]) == 1 and len(after["results"]) == 1
        assert after["results"][0]["external_identifier"] == "hit"
        assert sum(e["kind"] == "FINISHED" for e in after["events"]) == 1
    finally:
        engine.dispose()
