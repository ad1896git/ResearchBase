from __future__ import annotations

from typing import Any, cast

import pytest
from sqlalchemy.exc import DBAPIError

from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.literature_search_execution_uow import (
    literature_search_execution_uow_factory,
    normalize_literature_search_execution_error,
)
from researchbase.persistence.uow import SqlAlchemyUnitOfWork


def test_pr204_normalizes_deadlock_without_changing_global_policy() -> None:
    class DeadlockError(Exception):
        sqlstate = "40P01"

    error = DBAPIError("statement", {}, DeadlockError())
    normalized = normalize_literature_search_execution_error(error)
    assert normalized is not None
    assert normalized.code is ErrorCode.CONCURRENT_MODIFICATION


def test_existing_error_normalization_is_not_reimplemented() -> None:
    assert normalize_literature_search_execution_error(ValueError("unexpected")) is None
    assert ErrorCode.CONCURRENT_MODIFICATION.value == "CONCURRENT_MODIFICATION"


def test_pr204_normalizes_invalidated_connection_as_ambiguous_phase_commit() -> None:
    error = DBAPIError("commit", {}, OSError("connection lost"), connection_invalidated=True)

    normalized = normalize_literature_search_execution_error(error)

    assert normalized is not None
    assert normalized.code is ErrorCode.CONCURRENT_MODIFICATION


def test_scoped_uow_factory_normalizes_40p01_without_changing_default_uow() -> None:
    class DeadlockError(Exception):
        sqlstate = "40P01"

    class Session:
        def begin(self):
            return None

        def commit(self):
            raise DBAPIError("commit", {}, DeadlockError())

        def rollback(self):
            return None

        def close(self):
            return None

    scoped = literature_search_execution_uow_factory(cast(Any, Session))
    with pytest.raises(ResearchBaseError) as scoped_error:
        with scoped() as uow:
            uow.commit()
    assert getattr(scoped_error.value, "code", None) is ErrorCode.CONCURRENT_MODIFICATION

    historical = SqlAlchemyUnitOfWork(cast(Any, Session))
    with pytest.raises(DBAPIError):
        with historical as uow:
            uow.commit()


def test_scoped_uow_normalizes_40p01_raised_by_transaction_body() -> None:
    class DeadlockError(Exception):
        sqlstate = "40P01"

    class Session:
        def begin(self):
            return None

        def rollback(self):
            return None

        def close(self):
            return None

    scoped = literature_search_execution_uow_factory(cast(Any, Session))
    with pytest.raises(ResearchBaseError) as caught:
        with scoped():
            raise DBAPIError("body", {}, DeadlockError())

    assert caught.value.code is ErrorCode.CONCURRENT_MODIFICATION
    assert isinstance(caught.value.__cause__, DBAPIError)


def test_scoped_uow_normalizes_lost_commit_ack_without_global_policy_change() -> None:
    class Session:
        def begin(self):
            return None

        def commit(self):
            raise DBAPIError("commit", {}, OSError("connection lost"), connection_invalidated=True)

        def rollback(self):
            return None

        def close(self):
            return None

    scoped = literature_search_execution_uow_factory(cast(Any, Session))
    with pytest.raises(ResearchBaseError) as scoped_error:
        with scoped() as uow:
            uow.commit()
    assert scoped_error.value.code is ErrorCode.CONCURRENT_MODIFICATION
    assert isinstance(scoped_error.value.__cause__, DBAPIError)

    historical = SqlAlchemyUnitOfWork(cast(Any, Session))
    with pytest.raises(DBAPIError):
        with historical as uow:
            uow.commit()


def test_scoped_uow_closes_session_when_rollback_fails_after_connection_loss() -> None:
    state = {"closed": False}

    class Session:
        def begin(self):
            return None

        def rollback(self):
            raise DBAPIError("rollback", {}, OSError("connection lost"), connection_invalidated=True)

        def close(self):
            state["closed"] = True

    scoped = literature_search_execution_uow_factory(cast(Any, Session))
    error = DBAPIError("statement", {}, OSError("connection lost"), connection_invalidated=True)
    with pytest.raises(ResearchBaseError) as caught:
        with scoped():
            raise error

    assert caught.value.code is ErrorCode.CONCURRENT_MODIFICATION
    assert caught.value.__cause__ is error
    assert state["closed"]
