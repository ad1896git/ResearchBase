"""M1-S1 relational scope and lock inventories."""

import ast
from pathlib import Path

from researchbase.persistence.approval_repository import B09_SNAPSHOT_TABLES
from researchbase.persistence.manuscript_freeze_repository import (
    M1_EDIT_SQL,
    M1_EDIT_TABLES,
    M1_SHARE_SQL,
    M1_SNAPSHOT_TABLES,
)
from researchbase.persistence.revision_action_repository import REVISION_SNAPSHOT_TABLES

ROOT = Path(__file__).resolve().parents[2]


def test_m1_disjoint_final_mode_edit_inventory():
    assert len(M1_SNAPSHOT_TABLES) == 38
    assert len(M1_EDIT_TABLES) == 5
    assert not set(M1_SNAPSHOT_TABLES) & set(M1_EDIT_TABLES)
    assert list(M1_SNAPSHOT_TABLES) == sorted(M1_SNAPSHOT_TABLES)
    assert M1_SHARE_SQL.endswith(" IN SHARE MODE")
    assert M1_EDIT_SQL.endswith(" IN EXCLUSIVE MODE")
    assert set(M1_SNAPSHOT_TABLES) | set(M1_EDIT_TABLES) <= set(B09_SNAPSHOT_TABLES)
    # §12.2 gives disposition its own subset; action/decision/re-review use full B09.
    assert REVISION_SNAPSHOT_TABLES == tuple(
        t for t in B09_SNAPSHOT_TABLES if t not in {"review_issues", "review_issue_events"}
    )


def test_m1_forward_migration_admits_no_tables_columns_or_reconsideration():
    path = ROOT / "migrations/versions/0074_m1_manuscript_revision.py"
    tree = ast.parse(path.read_text())
    values = {
        n.targets[0].id: ast.literal_eval(n.value)
        for n in tree.body
        if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
    }
    assert values["down_revision"] == "0073_b02_strategy_admission"
    sql = values["_UPGRADE"].upper()
    assert "CREATE TABLE" not in sql and "ADD COLUMN" not in sql
    assert "CK_M1_MANUSCRIPT_CHANGE_CLASS" in sql
    assert "UQ_M1_ONE_DRAFT_MANUSCRIPT" in sql
    assert "CREATE FUNCTION M1_MANUSCRIPT" in sql
    assert "RECONSIDER REJECTION FOR READY_FOR_SUBMISSION" not in sql
