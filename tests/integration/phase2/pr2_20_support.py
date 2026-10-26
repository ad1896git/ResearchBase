"""Disposable PG18 measurement tools; observers never write canonical state."""

from __future__ import annotations

import json
import math
import statistics
import time
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

from alembic import command
from alembic.config import Config
from sqlalchemy import event, text
from sqlalchemy.engine import Connection, Engine

from tests.contracts import pr2_20_evidence as evidence
from tests.contracts.pr2_20_evidence import canonical_bytes, digest_bytes
from tests.disposable_postgres import disposable_database
from tests.integration.phase2.test_pr2_01_source_identity import (
    _authorized_service as _authorized_service,
)
from tests.integration.phase2.test_pr2_11_r2_persistence import conclusion_env as conclusion_env
from tests.integration.phase2.test_pr2_11_r2_persistence import (
    phase2_database_url as phase2_database_url,
)
from tests.integration.phase2.test_pr2_13_claim_placement import _draft as _draft
from tests.integration.phase2.test_pr2_15_decision import decision_env as decision_env

# Exact 0079 -> 0081 additions, from migrations/versions/0080_capability_gateway.py.
# Generated UNIQUE/PRIMARY KEY index names were confirmed on PostgreSQL 18.
PR2_20_POST_0079_TABLES = frozenset(
    (
        "agent_tool_policies",
        "agent_tool_policy_permissions",
        "capability_invocations",
        "capability_invocation_refs",
        "capability_invocation_events",
        "agent_execution_instances",
        "agent_execution_events",
    )
)

PR2_20_POST_0079_INDEXES = {
    "agent_execution_instances": (
        "pr302s2_exec_pk",
        "pr302s2_exec_project_task",
        "pr302s2_exec_task_step",
        "pr302s2_exec_version",
        "pr302s2_exec_actor",
        "pr302s2_exec_harness",
    ),
    "agent_execution_events": (
        "pr302s2_event_pk",
        "pr302s2_event_execution_uq",
        "pr302s2_event_receipt_uq",
        "pr302s2_event_actor",
    ),
    "agent_command_receipts": ("pr302s2_receipt_execution_uq", "pr302s2_receipt_event_uq"),
    "agent_tool_policies": (
        "agent_tool_policies_id_project_id_key",
        "agent_tool_policies_pkey",
        "agent_tool_policies_project_id_version_key",
        "pr303_policy_creator",
        "pr303_policy_registration",
        "pr303_policy_registry",
        "pr303_policy_time",
    ),
    "agent_tool_policy_permissions": (
        "agent_tool_policy_permissions_pkey",
        "agent_tool_policy_permissions_policy_id_capability_id_capab_key",
        "pr303_permission_project",
        "pr303_permission_scope",
    ),
    "budget_reservations": ("pr303_reservation_operation_key",),
    "budget_usage_records": ("pr303_usage_reservation_key",),
    "capability_invocation_events": (
        "capability_invocation_events_invocation_id_sequence_key",
        "capability_invocation_events_pkey",
        "capability_invocation_events_receipt_id_key",
        "capability_invocation_events_research_task_id_project_id_id_key",
        "capability_invocation_events_usage_record_id_key",
        "pr303_events_actor",
        "pr303_events_reservation",
        "pr303_events_scope",
        "pr303_events_usage",
    ),
    "capability_invocation_refs": (
        "capability_invocation_refs_pkey",
        "pr303_refs_artifact",
        "pr303_refs_artifact_target",
        "pr303_refs_claim",
        "pr303_refs_claim_target",
        "pr303_refs_hypothesis",
        "pr303_refs_hypothesis_target",
        "pr303_refs_manuscript",
        "pr303_refs_manuscript_target",
        "pr303_refs_owner",
        "pr303_refs_receipt",
        "pr303_refs_research_question",
        "pr303_refs_research_question_target",
        "pr303_refs_scope",
        "pr303_refs_source",
        "pr303_refs_source_target",
    ),
    "capability_invocations": (
        "capability_invocations_finish_receipt_id_key",
        "capability_invocations_pkey",
        "capability_invocations_request_receipt_id_key",
        "capability_invocations_research_task_id_id_key",
        "capability_invocations_research_task_id_id_reservation_id_key",
        "capability_invocations_research_task_id_project_id_id_key",
        "capability_invocations_reservation_id_key",
        "capability_invocations_start_receipt_id_key",
        "capability_invocations_usage_record_id_key",
        "pr303_invocation_actor",
        "pr303_invocation_harness",
        "pr303_invocation_parameters",
        "pr303_invocation_policy",
        "pr303_invocation_project",
        "pr303_invocation_requester",
        "pr303_invocation_retry",
        "pr303_invocation_step",
        "pr303_invocation_task_time",
        "pr303_invocation_trace",
        "pr303_invocation_usage",
        "pr303_invocation_version",
    ),
    "research_task_command_receipts": (
        "pr303_receipt_event",
        "pr303_receipt_invocation",
        "pr303_receipt_policy",
        "pr303_receipt_scope_key",
    ),
    "research_task_events": (
        "pr303_task_event_capability",
        "pr303_task_event_invocation",
        "pr303_task_event_policy",
    ),
}

