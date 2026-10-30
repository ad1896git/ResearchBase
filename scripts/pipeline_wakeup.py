"""Single scheduled entry: run prepared generations, observe approvals, never merge."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import plistlib
import re
import shutil
import sys
from pathlib import Path

from scripts.pipeline_ci import classify
from scripts.pipeline_driver import Policy, run_cycle
from scripts.pipeline_executor import run
from scripts.pipeline_protocol import (
    ID,
    StateStore,
    atomic_write,
    commit,
    decode,
    encoded,
    exact,
    require,
)
from scripts.pipeline_safety import ProcessLock

LABEL = "com.researchbase.pipeline-wakeup"


def absolute(raw):
    require(type(raw) is str and Path(raw).is_absolute(), "absolute path required")
    path = Path(raw)
    require(path.resolve() == path and not path.is_symlink(), "noncanonical path")
    return path


def interpreter(raw):
    require(type(raw) is str and Path(raw).is_absolute(), "absolute Python required")
    path = Path(raw)
    require(
        path.parent.resolve() == path.parent
        and path.resolve().is_file()
        and os.access(path, os.X_OK),
        "invalid Python executable",
    )
    # Preserve a venv's symlink spelling: resolving it changes sys.prefix.
    return path


def environment(config):
    return {
        "PYTHONPATH": config["runtime"],
        "CODEX_HOME": config["codex_home"],
        "PATH": ":".join(config["executable_dirs"]),
    }


def notify(root, value):
    folder = root / "notifications"
    folder.mkdir(exist_ok=True)
    require(not folder.is_symlink(), "symlink notifications")
    payload = encoded(value)
    path = folder / (hashlib.sha256(payload).hexdigest() + ".json")
    if not path.exists():
        atomic_write(path, payload)
        print(json.dumps(value), file=sys.stderr, flush=True)


def query(*args):
    # All remote operations in this module are GETs. No merge, label or settings writes.
    return decode(run("gh", *args, timeout=30))


def observe(repository, number):
    require(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository), "repository")
    pr = query(
        "pr",
        "view",
        str(number),
        "--repo",
        repository,
        "--json",
        "number,state,isDraft,headRefOid,baseRefOid,headRepository,labels",
    )
    require(pr["number"] == number, "wrong PR")
    require(pr["headRepository"]["nameWithOwner"].lower() == repository.lower(), "fork PR")
    events = query(
        "api", f"repos/{repository}/issues/{number}/events?per_page=100", "--paginate", "--slurp"
    )
    events = [row for page in events for row in page]
    require(len(events) <= 10000, "too many issue events")
    ids = [row["id"] for row in events]
    require(all(type(i) is int and i > 0 for i in ids) and len(set(ids)) == len(ids), "event IDs")
    relevant = sorted(
        (
            e
            for e in events
            if e["event"] in ("labeled", "unlabeled") and e["label"]["name"] == "approved-merge"
        ),
        key=lambda e: e["id"],
    )
    effective = None
    labels = {label["name"] for label in pr["labels"]}
    if relevant and relevant[-1]["event"] == "labeled" and "approved-merge" in labels:
        effective = (relevant[-1]["id"], relevant[-1]["actor"]["login"])
    pages = query(
        "api",
        f"repos/{repository}/commits/{pr['headRefOid']}/check-runs?per_page=100&filter=all",
        "--paginate",
        "--slurp",
    )
    rows = [row for page in pages for row in page["check_runs"]]
    require(len(rows) <= 1000, "too many CI checks")
    require(pages and all(p["total_count"] == len(rows) for p in pages), "incomplete CI pages")
    require(len({r["id"] for r in rows}) == len(rows), "duplicate check run IDs")
    outcome = classify(rows, pr["headRefOid"])
    checks = [dict(name=r["name"], head=r["head_sha"], conclusion=r["conclusion"]) for r in rows]
    return dict(
        pr=pr,
        labels=labels,
        effective=effective,
        cursor=max(ids, default=0),
        checks=checks,
        outcome=outcome,
    )


def check_merge(store, name, repository):
    binding = store.state["tasks"][name]["merge"]
    first = observe(repository, binding["pr"])
    second = observe(repository, binding["pr"])
    require(first == second, "PR approval/CI changed during observation")
    pr, effective = second["pr"], second["effective"]
    require(second["cursor"] >= binding["after_event"], "incomplete approval history")
    if pr["state"] != "OPEN" or pr["isDraft"]:
        return "manual_reconciliation"
    same = (pr["headRefOid"], pr["baseRefOid"]) == (binding["head"], binding["base"])
    if (
        same
        and effective is not None
        and effective[0] > max(binding["after_event"], binding["approved_event"] or 0)
        and effective[1] in store.merge_approvers
    ):
        store.approve_label(
            name,
            event_id=effective[0],
            label="approved-merge",
            pr=binding["pr"],
            head=binding["head"],
            base=binding["base"],
            actor=effective[1],
        )
    ready = store.merge_allowed(
        name,
        head=pr["headRefOid"],
        base=pr["baseRefOid"],
        checks=second["checks"],
        labels=second["labels"],
        label_cursor=second["cursor"],
        effective_approval=effective,
    )
    if store.state["tasks"][name]["status"] == "blocked":
        return "blocked"
    return "manual_merge_ready" if ready and second["outcome"] == "pass" else "awaiting_merge"


def load_config(path):
    config = decode(path.read_text())
    exact(
        config,
        (
            "version",
            "root",
            "queue",
            "runtime",
            "python",
            "source_head",
            "approvers",
            "codex_home",
            "executable_dirs",
        ),
    )
    require(config["version"] == 1, "config version")
    for key in ("root", "queue", "runtime", "codex_home"):
        absolute(config[key])
    interpreter(config["python"])
    require(
        type(config["executable_dirs"]) is list
        and config["executable_dirs"]
        and all(
            type(p) is str and Path(p).is_absolute() and ":" not in p and "\x00" not in p
            for p in config["executable_dirs"]
        ),
        "absolute executable directories required",
    )
    commit(config["source_head"])
    require(
        type(config["approvers"]) is list
        and all(
            type(a) is str and re.fullmatch(r"[A-Za-z0-9-]{1,39}", a) for a in config["approvers"]
        ),
        "explicit approver allowlist",
    )
    return config


def source_guard(config):
    runtime = absolute(config["runtime"])
    for tool in ("gh", "git", "codex"):
        require(
            shutil.which(tool, path=environment(config)["PATH"]) is not None,
            f"missing executable: {tool}",
        )
    require(Path(__file__).resolve().parent.parent == runtime, "wrong runtime checkout")
    require(
        run("git", "rev-parse", "HEAD", cwd=runtime) == config["source_head"], "runtime head drift"
    )
    require(not run("git", "status", "--porcelain", cwd=runtime), "dirty runtime checkout")


def wake(config):
    source_guard(config)
    root = absolute(config["root"])
    root.mkdir(parents=True, exist_ok=True)
    lock = ProcessLock(root / "wakeup.lock")
    if not lock.acquire():
        return {"status": "busy"}
    try:
        queue = decode(absolute(config["queue"]).read_text())
        exact(queue, ("version", "entries"))
        require(queue["version"] == 1 and type(queue["entries"]) is list, "queue format")
        entries, controls = {}, set()
        for entry in queue["entries"]:
            exact(
                entry,
                ("id", "control", "evidence", "checkout", "jobs", "jobs_sha256", "repository"),
            )
            require(type(entry["id"]) is str and ID.fullmatch(entry["id"]), "queue entry ID")
            require(entry["id"] not in entries, "duplicate queue entry")
            for key in ("control", "evidence", "checkout", "jobs"):
                absolute(entry[key])
            require(entry["control"] not in controls, "duplicate generation")
            controls.add(entry["control"])
            jobs = absolute(entry["jobs"]).read_bytes()
            require(hashlib.sha256(jobs).hexdigest() == entry["jobs_sha256"], "jobs digest drift")
            entries[entry["id"]] = (entry, decode(jobs.decode()))
        admitted = root / "admitted.json"
        old = decode(admitted.read_text()) if admitted.exists() else {}
        require(
            all(key in entries and entries[key][0] == value for key, value in old.items()),
            "queue removal or binding drift",
        )
        atomic_write(admitted, encoded({key: value[0] for key, value in entries.items()}))
        results = {}
        runnable = []
        for key, (entry, jobs) in entries.items():
            control, evidence = absolute(entry["control"]), absolute(entry["evidence"])
            lease = ProcessLock(control / "driver.lock")
            if not lease.acquire():
                results[key] = "busy"
                continue
            try:
                with StateStore(
                    control, evidence, merge_approvers=frozenset(config["approvers"])
                ) as store:
                    for name, task in list(store.state["tasks"].items()):
                        if task["status"] == "awaiting_merge":
                            status = check_merge(store, name, entry["repository"])
                            notify(
                                root,
                                dict(entry=key, task=name, status=status, binding=task["merge"]),
                            )
            except Exception as exc:
                notify(
                    root, dict(entry=key, status="blocked", reason=f"{type(exc).__name__}: {exc}")
                )
                results[key] = "blocked"
                continue
            finally:
                lease.close()
            runnable.append((key, entry, jobs))
        # Complete the read-only scan for every generation before entering a long CI wait.
        for key, entry, jobs in runnable:
            result = run_cycle(
                absolute(entry["control"]),
                absolute(entry["evidence"]),
                absolute(entry["checkout"]),
                jobs,
                policy=Policy(),
                park_human_gates=True,
            )
            results[key] = result["status"]
            if result["status"] in ("blocked", "budget_exhausted"):
                notify(root, dict(entry=key, status=result["status"]))
        return dict(status="checked", entries=results)
    finally:
        lock.close()


def render_plist(config, config_path):
    """Render only. Installation/launchctl activation is a separately authorized deployment."""
    runtime = absolute(config["runtime"])
    root = absolute(config["root"])
    return plistlib.dumps(
        dict(
            Label=LABEL,
            StartInterval=300,
            RunAtLoad=True,
            ProgramArguments=[
                config["python"],
                "-m",
                "scripts.pipeline_wakeup",
                "--config",
                str(config_path),
            ],
            WorkingDirectory=str(runtime),
            EnvironmentVariables=environment(config),
            StandardOutPath=str(root / "launchd.stdout.log"),
            StandardErrorPath=str(root / "launchd.stderr.log"),
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--render-plist", type=Path)
    args = parser.parse_args()
    try:
        config = load_config(args.config)
        if args.render_plist:
            args.render_plist.write_bytes(render_plist(config, args.config.resolve()))
            return 0
        os.environ.update(environment(config))
        print(json.dumps(wake(config)), flush=True)
        return 0
    except Exception as exc:
        print(
            json.dumps(dict(status="blocked", reason=f"{type(exc).__name__}: {exc}")),
            file=sys.stderr,
            flush=True,
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
