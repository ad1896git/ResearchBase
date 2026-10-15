"""Focused PR220 verification and sanitized machine records; never run the whole suite."""

from __future__ import annotations

import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

# Direct script execution, independent of an installed tests package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests.contracts.pr2_20_evidence import canonical_bytes, redact, write_chunks  # noqa: E402
from tests.contracts.pr2_20_reports import ROOT, context, subject, write_reports  # noqa: E402
from tests.integration.phase2.pr2_20_support import database  # noqa: E402

STATIC = (
    ("sync", ("uv", "sync", "--locked", "--group", "dev")),
    ("ruff", ("uv", "run", "ruff", "check", ".")),
    ("format", ("uv", "run", "ruff", "format", "--check", ".")),
    ("pyright", ("uv", "run", "pyright")),
    ("heads", ("uv", "run", "alembic", "heads")),
)
OWNING = (
    "tests/integration/phase2/test_pr2_01_source_identity.py",
    "tests/integration/phase2/test_pr2_13_scientific_trace.py",
    "tests/integration/phase2/test_pr2_14_internal_review.py",
    "tests/integration/phase2/test_pr2_15_coordination.py",
    "tests/integration/phase2/test_pr2_15_decision.py",
    "tests/integration/phase2/test_pr2_15_decision_schema.py",
    "tests/integration/phase2/test_pr2_12_migration.py",
    "tests/integration/phase2/test_pr2_19_citation_trace.py",
)


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


def verify() -> int:
    ctx = context()
    directory = ROOT / "pr_evidence/pr2-20" / subject()[2]
    directory.mkdir(parents=True, exist_ok=True)
    scratch = ROOT / "tmp/pr220-verification"
    scratch.mkdir(parents=True, exist_ok=True)
    commands = list(STATIC)
    changed = sorted(
        str(path.relative_to(ROOT))
        for path in (ROOT / "tests/integration/phase2").glob("test_pr2_20_*.py")
    )
    commands.extend(
        (
            ("unit-architecture", ("uv", "run", "pytest", "tests/unit", "tests/architecture")),
            (
                "changed-postgres",
                ("uv", "run", "pytest", *changed, "tests/e2e/test_pr2_20_benchmark.py"),
            ),
            ("owning-postgres", ("uv", "run", "pytest", *OWNING)),
            (
                "phase1-golden",
                (
                    "uv",
                    "run",
                    "pytest",
                    *(
                        str(path.relative_to(ROOT))
                        for path in sorted((ROOT / "tests/e2e").glob("test_phase1_*.py"))
                    ),
                ),
            ),
            ("large-benchmark", ("uv", "run", "pytest", "tests/e2e/test_pr2_20_benchmark.py")),
        )
    )
    results = []
    with database() as url, patch.dict(os.environ, {"DATABASE_URL": url}):
        for label, argv in commands:
            if subject()[2] != directory.name:
                raise RuntimeError("Authored subject changed during verification; rerun")
            invocation = list(argv)
            xml = scratch / (label + ".xml")
            is_pytest = "pytest" in argv
            if is_pytest:
                invocation.extend(("--junitxml", str(xml.relative_to(ROOT))))
            env = dict(os.environ)
            env["UV_CACHE_DIR"] = str(ROOT / ".uv-cache")
            if label == "large-benchmark":
                env["RB_PR220_BENCHMARK"] = "1"
            else:
                env.pop("RB_PR220_BENCHMARK", None)
            print("RUN", label, " ".join(invocation), flush=True)
            started = time.monotonic()
            completed = subprocess.run(
                invocation,
                cwd=ROOT,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            output = redact(completed.stdout.decode("utf-8", errors="replace"))
            # Logs and XML may exceed one file; retain every byte in numbered files.
            raw = output.encode()
            logs = []
            for number, offset in enumerate(range(0, max(1, len(raw)), 1024 * 1024)):
                path = directory / f"{label}-{number:03d}.txt"
                path.write_bytes(raw[offset : offset + 1024 * 1024])
                logs.append(path.relative_to(ROOT).as_posix())
            counts = counts_from_xml(xml) if is_pytest and xml.exists() else None
            if is_pytest and xml.exists():
                sanitized = redact(xml.read_text())
                # Bounded fragments are stored as JSON arrays for deterministic reconstruction.
                fragments = [
                    sanitized[index : index + 15000] for index in range(0, len(sanitized), 15000)
                ]
                write_chunks(directory, f"{label}-junit", fragments)
            result = dict(
                label=label,
                command=("RB_PR220_BENCHMARK=1 " if label == "large-benchmark" else "")
                + " ".join(invocation),
                exit_code=completed.returncode,
                counts=counts,
                logs=logs,
                elapsed_seconds=time.monotonic() - started,
                scope="FOCUSED",
                status="PASS" if completed.returncode == 0 else "FAIL",
            )
            if label == "large-benchmark" and counts and counts["skipped"]:
                result["status"] = "BLOCKED"
            results.append(result)
            (directory / "verification.json").write_bytes(
                canonical_bytes(
                    dict(
                        subject_revision=ctx["subject_revision"],
                        dirty_diff_sha256=ctx["dirty_diff_sha256"],
                        scope="FOCUSED",
                        results=results,
                    )
                )
            )
            print("RESULT", label, completed.returncode, counts, flush=True)
            if completed.returncode:
                print(output[-6000:], flush=True)
    write_reports()
    docs = ROOT / "docs/phase2"
    intro = (
        "# PR2-20 focused verification\n\n"
        f"Subject `{ctx['subject_revision']}`; authored dirty diff "
        f"`{ctx['dirty_diff_sha256']}`. "
        "Generated reports/evidence are excluded from their own digest.\n\n"
        f"[Machine commands and logs](../../pr_evidence/pr2-20/{directory.name}/"
        "verification.json). "
        "The verifier never runs the whole suite. Static checks have no pytest counts. "
        "Skipped large cases are BLOCKED timing evidence, not passes.\n\n"
        "| Command | Exit | Passed | Failed | Errors | Skipped |\n| --- | --- | --- | --"
        "- | --- | --- |\n"
    )
    for item in results:
        counts = item["counts"] or dict(passed="—", failed="—", errors="—", skipped="—")
        intro += (
            f"| `{item['command']}` | {item['exit_code']} | {counts['passed']} | "
            f"{counts['failed']} | {counts['errors']} | {counts['skipped']} |\n"
        )
    intro += (
        "\nIndependent read-only review found subject exclusion, false exit-PASS, raw se"
        "cret-validation "
        "and benchmark-attribution defects during authoring. Those were corrected and c"
        "overed by focused tests. "
        "Follow-up read-only review confirmed those fixes and found no remaining semantic "
        "P0/P1 in that scope; a missing test import was corrected before this run. "
        "No reviewer or owner exit acceptance is inferred from this log. "
        "The existing transport destination finding remains P1 and prevents exit success. "
        "Host/profile prerequisites and real PaperQA2 intake remain BLOCKED. "
        "Owner dispositions for inherited contracts are not attached. STOP; wait for ex"
        "plicit Phase 3 GO.\n"
    )
    (docs / "pr2_20_verification.md").write_text(intro)
    return int(any(item["exit_code"] for item in results))


if __name__ == "__main__":
    raise SystemExit(verify())
