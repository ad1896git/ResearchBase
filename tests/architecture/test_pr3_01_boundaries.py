"""Planning canonical ownership, imports, first-SHARE and frozen DDL inventory."""

import ast
from pathlib import Path

from researchbase.persistence.research_task_repository import SHARE_SQL, SHARE_TABLES

ROOT = Path(__file__).resolve().parents[2]


def test_runtime_cannot_import_persistence_or_transport_or_vendor():
    root = ROOT / "src/researchbase/agent_runtime"
    forbidden = (
        "sqlalchemy",
        "fastapi",
        "typer",
        "psycopg",
        "researchbase.persistence",
        "researchbase.api",
        "researchbase.cli",
        "researchbase.local_identity",
        "openai",
        "anthropic",
        "langgraph",
        "celery",
        "redis",
    )
    for file in root.rglob("*.py"):
        for node in ast.walk(ast.parse(file.read_text())):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            assert not any(
                name == prefix or name.startswith(prefix + ".")
                for name in names
                for prefix in forbidden
            ), file


def test_human_and_agent_share_application_and_closed_dtos():
    text = (ROOT / "src/researchbase/agent_runtime/application/research_task.py").read_text()
    assert "VerifiedPrincipal" in text and "ResearchTaskService" in text
    assert "begin_formal_read()" in text and "begin_research_task()" in text
    assert "principal.actor_id" in text and "requested_by" in text
    assert "actor_type" not in text  # No synthetic Human attribution for Agent callers.
    for file in ("src/researchbase/api/app.py", "src/researchbase/cli/composition.py"):
        assert "ResearchTaskService(" in (ROOT / file).read_text()


def test_graph_is_reconstructable_without_framework_or_json_core_refs():
    migration = (ROOT / "migrations/versions/0077_research_task_graph.py").read_text()
    assert migration.count("CREATE TABLE ") == 10
    assert migration.count("CREATE FUNCTION pr301_") == 14
    assert migration.count("CREATE CONSTRAINT TRIGGER ") == 4
    assert "pr301_history_complete" not in migration
    assert "pg_current_xact_id()::xid" in migration
    assert "current_setting(" not in migration
    assert " JSON" not in migration and "target_type" not in migration
    for forbidden in (
        "CREATE TABLE runs",
        "CREATE TABLE claims",
        "CREATE TABLE agent_executions",
        "budget_policy_id",
        "outbox",
        "provider",
    ):
        assert forbidden not in migration
    assert 'down_revision = "0076_agent_runtime_bootstrap"' in migration


def test_literal_first_share_inventory():
    assert SHARE_TABLES == (
        "actor_subject_bindings",
        "actors",
        "artifact_versions",
        "artifacts",
        "claim_versions",
        "claims",
        "hypothesis_versions",
        "hypotheses",
        "literature_source_project_links",
        "literature_sources",
        "manuscript_versions",
        "project_memberships",
        "project_role_assignments",
        "projects",
        "publications",
        "research_question_versions",
        "research_questions",
        "source_versions",
    )
    assert SHARE_SQL == "LOCK TABLE " + ", ".join(SHARE_TABLES) + " IN SHARE MODE"
    assert not any(name.startswith("research_task") for name in SHARE_TABLES)
