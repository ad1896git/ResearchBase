"""P01 prerequisites must fail before formatter or lineage success is possible."""

import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def _gates():
    from scripts import pr2_04_recovery_static_gates

    return pr2_04_recovery_static_gates


def test_missing_baseline_prevents_formatter_invocation():
    gates = _gates()
    calls = []
    with pytest.raises(subprocess.CalledProcessError):
        gates.format_changed(ROOT, base="0" * 40, formatter=lambda files: calls.append(files))
    assert calls == []


def test_missing_candidate_prevents_formatter_invocation():
    gates = _gates()
    calls = []
    with pytest.raises(subprocess.CalledProcessError):
        gates.format_changed(ROOT, head="0" * 40, formatter=lambda files: calls.append(files))
    assert calls == []


def test_nonancestor_baseline_prevents_formatter_invocation():
    gates = _gates()
    calls = []
    with pytest.raises(subprocess.CalledProcessError):
        gates.format_changed(
            ROOT,
            base="HEAD",
            head=gates.TRUSTED_BASE,
            formatter=lambda files: calls.append(files),
        )
    assert calls == []


def test_failed_file_selection_cannot_be_empty_success(monkeypatch):
    gates = _gates()
    original = gates.git
    calls = []

    def fail_selection(root, *args):
        if args[:2] == ("diff", "--name-only"):
            raise subprocess.CalledProcessError(128, ["git", *args], b"", b"bad object")
        return original(root, *args)

    monkeypatch.setattr(gates, "git", fail_selection)
    with pytest.raises(subprocess.CalledProcessError):
        gates.format_changed(ROOT, formatter=lambda files: calls.append(files))
    assert calls == []


def test_verified_empty_diff_needs_no_formatter():
    gates = _gates()
    calls = []
    result = gates.format_changed(ROOT, base="HEAD", formatter=lambda files: calls.append(files))
    assert result["files"] == [] and result["formatter_exit_code"] == 0
    assert calls == []


def test_formatter_failure_is_propagated_with_verified_scope():
    gates = _gates()
    calls = []

    def formatter(files):
        calls.append(files)
        return 9

    result = gates.format_changed(ROOT, formatter=formatter)
    assert result["formatter_exit_code"] == 9
    assert calls == [result["files"]] and result["files"]
    assert "src/researchbase/domain/literature_search_execution.py" in result["files"]


def test_missing_historical_lineage_is_not_recovery_pass():
    gates = _gates()
    result = gates.lineage(ROOT)
    assert result["historical_lineage"]["status"] == "NOT_RUN"
    assert result["historical_lineage"]["object_exit_code"] != 0
    assert result["recovery_lineage"]["status"] == "PASS"
    assert result["recovery_lineage"]["base"] == gates.TRUSTED_BASE
    assert result["original_history_recovered"] is False


def test_missing_recovery_object_cannot_generate_lineage_pass():
    gates = _gates()
    with pytest.raises(subprocess.CalledProcessError):
        gates.lineage(ROOT, base="0" * 40)


def test_missing_diff_prerequisite_exits_nonzero_without_pass():
    gates = _gates()
    with pytest.raises(subprocess.CalledProcessError):
        gates.diff_check(ROOT, base="0" * 40)


