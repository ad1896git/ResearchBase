"""S7 boundaries for ADR-0029's partial search slice; S8 and D1 remain open.

These static checks do not establish S8 contention/guard acceptance or admit a
production node/link/lifecycle writer, producer, evaluator, scoring or transport.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

from tests.architecture.test_pr3_00_boundaries import FORBIDDEN, _forbidden_imports

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src/researchbase"
DOMAIN = SRC / "agent_runtime/domain/experiment_search.py"
APPLICATION = SRC / "agent_runtime/application/experiment_search.py"
CONTRACTS = SRC / "agent_runtime/application/search_contracts.py"
SEARCH_MODULES = (
    "researchbase.agent_runtime.application.experiment_search",
    "researchbase.agent_runtime.application.search_contracts",
)
EXECUTION_BOUNDARIES = (
    "researchbase.agent_runtime.application.agent_executions",
    "researchbase.agent_runtime.application.capability_gateway",
    "researchbase.application.literature_search_execution",
    "researchbase.application.source_merge_execution",
    "researchbase.application.strategy_candidate_promotion",
    "researchbase.agent_runtime.ports.execution_repository",
    "researchbase.agent_runtime.ports.gateway_repository",
    "researchbase.agent_runtime.ports.capability_gateway",
    "researchbase.application.ports.StrategyCandidatePromotionRepository",
    "researchbase.application.ports.StrategyCandidatePromotionUnitOfWork",
)
EXECUTION_UOW_PORTS = {
    "agent_executions",
    "executions",
    "gateway",
    "literature_search_execution",
    "source_merge",
    "strategy_candidates",
    "begin_execution_intent",
    "begin_gateway_command",
    "begin_strategy",
}
SEARCH_OPERATIONS = {
    "create_search_session",
    "append_search_node",
    "get_experiment_search_tree",
    "get_branch_lineage",
    "get_search_budget",
    "link_search_node_run",
    "record_search_node_failure",
    "prune_search_node",
    "close_search_session",
}


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(), filename=str(path))


def _module(path: Path) -> str:
    return ".".join(path.relative_to(SRC.parent).with_suffix("").parts)


def _qualified(node: ast.expr, aliases: dict[str, str]) -> str:
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        return f"{_qualified(node.value, aliases)}.{node.attr}"
    return ""


def _imports(tree: ast.Module, module: str) -> tuple[set[str], dict[str, str], set[str]]:
    """Resolve static imports and literal dynamic targets without importing code."""
    names: set[str] = set()
    aliases: dict[str, str] = {}
    issues: set[str] = set()
    package = module.rpartition(".")[0]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for item in node.names:
                names.add(item.name)
                aliases[item.asname or item.name.split(".")[0]] = (
                    item.name if item.asname else item.name.split(".")[0]
                )
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            try:
                if node.level:
                    base = importlib.util.resolve_name("." * node.level + base, package)
            except (ImportError, ValueError):
                issues.add("unresolved relative import")
                continue
            names.add(base)
            for item in node.names:
                target = f"{base}.{item.name}"
                names.add(target)
                aliases[item.asname or item.name] = target
    # Preserve simple aliases of imported modules, constructors and dynamic loaders.
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            value = _qualified(node.value, aliases)
            if value:
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        aliases[target.id] = value
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        loader = _qualified(node.func, aliases)
        if loader not in {"__import__", "builtins.__import__", "importlib.import_module"}:
            continue
        issues.add("dynamic import")
        argument = (
            node.args[0]
            if node.args
            else next((kw.value for kw in node.keywords if kw.arg == "name"), None)
        )
        if not isinstance(argument, ast.Constant) or not isinstance(argument.value, str):
            issues.add("unresolved dynamic import")
            continue
        target = argument.value
        if target.startswith("."):
            package_arg = (
                node.args[1]
                if len(node.args) > 1
                else next((kw.value for kw in node.keywords if kw.arg == "package"), None)
            )
            if isinstance(package_arg, ast.Constant) and isinstance(package_arg.value, str):
                relative_package = package_arg.value
            elif isinstance(package_arg, ast.Name) and package_arg.id == "__package__":
                relative_package = package
            else:
                issues.add("unresolved dynamic import")
                continue
            try:
                target = importlib.util.resolve_name(target, relative_package)
            except (ImportError, ValueError):
                issues.add("unresolved dynamic import")
                continue
        names.add(target)
    return names, aliases, issues


def _direct_dependencies(source: str, module: str) -> set[str]:
    """Check only search additions; ports/UoW calls remain permitted."""
    tree = ast.parse(source)
    names, aliases, violations = _imports(tree, module)
    for name in names:
        if any(name == item or name.startswith(item + ".") for item in FORBIDDEN):
            violations.add(name)
        if name.split(".")[0] not in sys.stdlib_module_names | {"researchbase"}:
            violations.add(f"external dependency: {name}")
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _qualified(node.func, aliases)
        if name.rsplit(".", 1)[-1] in {"Session", "sessionmaker", "create_engine"}:
            violations.add(f"direct persistence call: {name}")
        parts = name.split(".")
        if set(parts[:-1]) & {"session", "_session", "db_session", "connection", "_connection"}:
            if parts[-1] in {
                "execute",
                "query",
                "scalar",
                "scalars",
                "add",
                "add_all",
                "delete",
                "flush",
                "commit",
                "rollback",
            }:
                violations.add(f"direct persistence call: {name}")
        if any(name == item or name.startswith(item + ".") for item in FORBIDDEN):
            violations.add(f"direct persistence call: {name}")
    return violations


def _execution_dependencies(source: str, module: str) -> set[str]:
    """Reject known execution boundaries in search, not the existing gateway itself."""
    tree = ast.parse(source)
    names, aliases, issues = _imports(tree, module)
    violations = set(issues)
    # Search uses synchronous factory contexts. Track their bound names so port
    # access cannot evade the check merely by renaming `uow` to `transaction`.
    # This remains a local syntax check, without inferring arbitrary object types.
    uow_bindings = {"uow"} | {
        _qualified(item.optional_vars, aliases)
        for node in ast.walk(tree)
        if isinstance(node, ast.With)
        for item in node.items
        if isinstance(item.context_expr, ast.Call) and isinstance(item.optional_vars, ast.Name)
    }
    # Typed helper parameters are another explicit UoW binding. Resolve imported
    # aliases and forward annotations; this is not arbitrary Python type inference.
    for node in ast.walk(tree):
        if not isinstance(node, ast.arg) or node.annotation is None:
            continue
        annotation = node.annotation
        if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str):
            annotation = ast.parse(annotation.value, mode="eval").body
        if any(
            isinstance(part, ast.Name | ast.Attribute)
            and _qualified(part, aliases).rsplit(".", 1)[-1]
            in {"SearchUnitOfWork", "TaskUnitOfWork", "SqlAlchemyUnitOfWork"}
            for part in ast.walk(annotation)
        ):
            uow_bindings.add(node.arg)
    # Keep explicit local aliases of known UoWs in the same bounded syntax model.
    assignments = [node for node in ast.walk(tree) if isinstance(node, ast.Assign)]
    for _ in range(len(assignments)):
        before = len(uow_bindings)
        for assignment in assignments:
            if isinstance(assignment.value, ast.Name) and assignment.value.id in uow_bindings:
                uow_bindings.update(
                    target.id for target in assignment.targets if isinstance(target, ast.Name)
                )
        if len(uow_bindings) == before:
            break
    for name in names:
        if any(
            name == boundary or name.startswith(boundary + ".") for boundary in EXECUTION_BOUNDARIES
        ):
            violations.add(name)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute | ast.Call):
            expr = node.func if isinstance(node, ast.Call) else node
            name = _qualified(expr, aliases)
            if any(
                name == boundary or name.startswith(boundary + ".")
                for boundary in EXECUTION_BOUNDARIES
            ):
                violations.add(name)
            parts = name.split(".")
            if len(parts) > 1 and parts[0] in uow_bindings and parts[1] in EXECUTION_UOW_PORTS:
                violations.add(name)
    return violations


def _transport_violations(sources: dict[str, str], roots: set[str]) -> set[str]:
    """Follow local import edges, including re-exports and registration helpers.

    Exact search operations and registration paths also catch injected services
    and string command dispatch without confusing literature search or gateway I/O.
    Persistence/other approved gateway dependencies are not prohibited here.
    """
    violations: set[str] = set()
    pending = list(roots)
    visited: set[str] = set()
    while pending:
        module = pending.pop()
        if module in visited:
            continue
        visited.add(module)
        tree = ast.parse(sources[module])
        names, aliases, issues = _imports(tree, module)
        violations.update(f"{module}: {issue}" for issue in issues)
        for name in names:
            if any(name == item or name.startswith(item + ".") for item in SEARCH_MODULES):
                violations.add(f"{module}: search import {name}")
            # Imported names may denote either a symbol or a module/package.
            candidate = name
            while candidate:
                local = candidate if candidate in sources else candidate + ".__init__"
                if local in sources:
                    pending.append(local)
                    break
                candidate = candidate.rpartition(".")[0]
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                name = _qualified(node, aliases)
                if node.attr in SEARCH_OPERATIONS or any(
                    name == item or name.startswith(item + ".") for item in SEARCH_MODULES
                ):
                    violations.add(f"{module}: search binding {name}")
            if not isinstance(node, ast.Call):
                continue
            operation = _qualified(node.func, aliases).rsplit(".", 1)[-1]
            if operation in SEARCH_OPERATIONS:
                violations.add(f"{module}: search call {operation}")
            values = {
                n.value
                for arg in [*node.args, *(kw.value for kw in node.keywords)]
                for n in ast.walk(arg)
                if isinstance(n, ast.Constant) and isinstance(n.value, str)
            }
            if values & SEARCH_OPERATIONS:
                violations.add(f"{module}: search command registration")
            if operation in {
                "get",
                "post",
                "put",
                "patch",
                "delete",
                "command",
                "add_api_route",
                "add_command",
                "add_typer",
                "include_router",
            }:
                segments = {
                    segment.replace("-", "_") for value in values for segment in value.split("/")
                }
                if segments & {
                    "experiment_search",
                    "experiment_searches",
                    "search_sessions",
                    "search_nodes",
                }:
                    violations.add(f"{module}: search route registration")
    return violations


def _service_methods() -> dict[str, ast.FunctionDef]:
    service = next(
        node
        for node in _tree(APPLICATION).body
        if isinstance(node, ast.ClassDef) and node.name == "ExperimentSearchService"
    )
    return {node.name: node for node in service.body if isinstance(node, ast.FunctionDef)}


def _calls(node: ast.AST, target: str) -> list[ast.Call]:
    return [
        n for n in ast.walk(node) if isinstance(n, ast.Call) and _qualified(n.func, {}) == target
    ]


def test_human_and_agent_share_application_boundary() -> None:
    methods = _service_methods()
    edges = {
        "execute": ("create_search_session", "append_search_node"),
        "create_search_session": ("_create",),
        "_create": ("_create_once",),
        "get_experiment_search_tree": ("_read",),
        "get_branch_lineage": ("_read",),
        "get_search_budget": ("_read",),
        "append_search_node": ("_command",),
    }
    for caller, targets in edges.items():
        assert "principal" in [arg.arg for arg in methods[caller].args.args]
        for target in targets:
            calls = _calls(methods[caller], f"self.{target}")
            assert calls, (caller, target)
            assert all(
                isinstance(call.args[0], ast.Name) and call.args[0].id == "principal"
                for call in calls
            )
            assert all(
                isinstance(call.args[1], ast.Name)
                and call.args[1].id == ("request" if target == "_read" else "command")
                for call in calls
            )
    init = methods["__init__"]
    assert any(
        arg.arg == "factory"
        and isinstance(arg.annotation, ast.Name)
        and arg.annotation.id == "SearchUowFactory"
        for arg in init.args.args
    )
    assert any(
        isinstance(n, ast.Assign)
        and isinstance(n.value, ast.Name)
        and n.value.id == "factory"
        and any(
            isinstance(t, ast.Attribute) and _qualified(t, {}) == "self._factory" for t in n.targets
        )
        for n in ast.walk(init)
    )
    for name, begin in (
        ("_read", "begin_formal_read"),
        ("_create_once", "begin_experiment_search"),
    ):
        method = methods[name]
        contexts = [
            n
            for n in ast.walk(method)
            if isinstance(n, ast.With)
            and any(
                isinstance(item.context_expr, ast.Call)
                and _qualified(item.context_expr.func, {}) == "self._factory"
                and isinstance(item.optional_vars, ast.Name)
                and item.optional_vars.id == "uow"
                for item in n.items
            )
        ]
        assert len(contexts) == 1
        context = contexts[0]
        assert _calls(context, f"uow.{begin}")
        assert any(
            isinstance(n, ast.Assign)
            and isinstance(n.value, ast.Attribute)
            and _qualified(n.value, {}) == "uow.experiment_search"
            and any(isinstance(t, ast.Name) and t.id == "repo" for t in n.targets)
            for n in ast.walk(context)
        )
        authorization = _calls(context, "self._authorize")
        assert authorization
        assert all(
            [ast.unparse(a) for a in call.args[:2]] == ["repo", "principal"]
            for call in authorization
        )
        kinds = [
            n
            for n in ast.walk(context)
            if isinstance(n, ast.Set) and {ast.unparse(e) for e in n.elts} == {"'HUMAN'", "'AGENT'"}
        ]
        assert kinds
        assert bool(_calls(context, "uow.commit")) == (name == "_create_once")
    calls = _calls(methods["_read"], "ObjectiveDefinition")
    assert len(calls) == 1
    assert [ast.unparse(arg) for arg in calls[0].args] == ["task['id']", "task['objective']"]


def test_domain_has_no_orm_transport_provider_dependencies() -> None:
    for path in (DOMAIN, APPLICATION, CONTRACTS):
        assert _direct_dependencies(path.read_text(), _module(path)) == set(), str(path)
    assert _forbidden_imports(DOMAIN.parent, "researchbase.agent_runtime.domain") == []


def test_no_execution_promotion_strategy_or_new_dependency() -> None:
    for path in (DOMAIN, APPLICATION, CONTRACTS):
        names, _, _ = _imports(_tree(path), _module(path))
        assert not any(
            name.startswith(("researchbase.strategies", "researchbase.capabilities"))
            for name in names
        )
        assert _direct_dependencies(path.read_text(), _module(path)) == set()
        assert _execution_dependencies(path.read_text(), _module(path)) == set()
    methods = _service_methods()
    assert (
        not {
            "execute_run",
            "dispatch",
            "promote",
            "score",
            "link_search_node_run",
            "record_search_node_failure",
            "prune_search_node",
            "close_search_session",
        }
        & methods.keys()
    )
    append = methods["append_search_node"]
    assert any(
        isinstance(n, ast.Attribute) and n.attr == "INVALID_STATE_TRANSITION"
        for n in ast.walk(append)
    )
    assert not any(isinstance(n, ast.With) for n in ast.walk(append))


def test_boundary_scanner_detects_deliberate_violation(tmp_path: Path) -> None:
    module = "researchbase.agent_runtime.application.violation"
    forbidden = (
        ("from ...persistence import uow", "researchbase.persistence.uow"),
        ("from ... import persistence", "researchbase.persistence"),
        (
            "import sqlalchemy.orm as orm\norm.Session()",
            "direct persistence call: sqlalchemy.orm.Session",
        ),
        (
            "from sqlalchemy import orm as db\nfactory = db.sessionmaker\nfactory()",
            "direct persistence call: sqlalchemy.orm.sessionmaker",
        ),
        ("storage.Session()", "direct persistence call: storage.Session"),
        ("uow._session.execute(statement)", "direct persistence call: uow._session.execute"),
        ("session.commit()", "direct persistence call: session.commit"),
        (
            "import importlib as loader\nloader.import_module('researchbase.persistence.uow')",
            "researchbase.persistence.uow",
        ),
        (
            "from importlib import import_module as load\nload('...persistence.uow', __package__)",
            "researchbase.persistence.uow",
        ),
        ("__import__('researchbase.persistence')", "researchbase.persistence"),
        (
            "import builtins as bi\nbi.__import__('researchbase.persistence')",
            "researchbase.persistence",
        ),
        ("load = __import__\nload(target)", "unresolved dynamic import"),
    )
    for source, expected in forbidden:
        assert expected in _direct_dependencies(source, module), source
    for source in (
        "from ..ports.search_repository import SearchUowFactory",
        "from .. import search_contracts",
        "with factory() as uow:\n    uow.begin_formal_read()\n"
        "    uow.experiment_search.retained_history(session_id)",
        "repo.flush()\nuow.commit()",
        "# import sqlalchemy\nmessage = 'from ...persistence import uow'",
    ):
        assert _direct_dependencies(source, module) == set(), source
    for source in (
        "from .agent_executions import AgentExecutionService as Service\n"
        "Service(factory).execute(command)",
        "from . import capability_gateway as gateway\n"
        "gateway.CapabilityGatewayService(factory, credentials).invoke(request)",
        "import researchbase.application.literature_search_execution as lit\n"
        "lit.LiteratureSearchExecutionService(factory).execute(command)",
        "from ...application.source_merge_execution import SourceMergeExecutionService as Merge\n"
        "Merge(factory).consume(command)",
        "from ...application import strategy_candidate_promotion as promotion\n"
        "promotion.StrategyCandidatePromotionService(factory).promote_strategy_question(command)",
        "from ..ports.execution_repository import ExecutionUowFactory",
        "from ..ports import gateway_repository as gateway",
        "from ...application.ports import StrategyCandidatePromotionUnitOfWork as PromotionUow",
        "uow.begin_gateway_command()\nuow.strategy_candidates.insert(kind, row)",
        "uow.literature_search_execution.execute(command)\nuow.begin_execution_intent()",
        "def helper(work: SearchUnitOfWork):\n    work.gateway",
        "from ..ports.search_repository import SearchUnitOfWork as Work\n"
        "def helper(transaction: Work):\n    transaction.executions",
        "def helper(work: 'SearchUnitOfWork'):\n    alias = work\n    alias.gateway",
        "with factory() as transaction:\n    transaction.gateway",
        "with factory() as transaction:\n    transaction.executions",
        "with self._factory() as work:\n    work.begin_gateway_command()",
        "with factory() as transaction:\n"
        "    promotion = transaction.strategy_candidates\n"
        "    promotion.insert(kind, row)",
    ):
        assert _execution_dependencies(source, module), source
    control = (
        "from ..ports.search_repository import SearchUowFactory\n"
        "from .task_safety import safety_projection\n"
        "with factory() as uow:\n"
        "    uow.begin_formal_read()\n"
        "    repo = uow.experiment_search\n"
        "    safety_projection(repo, task, at, history=False)\n"
        "    repo.retained_history(session_id)\n"
        "    uow.commit()\n"
    )
    assert _execution_dependencies(control, module) == set()
    assert _execution_dependencies(control.replace("uow", "transaction"), module) == set()
    typed_control = (
        "from ..ports.search_repository import SearchUnitOfWork as Work\n"
        "def helper(transaction: Work):\n"
        "    transaction.experiment_search.retained_history(session_id)\n"
    )
    assert _execution_dependencies(typed_control, module) == set()

    bad = tmp_path / "bad.py"
    bad.write_text("from sqlalchemy.orm import Session\nSession()\n")
    good = tmp_path / "good.py"
    good.write_text(
        "from researchbase.agent_runtime.ports.search_repository import SearchUowFactory\n"
    )
    violations = _forbidden_imports(tmp_path, "researchbase.agent_runtime.domain")
    assert any(path == bad and name == "sqlalchemy.orm" for path, name in violations)
    assert not any(path == good for path, _ in violations)


def test_no_api_or_cli_routes_added() -> None:
    sources = {_module(path): path.read_text() for path in SRC.rglob("*.py")}
    roots = {
        module
        for module in sources
        if module.startswith(("researchbase.api.", "researchbase.cli."))
    }
    assert _transport_violations(sources, roots) == set()
    # An existing route and the earlier gateway service remain legitimate controls.
    root = "researchbase.api.synthetic"
    control = """from .agent_routes import router
