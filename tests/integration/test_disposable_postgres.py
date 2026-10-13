"""Live fail-closed preflight and failure cleanup for disposable test databases."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from tests.disposable_postgres import admin_url, disposable_database

pytestmark = pytest.mark.integration


def test_database_is_dropped_after_setup_failure():
    name = None
    with pytest.raises(RuntimeError, match="simulated setup failure"):
        with disposable_database("researchbase_pr210_test_") as url:
            name = make_url(url).database
            raise RuntimeError("simulated setup failure")
    assert name is not None
    engine = create_engine(admin_url())
    try:
        with engine.connect() as connection:
            assert not connection.execute(
                text("SELECT EXISTS(SELECT 1 FROM pg_database WHERE datname=:name)"),
                {"name": name},
            ).scalar_one()
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "variable",
    [
        "RB_TEST_ADMIN_USER",
        "RB_TEST_ADMIN_PORT",
        "RB_TEST_ADMIN_DATA_DIRECTORY",
        "RB_TEST_ADMIN_SYSTEM_ID",
    ],
)
def test_optional_identity_mismatch_fails_before_database_creation(variable, monkeypatch):
    monkeypatch.setenv(variable, "deliberately-wrong-identity")
    with pytest.raises(AssertionError, match=f"{variable} identity mismatch"):
        with disposable_database("researchbase_pr210_test_"):
            pytest.fail("identity mismatch allowed database creation")
