"""Execute the static acceptance gate, rather than infer it from a summary."""

import json
import re
import subprocess
from pathlib import Path

import pytest
from scripts.pr2_04_pytest_evidence import FactRecorder

ROOT = Path(__file__).resolve().parents[3]
RECOVERY_GATES = "scripts/pr2_04_recovery_static_gates.py"


@pytest.mark.pr204_requirements("PR204-REG-03")
def test_candidate_static_gates_and_inherited_formatter_delta(pr204_trace: FactRecorder) -> None:
    def execute(arguments: list[str]) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(arguments, cwd=ROOT, capture_output=True, text=True, check=False)
        pr204_trace.record(
            command=arguments,
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )
        return result

    assert (
        execute(["uv", "run", "ruff", "check", "src", "migrations", "tests", "scripts"]).returncode
        == 0
    )
    assert execute(["uv", "run", "pyright"]).returncode == 0
    lineage = execute(["python3", RECOVERY_GATES, "lineage"])
    assert lineage.returncode == 0
    lineage_result = json.loads(lineage.stdout)
    pr204_trace.record(recovery_lineage=lineage_result)
    assert lineage_result["recovery_lineage"]["status"] == "PASS"
    # Historical NOT_RUN remains explicit; recovery comparison is a separate proof.
    assert execute(["python3", RECOVERY_GATES, "diff-check"]).returncode == 0
    formatted = execute(["python3", RECOVERY_GATES, "formatter"])
    assert formatted.returncode == 0
    # Preserved historical evidence can contain verbatim diagnostic Python drivers.
    # It is immutable run material, not repository implementation to reformat.
    raw = execute(
        ["uv", "run", "ruff", "format", "--check", ".", "--exclude", "artifacts/pr_evidence"]
    )
    assert raw.returncode in {0, 1}
    raw_text = raw.stdout + raw.stderr
    current = set(re.findall(r"^Would reformat: (.+)$", raw_text, re.MULTILINE))
    baseline = set(
        json.loads((ROOT / "artifacts/pr_evidence/PR2-00/formatter_baseline.json").read_text())[
            "baseline"
        ]["failing_files"]
    )
    pr204_trace.record(
        recovery_formatter_output=formatted.stdout,
        current_formatter_failures=sorted(current),
        baseline_formatter_failures=sorted(baseline),
        new_formatter_failures=sorted(current - baseline),
    )
    assert current <= baseline
    assert (raw.returncode == 0 and not current) or (raw.returncode == 1 and bool(current))
