"""Opt-in, single-publication executor. Never imports or starts the legacy loop."""

from __future__ import annotations

import argparse
import json
import re
import signal
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import cast

from scripts.pipeline_protocol import (
    Publication,
    StateStore,
    atomic_write,
    commit,
    decode,
    encoded,
    require,
)


def run(*args: str, cwd: Path | None = None) -> str:
    return subprocess.run(
        args, cwd=cwd, check=True, capture_output=True, text=True, timeout=120
    ).stdout.strip()


@dataclass(frozen=True)
class Target:
    repository: str
    base: str
    branch: str
    checkout: str
    head: str
    base_commit: str

    @classmethod
    def load(cls, path: Path) -> Target:
        data = decode(path.read_text())
        require(type(data) is dict and set(data) == set(cls.__dataclass_fields__), "target fields")
        require(all(type(v) is str for v in data.values()), "target values")
        target = cls(**cast(dict[str, str], data))
        target.validate()
        return target

    def validate(self):
        target = self
        require(
            re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", target.repository) is not None,
            "invalid repository",
        )
        require(target.repository.lower() != "ad1896git/researchbase", "main repo denied")
        require(target.branch.startswith("pipeline-test/"), "test branch prefix required")
        for ref in (target.branch, target.base):
            run("git", "check-ref-format", "refs/heads/" + ref)
        require(target.base != target.branch, "base equals branch")
        require(Path(target.checkout).is_absolute(), "absolute checkout required")
        commit(target.head)
        commit(target.base_commit)

    @property
    def url(self) -> str:
        return f"https://github.com/{self.repository}.git"

    @property
    def key(self) -> str:
        return f"{self.repository}:refs/heads/{self.branch}"


class GitHub:
    def __init__(self, target: Target):
        self.target = target

    def prs(self) -> list[dict]:
        t = self.target
        raw = run(
            "gh",
            "pr",
            "list",
            "--repo",
            t.repository,
            "--head",
            t.branch,
            "--state",
            "all",
            "--limit",
            "100",
            "--json",
            "number,headRefName,headRefOid,baseRefName,baseRefOid,isDraft,state,url,headRepository",
        )
        value = json.loads(raw)
        require(type(value) is list, "invalid PR query")
        return value

    def branch_head(self, branch: str) -> str | None:
        raw = run("git", "ls-remote", "--refs", self.target.url, "refs/heads/" + branch)
        if not raw:
            return None
        fields = raw.split()
        require(len(fields) == 2 and fields[1] == "refs/heads/" + branch, "ambiguous ref")
        commit(fields[0])
        return fields[0]

    def validate_pr(self, rows: list[dict]) -> Publication | None:
        require(len(rows) <= 1, "multiple PRs: operator reconciliation required")
        if not rows:
            return None
        row, t = rows[0], self.target
        require(
            row["headRefName"] == t.branch
            and row["headRefOid"] == t.head
            and row["baseRefName"] == t.base
            and row["baseRefOid"] == t.base_commit
            and row["isDraft"] is True
            and row["state"] == "OPEN"
            and row["headRepository"]["nameWithOwner"].lower() == t.repository.lower(),
            "PR binding/state drift",
        )
        return Publication(t.key, t.head, t.base_commit, row["number"])

    def push(self):
        t = self.target
        # An explicit URL avoids a checkout's origin redirecting this write.
        run(
            "git",
            "-c",
            "core.hooksPath=/dev/null",
            "push",
            "--no-verify",
            "--force-with-lease=refs/heads/" + t.branch + ":",
            t.url,
            t.head + ":refs/heads/" + t.branch,
            cwd=Path(t.checkout),
        )

    def create(self):
        t = self.target
        run(
            "gh",
            "pr",
            "create",
            "--repo",
            t.repository,
            "--base",
            t.base,
            "--head",
            t.branch,
            "--draft",
            "--title",
            "Pipeline recovery rehearsal",
            "--body",
            "Sandbox recovery evidence only. Do not merge.",
        )


def checkpoint(name: str, pause_after: str | None):
    if pause_after == name:
        print(json.dumps({"checkpoint": name}), flush=True)
        signal.raise_signal(signal.SIGSTOP)


def publish(target: Target, control: Path, evidence: Path, *, initialize=False, pause_after=None):
    target.validate()
    remote = GitHub(target)
    with StateStore(control, evidence, create=initialize) as store:
        binding = control / "executor-target.json"
        expected = encoded(asdict(target))
        if binding.exists():
            require(not binding.is_symlink() and binding.read_bytes() == expected, "target drift")
        else:
            require(not store.state["tasks"], "missing established target binding")
            atomic_write(binding, expected)
        if "publish" not in store.state["tasks"]:
            store.add("publish")
        task = store.state["tasks"]["publish"]
        if task["status"] == "ready":
            intent = store.begin("publish", "publish", target.key, target.head, target.base_commit)
            require(intent is not None, "publication budget exhausted")
        else:
            require(task["status"] in ("running", "done"), "publication not resumable")
        intent = store.state["tasks"]["publish"]["intent"]
        require(
            (intent["kind"], intent["key"], intent["head"], intent["base"])
            == ("publish", target.key, target.head, target.base_commit),
            "publication intent mismatch",
        )
        require(remote.branch_head(target.base) == target.base_commit, "base moved")
        rows = remote.prs()  # Always query ALL states before any write, including restart.
        observed = remote.validate_pr(rows)
        branch = remote.branch_head(target.branch)
        require(branch in (None, target.head), "remote branch drift")
        if observed is not None:
            require(branch == target.head, "PR branch missing")
        else:
            require(task["status"] != "done", "completed PR disappeared")
            marker = control / "create-requested.json"
            require(not marker.exists(), "unknown create outcome; query again or ask operator")
            if branch is None:
                require(
                    run("git", "rev-parse", target.head, cwd=Path(target.checkout)) == target.head,
                    "local commit missing",
                )
                run(
                    "git",
                    "merge-base",
                    "--is-ancestor",
                    target.base_commit,
                    target.head,
                    cwd=Path(target.checkout),
                )
                remote.push()
            require(remote.branch_head(target.branch) == target.head, "push not observed")
            checkpoint("after-push", pause_after)
            # Requery immediately before creation; a failed request is never blindly retried.
            observed = remote.validate_pr(remote.prs())
            if observed is None:
                atomic_write(marker, encoded({"intent": store.state["tasks"]["publish"]["intent"]}))
                remote.create()
                checkpoint("after-pr", pause_after)
                observed = remote.validate_pr(remote.prs())
                require(observed is not None, "created PR not yet observable; restart query")
        if task["status"] != "done":
            store.reconcile_publication("publish", observed)
        return cast(Publication, observed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--initialize", action="store_true")
    parser.add_argument("--pause-after", choices=("after-push", "after-pr"))
    args = parser.parse_args()
    result = publish(
        Target.load(args.config),
        args.control,
        args.evidence,
        initialize=args.initialize,
        pause_after=args.pause_after,
    )
    print(json.dumps(asdict(result)))


if __name__ == "__main__":
    main()
