from __future__ import annotations

import ast
from pathlib import Path

FOUNDATION = Path(__file__).parents[2] / "src" / "researchbase" / "foundation"

FORBIDDEN_MODULES = (
    "researchbase.persistence",
    "researchbase.identity",
    "researchbase.organization",
    "researchbase.research",
    "researchbase.experiment",
    "researchbase.evidence",
    "researchbase.governance",
    "sqlalchemy",
    "fastapi",
    "typer",
    "langgraph",
    "openhands",
    "storm",
    "evoscientist",
    "redis",
)


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.add(node.module)
    return modules


def test_foundation_has_no_forbidden_reverse_or_framework_imports() -> None:
    for path in FOUNDATION.glob("*.py"):
        for module in _imported_modules(path):
            assert not any(
                module == forbidden or module.startswith(f"{forbidden}.")
                for forbidden in FORBIDDEN_MODULES
            ), f"{path} imports forbidden module {module}"


def test_pr01_does_not_add_business_migrations() -> None:
    migrations = Path(__file__).parents[2] / "migrations" / "versions"
    assert [path.name for path in migrations.glob("*.py")] == ["0001_empty_bootstrap.py"]
