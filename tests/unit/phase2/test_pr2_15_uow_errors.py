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
