"""PR2-15-only database error boundary; no scientific writes or credentials."""

import traceback
from typing import Any, cast
from unittest.mock import Mock

import pytest
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.uow import SqlAlchemyUnitOfWork


class _DriverFailure(Exception):
    def __init__(self, sqlstate):
        super().__init__("SYNTHETIC_SECRET password=do-not-disclose")
        self.sqlstate = sqlstate


def _error(sqlstate):
    return DBAPIError("SELECT SYNTHETIC_SECRET", {}, _DriverFailure(sqlstate), False)


@pytest.mark.parametrize(
    "sqlstate,expected",
    [
        ("P17F1", ErrorCode.IMMUTABLE_RECORD),
        ("P17F2", ErrorCode.PROVENANCE_CLOSURE_VIOLATION),
        ("P17F3", ErrorCode.IDEMPOTENCY_CONFLICT),
        ("40001", ErrorCode.CONCURRENT_MODIFICATION),
        ("40P01", ErrorCode.CONCURRENT_MODIFICATION),
        ("XX000", ErrorCode.INVALID_STATE_TRANSITION),
    ],
)
@pytest.mark.parametrize("boundary", ["commit", "execute", "cleanup"])
def test_decision_database_failures_are_sanitized(sqlstate, expected, boundary):
    session = Mock()
    uow = SqlAlchemyUnitOfWork(lambda: cast(Session, session))
    uow._session = cast(Session, session)
    uow.enable_decision_error_normalization()
    failure = _error(sqlstate)
    with pytest.raises(ResearchBaseError) as caught:
        if boundary == "commit":
            session.commit.side_effect = failure
            try:
                uow.commit()
            except BaseException as exc:
                uow.__exit__(type(exc), exc, exc.__traceback__)
                raise
        elif boundary == "execute":
            uow.__exit__(type(failure), failure, failure.__traceback__)
        else:
            session.rollback.side_effect = failure
            uow.__exit__(None, None, None)
    assert caught.value.code is expected
    assert "SYNTHETIC_SECRET" not in "".join(traceback.format_exception(caught.value))
    assert caught.value.__cause__ is None
    session.close.assert_called_once()
    assert uow._session is None


def test_decision_boundary_does_not_swallow_unexpected_non_database_failure():
    session = Mock()
    uow = SqlAlchemyUnitOfWork(lambda: cast(Session, session))
    uow._session = cast(Session, session)
    uow.enable_decision_error_normalization()
    failure = RuntimeError("unexpected internal failure")
    uow.__exit__(type(failure), failure, None)
    session.rollback.assert_called_once()
    session.close.assert_called_once()


@pytest.mark.parametrize("sqlstate", ["P17R1", "55P03", "57014"])
def test_revision_unavailable_and_timeouts_are_sanitized(sqlstate):
    from researchbase.persistence.uow import _decision_database_error

    error = _decision_database_error(_error(sqlstate))
    assert error.code == ErrorCode.INVALID_STATE_TRANSITION
    assert "SYNTHETIC_SECRET" not in error.message


def test_revision_predecessor_unique_race_normalizes_after_rollback():
    from types import SimpleNamespace

    failure = _error("23505")
    cast(Any, failure.orig).diag = SimpleNamespace(constraint_name="uq_revision_action_predecessor")
    session = Mock()
    uow = SqlAlchemyUnitOfWork(lambda: cast(Session, session))
    uow._session = cast(Session, session)
    uow.enable_decision_error_normalization()
    with pytest.raises(ResearchBaseError) as caught:
        uow.__exit__(type(failure), failure, None)
    session.rollback.assert_called_once()
    assert caught.value.code == ErrorCode.INVALID_STATE_TRANSITION
    assert "SYNTHETIC_SECRET" not in "".join(traceback.format_exception(caught.value))


@pytest.mark.parametrize(
    "constraint,expected",
    [
        ("uq_b07_decision_concern", ErrorCode.IDEMPOTENCY_CONFLICT),
        ("pk_b07_action_re_review", ErrorCode.IDEMPOTENCY_CONFLICT),
    ],
)
def test_b07_named_unique_errors_are_sanitized(constraint, expected):
    from types import SimpleNamespace

    from researchbase.persistence.uow import _decision_database_error

    failure = _error("23505")
    cast(Any, failure.orig).diag = SimpleNamespace(constraint_name=constraint)
    error = _decision_database_error(failure)
    assert error.code == expected
    assert "SYNTHETIC_SECRET" not in error.message


