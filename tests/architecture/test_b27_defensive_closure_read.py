"""B27 keeps schema, literal hash material and Application boundaries intact."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_saved_boundary_has_no_persistence_or_transport_dependency():
    source = (ROOT / "src/researchbase/application/saved_provenance.py").read_text()
    imports = [n.module for n in ast.walk(ast.parse(source)) if isinstance(n, ast.ImportFrom)]
    assert all(
        not any(x in (name or "") for x in ("persistence", "sqlalchemy", "api", "cli"))
        for name in imports
    )
    assert "except Exception" not in source


def test_migration_retains_existing_schema_and_guards():
    assert not list((ROOT / "migrations/versions").glob("*b27*"))


def test_in_uow_diagnostics_do_not_reopen_transactions():
    tree = ast.parse((ROOT / "src/researchbase/application/closure.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.endswith("_in_uow"):
            assert not any(
                isinstance(x, ast.Attribute)
                and x.attr in {"begin_formal_read", "commit", "_uow_factory"}
                for x in ast.walk(node)
            )
