"""Finite source guard: one engine creator; not a hostile-Python sandbox."""

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CREATOR = ROOT / "src/researchbase/persistence/database.py"
BAD = {
    "create_engine",
    "create_async_engine",
    "engine_from_config",
    "async_engine_from_config",
    "raw_connection",
}


def violations(source: str, inherited=None, tree=None) -> list[int]:
    tree = ast.parse(source) if tree is None else tree
    names = dict(inherited or {})
    nodes = []
    nested = []

    def collect(node):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            nested.append(node)
            return
        nodes.append(node)
        for child in ast.iter_child_nodes(node):
            collect(child)

    collect(tree)
    constants = {}
    errors = set()

    def resolve(node):
        if isinstance(node, ast.Name):
            return names.get(node.id, node.id)
        if isinstance(node, ast.Attribute):
            return resolve(node.value) + "." + node.attr
        if isinstance(node, ast.Call):
            target = resolve(node.func)
            if target in {"__import__", "importlib.import_module"}:
                arg = literal(node.args[0]) if node.args else None
                return arg if isinstance(arg, str) else "<dynamic-import>"
            if target in {"getattr", "builtins.getattr"} and len(node.args) >= 2:
                return resolve(node.args[0]) + "." + str(literal(node.args[1]))
            return target + "()"
        return "<unknown>"

    def literal(node):
        return (
            node.value
            if isinstance(node, ast.Constant)
            else constants.get(node.id)
            if isinstance(node, ast.Name)
            else None
        )

    # Imports/aliases are closed and no unresolved dynamic import can acquire a DB driver.
    for node in nodes:
        if isinstance(node, ast.Import):
            if any(a.name.split(".")[0] in {"psycopg", "psycopg2", "asyncpg"} for a in node.names):
                errors.add(node.lineno)
            for a in node.names:
                names[a.asname or a.name.split(".")[0]] = (
                    a.name if a.asname else a.name.split(".")[0]
                )
        elif isinstance(node, ast.ImportFrom):
            if any(a.name in BAD for a in node.names) or (node.module or "").split(".")[0] in {
                "psycopg",
                "psycopg2",
                "asyncpg",
            }:
                errors.add(node.lineno)
            for a in node.names:
                names[a.asname or a.name] = (node.module or "") + "." + a.name
    for _ in range(4):
        for node in nodes:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        names[target.id] = resolve(node.value)
                        if isinstance(node.value, ast.Constant):
                            constants[target.id] = node.value.value
            elif isinstance(node, ast.With):
                for item in node.items:
                    if isinstance(item.optional_vars, ast.Name):
                        names[item.optional_vars.id] = resolve(item.context_expr)
    for node in nodes:
        if isinstance(node, ast.Call):
            target = resolve(node.func)
            leaf = target.rsplit(".", 1)[-1]
            if (
                leaf in BAD
                or target.startswith(
                    (
                        "psycopg.connect",
                        "psycopg2.connect",
                        "asyncpg.connect",
                        "asyncpg.create_pool",
                    )
                )
                or target in {"eval", "exec", "globals", "locals"}
                or "<dynamic-import>" in target
                or (leaf == "connect" and not target.startswith("socket.socket()."))
                or (
                    target in {"__import__", "importlib.import_module"}
                    and (not node.args or not isinstance(literal(node.args[0]), str))
                )
                or (
                    target in {"getattr", "builtins.getattr"}
                    and node.args
                    and resolve(node.args[0]).startswith(("sqlalchemy", "psycopg", "asyncpg"))
                    and (len(node.args) < 2 or not isinstance(literal(node.args[1]), str))
                )
            ):
                errors.add(node.lineno)
    for node in nested:
        errors.update(violations("", names, ast.Module(body=node.body, type_ignores=[])))
    return sorted(errors)


@pytest.mark.parametrize(
    "source",
    [
        'from sqlalchemy import create_engine as c\nc("x")',
        'import sqlalchemy as s\ns.create_engine("x")',
        'from sqlalchemy.ext.asyncio import create_async_engine as c\nc("x")',
        "from sqlalchemy import engine_from_config as c\nc({})",
        'import psycopg as p\np.connect("x")',
        'from psycopg import connect as c\nc("x")',
        'import importlib as i\nm=i.import_module("sqlalchemy")\nm.create_engine("x")',
        'm=__import__("psycopg")\nm.connect("x")',
        'import sqlalchemy as s\nc=getattr(s,"create_engine")\nc("x")',
        'import sqlalchemy as s\nc=getattr(s,key)\nc("x")',
        "import importlib\nm=importlib.import_module(key)",
        (
            "from researchbase.persistence.database import create_database_engine\n"
            "e=create_database_engine()\ne.connect()"
        ),
        "something.connect()",
        'from builtins import getattr as g\nimport sqlalchemy as s\ng(s,"create_engine")("x")',
        'import sqlalchemy as s\nglobals()["s"].create_engine("x")',
        "from sqlalchemy import create_engine as callback",
    ],
)
def test_rejects_bypass(source):
    assert violations(source)


def test_socket_is_not_database():
    assert not violations('import socket\nwith socket.socket() as s:\n s.connect("x")')


def test_shipped_sources_have_one_creator():
    failures = {}
    for p in [*(ROOT / "src/researchbase").rglob("*.py"), ROOT / "migrations/env.py"]:
        if p != CREATOR:
            bad = violations(p.read_text())
            if bad:
                failures[str(p.relative_to(ROOT))] = bad
    assert not failures


def test_neutral_module_has_no_framework_import():
    p = ROOT / "src/researchbase/foundation/bearing_binding_contracts.py"
    assert not any(
        word in p.read_text()
        for word in (
            "sqlalchemy",
            "psycopg",
            "researchbase.persistence",
            "researchbase.application",
        )
    )
