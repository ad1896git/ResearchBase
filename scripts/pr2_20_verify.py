"""Focused B31-S4 owning acceptance collection and generated Phase 2 artifacts."""

from __future__ import annotations

import json
import os
import platform
import shlex
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any
from unittest.mock import patch

# Direct script execution, independent of an installed tests package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import create_engine, text  # noqa: E402
from tests.contracts.pr2_20_evidence import (  # noqa: E402
    canonical_bytes,
    digest_bytes,
    redact,
)
from tests.contracts.pr2_20_reports import (  # noqa: E402
    AQ_S3,
    B31_CONTRACT,
    EXIT_CRITERIA,
    EXIT_FILES,
    LINUX_DISPOSITION,
    ROOT,
    context,
    exit_rows,
    subject,
    validate_exit,
    verification_findings,
    verified_acceptance,
    write_reports,
)
from tests.integration.phase2.pr2_20_support import (  # noqa: E402
    database,
    read_snapshot,
    require_pg18,
)

STATIC = (
    ("sync", ("uv", "sync", "--locked", "--group", "dev")),
    ("ruff", ("uv", "run", "ruff", "check", ".")),
    ("format", ("uv", "run", "ruff", "format", "--check", ".")),
    ("pyright", ("uv", "run", "pyright")),
    ("heads", ("uv", "run", "alembic", "heads")),
)
FOCUSED = (
    "tests/unit/phase2/test_pr2_20_evidence.py",
    "tests/unit/phase2/test_pr2_20_exit_report.py",
    "tests/unit/phase2/test_pr2_20_inventory.py",
    "tests/architecture/test_pr2_20_boundaries.py",
)
POSTGRES = (
    "tests/integration/phase2/test_pr2_20_security.py",
    "tests/integration/phase2/test_pr2_20_catalog_plans.py",
    "tests/integration/phase2/test_pr2_20_migrations.py",
    "tests/integration/phase2/test_pr2_20_governance_races.py",
    "tests/integration/phase2/test_pr2_20_novelty.py",
    "tests/e2e/test_pr2_20_benchmark.py",
)
OWNING = tuple(sorted({path for paths in EXIT_FILES.values() for path in paths} - set(POSTGRES)))


def counts_from_xml(path: Path) -> dict[str, int]:
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    total = sum(int(item.get("tests", "0")) for item in suites)
    counts = {
        name: sum(int(item.get(attribute, "0")) for item in suites)
        for name, attribute in (
            ("failed", "failures"),
            ("errors", "errors"),
            ("skipped", "skipped"),
        )
    }
    counts["passed"] = total - sum(counts.values())
    return counts


def cases_from_xml(path: Path) -> list[dict[str, str]]:
    """Retain every parametrized result; setup/teardown errors are never PASS."""
    cases = []
    for item in ET.parse(path).getroot().iter("testcase"):
        status = "PASS"
        for tag, result in (("skipped", "SKIPPED"), ("failure", "FAIL"), ("error", "ERROR")):
            if item.find(tag) is not None:
                status = result
        cases.append(
            dict(
                node=item.attrib["classname"].replace(".", "/") + ".py::" + item.attrib["name"],
                status=status,
            )
        )
    return cases


