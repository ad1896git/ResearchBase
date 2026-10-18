"""B26 is an Application-only, nonlocking composition of existing owners."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_application_uses_ports_without_adapter_dependencies():
    source = (ROOT / "src/researchbase/application/finding_impact.py").read_text()
    tree = ast.parse(source)
    modules = [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    assert "researchbase.application.ports" in modules
    assert not any(
        any(part in module for part in ("sqlalchemy", "persistence", "api.", "cli."))
        for module in modules
    )
    assert not any(
        token in source
        for token in (
            "prepare_write",
            "lock_snapshot",
            "FOR SHARE",
            "FOR UPDATE",
            "pg_advisory",
            "LOCK TABLE",
            ".commit(",
            ".flush(",
            ".get_manuscript_validity(",
            ".get_manuscript_audit(",
        )
    )
    assert source.count("with self._factory() as uow:") == 1
    assert source.count("prepare_read(bounded=True)") == 1
    assert "build_in_uow(" in source


def test_same_uow_builder_has_no_transaction_or_authorization():
    tree = ast.parse((ROOT / "src/researchbase/application/manuscript_validity.py").read_text())
    builder = next(
        n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "build_in_uow"
    )
    text = ast.unparse(builder)
    assert all(token not in text for token in ("_factory()", "prepare_read", "authorize("))
    assert "admission=False" in text


def test_no_b26_schema_or_adapter_or_dependency():
    assert not list((ROOT / "migrations/versions").glob("*b26*"))
    assert "finding_impact" not in (ROOT / "pyproject.toml").read_text()
    for folder in ("api", "cli", "domain"):
        assert not list((ROOT / "src/researchbase" / folder).glob("*finding_impact*"))
