from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

MIGRATION = Path(__file__).parents[2] / "migrations/versions/0016_pr17d_history_protection.py"


def test_pr17d_migration_declares_frozen_revision_and_object_graph() -> None:
    source = MIGRATION.read_text()
    tree = ast.parse(source)
    assignments = {}
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id in {"revision", "down_revision"}:
                assert node.value is not None
                assignments[node.target.id] = ast.literal_eval(node.value)

    assert assignments == {
        "revision": "0016_pr17d_history_protection",
        "down_revision": "0015_governance_audit",
    }
    spec = importlib.util.spec_from_file_location("pr17d_migration", MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert len(module.FUNCTION_NAMES) == 18
    assert len(module.TRIGGER_DEFINITIONS) == 40
    assert len({name for name in module.FUNCTION_NAMES}) == 18
    assert len({name for name, _table, _event, _function in module.TRIGGER_DEFINITIONS}) == 40
    assert all(name.startswith("pr17d_") for name in module.FUNCTION_NAMES)
    assert all(
        name.startswith("pr17d_") for name, _table, _event, _function in module.TRIGGER_DEFINITIONS
    )
