"""B20 remains inside existing owners with frozen sibling guards."""

import ast
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from researchbase.persistence.novelty_repository import N

ROOT = Path(__file__).resolve().parents[2]


def test_closed_owner_and_import_boundary():
    for layer in ("domain", "application"):
        source = (ROOT / f"src/researchbase/{layer}/novelty.py").read_text()
        imports = [x.module for x in ast.walk(ast.parse(source)) if isinstance(x, ast.ImportFrom)]
        assert not any(
            x
            and x.startswith(
                ("sqlalchemy", "fastapi", "typer", "researchbase.persistence", "codex")
            )
            for x in imports
        )
    assert not (ROOT / "src/researchbase/application/screening.py").exists()
    assert tuple(sorted(N)) == N
    assert not any("novelty_assessment" in x for x in N)


def test_one_forward_migration_owns_only_screening_guards():
    scripts = ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini")))
    assert scripts.get_heads() == ["0077_research_task_graph"]
    assert (
        scripts.get_revision(scripts.get_heads()[0]).down_revision == "0076_agent_runtime_bootstrap"
    )
    source = (ROOT / "migrations/versions/0070_b20_screening_basis.py").read_text()
    assert "CREATE OR REPLACE" not in source
    assert "ON DELETE CASCADE" not in source
    assert "JSONB" not in source
    assert "WHEN (NOT NEW.screening_captured)" in source
    assert "DEFERRABLE INITIALLY DEFERRED" in source
    assert "pg_current_xact_id()::xid" in source
    for name in ("pr218_", "b19_", "b21_", "b22_"):
        assert "CREATE FUNCTION " + name not in source


def test_reads_do_not_prepare_or_lock():
    source = (ROOT / "src/researchbase/application/novelty.py").read_text()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in {
            "_read",
            "select_prior_art_relation",
            "_screening",
        }:
            calls = {
                x.func.attr
                for x in ast.walk(node)
                if isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute)
            }
            assert not {"prepare", "predecessor", "lock_snapshot"} & calls
            if node.name != "_screening":
                assert "begin_formal_read" in calls