def collect_acceptance(results: list[dict[str, Any]], directory: Path, root: Path = ROOT) -> None:
    """Attach per-row, subject-bound owning assertions, preserving every missing case."""
    ctx = context(root)
    prefix = directory.relative_to(root).as_posix() + "/"
    # This is the attached scope disposition, not owner acceptance of Phase 2.
    disposition = directory / "scope-dispositions.json"
    disposition.write_bytes(
        canonical_bytes(
            dict(
                scope="OWNER_SCOPE_DISPOSITIONS",
                source_refs=[B31_CONTRACT, AQ_S3, LINUX_DISPOSITION],
                decision_ids=[
                    "D-B31-01",
                    "D-B31-03",
                    "AQ-S3-08",
                    "Linux benchmark host 2026-10-20",
                ],
                phase2_owner_acceptance=False,
            )
        )
    )
    for number, row in enumerate(exit_rows(root), 1):
        if row.status == "DEFERRED":
            continue
        sources = [
            result
            for result in results
            if result["label"] in {"changed-postgres", "owning-acceptance"}
            and any(path in result["files"] for path in EXIT_FILES[row.criterion])
        ]
        cases = [
            case
            for result in sources
            for case in result["cases"]
            if case["node"].split("::")[0] in EXIT_FILES[row.criterion]
        ]
        nodes = {}
        missing = []
        for node in row.test_nodes:
            matches = [case for case in cases if case["node"].split("[")[0] == node]
            nodes[node] = (
                "PASS" if matches and all(c["status"] == "PASS" for c in matches) else "BLOCKED"
            )
            if nodes[node] != "PASS":
                missing.append(node)
        counts = {
            name: sum(case["status"] == status for case in cases)
            for name, status in (
                ("passed", "PASS"),
                ("failed", "FAIL"),
                ("errors", "ERROR"),
                ("skipped", "SKIPPED"),
            )
        }
        blockers = []
        if not row.test_nodes or not cases:
            blockers.append("No executed owning assertions")
        if missing:
            blockers.append("Missing/non-PASS owning nodes: " + ", ".join(missing))
        if any(result["exit_code"] != 0 for result in sources):
            blockers.append(
                "Owning command failed: " + ", ".join(r["label"] for r in sources if r["exit_code"])
            )
        deferral = {
            EXIT_CRITERIA[4]: (
                AQ_S3,
                "AQ-S3-08: positive G2 AGENT admission pending; owner-accepted known gap "
                "2026-10-20; all other owning assertions verified",
            ),
            EXIT_CRITERIA[16]: (
                LINUX_DISPOSITION,
                "Dedicated Linux benchmark host not tested for now; owner-accepted deferral "
                "2026-10-20 for benchmark-host part only; local macOS timings informational, "
                "not a substitute; all other owning assertions verified",
            ),
        }.get(row.criterion)
        logs = tuple(dict.fromkeys(ref for result in sources for ref in result["logs"]))
        ref = prefix + f"owning-{number:02d}.json"
        candidate = replace(
            row,
            acceptance_revision=ctx["subject_revision"],
            status="BLOCKED" if blockers else "DEFERRED" if deferral else "PASS",
            reason="; ".join(blockers) if blockers else deferral[1] if deferral else None,
            commands=tuple(result["command"] for result in sources),
            exit_codes=tuple(result["exit_code"] for result in sources),
            evidence_refs=(ref, *logs),
            disposition_refs=(
                prefix + disposition.name,
                *((deferral[0],) if deferral and not blockers else ()),
            ),
            **counts,
        )
        payload = dict(
            scope="OWNING_ACCEPTANCE",
            subject_revision=ctx["subject_revision"],
            dirty_diff_sha256=ctx["dirty_diff_sha256"],
            acceptance_revision=candidate.acceptance_revision,
            mode="ENABLED",
            optional=False,
            criterion=row.criterion,
            commands=candidate.commands,
            exit_codes=candidate.exit_codes,
            nodes=nodes,
            cases=cases,
            counts=counts,
            count_scope=(
                "Every case in this row's owning files; shared command totals "
                "appear in verification.json"
            ),
            logs=logs,
            log_sha256={ref: digest_bytes((root / ref).read_bytes()) for ref in logs},
            row=asdict(candidate),
        )
        (root / ref).write_bytes(canonical_bytes(payload))
        if candidate.status in {"PASS", "DEFERRED"} and not verified_acceptance(candidate, root):
            raise RuntimeError(f"Generated owning evidence rejected: {row.criterion}")


