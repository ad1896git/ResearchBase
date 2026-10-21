"""B29 engineering measurement runner; index DDL only in fixture-owned clones.

Run through test_pr2_20_benchmark.py::test_b29_measurement. Never accepts an
application database. All science is built by existing owning services.
"""

from __future__ import annotations

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import asdict, is_dataclass
from typing import Any, cast

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from researchbase.application.decision import DecisionService
from researchbase.application.internal_review import InternalReviewService
from researchbase.application.literature_evidence import LiteratureEvidenceService
from researchbase.foundation.errors import ResearchBaseError
from researchbase.persistence.approval_repository import B09_SHARE_SQL
from researchbase.persistence.uow import SqlAlchemyUnitOfWork
from tests.contracts.pr2_20_evidence import canonical_bytes, digest_bytes, write_chunks
from tests.disposable_postgres import admin_url
from tests.integration.phase2 import pr2_20_support as s

INDEX = "ix_pr220_issue_open_blocking_review"
DDL = (
    f"CREATE INDEX {INDEX} ON review_issues USING btree (review_record_id) "
    "WHERE status = 'OPEN' AND severity = 'BLOCKING'"
)


def predicate(value: str) -> tuple[str, ...]:
    """Normalize pg_get_expr's casts/parentheses, preserving the exact two terms."""
    value = re.sub(r"::(?:text|character varying)", "", value.lower())
    return tuple(sorted(re.sub(r"[()\s]", "", value).split("and")))


def candidate_catalog(engine) -> list[dict[str, Any]]:
    with s.read_snapshot(engine) as conn:
        return [
            dict(row)
            for row in conn.execute(
                text("""SELECT c.relname AS name, am.amname AS method,
                i.indisunique AS unique, i.indisvalid AS valid, i.indisready AS ready,
                pg_get_indexdef(i.indexrelid,1,true) AS first_key,
                i.indnkeyatts AS keys, i.indnatts AS attributes,
                pg_get_expr(i.indpred,i.indrelid) AS predicate,
                pg_relation_size(c.oid) AS bytes
                FROM pg_index i JOIN pg_class c ON c.oid=i.indexrelid
                JOIN pg_am am ON am.oid=c.relam
                WHERE i.indrelid='review_issues'::regclass ORDER BY c.relname""")
            ).mappings()
        ]


def preflight(rows):
    for row in rows:
        if row["name"] == INDEX or (
            row["first_key"] == "review_record_id"
            and row["keys"] == row["attributes"] == 1
            and row["predicate"] is not None
            and predicate(row["predicate"]) == predicate("status='OPEN' AND severity='BLOCKING'")
        ):
            raise ValueError("candidate name or equivalent index already exists")


def install_candidate(engine):
    """Caller supplies only a database created by measurement_clone below."""
    if engine not in _CLONES:
        raise ValueError("candidate DDL requires a live fixture-owned measurement clone")
    preflight(candidate_catalog(engine))
    started = time.monotonic_ns()
    with engine.begin() as conn:
        conn.execute(text(DDL))
    elapsed = (time.monotonic_ns() - started) / 1_000_000
    row = next(row for row in candidate_catalog(engine) if row["name"] == INDEX)
    assert row["method"] == "btree" and not row["unique"] and row["valid"] and row["ready"]
    assert row["keys"] == row["attributes"] == 1 and row["first_key"] == "review_record_id"
    assert predicate(row["predicate"]) == predicate("status='OPEN' AND severity='BLOCKING'")
    return {"build_ms": elapsed, "index": row, "ddl": DDL}


_CLONES: set[Any] = set()


