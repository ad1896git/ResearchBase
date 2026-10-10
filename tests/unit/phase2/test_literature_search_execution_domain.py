from __future__ import annotations

from tests.pr2_04_provider_observations import PROVIDER_RETRIEVED_AT

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from researchbase.domain.literature_search_execution import (
    DeliveryCertainty,
    ExecutionStatus,
    LiteratureSearchExecution,
    SearchHit,
    SearchQueryRecord,
    SearchResponse,
)


def test_planned_execution_transitions_to_running_then_succeeded() -> None:
    execution = LiteratureSearchExecution.create(
        project_id=uuid4(),
        plan_version_id=uuid4(),
        requested_by=uuid4(),
        idempotency_key=uuid4(),
        execution_context={"queries": [{"query_type": "TEXT", "query_text": "cortex"}]},
    )

    assert execution.status is ExecutionStatus.PLANNED
    execution.start(uuid4(), datetime.now(UTC))
    assert execution.status is ExecutionStatus.RUNNING
    execution.finish(ExecutionStatus.SUCCEEDED, datetime.now(UTC))
    assert execution.status is ExecutionStatus.SUCCEEDED


def test_terminal_execution_cannot_transition_again() -> None:
    execution = LiteratureSearchExecution.create(
        project_id=uuid4(),
        plan_version_id=uuid4(),
        requested_by=uuid4(),
        idempotency_key=uuid4(),
        execution_context={"queries": [{"query_type": "TEXT", "query_text": "cortex"}]},
    )
    execution.cancel(datetime.now(UTC))

    with pytest.raises(ValueError, match="terminal"):
        execution.start(uuid4(), datetime.now(UTC))


def test_uncertain_response_cannot_be_treated_as_success() -> None:
    response = SearchResponse.uncertain(
        provider_id="fake",
        provider_version="1",
        normalized_query="cortex",
        provider_request_id=None,
    )

    assert response.delivery_certainty is DeliveryCertainty.MAY_HAVE_BEEN_SENT
    assert response.hits == ()
    with pytest.raises(ValueError, match="uncertain"):
        response.require_success()


@pytest.mark.parametrize("retry_after", [-1, 2_147_483_648, True, 1.5])
def test_provider_retry_after_must_fit_persisted_integer_domain(retry_after) -> None:
    with pytest.raises(ValueError, match="retry_after_seconds"):
        SearchResponse(
            "fake",
            "1",
            "cortex",
            None,
            DeliveryCertainty.NOT_SENT,
            retry_after_seconds=retry_after,
            failure_code="PROVIDER_TIMEOUT",
        )


def test_provider_failure_cannot_include_partial_hits() -> None:
    with pytest.raises(ValueError, match="cannot contain result hits"):
        SearchResponse(
            "fake",
            "1",
            "cortex",
            None,
            DeliveryCertainty.RESPONSE_RECEIVED,
            hits=(SearchHit(None, "Partial", None, None, None),),
            failure_code="PROVIDER_PERMANENT",
        )


def test_unknown_failure_code_requires_uncertain_delivery() -> None:
    with pytest.raises(ValueError, match="uncertain delivery"):
        SearchResponse(
            "fake",
            "1",
            "cortex",
            None,
            DeliveryCertainty.RESPONSE_RECEIVED,
            failure_code="PROVIDER_OUTCOME_UNKNOWN",
        )


def test_result_hash_is_stable_and_not_result_identity() -> None:
    query = SearchQueryRecord(
        id=uuid4(),
        execution_id=uuid4(),
        attempt_id=uuid4(),
        ordinal=0,
        query_text="cortex",
        provider_id="fake",
        provider_version="1",
        executed_at=datetime.now(UTC),
    )
    hit = SearchHit(
        external_identifier="paper-1",
        title="A paper",
        url="https://example.test/paper-1",
        snippet=None,
        provider_score=None,
    )

    assert query.query_hash
    assert hit.result_hash(query.query_hash, 0) == hit.result_hash(query.query_hash, 0)
    assert hit.result_hash(query.query_hash, 0) != hit.result_hash(query.query_hash, 1)


