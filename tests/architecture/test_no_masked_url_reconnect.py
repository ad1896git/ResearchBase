"""SQLAlchemy URL display strings must never become connection credentials."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
# Exact (relative path, expression) exemptions may be added only for logging.
# There are currently no SQLAlchemy URL display conversions needing an exemption.
LOGGING_ONLY: set[tuple[str, str]] = set()


def masked_conversions(source: str) -> list[tuple[int, str]]:
    tree = ast.parse(source)
    sqlalchemy = any(
        isinstance(node, ast.ImportFrom)
        and (node.module or "").startswith("sqlalchemy")
        or isinstance(node, ast.Import)
        and any(alias.name.startswith("sqlalchemy") for alias in node.names)
        for node in ast.walk(tree)
    )

    url_names: set[str] = set()

    def is_url(node: ast.AST) -> bool:
        if isinstance(node, ast.Attribute):
            return node.attr == "url"
        if isinstance(node, ast.Name):
            return node.id in url_names or (
                sqlalchemy and (node.id == "url" or node.id.endswith("_url"))
            )
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                return node.func.id in {"make_url", "db_url"}
            if isinstance(node.func, ast.Attribute):
                return (node.func.attr == "set" and is_url(node.func.value)) or (
                    node.func.attr == "create"
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "URL"
                )
        return False

    # Follow local aliases such as base = make_url(...); target = base.set(...).
    # Repeat to cover aliases regardless of traversal order.
    changed = True
    while changed:
        before = set(url_names)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and is_url(node.value):
                url_names.update(
                    target.id for target in node.targets if isinstance(target, ast.Name)
                )
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                if (node.value is not None and is_url(node.value)) or (
                    isinstance(node.annotation, ast.Name) and node.annotation.id == "URL"
                ):
                    url_names.add(node.target.id)
        changed = before != url_names

    found = []
    for node in ast.walk(tree):
        unsafe = False
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "str":
                unsafe = bool(node.args) and is_url(node.args[0])
            elif isinstance(node.func, ast.Attribute) and node.func.attr == "render_as_string":
                # Both default rendering and hide_password=True mask credentials.
                unsafe = not any(
                    keyword.arg == "hide_password"
                    and isinstance(keyword.value, ast.Constant)
                    and keyword.value.value is False
                    for keyword in node.keywords
                ) and not (
                    node.args
                    and isinstance(node.args[0], ast.Constant)
                    and node.args[0].value is False
                )
        elif isinstance(node, ast.FormattedValue):
            unsafe = is_url(node.value)
        if unsafe and isinstance(node, ast.Call | ast.FormattedValue):
            found.append((node.lineno, ast.unparse(node)))
    return found


def test_no_masked_url_reconnect() -> None:
    violations = []
    exemptions = set()
    for directory in ("tests", "scripts", "src"):
        for path in sorted((ROOT / directory).rglob("*.py")):
            relative = path.relative_to(ROOT).as_posix()
            for line, expression in masked_conversions(path.read_text()):
                if (relative, expression) in LOGGING_ONLY:
                    exemptions.add((relative, expression))
                else:
                    violations.append(f"{relative}:{line}: {expression}")
    assert exemptions == LOGGING_ONLY, "Remove stale logging exemptions"
    assert not violations, (
        "Pass URL objects or render_as_string(hide_password=False):\n" + "\n".join(violations)
    )


@pytest.mark.parametrize(
    "expression",
    [
        "str(engine.url)",
        "str(url)",
        "str(engine.url.set(database='other'))",
        'f"{engine.url}"',
        'f"{url}"',
        "engine.url.render_as_string()",
        "engine.url.render_as_string(hide_password=True)",
        "create_engine(str(engine.url))",
        "base = make_url('postgresql://user:password@localhost/db'); str(base)",
        "base = engine.url; target = base.set(database='other'); str(target)",
        "base: URL; str(base)",
    ],
)
def test_scan_rejects_masked_credentials(expression: str) -> None:
    assert masked_conversions("from sqlalchemy.engine import URL\n" + expression)


@pytest.mark.parametrize(
    "expression",
    [
        "create_engine(engine.url)",
        "engine.url.render_as_string(hide_password=False)",
        "url.set(database='other').render_as_string(hide_password=False)",
        "str(identity[0]) == url.username",
    ],
)
def test_scan_accepts_lossless_urls(expression: str) -> None:
    assert not masked_conversions("from sqlalchemy.engine import URL\n" + expression)
