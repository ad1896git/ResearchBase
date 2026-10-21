"""Safety and portable URL selection for the disposable PostgreSQL test helper."""

from __future__ import annotations

import pytest
from alembic.config import Config
from sqlalchemy.engine import make_url

from tests.disposable_postgres import admin_url, disposable_database

PRIMARY = "RB_TEST_ADMIN_URL"
ALIASES = ("RB_PR210_TEST_ADMIN_URL", "RB_PR211_R2_TEST_ADMIN_URL")
LOCAL = "postgresql+psycopg://test_admin:password@localhost:5432/postgres"


@pytest.fixture(autouse=True)
def clear_selectors(monkeypatch):
    for variable in (PRIMARY, *ALIASES):
        monkeypatch.delenv(variable, raising=False)


def test_missing_selector_fails():
    with pytest.raises(pytest.fail.Exception, match="Set RB_TEST_ADMIN_URL explicitly"):
        admin_url(*ALIASES)


@pytest.mark.parametrize(
    "value",
    [
        "",
        "invalid",
        "sqlite:///postgres",
        LOCAL.replace("/postgres", "/researchbase"),
        LOCAL.replace("localhost", "production.example.com"),
        LOCAL + "?service=production",
        LOCAL + "?dbname=researchbase",
        LOCAL + "?hostaddr=192.0.2.1",
        LOCAL + "?host=localhost&host=production.example.com",
    ],
)
def test_unsafe_selector_fails(value, monkeypatch):
    monkeypatch.setenv(PRIMARY, value)
    with pytest.raises(pytest.fail.Exception):
        admin_url(*ALIASES)


@pytest.mark.parametrize("alias", ALIASES)
def test_legacy_alias_is_an_explicit_selector(alias, monkeypatch):
    monkeypatch.setenv(alias, LOCAL)
    assert admin_url(*ALIASES).render_as_string(hide_password=False) == LOCAL


def test_primary_takes_precedence_and_empty_primary_fails(monkeypatch):
    monkeypatch.setenv(ALIASES[0], LOCAL)
    monkeypatch.setenv(PRIMARY, LOCAL.replace("5432", "5433"))
    assert admin_url(*ALIASES).port == 5433
    monkeypatch.setenv(PRIMARY, "")
    with pytest.raises(pytest.fail.Exception):
        admin_url(*ALIASES)


def test_socket_and_escaped_credentials_survive_database_replacement(monkeypatch):
    monkeypatch.setenv(PRIMARY, "postgresql+psycopg://admin:p%40ss@/postgres?host=%2Ftmp&port=5433")
    url = admin_url().set(database="researchbase_pr210_test_example")
    assert url.password == "p@ss"
    assert dict(url.query) == {"host": "/tmp", "port": "5433"}
    assert url.database == "researchbase_pr210_test_example"
    rendered = url.render_as_string(hide_password=False)
    assert "%40" in rendered and "%2F" in rendered
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", rendered.replace("%", "%%"))
    configured = config.get_main_option("sqlalchemy.url")
    assert configured is not None
    assert configured == rendered
    assert make_url(configured) == url


def test_unknown_prefix_is_rejected_before_connecting():
    with pytest.raises(ValueError, match="unapproved disposable database prefix"):
        with disposable_database("researchbase_"):
            pytest.fail("unapproved database was created")
