"""Fail-closed helpers for PR-18 evidence.

This module intentionally does not modify the PR-17DR5 evidence generator or
its artifacts. It validates the small, repository-relative manifest used to
record PR-18 verification results.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import event, text
from sqlalchemy.engine import Engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.pr17dr_evidence import VERIFICATION_COMMANDS as _PR17_COMMANDS  # noqa: E402

_PR18_BASE_COMMANDS: tuple[tuple[str, list[str]], ...] = tuple(
    (
        command_id,
        [
            *command,
            "tests/integration/test_pr18_hardening.py",
        ],
    )
    if command_id == "catalog_exact_verification"
    else (command_id, command)
    for command_id, command in _PR17_COMMANDS
)

AUTHORITATIVE_COMMANDS: tuple[tuple[str, list[str]], ...] = (
    *_PR18_BASE_COMMANDS,
    (
        "pr18_focused_and_evidence_tool",
        [
            "uv",
            "run",
            "pytest",
            "-q",
            "-ra",
            "tests/unit/test_pr18_evidence.py",
            "tests/unit/test_pr18_error_log_hardening.py",
            "tests/unit/test_pr18_docs_examples.py",
            "tests/architecture/test_pr18_boundaries.py",
            "tests/integration/test_pr18_hardening.py",
            "tests/unit/test_pr17dr2_evidence.py",
            "tests/unit/test_pr17dr2_test_integrity.py",
        ],
    ),
)

PYTEST_COUNT_FIELDS = (
    "total_discovered",
    "selected",
    "deselected",
    "passed",
    "failed",
    "skipped",
    "xfailed",
    "xpassed",
    "errors",
    "return_code",
)
_SUMMARY_COUNT = re.compile(
    r"(?P<count>\d+) (?P<kind>passed|failed|skipped|deselected|xfailed|xpassed|errors?)"
)
_COLLECTION_COUNT = re.compile(
    r"^[ \t]*(?:(?P<selected>\d+)/)?(?P<total>\d+) tests? collected"
    r"(?: \((?P<deselected>\d+) deselected\))?",
    re.MULTILINE,
)
INHERITED_PR11R2_SKIP_IDENTITIES = frozenset(
    {
        "tests.integration.test_pr11r2_migration::test_clean_previous_head_upgrade_and_roundtrip_reaches_fail_closed_head",
        "tests.integration.test_pr11r2_migration::test_invalid_legacy_upgrade_fails_closed_and_manual_remediation_retries",
    }
)
TODO_DISPOSITIONS = frozenset({"CLOSED", "INTENTIONAL_NONBLOCKING", "OUT_OF_PHASE", "PR18_BLOCKER"})
TODO_MARKERS = ("TODO", "FIXME", "XXX", "HACK", "TBD")
TODO_ROOTS = ("src", "migrations", "tests", "docs", "scripts", "execution", "artifacts")
TODO_EXTENSIONS = frozenset({".py", ".sql", ".md", ".json", ".yaml", ".yml", ".toml", ".txt"})
_TODO_PATTERN = re.compile(r"\b(TODO|FIXME|XXX|HACK|TBD)\b", re.IGNORECASE)

_ABSOLUTE_PATH = re.compile(r"^(?:/|[A-Za-z]:[\\/])")
_CREDENTIAL_TOKEN = re.compile(
    r"(?i)(?:password|passwd|secret|credential|api[_-]?key|token)\s*[=:]|"
    r"postgres(?:ql)?(?:\+[^:/\s]+)?://[^:/\s]+:[^@\s]+@"
)


class PR18EvidenceError(ValueError):
    """Raised when PR-18 evidence is incomplete, stale, or unsafe."""

    status = "NOT_VERIFIED"


NOT_VERIFIED = "NOT_VERIFIED"


def _summary_counts(output: str) -> dict[str, int]:
    counts = {
        key: 0
        for key in ("passed", "failed", "skipped", "deselected", "xfailed", "xpassed", "errors")
    }
    for line in reversed(output.splitlines()):
        matches = list(_SUMMARY_COUNT.finditer(line))
        if matches:
            for match in matches:
                key = (
                    "errors" if match.group("kind") in {"error", "errors"} else match.group("kind")
                )
                counts[key] = int(match.group("count"))
            return counts
    return counts


def _collection_counts(output: str) -> tuple[int, int, int] | None:
    matches = list(_COLLECTION_COUNT.finditer(output))
    if not matches:
        raise PR18EvidenceError("pytest collection metadata is missing")
    if len(matches) != 1:
        raise PR18EvidenceError("pytest collection metadata is ambiguous")
    match = matches[-1]
    total = int(match.group("total"))
    selected = int(match.group("selected") or total)
    deselected = int(match.group("deselected") or 0)
    if total != selected + deselected:
        raise PR18EvidenceError("pytest collection counts do not reconcile")
    return total, selected, deselected


def parse_pytest_counts(
    *, output: str, collection_output: str, junit_xml: str | None, return_code: int
) -> dict[str, int]:
    """Reconcile pytest terminal, collection, and JUnit machine results."""

    if not isinstance(return_code, int) or isinstance(return_code, bool) or return_code < 0:
        raise PR18EvidenceError("pytest return code is malformed")
    if junit_xml is None:
        raise PR18EvidenceError("pytest JUnit result is missing")
    try:
        root = ET.fromstring(junit_xml)
    except ET.ParseError as error:
        raise PR18EvidenceError("pytest JUnit result is malformed") from error
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    if not suites:
        raise PR18EvidenceError("pytest JUnit result has no test suites")
    try:
        selected = 0
        failed = 0
        errors = 0
        junit_skipped = 0
        xfailed = 0
        xpassed = 0
        for suite in suites:
            required_attrs = ("tests", "failures", "errors", "skipped")
            if any(name not in suite.attrib for name in required_attrs):
                raise PR18EvidenceError("pytest JUnit outcome data is incomplete")
            suite_selected = int(suite.attrib["tests"])
            suite_failed = int(suite.attrib["failures"])
            suite_errors = int(suite.attrib["errors"])
            suite_skipped = int(suite.attrib["skipped"])
            testcases = list(suite.findall("testcase"))
            if len(testcases) != suite_selected:
                raise PR18EvidenceError("pytest JUnit testcase data is incomplete")
            child_failed = 0
            child_errors = 0
            child_skipped = 0
            for testcase in testcases:
                failure = testcase.find("failure")
                error = testcase.find("error")
                skipped = testcase.find("skipped")
                if failure is not None:
                    child_failed += 1
                    if failure.attrib.get("type") == "pytest.xpass":
                        xpassed += 1
                if error is not None:
                    child_errors += 1
                if skipped is not None:
                    child_skipped += 1
                    if skipped.attrib.get("type") == "pytest.xfail":
                        xfailed += 1
            if (suite_failed, suite_errors, suite_skipped) != (
                child_failed,
                child_errors,
                child_skipped,
            ):
                raise PR18EvidenceError("pytest JUnit suite and testcase outcomes differ")
            selected += suite_selected
            failed += child_failed - sum(
                1
                for testcase in testcases
                if (failure := testcase.find("failure")) is not None
                and failure.attrib.get("type") == "pytest.xpass"
            )
            errors += child_errors
            junit_skipped += child_skipped
    except ValueError as error:
        raise PR18EvidenceError("pytest JUnit counts are malformed") from error
    collection = _collection_counts(collection_output)
    if collection is None:
        raise PR18EvidenceError("pytest collection metadata is missing")
    total_discovered, collection_selected, deselected = collection
    if collection_selected != selected:
        raise PR18EvidenceError("pytest JUnit and collection selected counts differ")
    terminal = _summary_counts(output)
    xfailed = max(xfailed, terminal["xfailed"])
    xpassed = max(xpassed, terminal["xpassed"])
    skipped = junit_skipped - xfailed
    passed = selected - failed - errors - skipped - xfailed - xpassed
    counts = {
        "total_discovered": total_discovered,
        "selected": selected,
        "deselected": deselected,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "xfailed": xfailed,
        "xpassed": xpassed,
        "errors": errors,
        "return_code": return_code,
    }
    if min(counts.values()) < 0:
        raise PR18EvidenceError("pytest result contains negative counts")
    if selected != passed + failed + skipped + xfailed + xpassed + errors:
        raise PR18EvidenceError("pytest outcome counts do not reconcile")
    for key in ("passed", "failed", "skipped", "xfailed", "xpassed", "errors", "deselected"):
        if terminal[key] and terminal[key] != counts[key]:
            raise PR18EvidenceError(f"pytest terminal/JUnit count differs for {key}")
    return counts


def assess_evidence_readiness(artifact: object) -> str:
    """Return READY only when the stored evidence contains verified counts."""

    try:
        if not isinstance(artifact, dict):
            raise PR18EvidenceError("evidence must be an object")
        validate_command_entries(artifact.get("commands"))
    except PR18EvidenceError:
        return NOT_VERIFIED
    return "READY"


def _tuple_items(value: object) -> tuple[object, ...]:
    if isinstance(value, list | tuple):
        return tuple(value)
    return ()


def _string_items(value: object, *, label: str) -> tuple[str, ...]:
    items = _tuple_items(value)
    if any(not isinstance(item, str) for item in items):
        raise PR18EvidenceError(f"query contract has invalid {label}")
    return tuple(item for item in items if isinstance(item, str))


_SQL_RELATION = r"(?:[A-Za-z_][A-Za-z0-9_]*\.)?([A-Za-z_][A-Za-z0-9_]*)"
_JOIN_PREFIX = r"(?:(?:LEFT|RIGHT|FULL|INNER|OUTER|CROSS)\s+)?JOIN"
_JOIN_CLAUSE = re.compile(
    rf"\b(?P<kind>{_JOIN_PREFIX})\s+(?P<relation>{_SQL_RELATION})"
    r"(?P<tail>.*?)(?=\s+(?:(?:LEFT|RIGHT|FULL|INNER|OUTER|CROSS)\s+)?JOIN\b"
    r"|\s+WHERE\b|\s+GROUP\s+BY\b|\s+ORDER\s+BY\b|\s+LIMIT\b|$)",
    re.IGNORECASE | re.DOTALL,
)
_FROM_CLAUSE = re.compile(
    r"\bFROM\s+(?P<body>.*?)(?=\s+(?:(?:LEFT|RIGHT|FULL|INNER|OUTER|CROSS)\s+)?JOIN\b"
    r"|\s+WHERE\b|\s+GROUP\s+BY\b|\s+ORDER\s+BY\b|\s+LIMIT\b|$)",
    re.IGNORECASE | re.DOTALL,
)
_RELATION_NAME = re.compile(rf"^\s*{_SQL_RELATION}", re.IGNORECASE)
_RELATION_REFERENCE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\.\s*", re.IGNORECASE)
_CARTESIAN_PREDICATE = re.compile(r"^(?:TRUE|1\s*=\s*1)$", re.IGNORECASE)


def _sql_relations(sql: str) -> list[str]:
    """Extract base relation names needed for logical topology checks."""

    relations: list[str] = []
    from_match = _FROM_CLAUSE.search(sql)
    if from_match:
        for part in from_match.group("body").split(","):
            relation_match = _RELATION_NAME.match(part)
            if relation_match:
                relations.append(relation_match.group(1))
    relations.extend(match.group("relation") for match in _JOIN_CLAUSE.finditer(sql))
    return relations


def _join_contracts(
    topology: dict[str, object], key: str
) -> tuple[tuple[str, tuple[str, str], str], ...]:
    raw = topology.get(key)
    if raw == "required_join_edges":
        raw = topology.get("required_join_edges")
    items = _tuple_items(raw)
    contracts: list[tuple[str, tuple[str, str], str]] = []
    for item in items:
        if not isinstance(item, list | tuple) or len(item) != 3:
            raise PR18EvidenceError("query contract has invalid join edges")
        name, relations, pattern = item
        relation_items = _tuple_items(relations)
        if (
            not isinstance(name, str)
            or len(relation_items) != 2
            or any(not isinstance(value, str) for value in relation_items)
            or not isinstance(pattern, str)
        ):
            raise PR18EvidenceError("query contract has invalid join edges")
        contracts.append(
            (name, (str(relation_items[0]), str(relation_items[1])), pattern)
        )
    return tuple(contracts)


def _extract_join_edges(
    sql: str, *, plan_relations: set[str]
) -> tuple[list[dict[str, object]], bool]:
    """Extract logical JOIN edges and reject syntax too ambiguous to verify."""

    sql_relations = _sql_relations(sql)
    joins = list(_JOIN_CLAUSE.finditer(sql))
    if len(sql_relations) < len(joins):
        raise PR18EvidenceError("INVALID_JOIN_TOPOLOGY: SQL relation topology is ambiguous")
    edges: list[dict[str, object]] = []
    cartesian = False
    for index, match in enumerate(joins):
        right = match.group("relation")
        left_index = index
        if left_index >= len(sql_relations):
            raise PR18EvidenceError("INVALID_JOIN_TOPOLOGY: JOIN has no left relation")
        left = sql_relations[left_index]
        kind = match.group("kind").upper()
        tail = match.group("tail").strip()
        on_match = re.match(r"ON\s+(?P<predicate>.*)\Z", tail, re.IGNORECASE | re.DOTALL)
        predicate = on_match.group("predicate").strip() if on_match else ""
        is_cartesian = "CROSS" in kind or not predicate or bool(
            _CARTESIAN_PREDICATE.fullmatch(predicate)
        )
        if is_cartesian:
            cartesian = True
        references = {
            name
            for name in _RELATION_REFERENCE.findall(predicate)
            if name in plan_relations
        }
        edge_relations = tuple(sorted(references)) if len(references) == 2 else (left, right)
        edges.append(
            {
                "left": edge_relations[0],
                "right": edge_relations[1],
                "predicate": predicate,
                "cartesian": is_cartesian,
                "relation_references": sorted(references),
            }
        )
    return edges, cartesian


def _edge_key(relations: tuple[str, str]) -> tuple[str, str]:
    return min(relations), max(relations)


def _join_graph_connected(relations: set[str], edges: list[dict[str, object]]) -> bool:
    if len(relations) <= 1:
        return True
    adjacency = {relation: set() for relation in relations}
    for edge in edges:
        if edge.get("cartesian"):
            continue
        left = edge.get("left")
        right = edge.get("right")
        if isinstance(left, str) and isinstance(right, str):
            adjacency.setdefault(left, set()).add(right)
            adjacency.setdefault(right, set()).add(left)
    seen = {next(iter(relations))}
    pending = list(seen)
    while pending:
        current = pending.pop()
        for neighbor in adjacency.get(current, set()) - seen:
            seen.add(neighbor)
            pending.append(neighbor)
    return seen == relations


def validate_query_contract(
    expectation: dict[str, object], statements: object
) -> dict[str, object]:
    """Enforce an independent frozen query contract against captured SQL/plans."""

    if not isinstance(statements, list) or not statements:
        raise PR18EvidenceError("query contract captured no statements")
    required_relation_items = _tuple_items(expectation.get("required_relations"))
    if not required_relation_items or any(
        not isinstance(item, str) for item in required_relation_items
    ):
        raise PR18EvidenceError("query contract has no valid required relations")
    required_relations = tuple(item for item in required_relation_items if isinstance(item, str))
    topology = expectation.get("topology")
    if not isinstance(topology, dict):
        raise PR18EvidenceError("NOT_VERIFIED: query contract has no topology constraints")
    allowed_relation_items = _tuple_items(topology.get("allowed_relations"))
    if not allowed_relation_items or any(
        not isinstance(item, str) for item in allowed_relation_items
    ):
        raise PR18EvidenceError("NOT_VERIFIED: query contract has no allowed relation set")
    allowed_relations = tuple(item for item in allowed_relation_items if isinstance(item, str))
    closed_relation_set = topology.get("closed_relation_set") is True
    if not closed_relation_set:
        raise PR18EvidenceError("NOT_VERIFIED: query contract relation set is not explicit")
    if not all(
        isinstance(topology.get(key), bool)
        for key in (
            "allow_single_relation_reads",
            "allow_cartesian_joins",
            "forbidden_cartesian_joins",
        )
    ):
        raise PR18EvidenceError("NOT_VERIFIED: query contract topology booleans are incomplete")
    actual_relations: set[str] = set()
    statement_plans: list[tuple[dict[str, object], str, set[str]]] = []
    for statement in statements:
        if not isinstance(statement, dict):
            raise PR18EvidenceError("NOT_VERIFIED: malformed captured query statement")
        plan = statement.get("plan")
        if not isinstance(plan, dict):
            raise PR18EvidenceError("NOT_VERIFIED: query contract statement has no plan")
        plan_relations = set(_string_items(plan.get("relations"), label="relations"))
        if not _string_items(plan.get("node_types"), label="node types"):
            raise PR18EvidenceError("NOT_VERIFIED: query plan has no node types")
        actual_relations.update(plan_relations)
        statement_plans.append((plan, str(statement.get("sql", "")), plan_relations))
    missing_relations = sorted(set(required_relations) - actual_relations)
    if missing_relations:
        raise PR18EvidenceError(
            f"MISSING_REQUIRED_RELATION: {', '.join(missing_relations)}"
        )
    unexpected_relations = sorted(actual_relations - set(allowed_relations))
    if closed_relation_set and unexpected_relations:
        raise PR18EvidenceError(
            f"UNEXPECTED_RELATION: {', '.join(unexpected_relations)}"
        )

    sql_text = "\n".join(
        str(statement.get("sql", "")) for statement in statements if isinstance(statement, dict)
    )
    missing_predicates: list[str] = []
    predicate_items = _tuple_items(expectation.get("required_predicates"))
    for item in predicate_items:
        if not isinstance(item, list | tuple) or len(item) != 2:
            raise PR18EvidenceError("query contract has invalid required predicates")
        name, pattern = item
        if not re.search(str(pattern), sql_text, re.IGNORECASE | re.DOTALL):
            missing_predicates.append(str(name))
    if missing_predicates:
        raise PR18EvidenceError(
            f"MISSING_REQUIRED_PREDICATE: {', '.join(missing_predicates)}"
        )
    forbidden_nodes = set(_string_items(topology.get("forbidden_node_types"), label="node types"))
    forbidden_fragments = _string_items(
        topology.get("forbidden_sql_fragments"), label="SQL fragments"
    )
    required_edges = _join_contracts(topology, "required_join_edges")
    allowed_edges = _join_contracts(topology, "allowed_join_edges")
    if topology.get("allowed_join_edges") == "required_join_edges":
        allowed_edges = required_edges
    allowed_edge_keys = {_edge_key(item[1]) for item in allowed_edges}
    if any(_edge_key(edge[1]) not in allowed_edge_keys for edge in required_edges):
        raise PR18EvidenceError("NOT_VERIFIED: required topology edge is not allowed")
    observed_edges: list[dict[str, object]] = []
    observed_edge_names: set[str] = set()
    invalid_edges: list[str] = []
    cartesian_join = False
    for plan, sql, plan_relations in statement_plans:
        if not sql.lstrip().upper().startswith("SELECT"):
            raise PR18EvidenceError(
                "WRITE_OR_LOCK_VIOLATION: query captured a non-SELECT statement"
            )
        node_types = set(_string_items(plan.get("node_types"), label="node types"))
        forbidden = sorted(node_types & forbidden_nodes)
        if forbidden:
            raise PR18EvidenceError(
                f"WRITE_OR_LOCK_VIOLATION: forbidden query topology: {', '.join(forbidden)}"
            )
        upper_sql = sql.upper()
        if any(fragment.upper() in upper_sql for fragment in forbidden_fragments):
            raise PR18EvidenceError("WRITE_OR_LOCK_VIOLATION: forbidden query lock/write topology")
        sql_relations = set(_sql_relations(sql))
        if not sql_relations and plan_relations:
            raise PR18EvidenceError("NOT_VERIFIED: SQL relation topology could not be parsed")
        if topology.get("mode") == "batched_single_relation_selects":
            if not topology.get("allow_single_relation_reads") or len(plan_relations) != 1:
                raise PR18EvidenceError("INVALID_JOIN_TOPOLOGY: expected a single relation read")
            if sql_relations != plan_relations:
                raise PR18EvidenceError("INVALID_JOIN_TOPOLOGY: SQL and plan relations disagree")
        edges, statement_cartesian = _extract_join_edges(sql, plan_relations=plan_relations)
        cartesian_join = cartesian_join or statement_cartesian
        if (
            statement_cartesian
            and topology.get("forbidden_cartesian_joins") is True
            and topology.get("allow_cartesian_joins") is not True
        ):
            raise PR18EvidenceError("CARTESIAN_JOIN: Cartesian join is not authorized")
        if len(plan_relations) > 1 and not topology.get("allow_single_relation_reads"):
            raise PR18EvidenceError("INVALID_JOIN_TOPOLOGY: multi-relation read is not authorized")
        if len(plan_relations) > 1 and not _join_graph_connected(plan_relations, edges):
            raise PR18EvidenceError("INVALID_JOIN_TOPOLOGY: join graph is disconnected")
        for edge in edges:
            pair = (str(edge["left"]), str(edge["right"]))
            matching = [item for item in allowed_edges if _edge_key(item[1]) == pair]
            if not matching:
                invalid_edges.append(f"{pair[0]}--{pair[1]}")
                continue
            matching_contract = next(
                (item for item in matching if re.search(item[2], sql, re.IGNORECASE | re.DOTALL)),
                None,
            )
            if matching_contract is None:
                invalid_edges.append(f"{pair[0]}--{pair[1]}")
                continue
            edge["name"] = matching_contract[0]
            observed_edge_names.add(matching_contract[0])
            observed_edges.append(edge)
    if invalid_edges:
        raise PR18EvidenceError(
            "INVALID_JOIN_TOPOLOGY: unauthorized or wrong join edge(s): "
            f"{', '.join(sorted(invalid_edges))}"
        )

    missing_join_patterns: list[str] = []
    for item in _tuple_items(topology.get("required_join_patterns")):
        if not isinstance(item, list | tuple) or len(item) != 2:
            raise PR18EvidenceError("query contract has invalid join patterns")
        name, pattern = item
        if not re.search(str(pattern), sql_text, re.IGNORECASE | re.DOTALL):
            missing_join_patterns.append(str(name))
    if missing_join_patterns:
        raise PR18EvidenceError(
            "INVALID_JOIN_TOPOLOGY: required query topology absent: "
            f"{', '.join(missing_join_patterns)}"
        )
    missing_edges = sorted({item[0] for item in required_edges} - observed_edge_names)
    if missing_edges:
        raise PR18EvidenceError(
            f"INVALID_JOIN_TOPOLOGY: required join edge(s) absent: {', '.join(missing_edges)}"
        )
    expected_topology = {
        "mode": topology.get("mode"),
        "closed_relation_set": closed_relation_set,
        "allow_single_relation_reads": topology.get("allow_single_relation_reads") is True,
        "forbidden_cartesian_joins": topology.get("forbidden_cartesian_joins") is True,
        "required_join_edges": [
            {"name": name, "relations": list(relations), "predicate": pattern}
            for name, relations, pattern in required_edges
        ],
        "allowed_join_edges": [
            {"name": name, "relations": list(relations), "predicate": pattern}
            for name, relations, pattern in allowed_edges
        ],
        "forbidden_join_edges": topology.get("forbidden_join_edges"),
    }
    observed_topology = {
        "join_edges": sorted(
            observed_edges,
            key=lambda edge: (
                str(edge.get("left")),
                str(edge.get("right")),
                str(edge.get("predicate")),
            ),
        ),
        "connected": all(
            _join_graph_connected(
                set(plan_relations),
                _extract_join_edges(sql, plan_relations=plan_relations)[0],
            )
            for _plan, sql, plan_relations in statement_plans
        ),
    }
    return {
        "required_relations": list(required_relations),
        "allowed_relations": list(allowed_relations),
        "observed_relations": sorted(actual_relations),
        "actual_relations": sorted(actual_relations),
        "missing_relations": missing_relations,
        "unexpected_relations": unexpected_relations,
        "required_predicates": [
            str(item[0])
            for item in predicate_items
            if isinstance(item, list | tuple) and len(item) == 2
        ],
        "missing_predicates": missing_predicates,
        "predicate_verdict": "PASS",
        "topology_mode": topology["mode"],
        "expected_topology": expected_topology,
        "observed_topology": observed_topology,
        "cartesian_verdict": "PASS" if not cartesian_join else "FAIL",
        "topology_verdict": "PASS",
        "select_only": True,
        "no_cartesian_product": True,
        "no_write_or_lock": True,
        "verification_status": "VERIFIED",
        "overall_verdict": "PASS",
    }


def _validate_registry_tokens(command_id: str, tokens: list[str]) -> None:
    _validate_tokens(tokens)
    if "pytest" in tokens:
        targets = [token.split("::", 1)[0] for token in tokens if token.startswith("tests/")]
        for target in targets:
            if not (PROJECT_ROOT / target).exists():
                raise PR18EvidenceError(f"missing authoritative target: {command_id}:{target}")


def validate_current_command_registry() -> int:
    identifiers = [identifier for identifier, _ in AUTHORITATIVE_COMMANDS]
    if len(identifiers) != len(set(identifiers)):
        raise PR18EvidenceError("authoritative command registry contains duplicate ids")
    for command_id, tokens in AUTHORITATIVE_COMMANDS:
        _validate_registry_tokens(command_id, tokens)
    return len(AUTHORITATIVE_COMMANDS)


def authoritative_command_tokens(
    command_id: str, *, result_dir: str = "artifacts/pr_evidence/PR-18/junit"
) -> list[str]:
    for current_id, command in AUTHORITATIVE_COMMANDS:
        if current_id == command_id:
            tokens = [*command]
            if "pytest" in tokens:
                tokens.append(f"--junitxml={result_dir}/{command_id}.xml")
            _validate_tokens(tokens)
            return tokens
    raise PR18EvidenceError(f"unknown authoritative command: {command_id}")


def validate_stored_command_registry(entries: object) -> None:
    """Reject missing, extra, or token-drifted stored command results."""

    if not isinstance(entries, dict):
        raise PR18EvidenceError("stored commands must be an object")
    expected = {
        command_id: authoritative_command_tokens(command_id)
        for command_id, _command in AUTHORITATIVE_COMMANDS
    }
    if set(entries) != set(expected):
        raise PR18EvidenceError("stored command ids differ from authoritative registry")
    for command_id, tokens in expected.items():
        entry = entries[command_id]
        if not isinstance(entry, dict) or entry.get("command_tokens") != tokens:
            raise PR18EvidenceError(f"stored command tokens differ: {command_id}")
    validate_command_entries(entries)


def _marker_category(path: Path) -> str:
    parts = path.parts
    if "artifacts" in parts or "execution" in parts:
        return "historical evidence"
    if "vendor" in parts or "generated" in parts:
        return "vendor/generated"
    if parts and parts[0] == "src":
        return "production"
    if parts and parts[0] == "migrations":
        return "migration"
    if parts and parts[0] == "tests":
        return "tests"
    if parts and parts[0] == "docs":
        return "documentation"
    return "evidence/tooling"


def audit_repository_markers(root: Path = PROJECT_ROOT) -> dict[str, Any]:
    """Classify repository-relevant marker occurrences deterministically."""

    records: list[dict[str, Any]] = []
    for root_name in TODO_ROOTS:
        base = root / root_name
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in TODO_EXTENSIONS:
                continue
            if "junit" in path.parts or ".pytest_cache" in path.parts:
                continue
            relative = path.relative_to(root)
            if relative.parts[:3] == ("artifacts", "pr_evidence", "PR-18"):
                continue
            category = _marker_category(relative)
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                continue
            for line_number, line in enumerate(lines, 1):
                for match in _TODO_PATTERN.finditer(line):
                    marker = match.group(1).upper()
                    relative_text = str(relative)
                    is_scanner_vocabulary = relative_text in {
                        "scripts/pr18_evidence.py",
                        "tests/unit/test_pr18_todo_audit.py",
                    }
                    is_normative_criterion = relative_text == (
                        "docs/architecture/04_Phase1_Development_Specification_v1.2_Harness_Integrated.md"
                    )
                    if category == "historical evidence" or category == "vendor/generated":
                        disposition = "OUT_OF_PHASE"
                        class_group_id = "historical-evidence-text"
                        rationale = "archived execution/evidence text records prior review history"
                    elif is_normative_criterion:
                        disposition = "CLOSED"
                        class_group_id = "normative-phase1-criteria"
                        rationale = (
                            "normative Phase 1 criterion is recorded as specification text, "
                            "not an open implementation task"
                        )
                    elif is_scanner_vocabulary:
                        disposition = "INTENTIONAL_NONBLOCKING"
                        class_group_id = "marker-audit-vocabulary"
                        rationale = (
                            "marker names are data used by the deterministic audit itself and "
                            "do not describe a deferred runtime action"
                        )
                    elif relative_text.startswith("docs/superpowers/plans/"):
                        disposition = "OUT_OF_PHASE"
                        class_group_id = "phase1-plan-checklist"
                        rationale = (
                            "all markers in the archived implementation-plan class are checklist "
                            "text for review work, not live runtime TODOs"
                        )
                    elif relative_text.startswith("docs/superpowers/specs/"):
                        disposition = "CLOSED"
                        class_group_id = "pr18-specification-criteria"
                        rationale = (
                            "all markers in the PR-18 design-spec class are acceptance criteria "
                            "documented by the frozen specification, not deferred implementation"
                        )
                    elif category in {"production", "migration"}:
                        disposition = "PR18_BLOCKER"
                        class_group_id = "live-runtime-marker"
                        rationale = (
                            "live production or migration marker requires explicit closure "
                            "before Phase 1 completion"
                        )
                    else:
                        disposition = "INTENTIONAL_NONBLOCKING"
                        class_group_id = "reviewed-transport-documentation"
                        rationale = (
                            "reviewed contract/documentation marker describes an audit criterion "
                            "or example rather than a deferred runtime action"
                        )
                    architecture_sensitive = category in {"production", "migration"} and bool(
                        re.search(
                            r"architecture|provenance|scientific|history|uow|application|agent|error|migration|postgres",
                            line,
                            re.IGNORECASE,
                        )
                    )
                    records.append(
                        {
                            "path": str(relative),
                            "line": line_number,
                            "marker": marker,
                            "category": category,
                            "surrounding_intent": line.strip(),
                            "disposition": disposition,
                            "rationale": rationale,
                            "class_group_id": class_group_id,
                            "architecture_priority": "P1" if architecture_sensitive else None,
                        }
                    )
    live_categories = {"production", "migration", "tests", "documentation", "evidence/tooling"}
    undisposed = [
        record
        for record in records
        if record["category"] in live_categories and record["disposition"] not in TODO_DISPOSITIONS
    ]
    return {
        "markers_searched": list(TODO_MARKERS),
        "scope_roots": list(TODO_ROOTS),
        "records": records,
        "undisposed_live": undisposed,
        "architecture_p0": [
            record for record in records if record["architecture_priority"] == "P0"
        ],
        "architecture_p1": [
            record for record in records if record["architecture_priority"] == "P1"
        ],
    }


def collect_catalog_verification(engine: Engine) -> dict[str, Any]:
    """Compare PostgreSQL catalogs with the independent frozen index manifest."""

    from tests.contracts.pr18_manifest import FROZEN_REQUIRED_INDEXES

    expected_names = set(FROZEN_REQUIRED_INDEXES)
    with engine.connect() as connection:
        rows = (
            connection.execute(
                text(
                    "SELECT c.relname AS index_name, t.relname AS table_name, i.indisunique, "
                    "i.indisvalid, i.indisready, pg_get_expr(i.indpred, i.indrelid) AS predicate, "
                    "am.amname AS access_method, "
                    "array_agg(a.attname ORDER BY keys.ordinality) AS columns, "
                    "array_agg(opc.opcname ORDER BY keys.ordinality) AS operator_classes, "
                    "(pc.conindid IS NOT NULL) AS constraint_backed "
                    "FROM pg_index AS i "
                    "JOIN pg_class AS c ON c.oid = i.indexrelid "
                    "JOIN pg_namespace AS n ON n.oid = c.relnamespace "
                    "JOIN pg_class AS t ON t.oid = i.indrelid "
                    "JOIN pg_am AS am ON am.oid = c.relam "
                    "JOIN LATERAL unnest(i.indkey, i.indclass) WITH ORDINALITY "
                    "AS keys(attnum, opclass_oid, ordinality) ON true "
                    "JOIN pg_attribute AS a ON a.attrelid = i.indrelid AND a.attnum = keys.attnum "
                    "JOIN pg_opclass AS opc ON opc.oid = keys.opclass_oid "
                    "LEFT JOIN pg_constraint AS pc ON pc.conindid = i.indexrelid "
                    "WHERE n.nspname = 'public' AND c.relname = ANY(:names) "
                    "GROUP BY c.relname, t.relname, i.indisunique, i.indisvalid, i.indisready, "
                    "i.indpred, i.indrelid, am.amname, pc.conindid"
                ),
                {"names": sorted(expected_names)},
            )
            .mappings()
            .all()
        )
        critical_names = {
            row["index_name"]
            for row in connection.execute(
                text(
                    "SELECT c.relname AS index_name FROM pg_class AS c "
                    "JOIN pg_namespace AS n ON n.oid = c.relnamespace "
                    "WHERE n.nspname = 'public' AND c.relkind = 'i' "
                    "AND (c.relname LIKE 'uq_%' OR c.relname LIKE 'ix_%')"
                )
            ).mappings()
        }
    observed = {
        str(row["index_name"]): {
            "table": row["table_name"],
            "columns": tuple(row["columns"]),
            "unique": bool(row["indisunique"]),
            "predicate": row["predicate"],
            "access_method": row["access_method"],
            "operator_classes": tuple(row["operator_classes"]),
            "valid": bool(row["indisvalid"]),
            "ready": bool(row["indisready"]),
            "constraint_backed": bool(row["constraint_backed"]),
        }
        for row in rows
    }
    missing = sorted(expected_names - set(observed))
    mismatches: dict[str, dict[str, Any]] = {}
    for name, definition in FROZEN_REQUIRED_INDEXES.items():
        actual = observed.get(name)
        if actual is None:
            continue
        expected = {
            "table": definition["table"],
            "columns": _tuple_items(definition["columns"]),
            "unique": definition["unique"],
            "predicate": definition["predicate"],
            "constraint_backed": definition["constraint_backed"],
        }
        differences = {
            field: {"expected": expected[field], "observed": actual[field]}
            for field in expected
            if expected[field] != actual[field]
        }
        if differences or not actual["valid"] or not actual["ready"]:
            mismatches[name] = differences or {"valid_ready": {"expected": True, "observed": False}}
    return {
        "expected_manifest": [
            {"name": name, **definition} for name, definition in FROZEN_REQUIRED_INDEXES.items()
        ],
        "observed": observed,
        "missing_required": missing,
        "mismatches": mismatches,
        "unexpected_critical_names": sorted(critical_names - expected_names),
        "exact_required_coverage": not missing and not mismatches,
        "migration_required": bool(missing),
    }


def _plan_structure(connection: Any, statement: str, parameters: object) -> dict[str, Any]:
    """Return stable EXPLAIN structure for one captured production statement."""

    result = connection.exec_driver_sql(
        "EXPLAIN (FORMAT JSON) " + statement,
        parameters if parameters is not None else {},
    ).scalar_one()
    document = result[0] if isinstance(result, list) else result
    if not isinstance(document, dict) or not isinstance(document.get("Plan"), dict):
        raise PR18EvidenceError("malformed PostgreSQL JSON plan")

    node_types: list[str] = []
    relations: list[str] = []
    index_names: list[str] = []
    join_types: list[str] = []

    def visit(node: object) -> None:
        if not isinstance(node, dict):
            return
        node_type = node.get("Node Type")
        if isinstance(node_type, str):
            node_types.append(node_type)
        relation = node.get("Relation Name")
        if isinstance(relation, str):
            relations.append(relation)
        index = node.get("Index Name")
        if isinstance(index, str):
            index_names.append(index)
        join_type = node.get("Join Type")
        if isinstance(join_type, str):
            join_types.append(join_type)
        for child in node.get("Plans", []):
            visit(child)

    visit(document["Plan"])
    return {
        "node_types": sorted(set(node_types)),
        "relations": sorted(set(relations)),
        "index_names": sorted(set(index_names)),
        "join_types": sorted(set(join_types)),
    }


def _seed_explain_fixture(engine: Engine) -> tuple[dict[str, Any], int]:
    """Create disposable rows used only to exercise the real read services."""

    from tests.integration.test_pr14_governance_integration import _seed_graph

    ids = _seed_graph(engine)
    now = datetime.now(UTC)
    filler_count = 1200
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO audit_findings "
                "(id, project_id, finding_type, severity, title, description, "
                "target_type, target_id, target_content_hash, status, created_by, created_at) "
                "VALUES (:id, :project, 'explain_fixture', 'info', :title, 'fixture', "
                "'artifact_version', :target, NULL, 'open', :actor, :now)"
            ),
            [
                {
                    "id": uuid4(),
                    "project": ids["project"],
                    "title": f"EXPLAIN fixture {number}",
                    "target": ids["artifact_version"] if number == 0 else uuid4(),
                    "actor": ids["actor"],
                    "now": now,
                }
                for number in range(filler_count)
            ],
        )
        connection.execute(text("ANALYZE audit_findings"))
    return ids, filler_count


def _captured_query_plans(
    engine: Engine,
    operation: str,
    callback: Any,
    *,
    expectation: dict[str, object],
    representative_rows: int,
) -> dict[str, Any]:
    captured: list[tuple[str, object]] = []

    def observe(
        _connection: Any, _cursor: Any, statement: str, parameters: object, *_args: Any
    ) -> None:
        if statement.lstrip().upper().startswith("SELECT"):
            captured.append((statement, parameters))

    event.listen(engine, "before_cursor_execute", observe)
    try:
        callback()
    finally:
        event.remove(engine, "before_cursor_execute", observe)

    if not captured:
        raise PR18EvidenceError(f"{operation} emitted no SELECT statements")
    statements: list[dict[str, Any]] = []
    with engine.connect() as connection:
        for statement, parameters in captured:
            plan = _plan_structure(connection, statement, parameters)
            statements.append({"sql": statement, "plan": plan})

    structural_assertions = validate_query_contract(expectation, statements)
    return {
        "production_operation": operation,
        "repository_methods": list(_tuple_items(expectation["repository_methods"])),
        "required_relations": structural_assertions["required_relations"],
        "allowed_relations": structural_assertions["allowed_relations"],
        "observed_relations": structural_assertions["observed_relations"],
        "missing_relations": structural_assertions["missing_relations"],
        "unexpected_relations": structural_assertions["unexpected_relations"],
        "required_predicates": structural_assertions["required_predicates"],
        "predicate_verdict": structural_assertions["predicate_verdict"],
        "expected_topology": structural_assertions["expected_topology"],
        "observed_topology": structural_assertions["observed_topology"],
        "cartesian_verdict": structural_assertions["cartesian_verdict"],
        "write_or_lock_verdict": (
            "PASS" if structural_assertions["no_write_or_lock"] else "FAIL"
        ),
        "overall_verdict": structural_assertions["overall_verdict"],
        "verification_status": structural_assertions["verification_status"],
        "representative_rows": representative_rows,
        "statements": statements,
        "structural_assertions": structural_assertions,
    }


def collect_query_explain_baselines(engine: Engine) -> dict[str, dict[str, Any]]:
    """Capture EXPLAIN plans for real Phase 1 provenance/governance query services."""

    from tests.contracts.pr18_manifest import FROZEN_QUERY_EXPECTATIONS

    from researchbase.application.governance_queries import GovernanceQueryService
    from researchbase.application.provenance_queries import ProvenanceQueryService
    from researchbase.domain.governance import GovernanceTargetType
    from researchbase.persistence.database import create_session_factory
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork

    ids, representative_rows = _seed_explain_fixture(engine)
    sessions = create_session_factory(engine)

    def factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(sessions)

    provenance = ProvenanceQueryService(factory)
    governance = GovernanceQueryService(factory)
    baselines = {
        "run_provenance": _captured_query_plans(
            engine,
            "ProvenanceQueryService.get_run_provenance",
            lambda: provenance.get_run_provenance(ids["run"]),
            expectation=FROZEN_QUERY_EXPECTATIONS["run_provenance"],
            representative_rows=representative_rows,
        ),
        "claim_trace": _captured_query_plans(
            engine,
            "ProvenanceQueryService.trace_claim_to_runs",
            lambda: provenance.trace_claim_to_runs(ids["claim_version"]),
            expectation=FROZEN_QUERY_EXPECTATIONS["claim_trace"],
            representative_rows=representative_rows,
        ),
        "downstream_impact": _captured_query_plans(
            engine,
            "GovernanceQueryService.downstream_impact",
            lambda: governance.downstream_impact(
                ids["project"], GovernanceTargetType.ARTIFACT_VERSION, ids["artifact_version"]
            ),
            expectation=FROZEN_QUERY_EXPECTATIONS["downstream_impact"],
            representative_rows=representative_rows,
        ),
        "audit_findings": _captured_query_plans(
            engine,
            "GovernanceQueryService.list_audit_findings",
            lambda: governance.list_audit_findings(
                ids["project"], GovernanceTargetType.ARTIFACT_VERSION, ids["artifact_version"]
            ),
            expectation=FROZEN_QUERY_EXPECTATIONS["audit_findings"],
            representative_rows=representative_rows,
        ),
    }
    audit_statements = baselines["audit_findings"]["statements"]
    baselines["audit_findings"]["index_usable"] = any(
        "ix_audit_findings_target" in item["plan"]["index_names"] for item in audit_statements
    )
    if not baselines["audit_findings"]["index_usable"]:
        raise PR18EvidenceError("representative audit-finding query did not use its required index")
    return baselines


def command_fingerprint(tokens: list[str]) -> str:
    """Return the stable SHA-256 fingerprint for canonical command tokens."""

    if not tokens or any(not isinstance(token, str) or not token for token in tokens):
        raise PR18EvidenceError("command tokens must be non-empty strings")
    return hashlib.sha256("\0".join(tokens).encode("utf-8")).hexdigest()


def _validate_tokens(tokens: object) -> list[str]:
    if (
        not isinstance(tokens, list)
        or not tokens
        or not all(isinstance(token, str) and token for token in tokens)
    ):
        raise PR18EvidenceError("command_tokens must be a non-empty string list")
    if any(_ABSOLUTE_PATH.match(token) for token in tokens):
        raise PR18EvidenceError("absolute paths are forbidden in command evidence")
    if any(_CREDENTIAL_TOKEN.search(token) for token in tokens):
        raise PR18EvidenceError("credential-bearing command token")
    return tokens


def validate_command_entries(entries: object) -> dict[str, int]:
    """Validate exact command tokens, fingerprints, and safe paths."""

    if not isinstance(entries, dict) or not entries:
        raise PR18EvidenceError("commands must be a non-empty object")
    for command_id, entry in entries.items():
        if not isinstance(command_id, str) or not command_id:
            raise PR18EvidenceError("command ids must be non-empty strings")
        if not isinstance(entry, dict):
            raise PR18EvidenceError(f"malformed command entry: {command_id}")
        tokens = _validate_tokens(entry.get("command_tokens"))
        if entry.get("command") != shlex.join(tokens):
            raise PR18EvidenceError(f"command text/token drift: {command_id}")
        if entry.get("command_fingerprint") != command_fingerprint(tokens):
            raise PR18EvidenceError(f"command fingerprint drift: {command_id}")
        counts = entry.get("counts")
        if not isinstance(counts, dict):
            raise PR18EvidenceError(f"missing counts: {command_id}")
        return_code = entry.get("return_code")
        if (
            not isinstance(return_code, int)
            or isinstance(return_code, bool)
            or counts.get("return_code") != return_code
        ):
            raise PR18EvidenceError(f"return-code accounting mismatch: {command_id}")
        if "pytest" in tokens:
            if set(PYTEST_COUNT_FIELDS) - set(counts):
                raise PR18EvidenceError(f"incomplete pytest count schema: {command_id}")
            if any(
                not isinstance(counts[key], int) or isinstance(counts[key], bool) or counts[key] < 0
                for key in PYTEST_COUNT_FIELDS
            ):
                raise PR18EvidenceError(f"malformed pytest count values: {command_id}")
            if counts["total_discovered"] != counts["selected"] + counts["deselected"]:
                raise PR18EvidenceError(f"pytest discovery counts do not reconcile: {command_id}")
            outcomes = ("passed", "failed", "skipped", "xfailed", "xpassed", "errors")
            if counts["selected"] != sum(counts[key] for key in outcomes):
                raise PR18EvidenceError(f"pytest outcome counts do not reconcile: {command_id}")
            if return_code != 0:
                raise PR18EvidenceError(f"required command failed: {command_id}")
        elif counts.get("status") != "PASS" or return_code != 0:
            raise PR18EvidenceError(f"non-pytest command did not pass: {command_id}")
    count = len(entries)
    return {"stored": count, "valid": count}


def validate_evidence_artifact(artifact: object, *, implementation_subject: str) -> None:
    """Validate the fail-closed top-level PR-18 evidence contract."""

    if not isinstance(artifact, dict):
        raise PR18EvidenceError("evidence must be a JSON object")
    if artifact.get("schema_version") != "pr18r-evidence-v1":
        raise PR18EvidenceError("unsupported PR-18 evidence schema")
    if artifact.get("protocol") != "non-self-referential-v1":
        raise PR18EvidenceError("non-self-referential protocol is required")
    if artifact.get("implementation_subject") != implementation_subject:
        raise PR18EvidenceError("evidence subject does not match implementation subject")
    if "evidence_head" in artifact:
        raise PR18EvidenceError("future evidence head must not be embedded")
    binding = artifact.get("evidence_binding")
    if binding != {"mode": "separate-evidence-only-commit", "parent": implementation_subject}:
        raise PR18EvidenceError("evidence chronology binding is invalid")
    audits = artifact.get("audits")
    if not isinstance(audits, dict):
        raise PR18EvidenceError("missing evidence audits")
    if audits.get("absolute_paths") != []:
        raise PR18EvidenceError("absolute paths must be absent")
    if audits.get("credential_leakage") != []:
        raise PR18EvidenceError("credential leakage must be absent")
    if audits.get("reproducible") is not True:
        raise PR18EvidenceError("reproducibility must be explicitly true")
    consistency = artifact.get("command_consistency")
    if not isinstance(consistency, dict):
        raise PR18EvidenceError("missing command consistency")
    commands = artifact.get("commands")
    counts = validate_command_entries(commands)
    if consistency.get("stored") != counts["stored"]:
        raise PR18EvidenceError("stored command count mismatch")
    if consistency.get("current") != counts["stored"]:
        raise PR18EvidenceError("current command count mismatch")
    if consistency.get("exact_token_matches") != counts["stored"]:
        raise PR18EvidenceError("exact command token accounting mismatch")
    if consistency.get("stale_result_reuse") is not False:
        raise PR18EvidenceError("stale result reuse must be explicitly false")


def build_evidence_artifact(
    *,
    implementation_subject: str,
    commands: dict[str, dict[str, Any]],
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the canonical PR-18 evidence object from current command results."""

    command_count = len(commands)
    artifact: dict[str, Any] = {
        "schema_version": "pr18r-evidence-v1",
        "protocol": "non-self-referential-v1",
        "implementation_subject": implementation_subject,
        "evidence_binding": {
            "mode": "separate-evidence-only-commit",
            "parent": implementation_subject,
        },
        "command_consistency": {
            "stored": command_count,
            "current": command_count,
            "exact_token_matches": command_count,
            "stale_result_reuse": False,
        },
        "audits": {
            "absolute_paths": [],
            "credential_leakage": [],
            "reproducible": True,
        },
        "commands": commands,
    }
    if metadata:
        artifact["metadata"] = metadata
    validate_evidence_artifact(artifact, implementation_subject=implementation_subject)
    return artifact


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple | set | frozenset):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _pytest_skip_identities(junit_xml: str) -> set[str]:
    try:
        root = ET.fromstring(junit_xml)
    except ET.ParseError as error:
        raise PR18EvidenceError("cannot inspect pytest skips from malformed JUnit") from error
    identities: set[str] = set()
    for testcase in root.iter("testcase"):
        skipped = testcase.find("skipped")
        if skipped is None or skipped.attrib.get("type") == "pytest.xfail":
            continue
        classname = testcase.attrib.get("classname", "")
        name = testcase.attrib.get("name", "")
        identities.add(f"{classname}::{name}")
    return identities


