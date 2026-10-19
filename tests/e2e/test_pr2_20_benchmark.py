"""Small CI parity plus opt-in, explicitly bounded PR220 service benchmark."""

from __future__ import annotations

import os
import platform
import shutil
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import text
from tests.contracts import pr2_20_evidence as evidence
from tests.contracts.pr2_20_evidence import BenchmarkProfile, digest_bytes, to_bytes
from tests.contracts.pr2_20_reports import ROOT, context, subject
from tests.integration.phase2 import b18_novelty_support as novelty
from tests.integration.phase2 import pr2_20_support as s
from tests.integration.phase2.pr2_20_scaled import APPROVAL_CASES, approval_profile
from tests.integration.phase2.test_approval import approval_env as _approval_env
from tests.integration.phase2.test_m3_evidence import m3 as _m3
from tests.integration.phase2.test_pr2_20_catalog_plans import trace_fixture

m3 = _m3
approval_env = _approval_env
conclusion_env = s.conclusion_env
phase2_database_url = s.phase2_database_url
decision_env = s.decision_env
pytestmark = pytest.mark.integration

LARGE_COUNTS: dict[str, Any] = dict(
    seed=2202026,
    projects=10,
    sources=10000,
    source_versions=20000,
    identifiers=20000,
    project_links=11000,
    shared_sources=1000,
    busy_project_sources=8000,
    claims=1000,
    manuscripts=100,
    typical_placements=25,
    high_placements=250,
    evidence_per_claim=4,
    conclusion_targets=512,
    reviews=5120,
    issues=51200,
)
SMALL_COUNTS: dict[str, Any] = dict(
    seed=2202026,
    projects=2,
    sources=10,
    source_versions=20,
    identifiers=20,
    project_links=11,
    shared_sources=1,
    busy_project_sources=8,
    claims=4,
    manuscripts=2,
    typical_placements=2,
    high_placements=4,
    evidence_per_claim=4,
    conclusion_targets=4,
    reviews=8,
    issues=16,
)
CASES = (
    "lookup-hit",
    "lookup-miss",
    "lookup-denied",
    "trace-typical",
    "trace-high",
    "review-gate",
    "decision-first-write",
    "decision-replay",
)


def profile(engine, large: bool) -> BenchmarkProfile:
    import psycopg

    with s.read_snapshot(engine) as conn:
        settings = {
            str(row[0]): str(row[1])
            for row in conn.execute(
                text(
                    "SELECT name,setting FROM pg_settings WHERE name IN "
                    "('shared_buffers','work_mem','max_connections','jit','track_io_timing')"
                )
            ).all()
        }
    # PostgreSQL reports shared_buffers in 8KiB blocks, work_mem in KiB.
    return BenchmarkProfile(
        **context(),
        **(LARGE_COUNTS if large else SMALL_COUNTS),
        vcpus=os.cpu_count() or 0,
        ram_gib=0,
        disk_gib=shutil.disk_usage(ROOT).total // (1024**3),
        shared_buffers_mb=int(settings["shared_buffers"]) // 128,
        work_mem_mb=int(settings["work_mem"]) // 1024,
        max_connections=int(settings["max_connections"]),
        warmups=5 if large else 1,
        calls_per_worker=100 if large else 2,
        repetitions=3,
        host_os=platform.platform(),
        cpu_model=platform.processor() or platform.machine(),
        kernel=platform.release(),
        storage_model="UNVERIFIED: dedicated host attestation required",
        postgres_version=s.require_pg18(engine),
        python_version=platform.python_version(),
        driver_version=psycopg.__version__,
        lock_sha256=digest_bytes(Path("uv.lock").read_bytes()),
        jit=settings["jit"] == "on",
        track_io_timing=settings["track_io_timing"] == "on",
        concurrency_profiles=(1, 4),
        regression_ratio=1.10,
        noise_spread=0.15,
        owner_override_ref=None,
    )


