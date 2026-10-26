"""Real PostgreSQL failures, passed through the intent UoW's normalization."""

import time
from concurrent.futures import ThreadPoolExecutor
from typing import cast

import pytest
from psycopg import Error as PostgresError
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker
from tests.disposable_postgres import disposable_database

from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.uow import SqlAlchemyUnitOfWork


def _serialization_failure(engine):
    with engine.connect().execution_options(isolation_level="REPEATABLE READ") as stale:
        stale.execute(text("SELECT * FROM intent_error_probe"))
        with engine.begin() as writer:
            writer.execute(text("UPDATE intent_error_probe SET value=value+1 WHERE id=1"))
        with pytest.raises(DBAPIError) as exc:
            stale.execute(text("UPDATE intent_error_probe SET value=value+1 WHERE id=1"))
        return exc.value


def _deadlock(engine):
    with engine.connect() as first, engine.connect() as second:
        first.execute(text("SET LOCAL statement_timeout='5s'"))
        second.execute(text("SET LOCAL statement_timeout='5s'"))
        first.execute(text("UPDATE intent_error_probe SET value=value+1 WHERE id=1"))
        second.execute(text("UPDATE intent_error_probe SET value=value+1 WHERE id=2"))
        pid = first.execute(text("SELECT pg_backend_pid()")).scalar_one()

        def contend():
            try:
                first.execute(text("UPDATE intent_error_probe SET value=value+1 WHERE id=2"))
            except DBAPIError as error:
                return error
            finally:
                first.rollback()
            return None

        with ThreadPoolExecutor(1) as pool:
            future = pool.submit(contend)
            victim = None
            try:
                deadline = time.monotonic() + 3
                with engine.connect() as observer:
                    while time.monotonic() < deadline:
                        if observer.execute(
                            text("SELECT cardinality(pg_blocking_pids(:pid)) > 0"), {"pid": pid}
                        ).scalar_one():
                            break
                        time.sleep(0.01)
                    else:
                        raise AssertionError("first deadlock edge was not observed")
                try:
                    second.execute(text("UPDATE intent_error_probe SET value=value+1 WHERE id=1"))
                except DBAPIError as error:
                    victim = error
            finally:
                second.rollback()
            other = future.result(timeout=6)
        # PostgreSQL may choose either transaction as the deadlock victim.
        errors = [error for error in (victim, other) if error is not None]
        assert len(errors) == 1
        return errors[0]


def _timeout(engine, sqlstate):
    with engine.connect() as holder, engine.connect() as waiter:
        holder.execute(text("UPDATE intent_error_probe SET value=value+1 WHERE id=1"))
        waiter.execute(text("SET LOCAL statement_timeout='2s'"))
        if sqlstate == "55P03":
            waiter.execute(text("SET LOCAL lock_timeout='50ms'"))
            sql = "UPDATE intent_error_probe SET value=value+1 WHERE id=1"
        else:
            waiter.execute(text("SET LOCAL statement_timeout='50ms'"))
            sql = "SELECT pg_sleep(2)"
        with pytest.raises(DBAPIError) as exc:
            waiter.execute(text(sql))
        return exc.value


@pytest.mark.parametrize("sqlstate", ["40001", "40P01", "55P03", "57014"])
def test_real_postgresql_failure_normalizes_intent_retryability(sqlstate):
    with disposable_database("researchbase_pr212_test_") as url:
        engine = create_engine(url)
        try:
            with engine.begin() as conn:
                assert int(conn.execute(text("SHOW server_version_num")).scalar_one()) >= 180000
                conn.execute(
                    text("CREATE TABLE intent_error_probe (id integer PRIMARY KEY, value integer)")
                )
                conn.execute(text("INSERT INTO intent_error_probe VALUES (1,0),(2,0)"))
            if sqlstate == "40001":
                error = _serialization_failure(engine)
            elif sqlstate == "40P01":
                error = _deadlock(engine)
            else:
                error = _timeout(engine, sqlstate)
            assert cast(PostgresError, error.orig).sqlstate == sqlstate
            sessions = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
            with pytest.raises(ResearchBaseError) as exc:
                with SqlAlchemyUnitOfWork(sessions) as uow:
                    uow.begin_execution_intent()
                    # Feed the actual driver exception through rollback/translation.
                    raise error
            assert exc.value.code == ErrorCode.CONCURRENT_MODIFICATION
            assert exc.value.details == {"retryable_pr302": sqlstate in {"40001", "40P01"}}
            assert "intent_error_probe" not in str(exc.value)
        finally:
            engine.dispose()
