from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).parents[2]
SOURCE = ROOT / "src" / "researchbase"
MIGRATION = ROOT / "migrations" / "versions" / "0019_phase2_bootstrap_membership.py"
EXPECTED_TABLES = {
    "project_memberships",
    "project_role_assignments",
    "project_membership_events",
    "project_role_events",
    "actor_subject_bindings",
    "actor_subject_binding_events",
    "bootstrap_records",
    "actor_enrollment_challenges",
}


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.add(node.module)
    return modules


def test_phase2_domain_and_application_respect_layer_boundaries() -> None:
    domain_imports = _imports(SOURCE / "domain" / "phase2_identity.py")
    assert not any(
        module == "sqlalchemy"
        or module.startswith("sqlalchemy.")
        or module == "fastapi"
        or module.startswith("fastapi.")
        or module == "typer"
        or module.startswith("typer.")
        or module.startswith("researchbase.persistence")
        for module in domain_imports
    )
    application_imports = _imports(SOURCE / "application" / "phase2_identity.py")
    assert not any(
        module == "sqlalchemy"
        or module.startswith("sqlalchemy.")
        or module.startswith("researchbase.persistence")
        for module in application_imports
    )


def test_pr2_00_migration_has_exact_eight_table_inventory() -> None:
    namespace: dict[str, object] = {}
    exec(compile(MIGRATION.read_text(), str(MIGRATION), "exec"), namespace)
    tables = namespace["PHASE2_TABLES"]
    assert isinstance(tables, tuple)
    assert set(tables) == EXPECTED_TABLES


def test_pr2_00_contains_no_literature_or_governance_effects() -> None:
    source_paths = (
        SOURCE / "application" / "phase2_identity.py",
        SOURCE / "persistence" / "phase2_identity_repository.py",
        MIGRATION,
    )
    text = "\n".join(path.read_text().lower() for path in source_paths)
    forbidden = (
        "literaturesource",
        "sourceidentifier",
        "approvalgrant",
        "grantconsumption",
        "literature_command_receipts",
    )
    assert not [term for term in forbidden if term in text]
