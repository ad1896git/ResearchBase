"""R2 may compose only public same-UoW owning readers after scoped preflight."""

import ast
from dataclasses import fields
from pathlib import Path

from researchbase.agent_runtime.application.context_contracts import (
    CanonicalContext,
    PromotionContextValidation,
)

ROOT = Path(__file__).resolve().parents[2]


def test_context_adapter_owning_imports_are_public_and_bounded():
    path = ROOT / "src/researchbase/persistence/context_repository.py"
    tree = ast.parse(path.read_text())
    allowed = {
        "researchbase.agent_runtime.application.context_contracts",
        "researchbase.agent_runtime.application.contracts",
        "researchbase.agent_runtime.application.research_task",
        "researchbase.application.governance_queries",
        "researchbase.application.manuscript_freeze",
        "researchbase.application.manuscript_scientific_trace",
        "researchbase.application.provenance_queries",
        "researchbase.application.source_version",
    }
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module is not None
        and (
            node.module.startswith("researchbase.application")
            or node.module.startswith("researchbase.agent_runtime.application")
        )
    }
    assert imports == allowed
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert all(not name.name.startswith("_") for name in node.names)
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Attribute):
            if node.value.attr in {"_freeze", "_provenance", "_governance"}:
                assert not node.attr.startswith("_"), ast.unparse(node)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in {
                "get_run_provenance",
                "trace_claim_to_runs",
                "get_manuscript_version",
                "commit",
                "flush",
                "lock_write",
                "put_verified",
                "begin_formal_read",
            }


def test_loader_has_public_read_admission_without_command_factory_or_private_principal():
    path = ROOT / "src/researchbase/agent_runtime/application/canonical_context.py"
    source = path.read_text()
    tree = ast.parse(source)
    assert "TaskContextAdmission(credentials)" in source
    assert "authorize_context_read" in source
    assert "ResearchTaskService" not in source
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            assert node.attr != "_principal"
    assert source.count("uow.begin_formal_read()") == 1
    assert source.count("uow.task_safety.snapshot_at()") == 1


def test_real_composition_binds_context_store_without_adding_transport_routes():
    for name in ("api/app.py", "cli/composition.py"):
        source = (ROOT / "src/researchbase" / name).read_text()
        assert "context_artifact_store=store" in source
        assert "canonical_context=CanonicalContextService(uow_factory, credentials)" in source


def test_read_services_have_no_transport_vendor_sql_or_write_calls():
    for name in ("canonical_context", "task_memory", "promotion_context"):
        tree = ast.parse(
            (ROOT / f"src/researchbase/agent_runtime/application/{name}.py").read_text()
        )
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert not any(
                    token in (node.module or "")
                    for token in (
                        "sqlalchemy",
                        "persistence",
                        "fastapi",
                        "typer",
                        "openai",
                        "anthropic",
                    )
                )
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in {
                    "commit",
                    "flush",
                    "lock_write",
                    "put_verified",
                    "execute",
                    "begin_nested",
                }
        assert any(
            isinstance(n, ast.Attribute) and n.attr == "begin_formal_read" for n in ast.walk(tree)
        )


def test_reviewer_reconstruction_has_no_memory_and_results_grant_no_actions():
    assert not any(
        "memory" in field.name or "scratchpad" in field.name for field in fields(CanonicalContext)
    )
    for name in (
        "promotion_enabled",
        "execution_enabled",
        "provider_disclosure_granted",
        "producer_provenance_verified",
    ):
        assert (
            next(f for f in fields(PromotionContextValidation) if f.name == name).default is False
        )
    assert vars(CanonicalContext)["__dataclass_params__"].frozen
    assert vars(PromotionContextValidation)["__dataclass_params__"].frozen