@contextmanager
def measurement_clone(template):
    """Exact physical clone of a quiescent disposable fixture, cleaned on all exits."""
    source = make_url(template.url).database
    if not source or not source.startswith(
        ("researchbase_pr211_r2_test_", "researchbase_pr212_test_")
    ):
        raise ValueError("source must be a disposable measurement fixture")
    template.dispose()  # PostgreSQL TEMPLATE requires no open source connections.
    with s.database() as url:
        engine = create_engine(url)
        name = make_url(url).database
        assert name is not None
        admin = create_engine(admin_url())
        try:
            with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                # Upstream fixture builders retain separate idle connection pools.
                # Close only this owned, quiescent template's idle backends, as in
                # disposable teardown; never terminate a running transaction.
                assert not conn.execute(
                    text(
                        "SELECT EXISTS(SELECT 1 FROM pg_stat_activity "
                        "WHERE datname=:name AND backend_type='client backend' AND state<>'idle')"
                    ),
                    {"name": source},
                ).scalar_one()
                conn.execute(
                    text(
                        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                        "WHERE datname=:name AND (state='idle' OR backend_type='autovacuum worker')"
                    ),
                    {"name": source},
                )
                quote = conn.dialect.identifier_preparer.quote
                conn.execute(text(f"DROP DATABASE {quote(name)}"))
                conn.execute(text(f"CREATE DATABASE {quote(name)} TEMPLATE {quote(source)}"))
            _CLONES.add(engine)
            yield engine
        finally:
            _CLONES.discard(engine)
            engine.dispose()
            admin.dispose()


def cardinalities(engine):
    counts = """count(i.id) AS total,
        count(i.id) FILTER (WHERE i.status='OPEN') AS open,
        count(i.id) FILTER (WHERE i.severity='BLOCKING') AS blocking,
        count(i.id) FILTER (WHERE i.status='OPEN' AND i.severity='BLOCKING') AS open_blocking"""
    relation = "internal_review_records r LEFT JOIN review_issues i ON i.review_record_id=r.id"
    target = """CASE WHEN r.scientific_conclusion_version_id IS NOT NULL THEN 'CONCLUSION'
        WHEN r.claim_version_id IS NOT NULL THEN 'CLAIM'
        WHEN r.manuscript_version_id IS NOT NULL THEN 'MANUSCRIPT'
        ELSE 'LITERATURE_SNAPSHOT' END"""
    result = {}
    with s.read_snapshot(engine) as conn:
        for name, group in (
            ("global", None),
            ("review", "r.id"),
            ("project", "r.project_id"),
            ("target_class", target),
        ):
            sql = f"SELECT {counts} FROM {relation}"
            if group:
                sql = (
                    f"SELECT {group} AS scope,{counts} FROM {relation} GROUP BY {group} ORDER BY 1"
                )
            result[name] = [dict(row) for row in conn.execute(text(sql)).mappings()]
        result["statistics"] = [
            dict(row)
            for row in conn.execute(
                text("""SELECT relname,last_analyze,n_live_tup FROM pg_stat_user_tables
                WHERE relname IN ('review_issues','internal_review_records') ORDER BY relname""")
            ).mappings()
        ]
    return result


def all_manifest(engine):
    with s.read_snapshot(engine) as conn:
        tables = tuple(
            conn.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
            ).scalars()
        )
    return s.manifest(engine, tables)


def services(engine, fixture):
    sf = sessionmaker(engine, expire_on_commit=False, autoflush=False)

    def factory():
        return SqlAlchemyUnitOfWork(sf)

    base = fixture["base"]
    evidence = LiteratureEvidenceService(factory, base[-1], base[2]._store)
    return (
        factory,
        DecisionService(factory, base[-1], evidence),
        InternalReviewService(factory, base[-1], evidence),
    )


def summarize(samples):
    return {
        "samples_ms": samples,
        "p50_ms": s.percentile(samples, 0.5),
        "p95_ms": s.percentile(samples, 0.95),
        "max_ms": max(samples),
    }


