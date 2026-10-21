"""B15 remains an Application-only typed local preparation slice."""

import ast
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from researchbase.persistence.prepared_submission_repository import B15_SNAPSHOT_TABLES

ROOT = Path(__file__).resolve().parents[2]


def test_domain_and_application_keep_layer_boundaries():
    domain = (ROOT / "src/researchbase/domain/prepared_submission.py").read_text()
    application = (ROOT / "src/researchbase/application/prepared_submission.py").read_text()
    for forbidden in ("sqlalchemy", "fastapi", "typer", "researchbase.persistence"):
        assert forbidden not in domain and forbidden not in application
    assert "self._authorship.get_" not in application
    assert "self._authorship.create_" not in application
    assert "enable_revision_action_snapshot_reads" in application
    for path in ("api/routes.py", "cli/commands/governance.py"):
        assert "PreparedSubmissionService" not in (ROOT / "src/researchbase" / path).read_text()


def test_literal_inventory_excludes_output_tables_and_is_complete():
    assert B15_SNAPSHOT_TABLES == tuple(sorted(set(B15_SNAPSHOT_TABLES)))
    assert {
        "publications",
        "manuscript_versions",
        "authorship_snapshots",
        "contribution_records",
        "authorship_snapshot_authors",
    } <= set(B15_SNAPSHOT_TABLES)
    assert not {
        "prepared_submission_versions",
        "author_consents",
        "prepared_submission_manifest_items",
        "prepared_submission_events",
    } & set(B15_SNAPSHOT_TABLES)


def test_new_forward_revision_preserves_closed_lifecycle_and_native_seal():
    scripts = ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini")))
    assert (
        scripts.get_revision("0060_b15_package_preparation").down_revision
        == "0059_b13_grant_consumption"
    )
    source = (ROOT / "migrations/versions/0060_b15_package_preparation.py").read_text()
    assert "ON DELETE CASCADE" not in source
    assert "xmin=pg_current_xact_id()::xid" in source
    assert "ck_b15_package_status" in source and "ck_b15_manifest_s2" in source
    assert "JSONB" not in source and "CREATE TABLE approval" not in source


def test_reads_do_not_open_write_uow_or_mutate():
    source = (ROOT / "src/researchbase/application/prepared_submission.py").read_text()
    tree = ast.parse(source)
    read = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_read")
    calls = [
        n.func.attr
        for n in ast.walk(read)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
    ]
    assert "begin_formal_read" in calls
    assert not {
        "prepare_write",
        "commit",
        "force_constraints",
        "coordinate",
        "withdraw",
        "insert_item",
    } & set(calls)
