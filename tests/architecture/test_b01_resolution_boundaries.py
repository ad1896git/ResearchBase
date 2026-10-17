"""B01 owns admission, never provider orchestration or scientific evidence."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_domain_has_no_adapter_or_application_dependencies():
    tree = ast.parse((ROOT / "src/researchbase/domain/search_result_resolution.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert not any(
                word in (node.module or "")
                for word in (
                    "application",
                    "persistence",
                    "sqlalchemy",
                    "fastapi",
                    "typer",
                    "adapters",
                )
            )


def test_application_has_only_two_public_operations_and_shared_composition():
    source = (ROOT / "src/researchbase/application/search_result_resolution.py").read_text()
    tree = ast.parse(source)
    service = next(
        n
        for n in tree.body
        if isinstance(n, ast.ClassDef) and n.name == "SearchResultResolutionService"
    )
    assert {
        n.name
        for n in service.body
        if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")
    } == {"record_search_result_resolution", "get_search_result_resolution"}
    for forbidden in (
        "register_literature_source",
        "verify_source_identifier(",
        "CreateSourceVersion",
        "import_document",
        "extract(",
        "provider.search",
        "sqlalchemy",
    ):
        assert forbidden not in source
    assert (
        "SearchResultResolutionService("
        in (ROOT / "src/researchbase/cli/composition.py").read_text()
    )
    assert not any(
        "SearchResultResolutionService" in p.read_text()
        for p in (ROOT / "src/researchbase/api").rglob("*.py")
    )


def test_only_forward_ddl_is_existing_relation_constraint_trigger():
    ddl = (ROOT / "migrations/versions/0050_b01_resolution_admission.py").read_text().lower()
    assert "create table" not in ddl and "create index" not in ddl
    assert "deferrable initially deferred" in ddl
    assert "execute function m2_check_closure()" in ddl
    assert "drop trigger b01_resolution_closure_at_commit" in ddl
    repo = (
        ROOT / "src/researchbase/persistence/search_result_resolution_repository.py"
    ).read_text()
    assert "for update" not in repo.lower()
    assert "insert_resolution(row)" in repo
    assert "create" not in repo.lower()
