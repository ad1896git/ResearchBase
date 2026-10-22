"""Exact frozen relational inventory and retained trigger attachment sites."""

import pytest
from sqlalchemy import inspect, text

from researchbase.persistence.task_safety_repository import SAFETY_TABLES


def test_exact_schema_indexes_and_trigger_inventory(planning):
    with planning.engine.connect() as conn:
        inspector = inspect(conn)
        assert set(SAFETY_TABLES) <= set(inspector.get_table_names())
        for table in SAFETY_TABLES:
            fks = inspector.get_foreign_keys(table)
            assert fks and all(fk["options"].get("ondelete") == "RESTRICT" for fk in fks)
            assert {"id", "research_task_id", "created_at", "receipt_id"} <= {
                c["name"] for c in inspector.get_columns(table)
            }
        assert (
            conn.execute(
                text(
                    "SELECT count(*) FROM pg_indexes WHERE schemaname='public' AND indexname LIKE 'pr304_%'"  # noqa: E501
                )
            ).scalar_one()
            == 34
        )
        triggers = conn.execute(
            text(
                "SELECT tgname,tgdeferrable FROM pg_trigger WHERE NOT tgisinternal AND (tgname LIKE 'pr301_%' OR tgname LIKE 'pr304_%')"  # noqa: E501
            )
        ).all()
        assert len(triggers) == 27
        assert sum(row.tgdeferrable for row in triggers) == 4
        assert sum(row.tgname.startswith("pr304_") for row in triggers) == 8
        assert (
            conn.execute(
                text("SELECT count(*) FROM pg_proc WHERE proname LIKE 'pr304_%'")
            ).scalar_one()
            == 5
        )
        assert conn.execute(text("SHOW server_version")).scalar_one().startswith("18.")


@pytest.mark.parametrize(
    "column,expected",
    (
        ("budget_policy_id", "uuid"),
        ("termination_policy_id", "uuid"),
        ("checkpoint_policy_id", "uuid"),
    ),
)
def test_nullable_task_policy_bindings(planning, column, expected):
    with planning.engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT data_type,is_nullable FROM information_schema.columns WHERE table_name='research_tasks' AND column_name=:column"  # noqa: E501
            ),
            {"column": column},
        ).one()
        assert tuple(row) == (expected, "YES")