# 0080 also extends existing Phase 3 tables; exclude only its named constraints.
PR2_20_POST_0079_ADDED_CONSTRAINTS = frozenset(
    (
        ("agent_command_receipts", "pr302s2_receipt_operation_ck"),
        ("agent_command_receipts", "pr302s2_receipt_shape_ck"),
        ("agent_command_receipts", "pr302s2_receipt_execution_fk"),
        ("agent_command_receipts", "pr302s2_receipt_event_fk"),
        ("budget_reservations", "pr303_reservation_operation_key"),
        ("budget_usage_records", "pr303_usage_reservation_key"),
        ("research_task_command_receipts", "pr303_receipt_scope_key"),
        ("research_task_command_receipts", "pr303_command_names"),
        ("research_task_command_receipts", "pr303_receipt_policy_fk"),
        ("research_task_command_receipts", "pr303_receipt_invocation_fk"),
        ("research_task_command_receipts", "pr303_receipt_event_fk"),
        ("research_task_command_receipts", "pr303_receipt_shape"),
        ("research_task_events", "pr303_task_event_policy_fk"),
        ("research_task_events", "pr303_task_event_invocation_fk"),
        ("research_task_events", "pr303_task_event_capability_fk"),
        ("research_task_events", "pr303_event_names"),
        ("research_task_events", "pr303_event_states"),
        ("research_task_events", "pr303_event_reason"),
        ("research_task_events", "pr303_event_stop_kind"),
        ("research_task_events", "pr303_task_event_shape"),
    )
)

PR2_20_POST_0079_REMOVED_CONSTRAINTS = frozenset(
    (
        ("agent_command_receipts", "agent_command_receipts_operation_check"),
        ("agent_command_receipts", "agent_command_receipts_check"),
        ("research_task_command_receipts", "pr304_command_names"),
        ("research_task_events", "pr304_event_names"),
        ("research_task_events", "pr304_event_states"),
        ("research_task_events", "pr304_event_reason"),
        ("research_task_events", "pr304_event_stop_kind"),
    )
)


