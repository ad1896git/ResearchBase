"""Explicit A01/A02 recovery content binding; never historical ancestry proof."""

import ast
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def baseline():
    data = json.loads((ROOT / "scripts/pr2_04_recovery_baseline.json").read_text())
    assert data["schema"] == "pr204-explicit-recovery-baseline-v1"
    assert data["original_history_recovered"] is False
    assert data["migration_base"] == "bf0a8a14037e21ea8ad086c6b1ab01239d36c650"
    assert data["recovery_base"] == "dd7dece1b7403a39d662c8fd16d50e4f75201e6d"
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", data["recovery_base"], "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    for name, digest in data["source_sha256"].items():
        sealed = subprocess.check_output(
            ["git", "show", data["recovery_base"] + ":" + name], cwd=ROOT
        )
        assert hashlib.sha256(sealed).hexdigest() == digest
    return data


def validate_migration_prefix(source_ref=None):
    data = baseline()
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", data["migration_base"], "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    prefix = {
        n: h for n, h in data["source_sha256"].items() if n.startswith("migrations/versions/")
    }
    if source_ref is None:
        current = {
            str(p.relative_to(ROOT)): p.read_bytes()
            for p in (ROOT / "migrations/versions").glob("*.py")
        }
    else:
        paths = subprocess.check_output(
            ["git", "ls-tree", "-r", "--name-only", source_ref, "--", "migrations/versions"],
            cwd=ROOT,
            text=True,
        ).splitlines()
        current = {
            p: subprocess.check_output(["git", "show", source_ref + ":" + p], cwd=ROOT)
            for p in paths
            if p.endswith(".py")
        }

    child = "migrations/versions/0025_pr2_04_reservation_guards.py"
    assert set(current) == set(prefix) | ({child} if child in current else set())
    for name, digest in prefix.items():
        parent_bytes = subprocess.check_output(
            ["git", "show", data["migration_base"] + ":" + name], cwd=ROOT
        )
        assert hashlib.sha256(parent_bytes).hexdigest() == digest
        assert hashlib.sha256(current[name]).hexdigest() == digest, name
    revisions = {}
    for p in current.values():
        values = {}
        for n in ast.parse(p).body:
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Name) and t.id in {"revision", "down_revision"}:
                        values[t.id] = ast.literal_eval(n.value)
            elif (
                isinstance(n, ast.AnnAssign)
                and isinstance(n.target, ast.Name)
                and n.target.id in {"revision", "down_revision"}
            ):
                values[n.target.id] = ast.literal_eval(n.value)
        if values.get("revision"):
            revisions[values["revision"]] = values.get("down_revision")
    heads = set(revisions) - {v for v in revisions.values() if isinstance(v, str)}
    expected = (
        "0025_pr2_04_reservation_guards" if child in current else "0024_literature_search_execution"
    )
    assert heads == {expected}
    if child in current:
        assert revisions[expected] == "0024_literature_search_execution"
    return {
        "binding_kind": "EXPLICIT_RECOVERY_CONTENT",
        "recovery_base": data["recovery_base"],
        "migration_head": expected,
        "subject": source_ref or "WORKTREE",
        "original_history_recovered": False,
    }


def validate_production_scope():
    data = baseline()
    expected = {n: h for n, h in data["source_sha256"].items() if n.startswith("src/")}
    current = {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (ROOT / "src").rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    }
    assert current == expected
    return {
        "binding_kind": "EXPLICIT_RECOVERY_CONTENT",
        "recovery_base": data["recovery_base"],
        "files": len(expected),
        "original_history_recovered": False,
    }


F2_CANDIDATE = "86658eb83bb0552da36510368d70fe5c049ec086"


def historical_gate_scope():
    """Exact F2 seals govern F2, never new development source bytes."""
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if head != F2_CANDIDATE:
        return {
            "status": "NOT_APPLICABLE",
            "subject": F2_CANDIDATE,
            "candidate": head,
            "reason": "historical exact-content checks require the F2 subject",
        }
    return {"status": "APPLICABLE", "subject": head, "candidate": head}


if __name__ == "__main__":
    scope = historical_gate_scope()
    if scope["status"] == "APPLICABLE":
        validate_migration_prefix()
        validate_production_scope()
    print(json.dumps(scope, sort_keys=True))