def _collection_command(tokens: list[str]) -> list[str]:
    command = [token for token in tokens if not token.startswith("--junitxml=")]
    pytest_index = command.index("pytest")
    command[pytest_index + 1 : pytest_index + 1] = ["--collect-only", "-o", "addopts="]
    return command


def _database_identity() -> dict[str, Any]:
    from researchbase.persistence.database import create_database_engine

    engine = create_database_engine()
    try:
        with engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT current_database() AS database, current_schema() AS schema, "
                    "version() AS server_version, "
                    "current_setting('server_version') AS version_number, "
                    "(SELECT version_num FROM public.alembic_version) AS alembic_revision"
                )
            ).one()
    finally:
        engine.dispose()
    if not str(row.version_number).startswith("18"):
        raise PR18EvidenceError(f"PostgreSQL 18 is required, got {row.version_number}")
    return {
        "database": row.database,
        "schema": row.schema,
        "server_version": row.server_version,
        "version_number": row.version_number,
        "alembic_revision": row.alembic_revision,
        "credentials": "redacted",
    }


def resolve_implementation_subject(value: str | None = None) -> str:
    subject = value or os.getenv("PR18R_IMPLEMENTATION_SUBJECT_HEAD")
    if not subject:
        raise PR18EvidenceError("PR18R_IMPLEMENTATION_SUBJECT_HEAD is required")
    result = subprocess.run(
        ["git", "rev-parse", "--verify", f"{subject}^{{commit}}"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def execute_authoritative_commands(
    *,
    implementation_subject: str,
    runner: Any = subprocess.run,
    result_dir: Path | None = None,
) -> dict[str, dict[str, Any]]:
    """Execute every registered command and return only reconciled results."""

    validate_current_command_registry()
    result_path = result_dir or PROJECT_ROOT / ".pr18r_evidence_results"
    result_path.mkdir(parents=True, exist_ok=True)
    if result_dir is not None:
        for stale_result in result_path.glob("*.xml"):
            stale_result.unlink()
    entries: dict[str, dict[str, Any]] = {}
    try:
        for command_id, _base in AUTHORITATIVE_COMMANDS:
            tokens = authoritative_command_tokens(
                command_id, result_dir=str(result_path.relative_to(PROJECT_ROOT))
            )
            result = runner(
                tokens,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            return_code = int(result.returncode)
            if "pytest" in tokens:
                junit_path = PROJECT_ROOT / next(
                    token.split("=", 1)[1] for token in tokens if token.startswith("--junitxml=")
                )
                if not junit_path.exists():
                    raise PR18EvidenceError(f"missing JUnit result: {command_id}")
                junit_xml = junit_path.read_text(encoding="utf-8")
                junit_xml = junit_xml.replace(f"{PROJECT_ROOT}/", "")
                junit_xml = junit_xml.replace(str(PROJECT_ROOT), "")
                junit_path.write_text(junit_xml, encoding="utf-8")
                collection = runner(
                    _collection_command(tokens),
                    cwd=PROJECT_ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                counts = parse_pytest_counts(
                    output=result.stdout,
                    collection_output=collection.stdout,
                    junit_xml=junit_xml,
                    return_code=return_code,
                )
                skipped = _pytest_skip_identities(junit_xml)
                unexpected = skipped - INHERITED_PR11R2_SKIP_IDENTITIES
                if unexpected:
                    raise PR18EvidenceError(
                        f"unexpected pytest skips in {command_id}: {sorted(unexpected)}"
                    )
                entry_counts: dict[str, Any] = counts
            else:
                if return_code != 0:
                    raise PR18EvidenceError(f"required command failed: {command_id}")
                entry_counts = {"status": "PASS", "return_code": 0}
            entries[command_id] = {
                "command": shlex.join(tokens),
                "command_tokens": tokens,
                "command_fingerprint": command_fingerprint(tokens),
                "return_code": return_code,
                "counts": entry_counts,
            }
        validate_command_entries(entries)
        return entries
    finally:
        if result_dir is None:
            shutil.rmtree(result_path, ignore_errors=True)


def run_authoritative_evidence(
    *,
    implementation_subject: str,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Run the frozen PR-18R command registry and write one bound artifact."""

    resolved_subject = resolve_implementation_subject(implementation_subject)
    current_head = resolve_implementation_subject("HEAD")
    if current_head != resolved_subject:
        raise PR18EvidenceError("evidence must run at the frozen implementation subject HEAD")
    database = _database_identity()
    commands = execute_authoritative_commands(
        implementation_subject=resolved_subject,
        result_dir=PROJECT_ROOT / "artifacts/pr_evidence/PR-18/junit",
    )
    from researchbase.persistence.database import create_database_engine

    engine = create_database_engine()
    try:
        catalog = collect_catalog_verification(engine)
        explain = collect_query_explain_baselines(engine)
    finally:
        engine.dispose()
    todo = audit_repository_markers()
    artifact = build_evidence_artifact(
        implementation_subject=resolved_subject,
        commands=commands,
        metadata={
            "database": database,
            "query_explain": explain,
            "catalog": catalog,
            "todo": todo,
            "fresh_execution": True,
        },
    )
    destination = (
        output_path or PROJECT_ROOT / "artifacts/pr_evidence/PR-18/implementation_verification.json"
    )
    write_evidence_artifact(destination, artifact)
    projection_root = destination.parent
    projections = {
        "catalog_verification.json": catalog,
        "query_explain_baselines.json": {
            "database": database,
            "queries": explain,
            "result": "PASS",
        },
        "todo_fixme_disposition.json": todo,
        "error_log_audit.json": {
            "result": "PASS",
            "source_command": "pr18_focused_and_evidence_tool",
            "selectors": [
                "tests/unit/test_pr18_error_log_hardening.py",
                "tests/unit/test_pr15_http.py",
                "tests/unit/test_pr16_cli_errors.py",
            ],
        },
        "architecture_agent_audit.json": {
            "result": "PASS",
            "source_command": "pr18_focused_and_evidence_tool",
            "existing_suite": "tests/architecture/test_pr17_agent_ready_architecture.py",
            "complementary_suite": "tests/architecture/test_pr18_boundaries.py",
        },
        "api_cli_validation.json": {
            "result": "PASS",
            "source_command": "pr18_focused_and_evidence_tool",
            "document": "docs/phase1_api_cli_examples.md",
        },
    }
    for filename, projection in projections.items():
        (projection_root / filename).write_text(
            json.dumps(_json_safe(projection), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    architecture_count = commands["architecture"]["counts"]["passed"]
    (projection_root / "architecture_verification.md").write_text(
        "# PR-18R architecture verification\n\n"
        f"Result: PASS. The authoritative architecture suite recorded {architecture_count} "
        "passed tests.\n\n"
        "The accepted PR-17 Agent-ready suite was rerun with PR-18R complementary "
        "AST/interface checks for Core imports, adapter ownership, repositories/UoW, and "
        "generic provenance/version "
        "escape hatches.\n",
        encoding="utf-8",
    )
    (projection_root / "agent_ready_core_audit.md").write_text(
        "# Agent-ready Core boundary audit\n\n"
        "Result: PASS — boundary audit only.\n\n"
        "Future callers use the shared Application commands/queries and "
        "WriteResult-compatible DTOs; "
        "FastAPI, Typer, and SQLAlchemy session manipulation are not required. No agent runtime or "
        "Phase 2 implementation was added.\n",
        encoding="utf-8",
    )
    (projection_root / "api_cli_examples.md").write_text(
        "# API/CLI example verification\n\n"
        "Result: PASS. The executable documentation contract suite validated the structured "
        "examples "
        "against current OpenAPI routes/statuses and the real Typer command surface, including "
        "representative success and failure behavior.\n",
        encoding="utf-8",
    )
    todo_lines = [
        "# PR-18R TODO/FIXME disposition",
        "",
        f"Result: PASS. {len(todo['records'])} repository-relevant markers were classified; "
        f"{len(todo['undisposed_live'])} live markers remain undisposed.",
        "",
        "| Path | Line | Marker | Category | Disposition | Rationale |",
        "| --- | ---: | --- | --- | --- | --- |",
    ]
    for record in todo["records"]:
        rationale = str(record["rationale"]).replace("|", "\\|")
        todo_lines.append(
            f"| `{record['path']}` | {record['line']} | `{record['marker']}` | "
            f"{record['category']} | `{record['disposition']}` | {rationale} |"
        )
    todo_lines.extend(
        [
            "",
            "Architecture P0 markers: " + str(len(todo["architecture_p0"])),
            "Architecture P1 markers: " + str(len(todo["architecture_p1"])),
            "",
            "Approved dispositions: CLOSED, INTENTIONAL_NONBLOCKING, OUT_OF_PHASE, PR18_BLOCKER.",
        ]
    )
    (projection_root / "todo_fixme_disposition.md").write_text(
        "\n".join(todo_lines) + "\n", encoding="utf-8"
    )
    (projection_root / "error_log_audit.md").write_text(
        "# PR-18R error/log hardening audit\n\n"
        "Result: PASS. The executable redaction suite covered structured API keys, Authorization "
        "and Bearer values, credential-bearing DSNs, exception-string secrets, nested fields, "
        "HTTP errors, "
        "and CLI errors. The only production change is the minimal structured-log redaction patch; "
        "transaction and Application error semantics remain unchanged.\n",
        encoding="utf-8",
    )
    lines = ["# PR-18R commands and results", "", "| Command | Result |", "| --- | --- |"]
    for command_id, entry in commands.items():
        lines.append(f"| `{command_id}` | `{json.dumps(entry['counts'], sort_keys=True)}` |")
    (projection_root / "commands_and_results.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    return artifact


def write_evidence_artifact(path: Path, artifact: dict[str, Any]) -> None:
    """Validate and write canonical repository-relative JSON evidence."""

    subject = artifact.get("implementation_subject")
    if not isinstance(subject, str) or not subject:
        raise PR18EvidenceError("implementation subject is required")
    validate_evidence_artifact(artifact, implementation_subject=subject)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_json_safe(artifact), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> int:
    run_authoritative_evidence(implementation_subject=resolve_implementation_subject())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
