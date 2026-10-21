"""P01 recovery comparisons; never evidence of missing historical ancestry.

Formatter and whitespace scope starts at the actual trusted pre-recovery base,
so every reconstructed Python change and subsequent remediation is included.
The existing B production and C migration content seals remain separate gates.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRUSTED_BASE = "14143dc09983ce1765b3b39fda536691193fd868"
HISTORICAL_CONTRACT = "ea216c9babea322808b3885f563d276b571575ab"
KIND = "RECOVERY_TRUSTED_BASE_TO_CANDIDATE"


def git(root: Path, *args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, check=True).stdout


def comparison(root: Path, base: str, head: str) -> dict:
    # Resolve both objects before deriving an empty scope or any PASS label.
    resolved_base = git(root, "rev-parse", "--verify", base + "^{commit}").decode().strip()
    resolved_head = git(root, "rev-parse", "--verify", head + "^{commit}").decode().strip()
    git(root, "merge-base", "--is-ancestor", resolved_base, resolved_head)
    return {"comparison_kind": KIND, "base": resolved_base, "head": resolved_head}


def lineage(root: Path, base: str = TRUSTED_BASE, head: str = "HEAD") -> dict:
    result = comparison(root, base, head)
    probe = subprocess.run(
        ["git", "cat-file", "-e", HISTORICAL_CONTRACT + "^{commit}"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    historical = {
        "base": HISTORICAL_CONTRACT,
        "object_exit_code": probe.returncode,
        "status": "NOT_RUN",
        "reason": "Historical object prerequisite unavailable; no ancestry assertion executed.",
    }
    if probe.returncode == 0:
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", HISTORICAL_CONTRACT, result["head"]],
            cwd=root,
            capture_output=True,
            check=False,
        )
        historical.update(
            status="PASS" if ancestor.returncode == 0 else "FAIL",
            ancestry_exit_code=ancestor.returncode,
            reason="Actual historical ancestry command executed.",
        )
    result.update(
        historical_lineage=historical,
        recovery_lineage={"base": result["base"], "status": "PASS"},
        original_history_recovered=False,
    )
    return result


def format_changed(
    root: Path,
    base: str = TRUSTED_BASE,
    head: str = "HEAD",
    formatter: Callable[[list[str]], int] | None = None,
) -> dict:
    result = comparison(root, base, head)
    selected = git(
        root,
        "diff",
        "--name-only",
        "-z",
        "--diff-filter=ACMR",
        result["base"],
        result["head"],
        "--",
        "*.py",
        "*.pyi",
    )
    files = [item.decode() for item in selected.split(b"\0") if item]
    if formatter is None:

        def formatter(files: list[str]) -> int:
            return subprocess.run(
                ["uv", "run", "ruff", "format", "--check", *files],
                cwd=root,
                check=False,
            ).returncode

    rc = formatter(files) if files else 0
    result.update(files=files, formatter_exit_code=rc)
    return result


def diff_check(root: Path, base: str = TRUSTED_BASE, head: str = "HEAD") -> dict:
    result = comparison(root, base, head)
    git(root, "diff", "--check", result["base"], result["head"])
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("gate", choices=("lineage", "formatter", "diff-check"))
    args = parser.parse_args()
    try:
        if args.gate == "lineage":
            result = lineage(ROOT)
        elif args.gate == "formatter":
            result = format_changed(ROOT)
        else:
            result = diff_check(ROOT)
        print(json.dumps(result, sort_keys=True))
        return result.get("formatter_exit_code", 0)
    except (subprocess.CalledProcessError, OSError) as error:
        print(f"Recovery gate prerequisite or command failed: {error}", file=sys.stderr)
        if isinstance(error, subprocess.CalledProcessError) and error.stderr:
            print(error.stderr.decode(errors="replace"), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
