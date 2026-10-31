"""Explicit released-policy squash effects, with no retry of ambiguous HTTP writes."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import secrets
import signal
import subprocess
from pathlib import Path
from urllib.parse import quote

from scripts.pipeline_executor import run
from scripts.pipeline_protocol import (
    EXPECTED_CHECKS,
    StateStore,
    atomic_write,
    decode,
    encoded,
    exact,
    require,
)
from scripts.pipeline_safety import ProcessLock
from scripts.pipeline_wakeup import check_merge

MAIN = "ad1896git/researchbase"
SANDBOX = "ad1896git/researchbase-pipeline-sandbox"
APP_ID = 15368


def get(endpoint, *, pages=False):
    args = ("--paginate", "--slurp") if pages else ()
    return decode(run("gh", "api", endpoint, *args, timeout=30))


def put_merge(repository, number, body):
    # Never shell-escape or interpolate JSON; the complete request goes through stdin.
    result = subprocess.run(
        [
            "gh",
            "api",
            "--method",
            "PUT",
            f"repos/{repository}/pulls/{number}/merge",
            "--input",
            "-",
        ],
        input=encoded(body).decode(),
        text=True,
        capture_output=True,
        timeout=45,
    )
    require(result.returncode == 0, "merge request outcome needs remote reconciliation")
    return decode(result.stdout)


def checkpoint(name, pause_after):
    if name == pause_after:
        print(json.dumps(dict(checkpoint=name)), flush=True)
        signal.raise_signal(signal.SIGSTOP)


def immutable(path, value):
    require(not path.is_symlink(), "symlink merge journal")
    data = encoded(value)
    if path.exists():
        require(path.read_bytes() == data, "merge journal binding drift")
    else:
        atomic_write(path, data)


def controls(policy):
    """Optional v2 operational controls; v1 remains for immutable historical policies."""
    if policy["version"] == 1:
        return None
    require(policy["version"] == 2, "merge policy version")
    paths = []
    for key in ("stop_file", "merge_log"):
        path = Path(policy[key])
        require(path.is_absolute() and path.parent.is_dir(), "merge control parent missing")
        require(path.resolve() == path and not path.is_symlink(), "unsafe merge control path")
        paths.append(path)
    require(paths[0] != paths[1], "merge controls must differ")
    return tuple(paths)


def paused(policy):
    paths = controls(policy)
    return paths is not None and paths[0].exists()


def append_merge_log(policy, target, row, effect):
    paths = controls(policy)
    if paths is None:
        return
    log = paths[1]
    # Stable shared lock and atomic prefix-preserving append prevent torn/duplicate rows
    # across generations or a crash after logging but before the local done receipt.
    with ProcessLock(log.with_name(log.name + ".lock")):
        controls(policy)
        old = log.read_bytes() if log.exists() else b""
        require(not old or old.endswith(b"\n"), "incomplete existing merge log")
        timestamp = row["merged_at"]
        require(
            type(timestamp) is str and re.fullmatch(r"[0-9T:Z+.-]+", timestamp), "merge timestamp"
        )
        task = target["backlog_id"]
        require(type(task) is str and re.fullmatch(r"[A-Za-z0-9_-]+", task), "log task id")
        line = (
            f"| {timestamp} | {effect['repository']}#{effect['pr']} | {task} | "
            f"{effect['risk']} | {effect['sha']} | PASS: exact head/base; independent review; "
            "7 trusted CI; authorized risk/actor; squash parent/tree; source retained |\n"
        ).encode()
        marker = ("| " + effect["sha"] + " |").encode()
        matching = [r + b"\n" for r in old.splitlines() if marker in r]
        if matching:
            require(matching == [line], "merge log receipt conflict")
            return
        atomic_write(log, old + line)


def authorized(policy, entry_id):
    exact(
        policy,
        (
            "version",
            "enabled",
            "allow_low_risk",
            "execution_actor",
            "authorization_file",
            "authorization_sha256",
            "targets",
            "sandbox_rehearsal",
            "round_budget",
        )
        + (("stop_file", "merge_log") if policy["version"] == 2 else ()),
    )
    controls(policy)
    require(
        policy["version"] in (1, 2) and policy["enabled"] is True, "executor not explicitly enabled"
    )
    require(type(policy["allow_low_risk"]) is bool, "low-risk policy")
    require(type(policy["sandbox_rehearsal"]) is bool, "sandbox policy")
    require(
        type(policy["round_budget"]) is int and 1 <= policy["round_budget"] <= 40,
        "merge round budget",
    )
    require(re.fullmatch(r"[A-Za-z0-9-]{1,39}", policy["execution_actor"]), "execution actor")
    path = Path(policy["authorization_file"])
    require(path.is_absolute() and path.resolve() == path and path.is_file(), "authorization path")
    raw = path.read_bytes()
    require(
        hashlib.sha256(raw).hexdigest() == policy["authorization_sha256"], "authorization drift"
    )
    manifest = decode(raw.decode())
    require(manifest["version"] == 1 and type(manifest["tasks"]) is list, "authorization schema")
    target = policy["targets"][entry_id]
    exact(target, ("backlog_id", "scope_kind"))
    require(target["scope_kind"] in ("implementation", "audit"), "owner-only operation")
    rows = [t for t in manifest["tasks"] if t["id"] == target["backlog_id"]]
    require(len(rows) == 1 and rows[0]["authorized"] is True, "task not in authorized BACKLOG")
    require(rows[0]["id"] not in ("M01", "D01", "F01", "R02"), "owner-only task")
    require(rows[0]["risk"] in ("low", "medium", "high"), "unknown risk")
    return target, rows[0]["risk"]


def remote_pr(repository, number):
    row = get(f"repos/{repository}/pulls/{number}")
    require(row["number"] == number, "wrong remote PR")
    require(row["head"]["repo"]["full_name"].lower() == repository.lower(), "fork PR denied")
    return row


def protection_guard(repository, base):
    protection = get(f"repos/{repository}/branches/{quote(base, safe='')}/protection")
    required = protection["required_status_checks"]
    checks = required["checks"]
    require(
        required["strict"] is True
        and protection["enforce_admins"]["enabled"] is True
        and {c["context"] for c in checks} >= EXPECTED_CHECKS
        and all(c["app_id"] == APP_ID for c in checks if c["context"] in EXPECTED_CHECKS),
        "production main lacks strict non-bypass seven-check protection",
    )


def released_source_guard():
    """A candidate cannot merge itself or run production effects before its main release."""
    runtime = Path(__file__).resolve().parent.parent
    require(not run("git", "status", "--porcelain", cwd=runtime), "unreleased dirty merge runtime")
    head = run("git", "rev-parse", "HEAD", cwd=runtime)
    comparison = get(f"repos/{MAIN}/compare/main...{head}")
    require(
        comparison["ahead_by"] == 0 and comparison["merge_base_commit"]["sha"] == head,
        "merge executor must run from a commit already released on main",
    )


def preflight(repository, row, *, rehearsal):
    normalized = repository.lower()
    require(normalized in (MAIN, SANDBOX), "repository not authorized for merge effects")
    require(not row["draft"] and row["state"] == "open", "PR not open and ready")
    settings = get(f"repos/{repository}")
    require(settings["allow_squash_merge"] is True, "squash disabled")
    require(settings["delete_branch_on_merge"] is False, "server would delete source branch")
    if normalized == MAIN:
        require(not rehearsal and row["base"]["ref"] == "main", "production target mismatch")
        protection_guard(repository, "main")
        released_source_guard()
    else:
        require(rehearsal and row["head"]["ref"].startswith("pipeline-test/"), "sandbox scope")
    files = get(f"repos/{repository}/pulls/{row['number']}/files?per_page=100", pages=True)
    files = [r for page in files for r in page]
    require(
        len(files) == row["changed_files"] and len(files) < 3000, "incomplete PR file inventory"
    )
    for file in files:
        name = file["filename"]
        require(file["status"] not in ("removed", "renamed"), "deletion requires owner")
        require(
            not name.startswith(("docs/architecture/", "config/harness/", ".codex/"))
            and name not in ("AGENTS.md", "harness.lock.yaml"),
            "architecture/governing change requires owner",
        )
    base = get(f"repos/{repository}/git/ref/heads/{row['base']['ref']}")["object"]["sha"]
    require(base == row["base"]["sha"], "base reference drift")
    comparison = get(f"repos/{repository}/compare/{base}...{row['head']['sha']}")
    require(
        comparison["behind_by"] == 0 and comparison["merge_base_commit"]["sha"] == base,
        "source must contain exact base before squash",
    )
    source = get(f"repos/{repository}/git/commits/{row['head']['sha']}")
    return source["tree"]["sha"]


def authority(store, policy, entry_id, expected):
    store.lock.check()
    require(not (store.directory / "state.json").is_symlink(), "symlink authoritative state")
    require(
        (store.directory / "initialized").is_file()
        and not (store.directory / "initialized").is_symlink(),
        "initialization marker drift",
    )
    require(
        decode((store.directory / "state.json").read_text()) == store.state,
        "state drift before merge",
    )
    target, risk = authorized(policy, entry_id)
    require((target, risk) == expected, "task authorization drift before merge")


def reconcile(store, name, repository, row, intent, folder, policy, target):
    require((folder / "requested.json").is_file(), "external merge without this executor request")
    require(
        row["merged"] is True and row["merged_by"]["login"] == intent["execution_actor"],
        "unexpected merger",
    )
    require(row["head"]["sha"] == intent["head"], "merged head mismatch")
    require(
        (row["head"]["ref"], row["base"]["ref"])
        == (intent["source_branch"], intent["base_branch"]),
        "merged branch binding mismatch",
    )
    commit = get(f"repos/{repository}/git/commits/{row['merge_commit_sha']}")
    require(
        len(commit["parents"]) == 1
        and commit["parents"][0]["sha"] == intent["base"]
        and commit["tree"]["sha"] == intent["source_tree"]
        and f"pipeline-merge:{intent['id']}" in commit["message"],
        "unexpected squash result",
    )
    branch = get(f"repos/{repository}/git/ref/heads/{intent['source_branch']}")
    require(branch["object"]["sha"] == intent["head"], "source branch changed or deleted")
    effect = dict(
        repository=repository,
        pr=row["number"],
        head=intent["head"],
        base=intent["base"],
        sha=row["merge_commit_sha"],
        tree=commit["tree"]["sha"],
        source_tree=intent["source_tree"],
        parent=commit["parents"][0]["sha"],
        merger=row["merged_by"]["login"],
        intent_id=intent["id"],
        risk=intent["risk"],
        message=commit["message"],
        proofs_sha256=intent["proofs_sha256"],
        approval_event=intent["approval_event"],
        approval_actor=intent["approval_actor"],
    )
    immutable(folder / "effect.json", effect)
    append_merge_log(policy, target, row, effect)
    store.finish_merge(name, effect)
    return "done"


def execute_merge(store, name, repository, *, policy, entry_id, pause_after=None):
    """Caller owns driver.lock plus this StateStore; models never supply merge authority."""
    try:
        target, risk = authorized(policy, entry_id)
        require(
            repository.lower() != MAIN or policy["version"] == 2,
            "production merge controls required",
        )
        require(repository.lower() in (MAIN, SANDBOX), "unauthorized merge repository")
        require(
            (repository.lower() == SANDBOX) == policy["sandbox_rehearsal"],
            "rehearsal target mismatch",
        )
        task = store.state["tasks"][name]
        if task["status"] == "done":
            require(task["intent"]["kind"] == "merge", "completed task is not a merge")
            effect = decode((store.directory / task["result"]).read_text())["merge"]
            require(
                effect["repository"] == repository and effect["risk"] == risk,
                "completed merge replay scope mismatch",
            )
            target_file = store.directory / "merge-operations" / name / "target.json"
            prior = decode(target_file.read_text())
            require(
                prior["entry_id"] == entry_id
                and prior["authorization_sha256"] == policy["authorization_sha256"],
                "completed merge replay authorization mismatch",
            )
            return "done"
        require(task["status"] == "awaiting_merge", "not awaiting merge")
        binding = dict(task["merge"])
        folder = store.directory / "merge-operations" / name
        folder.mkdir(parents=True, exist_ok=True)
        require(
            folder.resolve() == folder and not folder.is_symlink(), "noncanonical merge journal"
        )
        target_binding = dict(
            repository=repository,
            pr=binding["pr"],
            head=binding["head"],
            base=binding["base"],
            entry_id=entry_id,
            target=target,
            risk=risk,
            authorization_sha256=policy["authorization_sha256"],
            execution_actor=policy["execution_actor"],
            allow_low_risk=policy["allow_low_risk"],
            sandbox_rehearsal=policy["sandbox_rehearsal"],
        )
        if policy["version"] == 2:
            target_binding["controls"] = {k: policy[k] for k in ("stop_file", "merge_log")}
        immutable(folder / "target.json", target_binding)
        row = remote_pr(repository, binding["pr"])
        intent_path = folder / "intent.json"
        intent = decode(intent_path.read_text()) if intent_path.exists() else None
        if row["merged"]:
            require(intent is not None, "manual/external merge needs operator reconciliation")
            return reconcile(store, name, repository, row, intent, folder, policy, target)
        if paused(policy):
            return "awaiting_merge"
        require(
            not (folder / "requested.json").exists(),
            "unknown merge request outcome; never resubmit",
        )
        require(store.state["rounds_used"] < policy["round_budget"], "merge budget exhausted")
        status = check_merge(
            store, name, repository, risk=risk, low_risk_enabled=policy["allow_low_risk"]
        )
        if status != "manual_merge_ready":
            return status
        row = remote_pr(repository, binding["pr"])
        require(
            (row["head"]["sha"], row["base"]["sha"]) == (binding["head"], binding["base"]),
            "head/base drift",
        )
        source_tree = preflight(repository, row, rehearsal=policy["sandbox_rehearsal"])
        require(get("user")["login"] == policy["execution_actor"], "execution identity drift")
        current = store.state["tasks"][name]["merge"]
        facts = dict(
            head=binding["head"],
            base=binding["base"],
            source_tree=source_tree,
            source_branch=row["head"]["ref"],
            base_branch=row["base"]["ref"],
            risk=risk,
            execution_actor=policy["execution_actor"],
            approval_event=current["approved_event"],
            approval_actor=current["approved_actor"],
            proofs_sha256=store.merge_proof_digest(name),
        )
        if intent is None:
            intent = dict(id=secrets.token_hex(12), **facts)
            immutable(intent_path, intent)
        else:
            require(
                {k: v for k, v in intent.items() if k != "id"} == facts,
                "pending merge intent drift",
            )
        checkpoint("before-request", pause_after)
        authority(store, policy, entry_id, (target, risk))
        require(
            check_merge(
                store, name, repository, risk=risk, low_risk_enabled=policy["allow_low_risk"]
            )
            == "manual_merge_ready",
            "final approval/CI changed",
        )
        approval = store.state["tasks"][name]["merge"]
        require(
            (approval["approved_event"], approval["approved_actor"])
            == (intent["approval_event"], intent["approval_actor"]),
            "final approval differs from frozen merge intent",
        )
        final = remote_pr(repository, binding["pr"])
        require(
            (final["head"]["sha"], final["base"]["sha"]) == (binding["head"], binding["base"]),
            "final head/base drift",
        )
        require(
            (final["head"]["ref"], final["base"]["ref"])
            == (intent["source_branch"], intent["base_branch"]),
            "final branch binding drift",
        )
        require(
            preflight(repository, final, rehearsal=policy["sandbox_rehearsal"]) == source_tree,
            "source tree drift",
        )
        authority(store, policy, entry_id, (target, risk))
        require(store.merge_proof_digest(name) == intent["proofs_sha256"], "readiness proof drift")
        immutable(folder / "target.json", target_binding)
        immutable(intent_path, intent)
        request = dict(
            sha=intent["head"],
            merge_method="squash",
            commit_title=f"Pipeline squash PR {binding['pr']} [pipeline-merge:{intent['id']}]",
            commit_message=(
                f"Bound head {intent['head']}; base {intent['base']}; retained source branch."
            ),
        )
        if paused(policy):
            return "awaiting_merge"
        immutable(folder / "requested.json", dict(intent_id=intent["id"], request=request))
        checkpoint("unknown-request-window", pause_after)
        if paused(policy):
            return "awaiting_merge"
        response = put_merge(repository, binding["pr"], request)
        require(response["merged"] is True, "remote did not confirm merge")
        checkpoint("after-merge", pause_after)
        return reconcile(
            store,
            name,
            repository,
            remote_pr(repository, binding["pr"]),
            intent,
            folder,
            policy,
            target,
        )
    except Exception as exc:
        if store.state["tasks"][name]["status"] == "awaiting_merge":
            store.block(name, f"merge blocked: {type(exc).__name__}: {exc}"[:4000])
        return "blocked"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--entry-id", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--approver", action="append", default=[])
    parser.add_argument(
        "--pause-after", choices=("before-request", "after-merge", "unknown-request-window")
    )
    args = parser.parse_args()
    with (
        ProcessLock(args.control / "driver.lock"),
        StateStore(args.control, args.evidence, merge_approvers=frozenset(args.approver)) as store,
    ):
        status = execute_merge(
            store,
            args.task,
            args.repository,
            policy=decode(args.policy.read_text()),
            entry_id=args.entry_id,
            pause_after=args.pause_after,
        )
    print(json.dumps(dict(status=status)), flush=True)
    return 0 if status == "done" else 2


if __name__ == "__main__":
    raise SystemExit(main())
