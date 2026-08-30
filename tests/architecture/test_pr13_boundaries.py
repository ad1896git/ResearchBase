from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUERY_MODULE = ROOT / "src/researchbase/application/provenance_queries.py"


def test_query_boundary_has_no_persistence_framework_or_adapter_imports() -> None:
    tree = ast.parse(QUERY_MODULE.read_text())
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    forbidden = ("researchbase.persistence", "sqlalchemy", "fastapi", "typer", "networkx")

    assert not any(name.startswith(forbidden) for name in imported)


def test_pr13_adds_no_migration_or_generic_graph_abstraction() -> None:
    migrations = list((ROOT / "migrations/versions").glob("*.py"))
    assert [path.name for path in migrations if "0015" in path.name] == ["0015_governance_audit.py"]
    source = QUERY_MODULE.read_text()
    assert "GraphNode" not in source
    assert "GraphEdge" not in source
    assert "traverse_graph" not in source
    assert "commit(" not in source
