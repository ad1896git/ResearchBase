"""Complete PG outcome reapplication without replacing immutable facts."""

from dataclasses import replace
from uuid import uuid4

import pytest

from researchbase.application.literature_search_execution import CancelLiteratureSearchExecution
from researchbase.domain.literature_search_execution import DeliveryCertainty, SearchResponse
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.test_pr2_04_idempotency_coverage import _snapshot
from tests.integration.phase2.test_pr2_04_pg_retrieval_observation_repair import material
from tests.pr2_04_provider_observations import PROVIDER_RETRIEVED_AT
from tests.unit.phase2.test_pr2_04_retrieval_observation_repair import PausedFinalization


class OutcomeOnly(PausedFinalization):
    def _persist_outcome(self, *args, **kwargs):
        super()._persist_outcome(*args, **kwargs)
        # Deliberate crash boundary after real TX B, before next driver work.
        return None, False, False, 0.0


@pytest.mark.pr204_requirements("PR204-DOM-02", "PR204-DB-05")
@pytest.mark.parametrize("kind", ["success", "retryable", "permanent", "unknown", "cancelled"])
@pytest.mark.parametrize("changed", ["request_id", "warnings", "retry_after"])
def test_pg_all_outcome_exact_reapplication_and_changed_tuple(
    kind, changed, phase2_database_url, pr204_trace
):
    engine, principal, project, provider, service, command = material(
        phase2_database_url, 0, OutcomeOnly
    )
    response = SearchResponse(
        "provider-a",
        "1",
        "normalization evidence",
        "observed-id",
        DeliveryCertainty.MAY_HAVE_BEEN_SENT
        if kind == "unknown"
        else DeliveryCertainty.NOT_SENT
        if kind == "retryable"
        else DeliveryCertainty.RESPONSE_RECEIVED,
        failure_code={
            "success": None,
            "retryable": "PROVIDER_TIMEOUT",
            "permanent": "PROVIDER_PERMANENT",
            "unknown": None,
            "cancelled": "PROVIDER_CANCELLED",
        }[kind],
        retrieved_at=PROVIDER_RETRIEVED_AT if kind == "success" else None,
    )
    provider.responses = [response]
    if kind == "cancelled":

        def cancel(request):
            provider.responses[0] = replace(
                response,
                execution_id=request.execution_id,
                attempt_id=request.attempt_id,
                provider_request_key=request.provider_request_key,
            )
            service.cancel(
                CancelLiteratureSearchExecution(
                    command.execution_id,
                    principal.actor_id,
                    principal.deployment_id,
                    uuid4(),
                    project_id=project,
                    principal=principal,
                )
            )

        provider.observer = cancel
    try:
        service.execute(command)
        before = _snapshot(engine, project)
        attempt = before["attempts"][0]
        assert (
            attempt["status"]
            == {
                "success": "SUCCEEDED",
                "retryable": "RETRYABLE_FAILURE",
                "permanent": "PERMANENT_FAILURE",
                "unknown": "UNKNOWN",
                "cancelled": "CANCELLED",
            }[kind]
        )
        assert attempt["row_version"] == 2
        assert service.outcome_args is not None
        args, kwargs = service.outcome_args
        service._persist_outcome(*args, **kwargs)
        assert _snapshot(engine, project) == before
        different = list(args)
        delta = {
            "request_id": {"provider_request_id": "other-id"},
            "warnings": {"warning_codes": ("PARTIAL_COVERAGE",)},
            "retry_after": {"retry_after_seconds": 1},
        }[changed]
        different[6] = replace(different[6], **delta)
        with pytest.raises(ResearchBaseError) as caught:
            service._persist_outcome(*different, **kwargs)
        assert caught.value.code is ErrorCode.IMMUTABLE_RECORD
        assert _snapshot(engine, project) == before
        assert len(provider.calls) == 1
        pr204_trace.record(
            kind=kind,
            changed=changed,
            before=before,
            after=_snapshot(engine, project),
            provider_calls=1,
            error=caught.value.code.value,
        )
    finally:
        engine.dispose()
