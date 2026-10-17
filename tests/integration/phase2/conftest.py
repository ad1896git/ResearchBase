from __future__ import annotations

import os
from collections.abc import Iterator
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

# Expose the shared fixture throughout Phase 2 regardless of module/plugin collection order.
from tests.integration.phase2.test_m3_evidence import m3 as m3


@pytest.fixture
def phase2_database_url(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """Give each PostgreSQL integration test an isolated disposable database."""

    base_url = make_url(os.environ["DATABASE_URL"])
    database_name = f"researchbase_pr2_test_{uuid4().hex}"
    maintenance_url = base_url.set(database="postgres")
    admin_engine = create_engine(maintenance_url)
    quoted_name = admin_engine.dialect.identifier_preparer.quote(database_name)
    try:
        with admin_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            connection.execute(text(f"CREATE DATABASE {quoted_name}"))
        test_url = base_url.set(database=database_name)
        rendered_url = test_url.render_as_string(hide_password=False)
        # Config.set_main_option() is used by these tests. Keep a Unix socket
        # host as literal slashes so ConfigParser does not reject SQLAlchemy's
        # otherwise equivalent percent-escaped rendering before migration.
        socket_host = test_url.query.get("host")
        if isinstance(socket_host, str) and socket_host.startswith("/"):
            rendered_url = rendered_url.replace(
                f"host={socket_host.replace('/', '%2F')}", f"host={socket_host}"
            )
        monkeypatch.setenv("DATABASE_URL", rendered_url)
        yield rendered_url
    finally:
        with admin_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            connection.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :database_name AND pid <> pg_backend_pid()"
                ),
                {"database_name": database_name},
            )
            connection.execute(text(f"DROP DATABASE IF EXISTS {quoted_name}"))
        admin_engine.dispose()
