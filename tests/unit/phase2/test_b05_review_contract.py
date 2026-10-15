"""Closed B05 review inputs are rejected before opening a transaction."""

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

import pytest

from researchbase.application.internal_review import InternalReviewService, ReviewIssueRequest
from researchbase.domain.phase2_identity import VerifiedPrincipal
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


def inputs() -> dict[str, Any]:
    return dict(
        principal=VerifiedPrincipal(
            uuid4(), "deployment", "OS_UID", "reviewer", "credential", datetime.now(UTC)
        ),
        project=uuid4(),
        target_kind="MANUSCRIPT_VERSION",
        target_id=uuid4(),
        review_type="SCIENTIFIC",
        recommendation="ACCEPT",
        summary="Review",
        issues=(),
        request=uuid4(),
    )


def service():
    def no_sql():
        raise AssertionError("invalid input reached SQL")

    return InternalReviewService(no_sql, None, None)


@pytest.mark.parametrize(
    "field,value",
    [
        ("project", "uuid"),
        ("target_id", "uuid"),
        ("request", "uuid"),
        ("target_kind", "LATEST"),
        ("target_kind", []),
        ("review_type", "OTHER"),
        ("review_type", []),
        ("recommendation", "READY"),
        ("recommendation", 1),
        ("summary", " "),
        ("summary", "x" * 16001),
        ("summary", "\ud800"),
        ("summary", b"text"),
        ("issues", []),
        ("issues", (object(),)),
        ("issues", tuple(ReviewIssueRequest("MINOR", "OTHER", "x") for _ in range(101))),
        ("issues", (ReviewIssueRequest("minor", "OTHER", "x"),)),
        ("issues", (ReviewIssueRequest("MINOR", "other", "x"),)),
        ("issues", (ReviewIssueRequest("MINOR", "OTHER", "\udfff"),)),
    ],
)
def test_rejects_before_sql(field, value):
    args = inputs()
    args[field] = value
    with pytest.raises(ResearchBaseError) as exc:
        service().create(**args)
    assert exc.value.code == ErrorCode.VALIDATION_ERROR


@pytest.mark.parametrize("count", [0, 100])
def test_nfc_bounds_dispatch_and_order(count, monkeypatch):
    instance = service()
    args = inputs()
    args["summary"] = "e\u0301" * 16000
    args["issues"] = tuple(ReviewIssueRequest("MINOR", "OTHER", str(i)) for i in range(count))
    seen = []

    def create(*arguments):
        seen.extend(arguments)
        return "sentinel"

    monkeypatch.setattr(instance, "_create_manuscript", create)
    assert instance.create(**args) == "sentinel"
    assert seen[5] == "é" * 16000
    assert [i.description for i in seen[6]] == [str(i) for i in range(count)]


def test_closed_issue_and_create_arguments():
    with pytest.raises(TypeError):
        cast(Any, ReviewIssueRequest)("MINOR", "OTHER", "text", status="OPEN")
    with pytest.raises(TypeError):
        cast(Any, service().create)(**inputs(), reviewer_actor_id=UUID(int=1))


@pytest.mark.parametrize(
    "state,code,retry",
    [
        ("P05R1", ErrorCode.PROVENANCE_CLOSURE_VIOLATION, False),
        ("P17E1", ErrorCode.IMMUTABLE_RECORD, False),
        ("P17E2", ErrorCode.REVIEW_TARGET_NOT_FROZEN, False),
        ("23503", ErrorCode.REFERENTIAL_INTEGRITY_ERROR, False),
        ("23514", ErrorCode.VALIDATION_ERROR, False),
        ("23502", ErrorCode.VALIDATION_ERROR, False),
        ("23505", ErrorCode.CONCURRENT_MODIFICATION, False),
        ("40001", ErrorCode.CONCURRENT_MODIFICATION, True),
        ("40P01", ErrorCode.CONCURRENT_MODIFICATION, True),
        ("55P03", ErrorCode.CONCURRENT_MODIFICATION, False),
        ("57014", ErrorCode.CONCURRENT_MODIFICATION, False),
    ],
)
def test_scoped_database_error_mapping(state, code, retry):
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork
    from tests.unit.phase2.test_pr2_15_uow_errors import _error

    uow = SqlAlchemyUnitOfWork(cast(Any, lambda: None))
    uow.enable_internal_review_error_normalization()
    mapped = uow._command_database_error(_error(state))
    assert mapped.code == code and mapped.details == {"retryable_b05": retry}
    assert "SYNTHETIC_SECRET" not in str(mapped)


@pytest.mark.parametrize("retryable,expected_attempts", [(True, 3), (False, 1)])
def test_retry_restarts_whole_uow_at_most_three_times(monkeypatch, retryable, expected_attempts):
    instance = service()
    attempts = []

    def create(*args):
        attempts.append(1)
        raise ResearchBaseError(
            ErrorCode.CONCURRENT_MODIFICATION, "bounded conflict", {"retryable_b05": retryable}
        )

    monkeypatch.setattr(instance, "_create_manuscript", create)
    with pytest.raises(ResearchBaseError):
        instance.create(**inputs())
    assert len(attempts) == expected_attempts


def test_unknown_database_failure_stays_unexpected_and_sanitized():
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork
    from tests.unit.phase2.test_pr2_15_uow_errors import _error

    uow = SqlAlchemyUnitOfWork(cast(Any, lambda: None))
    uow.enable_internal_review_error_normalization()
    with pytest.raises(RuntimeError) as exc:
        uow._command_database_error(_error("XX000"))
    assert "SYNTHETIC_SECRET" not in str(exc.value)
