"""B16 extends the registered owner and literal lock protocol only."""

import ast
from pathlib import Path

from researchbase.persistence.prepared_submission_repository import (
    B15_SNAPSHOT_TABLES,
    B16_SHARE_SQL,
    B16_SNAPSHOT_TABLES,
)

ROOT = Path(__file__).resolve().parents[2]


def test_literal_inventory_and_final_modes():
    assert B16_SNAPSHOT_TABLES == tuple(sorted(set(B16_SNAPSHOT_TABLES)))
    assert set(B16_SNAPSHOT_TABLES) == set(B15_SNAPSHOT_TABLES) - {"publications"}
    assert B16_SHARE_SQL == "LOCK TABLE " + ",".join(B16_SNAPSHOT_TABLES) + " IN SHARE MODE"
    source = (ROOT / "src/researchbase/persistence/prepared_submission_repository.py").read_text()
    tree = ast.parse(source)
    write = next(
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "prepare_consent_write"
    )
    sql_calls = [
        n
        for n in write.body
        if isinstance(n, ast.Expr)
        and isinstance(n.value, ast.Call)
        and isinstance(n.value.func, ast.Attribute)
        and n.value.func.attr == "execute"
    ]
    assert ast.unparse(sql_calls[0]).endswith("text(B16_SHARE_SQL))")
    assert "SHARE ROW EXCLUSIVE" in ast.unparse(sql_calls[1])
    assert "approval_decisions,approval_request_reviews,approval_requests" in ast.unparse(
        sql_calls[2]
    )


def test_new_migration_has_no_new_table_or_effect():
    source = (ROOT / "migrations/versions/0061_b16_consent_withdrawal.py").read_text()
    assert 'down_revision = "0060_b15_package_preparation"' in source
    assert "CREATE TABLE" not in source and "ADD COLUMN" not in source
    for required in (
        "b16_consent_chain",
        "b16_withdrawal_staling",
        "b16_prepare_grant_guard",
        "xmin=pg_current_xact_id()::xid",
    ):
        assert required in source
    assert "SECURITY DEFINER" not in source


def test_own_read_and_replay_are_plain_snapshot_queries():
    source = (ROOT / "src/researchbase/application/prepared_submission.py").read_text()
    tree = ast.parse(source)
    for name in ("get_own_author_consent", "_consent_replay"):
        node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)
        calls = {
            n.func.attr
            for n in ast.walk(node)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        }
        assert "begin_formal_read" in calls
        assert not calls & {
            "prepare_write",
            "prepare_consent_write",
            "commit",
            "coordinate",
            "lock_chain",
            "force_constraints",
            "_stage",
            "_context",
        }
    for path in ("api/routes.py", "cli/commands/governance.py"):
        assert "get_own_author_consent" not in (ROOT / "src/researchbase" / path).read_text()
