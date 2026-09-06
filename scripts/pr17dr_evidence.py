"""Generate PR-17DR catalog and invariant evidence from PostgreSQL."""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import re
import shlex
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

_sqlalchemy = importlib.import_module("sqlalchemy")
text = _sqlalchemy.text
_database = importlib.import_module("researchbase.persistence.database")
create_database_engine = _database.create_database_engine
_manifest = importlib.import_module("tests.contracts.pr17dr_manifest")
PR17D_FUNCTIONS = _manifest.PR17D_FUNCTIONS
PR17D_TRIGGERS = _manifest.PR17D_TRIGGERS

OUTPUT_DIR = Path("artifacts/pr_evidence/PR-17DR2")
PROTOCOL = "non-self-referential-v1"
DISCARDED_V15_FUNCTION_COUNT = 64
IMPLEMENTATION_SUBJECT_ENV = "PR17DR2_IMPLEMENTATION_SUBJECT_HEAD"

FUNCTION_DETAILS: tuple[dict[str, Any], ...] = (
    {
        "function_id": "FN-01",
        "name": "pr17d_guard_research_question_version",
        "role": "version guard",
        "table": "research_question_versions",
        "invariants": ["INV-VERSION-01"],
        "consumers": [
            "pr17d_research_question_version_update",
            "pr17d_research_question_version_delete",
        ],
        "error_identifiers": ["P17D1", "P17D2"],
    },
    {
        "function_id": "FN-02",
        "name": "pr17d_guard_hypothesis_version",
        "role": "version guard",
        "table": "hypothesis_versions",
        "invariants": ["INV-VERSION-01"],
        "consumers": ["pr17d_hypothesis_version_update", "pr17d_hypothesis_version_delete"],
        "error_identifiers": ["P17D1", "P17D2"],
    },
    {
        "function_id": "FN-03",
        "name": "pr17d_guard_experiment_spec_version",
        "role": "version guard",
        "table": "experiment_spec_versions",
        "invariants": ["INV-VERSION-01"],
        "consumers": [
            "pr17d_experiment_spec_version_update",
            "pr17d_experiment_spec_version_delete",
        ],
        "error_identifiers": ["P17D1", "P17D2"],
    },
    {
        "function_id": "FN-04",
        "name": "pr17d_guard_artifact_version",
        "role": "version guard",
        "table": "artifact_versions",
        "invariants": ["INV-VERSION-01"],
        "consumers": ["pr17d_artifact_version_update", "pr17d_artifact_version_delete"],
        "error_identifiers": ["P17D1", "P17D2"],
    },
    {
        "function_id": "FN-05",
        "name": "pr17d_guard_metric_definition_version",
        "role": "version guard",
        "table": "metric_definition_versions",
        "invariants": ["INV-VERSION-01"],
        "consumers": [
            "pr17d_metric_definition_version_update",
            "pr17d_metric_definition_version_delete",
        ],
        "error_identifiers": ["P17D1", "P17D2"],
    },
    {
        "function_id": "FN-06",
        "name": "pr17d_guard_claim_version",
        "role": "version guard",
        "table": "claim_versions",
        "invariants": ["INV-VERSION-01"],
        "consumers": ["pr17d_claim_version_update", "pr17d_claim_version_delete"],
        "error_identifiers": ["P17D1", "P17D2"],
    },
    {
        "function_id": "FN-07",
        "name": "pr17d_reject_dataset_snapshot_mutation",
        "role": "immutable-record guard",
        "table": "dataset_snapshots",
        "invariants": ["INV-IMMUTABLE-01"],
        "consumers": ["pr17d_dataset_snapshot_update", "pr17d_dataset_snapshot_delete"],
        "error_identifiers": ["P17D1"],
    },
    {
        "function_id": "FN-08",
        "name": "pr17d_reject_measurement_mutation",
        "role": "immutable-record guard",
        "table": "measurements",
        "invariants": ["INV-IMMUTABLE-02"],
        "consumers": ["pr17d_measurement_update", "pr17d_measurement_delete"],
        "error_identifiers": ["P17D1"],
    },
    {
        "function_id": "FN-09",
        "name": "pr17d_reject_statistical_result_mutation",
        "role": "immutable-record guard",
        "table": "statistical_results",
        "invariants": ["INV-IMMUTABLE-03"],
        "consumers": ["pr17d_statistical_result_update", "pr17d_statistical_result_delete"],
        "error_identifiers": ["P17D1"],
    },
    {
        "function_id": "FN-10",
        "name": "pr17d_reject_statistical_result_input_mutation",
        "role": "immutable-record guard",
        "table": "statistical_result_inputs",
        "invariants": ["INV-IMMUTABLE-04"],
        "consumers": [
            "pr17d_statistical_result_input_update",
            "pr17d_statistical_result_input_delete",
        ],
        "error_identifiers": ["P17D1"],
    },
    {
        "function_id": "FN-11",
        "name": "pr17d_guard_run",
        "role": "Run guard",
        "table": "runs",
        "invariants": ["INV-RUN-01"],
        "consumers": ["pr17d_run_update", "pr17d_run_delete"],
        "error_identifiers": ["P17D1", "P17D2"],
    },
    {
        "function_id": "FN-12",
        "name": "pr17d_guard_run_input_parent",
        "role": "parent-state guard",
        "table": "run_dataset_inputs, run_artifact_inputs",
        "invariants": ["INV-RUNINPUT-01"],
        "consumers": [
            name
            for name, _table, _event, function in PR17D_TRIGGERS
            if function == "pr17d_guard_run_input_parent"
        ],
        "error_identifiers": ["P17D1", "P17D3"],
    },
    {
        "function_id": "FN-13",
        "name": "pr17d_guard_evidence_relation_parent",
        "role": "parent-state guard",
        "table": "evidence_relations, claim_versions",
        "invariants": ["INV-EVIDENCE-01"],
        "consumers": [
            name
            for name, _table, _event, function in PR17D_TRIGGERS
            if function == "pr17d_guard_evidence_relation_parent"
        ],
        "error_identifiers": ["P17D1", "P17D3"],
    },
    {
        "function_id": "FN-14",
        "name": "pr17d_reject_audit_finding_mutation",
        "role": "immutable-record guard",
        "table": "audit_findings",
        "invariants": ["INV-GOV-01"],
        "consumers": ["pr17d_audit_finding_update", "pr17d_audit_finding_delete"],
        "error_identifiers": ["P17D1"],
    },
    {
        "function_id": "FN-15",
        "name": "pr17d_guard_audit_finding_transition",
        "role": "transition guard",
        "table": "audit_findings",
        "invariants": ["INV-GOV-01"],
        "consumers": ["pr17d_audit_finding_transition"],
        "error_identifiers": ["P17D2"],
    },
    {
        "function_id": "FN-16",
        "name": "pr17d_reject_impact_assessment_mutation",
        "role": "immutable-record guard",
        "table": "impact_assessments",
        "invariants": ["INV-GOV-02"],
        "consumers": ["pr17d_impact_assessment_update", "pr17d_impact_assessment_delete"],
        "error_identifiers": ["P17D1"],
    },
    {
        "function_id": "FN-17",
        "name": "pr17d_reject_impact_target_mutation",
        "role": "immutable-record guard",
        "table": "impact_targets",
        "invariants": ["INV-GOV-03"],
        "consumers": ["pr17d_impact_target_update", "pr17d_impact_target_delete"],
        "error_identifiers": ["P17D1"],
    },
    {
        "function_id": "FN-18",
        "name": "pr17d_reject_correction_record_mutation",
        "role": "immutable-record guard",
        "table": "correction_records",
        "invariants": ["INV-GOV-04"],
        "consumers": ["pr17d_correction_record_update", "pr17d_correction_record_delete"],
        "error_identifiers": ["P17D1"],
    },
)

