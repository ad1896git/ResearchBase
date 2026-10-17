"""Explicitly selected local admin cluster; only random test databases are mutated.

RB_TEST_ADMIN_URL is an opt-in to CREATE/DROP disposable databases on that cluster.
Legacy selectors remain aliases. Optional RB_TEST_ADMIN_{USER,PORT,DATA_DIRECTORY,
SYSTEM_ID} values pin the corresponding server identity when desired.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError

_PREFIXES = {
    "researchbase_pr210_test_",
    "researchbase_pr211_r2_test_",
    "researchbase_pr212_test_",
}


def admin_url(*aliases: str) -> URL:
    """Require explicit opt-in and reject application databases and remote hosts."""
    selector = "RB_TEST_ADMIN_URL"
    if selector not in os.environ:
        selector = next((alias for alias in aliases if alias in os.environ), selector)
    value = os.environ.get(selector)
    if not value:
        pytest.fail("Set RB_TEST_ADMIN_URL explicitly to a disposable local PostgreSQL admin URL")
    try:
        url = make_url(value)
    except (ArgumentError, ValueError, TypeError) as error:
        pytest.fail(f"{selector} is not a valid PostgreSQL URL: {type(error).__name__}")
    host = url.query.get("host", url.host)
    if (
        url.drivername != "postgresql+psycopg"
        or url.database != "postgres"
        or not url.username
        or not isinstance(host, str)
        or not (host in {"localhost", "127.0.0.1", "::1"} or host.startswith("/"))
        or set(url.query) - {"host", "port", "sslmode", "connect_timeout", "application_name"}
    ):
        pytest.fail(f"{selector} must name a local PostgreSQL postgres admin database")
    return url


@contextmanager
def disposable_database(prefix: str, *aliases: str) -> Iterator[str]:
    """Create only an absent random database and drop it even if setup/test fails."""
    if prefix not in _PREFIXES:
        raise ValueError("unapproved disposable database prefix")
    url = admin_url(*aliases)
    admin = create_engine(url)
    try:
        with admin.connect() as connection:
            identity = connection.execute(
                text("""SELECT current_user,current_database(),
                current_setting('port'),current_setting('data_directory'),
                (SELECT system_identifier FROM pg_control_system())""")
            ).one()
        assert str(identity[0]) == url.username
        assert str(identity[1]) == "postgres"
        for variable, actual in zip(
            (
                "RB_TEST_ADMIN_USER",
                "RB_TEST_ADMIN_PORT",
                "RB_TEST_ADMIN_DATA_DIRECTORY",
                "RB_TEST_ADMIN_SYSTEM_ID",
            ),
            (identity[0], identity[2], identity[3], identity[4]),
            strict=True,
        ):
            if variable in os.environ:
                assert str(actual) == os.environ[variable], f"{variable} identity mismatch"
        print(f"DISPOSABLE_PG_PREFLIGHT: port={identity[2]} system_id={identity[4]}")
        name = f"{prefix}{uuid4().hex}"
        with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            assert not connection.execute(
                text("SELECT EXISTS(SELECT 1 FROM pg_database WHERE datname=:name)"),
                {"name": name},
            ).scalar_one()
            connection.execute(text(f'CREATE DATABASE "{name}"'))
        try:
            print(f"DISPOSABLE_CREATED: {name}")
            yield url.set(database=name).render_as_string(hide_password=False)
        finally:
            with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
                connection.execute(
                    text("""SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity WHERE datname=:name AND pid<>pg_backend_pid()"""),
                    {"name": name},
                )
                connection.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))
            print(f"DISPOSABLE_DROPPED: {name}")
    finally:
        admin.dispose()