from researchbase.agent_runtime.application.capability_gateway import CapabilityGatewayService
app.include_router(router, prefix='/v1')
@app.get('/literature/search')
def search_literature():
    return 'search is not itself a forbidden keyword'
"""
    assert _transport_violations({**sources, root: control}, {root}) == set()
    fixtures = (
        "from researchbase.agent_runtime.application import experiment_search",
        "from ..agent_runtime.application import search_contracts as contracts",
        "@app.post('/experiment-search/sessions')\ndef create():\n    return {}",
        "@app.get('/budget')\ndef budget():\n"
        "    return services.get_search_budget(principal, request)",
        "add_command(app, 'create', 'create_search_session', handler)",
        "app.add_api_route('/budget', services.get_search_budget)",
        "from ..agent_runtime import application as ar\n"
        "service = ar.experiment_search.ExperimentSearchService(factory)",
        "from .search_bridge import router\napp.include_router(router)",
        "from .search_bridge import register as mount\nmount(app)",
    )
    bridge = "researchbase.api.search_bridge"
    intermediary = """from researchbase.agent_runtime.application import experiment_search
router = object()
def register(app):
    app.add_api_route('/budget', experiment_search.ExperimentSearchService.get_search_budget)
"""
    for source in fixtures:
        assert _transport_violations({**sources, root: source, bridge: intermediary}, {root}), (
            source
        )
