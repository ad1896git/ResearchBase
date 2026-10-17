"""Adapter error translation and bounded Application retries; no database I/O."""

from typing import cast
from unittest.mock import Mock

import pytest
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from researchbase.application.discussion import DiscussionService
from researchbase.application.scientific_conclusion import ScientificConclusionService
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.uow import SqlAlchemyUnitOfWork


def _failure(state):
    class DriverFailure(RuntimeError):
        sqlstate = state

    original = DriverFailure("synthetic driver failure")
    return DBAPIError("statement", {}, original)


@pytest.mark.parametrize("service", ["discussion", "conclusion"])
@pytest.mark.parametrize("state", ["40001", "40P01", "XX000"])
@pytest.mark.parametrize("boundary", ["execute", "commit", "begin"])
@pytest.mark.parametrize("failures", [1, 3])
def test_driver_failures_cross_adapter_before_application_retry(service, state, boundary, failures):
    sessions = []
    failure = _failure(state)

    def operation():
        session = Mock()
        sessions.append(session)
        if len(sessions) <= failures:
            if boundary == "commit":
                session.commit.side_effect = failure
            elif boundary == "begin":
                session.connection.side_effect = failure
        with SqlAlchemyUnitOfWork(lambda: cast(Session, session)) as uow:
            uow.enable_serializable_retry_normalization()
            uow.begin_serializable()
            if len(sessions) <= failures and boundary == "execute":
                raise failure
            uow.commit()
        return "committed"

    def retry():
        if service == "discussion":
            return DiscussionService._run(cast(DiscussionService, None), operation)
        return ScientificConclusionService._retry(operation)

    if state == "XX000":
        with pytest.raises(DBAPIError) as caught:
            retry()
        assert caught.value is failure
        assert len(sessions) == 1
    elif failures == 3:
        with pytest.raises(ResearchBaseError) as caught:
            retry()
        assert caught.value.code is ErrorCode.CONCURRENT_MODIFICATION
        assert caught.value.__cause__ is failure
        assert len(sessions) == 3
    else:
        assert retry() == "committed"
        assert len(sessions) == 2
    for session in sessions:
        session.close.assert_called_once()
    for session in sessions[:failures]:
        session.rollback.assert_called_once()


@pytest.mark.parametrize("service", ["discussion", "conclusion"])
def test_nonconcurrent_application_error_is_not_retried(service):
    error = ResearchBaseError(ErrorCode.FORBIDDEN, "denied")
    operation = Mock(side_effect=error)
    with pytest.raises(ResearchBaseError) as caught:
        if service == "discussion":
            DiscussionService._run(cast(DiscussionService, None), operation)
        else:
            ScientificConclusionService._retry(operation)
    assert caught.value is error
    operation.assert_called_once()


@pytest.mark.parametrize("boundary", ["execute", "commit", "begin"])
def test_default_serializable_uow_preserves_raw_deadlock(boundary):
    session = Mock()
    failure = _failure("40P01")
    if boundary == "commit":
        session.commit.side_effect = failure
    elif boundary == "begin":
        session.connection.side_effect = failure
    with pytest.raises(DBAPIError) as caught:
        with SqlAlchemyUnitOfWork(lambda: cast(Session, session)) as uow:
            uow.begin_serializable()
            if boundary == "execute":
                raise failure
            uow.commit()
    assert caught.value is failure
    session.rollback.assert_called_once()
    session.close.assert_called_once()
