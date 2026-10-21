"""PR-17R proof that Phase 1 keeps one transport-independent Application boundary."""

from __future__ import annotations

import ast
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import get_type_hints

ROOT = Path(__file__).parents[2]
SOURCE = ROOT / "src" / "researchbase"
APPLICATION = SOURCE / "application"
DOMAIN = SOURCE / "domain"
DTO = APPLICATION / "dto.py"
API = SOURCE / "api"
CLI = SOURCE / "cli"


def _python_files(path: Path) -> list[Path]:
    return sorted(path.rglob("*.py"))


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.add(node.module or "")
    return modules


def test_domain_and_application_are_transport_independent() -> None:
    for path in _python_files(DOMAIN) + _python_files(APPLICATION):
        imported = _imports(path)
        assert not any(
            module == forbidden or module.startswith(f"{forbidden}.")
            for module in imported
            for forbidden in ("fastapi", "typer", "researchbase.api", "researchbase.cli")
        ), path


def test_http_and_cli_adapters_call_application_directly_without_peer_coupling() -> None:
    http_source = "\n".join(path.read_text() for path in _python_files(API))
    cli_source = "\n".join(path.read_text() for path in _python_files(CLI))

    assert "application = _services(request).application" in http_source
    assert "_legacy_write(" in http_source
    assert "runtime.services.application." in cli_source
    assert "researchbase.cli" not in http_source
    assert "researchbase.api" not in cli_source
    for forbidden in ("httpx", "requests", "urllib.request", "subprocess", "os.system"):
        assert forbidden not in cli_source


def test_agent_ready_application_writes_share_the_canonical_result_contract() -> None:
    from researchbase.application.commands import _WRITE_COMMAND_NAMES, ApplicationService
    from researchbase.application.dto import WriteResult

    for name in _WRITE_COMMAND_NAMES:
        method = getattr(ApplicationService, name)
        assert get_type_hints(method)["return"] is WriteResult, name


def test_transport_adapters_do_not_own_persistence_or_business_transaction_semantics() -> None:
    adapter_source = "\n".join(
        path.read_text()
        for path in _python_files(API) + _python_files(CLI)
        if path != API / "app.py" and path != CLI / "composition.py"
    ).lower()

    for forbidden in ("sqlalchemy", "session", ".commit(", ".flush("):
        assert forbidden not in adapter_source


def test_application_dtos_are_frozen_dataclasses_without_orm_or_session_dependencies() -> None:
    source = DTO.read_text()
    assert "sqlalchemy" not in source.lower()
    assert "session" not in source.lower()
    assert "researchbase.persistence" not in source

    tree = ast.parse(source, filename=str(DTO))
    dto_names = {
        node.name
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name.endswith("ReadModel")
    }
    assert dto_names
    dto_module = __import__("researchbase.application.dto", fromlist=sorted(dto_names))
    for name in dto_names:
        model = getattr(dto_module, name)
        assert is_dataclass(model)
        params = getattr(model, "__dataclass_params__", None)
        assert params is not None
        assert params.frozen is True
        assert all("Session" not in str(field.type) for field in fields(model))


def test_no_agent_runtime_or_workflow_engine_is_present_in_phase1_source() -> None:
    forbidden_classes: list[tuple[Path, str]] = []
    for path in _python_files(SOURCE):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            # ADR-0023 S1 admits only these identity/version modules and mappings.
            admitted = {
                "agent_runtime/domain/agent_version.py",
                "agent_runtime/domain/harness_manifest.py",
                "agent_runtime/application/agent_contracts.py",
                "agent_runtime/application/agent_versions.py",
                "agent_runtime/ports/agent_repository.py",
                "persistence/agent_version_repository.py",
                "api/agent_routes.py",
            }
            if path.relative_to(SOURCE).as_posix() in admitted or (
                path == SOURCE / "persistence/models.py"
                and node.name
                in {
                    "AgentVersionModel",
                    "AgentAvailabilityModel",
                    "AgentCommandReceiptModel",
                    "AgentAvailabilityEventModel",
                }
            ):
                continue
            if (
                "agent" in node.name.lower()
                or "workflow" in node.name.lower()
                or node.name in {"DecisionRecord", "DecisionBasis", "ApprovalRequest"}
            ):
                forbidden_classes.append((path, node.name))

    assert forbidden_classes == []
    assert not (SOURCE / "agent").exists()
    assert not (SOURCE / "workflow").exists()
