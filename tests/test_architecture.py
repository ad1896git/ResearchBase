from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[1]
SRC = ROOT / "src" / "researchbase"


def _python_files(path: Path) -> list[Path]:
    return sorted(path.rglob("*.py"))


def test_domain_is_not_present_in_pr00() -> None:
    assert not (SRC / "domain").exists()


def test_persistence_does_not_import_framework_adapters() -> None:
    forbidden = ("fastapi", "typer")
    for path in _python_files(SRC / "persistence"):
        contents = path.read_text()
        assert not any(
            f"import {name}" in contents or f"from {name}" in contents for name in forbidden
        )


def test_no_forbidden_runtime_dependencies_or_parallel_manifests() -> None:
    project = (ROOT / "pyproject.toml").read_text().lower()
    for forbidden in ("redis", "celery", "rq", "langgraph", "storm", "evoscientist", "vector"):
        assert forbidden not in project
    assert not (ROOT / "requirements.txt").exists()
    assert not (ROOT / "Pipfile").exists()
    assert not (ROOT / "poetry.lock").exists()


def test_pr00_has_no_business_schema_migration() -> None:
    migration_text = "\n".join(path.read_text() for path in _python_files(ROOT / "migrations"))
    forbidden_tables = (
        "research_questions",
        "hypotheses",
        "experiment_specs",
        "datasets",
        "claims",
        "measurements",
    )
    assert not any(table in migration_text for table in forbidden_tables)