def save_profile(value: BenchmarkProfile):
    directory = evidence.EVIDENCE_ROOT / "pr_evidence/pr2-20" / subject()[2]
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "benchmark_profile.json").write_bytes(to_bytes(value))


def large_host_blockers(value: BenchmarkProfile) -> tuple[str, ...]:
    failures = ["Superseded manuscript history BLOCKED: owning lifecycle unavailable"]
    if not (
        platform.system() == "Linux"
        and platform.machine() in {"x86_64", "AMD64"}
        and Path("/etc/os-release").exists()
        and 'VERSION_ID="24.04"' in Path("/etc/os-release").read_text()
    ):
        failures.append("Dedicated Ubuntu 24.04 x86-64 host unavailable")
    # Host reservation/storage must be evidenced, not guessed from machine totals.
    if "UNVERIFIED" in value.storage_model:
        failures.append("Reserved CPU/RAM/storage/no-competing-job attestation unavailable")
    if (
        value.shared_buffers_mb,
        value.work_mem_mb,
        value.max_connections,
        value.jit,
        value.track_io_timing,
    ) != (1024, 16, 32, False, True):
        failures.append("Declared PostgreSQL benchmark settings unavailable")
    return tuple(failures)


def test_nearest_rank_zero_tolerance_regression_and_noise_classification():
    assert s.percentile(list(range(1, 101)), 0.95) == 95
    assert s.percentile([1, 2, 3, 4], 0.5) == 2
    assert s.classify([100] * 3, [110] * 3, equal=True, counts_equal=True) == "PASS"
    assert s.classify([100] * 3, [111] * 3, equal=True, counts_equal=True) == "FAIL"
    assert s.classify([100] * 3, [90, 100, 110], equal=True, counts_equal=True) == "BLOCKED"
    assert s.classify([100] * 3, [100] * 3, equal=False, counts_equal=True) == "FAIL"
    assert s.classify([100] * 3, [100] * 3, equal=True, counts_equal=False) == "FAIL"
    for values in ([], [float("inf")], [-1]):
        with pytest.raises(ValueError):
            s.percentile(values, 0.95)
    with pytest.raises(ValueError):
        s.classify([1], [1], equal=True, counts_equal=True)


def test_small_trace_service_parity_and_query_count(conclusion_env, phase2_database_url, tmp_path):
    engine, service, principal, project, publication, draft, claim, ids = trace_fixture(
        conclusion_env, phase2_database_url, tmp_path, 25
    )

    def call():
        return service.trace(principal, project, publication, draft)

    with s.capture(engine) as before:
        expected = call()
    times, results = s.sample(call, 1, 3)
    with s.capture(engine) as after:
        actual = call()
    assert all(result == expected == actual for result in results)
    assert {p.placement_id for p in actual.placements} == set(ids)
    assert before.query_count == after.query_count
    s.save_observation(
        "benchmark-small-trace",
        {
            "status": "PASS",
            "profile": "small informational",
            "samples_ms": times,
            "p50_ms": s.percentile(times, 0.5),
            "p95_ms": s.percentile(times, 0.95),
            "query_counts": [before.query_count, after.query_count],
            "external_latency_ms": None,
        },
    )


def test_small_scaled_counts_and_complete_review_gate(m3, phase2_database_url, tmp_path):
    from tests.integration.phase2.pr2_20_scaled import build

    generated = build(m3, phase2_database_url, tmp_path, SMALL_COUNTS)
    assert generated["counts"] == SMALL_COUNTS
    for case in CASES:
        generated["prepare"](case)
        result = generated["call"](case, 1 if case == "decision-first-write" else 0)
        assert result is not None
    save_profile(profile(m3[7], False))


