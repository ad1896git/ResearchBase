"""B22 changes only immutable literature comparisons and derived navigation."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_b22_schema_is_additive_without_shared_guard_replacement():
    migration = (ROOT / "migrations/versions/0065_b22_prior_art_correction.py").read_text()
    assert "CREATE TABLE" not in migration
    assert "CREATE OR REPLACE" not in migration
    assert "ON DELETE CASCADE" not in migration
    assert "UPDATE prior_art_relations" not in migration
    assert "pr218_capture_prelocked()" in migration
    assert "pg_current_xact_id()" in migration


def test_selection_and_exact_reads_have_no_lock_or_write_calls():
    tree = ast.parse((ROOT / "src/researchbase/application/novelty.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in {
            "_read",
            "select_prior_art_relation",
            "_prior_art_history",
        }:
            calls = {
                n.func.attr
                for n in ast.walk(node)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            }
            assert not calls & {
                "prepare",
                "lock_snapshot",
                "predecessor",
                "prior_art_predecessor",
                "insert",
                "insert_child",
                "force_constraints",
                "commit",
            }
            if node.name != "_prior_art_history":
                assert "begin_formal_read" in calls


def test_no_positive_assessment_or_downstream_effect_admission():
    source = (ROOT / "src/researchbase/application/novelty.py").read_text()
    assert "c.assessment is not NoveltyOutcome.INCONCLUSIVE" in source
    for forbidden in ("approval_grant", "publication_ready", "support_set_hash", "create_decision"):
        assert forbidden not in source
    tree = ast.parse((ROOT / "src/researchbase/domain/novelty.py").read_text())
    assert not any(
        isinstance(n, ast.ImportFrom)
        and n.module
        and any(x in n.module for x in ("sqlalchemy", "fastapi", "persistence"))
        for n in ast.walk(tree)
    )