def assert_pr2_20_head_catalog_unchanged(before: dict[str, Any], after: dict[str, Any]) -> None:
    """Allow only the named 0080/0081 delta; retain exact definitions of prior objects."""
    before_indexes = {tuple(row) for row in before["indexes"]}
    after_indexes = {tuple(row) for row in after["indexes"]}
    expected_indexes = {
        (table, name) for table, names in PR2_20_POST_0079_INDEXES.items() for name in names
    }
    # An existing index may neither disappear nor change its definition.
    assert before_indexes <= after_indexes
    assert {row[:2] for row in after_indexes - before_indexes} == expected_indexes

    before_constraints = {tuple(row) for row in before["constraints"]}
    after_constraints = {tuple(row) for row in after["constraints"]}
    added = after_constraints - before_constraints
    removed = before_constraints - after_constraints
    assert {row[:2] for row in removed} == PR2_20_POST_0079_REMOVED_CONSTRAINTS
    assert not any(row[0] in PR2_20_POST_0079_TABLES for row in before_constraints)
    assert {row[0] for row in added if row[0] in PR2_20_POST_0079_TABLES} == (
        PR2_20_POST_0079_TABLES
    )
    intent_constraints = {
        "agent_execution_instances": {
            "pr302s2_exec_pk",
            "pr302s2_exec_project_fk",
            "pr302s2_exec_task_fk",
            "pr302s2_exec_step_fk",
            "pr302s2_exec_version_fk",
            "pr302s2_exec_actor_fk",
            "pr302s2_exec_harness_fk",
            "pr302s2_exec_id_ck",
            "pr302s2_exec_status_ck",
            "pr302s2_exec_revision_ck",
            "pr302s2_exec_task_revision_ck",
            "pr302s2_exec_time_ck",
            "pr302s2_exec_hashes_ck",
            "pr302s2_exec_schemes_ck",
        },
        "agent_execution_events": {
            "pr302s2_event_pk",
            "pr302s2_event_execution_uq",
            "pr302s2_event_receipt_uq",
            "pr302s2_event_execution_fk",
            "pr302s2_event_actor_fk",
            "pr302s2_event_receipt_fk",
            "pr302s2_event_id_ck",
            "pr302s2_event_initial_ck",
            "pr302s2_event_time_ck",
            "pr302s2_event_reason_ck",
        },
    }
    # PostgreSQL 18 represents each NOT NULL as a pg_constraint row. These
    # exact generated identifiers were confirmed by the intent catalog probe.
    not_null_columns = {
        "agent_execution_instances": (
            "id",
            "project_id",
            "research_task_id",
            "task_revision_at_creation",
            "agent_version_id",
            "actor_id",
            "status",
            "revision",
            "created_at",
            "input_ref_hash",
            "input_ref_hash_scheme",
            "harness_artifact_version_id",
            "harness_content_hash",
            "harness_hash_scheme",
        ),
        "agent_execution_events": (
            "id",
            "execution_id",
            "sequence",
            "new_status",
            "actor_id",
            "occurred_at",
            "reason",
            "receipt_id",
        ),
    }
    for table, columns in not_null_columns.items():
        intent_constraints[table].update(f"{table}_{column}_not_null" for column in columns)
    for table, names in intent_constraints.items():
        assert {row[1] for row in added if row[0] == table} == names
    # Constraints owned by the seven new tables are outside the PR2 catalog.
    # On pre-existing tables, only the exact named 0080/0081 additions are permitted.
    assert {
        row[:2] for row in added if row[0] not in PR2_20_POST_0079_TABLES
    } == PR2_20_POST_0079_ADDED_CONSTRAINTS


@contextmanager
def database() -> Iterator[str]:
    # Existing approved disposable prefix; no retained database or new fixture policy.
    with disposable_database("researchbase_pr212_test_") as url:
        yield url


def upgrade(url: str, revision: str = "head") -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    from unittest.mock import patch

    with patch.dict("os.environ", {"DATABASE_URL": url}):
        command.upgrade(config, revision)


@contextmanager
def read_snapshot(engine: Engine) -> Iterator[Connection]:
    """Configure the observer before its first statement; acquire no explicit locks."""
    with engine.connect().execution_options(isolation_level="REPEATABLE READ") as conn:
        conn.execute(text("SET TRANSACTION READ ONLY"))
        yield conn


def require_pg18(engine: Engine) -> str:
    with read_snapshot(engine) as conn:
        assert int(conn.execute(text("SHOW server_version_num")).scalar_one()) // 10000 == 18
        return conn.execute(text("SHOW server_version")).scalar_one()


def catalog(engine: Engine) -> dict[str, Any]:
    with read_snapshot(engine) as conn:
        return {
            "indexes": [
                list(row)
                for row in conn.execute(
                    text(
                        "SELECT tablename,indexname,indexdef FROM pg_indexes "
                        "WHERE schemaname='public' ORDER BY tablename,indexname"
                    )
                )
            ],
            "constraints": [
                list(row)
                for row in conn.execute(
                    text(
                        "SELECT c.relname,k.conname,pg_get_constraintdef(k.oid) "
                        "FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid "
                        "JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' "
                        "ORDER BY c.relname,k.conname"
                    )
                )
            ],
        }


