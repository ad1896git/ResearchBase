import ast
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

ROOT = Path(__file__).resolve().parents[2]


def test_authorized_head_and_s1_only():
    scripts = ScriptDirectory.from_config(Config("alembic.ini"))
    assert scripts.get_heads() == ["0082_experiment_search_core"]
    assert (
        scripts.get_revision("0079_agent_identity_versions").down_revision
        == "0078_task_safety_policies"
    )
    migration = (ROOT / "migrations/versions/0079_agent_identity_versions.py").read_text()
    assert migration.count("CREATE TABLE ") == 4
    assert migration.count("CREATE FUNCTION pr302_") == 8
    assert migration.count("CREATE CONSTRAINT TRIGGER ") == 1
    assert "xmin = pg_current_xact_id()::xid" in migration
    assert "SECURITY DEFINER" not in migration
    assert "CREATE TABLE agent_execution" not in migration


def test_domain_pure_and_common_boundary():
    for name in ("agent_version.py", "harness_manifest.py"):
        source = (ROOT / "src/researchbase/agent_runtime/domain" / name).read_text()
        ast.parse(source)
        assert all(
            term not in source
            for term in ("sqlalchemy", "fastapi", "typer", "psycopg", "import openai")
        )
    source = (ROOT / "src/researchbase/agent_runtime/application/agent_versions.py").read_text()
    assert "begin_formal_read()" in source and "begin_agent_command()" in source
    assert "self._factory()" in source
