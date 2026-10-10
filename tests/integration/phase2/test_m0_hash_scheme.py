"""Fixed provenance schemes: real commit rejection and atomic migration preflight."""

from unittest.mock import patch

import pytest
from alembic import command
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from tests.integration.phase2.test_pr2_03_review_guards import _setup
from tests.integration.phase2.test_pr2_04_execution_migration import _alembic, _upgrade
from tests.integration.phase2.test_pr2_04_remaining_schema_acceptance import complete
from tests.integration.phase2.test_pr2_04_schema_coverage import Q, R, _material, _rows

PARENT = "0026_pr2_04_p1_contract_guards"
REVISION = "0027_pr2_04_hash_scheme_guards"


@pytest.mark.parametrize("probe", [None, "query_hash_scheme", "result_hash_scheme"])
def test_hash_scheme_commit_is_atomic(phase2_database_url, probe):
    material = _material(phase2_database_url, "reserved")
    engine = material["engine"]
    try:
        before = _rows(engine)
        if probe is None:
            with engine.begin() as connection:
                complete(connection, material)
            after = _rows(engine)
            assert len(after[Q]) == len(after[R]) == 1
            assert after[Q][0]["hash_scheme"] == after[R][0]["hash_scheme"] == "sha256-cjson-v1"
        else:
            with pytest.raises(DBAPIError) as denied:
                with engine.begin() as connection:
                    complete(connection, material, probe)
            assert getattr(denied.value.orig, "sqlstate", None) == "23514"
            assert getattr(getattr(denied.value.orig, "diag", None), "constraint_name", None) == (
                "ck_sqrec_hash_scheme" if probe == "query_hash_scheme" else "ck_srrec_hash_scheme"
            )
            assert _rows(engine) == before
    finally:
        engine.dispose()


@pytest.mark.parametrize("table", [Q, R])
def test_historical_invalid_scheme_blocks_upgrade_without_rewriting(phase2_database_url, table):
    # Build authentic complete history at 0026, then simulate an already-stored
    # bad label. Only this disposable fixture suppresses its UPDATE-only guard.
    with patch(
        "tests.integration.phase2.test_pr2_04_schema_coverage._setup",
        side_effect=lambda url: _setup(url, migration_revision=PARENT),
    ):
        material = _material(phase2_database_url, "sealed")
    engine = material["engine"]
    trigger = "trg_pr204_query_immutable" if table == Q else "trg_pr204_result_immutable"
    try:
        with engine.begin() as connection:
            connection.execute(text(f"ALTER TABLE {table} DISABLE TRIGGER {trigger}"))
            connection.execute(text(f"UPDATE {table} SET hash_scheme='other'"))
            connection.execute(text(f"ALTER TABLE {table} ENABLE TRIGGER {trigger}"))
        before = _rows(engine)
        with pytest.raises(DBAPIError, match="invalid historical hash scheme"):
            _upgrade(phase2_database_url, REVISION)
        assert _rows(engine) == before
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == PARENT
            assert (
                connection.scalar(
                    text(
                        "SELECT count(*) FROM pg_constraint WHERE conname IN "
                        "('ck_sqrec_hash_scheme','ck_srrec_hash_scheme')"
                    )
                )
                == 0
            )
            assert (
                connection.scalar(
                    text("SELECT tgenabled FROM pg_trigger WHERE tgname=:name"), {"name": trigger}
                )
                == "O"
            )
    finally:
        engine.dispose()


def test_fresh_upgrade_empty_downgrade_and_reupgrade(phase2_database_url):
    _upgrade(phase2_database_url, REVISION)
    command.downgrade(_alembic(phase2_database_url), PARENT)
    _upgrade(phase2_database_url, REVISION)
    engine = create_engine(phase2_database_url)
    try:
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == REVISION
            assert (
                connection.scalar(
                    text(
                        "SELECT count(*) FROM pg_constraint WHERE conname IN "
                        "('ck_sqrec_hash_scheme','ck_srrec_hash_scheme') AND convalidated"
                    )
                )
                == 2
            )
    finally:
        engine.dispose()


def test_populated_downgrade_refuses_before_removing_protection(phase2_database_url):
    material = _material(phase2_database_url, "sealed")
    engine = material["engine"]
    try:
        before = _rows(engine)
        with pytest.raises(DBAPIError, match="cannot downgrade populated"):
            command.downgrade(_alembic(phase2_database_url), PARENT)
        assert _rows(engine) == before
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == REVISION
            assert (
                connection.scalar(
                    text(
                        "SELECT count(*) FROM pg_constraint WHERE conname IN "
                        "('ck_sqrec_hash_scheme','ck_srrec_hash_scheme') AND convalidated"
                    )
                )
                == 2
            )
    finally:
        engine.dispose()


def test_valid_historical_provenance_is_preserved_by_upgrade(phase2_database_url):
    with patch(
        "tests.integration.phase2.test_pr2_04_schema_coverage._setup",
        side_effect=lambda url: _setup(url, migration_revision=PARENT),
    ):
        material = _material(phase2_database_url, "sealed")
    engine = material["engine"]
    try:
        before = _rows(engine)
        _upgrade(phase2_database_url, REVISION)
        assert _rows(engine) == before
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == REVISION
    finally:
        engine.dispose()