def run_command(
    label: str, argv: tuple[str, ...], directory: Path, scratch: Path
) -> dict[str, Any]:
    invocation = list(argv)
    xml = scratch / (label + ".xml")
    is_pytest = "pytest" in argv
    if is_pytest:
        invocation.extend(("--tb=short", "--junitxml", str(xml)))
    env = dict(os.environ)
    env["UV_CACHE_DIR"] = str(ROOT / ".uv-cache")
    # Only the explicit large-profile command opts in. B29's closed measurement
    # must not be re-enabled: its runner writes durable evidence by design.
    env.pop("RB_B29_MEASUREMENT", None)
    if label == "large-benchmark":
        env["RB_PR220_BENCHMARK"] = "1"
    else:
        env.pop("RB_PR220_BENCHMARK", None)
    print("RUN", label, shlex.join(invocation), flush=True)
    started = time.monotonic()
    completed = subprocess.run(
        invocation, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False
    )
    output = redact(completed.stdout.decode("utf-8", errors="replace"))
    logs = []
    raw = output.encode()
    for number, offset in enumerate(range(0, max(1, len(raw)), 1024 * 1024)):
        path = directory / f"{label}-{number:03d}.txt"
        path.write_bytes(raw[offset : offset + 1024 * 1024])
        logs.append(path.relative_to(ROOT).as_posix())
    counts = counts_from_xml(xml) if is_pytest and xml.exists() else None
    cases = cases_from_xml(xml) if is_pytest and xml.exists() else []
    if xml.exists():
        # The XML is also sanitized; test-produced observations themselves stay in tmp_path.
        xml_target = directory / (label + "-junit.xml")
        xml_target.write_text(redact(xml.read_text()))
        logs.append(xml_target.relative_to(ROOT).as_posix())
    result = dict(
        label=label,
        command=("RB_PR220_BENCHMARK=1 " if label == "large-benchmark" else "")
        + shlex.join(invocation),
        exit_code=completed.returncode,
        counts=counts,
        cases=cases,
        files=[arg for arg in argv if arg.endswith(".py")],
        logs=logs,
        elapsed_seconds=time.monotonic() - started,
        scope="FOCUSED",
        status="FAIL"
        if completed.returncode
        else "BLOCKED"
        if counts and counts["skipped"]
        else "PASS",
    )
    print("RESULT", label, completed.returncode, counts, flush=True)
    if completed.returncode:
        print(output[-6000:], flush=True)
    return result


def verify() -> int:
    ctx = context()
    directory = ROOT / "pr_evidence/pr2-20" / subject()[2]
    directory.mkdir(parents=True, exist_ok=True)
    commands = [
        *STATIC,
        ("unit-architecture", ("uv", "run", "pytest", *FOCUSED)),
        ("changed-postgres", ("uv", "run", "pytest", *POSTGRES)),
        ("owning-acceptance", ("uv", "run", "pytest", *OWNING)),
        ("large-benchmark", ("uv", "run", "pytest", "tests/e2e/test_pr2_20_benchmark.py")),
    ]
    results = []
    # Scratch/JUnit paths are outside the authored subject. Tests use their normal
    # tmp_path evidence root; only this script publishes sanitized acceptance records.
    with tempfile.TemporaryDirectory(prefix="b31-s4-") as temporary:
        scratch = Path(temporary)
        for label, argv in commands:
            if subject()[2] != directory.name:
                raise RuntimeError("Authored subject changed during verification; rerun")
            if label in {"changed-postgres", "owning-acceptance", "large-benchmark"}:
                # Fresh disposable database, never an application database.
                with database() as url, patch.dict(os.environ, {"DATABASE_URL": url}):
                    engine = create_engine(url)
                    try:
                        with read_snapshot(engine) as connection:
                            postgres = dict(
                                version=require_pg18(engine),
                                settings=dict(
                                    connection.execute(
                                        text(
                                            "SELECT name,setting FROM pg_settings WHERE name IN "
                                            "('shared_buffers','work_mem','max_connections',"
                                            "'jit','track_io_timing')"
                                        )
                                    ).all()
                                ),
                            )
                        result = run_command(label, argv, directory, scratch)
                        result["postgres"] = postgres
                    finally:
                        engine.dispose()
            else:
                result = run_command(label, argv, directory, scratch)
            results.append(result)
            (directory / "verification.json").write_bytes(
                canonical_bytes(dict(**ctx, scope="FOCUSED", host=host_details(), results=results))
            )
    collect_acceptance(results, directory)
    write_reports()
    rows = exit_rows(acceptance_directory=directory)
    verdict = validate_exit(rows, verification_findings(directory))
    write_verification(ctx, directory, results, verdict)
    print("EXIT", verdict, flush=True)
    # A blocked exit is a non-successful gate even if every executable assertion passes.
    return int(verdict != "PASS" or any(result["exit_code"] for result in results))