def test_b07_missing_concrete_foreign_key_uses_existing_mapping():
    from researchbase.persistence.uow import _decision_database_error

    assert _decision_database_error(_error("23503")).code == ErrorCode.REFERENTIAL_INTEGRITY_ERROR


@pytest.mark.parametrize("constraint", ["uq_b08_issue_terminal", "review_issue_events_pkey"])
def test_b08_unique_requires_rollback_reload_and_comparison(constraint):
    from types import SimpleNamespace

    from researchbase.persistence.uow import _decision_database_error

    failure = _error("23505")
    cast(Any, failure.orig).diag = SimpleNamespace(constraint_name=constraint)
    result = _decision_database_error(failure)
    assert result.code == ErrorCode.IDEMPOTENCY_CONFLICT
    assert result.message == "reload issue disposition"
    assert not (result.details or {}).get("retryable_b08")


@pytest.mark.parametrize(
    "state,retry",
    [
        ("40001", True),
        ("40P01", True),
        ("55P03", False),
        ("57014", False),
        ("23503", False),
        ("XX000", False),
    ],
)
def test_b08_only_serialization_and_deadlock_are_retryable(state, retry):
    from researchbase.persistence.uow import _issue_disposition_database_error

    result = _issue_disposition_database_error(_error(state))
    assert bool((result.details or {}).get("retryable_b08")) == retry


@pytest.mark.parametrize("retryable,expected_attempts", [(True, 3), (False, 1)])
def test_b08_restarts_only_retryable_failures_exactly_three_total_attempts(
    monkeypatch, retryable, expected_attempts
):
    from datetime import UTC, datetime
    from uuid import uuid4

    from researchbase.application.internal_review import (
        InternalReviewService,
        RecordIssueDispositionCommand,
    )
    from researchbase.domain.phase2_identity import VerifiedPrincipal

    principal = VerifiedPrincipal(uuid4(), "test", "OS_UID", "1", "credential", datetime.now(UTC))
    service = object.__new__(InternalReviewService)
    attempts = []

    def fail(*args, **kwargs):
        attempts.append(1)
        raise ResearchBaseError(
            ErrorCode.CONCURRENT_MODIFICATION, "sanitized", {"retryable_b08": retryable}
        )

    monkeypatch.setattr(service, "_record_disposition_once", fail)
    cmd = RecordIssueDispositionCommand(
        uuid4(), uuid4(), uuid4(), "ADDRESSED", uuid4(), uuid4(), "Attested"
    )
    with pytest.raises(ResearchBaseError) as caught:
        service.record_issue_disposition(principal, cmd)
    assert caught.value.code == ErrorCode.CONCURRENT_MODIFICATION
    assert len(attempts) == expected_attempts


@pytest.mark.parametrize("state", ["40001", "40P01"])
def test_b08_retry_metadata_does_not_change_other_decision_boundaries(state):
    from researchbase.persistence.uow import _decision_database_error

    error = _decision_database_error(_error(state))
    assert error.code == ErrorCode.CONCURRENT_MODIFICATION
    assert error.details is None


@pytest.mark.parametrize("boundary", ["commit", "execute"])
def test_issue_disposition_retry_normalization_requires_explicit_uow_opt_in(boundary):
    session = Mock()
    uow = SqlAlchemyUnitOfWork(lambda: cast(Session, session))
    uow._session = cast(Session, session)
    uow.enable_issue_disposition_error_normalization()
    failure = _error("40P01")
    with pytest.raises(ResearchBaseError) as caught:
        if boundary == "commit":
            session.commit.side_effect = failure
            try:
                uow.commit()
            except BaseException as exc:
                uow.__exit__(type(exc), exc, exc.__traceback__)
                raise
        else:
            uow.__exit__(type(failure), failure, failure.__traceback__)
    assert caught.value.details == {"retryable_b08": True}
    session.rollback.assert_called_once()