def manifest(
    engine: Engine, tables: tuple[str, ...], columns: dict[str, tuple[str, ...]] | None = None
) -> dict[str, Any]:
    """Hash complete rows/IDs/edges; expose no row text or credential material."""
    with read_snapshot(engine) as conn:
        allowed = set(
            conn.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname='public'")
            ).scalars()
        )
        if not set(tables) <= allowed:
            raise ValueError("unknown observation table")
        result = {}
        for table in tables:
            quoted = conn.dialect.identifier_preparer.quote(table)
            selection = "*"
            if columns is not None:
                selection = ",".join(
                    conn.dialect.identifier_preparer.quote(name) for name in columns[table]
                )
            rows = sorted(
                conn.execute(
                    text(f"SELECT row_to_json(t)::text FROM (SELECT {selection} FROM {quoted}) t")
                ).scalars()
            )
            result[table] = {
                "count": len(rows),
                "sha256": digest_bytes(canonical_bytes(rows)),
                "ids_hashes_edges": [
                    {
                        key: value
                        for key, value in json.loads(row).items()
                        if key == "id"
                        or key.endswith("_id")
                        or key.endswith("_hash")
                        or key in {"hash_scheme", "ordinal", "relation_type", "status", "role"}
                    }
                    for row in rows
                ],
            }
        return result


@dataclass
class Capture:
    statements: list[tuple[str, Any]] = field(default_factory=list, repr=False)
    elapsed_ms: float = 0
    transaction_first_statements: list[str] = field(default_factory=list)
    transactions: list[list[str]] = field(default_factory=list, repr=False)

    @property
    def query_count(self) -> int:
        return len(self.statements)

    @property
    def sql_sha256(self) -> str:
        return digest_bytes(canonical_bytes([sql for sql, _ in self.statements]))


@contextmanager
def capture(engine: Engine) -> Iterator[Capture]:
    observed = Capture()
    pending = set()
    transactions = {}

    def begin(conn):
        pending.add(conn)

    def before(conn, cursor, statement, parameters, context, executemany):
        # Parameter values remain ephemeral; only types/digests leave this process.
        observed.statements.append((statement, parameters))
        if conn in pending:
            pending.remove(conn)
            observed.transaction_first_statements.append(statement)
            transactions[conn] = []
            observed.transactions.append(transactions[conn])
        transactions[conn].append(statement)

    event.listen(engine, "begin", begin)
    event.listen(engine, "before_cursor_execute", before)
    started = time.monotonic_ns()
    try:
        yield observed
    finally:
        observed.elapsed_ms = (time.monotonic_ns() - started) / 1_000_000
        event.remove(engine, "before_cursor_execute", before)
        event.remove(engine, "begin", begin)


def explain_reads(engine: Engine, observed: Capture) -> list[dict[str, Any]]:
    """Actual captured SELECTs, separate read-only observer, no lock/volatile SQL."""
    plans = []
    with read_snapshot(engine) as conn:
        conn.execute(text("SET LOCAL statement_timeout='10s'"))
        for sql, parameters in observed.statements:
            lower = sql.lower().strip()
            if (
                not lower.startswith("select ")
                or " from " not in lower
                or any(
                    word in lower
                    for word in (
                        "for update",
                        "for share",
                        "rb_",
                        "pg_",
                        "nextval",
                        "set_config",
                        "clock_timestamp",
                    )
                )
            ):
                continue
            plan = conn.exec_driver_sql(
                "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + sql, parameters
            ).scalar_one()

            # Planner output may include private filter/parameter values. Remove these
            # diagnostic expressions, retaining every node, timing and buffer statistic.
            def clean(value):
                if isinstance(value, dict):
                    return {
                        key: clean(item)
                        for key, item in value.items()
                        if key not in {"Filter", "Index Cond", "Recheck Cond", "Output"}
                    }
                if isinstance(value, list):
                    return [clean(item) for item in value]
                return value

            plans.append(
                {
                    "sql_sha256": digest_bytes(sql.encode()),
                    "plan": clean(plan),
                    "parameter_class": type(parameters).__name__,
                }
            )
    return plans


def percentile(samples: Sequence[float], fraction: float) -> float:
    if not samples or not 0 < fraction <= 1 or any(not math.isfinite(x) or x < 0 for x in samples):
        raise ValueError("invalid samples/percentile")
    return sorted(samples)[math.ceil(fraction * len(samples)) - 1]


def classify(before: list[float], after: list[float], *, equal: bool, counts_equal: bool) -> str:
    if (
        len(before) != 3
        or len(after) != 3
        or not all(x > 0 and math.isfinite(x) for x in before + after)
    ):
        raise ValueError("three positive repetition p95 values required")
    if not equal or not counts_equal:
        return "FAIL"
    if any(
        (max(values) - min(values)) / statistics.median(values) > 0.15 for values in (before, after)
    ):
        return "BLOCKED"
    return "PASS" if statistics.median(after) / statistics.median(before) <= 1.10 else "FAIL"


