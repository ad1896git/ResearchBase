"""Safety remains a pure Application boundary with no execution activation."""

import ast
from dataclasses import fields
from pathlib import Path

from researchbase.agent_runtime.application.safety_contracts import SafetyCommand
from researchbase.agent_runtime.domain.research_task import EXECUTION_COMMANDS, TaskStatus

ROOT = Path(__file__).resolve().parents[2]


def test_safety_domain_is_pure_and_public_material_has_no_capability():
    domain = ROOT / "src/researchbase/agent_runtime/domain/task_safety.py"
    tree = ast.parse(domain.read_text())
    imports = [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    assert not any(
        any(
            x in name
            for x in ("sqlalchemy", "persistence", "fastapi", "typer", "provider", "codex")
        )
        for name in imports
    )
    assert {f.name for f in fields(SafetyCommand)} == {
        "project_id",
        "task_id",
        "command_id",
        "expected_row_version",
        "command_name",
        "arguments",
    }
    assert {s.value for s in TaskStatus} == {"CREATED", "PLANNING", "CANCELLED"}
    assert "start_research_task" in EXECUTION_COMMANDS


def test_no_new_deferred_child_scans_or_dependency():
    source = (ROOT / "migrations/versions/0078_task_safety_policies.py").read_text()
    assert source.count("CREATE CONSTRAINT TRIGGER") == 0
    assert source.count("CREATE TRIGGER pr304_") == 8
    assert "SECURITY DEFINER" not in source
    assert "pg_current_xact_id()::xid" in source
    assert source.count("CREATE OR REPLACE FUNCTION pr301_") == 3
    assert "CREATE FUNCTION pr304_validate_safety" in source
    assert "PERFORM pr304_validate_safety(NEW.id)" in source
    app = (ROOT / "src/researchbase/agent_runtime/application/task_safety.py").read_text()
    assert "researchbase.persistence" not in app
    assert ".begin_research_task()" in app and ".begin_formal_read()" in app
    assert "import requests" not in app and "import httpx" not in app