@pytest.mark.skipif(
    os.getenv("RB_PR220_BENCHMARK") != "1", reason="NOT RUN: opt-in large benchmark"
)
@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("workers", [1, 4])
@pytest.mark.parametrize("repeat", range(3))
def test_declared_large_service_profile(m3, phase2_database_url, tmp_path, case, workers, repeat):
    value = profile(m3[7], True)
    blockers = large_host_blockers(value)
    if blockers:
        save_profile(replace(value, reason="; ".join(blockers)))
        s.save_observation(
            f"benchmark-{case}-{workers}-{repeat}",
            {
                "status": "BLOCKED",
                "reason": "; ".join(blockers),
                "samples_ms": [],
                "external_latency_ms": None,
            },
        )
        pytest.skip("BLOCKED: " + "; ".join(blockers))
    from tests.integration.phase2.pr2_20_scaled import build

    generated = build(m3, phase2_database_url, tmp_path, LARGE_COUNTS)
    assert generated["counts"] == LARGE_COUNTS
    save_profile(value)
    generated["prepare"](case)

    def worker(index):
        cursor = iter(range(index * 105, (index + 1) * 105))

        def call():
            return generated["call"](case, next(cursor))

        return s.sample(call, 5, 100)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        observations = list(pool.map(worker, range(workers)))
    times = [sample for values, _ in observations for sample in values]
    assert len(times) == workers * 100
    s.save_observation(
        f"benchmark-{case}-{workers}-{repeat}",
        {
            "status": "BLOCKED",
            "reason": "Informational samples only; matching-subject baseline and repeti"
            "tion comparison required",
            "samples_ms": times,
            "p50_ms": s.percentile(times, 0.5),
            "p95_ms": s.percentile(times, 0.95),
            "max_ms": max(times),
            "actual_counts": generated["counts"],
            "external_latency_ms": None,
            "limitation": generated["limitation"],
        },
    )


# Novelty cardinalities are bounded independently of the scaled source/trace fixture.

b18_env = novelty.b18_env
pytest_plugins = ("tests.integration.phase2.pr2_18_fixtures",)
NOVELTY_CASES = novelty.NOVELTY_CASES


@pytest.mark.parametrize("workers", [1, 4])
@pytest.mark.parametrize(
    "large",
    [
        False,
        pytest.param(
            True,
            marks=pytest.mark.skipif(
                os.getenv("RB_PR220_BENCHMARK") != "1",
                reason="NOT RUN: opt-in novelty sampling profile",
            ),
        ),
    ],
)
def test_bounded_novelty_service_profile(b18_env, workers, large):
    e = b18_env
    value = profile(e["engine"], large)
    save_profile(value)
    protected = novelty.protected_manifest(e)
    for case in NOVELTY_CASES:
        kind, operation = case.rsplit("-", 1)
        for repeat in range(value.repetitions):
            before = s.manifest(e["engine"], novelty.NOVELTY_TABLES)
            # Allocate outside timing. Fresh roots never form a supersession chain.
            commands = [
                [
                    novelty.fresh_command(e, kind) if operation == "first" else e["commands"][kind]
                    for _ in range(value.warmups + value.calls_per_worker)
                ]
                for _ in range(workers)
            ]

            def worker(index, commands=commands, kind=kind, operation=operation):
                pending = iter(commands[index])

                def call():
                    return novelty.invoke(e, kind, operation, command=next(pending))

                return s.sample(call, value.warmups, value.calls_per_worker)

            with ThreadPoolExecutor(max_workers=workers) as pool:
                observations = list(pool.map(worker, range(workers)))
            times = [duration for durations, _ in observations for duration in durations]
            assert len(times) == workers * value.calls_per_worker
            for index, (_, results) in enumerate(observations):
                for command, result in zip(commands[index][value.warmups :], results, strict=True):
                    for check in ("replay", "read"):
                        assert novelty.stable(
                            novelty.invoke(e, kind, check, command=command)
                        ) == novelty.stable(result)
                    if kind == "coverage":
                        assert (
                            result.query_count,
                            result.result_count,
                            result.resolved_source_count,
                        ) == (1, 2, 1)
                    if kind == "novelty":
                        assert result.supersedes_assessment_id is None
            after = s.manifest(e["engine"], novelty.NOVELTY_TABLES)
            increments = {
                # This bounded fixture has one saved resolution per capture (B21).
                "coverage": {
                    "search_coverage",
                    "search_coverage_executions",
                    "search_coverage_resolutions",
                },
                "prior_art": {"prior_art_relations", "prior_art_evidence_inputs"},
                "novelty": {"novelty_assessments"},
            }[kind]
            for table in before:
                delta = (
                    workers * (value.warmups + value.calls_per_worker)
                    if operation == "first" and table in increments
                    else 0
                )
                assert after[table]["count"] == before[table]["count"] + delta
                if delta == 0:
                    assert after[table] == before[table]
            assert novelty.protected_manifest(e) == protected
            data = {
                "status": "PASS",
                "scope": "bounded correctness and informational timing only",
                "large_profile_acceptance": "NOT ESTABLISHED",
                "case": case,
                "workers": workers,
                "repeat": repeat,
                "warmups": value.warmups,
                "calls_per_worker": value.calls_per_worker,
                "samples_ms": times,
                "p50_ms": s.percentile(times, 0.5),
                "p95_ms": s.percentile(times, 0.95),
                "max_ms": max(times),
                "novelty_cardinalities": novelty.CARDINALITIES,
                "saved_ids_hashes": {
                    k: {"id": str(v.id), "content_hash": v.content_hash}
                    for k, v in e["saved"].items()
                },
                "sample_outputs": [
                    {
                        "id": str(result.id),
                        "content_hash": result.content_hash,
                        "created_at": result.created_at.isoformat(),
                        "created_by": str(result.created_by),
                    }
                    for _, results in observations
                    for result in results
                ],
                "postgres_version": value.postgres_version,
                "lock_wait_ms": None,
                "phantom_references": novelty.PHANTOM_REFERENCES,
                "external_latency_ms": None,
            }
            s.save_observation(f"novelty-{case}-{workers}-{repeat}", data)
            print("B18_BENCHMARK", data)