INVARIANT_TESTS = {
    "INV-VERSION-01": [
        "tests/integration/test_pr17dr2_adversarial.py",
        "tests/integration/test_pr17dr_adversarial.py",
        "tests/e2e/test_phase1_historical_exactness.py",
        "tests/integration/test_pr09r2_proof.py",
    ],
    "INV-RUN-01": [
        "tests/integration/test_pr17dr2_adversarial.py",
        "tests/integration/test_pr17dr_adversarial.py",
        "tests/integration/test_pr09_application.py",
        "tests/integration/test_pr10_application.py",
    ],
    "INV-RUNINPUT-01": [
        "tests/integration/test_pr17dr2_concurrency.py",
        "tests/integration/test_pr17dr_adversarial.py",
        "tests/e2e/test_phase1_concurrency_acceptance.py",
    ],
    "INV-EVIDENCE-01": [
        "tests/integration/test_pr17dr2_adversarial.py",
        "tests/integration/test_pr17dr_adversarial.py",
        "tests/integration/test_pr12_closure.py",
    ],
    "INV-IMMUTABLE-01": ["tests/integration/test_pr06_application.py"],
    "INV-IMMUTABLE-02": ["tests/integration/test_pr10_application.py"],
    "INV-IMMUTABLE-03": ["tests/integration/test_pr11_application.py"],
    "INV-IMMUTABLE-04": ["tests/integration/test_pr11_application.py"],
    "INV-GOV-01": [
        "tests/integration/test_pr17dr_adversarial.py",
        "tests/integration/test_pr17dr_adversarial.py",
        "tests/integration/test_pr14_governance_integration.py",
    ],
    "INV-GOV-02": ["tests/integration/test_pr14_governance_integration.py"],
    "INV-GOV-03": ["tests/integration/test_pr14_governance_integration.py"],
    "INV-GOV-04": ["tests/integration/test_pr14_governance_integration.py"],
}


def _subject_head() -> str:
    value = os.getenv(IMPLEMENTATION_SUBJECT_ENV)
    if not value:
        raise RuntimeError(
            f"{IMPLEMENTATION_SUBJECT_ENV} is required; evidence must name a frozen subject"
        )
    return subprocess.check_output(
        ["git", "rev-parse", "--verify", value], cwd=PROJECT_ROOT, text=True
    ).strip()


def _database_identity(engine: Any) -> dict[str, Any]:
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT current_database() AS database, current_schema() AS schema, "
                "version() AS server_version, current_setting('server_version') AS version_number, "
                "(SELECT version_num FROM public.alembic_version) AS alembic_revision"
            )
        ).one()
    return {
        "database": row.database,
        "schema": row.schema,
        "server_version": row.server_version,
        "version_number": row.version_number,
        "alembic_revision": row.alembic_revision,
        "credentials": "redacted",
    }


