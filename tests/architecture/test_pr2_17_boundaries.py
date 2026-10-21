"""S1 boundaries are literal, additive, and have exactly four service methods."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_pure_domain_and_application_imports():
    for layer in ("domain", "application"):
        tree = ast.parse((ROOT / f"src/researchbase/{layer}/authorship.py").read_text())
        for node in ast.walk(tree):
            imports = (
                [node.module or ""]
                if isinstance(node, ast.ImportFrom)
                else [n.name for n in node.names]
                if isinstance(node, ast.Import)
                else []
            )
            assert not any(
                m.startswith(
                    ("sqlalchemy", "fastapi", "typer", "researchbase.persistence", "codex")
                )
                for m in imports
            )


def test_exact_four_methods_and_no_future_transport():
    source = (ROOT / "src/researchbase/application/authorship.py").read_text()
    service = next(
        n
        for n in ast.parse(source).body
        if isinstance(n, ast.ClassDef) and n.name == "AuthorshipService"
    )
    public = {
        n.name
        for n in service.body
        if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")
    }
    assert public == {
        "record_contribution",
        "create_authorship_snapshot",
        "get_contribution",
        "get_authorship_snapshot",
    }
    assert "ExternalEffect" not in source
    assert (ROOT / "src/researchbase/application/prepared_submission.py").exists()
    assert not (ROOT / "src/researchbase/cli/commands/authorship.py").exists()
    assert "authorship" not in (ROOT / "src/researchbase/api/routes.py").read_text()


def test_ports_uow_and_admitted_tables_only():
    ports = (ROOT / "src/researchbase/application/ports.py").read_text()
    uow = (ROOT / "src/researchbase/persistence/uow.py").read_text()
    assert "class AuthorshipRepository(Protocol)" in ports
    assert "authorship: AuthorshipRepository" in ports
    assert "SqlAlchemyAuthorshipRepository(self._session)" in uow
    migration = (ROOT / "migrations/versions/0046_pr2_17_authorship_preparation.py").read_text()
    tree = ast.parse(migration)
    tables = next(
        ast.literal_eval(n.value)
        for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "TABLES" for t in n.targets)
    )
    assert set(tables) == {
        "contribution_records",
        "authorship_snapshots",
        "authorship_snapshot_authors",
        "authorship_snapshot_corresponding_authors",
        "authorship_snapshot_equal_groups",
        "authorship_snapshot_contributions",
    }
    assert "ON DELETE CASCADE" not in migration
    assert "target_type" not in migration and "target_id" not in migration