@pytest.mark.skipif(
    os.getenv("RB_B29_MEASUREMENT") != "1", reason="NOT RUN: opt-in B29 measurement"
)
def test_b29_measurement(decision_env, monkeypatch):
    """Only this opt-in runner installs candidate DDL, in disposable clones."""
    from dataclasses import asdict

    from tests.integration.phase2.b29_measurement import measure
    from tests.integration.phase2.pr2_20_scaled import build_b29

    # Explicit opt-in preserves durable evidence; ordinary test observations stay temporary.
    monkeypatch.setattr(evidence, "EVIDENCE_ROOT", ROOT)
    fixture = build_b29(decision_env)
    reference = asdict(profile(decision_env[-1][8], False))
    host = {
        key: reference[key]
        for key in (
            "host_os",
            "cpu_model",
            "kernel",
            "storage_model",
            "postgres_version",
            "python_version",
            "driver_version",
            "lock_sha256",
            "vcpus",
            "ram_gib",
            "shared_buffers_mb",
            "work_mem_mb",
            "max_connections",
            "jit",
            "track_io_timing",
        )
    }
    result = measure(decision_env[-1][8], fixture, host)
    assert len(result["rows"]) == 54
    assert result["status"] == "BLOCKED"  # measurements never self-admit DDL


PACKAGE_CASES = (
    "package-first-freeze",
    "package-exact-replay",
    "package-consent-denied",
    "package-frozen-read",
)

# Existing owning fixtures, registered locally without changing global bootstrap.
from tests.integration.phase2.b17_fixtures import b04_env, b05_env, revision_env  # noqa: E402

_B17_FIXTURES = (b04_env, b05_env, revision_env)