def test_cli_lineage_reports_separate_recovery_and_history():
    completed = subprocess.run(
        ["python3", "scripts/pr2_04_recovery_static_gates.py", "lineage"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["historical_lineage"]["status"] == "NOT_RUN"
    assert result["comparison_kind"] == "RECOVERY_TRUSTED_BASE_TO_CANDIDATE"


def test_host_consumers_use_recovery_gates_without_unconditional_lineage_pass():
    shell = (ROOT / "scripts/researchbase_host_pr2_04_verification.sh").read_text()
    static = (ROOT / "tests/unit/phase2/test_pr2_04_static_acceptance.py").read_text()
    assert "record frozen_contract_lineage PASS" not in shell
    assert 'git diff --name-only -z "$FROZEN_CONTRACT"' not in shell
    assert 'git diff --check "$FROZEN_CONTRACT"' not in shell
    assert '"accepted_baseline":sys.argv[3]' not in shell
    assert '"diff", "--check", CONTRACT' not in static
    assert (
        "pr2_04_recovery_static_gates.py" in shell and "pr2_04_recovery_static_gates.py" in static
    )


def _run_formatter_block(shell, tmp_path, monkeypatch):
    """Run only the real formatter subgate; never the host/DB runner."""
    import os

    start = shell.find('git diff --name-only -z "$FROZEN_CONTRACT"')
    if start < 0:
        start = shell.index("python3 scripts/pr2_04_recovery_static_gates.py formatter")
    end = shell.index('python3 - "$OUT/logs/formatter_raw.log"', start)
    out = tmp_path / "out"
    (out / "logs").mkdir(parents=True)
    probe = tmp_path / "git"
    probe.write_text('#!/bin/sh\necho "forced missing prerequisite" >&2\nexit 128\n')
    probe.chmod(0o700)
    monkeypatch.setenv("PATH", str(tmp_path) + os.pathsep + os.environ["PATH"])
    script = "\n".join(
        [
            "set -uo pipefail",
            'record() { printf "%s %s\\n" "$1" "$2"; }',
            "FROZEN_CONTRACT=ea216c9babea322808b3885f563d276b571575ab",
            "RECOVERY_COMPARISON_BASE=14143dc09983ce1765b3b39fda536691193fd868",
            "HEAD=HEAD",
            'OUT="$1"',
            shell[start:end],
        ]
    )
    return subprocess.run(
        ["bash", "-c", script, "formatter-subgate", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_host_formatter_block_fails_closed_on_git_error(tmp_path, monkeypatch):
    shell = (ROOT / "scripts/researchbase_host_pr2_04_verification.sh").read_text()
    result = _run_formatter_block(shell, tmp_path, monkeypatch)
    assert "formatter_changed_scope FAIL" in result.stdout
    assert "formatter_changed_scope PASS" not in result.stdout


def test_f2_formatter_false_pass_is_reproduced_without_host_execution(tmp_path, monkeypatch):
    shell = subprocess.check_output(
        [
            "git",
            "show",
            "86658eb83bb0552da36510368d70fe5c049ec086:"
            "scripts/researchbase_host_pr2_04_verification.sh",
        ],
        cwd=ROOT,
        text=True,
    )
    result = _run_formatter_block(shell, tmp_path, monkeypatch)
    assert "formatter_changed_scope PASS" in result.stdout
    assert "forced missing prerequisite" in result.stderr


@pytest.mark.parametrize("gate", ["lineage", "formatter", "diff-check"])
def test_cli_failed_git_prerequisite_cannot_emit_pass(gate, tmp_path, monkeypatch):
    import os

    probe = tmp_path / "git"
    probe.write_text('#!/bin/sh\necho "missing object" >&2\nexit 128\n')
    probe.chmod(0o700)
    monkeypatch.setenv("PATH", str(tmp_path) + os.pathsep + os.environ["PATH"])
    result = subprocess.run(
        ["python3", "scripts/pr2_04_recovery_static_gates.py", gate],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "PASS" not in result.stdout and "missing object" in result.stderr


def test_host_lineage_block_reports_missing_history_separately(tmp_path):
    shell = (ROOT / "scripts/researchbase_host_pr2_04_verification.sh").read_text()
    start = shell.index("python3 scripts/pr2_04_recovery_static_gates.py lineage >")
    end = shell.index("record phase1_migration_non_drift", start)
    (tmp_path / "logs").mkdir()
    script = "\n".join(
        [
            "set -uo pipefail",
            'record() { printf "%s %s\\n" "$1" "$2"; }',
            'OUT="$1"',
            "RECOVERY_COMPARISON_BASE=14143dc09983ce1765b3b39fda536691193fd868",
            "HEAD=HEAD",
            shell[start:end],
        ]
    )
    result = subprocess.run(
        ["bash", "-c", script, "lineage-subgate", str(tmp_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "recovery_baseline_lineage PASS" in result.stdout
    assert "frozen_contract_lineage NOT_RUN" in result.stdout
    assert "frozen_contract_lineage PASS" not in result.stdout
