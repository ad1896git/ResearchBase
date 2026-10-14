from __future__ import annotations

import ast
from pathlib import Path

import pytest

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


def _imported_modules(path: Path, package: str = "researchbase.foundation") -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.add(_resolve_import(node, package))
            if node.level == 0 and node.module == "researchbase":
                modules.update(f"researchbase.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            resolved_base = _resolve_import(node, package)
            modules.update(f"{resolved_base}.{alias.name}" for alias in node.names)
    return modules


def _resolve_import(node: ast.ImportFrom, package: str) -> str:
    if node.level == 0:
        return node.module or ""

    package_parts = package.split(".")
    base_parts = package_parts[: len(package_parts) - node.level + 1]
    if node.module:
        base_parts.append(node.module)
    return ".".join(base_parts)


def _find_forbidden_imports(
    root: Path, package: str = "researchbase.foundation"
) -> list[tuple[Path, str]]:
    violations: list[tuple[Path, str]] = []
    for path in sorted(root.rglob("*.py")):
        relative_parent = path.relative_to(root).parent.parts
        current_package = ".".join((package, *relative_parent))
        imported_modules = _imported_modules(path, current_package)
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                function_name = (
                    node.func.attr
                    if isinstance(node.func, ast.Attribute)
                    else node.func.id
                    if isinstance(node.func, ast.Name)
                    else None
                )
                if (
                    function_name in {"import_module", "__import__"}
                    and node.args
                    and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)
                ):
                    imported_modules.add(node.args[0].value)

        for module in sorted(imported_modules):
            forbidden = next(
                (
                    candidate
                    for candidate in FORBIDDEN_MODULES
                    if module == candidate or module.startswith(f"{candidate}.")
                ),
                None,
            )
            if forbidden is not None:
                violations.append((path, forbidden))
    return violations


def test_foundation_has_no_forbidden_reverse_or_framework_imports() -> None:
    assert _find_forbidden_imports(FOUNDATION) == []


def test_production_does_not_import_shared_test_contracts() -> None:
    source_root = Path(__file__).parents[2] / "src" / "researchbase"
    violations = []
    for path in sorted(source_root.rglob("*.py")):
        relative_parent = path.relative_to(source_root).parent.parts
        current_package = ".".join(("researchbase", *relative_parent))
        for module in _imported_modules(path, current_package):
            if module == "tests" or module.startswith("tests."):
                violations.append((path, module))
    assert violations == []


def test_migration_lineage_preserves_phase1_and_adds_authorized_phase2_migration() -> None:
    # Exact allowlist through owner-approved Task 12 schema repair. Phase 1 and
    # earlier Phase 2 entries remain mandatory; unapproved additions still fail.
    migrations = Path(__file__).parents[2] / "migrations" / "versions"
    assert sorted(path.name for path in migrations.glob("*.py")) == [
        "0001_empty_bootstrap.py",
        "0002_actor_project_workspace.py",
        "0003_research_question_hypothesis.py",
        "0004_experiment_spec.py",
        "0005_dataset_snapshot.py",
        "0006_artifact_version.py",
        "0007_metric_definition.py",
        "0008_run_core.py",
        "0009_run_input_seal_fix.py",
        "0010_measurement.py",
        "0011_statistical_result.py",
        "0012_statistical_result_input_guard.py",
        "0013_statistical_result_legacy_input_precheck.py",
        "0014_claim_evidence.py",
        "0015_governance_audit.py",
        "0016_pr17d_history_protection.py",
        "0017_persisted_canonical_enum_normalization.py",
        "0018_current_pointer_same_parent_integrity.py",
        "0019_phase2_bootstrap_membership.py",
        "0020_literature_source_identity.py",
        "0021_source_merge_governance_bridge.py",
        "0021a_source_merge_governance_guards.py",
        "0022_source_version_and_merge_lineage.py",
        "0023_literature_search_plan.py",
        "0023a_search_plan_review_guards.py",
        "0024_literature_search_execution.py",
        "0025_pr2_04_reservation_guards.py",
        "0026_pr2_04_p1_contract_guards.py",
        "0027_pr2_04_hash_scheme_guards.py",
        "0028_provider_cancellation.py",
        "0029_metadata_observations.py",
        "0030_literature_evidence.py",
        "0031_m3_snapshot_relation_cardinality.py",
        "0032_pr2_10_discussion.py",
        "0033_pr2_11_r2_scientific_conclusion.py",
        "0034_pr2_10_exact_transcript_binding.py",
        "0035_pr2_12_publication_draft.py",
        "0036_pr2_13_citation_placement.py",
        "0037_pr2_13_claim_placement.py",
        "0038_pr2_13_artifact_placement.py",
        "0039_pr2_13_citation_rebinding_guard.py",
        "0040_pr2_14_initial_internal_review.py",
        "0041_pr2_15_review_coordination.py",
        "0042_pr2_15_minimal_decision.py",
        "0043_pr2_04_schema_contract.py",
        "0044_pr2_15_revision_action.py",
    ]


def test_boundary_scanner_recurses_into_nested_foundation_files(tmp_path: Path) -> None:
    nested = tmp_path / "nested" / "unsafe.py"
    nested.parent.mkdir()
    nested.write_text("from ...persistence import db\n")

    violations = _find_forbidden_imports(tmp_path)

    assert violations == [(nested, "researchbase.persistence")]


@pytest.mark.parametrize(
    "source, expected",
    [
        ("from researchbase.persistence import db\n", "researchbase.persistence"),
        ("from researchbase import persistence\n", "researchbase.persistence"),
        ("from sqlalchemy import text\n", "sqlalchemy"),
        ("from fastapi import FastAPI\n", "fastapi"),
        ("import typer\n", "typer"),
        ("import langgraph\n", "langgraph"),
    ],
)
def test_boundary_scanner_catches_absolute_and_framework_imports(
    tmp_path: Path, source: str, expected: str
) -> None:
    path = tmp_path / "unsafe.py"
    path.write_text(source)

    violations = _find_forbidden_imports(tmp_path)

    assert violations == [(path, expected)]


def test_boundary_scanner_resolves_relative_imports_from_foundation_package(tmp_path: Path) -> None:
    path = tmp_path / "unsafe.py"
    path.write_text("from .. import persistence\n")

    violations = _find_forbidden_imports(tmp_path, package="researchbase.foundation")

    assert violations == [(path, "researchbase.persistence")]


@pytest.mark.parametrize(
    "source",
    [
        'import importlib\nimportlib.import_module("sqlalchemy")\n',
        '__import__("fastapi")\n',
    ],
)
def test_boundary_scanner_catches_obvious_dynamic_framework_imports(
    tmp_path: Path, source: str
) -> None:
    path = tmp_path / "unsafe.py"
    path.write_text(source)

    violations = _find_forbidden_imports(tmp_path)

    assert violations[0][0] == path
    assert violations[0][1] in {"sqlalchemy", "fastapi"}
