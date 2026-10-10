"""Frozen PR2-04 transition and independently calculated hash vectors."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from scripts.pr2_04_pytest_evidence import FactRecorder

from researchbase.domain.literature_search_execution import (
    DeliveryCertainty,
    ExecutionStatus,
    LiteratureSearchExecution,
    SearchHit,
    SearchQueryRecord,
    SearchResponse,
)

AT = datetime(2026, 1, 1, tzinfo=UTC)
OPERATIONS = (
    "start",
    "cancel",
    "request_cancellation",
    *[f"finish_{s.value}" for s in ExecutionStatus],
)


@pytest.mark.pr204_requirements("PR204-DOM-01")
@pytest.mark.parametrize("status", list(ExecutionStatus), ids=lambda s: s.value)
@pytest.mark.parametrize("operation", OPERATIONS)
def test_execution_transition_matrix(
    status: ExecutionStatus, operation: str, pr204_trace: FactRecorder
) -> None:
    row = LiteratureSearchExecution.create(
        project_id=uuid4(),
        plan_version_id=uuid4(),
        requested_by=uuid4(),
        idempotency_key=uuid4(),
        execution_context={},
    )
    row.status = status
    before = deepcopy(row)
    allowed = status in {ExecutionStatus.PLANNED, ExecutionStatus.RUNNING} and (
        operation in {"cancel", "request_cancellation"}
        or (operation == "start" and status is ExecutionStatus.PLANNED)
        or (
            operation.startswith("finish_")
            and status is ExecutionStatus.RUNNING
            and operation[7:] not in {"PLANNED", "RUNNING"}
        )
    )

    def act() -> None:
        if operation == "start":
            row.start(UUID(int=7), AT)
        elif operation == "cancel":
            row.cancel(AT)
        elif operation == "request_cancellation":
            row.request_cancellation()
        else:
            row.finish(ExecutionStatus(operation[7:]), AT)

    if allowed:
        act()
        assert row.row_version == before.row_version + 1
        expected = (
            ExecutionStatus.RUNNING
            if operation == "start"
            else ExecutionStatus.CANCELLED
            if operation == "cancel"
            else status
            if operation == "request_cancellation"
            else ExecutionStatus(operation[7:])
        )
        assert row.status is expected
        if operation == "start":
            assert row.executed_by == UUID(int=7) and row.started_at == AT
        if operation == "cancel" or operation.startswith("finish_"):
            assert row.finished_at == AT
        if operation == "request_cancellation":
            assert row.cancellation_requested
    else:
        with pytest.raises(ValueError):
            act()
        assert row == before
    pr204_trace.record(
        from_state=status.value,
        operation=operation,
        permitted=allowed,
        final_state=row.status.value,
        row_version=row.row_version,
    )


@pytest.mark.pr204_requirements("PR204-TRACE-02")
@pytest.mark.parametrize(
    "ordinal,digest",
    [
        (0, "bf4651bc6001bafa6ad96bb1eb08edbb28abb6414368c46b7f8d757ca6a5ee07"),
        (1, "4f1ac06997abf035615230390cf062c84d6be439b73b4675820c7fc0f3682ba0"),
    ],
    ids=["first", "retry"],
)
def test_query_literal_golden(ordinal: int, digest: str, pr204_trace: FactRecorder) -> None:
    query = SearchQueryRecord(
        UUID(int=1), UUID(int=2), UUID(int=3), ordinal, "  A\tsearch\n", "provider-a", None, AT
    )
    assert query.query_text == "A search"
    assert query.query_hash == digest
    different_identity = SearchQueryRecord(
        uuid4(),
        query.execution_id,
        uuid4(),
        ordinal,
        "A search",
        "provider-a",
        None,
        datetime(2027, 1, 1, tzinfo=UTC),
        "perspective",
    )
    assert different_identity.query_hash == digest
    pr204_trace.record(
        ordinal=ordinal, normalized_query=query.query_text, query_hash=query.query_hash
    )


@pytest.mark.pr204_requirements("PR204-TRACE-03")
@pytest.mark.parametrize(
    "score,digest",
    [
        (None, "e71d71345fd321a24a407ee9dadb513dc9b57f13955a37ceaed3fb1f9563ffba"),
        (Decimal("001.2300"), "5179f58bd28401ada2658af58d5907cbcc669f03ec349c72a4fccac62be8ab6d"),
        (Decimal("-0.00"), "f87e8174683b12e8e8005eea85273bae36a104d78ed67998bc15311bb4bce499"),
    ],
    ids=["null", "decimal", "negative-zero"],
)
def test_result_literal_golden(
    score: Decimal | None, digest: str, pr204_trace: FactRecorder
) -> None:
    hit = SearchHit(" ", "Paper", " ", " ", score)
    assert (hit.external_identifier, hit.url, hit.snippet) == (None, None, None)
    assert hit.result_hash("a" * 64, 0) == digest
    assert hit.result_hash("a" * 64, 1) != digest
    assert hit.result_hash("b" * 64, 0) != digest
    pr204_trace.record(score=score, rank=0, content_hash=digest)


@pytest.mark.pr204_requirements("PR204-DOM-02")
@pytest.mark.parametrize(
    "failure",
    [
        "PROVIDER_TIMEOUT",
        "PROVIDER_TRANSIENT",
        "PROVIDER_PERMANENT",
        "PROVIDER_RATE_LIMIT",
        "PROVIDER_CANCELLED",
    ],
)
def test_uncertainty_cannot_be_reclassified_safe(failure: str, pr204_trace: FactRecorder) -> None:
    with pytest.raises(ValueError, match="uncertain delivery"):
        SearchResponse(
            "fake", "1", "cortex", None, DeliveryCertainty.MAY_HAVE_BEEN_SENT, failure_code=failure
        )
    pr204_trace.record(certainty="MAY_HAVE_BEEN_SENT", rejected_failure=failure)


@pytest.mark.pr204_requirements("PR204-PROV-04", "PR204-DOM-03")
@pytest.mark.parametrize(
    "field,value",
    [
        ("title", " "),
        ("title", "x" * 2049),
        ("external_identifier", "x" * 1025),
        ("url", "https://example.test/" + "x" * 4096),
        ("url", "https://secret:password@example.test"),
        ("url", "file:///private/key"),
        ("snippet", "x" * 4097),
        ("provider_score", float("nan")),
        ("provider_score", float("inf")),
        ("provider_score", float("-inf")),
    ],
    ids=[
        "blank-title",
        "long-title",
        "long-id",
        "long-url",
        "userinfo",
        "file-url",
        "long-snippet",
        "nan",
        "inf",
        "negative-inf",
    ],
)
def test_hit_rejects_invalid_fields(field: str, value: object, pr204_trace: FactRecorder) -> None:
    fields: dict[str, Any] = dict(
        external_identifier=None, title="Paper", url=None, snippet=None, provider_score=None
    )
    fields[field] = value
    with pytest.raises((TypeError, ValueError)):
        SearchHit(**fields)
    pr204_trace.record(rejected_field=field, rejected_kind=type(value).__name__)