def run_pair(template, fixture, *, case, workers, repeat):
    """Reset both clones for every case/concurrency/repetition, including writes."""
    observations = []
    for candidate in (False, True):
        with measurement_clone(template) as engine:
            before_catalog = s.catalog(engine)
            before = all_manifest(engine)
            before_storage = storage(engine)
            guards_before = guards(engine)
            build = install_candidate(engine) if candidate else None
            after_catalog = s.catalog(engine)
            assert after_catalog["constraints"] == before_catalog["constraints"]
            assert [row for row in after_catalog["indexes"] if row[1] != INDEX] == before_catalog[
                "indexes"
            ]
            assert all_manifest(engine) == before
            assert guards(engine) == guards_before
            factory, decisions, reviews = services(engine, fixture)
            actor, project = fixture["actor"], fixture["base"][5]

            def call(
                index,
                reviews=reviews,
                actor=actor,
                project=project,
                decisions=decisions,
                factory=factory,
            ):
                if case == "issue-insert":
                    from researchbase.application.internal_review import ReviewIssueRequest

                    return reviews.create(
                        actor,
                        project,
                        "SCIENTIFIC_CONCLUSION_VERSION",
                        fixture["insert_targets"][index],
                        "SCIENTIFIC",
                        "ACCEPT",
                        "TEST ONLY measured insert",
                        (ReviewIssueRequest("BLOCKING", "OTHER", "Measured fresh Issue"),),
                        fixture["insert_ids"][index],
                    )
                if case == "disposition":
                    command = fixture["dispositions"][index]
                    result = reviews.record_issue_disposition(actor, command)
                    assert result.id == command.id
                    return result
                if case == "service-hit":
                    try:
                        decisions.record_decision(actor, fixture["denied"])
                    except ResearchBaseError as error:
                        return error.code.value
                    raise AssertionError("one-blocker gate admitted a Decision")
                if case == "history":
                    return reviews.get_issue_history(actor, project, fixture["terminal_issue"])
                if case == "service-replay":
                    return decisions.record_decision(actor, fixture["replay"])
                target = fixture[case]
                # Owning repository gate in a single lock-free read snapshot.
                with factory() as uow:
                    uow.configure_approval_transaction(readonly=True)
                    return uow.decision.has_blockers(target, project)

            with s.capture(engine) as observed:
                expected = call(0)
            if case == "service-hit":
                # Current service first probes replay in a separate lock-free read.
                # The subsequent writing transaction still starts with exact SHARE.
                assert observed.transaction_first_statements[-1] == B09_SHARE_SQL
                assert expected == fixture["denial_code"]
            if case == "disposition":
                from researchbase.persistence.revision_action_repository import (
                    REVISION_SNAPSHOT_TABLES,
                )

                assert observed.statements[0][0] == (
                    "LOCK TABLE " + ",".join(REVISION_SNAPSHOT_TABLES) + " IN SHARE MODE"
                )
            if case in {"sparse", "dense", "miss", "terminal", "history"}:
                assert all(
                    not any(
                        term in sql.lower()
                        for term in (
                            "lock table",
                            "pg_advisory",
                            "for update",
                            "for share",
                            "for key share",
                        )
                    )
                    for sql, _ in observed.statements
                )
            plans = s.explain_reads(engine, observed)

            # Each timed write has a fresh ID, including warmup; index 0 above is separate.
            def worker(number):
                indexes = iter(range(1 + number * 3, 4 + number * 3))
                return s.sample(lambda: call(next(indexes)), 1, 2)

            with s.capture(engine) as sampled, ThreadPoolExecutor(max_workers=workers) as pool:
                batches = list(pool.map(worker, range(workers)))
            samples = [value for times, _ in batches for value in times]
            results = [value for _, batch in batches for value in batch]
            if case not in {"issue-insert", "disposition"}:
                assert all(value == expected for value in results)
                assert all_manifest(engine) == before
            from tests.contracts.pr2_20_evidence import EVIDENCE_ROOT
            from tests.contracts.pr2_20_reports import subject

            directory = EVIDENCE_ROOT / "pr_evidence/pr2-20" / subject()[2]
            plan_paths = write_chunks(
                directory, f"plans-b29-{case}-{workers}-{repeat}-{int(candidate)}", plans
            )
            post = all_manifest(engine)
            # Independent committed writes have independent trusted DB timestamps.
            # Retain exact full-row digests, and compare every non-clock field too.
            post_semantic = (
                scientific_rows(engine, before) if case in {"issue-insert", "disposition"} else None
            )
            observations.append(
                {
                    "candidate": candidate,
                    "build": build,
                    **summarize(samples),
                    "storage_before": before_storage,
                    "storage_after": storage(engine),
                    "sampled_query_count": sampled.query_count,
                    "query_count": observed.query_count,
                    "first_statement": observed.statements[0][0],
                    "transaction_first_statements": observed.transaction_first_statements,
                    "gate_sql": [
                        sql
                        for sql, _ in observed.statements
                        if sql.lstrip().lower().startswith("select")
                        and ("review_issues" in sql or "b08_check_history" in sql)
                    ],
                    "parameter_classes": [
                        [type(value).__name__ for value in parameters.values()]
                        if isinstance(parameters, dict)
                        else type(parameters).__name__
                        for _, parameters in observed.statements
                    ],
                    "sql_sha256": observed.sql_sha256,
                    "plan_refs": [
                        path.relative_to(EVIDENCE_ROOT).as_posix() for path in plan_paths
                    ],
                    "result": expected,
                    "results": results,
                    "manifest": {
                        table: {k: v for k, v in entry.items() if k != "ids_hashes_edges"}
                        for table, entry in before.items()
                    },
                    "catalog_sha256": digest_bytes(canonical_bytes(after_catalog)),
                    "issue_indexes": candidate_catalog(engine),
                    "post_write_manifest": s.persist_manifest(
                        f"b29-post-{case}-{workers}-{repeat}-{int(candidate)}", post
                    )
                    if post_semantic is not None
                    else None,
                    "post_semantic": post_semantic,
                }
            )
    before, after = observations
    assert before["manifest"] == after["manifest"]
    assert before["query_count"] == after["query_count"]
    assert before["sampled_query_count"] == after["sampled_query_count"]
    clocks = []
    for key in ("result", "results"):
        if case == "disposition":
            for item in observations:
                values = item[key] if key == "results" else [item[key]]
                clocks.extend(value.occurred_at.isoformat() for value in values)
            left = before[key] if key == "results" else [before[key]]
            right = after[key] if key == "results" else [after[key]]
            assert [asdict(value) | {"occurred_at": None} for value in left] == [
                asdict(value) | {"occurred_at": None} for value in right
            ]
        else:
            assert before[key] == after[key]
    assert before["post_semantic"] == after["post_semantic"]
    for item in observations:
        item.pop("post_semantic")
    # Persist exact DTO parity as a digest, avoiding private service text in evidence.

    for item in observations:
        value = item.pop("result")
        item["result_sha256"] = digest_bytes(
            json.dumps(
                asdict(cast(Any, value)) if is_dataclass(value) else value,
                default=str,
                sort_keys=True,
            ).encode()
        )
        item.pop("results")
    return {
        "case": case,
        "workers": workers,
        "repeat": repeat,
        "correctness_equal": True,
        "independent_write_clock_values": clocks,
        "write_comparison_exceptions": ["new created_at/occurred_at", "new OPEN-root random UUID"],
        "observations": observations,
    }


