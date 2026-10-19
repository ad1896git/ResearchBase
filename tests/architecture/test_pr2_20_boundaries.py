"""Read-only hardening helpers have no canonical ownership or public command surface."""

import ast
from pathlib import Path

from tests.contracts.pr2_20_reports import (
    ARCHITECTURE_NODES,
    EXIT_CRITERIA,
    exit_rows,
    validate_exit,
)


def test_all_thirteen_mandatory_names_map_to_concrete_owning_tests():
    assert len(ARCHITECTURE_NODES) == 13
    for name, node in ARCHITECTURE_NODES.items():
        path, method = node.split("::")
        tree = ast.parse(Path(path).read_text())
        assert name == method
        assert any(isinstance(item, ast.FunctionDef) and item.name == method for item in tree.body)
    assert validate_exit(exit_rows(), ()) == "BLOCKED"
    assert len(EXIT_CRITERIA) == 19


def test_file_helpers_never_own_canonical_schema_or_new_public_commands():
    paths = (
        *Path("tests/contracts").glob("pr2_20*.py"),
        Path("tests/integration/phase2/pr2_20_support.py"),
    )
    for path in paths:
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not node.module or not node.module.startswith(
                    ("researchbase.persistence.models", "researchbase.api", "researchbase.cli")
                )
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in {
                    "create_all",
                    "drop_all",
                    "add_all",
                    "bulk_save_objects",
                }
    assert not Path("src/researchbase/application/hardening.py").exists()
    assert not list(Path("migrations/versions").glob("*pr2_20*"))


def test_strategy_and_adapter_import_graph_excludes_direct_persistence():
    paths = [
        Path("src/researchbase/application/native_research_strategy.py"),
        Path("src/researchbase/application/scientific_rag_provider.py"),
        *Path("src/researchbase/adapters").glob("*.py"),
    ]
    for path in paths:
        for node in ast.walk(ast.parse(path.read_text())):
            imports = (
                [node.module]
                if isinstance(node, ast.ImportFrom)
                else [item.name for item in node.names]
                if isinstance(node, ast.Import)
                else []
            )
            assert not any(
                name
                and any(
                    part in name.split(".") for part in ("persistence", "sqlalchemy", "psycopg")
                )
                for name in imports
            )


def test_b29_measurement_stays_in_tests_and_observers_are_snapshot_only():
    helper = Path("tests/integration/phase2/b29_measurement.py").read_text()
    tree = ast.parse(helper)
    assert "engine not in _CLONES" in helper
    assert "enable_seqscan" not in helper
    assert not list(Path("migrations/versions").glob("*b29*"))
    assert not list(Path("src/researchbase").rglob("*b29*"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert not node.module or not node.module.startswith(
                ("researchbase.persistence.models", "researchbase.api", "researchbase.cli")
            )
    support = Path("tests/integration/phase2/pr2_20_support.py").read_text()
    snapshot = next(
        node
        for node in ast.parse(support).body
        if isinstance(node, ast.FunctionDef) and node.name == "read_snapshot"
    )
    body = ast.get_source_segment(support, snapshot)
    assert body and 'isolation_level="REPEATABLE READ"' in body
    assert "SET TRANSACTION READ ONLY" in body
    assert not any(lock in body.lower() for lock in ("lock table", "pg_advisory", "for update"))


def test_h2_compaction_metadata_and_lock_observers_stay_engineering_only():
    from dataclasses import fields

    from tests.contracts.pr2_20_evidence import CompactionEvidence

    assert {f.name for f in fields(CompactionEvidence)} >= {
        "original_path",
        "retained_path",
        "retained_revision",
        "summary",
        "original_bytes",
        "retained_bytes",
        "original_sha256",
        "retained_sha256",
    }
    support = Path("tests/integration/phase2/pr2_20_support.py").read_text()
    node = next(
        n
        for n in ast.parse(support).body
        if isinstance(n, ast.FunctionDef) and n.name == "passive_locks"
    )
    body = ast.get_source_segment(support, node)
    assert body and "read_snapshot(engine)" in body
    assert "pg_locks" in body and "pg_blocking_pids" in body
    assert not any(
        token in body.lower() for token in ("lock table", "for update", "for share", "pg_advisory")
    )