def test_bounded_prepared_package_service_profile(b05_env):
    from tests.integration.phase2.b17_fixtures import build, next_package, withdraw_consent

    from researchbase.foundation.errors import ErrorCode, ResearchBaseError

    f = build(b05_env)
    saved = f.app.freeze_prepared_submission(f.actor, f.command)
    current_frozen, current_receipt = f, saved
    value = profile(f.engine, False)
    inventory = {
        "projects": "projects",
        "sources": "literature_sources",
        "source_versions": "source_versions",
        "identifiers": "source_identifiers",
        "project_links": "literature_source_project_links",
        "claims": "claims",
        "manuscripts": "manuscript_versions",
        "conclusion_targets": "scientific_conclusion_versions",
        "reviews": "internal_review_records",
        "issues": "review_issues",
    }
    with s.read_snapshot(f.engine) as conn:
        cardinalities = {
            field: conn.execute(text("SELECT count(*) FROM " + table)).scalar_one()
            for field, table in inventory.items()
        }
        cardinalities["shared_sources"] = conn.execute(
            text(
                "SELECT count(*) FROM (SELECT literature_source_id "
                "FROM literature_source_project_links GROUP BY literature_source_id "
                "HAVING count(DISTINCT project_id)>1) shared"
            )
        ).scalar_one()
        cardinalities["busy_project_sources"] = conn.execute(
            text(
                "SELECT coalesce(max(n),0) FROM (SELECT count(*) n "
                "FROM literature_source_project_links GROUP BY project_id) busy"
            )
        ).scalar_one()
        cardinalities["evidence_per_claim"] = conn.execute(
            text(
                "SELECT coalesce(max(n),0) FROM (SELECT count(*) n "
                "FROM evidence_relations GROUP BY claim_version_id) evidence"
            )
        ).scalar_one()
        placements = sum(
            conn.execute(
                text("SELECT count(*) FROM " + table + " WHERE manuscript_version_id=:id"),
                {"id": f.package_command.manuscript_version_id},
            ).scalar_one()
            for table in (
                "manuscript_claim_placements",
                "manuscript_citation_placements",
                "manuscript_artifact_placements",
            )
        )
    value = replace(
        value,
        **cardinalities,
        seed=0,
        typical_placements=placements,
        high_placements=placements,
        concurrency_profiles=(1,),
    )
    save_profile(value)
    for case in PACKAGE_CASES:
        for repeat in range(value.repetitions):
            samples = value.warmups + value.calls_per_worker
            fresh = (
                [next_package(f) for _ in range(samples)]
                if case in {"package-first-freeze", "package-consent-denied"}
                else []
            )
            if case == "package-consent-denied":
                for fixture in fresh:
                    withdraw_consent(fixture)
            pending = iter(fresh)

            def invoke(case=case, pending=pending):
                nonlocal current_frozen, current_receipt
                if case == "package-first-freeze":
                    fixture = next(pending)
                    result = fixture.app.freeze_prepared_submission(fixture.actor, fixture.command)
                    current_frozen, current_receipt = fixture, result
                    return result
                if case == "package-exact-replay":
                    result = f.app.freeze_prepared_submission(f.actor, f.command)
                    assert result == saved
                    return result
                if case == "package-frozen-read":
                    result = current_frozen.app.get_prepared_submission(
                        current_frozen.actor, current_frozen.query
                    )
                    assert result.status == "FROZEN"
                    assert result.consumption_id == current_receipt.id
                    return result
                fixture = next(pending)
                try:
                    fixture.app.freeze_prepared_submission(fixture.actor, fixture.command)
                except ResearchBaseError as exc:
                    assert exc.code == ErrorCode.GRANT_STALE
                    return exc.code.value
                raise AssertionError("withdrawn consent must deny")

            times, results = s.sample(invoke, value.warmups, value.calls_per_worker)
            data = dict(
                status="PASS",
                scope="B17 bounded correctness and informational timing",
                large_profile_acceptance="NOT ESTABLISHED",
                case=case,
                workers=1,
                repeat=repeat,
                warmups=value.warmups,
                calls_per_worker=value.calls_per_worker,
                samples_ms=times,
                p50_ms=s.percentile(times, 0.5),
                p95_ms=s.percentile(times, 0.95),
                max_ms=max(times),
                failures=0,
                expected_denials=len(results) if case == "package-consent-denied" else 0,
                postgres_version=value.postgres_version,
                fixture_counts=dict(
                    samples=samples,
                    fresh_packages=len(fresh),
                    authors=1,
                    reviews=len(f.command.checked_review_ids),
                ),
                profile="SMALL",
                seed_semantics=(
                    "0: fixed Application fixture structure; UUID identities are unseeded"
                ),
                scientific_cardinalities=cardinalities,
                external_latency_ms=None,
            )
            s.save_observation(f"{case}-1-{repeat}", data)
            print("B17_BENCHMARK", data)


