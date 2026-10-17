"""B10 typed relations, literal snapshot inventory and Application boundary."""

import ast
import re
from pathlib import Path

from researchbase.application.decision import DecisionService
from researchbase.persistence.approval_repository import B09_SNAPSHOT_TABLES
from researchbase.persistence.manuscript_freeze_repository import B04_SNAPSHOT_TABLES

ROOT = Path(__file__).parents[2]


def test_fixed_inventory_is_exact_approved_union():
    assert B09_SNAPSHOT_TABLES == tuple(
        sorted(
            set(B04_SNAPSHOT_TABLES)
            | {
                "internal_review_records",
                "review_issues",
                "review_issue_events",
                "manuscript_versions",
                "publications",
            }
        )
    )
    assert "approval_requests" not in B09_SNAPSHOT_TABLES
    assert "decision_records" not in B09_SNAPSHOT_TABLES
    ddl = (ROOT / "migrations/versions/0056_b10_reconsideration.py").read_text()
    inventory = re.search(r"unnest\(ARRAY\[(.*?)\]\)", ddl, re.S)
    assert inventory is not None
    assert tuple(re.findall(r"'([^']+)'", inventory.group(1))) == B09_SNAPSHOT_TABLES


def test_two_common_application_methods():
    assert callable(DecisionService.record_rejection_reconsideration)
    assert callable(DecisionService.get_rejection_reconsideration)
    domain = (ROOT / "src/researchbase/domain/decision.py").read_text()
    for node in ast.walk(ast.parse(domain)):
        if isinstance(node, ast.ImportFrom):
            assert not any(
                name in (node.module or "")
                for name in ("sqlalchemy", "fastapi", "typer", "persistence", "application")
            )


def test_only_admitted_concrete_relations_are_created():
    ddl = (ROOT / "migrations/versions/0056_b10_reconsideration.py").read_text()
    tree = ast.parse(ddl)
    values = {
        n.targets[0].id: ast.literal_eval(n.value)
        for n in tree.body
        if isinstance(n, ast.Assign)
        and isinstance(n.targets[0], ast.Name)
        and n.targets[0].id in {"UPGRADE_SQL", "DOWNGRADE_SQL"}
    }
    sql = values["UPGRADE_SQL"]
    assert sql.count("CREATE TABLE ") == 2
    assert "CREATE TABLE decision_basis_approval_decisions" in sql
    assert "CREATE TABLE decision_basis_revision_actions" in sql
    assert "ON DELETE CASCADE" not in sql
    assert "DEFERRABLE INITIALLY DEFERRED" in sql
    assert "RECONSIDER_REJECTION" in sql
    assert "cannot discard reconsideration history" in values["DOWNGRADE_SQL"]
