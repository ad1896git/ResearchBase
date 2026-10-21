"""Frozen pack §8: credential/raw payload metadata is outside every neutral DTO."""

from dataclasses import fields, replace
from datetime import UTC, datetime

import pytest
from scripts.pr2_04_pytest_evidence import FactRecorder

from researchbase.application.literature_search_provider import SearchCallContext, SearchRequest
from researchbase.domain.literature_search_execution import SearchHit
from tests.unit.phase2.test_pr2_04_provider_coverage import harness, success


@pytest.mark.pr204_requirements("PR204-SEC-01")
@pytest.mark.parametrize("dto", ["request", "context", "response", "hit"])
@pytest.mark.parametrize(
    "field", ["api_key", "authorization", "credentials", "headers", "raw_payload", "retry_callback"]
)
def test_neutral_dtos_reject_secret_or_raw_metadata_without_effects(
    dto, field, pr204_trace: FactRecorder
):
    repo, provider, service, command, project = harness([success()])
    service.execute(command)
    before = service.get_provenance(None, project, command.execution_id)
    request = provider.calls[0]
    objects = {
        "request": request,
        "context": SearchCallContext(command.execution_id, datetime.now(UTC), 1.0, lambda: False),
        "response": success(),
        "hit": SearchHit(None, "Paper", None, None, None),
    }
    with pytest.raises(TypeError):
        replace(objects[dto], **{field: "PR204_CLOSED_DTO_SECRET_DO_NOT_PERSIST"})
    assert service.get_provenance(None, project, command.execution_id) == before
    assert len(provider.calls) == 1
    pr204_trace.record(
        dto=dto,
        rejected_metadata_field=field,
        exception_type="TypeError",
        durable_provenance_unchanged=True,
        provider_calls=1,
    )


@pytest.mark.pr204_requirements("PR204-DOM-03")
def test_search_request_has_exact_frozen_invocation_fields(pr204_trace: FactRecorder):
    actual = {item.name for item in fields(SearchRequest)}
    expected = {
        "execution_id",
        "attempt_id",
        "provider_request_key",
        "plan_version_id",
        "plan_content_hash",
        "plan_material",
        "query_index",
        "query_text",
        "perspective",
        "query_type",
        "provider_id",
        "provider_version",
        "max_results",
    }
    pr204_trace.record(actual_fields=sorted(actual), required_fields=sorted(expected))
    assert actual == expected
