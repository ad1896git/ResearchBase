import ast
from dataclasses import fields
from pathlib import Path

from researchbase.agent_runtime.application.execution_contracts import (
    AgentExecutionDTO,
    CreateAgentExecution,
)
from researchbase.agent_runtime.domain.research_task import TaskStatus

ROOT = Path(__file__).resolve().parents[2]


def test_intent_only_application_boundary():
    domain = (ROOT / "src/researchbase/agent_runtime/domain/agent_execution.py").read_text()
    imports = [
        node
        for node in ast.walk(ast.parse(domain))
        if isinstance(node, ast.Import | ast.ImportFrom)
    ]
    assert all(
        not any(
            term in ast.unparse(node)
            for term in ("sqlalchemy", "fastapi", "typer", "persistence", "openai", "langgraph")
        )
        for node in imports
    )
    service = (ROOT / "src/researchbase/agent_runtime/application/agent_executions.py").read_text()
    assert "self._factory()" in service and "begin_formal_read()" in service
    assert "begin_execution_intent()" in service
    assert "authorize_agent_project(repo," in service
    assert "AgentVersionService" not in service
    assert "._authorize(" not in service
    assert not any(
        term in service
        for term in (
            "sqlalchemy",
            "Session",
            "execution_enabled",
            "capability_invocations",
            "producing_execution_id",
            "AGENT_POLICY",
            "transition_agent_execution",
        )
    )
    migration = (ROOT / "migrations/versions/0081_agent_execution_intents.py").read_text()
    assert migration.count("CREATE TABLE ") == 2
    assert "SECURITY DEFINER" not in migration
    assert not {"target_type", "target_id", "controller_actor_id", "result_promotion_id"} & {
        f.name for f in fields(AgentExecutionDTO)
    }
    assert {f.name for f in fields(CreateAgentExecution)} == {
        "execution_id",
        "agent_version_id",
        "research_task_id",
        "research_task_step_id",
        "expected_task_revision",
        "harness_artifact_version_id",
    }
    assert {status.value for status in TaskStatus} == {"CREATED", "PLANNING", "CANCELLED"}


def test_inert_persistence_metadata_matches_intent_values():
    from typing import cast

    from sqlalchemy import Table

    from researchbase.agent_runtime.application.execution_contracts import AgentExecutionEventDTO
    from researchbase.persistence.models import (
        AgentCommandReceiptModel,
        AgentExecutionEventModel,
        AgentExecutionInstanceModel,
    )

    intent = cast(Table, AgentExecutionInstanceModel.__table__)
    event = cast(Table, AgentExecutionEventModel.__table__)
    assert set(intent.columns.keys()) == {f.name for f in fields(AgentExecutionDTO)} - {"events"}
    assert set(event.columns.keys()) == {f.name for f in fields(AgentExecutionEventDTO)}
    assert all(
        fk.ondelete == "RESTRICT"
        for table in (intent, event)
        for fk in table.foreign_key_constraints
    )
    assert {"result_execution_id", "result_execution_event_id"} <= set(
        AgentCommandReceiptModel.__table__.columns.keys()
    )
    assert all(
        c.default is None and c.server_default is None
        for table in (intent, event)
        for c in table.columns
    )
