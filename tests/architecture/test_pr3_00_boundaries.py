"""PR3-00 recursive import boundaries, including hostile nested source fixtures."""

from __future__ import annotations

import ast
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "src/researchbase"
NAMESPACES = (
    "agent_runtime",
    "strategies",
    "capabilities",
    "adapters/coding",
    "adapters/compute",
    "adapters/runtime",
)
FORBIDDEN = (
    "researchbase.persistence",
    "researchbase.orm",
    "sqlalchemy",
    "psycopg",
    "psycopg2",
    "asyncpg",
    "sqlite3",
    "peewee",
    "django.db",
    "fastapi",
    "typer",
    "openai",
    "anthropic",
    "google.genai",
    "google.generativeai",
    "boto3",
    "litellm",
    "cohere",
    "mistralai",
    "langchain",
    "langchain_core",
    "langchain_openai",
    "langgraph",
    "deepagents",
    "autogen",
    "crewai",
    "semantic_kernel",
    "agents",
    "codex",
    "openhands",
    "storm",
    "knowledge_storm",
    "paperqa",
    "evoscientist",
    "deerflow",
    "researchbase.harness",
    "skills",
    "plugins",
)


def _forbidden_imports(root: Path, package: str, forbidden: tuple[str, ...] = FORBIDDEN):
    violations: list[tuple[Path, str]] = []
    for path in sorted(root.rglob("*.py")):
        current = ".".join((package, *path.relative_to(root).parent.parts))
        tree = ast.parse(path.read_text(), filename=str(path))
        modules: set[str] = set()
        dynamic_names = {"__import__", "import_module"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                base = importlib.util.resolve_name("." * node.level + (node.module or ""), current)
                modules.add(base)
                modules.update(f"{base}.{alias.name}" for alias in node.names)
                dynamic_names.update(
                    alias.asname or alias.name
                    for alias in node.names
                    if alias.name in {"import_module", "__import__"}
                )
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = (
                node.func.id
                if isinstance(node.func, ast.Name)
                else node.func.attr
                if isinstance(node.func, ast.Attribute)
                else ""
            )
            if name not in dynamic_names:
                continue
            argument = (
                node.args[0]
                if node.args
                else next((kw.value for kw in node.keywords if kw.arg == "name"), None)
            )
            if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                target = argument.value
                if target.startswith("."):
                    # Reject unresolved relative/dynamic package expressions too.
                    package_arg = (
                        node.args[1]
                        if len(node.args) > 1
                        else next((kw.value for kw in node.keywords if kw.arg == "package"), None)
                    )
                    if isinstance(package_arg, ast.Constant) and isinstance(package_arg.value, str):
                        current_package = package_arg.value
                    elif isinstance(package_arg, ast.Name) and package_arg.id == "__package__":
                        current_package = current
                    else:
                        violations.append((path, "unresolved dynamic import"))
                        continue
                    target = importlib.util.resolve_name(target, current_package)
                modules.add(target)
            else:
                violations.append((path, "unresolved dynamic import"))
        for module in sorted(modules):
            if any(module == item or module.startswith(item + ".") for item in forbidden):
                violations.append((path, module))
    return violations


@pytest.mark.parametrize("namespace", NAMESPACES)
def test_runtime_namespaces_have_no_forbidden_imports(namespace: str) -> None:
    assert (
        _forbidden_imports(SOURCE / namespace, "researchbase." + namespace.replace("/", ".")) == []
    )


def test_foundation_does_not_import_runtime() -> None:
    assert (
        _forbidden_imports(
            SOURCE / "foundation", "researchbase.foundation", ("researchbase.agent_runtime",)
        )
        == []
    )


@pytest.mark.parametrize("module", FORBIDDEN)
def test_nested_scanner_rejects_forbidden_dependencies(tmp_path: Path, module: str) -> None:
    path = tmp_path / "nested/deeper/unsafe.py"
    path.parent.mkdir(parents=True)
    path.write_text(f"import {module} as hidden\n")
    assert _forbidden_imports(tmp_path, "researchbase.agent_runtime") == [(path, module)]


@pytest.mark.parametrize(
    "source, expected",
    [
        ("from researchbase import persistence as db", "researchbase.persistence"),
        ("from .... import persistence", "researchbase.persistence"),
        ("from ....persistence import uow", "researchbase.persistence"),
        ('__import__("sqlalchemy.orm")', "sqlalchemy.orm"),
        ('import importlib as x; x.import_module("fastapi")', "fastapi"),
        ('from importlib import import_module as load; load("openai")', "openai"),
        ('import importlib; importlib.import_module(name="typer")', "typer"),
        (
            'import importlib; importlib.import_module("....persistence", __package__)',
            "researchbase.persistence",
        ),
        (
            "from importlib import import_module; "
            'import_module("....persistence", package="researchbase.agent_runtime.nested.deeper")',
            "researchbase.persistence",
        ),
        ("__import__(provider)", "unresolved dynamic import"),
    ],
)
def test_nested_scanner_resolves_relative_and_dynamic_imports(
    tmp_path: Path, source: str, expected: str
) -> None:
    path = tmp_path / "nested/deeper/unsafe.py"
    path.parent.mkdir(parents=True)
    path.write_text(source + "\n")
    assert (path, expected) in _forbidden_imports(tmp_path, "researchbase.agent_runtime")


@pytest.mark.parametrize(
    "source", ["from .. import agent_runtime", "import researchbase.agent_runtime"]
)
def test_foundation_reverse_import_counterexamples(tmp_path: Path, source: str) -> None:
    path = tmp_path / "unsafe.py"
    path.write_text(source)
    assert _forbidden_imports(
        tmp_path, "researchbase.foundation", ("researchbase.agent_runtime",)
    ) == [(path, "researchbase.agent_runtime")]


def test_scanner_allows_application_dtos_and_foundation(tmp_path: Path) -> None:
    path = tmp_path / "safe.py"
    path.write_text(
        "from researchbase.application import commands\nfrom researchbase.foundation import errors"
    )
    assert _forbidden_imports(tmp_path, "researchbase.agent_runtime") == []


def test_bootstrap_initializers_stay_empty_and_import_without_activation(tmp_path: Path) -> None:
    packages = []
    admitted_planning_files = {
        # Owner-frozen PR3-02-S2 Q1/Q4/Q5: CREATED intents and reads only.
        "agent_runtime/domain/agent_execution.py",
        "agent_runtime/application/execution_contracts.py",
        "agent_runtime/application/agent_executions.py",
        "agent_runtime/ports/execution_repository.py",
        "agent_runtime/domain/research_task.py",
        "agent_runtime/domain/task_step.py",
        "agent_runtime/domain/task_graph.py",
        "agent_runtime/application/contracts.py",
        "agent_runtime/application/research_task.py",
        "agent_runtime/ports/task_repository.py",
        "agent_runtime/domain/task_safety.py",
        "agent_runtime/application/safety_contracts.py",
        "agent_runtime/application/task_safety.py",
        "agent_runtime/ports/task_safety_repository.py",
        "agent_runtime/services/fake_consumer.py",
        "agent_runtime/domain/agent_version.py",
        "agent_runtime/domain/harness_manifest.py",
        "agent_runtime/application/agent_contracts.py",
        "agent_runtime/application/agent_versions.py",
        "agent_runtime/ports/agent_repository.py",
        "agent_runtime/domain/capability_invocation.py",  # ADR-0025: frozen pack §8.
        "agent_runtime/domain/tool_policy.py",  # ADR-0025: frozen pack §8.
        "agent_runtime/application/gateway_contracts.py",  # ADR-0025: frozen pack §8.
        "agent_runtime/application/capability_gateway.py",  # ADR-0025: frozen pack §8.
        "agent_runtime/application/routing.py",  # ADR-0025: frozen pack §8.
        "agent_runtime/ports/capability_gateway.py",  # ADR-0025: frozen pack §8.
        "agent_runtime/ports/gateway_repository.py",  # ADR-0025: frozen pack §8.
        "agent_runtime/ports/search_repository.py",  # ADR-0029: bounded S2 storage port.
        "agent_runtime/domain/experiment_search.py",  # PR3-16 S3 pure contracts.
        "agent_runtime/domain/bearing_evaluation.py",  # D1 Stage 1 pure evaluator.
        "agent_runtime/application/search_contracts.py",  # PR3-16 S3/S6 closed contracts.
        "agent_runtime/application/experiment_search.py",  # PR3-16 bounded S4/S6 boundary.
        # Owner-approved PR3-05 read-only plan §3 R1; contracts only, no activation.
        "agent_runtime/application/context_contracts.py",
        "agent_runtime/domain/task_memory.py",
        "agent_runtime/ports/context_repository.py",
        # Owner-approved PR3-05 read-only plan §3 R2; reconstruction only.
        "agent_runtime/application/canonical_context.py",
        # Owner-approved PR3-05 read-only plan §3 R3; reads and validation only.
        "agent_runtime/application/task_memory.py",
        "agent_runtime/application/promotion_context.py",
    }
    for namespace in NAMESPACES:
        for path in sorted((SOURCE / namespace).rglob("*.py")):
            if path.relative_to(SOURCE).as_posix() in admitted_planning_files:
                continue
            assert path.name == "__init__.py" and path.read_bytes() == b""
            packages.append("researchbase." + ".".join(path.relative_to(SOURCE).parent.parts))
    script = """
import importlib
import sys
packages = sys.argv[1:]
def deny(event, args):
    if event in {'socket.connect', 'socket.bind', 'subprocess.Popen', 'os.system'}:
        raise AssertionError(event)
sys.addaudithook(deny)
for package in packages:
    importlib.import_module(package)
assert not any(name == 'sqlalchemy' or name.startswith('sqlalchemy.') for name in sys.modules)
"""
    result = subprocess.run(
        [sys.executable, "-c", script, *packages],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPYCACHEPREFIX": str(tmp_path / "pycache")},
        check=False,
    )
    assert result.returncode == 0, result.stderr