_SUMMARY_COUNT = re.compile(
    r"(?P<count>\d+) (?P<kind>passed|failed|skipped|deselected|xfailed|xpassed|errors?)"
)
_COLLECTION_COUNT = re.compile(
    r"(?:(?P<selected>\d+)/)?(?P<total>\d+) tests? collected"
    r"(?: \((?P<deselected>\d+) deselected\))?"
)
_SKIP_DETAIL = re.compile(r"SKIPPED \[(?P<count>\d+)\] (?P<nodeid>[^:]+:\d+): (?P<reason>.*)")


def _summary_counts(output: str) -> dict[str, int]:
    counts = {
        kind: 0
        for kind in ("passed", "failed", "skipped", "deselected", "xfailed", "xpassed", "error")
    }
    for line in reversed(output.splitlines()):
        matches = list(_SUMMARY_COUNT.finditer(line))
        if matches:
            for match in matches:
                kind = (
                    "error"
                    if match.group("kind") in {"error", "errors"}
                    else match.group("kind")
                )
                counts[kind] = int(match.group("count"))
            break
    return counts


def _collection_counts(output: str) -> dict[str, int] | None:
    matches = list(_COLLECTION_COUNT.finditer(output))
    if not matches:
        return None
    match = matches[-1]
    total = int(match.group("total"))
    selected = int(match.group("selected") or total)
    deselected = int(match.group("deselected") or 0)
    if total != selected + deselected:
        return None
    return {"total_discovered": total, "collected": selected, "deselected": deselected}


def _validated_pytest_counts(
    output: str, collection_output: str, junit_xml: str | None
) -> dict[str, int] | None:
    collection = _collection_counts(collection_output)
    if collection is None or junit_xml is None:
        return None
    try:
        root = ET.fromstring(junit_xml)
    except ET.ParseError:
        return None
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    if not suites:
        return None
    try:
        junit = {
            key: sum(int(suite.attrib.get(attribute, "0")) for suite in suites)
            for key, attribute in (
                ("collected", "tests"),
                ("failed", "failures"),
                ("error", "errors"),
                ("junit_skipped", "skipped"),
            )
        }
    except ValueError:
        return None

    summary = _summary_counts(output)
    xfailed = summary["xfailed"]
    xpassed = summary["xpassed"]
    skipped = junit["junit_skipped"] - xfailed
    passed = (
        junit["collected"]
        - junit["failed"]
        - junit["error"]
        - junit["junit_skipped"]
        - xpassed
    )
    counts = {
        **collection,
        "passed": passed,
        "failed": junit["failed"],
        "skipped": skipped,
        "xfailed": xfailed,
        "xpassed": xpassed,
        "error": junit["error"],
    }
    if min(counts.values()) < 0 or junit["collected"] != collection["collected"]:
        return None
    if collection["collected"] != sum(
        counts[key] for key in ("passed", "failed", "skipped", "xfailed", "xpassed", "error")
    ):
        return None
    for key in ("passed", "failed", "skipped", "xfailed", "xpassed", "error"):
        if summary[key] and summary[key] != counts[key]:
            return None
    if summary["deselected"] and summary["deselected"] != counts["deselected"]:
        return None
    return counts


def _skip_details(output: str) -> list[dict[str, Any]]:
    return [
        {
            "count": int(match.group("count")),
            "nodeid": match.group("nodeid"),
            "reason": match.group("reason"),
            "classification": (
                "inherited_pr11r2"
                if match.group("nodeid").startswith("tests/integration/test_pr11r2_migration.py")
                and "PR11R2_MIGRATION_DB_URL" in match.group("reason")
                else "current_remediation"
            ),
        }
        for match in _SKIP_DETAIL.finditer(output)
    ]


def _run_verification(
    command_id: str, command: list[str], database: dict[str, Any] | None
) -> dict[str, Any]:
    command_tokens = _authoritative_command_tokens(command_id, command)
    command_text = shlex.join(command_tokens)
    junit_path = PROJECT_ROOT / ".pr17dr_evidence_results" / f"{command_id}.xml"
    if "pytest" in command_tokens:
        junit_path.parent.mkdir(exist_ok=True)
    completed = subprocess.run(
        command_tokens,
        capture_output=True,
        text=True,
        check=False,
        cwd=PROJECT_ROOT,
        env=os.environ.copy(),
    )
    collection: dict[str, Any] | None = None
    counts: dict[str, int] | None = None
    if "pytest" in command_tokens:
        collect_command = [token for token in command_tokens if not token.startswith("--junitxml=")]
        pytest_index = collect_command.index("pytest")
        collect_command.insert(pytest_index + 1, "--collect-only")
        collect_command.insert(pytest_index + 2, "-o")
        collect_command.insert(pytest_index + 3, "addopts=")
        collected = subprocess.run(
            collect_command,
            capture_output=True,
            text=True,
            check=False,
            cwd=PROJECT_ROOT,
            env=os.environ.copy(),
        )
        collection = {
            "command": shlex.join(collect_command),
            "return_code": collected.returncode,
            **(_collection_counts(collected.stdout + collected.stderr) or {}),
        }
        junit_xml = junit_path.read_text(encoding="utf-8") if junit_path.exists() else None
        counts = _validated_pytest_counts(
            completed.stdout + completed.stderr,
            collected.stdout + collected.stderr,
            junit_xml,
        )
        if junit_path.exists():
            junit_path.unlink()
        if junit_path.parent.exists() and not any(junit_path.parent.iterdir()):
            junit_path.parent.rmdir()
    output = completed.stdout + completed.stderr
    skip_details = _skip_details(output)
    if completed.returncode != 0:
        verdict = "FAIL"
    elif collection is not None and (
        collection["return_code"] != 0 or counts is None
    ):
        verdict = "NOT_VERIFIED"
    elif counts is not None and (counts["failed"] or counts["error"]):
        verdict = "FAIL"
    else:
        verdict = "PASS"
    return {
        "command_id": command_id,
        "command": command_text,
        "command_tokens": command_tokens,
        "command_fingerprint": _command_fingerprint(command_tokens),
        "executed": True,
        "return_code": completed.returncode,
        "counts": counts if counts is not None else None,
        "skips": skip_details,
        "collection": collection,
        "database": database,
        "verdict": verdict,
    }


