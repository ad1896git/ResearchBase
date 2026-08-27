from __future__ import annotations

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).parents[2] / "src" / "researchbase"


def _imports(path: Path, package: str) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            resolved = _resolve_import(node, package)
            if resolved:
                modules.add(resolved)
            if node.level == 0 and node.module == "researchbase":
                modules.update(f"researchbase.{alias.name}" for alias in node.names)
            elif node.module is None:
                modules.update(f"{resolved}.{alias.name}" for alias in node.names)
    return modules


def _resolve_import(node: ast.ImportFrom, package: str) -> str:
    if node.level == 0:
        return node.module or ""
    package_parts = package.split(".")
    base_parts = package_parts[: len(package_parts) - node.level + 1]
    if node.module:
        base_parts.append(node.module)
    return ".".join(base_parts)


def _violations(
    root: Path, forbidden: tuple[str, ...], package: str = "researchbase"
) -> list[tuple[Path, str]]:
    violations: list[tuple[Path, str]] = []
    for path in sorted(root.rglob("*.py")):
        relative_parent = path.relative_to(root).parent.parts
        current_package = ".".join((package, *relative_parent))
        for module in sorted(_imports(path, current_package)):
            if any(module == item or module.startswith(f"{item}.") for item in forbidden):
                violations.append((path, module))
    return violations


def test_domain_has_no_framework_or_persistence_imports() -> None:
    assert (
        _violations(
            SRC / "domain",
            ("sqlalchemy", "fastapi", "typer", "researchbase.persistence"),
        )
        == []
    )


def test_application_has_no_sqlalchemy_or_concrete_persistence_imports() -> None:
    assert _violations(SRC / "application", ("sqlalchemy", "researchbase.persistence")) == []


@pytest.mark.parametrize(
    ("source", "package", "expected"),
    [
        (
            "from researchbase.persistence.models import ActorModel\n",
            "researchbase.application",
            "researchbase.persistence.models",
        ),
        (
            "from researchbase import persistence\n",
            "researchbase.application",
            "researchbase.persistence",
        ),
        (
            "from ..persistence import models\n",
            "researchbase.application",
            "researchbase.persistence",
        ),
        ("from sqlalchemy.orm import Session\n", "researchbase.application", "sqlalchemy.orm"),
    ],
)
def test_boundary_checker_catches_adversarial_application_imports(
    tmp_path: Path, source: str, package: str, expected: str
) -> None:
    path = tmp_path / "unsafe.py"
    path.write_text(source)

    assert _violations(tmp_path, ("sqlalchemy", "researchbase.persistence"), package) == [
        (path, expected)
    ]
