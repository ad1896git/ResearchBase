"""B06 retains concrete result FKs and the scientific/Application boundary."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_b06_domain_has_no_persistence_or_adapter_dependency():
    tree = ast.parse((ROOT / "src/researchbase/domain/revision_action.py").read_text())
    imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    assert not any(
        name
        and any(
            part in name
            for part in ("persistence", "sqlalchemy", "fastapi", "typer", "application")
        )
        for name in imports
    )


def test_forward_migration_changes_guards_only_and_keeps_existing_history():
    ddl = (ROOT / "migrations/versions/0051_b06_revision_action.py").read_text()
    assert "CREATE TABLE" not in ddl and "ALTER TABLE" not in ddl
    assert "DELETE FROM" not in ddl and "UPDATE revision_actions" not in ddl
    assert "DEFERRABLE INITIALLY DEFERRED" in ddl
    assert "new revision history cannot be stranded" in ddl
    guard = ddl.split("CREATE OR REPLACE FUNCTION pr215_revision_guard()", 1)[1].split(
        "_RESTORE", 1
    )[0]
    assert "FROM claim_versions WHERE" not in guard
    assert "FOR UPDATE" in guard and "id=NEW.supersedes_revision_action_id FOR UPDATE" in guard
    assert "LOCK TABLE" in guard


def test_b06_has_no_issue_disposition_or_extra_result_schema():
    application = (ROOT / "src/researchbase/application/revision_action.py").read_text()
    assert "INSERT INTO" not in application and "UPDATE " not in application
    from dataclasses import fields

    from researchbase.application.revision_action import RecordRevisionActionCommand
    from researchbase.domain.revision_action import RESULT_KEYS

    assert {
        x.name for x in fields(RecordRevisionActionCommand) if x.name.startswith("result_")
    } == {key + "_id" for key in RESULT_KEYS}
    assert 'if action == "MANUSCRIPT_CHANGE"' in application
    assert "manuscript revision path deferred" not in application