def _function_manifest_rows() -> list[dict[str, Any]]:
    by_name = {row["name"]: row for row in FUNCTION_DETAILS}
    rows: list[dict[str, Any]] = []
    for index, name in enumerate(PR17D_FUNCTIONS, start=1):
        detail = by_name[name]
        rows.append(
            {
                "function_id": detail["function_id"],
                "name": name,
                "schema": "public",
                "classification": detail["role"],
                "owning_table": detail["table"],
                "invariants": detail["invariants"],
                "signature": {"identity_arguments": [], "result": "trigger", "language": "plpgsql"},
                "consumer_triggers": detail["consumers"],
                "dependencies": {"tables": detail["table"].split(", "), "functions": []},
                "stages": {
                    "upgrade": f"U04.{index:02d}",
                    "downgrade": f"D03.{len(PR17D_FUNCTIONS) - index + 1:02d}",
                },
                "catalog_query_id": f"U07-FN-{index:02d}",
                "expected_projection": {
                    "schema": "public",
                    "name": name,
                    "identity_arguments": [],
                    "result": "trigger",
                    "language": "plpgsql",
                },
                "stable_error_identifiers": detail["error_identifiers"],
            }
        )
    return rows


def _trigger_manifest_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, (name, table, event, function) in enumerate(PR17D_TRIGGERS, start=1):
        rows.append(
            {
                "trigger_id": f"TR-{index:02d}",
                "name": name,
                "schema": "public",
                "owning_table": table,
                "invariants": next(
                    row["invariants"] for row in FUNCTION_DETAILS if row["name"] == function
                ),
                "timing": "BEFORE",
                "events": [event],
                "level": "ROW",
                "bound_function": {"schema": "public", "name": function},
                "dependencies": {"tables": [table], "functions": [function]},
                "stages": {
                    "upgrade": f"U05.{index:02d}",
                    "downgrade": f"D01.{len(PR17D_TRIGGERS) - index + 1:02d}",
                },
                "catalog_query_id": f"U07-TR-{index:02d}",
                "expected_projection": {
                    "schema": "public",
                    "name": name,
                    "table": table,
                    "timing": "BEFORE",
                    "events": [event],
                    "level": "ROW",
                    "bound_function": {"schema": "public", "name": function},
                    "enabled": "O",
                },
                "stable_error_identifiers": next(
                    row["error_identifiers"] for row in FUNCTION_DETAILS if row["name"] == function
                ),
            }
        )
    return rows


