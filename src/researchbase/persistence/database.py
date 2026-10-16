"""Synchronous SQLAlchemy database adapter for the bootstrap smoke gate."""

from __future__ import annotations

import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DEFAULT_DATABASE_URL = "postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase"


class Base(DeclarativeBase):
    """Base for persistence-only SQLAlchemy models."""


def database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def create_database_engine(
    url: str | None = None, *, b04_write_timeouts: bool = False, b05_write_timeouts: bool = False
) -> Engine:
    """Opt B04 write factories into the guide's bounded first SHARE wait.

    Connection options apply before BEGIN; ordinary callers retain server defaults.
    B04 exact-read factories do not need this option.
    """
    options = (
        {"options": "-c lock_timeout=10000 -c statement_timeout=30000"}
        if b04_write_timeouts or b05_write_timeouts
        else {}
    )
    return create_engine(url or database_url(), future=True, connect_args=options)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


def check_database_connection(engine: Engine) -> bool:
    with engine.connect() as connection:
        return connection.execute(text("SELECT 1")).scalar_one() == 1


def configure_revision_connection(connection) -> None:
    """Apply the B06 timeout profile before the driver's transaction begins.

    Session.connection() has a logical SQLAlchemy transaction, but psycopg has
    not sent BEGIN yet. Configure in autocommit, then restore on pool checkin;
    owning writers using the pool retain their original connection settings.
    """
    from sqlalchemy import event

    raw = connection.connection.driver_connection
    info = connection.info
    previous_autocommit = raw.autocommit
    raw.autocommit = True
    try:
        with raw.cursor() as cursor:
            cursor.execute("SHOW lock_timeout")
            lock = cursor.fetchone()[0]
            cursor.execute("SHOW statement_timeout")
            statement = cursor.fetchone()[0]
            info["b06_timeouts"] = (lock, statement)
            pool = connection.engine.pool
            if not event.contains(pool, "checkin", _restore_revision_connection):
                event.listen(pool, "checkin", _restore_revision_connection)
            cursor.execute("SET lock_timeout = '10s'")
            cursor.execute("SET statement_timeout = '30s'")
    except Exception:
        from researchbase.foundation.errors import ErrorCode, ResearchBaseError

        raise ResearchBaseError(
            ErrorCode.INVALID_STATE_TRANSITION, "revision connection configuration failed"
        ) from None
    finally:
        raw.autocommit = previous_autocommit


def _restore_revision_connection(raw, record) -> None:
    bounds = record.info.pop("b06_timeouts", None)
    if raw is None or bounds is None:
        return
    autocommit = raw.autocommit
    try:
        raw.autocommit = True
        with raw.cursor() as cursor:
            cursor.execute("SELECT set_config('lock_timeout', %s, false)", (bounds[0],))
            cursor.execute("SELECT set_config('statement_timeout', %s, false)", (bounds[1],))
    except Exception:
        # A lost connection is discarded, never returned with leaked settings.
        record.invalidate()
    finally:
        if not raw.closed:
            raw.autocommit = autocommit