def host_details() -> dict[str, Any]:
    return dict(
        os=platform.platform(),
        kernel=platform.release(),
        architecture=platform.machine(),
        cpu=platform.processor() or platform.machine(),
        logical_cpus=os.cpu_count(),
        python=platform.python_version(),
        dedicated_linux_attested=False,
        benchmark_disposition=(
            "DEFERRED: owner 2026-10-20; dedicated Linux host not tested for now"
        ),
    )


def write_verification(ctx, directory: Path, results, verdict: str) -> None:
    postgres = next((r["postgres"] for r in results if "postgres" in r), {})
    body = (
        "# PR2-20 focused verification\n\n"
        f"Subject `{ctx['subject_revision']}`; authored dirty diff `{ctx['dirty_diff_sha256']}`. "
        "Generated reports/evidence are excluded from their own digest.\n\n"
        "[Recorded commands, host and counts](#focused-commands). "
        "Counts below are exact command totals. Each OWNING_ACCEPTANCE record partitions "
        "those cases by the row's owning files and retains every parametrized outcome. "
        "ENABLED describes the required acceptance check, not a live provider. "
        "The verifier never runs the whole suite. Static checks have no pytest counts. "
        "Test observations remain in tmp_path; sanitized raw JSON/logs remain local under "
        f"`{directory.relative_to(ROOT).as_posix()}`. Report links target tracked Markdown "
        "because the sandbox prohibits writing Git's index. No evidence directory was staged.\n\n"
        "## Subject\n\n"
        "```json\n"
        + json.dumps(
            {key: ctx[key] for key in ("subject_revision", "dirty_diff_sha256")},
            sort_keys=True,
            indent=2,
        )
        + "\n```\n\n"
        f"Actual local host: `{json.dumps(host_details(), sort_keys=True)}`. "
        f"Actual PostgreSQL: `{json.dumps(postgres, sort_keys=True)}`. "
        "Local timing is informational; it cannot satisfy the dedicated Linux host requirement.\n\n"
        "## Focused commands\n\n"
        "| Command | Exit | Passed | Failed | Errors | Skipped | Status |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n"
    )
    for item in results:
        counts = item["counts"] or dict(passed="—", failed="—", errors="—", skipped="—")
        body += (
            f"| `{item['command']}` | {item['exit_code']} | {counts['passed']} | "
            f"{counts['failed']} | {counts['errors']} | {counts['skipped']} | {item['status']} |\n"
        )
    body += (
        f"\nComputed validate_exit verdict: **{verdict}**. Owner acceptance is separate. "
        "B28 real PaperQA2 is DEFERRED under the owner 2026-10-19 disposition. "
        f"AQ-S3-08 defers only positive G2 AGENT admission ({AQ_S3}); dedicated Linux "
        f"benchmark host defers only the Row 17 host requirement ({LINUX_DISPOSITION}). "
        "Both are owner-accepted 2026-10-20; every other owning assertion must pass. "
        f"B20 NO_CLOSE_PRIOR_ART, B23 and MANUSCRIPT_CHANGE are Phase 2 exit non-goals "
        f"under D-B31-03 ({B31_CONTRACT}). "
        "No independent reviewer or loop full-suite result is inferred. "
        "See phase2_exit_report.md for every remaining owner decision. "
        "STOP; wait for explicit Phase 3 GO.\n"
    )
    body += "\n## Row evidence\n\n"
    for number, row in enumerate(exit_rows(acceptance_directory=directory), 1):
        body += (
            f"### Exit row {number}\n\n"
            "Recorded after verification of the owning assertions and local log digests. "
            "Raw evidence paths below identify local artifacts; they are not file links.\n\n"
            f"```json\n{json.dumps(asdict(row), sort_keys=True, indent=2)}\n```\n\n"
        )
    (ROOT / "docs/phase2/pr2_20_verification.md").write_text(body)


if __name__ == "__main__":
    raise SystemExit(verify())