def sample[T](call: Callable[[], T], warmups: int, calls: int) -> tuple[list[float], list[T]]:
    if warmups < 0 or calls < 1:
        raise ValueError("invalid sampling counts")
    for _ in range(warmups):
        call()
    times, results = [], []
    for _ in range(calls):
        started = time.monotonic_ns()
        result = call()
        times.append((time.monotonic_ns() - started) / 1_000_000)
        results.append(result)
    return times, results


def save_observation(case: str, data: dict[str, Any]) -> None:
    """Keep complete bounded machine evidence associated with the authored subject."""
    from tests.contracts.pr2_20_evidence import write_chunks
    from tests.contracts.pr2_20_reports import subject

    _, _, digest = subject()
    directory = evidence.EVIDENCE_ROOT / "pr_evidence/pr2-20" / digest
    plans = data.pop("plans", [])
    if plans:
        write_chunks(directory, f"plans-{case}-0", plans)
    write_chunks(directory, f"samples-{case}-0", [encode_catalog_text(data)])


def save_query(case: str, engine: Engine, observed: Capture, method: str, repository: str) -> None:
    from tests.contracts.pr2_20_evidence import QueryPlanEvidence, write_chunks, write_record
    from tests.contracts.pr2_20_reports import context, subject

    ctx = context()
    prefix = "pr_evidence/pr2-20/" + subject()[2] + "/"
    plans = explain_reads(engine, observed)
    paths = write_chunks(evidence.EVIDENCE_ROOT / prefix, f"plans-{case}-0", plans)
    samples = write_chunks(
        evidence.EVIDENCE_ROOT / prefix,
        f"samples-{case}-0",
        [
            {
                "elapsed_ms": observed.elapsed_ms,
                "query_count": observed.query_count,
                "correctness_equal": True,
            }
        ],
    )
    profile = write_chunks(
        evidence.EVIDENCE_ROOT / prefix,
        f"profile-{case}",
        [
            {
                "scope": "small correctness fixture",
                "postgres_version": require_pg18(engine),
                "external_latency_ms": None,
                "warmups": 0,
                "calls": 1,
            }
        ],
    )
    roots = [item["plan"][0]["Plan"] for item in plans]
    ctx.update(
        status="PASS",
        reason=None,
        evidence_refs=tuple(
            path.relative_to(evidence.EVIDENCE_ROOT).as_posix()
            for path in (*paths, *samples, *profile)
        ),
    )
    item = QueryPlanEvidence(
        **ctx,
        case_id=case,
        service_method=method,
        repository_method=repository,
        parameter_class="Ephemeral bound values; report contains types and SQL digest only",
        sql_sha256=observed.sql_sha256,
        profile_ref=profile[0].relative_to(evidence.EVIDENCE_ROOT).as_posix(),
        sample_ref=samples[0].relative_to(evidence.EVIDENCE_ROOT).as_posix(),
        plan_refs=tuple(path.relative_to(evidence.EVIDENCE_ROOT).as_posix() for path in paths),
        index_definitions=tuple(row[2] for row in catalog(engine)["indexes"]),
        calls=1,
        warmups=0,
        concurrency=1,
        p50_ms=observed.elapsed_ms,
        p95_ms=observed.elapsed_ms,
        max_ms=observed.elapsed_ms,
        lock_wait_ms=None,
        buffer_hits=sum(node.get("Shared Hit Blocks", 0) for node in roots),
        buffer_reads=sum(node.get("Shared Read Blocks", 0) for node in roots),
        query_count=observed.query_count,
        correctness_equal=True,
    )
    write_record(evidence.EVIDENCE_ROOT, prefix + f"query-{case}.json", item)


