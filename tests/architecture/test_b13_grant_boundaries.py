"""B13 finite bindings, literal locks and one canonical review membership owner."""

import ast
import importlib.util
import inspect
from pathlib import Path

from researchbase.application.approval import ApprovalService
from researchbase.application.scientific_conclusion import ScientificConclusionService
from researchbase.persistence.approval_repository import B13_SNAPSHOT_TABLES
from researchbase.persistence.manuscript_freeze_repository import B04_SNAPSHOT_TABLES

ROOT = Path(__file__).resolve().parents[2]


def test_literal_inventory_matches_frozen_guide_and_migration():
    expected = tuple(
        sorted(
            set(B04_SNAPSHOT_TABLES)
            | {
                "manuscript_versions",
                "internal_review_records",
                "review_issues",
                "review_issue_events",
            }
        )
    )
    assert B13_SNAPSHOT_TABLES == expected and "publications" not in expected
    spec = importlib.util.spec_from_file_location(
        "b13", ROOT / "migrations/versions/0059_b13_grant_consumption.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.B13_SNAPSHOT_TABLES == expected


def test_no_transport_effect_or_parallel_review_membership():
    migration = (ROOT / "migrations/versions/0059_b13_grant_consumption.py").read_text()
    assert "CREATE TABLE approval_grant_consumptions" in migration
    assert "CREATE TABLE approval_grant_consumption_reviews" not in migration
    assert "fk_b13_result_conclusion" in migration and "ON DELETE CASCADE" not in migration
    assert "b13_complete_terminal_event" in migration and "uq_b13_one_terminal_event" in migration
    assert "ck_b13_result_tuple" in migration
    for path in ("api/routes.py", "cli/commands/governance.py"):
        source = (ROOT / "src/researchbase" / path).read_text()
        assert "get_grant_consumption" not in source and "consume_grant" not in source


def test_one_application_boundary_and_domain_isolation():
    source = inspect.getsource(ScientificConclusionService.record_internal_scientific_release)
    assert "._release(" in source and "principal, command" in source
    for layer in ("application", "domain"):
        tree = ast.parse((ROOT / f"src/researchbase/{layer}/approval.py").read_text())
        imports = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        assert not any(
            m and m.startswith(("sqlalchemy", "fastapi", "typer", "researchbase.persistence"))
            for m in imports
        )


def test_historical_read_path_never_prepares_a_write_or_commits():
    source = inspect.getsource(ApprovalService._consumption_read)
    assert "_prepare_read" in source
    assert all(
        x not in source for x in ("prepare_write", "lock_grant_chain", "commit(", "terminalize")
    )
    view = inspect.getsource(ApprovalService._receipt_view)
    assert "_gate(" not in view and "verify_receipt" in view
