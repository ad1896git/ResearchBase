"""Bounded read-only CI polling against an exact sandbox PR/head/base binding."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
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

    def validate(self, *, deadline: float | None = None, query_timeout: float = 10):
        integer(self.pr, 1)
        Target(
            self.repository,
            self.base,
            self.branch,
            str(Path.cwd()),
            self.head,
            self.base_commit,
        ).validate(deadline=deadline, query_timeout=query_timeout)


class CIObserver:
    def __init__(self, target: CITarget):
        self.target = target

    def observe(self, *, deadline: float, query_timeout: float) -> dict:
        def query(*args: str):
            result = run(*args, timeout=remaining(deadline, query_timeout))
            remaining(deadline, query_timeout)  # Never accept a response that arrived too late.
            return result

        t = self.target
        pr = json.loads(
            query(
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
            query(
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


def remaining(deadline: float, query_timeout: float) -> float:
    budget = deadline - time.monotonic()
    if budget <= 0:
        raise TimeoutError("CI total deadline exhausted")
    return min(query_timeout, budget)


def wait_ci(
    target: CITarget,
    task_id: str,
    control: Path,
    evidence: Path,
    *,
    timeout: float = 180,
    query_timeout: float = 10,
    interval: float = 2,
    expected_revision=None,
    on_observation=None,
) -> str:
    require(0 <= timeout <= 86400 and 0 < interval <= 10, "CI wait bounds")
    require(0 < query_timeout <= 120, "CI query timeout bounds")
    deadline = time.monotonic() + timeout
    try:
        remaining(deadline, query_timeout)
        return _wait_ci_until(
            target,
            task_id,
            control,
            evidence,
            deadline=deadline,
            query_timeout=query_timeout,
            interval=interval,
            expected_revision=expected_revision,
            on_observation=on_observation,
        )
    except (TimeoutError, subprocess.TimeoutExpired):
        # Queries, validation, sleep and confirmation share one absolute budget.
        # Keep any established intent; timeout never becomes completion or a new attempt.
        return "timeout"


def _wait_ci_until(
    target: CITarget,
    task_id: str,
    control: Path,
    evidence: Path,
    *,
    deadline: float,
    query_timeout: float,
    interval: float = 2,
    expected_revision=None,
    on_observation=None,
) -> str:
    target.validate(deadline=deadline, query_timeout=query_timeout)
    remaining(deadline, query_timeout)
    with StateStore(control, evidence) as store:
        remaining(deadline, query_timeout)
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
            remaining(deadline, query_timeout)
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
            remaining(deadline, query_timeout)
            return task["status"]
        saved = control / f"results/{task_id}-{task['attempt']}.json"
        if saved.exists():
            remaining(deadline, query_timeout)
            store.recover_result(task_id)
            return store.state["tasks"][task_id]["status"]
        observer = CIObserver(target)
        while True:
            remaining(deadline, query_timeout)
            observation = observer.observe(deadline=deadline, query_timeout=query_timeout)
            remaining(deadline, query_timeout)
            outcome = classify(observation["check_runs"], target.head)
            if on_observation is not None:
                on_observation(outcome)
            authority(store)
            if outcome != "pending":
                # Recheck the PR binding immediately before producing completion evidence.
                remaining(deadline, query_timeout)
                confirmation = observer.observe(deadline=deadline, query_timeout=query_timeout)
                remaining(deadline, query_timeout)
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
                remaining(deadline, query_timeout)
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
            time.sleep(remaining(deadline, interval))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--query-timeout", type=float, default=10)
    args = parser.parse_args()
    result = wait_ci(
        CITarget(**decode(args.target.read_text())),
        args.task,
        args.control.resolve(),
        args.evidence.resolve(),
        timeout=args.timeout,
        query_timeout=args.query_timeout,
    )
    print(json.dumps({"status": result}))


if __name__ == "__main__":
    main()