def _observed_catalog(engine: Any) -> dict[str, Any]:
    with engine.connect() as connection:
        functions = [
            {
                "schema": row.schema_name,
                "name": row.name,
                "identity_arguments": (
                    [] if not row.identity_arguments else row.identity_arguments
                ),
                "result": row.result,
                "language": row.language,
            }
            for row in connection.execute(
                text(
                    "SELECT n.nspname AS schema_name, p.proname AS name, "
                    "pg_get_function_identity_arguments(p.oid) AS identity_arguments, "
                    "pg_get_function_result(p.oid) AS result, l.lanname AS language "
                    "FROM pg_proc AS p JOIN pg_namespace AS n ON n.oid=p.pronamespace "
                    "JOIN pg_language AS l ON l.oid=p.prolang "
                    "WHERE n.nspname='public' AND left(p.proname,6)='pr17d_' "
                    "ORDER BY p.proname"
                )
            )
        ]
        triggers = [
            {
                "schema": row.schema_name,
                "name": row.name,
                "table": row.table_name,
                "timing": row.timing,
                "events": list(row.events),
                "level": row.level,
                "bound_function": {"schema": row.function_schema, "name": row.function_name},
                "enabled": row.enabled,
            }
            for row in connection.execute(
                text(
                    "SELECT tn.nspname AS schema_name, t.tgname AS name, c.relname AS table_name, "
                    "CASE WHEN (t.tgtype & 2)=2 THEN 'BEFORE' "
                    "WHEN (t.tgtype & 64)=64 THEN 'INSTEAD OF' ELSE 'AFTER' END AS timing, "
                    "array_remove(ARRAY[CASE WHEN (t.tgtype & 4)=4 THEN 'INSERT'::text END, "
                    "CASE WHEN (t.tgtype & 8)=8 THEN 'DELETE'::text END, "
                    "CASE WHEN (t.tgtype & 16)=16 THEN 'UPDATE'::text END, "
                    "CASE WHEN (t.tgtype & 32)=32 THEN 'TRUNCATE'::text END], NULL) AS events, "
                    "CASE WHEN (t.tgtype & 1)=1 THEN 'ROW' ELSE 'STATEMENT' END AS level, "
                    "pn.nspname AS function_schema, p.proname AS function_name, "
                    "t.tgenabled AS enabled "
                    "FROM pg_trigger AS t JOIN pg_class AS c ON c.oid=t.tgrelid "
                    "JOIN pg_namespace AS tn ON tn.oid=c.relnamespace "
                    "JOIN pg_proc AS p ON p.oid=t.tgfoid "
                    "JOIN pg_namespace AS pn ON pn.oid=p.pronamespace "
                    "WHERE tn.nspname='public' AND NOT t.tgisinternal "
                    "AND left(t.tgname,6)='pr17d_' ORDER BY t.tgname"
                )
            )
        ]
        constraints = [
            {"schema": row.schema_name, "name": row.name}
            for row in connection.execute(
                text(
                    "SELECT n.nspname AS schema_name, c.conname AS name "
                    "FROM pg_constraint AS c JOIN pg_namespace AS n ON n.oid=c.connamespace "
                    "WHERE n.nspname='public' AND left(c.conname,6)='pr17d_' ORDER BY c.conname"
                )
            )
        ]
        non_public_functions = [
            {"schema": row.schema_name, "name": row.name}
            for row in connection.execute(
                text(
                    "SELECT n.nspname AS schema_name, p.proname AS name "
                    "FROM pg_proc AS p JOIN pg_namespace AS n ON n.oid=p.pronamespace "
                    "WHERE n.nspname <> 'public' AND left(p.proname,6)='pr17d_' "
                    "ORDER BY n.nspname, p.proname"
                )
            )
        ]
        discarded_v15_functions = [
            {"schema": row.schema_name, "name": row.name}
            for row in connection.execute(
                text(
                    "SELECT n.nspname AS schema_name, p.proname AS name "
                    "FROM pg_proc AS p JOIN pg_namespace AS n ON n.oid=p.pronamespace "
                    "WHERE n.nspname='public' AND "
                    "(p.proname LIKE 'pr17d_v15_%' OR p.proname LIKE 'v15_pr17d_%') "
                    "ORDER BY p.proname"
                )
            )
        ]
    expected_triggers = {
        name: {"table": table, "function": function}
        for name, table, _event, function in PR17D_TRIGGERS
    }
    stale_references = []
    for row in triggers:
        expected = expected_triggers.get(row["name"])
        observed_reference = {
            "schema": row["schema"],
            "table": row["table"],
            "function": row["bound_function"],
        }
        if (
            expected is None
            or expected["table"] != row["table"]
            or expected["function"] != row["bound_function"]["name"]
        ):
            stale_references.append(
                {"trigger": row["name"], "observed_reference": observed_reference}
            )
    return {
        "functions": functions,
        "triggers": triggers,
        "constraints": constraints,
        "non_public_functions": non_public_functions,
        "discarded_v1_5_functions": discarded_v15_functions,
        "stale_references": stale_references,
    }


def _set_equality(
    expected: list[dict[str, Any]], observed: list[dict[str, Any]], key: str
) -> dict[str, Any]:
    expected_keys = {item[key] for item in expected}
    observed_keys = {item[key] for item in observed}
    return {
        "expected_count": len(expected_keys),
        "observed_count": len(observed_keys),
        "missing": sorted(expected_keys - observed_keys),
        "unexpected": sorted(observed_keys - expected_keys),
        "exact": expected_keys == observed_keys,
    }


def _projection_mismatches(
    expected: list[dict[str, Any]], observed: list[dict[str, Any]], projection_key: str
) -> list[str]:
    expected_by_name = {item["name"]: item[projection_key] for item in expected}
    observed_by_name = {item["name"]: item for item in observed}
    names = sorted(set(expected_by_name) | set(observed_by_name))
    return [name for name in names if expected_by_name.get(name) != observed_by_name.get(name)]


