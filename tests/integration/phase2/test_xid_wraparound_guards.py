"""Forward-only xid correction preserves every other trigger byte and attribute."""

import re

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from tests.integration.phase2 import pr2_20_support as support

pytestmark = pytest.mark.integration

FUNCTIONS = (
    "allow_impact_target_only_with_new_parent",
    "b07_revision_basis_guard",
    "b07_validate_decision",
    "b07_validate_re_review",
    "b07_validate_revision",
    "b08_check_history",
    "b08_complete_history",
    "b08_event_guard",
    "b08_validate_mapping",
    "b10_child_check",
    "b10_revision_verify",
    "b10_successor_check",
    "b10_validate",
    "b11_check_basis",
    "m3_support_guard",
    "pr210_reference_guard",
    "pr214_issue_guard",
    "pr215_basis_guard",
    "pr216_complete",
    "pr216_event_insert",
    "pr216_grant_guard",
    "pr216_relation_guard",
    "pr216_request_guard",
    "pr217_snapshot_sealed",
    "pr218_child_guard",
    "reject_statistical_result_input_mutation",
)


def definitions(engine):
    with engine.connect() as connection:
        return dict(
            connection.execute(
                text(
                    "SELECT proname,pg_get_functiondef(oid) FROM pg_proc "
                    "WHERE pronamespace='public'::regnamespace"
                )
            ).all()
        )


def corrected(sql):
    sql = sql.replace("xmin::text::bigint", "xmin")
    sql = sql.replace("pg_current_xact_id()::text::bigint", "pg_current_xact_id()::xid")
    sql = sql.replace("txid_current()", "pg_current_xact_id()::xid")
    return re.sub(
        r"((?:parent_xmin|owner_xmin|parent_xid|stamp)\s+)bigint", r"\1xid", sql, flags=re.I
    )


def test_forward_migration_replaces_all_epoch_unsafe_functions_and_nothing_else(monkeypatch):
    with support.database() as url:
        monkeypatch.setenv("DATABASE_URL", url)
        support.upgrade(url, "0056_b10_reconsideration")
        engine = create_engine(url)
        try:
            support.require_pg18(engine)
            before = definitions(engine)
            affected = {name for name, sql in before.items() if "xmin::text::bigint" in sql}
            assert affected == set(FUNCTIONS)
            support.upgrade(url, "0057_xid_wraparound_guards")
            after = definitions(engine)
            assert set(before) == set(after)
            assert {name for name in before if before[name] != after[name]} == affected
            for name in before:
                assert after[name] == corrected(before[name]), name
            support.upgrade(url, "0057_xid_wraparound_guards")
            assert definitions(engine) == after

            config = Config("alembic.ini")
            config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
            command.downgrade(config, "0056_b10_reconsideration")
            assert definitions(engine) == after
            support.upgrade(url, "0057_xid_wraparound_guards")
            assert definitions(engine) == after
            engine.dispose()
            assert definitions(engine) == after
        finally:
            engine.dispose()


@pytest.mark.parametrize("epoch", [0, 1, 7])
def test_xmin_comparison_retains_same_transaction_and_sealing_across_epochs(epoch, monkeypatch):
    with support.database() as url:
        monkeypatch.setenv("DATABASE_URL", url)
        engine = create_engine(url)
        try:
            support.require_pg18(engine)
            with engine.begin() as connection:
                connection.execute(text("CREATE TABLE xid_probe (id integer PRIMARY KEY)"))
                connection.execute(text("INSERT INTO xid_probe VALUES (1)"))
                low = connection.execute(
                    text("SELECT pg_current_xact_id()::xid::text::bigint")
                ).scalar_one()
                full = str((epoch << 32) + low)
                same, unsafe = connection.execute(
                    text(
                        "SELECT xmin=CAST(:full AS text)::xid8::xid, "
                        "xmin::text::bigint=CAST(:full AS text)::bigint FROM xid_probe"
                    ),
                    {"full": full},
                ).one()
                assert same is True
                assert unsafe is (epoch == 0)
            # A later transaction still cannot append to the sealed parent's set.
            with engine.begin() as connection:
                connection.execute(text("SELECT pg_current_xact_id()"))
                assert (
                    connection.execute(
                        text("SELECT xmin=pg_current_xact_id()::xid FROM xid_probe")
                    ).scalar_one()
                    is False
                )
        finally:
            engine.dispose()
