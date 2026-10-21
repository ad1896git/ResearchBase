"""B23 keeps typed persistence and the common Application boundary."""

import ast
import inspect
from pathlib import Path

from researchbase.application.internal_review import InternalReviewService
from researchbase.application.revision_action import RevisionActionService
from researchbase.persistence.internal_review_repository import (
    B23_SNAPSHOT_TABLES,
    SqlAlchemyInternalReviewRepository,
)
from researchbase.persistence.novelty_repository import N

ROOT = Path(__file__).resolve().parents[2]


def test_fixed_inventory_and_first_statement():
    assert B23_SNAPSHOT_TABLES == N == tuple(sorted(N))
    assert not set(N) & {
        "novelty_assessments",
        "prior_art_relations",
        "internal_review_records",
        "review_issues",
        "review_issue_events",
        "revision_actions",
        "revision_action_re_reviews",
    }
    source = inspect.getsource(SqlAlchemyInternalReviewRepository.prepare_novelty_write)
    assert (
        source.index("IN SHARE MODE")
        < source.index("IN ROW EXCLUSIVE MODE")
        < source.index("SET LOCAL")
        < source.index("pg_advisory_xact_lock")
    )


def test_lock_free_exact_read_and_separate_new_shape():
    for method in (
        InternalReviewService._novelty_view,
        RevisionActionService.read_novelty_re_review,
    ):
        source = inspect.getsource(method)
        assert "FOR UPDATE" not in source and "FOR SHARE" not in source and "advisory" not in source
    assert "begin_formal_read" in inspect.getsource(RevisionActionService.read_novelty_re_review)
    assert "NOVELTY_REASSESSMENT" not in inspect.getsource(
        __import__(
            "researchbase.domain.revision_action", fromlist=["revision_action_material"]
        ).revision_action_material
    )


def test_no_new_table_or_domain_adapter_import():
    migration = (ROOT / "migrations/versions/0071_b23_novelty_review.py").read_text()
    assert "CREATE TABLE" not in migration
    for name in ("internal_review", "revision_action"):
        tree = ast.parse((ROOT / f"src/researchbase/domain/{name}.py").read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not any(
                    (node.module or "").startswith(p)
                    for p in (
                        "sqlalchemy",
                        "fastapi",
                        "typer",
                        "researchbase.persistence",
                        "researchbase.application",
                    )
                )
