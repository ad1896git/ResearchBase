"""B02 driver-metadata classification and isolation across reused UoW contexts."""

import traceback
from types import SimpleNamespace
from typing import cast
from unittest.mock import Mock

import pytest
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.uow import SqlAlchemyUnitOfWork


class DriverFailure(Exception):
    def __init__(self, state: str, constraint: str | None = None) -> None:
        super().__init__("SYNTHETIC_SECRET is not public error material")
        self.sqlstate = state
        self.diag = SimpleNamespace(constraint_name=constraint)


def failure(state: str, constraint: str | None = None) -> DBAPIError:
    return DBAPIError("SELECT SYNTHETIC_SECRET", {}, DriverFailure(state, constraint), False)


@pytest.mark.parametrize("boundary", ["commit", "execute", "cleanup"])
@pytest.mark.parametrize(
    "state,constraint,code,details",
    [
        ("P22B1", None, ErrorCode.IMMUTABLE_RECORD, None),
        ("P22B2", None, ErrorCode.PROVENANCE_CLOSURE_VIOLATION, None),
        ("23505", "uq_b02_q_candidate", ErrorCode.DUPLICATE_CONTENT, None),
        ("23505", "uq_b02_h_candidate", ErrorCode.DUPLICATE_CONTENT, None),
        ("23505", "pk_b02_capture", ErrorCode.CONCURRENT_MODIFICATION, {"reread_b02": True}),
        ("23505", "pk_b02_q", ErrorCode.CONCURRENT_MODIFICATION, {"reread_b02": True}),
        ("23505", "pk_b02_h", ErrorCode.CONCURRENT_MODIFICATION, {"reread_b02": True}),
        ("40001", None, ErrorCode.CONCURRENT_MODIFICATION, {"retryable_b02": True}),
        ("40P01", None, ErrorCode.CONCURRENT_MODIFICATION, {"retryable_b02": True}),
        ("55P03", None, ErrorCode.CONCURRENT_MODIFICATION, None),
        ("57014", None, ErrorCode.CONCURRENT_MODIFICATION, None),
        ("23503", "fk_b02_q_version", ErrorCode.REFERENTIAL_INTEGRITY_ERROR, None),
    ],
)
def test_b02_metadata_mapping_at_each_transaction_boundary(
    boundary, state, constraint, code, details
):
    session = Mock(spec=Session)
    uow = SqlAlchemyUnitOfWork(lambda: cast(Session, session))
    error = failure(state, constraint)
    with pytest.raises(ResearchBaseError) as caught:
        with uow:
            uow.begin_strategy(read_only=False)
            if boundary == "commit":
                session.commit.side_effect = error
                uow.commit()
            elif boundary == "execute":
                raise error
            else:
                session.rollback.side_effect = error
    assert caught.value.code is code
    assert caught.value.details == details
    assert "SYNTHETIC_SECRET" not in "".join(traceback.format_exception(caught.value))
    assert caught.value.__cause__ is None
    session.rollback.assert_called_once()
    session.close.assert_called_once()
    assert uow._session is None


def configure(uow: SqlAlchemyUnitOfWork, flow: str) -> None:
    if flow == "b02":
        uow.begin_strategy(read_only=False)
    elif flow == "b01":
        uow.begin_resolution(read_only=False)
    elif flow == "manuscript":
        uow.enable_manuscript_freeze_error_normalization()


@pytest.mark.parametrize("previous", ["b02", "b01", "manuscript"])
@pytest.mark.parametrize("following", ["ordinary", "b02", "b01", "manuscript"])
def test_reused_uow_context_resets_command_normalization_flags(previous, following):
    first, second = Mock(spec=Session), Mock(spec=Session)
    sessions = iter((first, second))
    uow = SqlAlchemyUnitOfWork(lambda: cast(Session, next(sessions)))
    with uow:
        configure(uow, previous)
    with pytest.raises(ResearchBaseError) as caught:
        with uow:
            assert uow._session is second
            assert not uow._b02_error_normalization
            assert not uow._b01_error_normalization
            assert not uow._manuscript_freeze_error_normalization
            assert not uow._decision_error_normalization
            configure(uow, following)
            raise failure("40001")
    expected = {
        "ordinary": None,
        "b02": {"retryable_b02": True},
        "b01": {"retryable_b01": True},
        "manuscript": {"retryable_b04": True},
    }
    assert caught.value.code is ErrorCode.CONCURRENT_MODIFICATION
    assert caught.value.details == expected[following]
    first.close.assert_called_once()
    second.close.assert_called_once()
    assert uow._session is None


@pytest.mark.parametrize("constraint", [None, "unrelated_unique_constraint"])
def test_b02_unrecognized_unique_does_not_become_candidate_or_request_race(constraint):
    session = Mock(spec=Session)
    with pytest.raises(RuntimeError, match="strategy transaction failed") as caught:
        with SqlAlchemyUnitOfWork(lambda: cast(Session, session)) as uow:
            uow.begin_strategy(read_only=False)
            raise failure("23505", constraint)
    assert "SYNTHETIC_SECRET" not in "".join(traceback.format_exception(caught.value))
    session.rollback.assert_called_once()
    session.close.assert_called_once()
