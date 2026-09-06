"""PR-18 architecture and Agent-ready Core boundary gate."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = ROOT / "src" / "researchbase"
ALLOWED_TODO_DISPOSITIONS = {
    "RESOLVED_IN_PR18",
    "ACCEPTED_NON_BLOCKING",
    "DEFERRED_WITH_EXPLICIT_FUTURE_OWNER",
    "OUT_OF_SCOPE",
}
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
                if any(term in name.lower() for term in FORBIDDEN_RUNTIME_TERMS):
                    violations.append(f"{path.relative_to(ROOT)}:{name}")
    assert violations == []


def test_adapters_do_not_own_domain_persistence_or_transactions() -> None:
    adapter_root = SOURCE_ROOT / "adapters"
    violations: list[str] = []
    if adapter_root.exists():
        for path in _python_files(adapter_root):
            text = path.read_text(encoding="utf-8")
            if "researchbase.persistence" in text or ".commit(" in text:
                violations.append(str(path.relative_to(ROOT)))
    assert violations == []


def test_architecture_todo_gate_has_no_unclassified_runtime_markers() -> None:
    markers: list[str] = []
    for root in (SOURCE_ROOT, ROOT / "migrations"):
        for path in _python_files(root):
            for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if "TODO" in line or "FIXME" in line:
                    markers.append(f"{path.relative_to(ROOT)}:{line_number}:{line.strip()}")
    assert markers == []


def test_todo_disposition_vocabulary_is_frozen() -> None:
    assert ALLOWED_TODO_DISPOSITIONS == {
        "RESOLVED_IN_PR18",
        "ACCEPTED_NON_BLOCKING",
        "DEFERRED_WITH_EXPLICIT_FUTURE_OWNER",
        "OUT_OF_SCOPE",
    }
