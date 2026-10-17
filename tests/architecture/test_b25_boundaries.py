"""B25 remains an Application projection with one caller-owned snapshot."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_queries_have_one_uow_and_no_writes_or_nested_public_queries():
    source = (ROOT / "src/researchbase/application/manuscript_validity.py").read_text()
    tree = ast.parse(source)
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    attrs = [node.func.attr for node in calls if isinstance(node.func, ast.Attribute)]
    assert attrs.count("_factory") == 1
    assert "prepare_read" in attrs and "enable_revision_action_snapshot_reads" in attrs
    assert not set(attrs) & {
        "commit",
        "prepare_write",
        "lock_project",
        "lock_publication",
        "trace",
        "read",
        "get_manuscript_version",
        "collect_manuscript_review_basis",
    }
    assert not any(
        token in source.upper()
        for token in ("LOCK TABLE", "PG_ADVISORY", "FOR UPDATE", "FOR SHARE")
    )
    assert "sqlalchemy" not in source and "fastapi" not in source and "typer" not in source


def test_audit_selectors_are_bounded_nonlocking():
    tree = ast.parse(
        (ROOT / "src/researchbase/persistence/internal_review_repository.py").read_text()
    )
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in {
            "scoped_reviews",
            "audit_issues",
            "audit_issue_events",
        }:
            source = ast.unparse(node).upper()
            assert "LIMIT 10001" in source
            assert not any(
                token in source for token in ("LOCK TABLE", "FOR SHARE", "FOR UPDATE", "ADVISORY")
            )


def test_b25_has_no_canonical_schema_or_migration():
    assert not list((ROOT / "migrations/versions").glob("*b25*"))
    assert not list((ROOT / "src/researchbase/domain").glob("*manuscript_validity*"))
    source = (ROOT / "src/researchbase/application/manuscript_validity.py").read_text()
    assert '"UNSUPPORTED_CLAIM"' in source
    assert "validity_projection_in_uow" not in source  # owner verifier supplies projections
