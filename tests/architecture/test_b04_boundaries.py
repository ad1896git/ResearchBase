"""B04 owns a seal suffix, with explicit dependency and transaction boundaries."""

import ast
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from researchbase.persistence.manuscript_freeze_repository import B04_SHARE_SQL, B04_SNAPSHOT_TABLES

ROOT = Path(__file__).resolve().parents[2]


def test_literal_inventory_matches_approved_guide():
    guide = (ROOT / "docs/proposals/B04_Manuscript_Freeze_Contract_DRAFT.md").read_text()
    literal = guide.split(
        "actor_subject_bindings actors artifact_versions artifacts audit_findings", 1
    )[1].split("```", 1)[0]
    expected = (
        "actor_subject_bindings actors artifact_versions artifacts audit_findings" + literal
    ).split()
    assert tuple(sorted(expected)) == B04_SNAPSHOT_TABLES
    assert B04_SHARE_SQL == "LOCK TABLE " + ",".join(sorted(expected)) + " IN SHARE MODE"
    assert (
        "publications" not in B04_SNAPSHOT_TABLES
        and "manuscript_versions" not in B04_SNAPSHOT_TABLES
    )


def test_domain_and_application_do_not_import_persistence():
    for relative in ["domain/manuscript.py", "application/manuscript_freeze.py"]:
        tree = ast.parse((ROOT / "src/researchbase" / relative).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not any(
                    x in (node.module or "")
                    for x in ["sqlalchemy", "fastapi", "typer", "persistence"]
                )


def test_one_migration_and_no_new_schema_or_transport():
    scripts = ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini")))
    assert scripts.get_heads() == ["0078_task_safety_policies"]
    assert (
        scripts.get_revision("0048_b04_manuscript_freeze").down_revision
        == "0047_pr2_18_novelty_prior_art"
    )
    ddl = (ROOT / "migrations/versions/0048_b04_manuscript_freeze.py").read_text().lower()
    assert "create table" not in ddl
    for directory in ["api", "cli"]:
        assert not any(
            "freeze_manuscript_version" in p.read_text()
            for p in (ROOT / "src/researchbase" / directory).rglob("*.py")
        )


def test_frozen_traces_use_same_uow_verifier_and_read_protocol():
    for name in ["manuscript_placement.py", "manuscript_scientific_trace.py"]:
        tree = ast.parse((ROOT / "src/researchbase/application" / name).read_text())
        traces = [x for x in ast.walk(tree) if isinstance(x, ast.FunctionDef) and x.name == "trace"]
        for trace in traces:
            code = ast.unparse(trace)
            assert ".prepare_read()" in code and ".verify_in_uow(" in code
            assert "._authorize(" not in code and ".lock_project(" not in code
            assert code.count("with self._factory()") == 1
            assert ".get_manuscript_version(" not in code
