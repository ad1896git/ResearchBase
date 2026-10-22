"""PR3-03 dependency and typed ownership guards; no PostgreSQL correctness claim."""

import ast
import importlib.util
import inspect
import sys
import tomllib
from dataclasses import fields
from pathlib import Path

import pytest
from sqlalchemy import JSON

from researchbase.agent_runtime.application.gateway_contracts import (
    AgentExecutionContext,
    CapabilityInvocationRead,
    GatewayCommand,
)
from researchbase.agent_runtime.domain.research_task import TaskStatus
from researchbase.agent_runtime.ports.capability_gateway import CapabilityGateway
from researchbase.persistence.models import Base

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "src/researchbase/agent_runtime"
GATEWAY_TABLES = {
    "agent_tool_policies",
    "agent_tool_policy_permissions",
    "capability_invocations",
    "capability_invocation_refs",
    "capability_invocation_events",
}
# An allowlist prevents an unlisted SDK from evading a vendor-name blacklist.
INTERNAL = (
    "researchbase.agent_runtime",
    "researchbase.foundation",
    "researchbase.domain.phase2_identity",
    "researchbase.application",
)
EFFECT_MODULES = {
    "asyncio",
    "builtins",
    "concurrent",
    "ctypes",
    "http",
    "importlib",
    "io",
    "multiprocessing",
    "os",
    "pathlib",
    "pickle",
    "queue",
    "shutil",
    "socket",
    "subprocess",
    "tempfile",
    "threading",
    "urllib",
}


def boundary_violations(source: str, module: str, *, domain: bool = False) -> list[str]:
    """Resolve both import forms, aliases and relative dependencies before checking."""
    violations = []
    for node in ast.walk(ast.parse(source)):
        names = []
        line = 0
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
            line = node.lineno
        elif isinstance(node, ast.ImportFrom):
            line = node.lineno
            name = node.module or ""
            if node.level:
                name = importlib.util.resolve_name(
                    "." * node.level + name, module.rpartition(".")[0]
                )
            names = [name, *(name + "." + alias.name for alias in node.names)]
        for name in names:
            root = name.split(".")[0]
            if root == "researchbase":
                allowed = (
                    ("researchbase.agent_runtime.domain", "researchbase.foundation")
                    if domain
                    else INTERNAL
                )
                if not any(name == p or name.startswith(p + ".") for p in allowed):
                    violations.append(f"{line}: forbidden dependency {name}")
            elif root not in sys.stdlib_module_names or root in EFFECT_MODULES:
                violations.append(f"{line}: forbidden dependency {name}")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in {"__import__", "eval", "exec", "open", "compile"}:
                violations.append(f"{node.lineno}: dynamic effect {node.func.id}")
    return violations


def test_runtime_import_dependencies_exclude_persistence_transport_sdk_and_effects():
    checked = 0
    for path in RUNTIME.rglob("*.py"):
        module = ".".join(path.relative_to(ROOT / "src").with_suffix("").parts)
        violations = boundary_violations(
            path.read_text(), module, domain=path.parent.name == "domain"
        )
        assert not violations, (path, violations)
        checked += 1
    assert checked >= 20


@pytest.mark.parametrize(
    "source",
    [
        "import sqlalchemy as innocent",
        "from fastapi import FastAPI",
        "from researchbase.persistence import uow",
        "from ...persistence import models",
        "import unknown_provider_sdk",
        "import subprocess as runner",
        "from pathlib import Path",
        "__import__('researchbase.persistence')",
        "open('credentials')",
    ],
)
def test_boundary_scanner_detects_deliberate_violation(source):
    assert boundary_violations(source, "researchbase.agent_runtime.application.violation")


def test_domain_scanner_rejects_application_and_ports():
    for source in (
        "from ..application import capability_gateway",
        "from researchbase.agent_runtime.ports import gateway_repository",
    ):
        assert boundary_violations(
            source, "researchbase.agent_runtime.domain.violation", domain=True
        )


def test_gateway_tables_use_concrete_refs_and_own_no_scientific_json_state():
    refs = Base.metadata.tables["capability_invocation_refs"]
    concrete = {
        "research_question_version_id",
        "hypothesis_version_id",
        "claim_version_id",
        "source_version_id",
        "artifact_version_id",
        "manuscript_version_id",
    }
    assert concrete <= set(refs.columns.keys())
    foreign_columns = {c.name for fk in refs.foreign_key_constraints for c in fk.columns}
    assert concrete <= foreign_columns
    for name in GATEWAY_TABLES:
        table = Base.metadata.tables[name]
        assert not any(isinstance(column.type, JSON) for column in table.columns)
        assert not {"target_type", "target_id", "execution_id", "scientific_validity"} & set(
            table.columns.keys()
        )
        assert all(fk.ondelete == "RESTRICT" for fk in table.foreign_key_constraints)
    assert set(refs.columns.keys()) == {
        "id",
        "project_id",
        "research_task_id",
        "invocation_id",
        "receipt_id",
        "direction",
        "content_hash",
        "hash_scheme",
        *concrete,
    }


def test_public_port_and_values_do_not_admit_credentials_execution_or_promotion():
    assert list(inspect.signature(CapabilityGateway.invoke).parameters) == [
        "self",
        "request",
        "context",
    ]
    assert {field.name for field in fields(GatewayCommand)} == {
        "project_id",
        "task_id",
        "command_id",
        "expected_row_version",
        "command_name",
        "arguments",
    }
    for kind in (GatewayCommand, AgentExecutionContext, CapabilityInvocationRead):
        assert not {
            "execution_id",
            "credentials",
            "provider",
            "approved",
            "scientific_validity",
        } & {field.name for field in fields(kind)}
    assert {state.value for state in TaskStatus} == {"CREATED", "PLANNING", "CANCELLED"}
    assert next(f for f in fields(CapabilityInvocationRead) if f.name == "execution_enabled")


def test_runtime_dependencies_remain_the_accepted_set():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert set(project["project"]["dependencies"]) == {
        "alembic>=1.16,<2",
        "fastapi>=0.141,<0.142",
        "idna>=3.10,<4",
        "psycopg[binary]>=3.2,<4",
        "pydantic>=2.11,<3",
        "sqlalchemy>=2.0,<2.1",
        "typer>=0.27,<0.28",
    }
