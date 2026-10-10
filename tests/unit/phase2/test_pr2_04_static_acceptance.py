"""Execute the static acceptance gate, rather than infer it from a summary."""

import json
import re
import subprocess
from pathlib import Path

import pytest
from scripts.pr2_04_pytest_evidence import FactRecorder

ROOT = Path(__file__).resolve().parents[3]
CONTRACT = "ea216c9babea322808b3885f563d276b571575ab"


@pytest.mark.pr204_requirements("PR204-REG-03")
def test_candidate_static_gates_and_inherited_formatter_delta(pr204_trace: FactRecorder) -> None:
    def execute(arguments: list[str]) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(arguments, cwd=ROOT, capture_output=True, text=True, check=False)
        pr204_trace.record(command=arguments, exit_code=result.returncode,
                           stdout=result.stdout, stderr=result.stderr)
        return result

    assert execute(["uv", "run", "ruff", "check", "src", "migrations", "tests", "scripts"]).returncode == 0
    assert execute(["uv", "run", "pyright"]).returncode == 0
    assert execute(["git", "diff", "--check", CONTRACT, "HEAD"]).returncode == 0
    changed = execute(["git", "diff", "--name-only", CONTRACT, "HEAD", "--", "*.py", "*.pyi"])
    assert changed.returncode == 0
    changed_files = changed.stdout.splitlines()
    assert changed_files
    assert execute(["uv", "run", "ruff", "format", "--check", *changed_files]).returncode == 0
    raw = execute(["uv", "run", "ruff", "format", "--check", "."])
    assert raw.returncode in {0, 1}
    raw_text = raw.stdout + raw.stderr
    current = set(re.findall(r"^Would reformat: (.+)$", raw_text, re.MULTILINE))
    baseline = set(json.loads((ROOT / "artifacts/pr_evidence/PR2-00/formatter_baseline.json").read_text())["baseline"]["failing_files"])
    pr204_trace.record(changed_files=changed_files, current_formatter_failures=sorted(current),
                       baseline_formatter_failures=sorted(baseline),
                       new_formatter_failures=sorted(current - baseline))
    assert current <= baseline
    assert (raw.returncode == 0 and not current) or (raw.returncode == 1 and bool(current))
