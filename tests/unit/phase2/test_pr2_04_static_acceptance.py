"""Static gates reject new debt against the pinned, authorized Phase 2 baseline."""

import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from scripts.pr2_04_pytest_evidence import FactRecorder

ROOT = Path(__file__).resolve().parents[3]
BASELINE = ROOT / "tests/fixtures/phase2_static_baseline.json"
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

    baseline = json.loads(BASELINE.read_text())
    assert ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini"))).get_heads() == [
        baseline["migration_head"]
    ]
    assert baseline["baseline_commit"] == "b8179f17720ca47c3b25ad9d36f6a8e8d4aa79ff"
    assert (
        execute(
            ["git", "merge-base", "--is-ancestor", baseline["baseline_commit"], "HEAD"]
        ).returncode
        == 0
    )
    scopes = ["src", "migrations", "tests", "scripts"]
    lint = execute([sys.executable, "-m", "ruff", "check", *scopes, "--output-format", "json"])
    assert lint.returncode in {0, 1}
    lint_diagnostics = [
        (str(Path(row["filename"]).relative_to(ROOT)), row["code"], row["message"])
        for row in json.loads(lint.stdout)
    ]
    types = execute([sys.executable, "-m", "pyright", "--outputjson"])
    assert types.returncode in {0, 1}
    type_diagnostics = [
        (str(Path(row["file"]).relative_to(ROOT)), row["severity"], row.get("rule"), row["message"])
        for row in json.loads(types.stdout)["generalDiagnostics"]
    ]
    # Exact file/rule/message multisets cap inherited debt; new or duplicated errors fail.
    assert not (Counter(lint_diagnostics) - Counter(map(tuple, baseline.get("ruff", []))))
    assert not (Counter(type_diagnostics) - Counter(map(tuple, baseline["pyright"])))
    lineage = execute([sys.executable, RECOVERY_GATES, "lineage"])
    assert lineage.returncode == 0
    assert json.loads(lineage.stdout)["recovery_lineage"]["status"] == "PASS"
    # Whitespace/format deltas start at the current authorized baseline below.
    raw = execute([sys.executable, "-m", "ruff", "format", "--check", *scopes])
    assert raw.returncode in {0, 1}
    current = set(re.findall(r"^Would reformat: (.+)$", raw.stdout + raw.stderr, re.MULTILINE))
    assert current <= set(baseline.get("formatter", []))
    assert (raw.returncode == 0 and not current) or (raw.returncode == 1 and bool(current))
    changed = execute(
        [
            "git",
            "diff",
            "--name-only",
            "--diff-filter=ACMR",
            baseline["baseline_commit"],
            "--",
            "*.py",
            "*.pyi",
        ]
    )
    assert changed.returncode == 0
    assert execute(["git", "diff", "--check", baseline["baseline_commit"]]).returncode == 0
    files = changed.stdout.splitlines()
    if files:
        assert execute([sys.executable, "-m", "ruff", "check", *files]).returncode == 0
        assert execute([sys.executable, "-m", "ruff", "format", "--check", *files]).returncode == 0
    pr204_trace.record(
        static_baseline=baseline["baseline_commit"],
        changed_files=files,
        inherited_lint_diagnostics=len(lint_diagnostics),
        inherited_type_diagnostics=len(type_diagnostics),
        inherited_formatter_failures=sorted(current),
        new_static_diagnostics=0,
    )
