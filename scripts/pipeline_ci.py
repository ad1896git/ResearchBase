"""Bounded read-only CI polling against an exact sandbox PR/head/base binding."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from scripts.pipeline_executor import Target, run
from scripts.pipeline_protocol import (
    EXPECTED_CHECKS,
    ExecutionReceipt,
    StateStore,
    atomic_write,
    decode,
    encoded,
    integer,
    require,
)
from scripts.pipeline_worker import authority


@dataclass(frozen=True)
class CITarget:
    repository: str
    pr: int
    branch: str
    head: str
    base: str
    base_commit: str

    def validate(self):
        integer(self.pr, 1)
        Target(
            self.repository,
            self.base,
            self.branch,
            str(Path.cwd()),
            self.head,
            self.base_commit,
        ).validate()


class CIObserver:
    def __init__(self, target: CITarget):
        self.target = target

    def observe(self) -> dict:
        t = self.target
        pr = json.loads(
            run(
                "gh",
                "pr",
                "view",
                str(t.pr),
                "--repo",
                t.repository,
                "--json",
                "number,headRefName,headRefOid,baseRefName,baseRefOid,state,isDraft,headRepository",
            )
        )
        require(
            pr["number"] == t.pr
            and pr["headRefName"] == t.branch
            and pr["headRefOid"] == t.head
            and pr["baseRefName"] == t.base
            and pr["baseRefOid"] == t.base_commit
            and pr["state"] == "OPEN"
            and pr["headRepository"]["nameWithOwner"].lower() == t.repository.lower(),
            "CI PR/head/base drift",
        )
        pages = json.loads(
            run(
                "gh",
                "api",
                f"repos/{t.repository}/commits/{t.head}/check-runs?per_page=100&filter=all",
                "--paginate",
                "--slurp",
            )
        )
        rows = [row for page in pages for row in page["check_runs"]]
        require(len(rows) <= 1000, "too many check runs")
        return {"pr": pr, "check_runs": rows}


def classify(rows: list[dict], head: str) -> str:
    pending = False
    for name in EXPECTED_CHECKS:
        matches = [r for r in rows if r["name"] == name]
        require(len(matches) <= 1, "ambiguous duplicate CI check")
        if not matches:
            pending = True
            continue
        row = matches[0]
        require(row["head_sha"] == head, "wrong CI checked head")
        require(row["app"]["slug"] == "github-actions", "unexpected CI producer")
        require(row["status"] in ("queued", "in_progress", "completed"), "unknown CI status")
        if row["status"] != "completed":
            pending = True
        elif row["conclusion"] != "success":
            return "fail"
    return "pending" if pending else "pass"


def wait_ci(
    target: CITarget,
    task_id: str,
    control: Path,
    evidence: Path,
    *,
    timeout=180,
    interval=2,
    expected_revision=None,
) -> str:
    target.validate()
    require(0 <= timeout <= 600 and 0 < interval <= 10, "CI wait bounds")
    with StateStore(control, evidence) as store:
        if expected_revision is not None:
            require(store.state["revision"] == expected_revision, "stale CI dispatch")
        task = store.state["tasks"][task_id]
        binding = control / ("ci-" + task_id + ".json")
        expected = encoded(target.__dict__)
        if binding.exists():
            require(
                not binding.is_symlink() and binding.read_bytes() == expected, "CI target drift"
            )
        else:
            require(task["status"] == "ready", "missing established CI binding")
            atomic_write(binding, expected)
        if task["status"] == "ready":
            intent = store.begin(task_id, "ci", f"pr:{target.pr}", target.head, target.base_commit)
            require(intent is not None, "CI budget exhausted")
        else:
            require(task["status"] in ("running", "done", "failed"), "CI not resumable")
            intent = task["intent"]
        task = store.state["tasks"][task_id]
        intent = cast(dict, intent)
        require(
            (intent["kind"], intent["key"], intent["head"], intent["base"])
            == ("ci", f"pr:{target.pr}", target.head, target.base_commit),
            "CI intent mismatch",
        )
        if task["status"] in ("done", "failed"):
            return task["status"]
        saved = control / f"results/{task_id}-{task['attempt']}.json"
        if saved.exists():
            store.recover_result(task_id)
            return store.state["tasks"][task_id]["status"]
        observer = CIObserver(target)
        deadline = time.monotonic() + timeout
        while True:
            observation = observer.observe()
            outcome = classify(observation["check_runs"], target.head)
            authority(store)
            if outcome != "pending":
                # Recheck the PR binding immediately before producing completion evidence.
                confirmation = observer.observe()
                require(classify(confirmation["check_runs"], target.head) == outcome, "CI changed")
                authority(store)
                payload = encoded(confirmation)
                digest = hashlib.sha256(payload).hexdigest()
                relative = f"ci-{task_id}-{task['attempt']}-{digest}.json"
                path = evidence / relative
                require(not path.is_symlink(), "symlink CI evidence")
                if path.exists():
                    require(path.read_bytes() == payload, "conflicting CI observation evidence")
                else:
                    atomic_write(path, payload)
                report = dict(
                    task_id=task_id,
                    attempt=task["attempt"],
                    result=outcome,
                    commit=target.head,
                    evidence=[dict(path=relative, sha256=digest)],
                    notes="Host observed exact-head GitHub Actions checks; no merge authority.",
                )
                store.finish(
                    json.dumps(report),
                    ExecutionReceipt(
                        task_id,
                        task["attempt"],
                        intent["id"],
                        target.head,
                        0 if outcome == "pass" else 1,
                        intent["key"],
                    ),
                )
                return store.state["tasks"][task_id]["status"]
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return "timeout"  # Preserve the running intent. No extra attempt on resume.
            time.sleep(min(interval, remaining))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    result = wait_ci(
        CITarget(**decode(args.target.read_text())),
        args.task,
        args.control.resolve(),
        args.evidence.resolve(),
        timeout=args.timeout,
    )
    print(json.dumps({"status": result}))


if __name__ == "__main__":
    main()
