from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).parents[2]


def _python_files(relative: str) -> list[Path]:
    return list((ROOT / relative).rglob("*.py"))


def test_domain_application_and_foundation_do_not_import_fastapi() -> None:
    for path in (
        _python_files("src/researchbase/domain")
        + _python_files("src/researchbase/application")
        + _python_files("src/researchbase/foundation")
    ):
        assert "fastapi" not in path.read_text().lower(), path


def test_http_routes_do_not_import_persistence_or_sqlalchemy_or_commit() -> None:
    path = ROOT / "src/researchbase/api/routes.py"
    source = path.read_text()
    tree = ast.parse(source)
    imports = {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)} | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not any(name.startswith("researchbase.persistence") for name in imports)
    assert not any(name.startswith("sqlalchemy") for name in imports)
    assert ".commit(" not in source
    assert "Session" not in source


def test_pr15_adds_no_cli_or_later_phase_symbols() -> None:
    owned = "\n".join(path.read_text() for path in _python_files("src/researchbase/api"))
    assert "DecisionRecord" not in owned
    assert "ApprovalRequest" not in owned
    assert "researchbase.cli" not in owned
