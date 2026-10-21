from __future__ import annotations

import ast
from importlib.util import resolve_name
from pathlib import Path

from researchbase.application.governance import TargetResolverRegistry
from researchbase.domain.governance import GovernanceTargetType

ROOT = Path(__file__).resolve().parents[2]
PHASE1_GOVERNANCE = frozenset(
    {
        "researchbase.domain.governance",
        "researchbase.application.governance",
        "researchbase.application.governance_queries",
        "researchbase.persistence.governance_repository",
    }
)
DECISION_MODULES = frozenset(
    {
        "researchbase.domain.decision",
        "researchbase.application.decision",
        "researchbase.persistence.decision_repository",
    }
)
PHASE1_TARGETS = frozenset(
    {
        "experiment_spec_version",
        "dataset_snapshot",
        "artifact_version",
        "run",
        "metric_definition_version",
        "measurement",
        "statistical_result",
        "claim_version",
    }
)


def _dotted(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_dotted(node.value)}.{node.attr}"
    return ""


def _dependencies(source: str, module: str, is_package: bool = False) -> set[str]:
    """Static imports, namespace references and literal dynamic imports; no execution."""
    tree = ast.parse(source)
    package = module if is_package else module.rpartition(".")[0]
    dependencies: set[str] = set()
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                dependencies.add(alias.name)
                aliases[alias.asname or alias.name.split(".")[0]] = (
                    alias.name if alias.asname else alias.name.split(".")[0]
                )
        elif isinstance(node, ast.ImportFrom):
            base = resolve_name("." * node.level + (node.module or ""), package)
            dependencies.add(base)
            for alias in node.names:
                child = f"{base}.{alias.name}"
                dependencies.add(child)
                aliases[alias.asname or alias.name] = child
    for node in ast.walk(tree):
        name = _dotted(node.func if isinstance(node, ast.Call) else node)
        head, separator, tail = name.partition(".")
        name = aliases.get(head, head) + (separator + tail if separator else "")
        if name.startswith("researchbase."):
            dependencies.add(name)
        if isinstance(node, ast.Call) and name in {
            "importlib.import_module",
            "builtins.__import__",
            "__import__",
        }:
            keywords = {keyword.arg: keyword.value for keyword in node.keywords}
            target_node = node.args[0] if node.args else keywords.get("name")
            if not isinstance(target_node, ast.Constant) or not isinstance(target_node.value, str):
                continue
            target = target_node.value
            if target.startswith("."):
                # Resolve only an explicit literal package; computed imports are not modeled.
                package_node = node.args[1] if len(node.args) > 1 else keywords.get("package")
                if not isinstance(package_node, ast.Constant):
                    continue
                if not isinstance(package_node.value, str):
                    continue
                target = resolve_name(target, package_node.value)
            dependencies.add(target)
    return dependencies


def _boundary_violations(
    sources: dict[str, str], packages: frozenset[str] = frozenset()
) -> list[str]:
    """Preserve PR-14 ownership, not its historical ban on all later phase source."""
    assert PHASE1_GOVERNANCE <= sources.keys(), "missing protected Phase 1 module"
    violations: list[str] = []
    for module, source in sources.items():
        for forbidden in ("load_any(", "find_any_target", "networkx", "graph cache"):
            if forbidden in source.lower():
                violations.append(f"{module}: {forbidden}")
    for root in sorted(PHASE1_GOVERNANCE):
        pending: list[tuple[str, tuple[str, ...]]] = [(root, (root,))]
        seen: set[str] = set()
        while pending:
            module, route = pending.pop()
            if module in seen:
                continue
            seen.add(module)
            for forbidden in (
                "decisionrecord",
                "approvalrequest",
                "approvaldecision",
                "approvalgrant",
            ):
                if forbidden in sources[module].lower():
                    violations.append(f"{' -> '.join(route)}: {forbidden}")
            dependencies = _dependencies(sources[module], module, module in packages)
            # Importing a child executes its package initializers too, including
            # when only the fully qualified child module appears in the source.
            parents = {
                package
                for package in packages
                if module.startswith(package + ".")
                or any(dependency.startswith(package + ".") for dependency in dependencies)
            }
            for dependency in sorted(dependencies | parents):
                if any(
                    dependency == item or dependency.startswith(item + ".")
                    for item in DECISION_MODULES
                ):
                    violations.append(" -> ".join((*route, dependency)))
                elif dependency in sources:
                    pending.append((dependency, (*route, dependency)))
    return violations


def test_pr14_has_closed_registry_and_no_generic_graph_or_later_governance() -> None:
    assert TargetResolverRegistry().supported_types == frozenset(GovernanceTargetType)
    assert frozenset(kind.value for kind in GovernanceTargetType) == PHASE1_TARGETS
    # Phase 1 spec §20 PR-14 owns governance + queries, while frozen companion20
    # §1 explicitly permits bounded Phase 2 DecisionRecord code. Shared ports and
    # UoW are composition boundaries, not globally excluded from dependency checks.
    source_root = ROOT / "src"
    sources = {}
    packages: set[str] = set()
    for path in sorted((source_root / "researchbase").rglob("*.py")):
        parts = path.relative_to(source_root).with_suffix("").parts
        module = ".".join(parts[:-1] if parts[-1] == "__init__" else parts)
        sources[module] = path.read_text()
        if parts[-1] == "__init__":
            packages.add(module)
    assert _boundary_violations(sources, frozenset(packages)) == []


def test_pr14_migration_has_exactly_four_business_tables() -> None:
    migration = (ROOT / "migrations/versions/0015_governance_audit.py").read_text()
    assert migration.count("op.create_table(") == 4
    for table in (
        "audit_findings",
        "impact_assessments",
        "impact_targets",
        "correction_records",
    ):
        assert f'"{table}"' in migration
    assert 'ondelete="CASCADE"' not in migration