def test_query_hash_matches_frozen_contract_golden_vector() -> None:
    query = SearchQueryRecord(
        id=UUID(int=1),
        execution_id=UUID(int=2),
        attempt_id=UUID(int=3),
        ordinal=0,
        query_text="A search",
        provider_id="provider-a",
        provider_version=None,
        executed_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    assert query.query_hash == "bf4651bc6001bafa6ad96bb1eb08edbb28abb6414368c46b7f8d757ca6a5ee07"


def test_result_hash_uses_canonical_decimal_score_strings() -> None:
    query_hash = "a" * 64
    rank = 0
    padded = SearchHit(None, "Paper", None, None, Decimal("001.2300"))
    normalized = SearchHit(None, "Paper", None, None, Decimal("1.23"))
    negative_zero = SearchHit(None, "Paper", None, None, Decimal("-0.00"))
    positive_zero = SearchHit(None, "Paper", None, None, Decimal("0"))

    assert padded.result_hash(query_hash, rank) == normalized.result_hash(query_hash, rank)
    assert negative_zero.result_hash(query_hash, rank) == positive_zero.result_hash(
        query_hash, rank
    )


def test_provider_text_is_nfc_without_trimming_scientific_material() -> None:
    query = SearchQueryRecord(
        id=uuid4(),
        execution_id=uuid4(),
        attempt_id=uuid4(),
        ordinal=0,
        query_text="  cortex\tsearch  ",
        provider_id="fake",
        provider_version="1",
        executed_at=datetime.now(UTC),
        perspective="  author perspective  ",
    )
    hit = SearchHit("  provider id  ", "  Paper title  ", None, "  excerpt  ", None)
    empty_optional = SearchHit(None, "Paper", None, "   ", None)

    assert query.query_text == "cortex search"
    assert query.perspective == "  author perspective  "
    assert hit.external_identifier == "  provider id  "
    assert hit.title == "  Paper title  "
    assert hit.snippet == "  excerpt  "
    assert empty_optional.snippet is None


@pytest.mark.parametrize("url", ["http:///paper", "https:///paper", "https://?query=paper"])
def test_result_url_requires_http_authority(url: str) -> None:
    with pytest.raises(ValueError, match="valid http or https URL"):
        SearchHit(None, "Paper", url, None, None)


def test_result_url_accepts_case_insensitive_http_scheme() -> None:
    assert SearchHit(None, "Paper", "HTTPS://example.test/paper", None, None).url == (
        "HTTPS://example.test/paper"
    )


def test_provider_response_echoes_are_normalized_before_application_comparison() -> None:
    response = SearchResponse(
        " cafe\u0301 ",
        " 1 ",
        " Cafe\u0301\tsearch  ",
        " request-1 ",
        DeliveryCertainty.RESPONSE_RECEIVED,
        retrieved_at=PROVIDER_RETRIEVED_AT,
    )

    assert response.provider_id == "café"
    assert response.provider_version == "1"
    assert response.normalized_query == "Café search"
    assert response.provider_request_id == "request-1"


def test_query_ordinal_rejects_boolean_values() -> None:
    with pytest.raises(ValueError, match="ordinal must be an integer"):
        SearchQueryRecord(
            id=uuid4(),
            execution_id=uuid4(),
            attempt_id=uuid4(),
            ordinal=True,
            query_text="cortex",
            provider_id="fake",
            provider_version="1",
            executed_at=datetime.now(UTC),
        )


def test_result_hash_rank_rejects_boolean_values() -> None:
    hit = SearchHit(None, "Paper", None, None, None)

    with pytest.raises(ValueError, match="rank must be an integer"):
        hit.result_hash("a" * 64, True)
