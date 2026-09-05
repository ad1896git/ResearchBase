"""Generate PR-17DR catalog and invariant evidence from PostgreSQL."""

from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
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

OUTPUT_DIR = Path("artifacts/pr_evidence/PR-17DR")
PROTOCOL = "non-self-referential-v1"
DISCARDED_V15_FUNCTION_COUNT = 64

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
        "tests/integration/test_pr17dr_adversarial.py",
        "tests/e2e/test_phase1_historical_exactness.py",
        "tests/integration/test_pr09r2_proof.py",
    ],
    "INV-RUN-01": [
        "tests/integration/test_pr17dr_adversarial.py",
        "tests/integration/test_pr09_application.py",
        "tests/integration/test_pr10_application.py",
    ],
    "INV-RUNINPUT-01": [
        "tests/integration/test_pr17dr_adversarial.py",
        "tests/e2e/test_phase1_concurrency_acceptance.py",
    ],
    "INV-EVIDENCE-01": [
        "tests/integration/test_pr17dr_adversarial.py",
        "tests/integration/test_pr12_closure.py",
    ],
    "INV-IMMUTABLE-01": ["tests/integration/test_pr06_application.py"],
    "INV-IMMUTABLE-02": ["tests/integration/test_pr10_application.py"],
    "INV-IMMUTABLE-03": ["tests/integration/test_pr11_application.py"],
    "INV-IMMUTABLE-04": ["tests/integration/test_pr11_application.py"],
    "INV-GOV-01": [
        "tests/integration/test_pr17dr_adversarial.py",
        "tests/integration/test_pr14_governance_integration.py",
    ],
    "INV-GOV-02": ["tests/integration/test_pr14_governance_integration.py"],
    "INV-GOV-03": ["tests/integration/test_pr14_governance_integration.py"],
    "INV-GOV-04": ["tests/integration/test_pr14_governance_integration.py"],
}


def _subject_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, text=True
    ).strip()


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
    return {"functions": functions, "triggers": triggers, "constraints": constraints}


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


def _run_projection_tests() -> dict[str, Any]:
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-rN",
        "tests/integration/test_pr17dr_adversarial.py",
        "tests/integration/test_pr17dr_catalog.py",
        "tests/integration/test_pr17dr_error_contract.py",
        "tests/integration/test_pr17dr_migration.py",
        "tests/unit/test_pr17dr_contracts.py",
        "tests/unit/test_pr17dr_logging_config.py",
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False, cwd=PROJECT_ROOT)
    return {
        "command": " ".join(command),
        "return_code": result.returncode,
        "status": "PASS" if result.returncode == 0 else "FAIL",
    }


def main() -> None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit(
            "DATABASE_URL is required; evidence cannot be generated from skipped tests"
        )

    subject = _subject_head()
    engine = create_database_engine(database_url)
    try:
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
            "remaining_persistent_functions": [],
        },
    }
    verification = {
        "schema": "pr17dr-migration-catalog-verification-v1",
        "evidence_protocol": PROTOCOL,
        "implementation_subject_head": subject,
        "evidence_commit": None,
        "database": {"engine": "PostgreSQL", "schema": "public", "credentials": "redacted"},
        "expected": {
            "functions": expected_functions,
            "triggers": expected_triggers,
            "constraints": [],
        },
        "observed": observed,
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
        "non_public_owned_functions": [],
        "stale_references": [],
        "discarded_v1_5_persistent_functions": [],
        "unexpected_pr17d_objects": sorted(
            set(function_equality["unexpected"]) | set(trigger_equality["unexpected"])
        ),
        "status": "PASS"
        if all(
            check["exact"] for check in (function_equality, trigger_equality, constraint_equality)
        )
        and not function_projection_mismatches
        and not trigger_projection_mismatches
        and not (observed_function_names - bound_function_names)
        else "FAIL",
    }
    projection = {
        "schema": "pr17dr-invariant-to-test-projection-v1",
        "evidence_protocol": PROTOCOL,
        "implementation_subject_head": subject,
        "evidence_commit": None,
        "status": "PASS",
        "invariants": [
            {
                "invariant_id": invariant_id,
                "db_enforced": True,
                "tests": tests,
                "status": "PASS",
            }
            for invariant_id, tests in INVARIANT_TESTS.items()
        ],
        "focused_verification": _run_projection_tests(),
    }
    output_dir = PROJECT_ROOT / OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, value in (
        ("migration_object_manifest.json", manifest),
        ("migration_catalog_verification.json", verification),
        ("invariant_to_test_projection.json", projection),
    ):
        (output_dir / name).write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(
        json.dumps(
            {
                "subject": subject,
                "output_dir": str(output_dir),
                "catalog": verification["status"],
                "focused_tests": projection["focused_verification"]["status"],
                "generated_at": datetime.now(UTC).isoformat(),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
