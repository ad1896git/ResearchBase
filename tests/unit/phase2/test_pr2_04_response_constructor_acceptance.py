"""Legitimate DTO constructor faults during observed adapter invocation."""

import json

import pytest

from researchbase.domain.literature_search_execution import SearchHit, SearchResponse
from tests.pr2_04_provider_observations import PROVIDER_RETRIEVED_AT
from tests.unit.phase2.test_pr2_04_provider_coverage import harness

CANARY = "PR204_RESPONSE_CONSTRUCTOR_CANARY_b872"
CASES = ["nan", "inf", "negative-inf", "blank-title", "warning", "retry-type", "request-id"]


def constructor_fault(provider, kind, query, provider_id):
    def search(request, context=None):
        provider.calls.append(request)
        good = SearchHit("good", "Valid first hit", None, None, None)
        try:
            if kind in {"nan", "inf", "negative-inf", "blank-title"}:
                score = {"nan": "NaN", "inf": "Infinity", "negative-inf": "-Infinity"}.get(kind)
                bad = SearchHit(
                    "bad", " " if kind == "blank-title" else "Bad hit", None, None, score
                )
                hits = (good, bad)
            else:
                hits = (good,)
            return SearchResponse.success(
                provider_id=provider_id,
                provider_version="1",
                normalized_query=query,
                provider_request_id="x" * 257 if kind == "request-id" else None,
                hits=hits,
                retrieved_at=PROVIDER_RETRIEVED_AT,
                **({"warning_codes": ("INVALID",)} if kind == "warning" else {}),
                **({"retry_after_seconds": True} if kind == "retry-type" else {}),
            )
        except (ValueError, TypeError) as error:
            raise ValueError(CANARY) from error

    return search


def assert_unknown(data, calls):
    assert len(calls) == len(data["attempts"]) == len(data["queries"]) == 1
    assert data["results"] == []
    attempt = data["attempts"][0]
    assert attempt["status"] == data["execution"]["status"] == "UNKNOWN"
    assert attempt["delivery_certainty"] == "MAY_HAVE_BEEN_SENT"
    assert attempt["failure_code"] == "PROVIDER_OUTCOME_UNKNOWN"
    assert attempt["invoked_at"] is not None
    assert attempt["query_record_id"] == data["queries"][0]["id"]
    assert attempt["result_count"] == 0


@pytest.mark.pr204_requirements("PR204-PROV-04")
@pytest.mark.parametrize("kind", CASES)
def test_observed_constructor_failure_rejects_entire_response(kind, caplog, pr204_trace):
    repo, provider, service, command, project = harness([])
    provider.search = constructor_fault(provider, kind, "cortex", "fake")
    admission = service.execute(command)
    data = service.get_provenance(None, project, command.execution_id)
    assert_unknown(data, provider.calls)
    assert data["queries"][0]["query_text"] == "cortex"
    assert service.execute(command) == admission
    assert service.get_provenance(None, project, command.execution_id) == data
    assert len(provider.calls) == 1
    assert CANARY not in json.dumps(data, default=str) + json.dumps(admission) + caplog.text
    pr204_trace.record(case=kind, provider_calls=1, provenance=data, admission=admission)
