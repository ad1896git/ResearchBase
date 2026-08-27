"""Synchronous SQLAlchemy database adapter for the bootstrap smoke gate."""

from __future__ import annotations

import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

DEFAULT_DATABASE_URL = "postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase"


def database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def create_database_engine(url: str | None = None) -> Engine:
    return create_engine(url or database_url(), future=True)


def check_database_connection(engine: Engine) -> bool:
    with engine.connect() as connection:
        return connection.execute(text("SELECT 1")).scalar_one() == 1
