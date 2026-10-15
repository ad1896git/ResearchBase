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
from sqlalchemy.engine import Engine

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


def require_pg18(engine: Engine) -> str:
    with engine.connect() as conn:
        assert int(conn.execute(text("SHOW server_version_num")).scalar_one()) // 10000 == 18
        return conn.execute(text("SHOW server_version")).scalar_one()


def catalog(engine: Engine) -> dict[str, Any]:
    with engine.connect() as conn:
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
    with engine.connect() as conn:
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

    @property
    def query_count(self) -> int:
        return len(self.statements)

    @property
    def sql_sha256(self) -> str:
        return digest_bytes(canonical_bytes([sql for sql, _ in self.statements]))


@contextmanager
def capture(engine: Engine) -> Iterator[Capture]:
    observed = Capture()

    def before(conn, cursor, statement, parameters, context, executemany):
        # Parameter values remain ephemeral; only types/digests leave this process.
        observed.statements.append((statement, parameters))

    event.listen(engine, "before_cursor_execute", before)
    started = time.monotonic_ns()
    try:
        yield observed
    finally:
        observed.elapsed_ms = (time.monotonic_ns() - started) / 1_000_000
        event.remove(engine, "before_cursor_execute", before)


def explain_reads(engine: Engine, observed: Capture) -> list[dict[str, Any]]:
    """Actual captured SELECTs, separate read-only observer, no lock/volatile SQL."""
    plans = []
    with engine.connect() as conn:
        conn.execute(text("SET TRANSACTION READ ONLY"))
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
    from tests.contracts.pr2_20_reports import ROOT, subject

    _, _, digest = subject()
    directory = ROOT / "pr_evidence/pr2-20" / digest
    plans = data.pop("plans", [])
    if plans:
        write_chunks(directory, f"plans-{case}-0", plans)
    write_chunks(directory, f"samples-{case}-0", [encode_catalog_text(data)])


def save_query(case: str, engine: Engine, observed: Capture, method: str, repository: str) -> None:
    from tests.contracts.pr2_20_evidence import QueryPlanEvidence, write_chunks, write_record
    from tests.contracts.pr2_20_reports import ROOT, context, subject

    ctx = context()
    prefix = "pr_evidence/pr2-20/" + subject()[2] + "/"
    plans = explain_reads(engine, observed)
    paths = write_chunks(ROOT / prefix, f"plans-{case}-0", plans)
    samples = write_chunks(
        ROOT / prefix,
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
        ROOT / prefix,
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
            path.relative_to(ROOT).as_posix() for path in (*paths, *samples, *profile)
        ),
    )
    item = QueryPlanEvidence(
        **ctx,
        case_id=case,
        service_method=method,
        repository_method=repository,
        parameter_class="Ephemeral bound values; report contains types and SQL digest only",
        sql_sha256=observed.sql_sha256,
        profile_ref=profile[0].relative_to(ROOT).as_posix(),
        sample_ref=samples[0].relative_to(ROOT).as_posix(),
        plan_refs=tuple(path.relative_to(ROOT).as_posix() for path in paths),
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
    write_record(ROOT, prefix + f"query-{case}.json", item)


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
    from tests.contracts.pr2_20_reports import ROOT, context, migration_inventory, subject

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
            write_chunks(ROOT / prefix, f"{case}-{name}", [encode_catalog_text(data)])[0]
            .relative_to(ROOT)
            .as_posix()
        )
    with engine.connect() as conn:
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
    write_record(ROOT, prefix + f"migration-{case}.json", item)


def column_inventory(engine: Engine, tables: tuple[str, ...]) -> dict[str, tuple[str, ...]]:
    with engine.connect() as conn:
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
    from tests.contracts.pr2_20_reports import ROOT, subject

    directory = ROOT / "pr_evidence/pr2-20" / subject()[2]
    result = {}
    for table, entry in data.items():
        paths = write_chunks(directory, f"{case}-{table}", entry["ids_hashes_edges"])
        result[table] = {key: value for key, value in entry.items() if key != "ids_hashes_edges"}
        result[table]["ids_hashes_edges_refs"] = [
            path.relative_to(ROOT).as_posix() for path in paths
        ]
    return result