@pytest.mark.parametrize("case", APPROVAL_CASES)
@pytest.mark.parametrize("workers", [1, 4])
@pytest.mark.parametrize(
    "large",
    [
        False,
        pytest.param(
            True,
            marks=pytest.mark.skipif(
                os.getenv("RB_PR220_BENCHMARK") != "1", reason="NOT RUN: opt-in H2 approval profile"
            ),
        ),
    ],
)
def test_h2_unchanged_approval_inventories(approval_env, case, workers, large):
    from sqlalchemy import create_engine, event

    from researchbase.persistence.approval_repository import B09_DECIDE_SHARE_SQL, B09_SHARE_SQL

    engine = approval_env[-1][-1][8]
    value = profile(engine, large)
    if large:
        blockers = (
            *large_host_blockers(value),
            "H2 approval scientific envelope unverified; bounded fixture only",
        )
        if blockers:
            save_profile(replace(value, reason="; ".join(blockers)))
            pytest.skip("BLOCKED: " + "; ".join(blockers))
    warmups, calls = (5, 100) if large else (1, 2)
    observer = create_engine(engine.url)
    try:
        for repeat in range(3):
            invoke = approval_profile(approval_env, case, workers * (warmups + calls))
            locks = []
            sqlstates = {}

            def record_sqlstate(context, sqlstates=sqlstates):
                state = getattr(context.original_exception, "sqlstate", None)
                if state:
                    sqlstates[state] = sqlstates.get(state, 0) + 1

            def observe(conn, cursor, sql, parameters, context, many, locks=locks):
                if sql.startswith("LOCK TABLE"):
                    pid = conn.connection.driver_connection.info.backend_pid
                    locks.append(dict(sql=sql, **s.passive_locks(observer, (pid,))))

            event.listen(engine, "after_cursor_execute", observe)
            event.listen(engine, "handle_error", record_sqlstate)
            try:
                with s.capture(engine) as captured:

                    def worker(position, invoke=invoke):
                        cursor = iter(
                            range(position * (warmups + calls), (position + 1) * (warmups + calls))
                        )
                        return s.sample(lambda: invoke(next(cursor)), warmups, calls)

                    with ThreadPoolExecutor(max_workers=workers) as pool:
                        results = list(pool.map(worker, range(workers)))
            finally:
                event.remove(engine, "after_cursor_execute", observe)
                event.remove(engine, "handle_error", record_sqlstate)
            samples = [sample for times, _ in results for sample in times]
            assert len(samples) == workers * calls
            writers = [
                tx
                for tx in captured.transactions
                if any(sql.startswith("LOCK TABLE") for sql in tx)
            ]
            if case in {"request-first", "request-denied"}:
                assert writers and all(tx[0] == B09_SHARE_SQL for tx in writers)
            elif case in {"decision-first", "decision-denied"}:
                assert writers and all(
                    tx[:2]
                    == [B09_DECIDE_SHARE_SQL, "LOCK TABLE publications IN SHARE ROW EXCLUSIVE MODE"]
                    for tx in writers
                )
            else:
                assert not locks
            directory = evidence.EVIDENCE_ROOT / "pr_evidence/pr2-20" / subject()[2]
            paths = evidence.write_chunks(directory, f"h2-locks-{case}-{workers}-{repeat}", locks)
            s.save_observation(
                f"h2-approval-{case}-{workers}-{repeat}",
                dict(
                    status="BLOCKED",
                    reason="Reference host/baseline unavailable; inventories retained",
                    profile="declared" if large else "small informational",
                    samples_ms=samples,
                    p50_ms=s.percentile(samples, 0.5),
                    p95_ms=s.percentile(samples, 0.95),
                    throughput_per_second=len(samples) * 1000 / max(captured.elapsed_ms, 0.001),
                    first_sql=captured.transaction_first_statements,
                    inventory_refs=[
                        path.relative_to(evidence.EVIDENCE_ROOT).as_posix() for path in paths
                    ],
                    sqlstate_counts=sqlstates,
                ),
            )
    finally:
        observer.dispose()


