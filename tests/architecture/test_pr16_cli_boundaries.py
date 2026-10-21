from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).parents[2]
CLI_ROOT = ROOT / "src/researchbase/cli"


def _python_files(path: Path) -> list[Path]:
    return sorted(path.rglob("*.py"))


def test_domain_application_and_foundation_do_not_import_typer() -> None:
    for path in (
        _python_files(ROOT / "src/researchbase/domain")
        + _python_files(ROOT / "src/researchbase/application")
        + _python_files(ROOT / "src/researchbase/foundation")
    ):
        assert "typer" not in path.read_text().lower(), path


def test_cli_command_modules_do_not_import_orm_session_or_http_adapter() -> None:
    for path in _python_files(CLI_ROOT):
        if path.name == "composition.py":
            continue
        source = path.read_text().lower()
        assert "sqlalchemy" not in source, path
        assert "session" not in source, path
        assert "fastapi" not in source, path
        assert "httpx" not in source, path
        assert "requests" not in source, path
        assert "subprocess" not in source, path
        assert "os.system" not in source, path
        assert ".commit(" not in source, path
        assert ".flush(" not in source, path


def test_cli_does_not_introduce_forbidden_later_scope_symbols() -> None:
    source = "\n".join(path.read_text() for path in _python_files(CLI_ROOT))
    for forbidden in ("DecisionRecord", "ApprovalRequest", "PR-17", "Phase 3", "Phase 4"):
        assert forbidden not in source


def test_cli_source_has_no_direct_repository_imports() -> None:
    for path in _python_files(CLI_ROOT):
        if path.name == "composition.py":
            continue
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith("researchbase.persistence")