VERIFICATION_COMMANDS: tuple[tuple[str, list[str]], ...] = (
    ("full_pytest", ["uv", "run", "pytest", "-q", "-ra"]),
    ("postgresql_integration", ["uv", "run", "pytest", "-q", "-ra", "-m", "integration"]),
    (
        "focused_write_result",
        [
            "uv",
            "run",
            "pytest",
            "-q",
            "-ra",
            "tests/unit/test_pr17dr2_write_result.py",
            "tests/unit/test_pr15_http.py",
            "tests/unit/test_pr16_cli_contract.py",
            "tests/unit/test_pr16_cli_errors.py",
            "tests/unit/test_pr16_cli_transport_matrix.py",
            "tests/architecture/test_pr17_agent_ready_architecture.py",
            "tests/integration/test_pr15_api.py",
            "tests/integration/test_pr16_cli.py",
        ],
    ),
    (
        "pr17dr2_direct_sql_adversarial",
        [
            "uv",
            "run",
            "pytest",
            "-q",
            "-ra",
            "tests/integration/test_pr17dr2_adversarial.py",
        ],
    ),
    (
        "pr17dr2_concurrency",
        ["uv", "run", "pytest", "-q", "-ra", "tests/integration/test_pr17dr2_concurrency.py"],
    ),
    (
        "migration_lifecycle",
        ["uv", "run", "pytest", "-q", "-ra", "tests/integration/test_pr17dr_migration.py"],
    ),
    (
        "migration_rollback_snapshot",
        [
            "uv",
            "run",
            "pytest",
            "-q",
            "-ra",
            "tests/integration/test_pr17dr_migration.py::test_preflight_failure_rolls_back_revision_objects_and_preserves_rows",
        ],
    ),
    (
        "regression_db_invariants",
        [
            "uv",
            "run",
            "pytest",
            "-q",
            "-ra",
            "tests/integration/test_pr06_application.py",
            "tests/integration/test_pr09_application.py",
            "tests/integration/test_pr10_application.py",
            "tests/integration/test_pr11_application.py",
            "tests/integration/test_pr12_closure.py",
            "tests/integration/test_pr14_governance_integration.py",
            "tests/integration/test_pr17dr_adversarial.py",
        ],
    ),
    (
        "catalog_exact_verification",
        ["uv", "run", "pytest", "-q", "-ra", "tests/integration/test_pr17dr_catalog.py"],
    ),
    ("architecture", ["uv", "run", "pytest", "-q", "-ra", "tests/architecture"]),
    (
        "atomicity",
        ["uv", "run", "pytest", "-q", "-ra", "tests/integration/test_pr12_atomicity.py"],
    ),
    (
        "historical_exactness",
        ["uv", "run", "pytest", "-q", "-ra", "tests/e2e/test_phase1_historical_exactness.py"],
    ),
    (
        "hash_invariance",
        [
            "uv",
            "run",
            "pytest",
            "-q",
            "-ra",
            "tests/unit/domain/test_pr05_experiment.py",
            "tests/unit/domain/test_pr06_dataset.py",
            "tests/unit/domain/test_pr08_metric.py",
            "tests/unit/domain/test_pr10_measurement.py",
            "tests/unit/domain/test_pr11_statistical_result.py",
            "tests/unit/domain/test_pr12_claim.py",
        ],
    ),
    (
        "provenance",
        [
            "uv",
            "run",
            "pytest",
            "-q",
            "-ra",
            "tests/integration/test_pr09r2_proof.py",
            "tests/integration/test_pr13_queries.py",
        ],
    ),
    (
        "adapter_equivalence",
        [
            "uv",
            "run",
            "pytest",
            "-q",
            "-ra",
            "tests/e2e/test_phase1_cross_adapter_equivalence.py",
            "tests/integration/test_pr15_api.py",
            "tests/integration/test_pr16_cli.py",
        ],
    ),
    ("ruff", ["uv", "run", "ruff", "check", "."]),
    ("pyright", ["uv", "run", "pyright"]),
    ("git_diff_check", ["git", "diff", "--check"]),
)


def _authoritative_command_tokens(command_id: str, command: list[str]) -> list[str]:
    tokens = [*command]
    if "pytest" in tokens:
        tokens.append(f"--junitxml=.pr17dr_evidence_results/{command_id}.xml")
    return tokens