def measure(template, fixture, host):
    """Small informational profile. No timing threshold admits production DDL."""
    from tests.contracts.pr2_20_reports import migration_inventory, subject

    frozen_subject = subject()
    baseline = s.catalog(template)
    preflight(candidate_catalog(template))
    with s.read_snapshot(template) as conn:
        head = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    distributions = cardinalities(template)
    s.save_observation("b29-guards", {"guards": guards(template)})
    with s.read_snapshot(template) as conn:
        settings = [
            list(row)
            for row in conn.execute(
                text(
                    "SELECT name,setting,unit FROM pg_settings WHERE name IN "
                    "('shared_buffers','work_mem','max_connections','jit','track_io_timing',"
                    "'fsync','synchronous_commit','full_page_writes') ORDER BY name"
                )
            )
        ]
    s.save_observation(
        "b29-profile",
        {
            "status": "BLOCKED",
            "reason": "Dedicated large host/profile unavailable",
            "seed": 2202026,
            "fixture_identity": str(fixture["sparse"]),
            "host": host,
            "warmups": 1,
            "calls_per_worker": 2,
            "repetitions": 3,
            "workers": [1, 4],
            "settings": settings,
            "distributions": json.loads(json.dumps(distributions, default=str)),
        },
    )
    rows = []
    cases = (
        "issue-insert",
        "disposition",
        "history",
        "sparse",
        "dense",
        "miss",
        "terminal",
        "service-hit",
        "service-replay",
    )
    for case in cases:
        for workers in (1, 4):
            repetitions = [
                run_pair(template, fixture, case=case, workers=workers, repeat=repeat)
                for repeat in range(3)
            ]
            classification = s.classify(
                [row["observations"][0]["p95_ms"] for row in repetitions],
                [row["observations"][1]["p95_ms"] for row in repetitions],
                equal=True,
                counts_equal=True,
            )
            for row in repetitions:
                row["classification"] = classification
                s.save_observation(f"b29-{case}-{workers}-{row['repeat']}", row.copy())
                rows.append(row)
    report = {
        "status": "BLOCKED",
        "reason": "Local informational profile; owner admission pending; "
        "dedicated large host/profile unavailable",
        "subject": frozen_subject,
        "host": host,
        "head": head,
        "migration_inventory": migration_inventory(),
        "postgres_version": s.require_pg18(template),
        "catalog_baseline": baseline,
        "distributions": json.loads(json.dumps(distributions, default=str)),
        "fixture_manifest": s.persist_manifest("b29-seed", all_manifest(template)),
        "seed": 2202026,
        "warmups": 1,
        "calls_per_worker": 2,
        "repetitions": 3,
        "concurrency_profiles": [1, 4],
        "rows": rows,
    }
    summary = report | {
        "rows": [
            {
                "case": row["case"],
                "workers": row["workers"],
                "repeat": row["repeat"],
                "classification": row["classification"],
                "correctness_equal": row["correctness_equal"],
                "before": {
                    k: row["observations"][0][k]
                    for k in ("p50_ms", "p95_ms", "max_ms", "query_count")
                },
                "after": {
                    k: row["observations"][1][k]
                    for k in ("p50_ms", "p95_ms", "max_ms", "query_count")
                },
            }
            for row in rows
        ]
    }
    s.save_observation("b29-summary", summary)
    return report


