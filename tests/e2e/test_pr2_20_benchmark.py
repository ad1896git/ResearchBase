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
from tests.integration.phase2 import pr2_20_support as s
from tests.integration.phase2.test_m3_evidence import m3 as _m3
from tests.integration.phase2.test_pr2_20_catalog_plans import trace_fixture

m3 = _m3
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

    with engine.connect() as conn:
        settings = dict(
            conn.execute(
                text(
                    "SELECT name,setting FROM pg_settings WHERE name IN "
                    "('shared_buffers','work_mem','max_connections','jit','track_io_timing')"
                )
            ).all()
        )
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
