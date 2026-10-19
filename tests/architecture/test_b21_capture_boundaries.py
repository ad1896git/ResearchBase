"""B21 extends the literature assessment without adding a persistence owner."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_one_typed_relation_and_no_shared_guard_replacement():
    source = (ROOT / "migrations/versions/0068_b21_unresolved_capture.py").read_text()
    assert source.count("CREATE TABLE ") == 1
    assert "CREATE TABLE search_coverage_resolutions" in source
    assert "CREATE OR REPLACE" not in source
    assert "CREATE FUNCTION pr218_" not in source
    assert "pg_current_xact_id()::xid" in source
    assert "xmin::" not in source
    assert "JSONB" not in source
    assert "ON DELETE CASCADE" not in source
    assert "ADD COLUMN material_version" in source


def test_domain_and_transports_keep_application_boundary():
    domain = ast.parse((ROOT / "src/researchbase/domain/novelty.py").read_text())
    for node in ast.walk(domain):
        if isinstance(node, ast.ImportFrom):
            assert not any(
                x in (node.module or "")
                for x in ("sqlalchemy", "fastapi", "typer", "persistence", "application")
            )
    app = (ROOT / "src/researchbase/application/novelty.py").read_text()
    assert "from sqlalchemy" not in app
    assert "resolution_hash(row)" in app
    for file in ("api/routes.py", "cli/commands/literature.py"):
        transport = (ROOT / "src/researchbase" / file).read_text()
        assert "INSERT INTO search_coverage" not in transport
        assert "INSERT INTO search_coverage_resolutions" not in transport
    assert "def coverage_material(" in (ROOT / "src/researchbase/domain/novelty.py").read_text()