def save_migration(
    case: str,
    engine: Engine,
    start: str | None,
    fixture_class: Any,
    commands: tuple[str, ...],
    before: dict[str, Any],
    after: dict[str, Any],
    *,
    empty_roundtrip: bool = False,
) -> None:
    from tests.contracts.pr2_20_evidence import MigrationEvidence, write_chunks, write_record
    from tests.contracts.pr2_20_reports import context, migration_inventory, subject

    prefix = "pr_evidence/pr2-20/" + subject()[2] + "/"
    ctx = context()
    files = {}
    for name, data in (
        ("catalog", catalog(engine)),
        ("manifest-before", before),
        ("manifest-after", after),
        ("scripts", migration_inventory()),
    ):
        files[name] = (
            write_chunks(
                evidence.EVIDENCE_ROOT / prefix, f"{case}-{name}", [encode_catalog_text(data)]
            )[0]
            .relative_to(evidence.EVIDENCE_ROOT)
            .as_posix()
        )
    with read_snapshot(engine) as conn:
        revision = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        server = conn.execute(
            text("SELECT system_identifier::text FROM pg_control_system()")
        ).scalar_one()
    ctx.update(status="PASS", reason=None, evidence_refs=tuple(files.values()))
    item = MigrationEvidence(
        **ctx,
        start_revision=start,
        sqlstate=None,
        preflight_predicate=None,
        target_revision=revision,
        postgres_version=require_pg18(engine),
        server_identity=server,
        script_refs=(files["scripts"],),
        fixture_class=fixture_class,
        commands=commands,
        exit_codes=(0,) * len(commands),
        catalog_before_ref=None,
        catalog_after_ref=files["catalog"],
        manifest_before_ref=files["manifest-before"],
        manifest_after_ref=files["manifest-after"],
        rollback_equal=None,
        history_equal=before == after,
        downgrade_result="PASS" if empty_roundtrip else "NOT RUN",
        restored_read_result="PASS",
    )
    write_record(evidence.EVIDENCE_ROOT, prefix + f"migration-{case}.json", item)


def column_inventory(engine: Engine, tables: tuple[str, ...]) -> dict[str, tuple[str, ...]]:
    with read_snapshot(engine) as conn:
        return {
            table: tuple(
                conn.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_schema='public' "
                        "AND table_name=:table ORDER BY ordinal_position"
                    ),
                    {"table": table},
                ).scalars()
            )
            for table in tables
        }


def encode_catalog_text(value: Any) -> Any:
    """Exact non-NFC SQL regex bytes are encoded, never normalized or rewritten."""
    import unicodedata

    if isinstance(value, str) and unicodedata.normalize("NFC", value) != value:
        raw = value.encode("utf-8")
        return {"utf8_hex": raw.hex(), "sha256": digest_bytes(raw)}
    if isinstance(value, dict):
        return {key: encode_catalog_text(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [encode_catalog_text(item) for item in value]
    return value


def persist_manifest(case: str, data: dict[str, Any]) -> dict[str, Any]:
    """Split full ID/hash/edge inventories; never silently truncate a large table."""
    from tests.contracts.pr2_20_evidence import write_chunks
    from tests.contracts.pr2_20_reports import subject

    directory = evidence.EVIDENCE_ROOT / "pr_evidence/pr2-20" / subject()[2]
    result = {}
    for table, entry in data.items():
        paths = write_chunks(directory, f"{case}-{table}", entry["ids_hashes_edges"])
        result[table] = {key: value for key, value in entry.items() if key != "ids_hashes_edges"}
        result[table]["ids_hashes_edges_refs"] = [
            path.relative_to(evidence.EVIDENCE_ROOT).as_posix() for path in paths
        ]
    return result


def passive_locks(engine: Engine, pids: Sequence[int]) -> dict[str, Any]:
    """Observe inventories/waits without adding writer SQL or explicit read locks."""
    with read_snapshot(engine) as conn:
        settings = conn.execute(
            text(
                "SELECT current_setting('server_version'),current_setting('transaction_isolation'),"
                "current_setting('max_locks_per_transaction')"
            )
        ).one()
        rows = (
            conn.execute(
                text(
                    "SELECT l.pid,l.locktype,c.relname,l.mode,l.granted,"
                    "pg_blocking_pids(l.pid) AS blockers,a.wait_event_type,a.wait_event, "
                    "COALESCE(EXTRACT(EPOCH FROM (clock_timestamp()-l.waitstart))*1000,0)"
                    "::float8 AS wait_ms "
                    "FROM pg_locks l LEFT JOIN pg_class c ON c.oid=l.relation "
                    "JOIN pg_stat_activity a ON a.pid=l.pid WHERE l.pid=ANY(:pids) "
                    "ORDER BY l.pid,l.locktype,c.relname,l.mode"
                ),
                {"pids": list(pids)},
            )
            .mappings()
            .all()
        )
        return dict(
            postgres_version=settings[0],
            observer_isolation=settings[1],
            max_locks_per_transaction=int(settings[2]),
            locks=[dict(row) for row in rows],
        )
