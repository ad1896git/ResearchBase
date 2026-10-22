"""PR-18 architecture and Agent-ready Core boundary gate."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import get_type_hints

from scripts.pr18_evidence import TODO_DISPOSITIONS, audit_repository_markers

from researchbase.application.commands import _WRITE_COMMAND_NAMES, ApplicationService
from researchbase.application.dto import WriteResult

ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = ROOT / "src" / "researchbase"
ALLOWED_TODO_DISPOSITIONS = set(TODO_DISPOSITIONS)
FORBIDDEN_RUNTIME_TERMS = (
    "agent_runtime",
    "agent_framework",
    "langgraph",
    "autogen",
    "celery",
)


def _python_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.py") if path.is_file())


def test_core_has_no_agent_or_phase2_runtime_imports() -> None:
    violations: list[str] = []
    for path in _python_files(SOURCE_ROOT):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [item.name for item in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            for name in names:
                # PR3-01 admits the planning module at its specified adapters/ports.
                # Phase 1 scientific Core still cannot import that runtime.
                if name.startswith("researchbase.agent_runtime") and (
                    path.is_relative_to(SOURCE_ROOT / "agent_runtime")
                    or path.is_relative_to(SOURCE_ROOT / "persistence")
                    or path.relative_to(SOURCE_ROOT).as_posix()
                    in {
                        "api/app.py",
                        "api/routes.py",
                        "cli/composition.py",
                        "cli/commands/research_tasks.py",
                    }
                ):
                    continue
                if any(term in name.lower() for term in FORBIDDEN_RUNTIME_TERMS):
                    violations.append(f"{path.relative_to(ROOT)}:{name}")
    assert violations == []


def test_adapters_do_not_own_domain_persistence_or_transactions() -> None:
    violations: list[str] = []
    for adapter_root in (SOURCE_ROOT / "api", SOURCE_ROOT / "cli"):
        for path in _python_files(adapter_root):
            if path.name in {"app.py", "composition.py"}:
                continue
            source = path.read_text(encoding="utf-8")
            if "researchbase.persistence" in source or ".commit(" in source or ".flush(" in source:
                violations.append(str(path.relative_to(ROOT)))
    assert violations == []


def test_architecture_todo_gate_has_no_unclassified_runtime_markers() -> None:
    audit = audit_repository_markers(ROOT)
    assert audit["undisposed_live"] == []
    assert audit["architecture_p0"] == []
    assert audit["architecture_p1"] == []


def test_todo_disposition_vocabulary_is_frozen() -> None:
    assert ALLOWED_TODO_DISPOSITIONS == {
        "CLOSED",
        "INTENTIONAL_NONBLOCKING",
        "OUT_OF_PHASE",
        "PR18_BLOCKER",
    }


def test_core_imports_are_transport_and_persistence_independent() -> None:
    forbidden = ("fastapi", "typer", "sqlalchemy", "researchbase.persistence")
    violations: list[str] = []
    for path in _python_files(SOURCE_ROOT / "domain") + _python_files(SOURCE_ROOT / "application"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        for imported in imports:
            if any(imported == item or imported.startswith(f"{item}.") for item in forbidden):
                violations.append(f"{path.relative_to(ROOT)}:{imported}")
    assert violations == []


def test_application_writes_and_queries_remain_the_shared_agent_ready_boundary() -> None:
    for name in _WRITE_COMMAND_NAMES:
        assert get_type_hints(getattr(ApplicationService, name))["return"] is WriteResult
    query_source = (SOURCE_ROOT / "application" / "provenance_queries.py").read_text()
    assert "FastAPI" not in query_source
    assert "Typer" not in query_source
    assert "Session" not in query_source


def test_phase1_has_no_generic_version_or_polymorphic_provenance_escape_hatches() -> None:
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in _python_files(SOURCE_ROOT / "persistence")
        + _python_files(SOURCE_ROOT / "domain")
    )
    assert "class VersionRepository" not in source
    assert "class GenericVersion" not in source
    assert "class ProvenanceNode" not in source
    assert "class PolymorphicProvenance" not in source
