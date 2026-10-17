"""Application admission must enforce the frozen integer context, not just ranges.

The real application service and repository are exercised. In-memory persistence
does not establish PostgreSQL acceptance; it makes pre-admission effects visible.
"""

from dataclasses import replace
from uuid import uuid4

import pytest
from scripts.pr2_04_pytest_evidence import FactRecorder

from researchbase.application.literature_search_execution import (
    CreateLiteratureSearchExecution,
    LiteratureSearchExecutionService,
)
from researchbase.application.literature_search_provider import FakeSearchCapability
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.in_memory_literature_search_execution import (
    InMemoryExecutionUnitOfWork,
    InMemoryLiteratureSearchExecutionRepository,
)

LIMITS = (
    ("max_results", 1, 100),
    ("max_provider_attempts", 1, 3),
    ("timeout_seconds", 1, 30),
    ("execution_budget_seconds", 1, 600),
)


def _admit(field: str, value: object, trace: FactRecorder):
    repository = InMemoryLiteratureSearchExecutionRepository()
    provider = FakeSearchCapability()
    service = LiteratureSearchExecutionService(
        lambda: InMemoryExecutionUnitOfWork(repository),
        provider,
        allow_unverified_principal=True,
    )
    command = replace(
        CreateLiteratureSearchExecution(
            uuid4(), uuid4(), uuid4(), "test", uuid4(), "fake", "1", ("bounded query",)
        ),
        **{field: value},
    )
    error = None
    admission = None
    try:
        admission = service.create(command)
    except Exception as caught:
        # Observe the public result; do not turn raw exceptions into canonical ones.
        error = caught
    trace.record(
        storage_kind="deterministic_in_memory",
        field=field,
        supplied_value=value,
        supplied_type=type(value).__name__,
        error_type=type(error).__name__ if error else None,
        error_code=error.code.value if isinstance(error, ResearchBaseError) else None,
        admission=admission,
        execution_count=len(repository.executions),
        receipt_count=len(repository.receipts),
        event_count=len(repository.events),
        attempt_count=len(repository.attempt_rows),
        provider_calls=len(provider.calls),
    )
    return error, admission, repository, provider


@pytest.mark.parametrize("field", [field for field, _, _ in LIMITS])
@pytest.mark.parametrize("value", [True, 1.5, "2"], ids=["boolean", "fractional", "text"])
@pytest.mark.pr204_requirements("PR204-DOM-03", "PR204-PROV-02")
def test_noninteger_limits_reject_canonically_before_admission(
    field: str, value: object, pr204_trace: FactRecorder
) -> None:
    # Removing integral-type validation must fail even when the value lies in range.
    error, admission, repository, provider = _admit(field, value, pr204_trace)
    assert isinstance(error, ResearchBaseError), (
        f"{field} accepted {type(value).__name__} or leaked a noncanonical error: {error!r}"
    )
    assert error.code is ErrorCode.VALIDATION_ERROR
    assert admission is None
    assert repository.executions == {} and repository.receipts == {}
    assert repository.events == [] and repository.attempt_rows == {}
    assert provider.calls == []


@pytest.mark.parametrize(
    ("field", "value"),
    [(field, boundary) for field, lower, upper in LIMITS for boundary in (lower, upper)],
    ids=[f"{field}-{bound}" for field, _, _ in LIMITS for bound in ("lower", "upper")],
)
@pytest.mark.pr204_requirements("PR204-DOM-03", "PR204-PROV-02")
def test_integer_limit_boundaries_admit_without_dispatch(
    field: str, value: int, pr204_trace: FactRecorder
) -> None:
    error, admission, repository, provider = _admit(field, value, pr204_trace)
    assert error is None and admission is not None
    execution = next(iter(repository.executions.values()))
    assert execution.status.value == "PLANNED" and execution.row_version == 1
    assert execution.execution_context[field] == value
    assert type(execution.execution_context[field]) is int
    assert len(repository.receipts) == 1
    assert [event["kind"] for event in repository.events] == ["CREATED"]
    assert repository.attempt_rows == {} and provider.calls == []


@pytest.mark.parametrize(
    ("field", "value"),
    [(field, invalid) for field, _, upper in LIMITS for invalid in (0, upper + 1)],
    ids=[f"{field}-{bound}" for field, _, _ in LIMITS for bound in ("below", "above")],
)
@pytest.mark.pr204_requirements("PR204-DOM-03", "PR204-PROV-02")
def test_out_of_range_integers_reject_without_admission(
    field: str, value: int, pr204_trace: FactRecorder
) -> None:
    error, admission, repository, provider = _admit(field, value, pr204_trace)
    assert isinstance(error, ResearchBaseError)
    assert error.code is ErrorCode.VALIDATION_ERROR and admission is None
    assert repository.executions == {} and repository.receipts == {}
    assert repository.events == [] and repository.attempt_rows == {}
    assert provider.calls == []


@pytest.mark.parametrize("field", [field for field, _, _ in LIMITS])
@pytest.mark.parametrize("value", [True, 1.5, "2"], ids=["boolean", "fractional", "text"])
@pytest.mark.pr204_requirements("PR204-DOM-03", "PR204-PROV-02")
def test_invalid_integer_types_reject_before_opening_any_uow(
    field: str, value: object, pr204_trace: FactRecorder
) -> None:
    opened = []

    def forbidden_factory():
        opened.append("UOW_OPENED")
        raise AssertionError("invalid admission input opened a transaction")

    provider = FakeSearchCapability()
    service = LiteratureSearchExecutionService(
        forbidden_factory, provider, allow_unverified_principal=True
    )
    command = replace(
        CreateLiteratureSearchExecution(
            uuid4(), uuid4(), uuid4(), "test", uuid4(), "fake", "1", ("query",)
        ),
        **{field: value},
    )
    with pytest.raises(ResearchBaseError) as caught:
        service.create(command)
    pr204_trace.record(
        storage_kind="no_uow_opened",
        field=field,
        supplied_type=type(value).__name__,
        error_code=caught.value.code.value,
        uow_open_attempts=len(opened),
        provider_calls=len(provider.calls),
    )
    assert caught.value.code is ErrorCode.VALIDATION_ERROR
    assert opened == [] and provider.calls == []
