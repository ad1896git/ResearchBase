"""PG evidence for constructor faults at the actual invoked adapter boundary."""
import json

import pytest

from tests.integration.phase2.test_pr2_04_idempotency_coverage import _snapshot
from tests.integration.phase2.test_pr2_04_provider_pg_coverage import QUERY, setup_case
from tests.unit.phase2.test_pr2_04_response_constructor_acceptance import (
    CANARY, CASES, assert_unknown, constructor_fault,
)


@pytest.mark.pr204_requirements("PR204-PROV-04")
@pytest.mark.parametrize("kind", CASES)
def test_pg_constructor_failure_has_no_salvaged_results(phase2_database_url, kind,
                                                        caplog, pr204_trace):
    engine, provider, service, principal, project, command, _ = setup_case(phase2_database_url, [])
    provider.search = constructor_fault(provider, kind, QUERY, "provider-a")
    try:
        admission = service.execute(command)
        data = service.get_provenance(principal, project, command.execution_id)
        assert_unknown(data, provider.calls)
        assert data["queries"][0]["query_text"] == QUERY
        assert data["queries"][0]["provider_id"] == "provider-a"
        before = _snapshot(engine, project)
        assert len(before["receipts"]) == 2
        assert before["results"] == []
        assert service.execute(command) == admission
        assert _snapshot(engine, project) == before
        assert len(provider.calls) == 1
        assert CANARY not in json.dumps(before, default=str) + json.dumps(admission) + caplog.text
        pr204_trace.record(case=kind, provider_calls=1, provenance=data, rows=before)
    finally:
        engine.dispose()