def scientific_rows(engine, before):
    """Full field parity except explicit DB clocks for independently run writes."""
    result = {}
    with s.read_snapshot(engine) as conn:
        tables = list(
            conn.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
            ).scalars()
        )
        for table in tables:
            name = conn.dialect.identifier_preparer.quote(table)
            rows = [
                json.loads(row)
                for row in conn.execute(
                    text(f"SELECT row_to_json(t)::text FROM {name} t")
                ).scalars()
            ]
            existing_ids = {row.get("id") for row in before[table]["ids_hashes_edges"]}
            clocks = {
                "internal_review_records": {"created_at"},
                "review_issues": {"created_at"},
                "review_issue_events": {"occurred_at"},
            }.get(table, set())
            clean = []
            for row in rows:
                new = row.get("id") not in existing_ids
                value = {key: field for key, field in row.items() if not (new and key in clocks)}
                if (
                    new
                    and table == "review_issue_events"
                    and row["prior_status"] is None
                    and row["new_status"] == "OPEN"
                ):
                    # Frozen 0040 generates a random root UUID on each independent
                    # INSERT. Retain it in the full manifest; compare roots by the
                    # unique concrete Issue FK, without modifying stored identity.
                    value["id"] = "OPEN-root-for:" + row["issue_id"]
                clean.append(value)
            result[table] = digest_bytes(
                canonical_bytes(sorted(clean, key=lambda x: json.dumps(x, sort_keys=True)))
            )
    return result


def storage(engine):
    with s.read_snapshot(engine) as conn:
        return dict(
            conn.execute(
                text("""SELECT
            pg_relation_size('review_issues') AS heap_bytes,
            pg_indexes_size('review_issues') AS index_bytes,
            pg_total_relation_size('review_issues') AS total_bytes""")
            )
            .mappings()
            .one()
        )


def guards(engine):
    with s.read_snapshot(engine) as conn:
        return [
            list(row)
            for row in conn.execute(
                text("""SELECT c.relname,t.tgname,
            t.tgenabled,t.tgdeferrable,t.tginitdeferred,pg_get_triggerdef(t.oid),
            encode(sha256(convert_to(pg_get_functiondef(t.tgfoid),'UTF8')),'hex')
            FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
            JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='public' AND NOT t.tgisinternal
            ORDER BY c.relname,t.tgname""")
            )
        ]