@pytest.mark.parametrize("duplicate", [False, True])
def test_h2_same_target_writer_contention_observes_wait_and_no_partial_effect(
    approval_env, duplicate
):
    from threading import Event
    from time import monotonic
    from uuid import uuid4

    from sqlalchemy import create_engine, event, text

    from researchbase.foundation.errors import ErrorCode, ResearchBaseError

    service, actor, _, command, env = approval_env
    engine = env[-1][8]
    observer = create_engine(engine.url)
    entered, release = Event(), Event()
    pids, failures = [], {}

    def pause(conn, cursor, sql, parameters, context, many):
        if sql.startswith("INSERT INTO approval_requests") and not entered.is_set():
            pids.append(conn.connection.driver_connection.info.backend_pid)
            entered.set()
            assert release.wait(15)

    def sql_error(context):
        state = getattr(context.original_exception, "sqlstate", None)
        if state:
            failures[state] = failures.get(state, 0) + 1

    event.listen(engine, "after_cursor_execute", pause)
    event.listen(engine, "handle_error", sql_error)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(service.request_approval, actor, command)
            assert entered.wait(10)
            second = pool.submit(
                service.request_approval,
                actor,
                command if duplicate else replace(command, id=uuid4()),
            )
            deadline = monotonic() + 10
            witness = None
            while monotonic() < deadline:
                with s.read_snapshot(observer) as conn:
                    waiters = tuple(
                        conn.execute(
                            text(
                                "SELECT pid FROM pg_stat_activity "
                                "WHERE :pid=ANY(pg_blocking_pids(pid))"
                            ),
                            {"pid": pids[0]},
                        ).scalars()
                    )
                snapshot = s.passive_locks(observer, waiters)
                if any(
                    not row["granted"] and pids[0] in row["blockers"] and row["wait_ms"] > 0
                    for row in snapshot["locks"]
                ):
                    witness = snapshot
                    break
                if second.done():
                    second.result()
            assert witness is not None
            assert any(row["wait_ms"] > 0 for row in witness["locks"] if not row["granted"])
            release.set()
            saved = first.result(timeout=15)
            if duplicate:
                assert second.result(timeout=15) == saved
            else:
                with pytest.raises(ResearchBaseError) as caught:
                    second.result(timeout=15)
                assert caught.value.code == ErrorCode.IDEMPOTENCY_CONFLICT
        with s.read_snapshot(observer) as conn:
            assert conn.execute(text("SELECT count(*) FROM approval_requests")).scalar_one() == 1
            assert (
                conn.execute(text("SELECT count(*) FROM approval_grant_consumptions")).scalar_one()
                == 0
            )
        s.save_observation(
            f"h2-same-target-{duplicate}",
            dict(
                status="BLOCKED",
                reason="Bounded contention correctness; reference-host timing unavailable",
                witnesses=witness,
                sqlstate_counts=failures,
                duplicate=duplicate,
            ),
        )
    finally:
        release.set()
        event.remove(engine, "after_cursor_execute", pause)
        event.remove(engine, "handle_error", sql_error)
        observer.dispose()
