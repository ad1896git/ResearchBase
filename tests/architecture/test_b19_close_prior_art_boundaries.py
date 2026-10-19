"""B19 adds one literature-owned relation and keeps exact read traversal plain."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_one_relation_and_owned_guards():
    source = (ROOT / "migrations/versions/0066_b19_close_prior_art_basis.py").read_text()
    assert source.count("CREATE TABLE ") == 1
    assert "CREATE TABLE novelty_assessment_prior_art_inputs" in source
    assert "CREATE OR REPLACE" not in source
    assert "ON DELETE CASCADE" not in source
    assert "UPDATE novelty_assessments" not in source
    assert "pg_current_xact_id()::xid" in source


def test_read_traversal_has_no_explicit_locks_or_writes():
    tree = ast.parse((ROOT / "src/researchbase/application/novelty.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in {
            "_view",
            "_view_saved",
            "_basis",
            "_read",
        }:
            calls = {
                x.func.attr
                for x in ast.walk(node)
                if isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute)
            }
            assert not calls & {
                "prepare",
                "lock_snapshot",
                "predecessor",
                "prior_art_predecessor",
                "insert",
                "insert_child",
                "commit",
            }