def _command_fingerprint(command_tokens: list[str]) -> str:
    normalized = json.dumps(command_tokens, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _stored_command_mismatches(stored: dict[str, dict[str, Any]]) -> list[str]:
    generated = {
        command_id: _authoritative_command_tokens(command_id, command)
        for command_id, command in VERIFICATION_COMMANDS
    }
    return sorted(
        command_id
        for command_id in set(generated) | set(stored)
        if (
            stored.get(command_id, {}).get("command_tokens") != generated.get(command_id)
            or shlex.split(stored.get(command_id, {}).get("command", ""))
            != generated.get(command_id)
            or stored.get(command_id, {}).get("command_fingerprint")
            != _command_fingerprint(generated.get(command_id, []))
        )
    )


def _audit_verification_commands() -> dict[str, Any]:
    duplicated_executables: list[str] = []
    invalid_executable_sequences: list[str] = []
    missing_targets: list[str] = []
    absolute_paths: list[str] = []
    credential_bearing_tokens: list[str] = []

    for command_id, base_command in VERIFICATION_COMMANDS:
        command = _authoritative_command_tokens(command_id, base_command)
        if command[:3] == ["uv", "run", "pytest"]:
            executable = "pytest"
            targets = [token.split("::", 1)[0] for token in command if token.startswith("tests/")]
        elif command[:3] in (["uv", "run", "ruff"], ["uv", "run", "pyright"]):
            executable = command[2]
            targets = []
        elif command == ["git", "diff", "--check"]:
            executable = "git"
            targets = []
        else:
            executable = (
                command[2]
                if command[:2] == ["uv", "run"] and len(command) > 2
                else command[0]
            )
            targets = []
            invalid_executable_sequences.append(command_id)

        if command.count(executable) != 1:
            duplicated_executables.append(command_id)
        for token in command:
            path_token = token.split("::", 1)[0]
            if Path(path_token).is_absolute() or ".worktrees/" in path_token:
                absolute_paths.append(f"{command_id}:{token}")
            if "://" in token and "@" in token.split("://", 1)[1]:
                credential_bearing_tokens.append(f"{command_id}:{token}")
        for target in targets:
            if not (PROJECT_ROOT / target).exists():
                missing_targets.append(f"{command_id}:{target}")

    return {
        "expected": 18,
        "audited": len(VERIFICATION_COMMANDS),
        "duplicated_executables": duplicated_executables,
        "invalid_executable_sequences": invalid_executable_sequences,
        "missing_targets": missing_targets,
        "absolute_paths": absolute_paths,
        "credential_bearing_tokens": credential_bearing_tokens,
    }


def _run_verifications(database: dict[str, Any]) -> dict[str, Any]:
    audit = _audit_verification_commands()
    if audit != {
        "expected": 18,
        "audited": 18,
        "duplicated_executables": [],
        "invalid_executable_sequences": [],
        "missing_targets": [],
        "absolute_paths": [],
        "credential_bearing_tokens": [],
    }:
        raise RuntimeError(f"invalid authoritative verification commands: {audit}")
    results = {
        command_id: _run_verification(command_id, command, database)
        for command_id, command in VERIFICATION_COMMANDS
    }
    mismatches = _stored_command_mismatches(results)
    if mismatches:
        raise RuntimeError(f"stored command differs from current generator: {mismatches}")
    return results


def _verification_verdict(result: dict[str, Any]) -> str:
    if result["verdict"] != "PASS":
        return result["verdict"]
    current_skips = [
        item for item in result["skips"] if item["classification"] != "inherited_pr11r2"
    ]
    return "FAIL" if current_skips else "PASS"


def _all_required_checks_pass(results: dict[str, Any]) -> bool:
    return all(_verification_verdict(result) == "PASS" for result in results.values())


def _invariant_projection(results: dict[str, Any], catalog_verdict: str) -> list[dict[str, Any]]:
    projection: list[dict[str, Any]] = []
    for invariant_id, test_paths in INVARIANT_TESTS.items():
        command_ids = [
            command_id
            for command_id, result in results.items()
            if any(path in result["command"] for path in test_paths)
        ]
        if not command_ids:
            verdict = "NOT_VERIFIED"
            observed = {"commands": [], "db_enforced": None}
        else:
            observed_verdicts = [
                _verification_verdict(results[command_id]) for command_id in command_ids
            ]
            verdict = (
                "PASS"
                if catalog_verdict == "PASS" and all(value == "PASS" for value in observed_verdicts)
                else next(
                    (value for value in observed_verdicts if value != "PASS"),
                    "FAIL",
                )
            )
            observed = {
                "commands": command_ids,
                "db_enforced": catalog_verdict == "PASS",
                "command_verdicts": observed_verdicts,
            }
        projection.append(
            {
                "invariant_id": invariant_id,
                "expected": {"db_enforced": True, "test_paths": test_paths},
                "observed": observed,
                "verdict": verdict,
                "source": {"catalog": "U07 live PostgreSQL catalog", "tests": test_paths},
            }
        )
    return projection


def main() -> None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit(
            "DATABASE_URL is required; evidence cannot be generated from skipped tests"
        )

    subject = _subject_head()
    engine = create_database_engine(database_url)
    try:
        database = _database_identity(engine)
        observed = _observed_catalog(engine)
    finally:
        engine.dispose()

    expected_functions = _function_manifest_rows()
    expected_triggers = _trigger_manifest_rows()
    function_equality = _set_equality(expected_functions, observed["functions"], "name")
    trigger_equality = _set_equality(expected_triggers, observed["triggers"], "name")
    constraint_equality = _set_equality([], observed["constraints"], "name")
    function_projection_mismatches = _projection_mismatches(
        expected_functions, observed["functions"], "expected_projection"
    )
    trigger_projection_mismatches = _projection_mismatches(
        expected_triggers, observed["triggers"], "expected_projection"
    )
    observed_function_names = {row["name"] for row in observed["functions"]}
    bound_function_names = {row["bound_function"]["name"] for row in observed["triggers"]}
    catalog_checks = {
        "functions": {
            "expected": sorted(item["name"] for item in expected_functions),
            "observed": sorted(observed_function_names),
            "verdict": "PASS" if function_equality["exact"] else "FAIL",
            "source": "U07 live PostgreSQL pg_proc query",
        },
        "triggers": {
            "expected": sorted(item["name"] for item in expected_triggers),
            "observed": sorted(item["name"] for item in observed["triggers"]),
            "verdict": "PASS" if trigger_equality["exact"] else "FAIL",
            "source": "U07 live PostgreSQL pg_trigger query",
        },
        "constraints": {
            "expected": [],
            "observed": sorted(item["name"] for item in observed["constraints"]),
            "verdict": "PASS" if constraint_equality["exact"] else "FAIL",
            "source": "U07 live PostgreSQL pg_constraint query",
        },
        "orphan_functions": {
            "expected": [],
            "observed": sorted(observed_function_names - bound_function_names),
            "verdict": "PASS" if not observed_function_names - bound_function_names else "FAIL",
            "source": "U07 live trigger-to-function projection",
        },
        "stale_references": {
            "expected": [],
            "observed": observed["stale_references"],
            "verdict": "PASS" if not observed["stale_references"] else "FAIL",
            "source": "U07 live trigger metadata compared with frozen manifest",
        },
        "non_public_functions": {
            "expected": [],
            "observed": observed["non_public_functions"],
            "verdict": "PASS" if not observed["non_public_functions"] else "FAIL",
            "source": "U07 live PostgreSQL pg_proc schema query",
        },
        "discarded_v1_5_functions": {
            "expected": {
                "count": DISCARDED_V15_FUNCTION_COUNT,
                "name_patterns": ["pr17d_v15_%", "v15_pr17d_%"],
            },
            "observed": observed["discarded_v1_5_functions"],
            "verdict": "PASS" if not observed["discarded_v1_5_functions"] else "FAIL",
            "source": "live PostgreSQL pg_proc query for frozen v1.5 name patterns",
        },
        "function_projection": {
            "expected": expected_functions,
            "observed": observed["functions"],
            "verdict": "PASS" if not function_projection_mismatches else "FAIL",
            "source": "U07 live function projection",
        },
        "trigger_projection": {
            "expected": expected_triggers,
            "observed": observed["triggers"],
            "verdict": "PASS" if not trigger_projection_mismatches else "FAIL",
            "source": "U07 live trigger projection",
        },
    }
    catalog_verdict = (
        "PASS" if all(check["verdict"] == "PASS" for check in catalog_checks.values()) else "FAIL"
    )

    manifest = {
        "schema": "pr17dr-migration-object-manifest-v1",
        "evidence_protocol": PROTOCOL,
        "implementation_subject_head": subject,
        "evidence_commit": None,
        "authorized_schema": "public",
        "ownership_predicate": "left(object_name, 6) = 'pr17d_'",
        "counts": {"functions": 18, "triggers": 40, "constraints": 0},
        "functions": expected_functions,
        "triggers": expected_triggers,
        "constraints": [],
        "discarded_v1_5_functions": {
            "expected_count": DISCARDED_V15_FUNCTION_COUNT,
            "name_patterns": ["pr17d_v15_%", "v15_pr17d_%"],
        },
    }
    verification = {
        "schema": "pr17dr-migration-catalog-verification-v1",
        "evidence_protocol": PROTOCOL,
        "implementation_subject_head": subject,
        "evidence_commit": None,
        "database": database,
        "expected": {
            "functions": expected_functions,
            "triggers": expected_triggers,
            "constraints": [],
        },
        "observed": observed,
        "checks": catalog_checks,
        "exact_set_equality": {
            "functions": function_equality,
            "triggers": trigger_equality,
            "constraints": constraint_equality,
        },
        "projection_mismatches": {
            "functions": function_projection_mismatches,
            "triggers": trigger_projection_mismatches,
        },
        "orphan_functions": sorted(observed_function_names - bound_function_names),
        "non_public_owned_functions": observed["non_public_functions"],
        "stale_references": observed["stale_references"],
        "discarded_v1_5_persistent_functions": observed["discarded_v1_5_functions"],
        "unexpected_pr17d_objects": sorted(
            set(function_equality["unexpected"]) | set(trigger_equality["unexpected"])
        ),
        "verdict": catalog_verdict,
        "source": "U07 live PostgreSQL catalog verification",
    }
    implementation = _run_verifications(database)
    implementation_verdict = "PASS" if _all_required_checks_pass(implementation) else "FAIL"
    projection = {
        "schema": "pr17dr-invariant-to-test-projection-v1",
        "evidence_protocol": PROTOCOL,
        "implementation_subject_head": subject,
        "evidence_commit": None,
        "invariants": _invariant_projection(implementation, catalog_verdict),
        "verdict": (
            "PASS"
            if implementation_verdict == "PASS"
            and catalog_verdict == "PASS"
            and all(
                item["verdict"] == "PASS"
                for item in _invariant_projection(implementation, catalog_verdict)
            )
            else "FAIL"
        ),
        "source": "executed implementation verification commands",
    }
    readiness = {
        "expected": {"all_required_checks": "PASS", "current_remediation_skips": 0},
        "observed": {
            "implementation_verdict": implementation_verdict,
            "catalog_verdict": catalog_verdict,
            "current_remediation_skips": sum(
                sum(item["classification"] == "current_remediation" for item in result["skips"])
                for result in implementation.values()
            ),
        },
        "verdict": (
            "PASS"
            if implementation_verdict == "PASS"
            and catalog_verdict == "PASS"
            and projection["verdict"] == "PASS"
            else "FAIL"
        ),
        "source": "execution-derived catalog and verification results",
    }
    output_dir = PROJECT_ROOT / OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, value in (
        ("migration_object_manifest.json", manifest),
        ("migration_catalog_verification.json", verification),
        ("invariant_to_test_projection.json", projection),
        (
            "implementation_verification.json",
            {
                "schema": "pr17dr2-implementation-verification-v1",
                "evidence_protocol": PROTOCOL,
                "implementation_subject_head": subject,
                "evidence_commit": None,
                "database": database,
                "commands": implementation,
                "command_consistency": {
                    "generated": len(VERIFICATION_COMMANDS),
                    "stored": len(implementation),
                    "exact_token_matches": len(implementation),
                    "mismatches": [],
                },
                "pytest_count_semantics": {
                    "total_discovered": "all tests discovered before selection",
                    "collected": "tests selected for this invocation",
                    "deselected": "discovered tests excluded by marker or filter",
                    "outcomes": [
                        "passed",
                        "failed",
                        "skipped",
                        "xfailed",
                        "xpassed",
                        "error",
                    ],
                },
                "verdict": implementation_verdict,
                "source": "exact commands executed by scripts/pr17dr_evidence.py",
            },
        ),
        (
            "readiness.json",
            {
                "schema": "pr17dr2-readiness-v1",
                "evidence_protocol": PROTOCOL,
                "implementation_subject_head": subject,
                "evidence_commit": None,
                **readiness,
            },
        ),
    ):
        (output_dir / name).write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(
        json.dumps(
            {
                "subject": subject,
                "output_dir": str(output_dir),
                "catalog": catalog_verdict,
                "implementation": implementation_verdict,
                "readiness": readiness["verdict"],
                "generated_at": datetime.now(UTC).isoformat(),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
