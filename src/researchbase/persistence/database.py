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
