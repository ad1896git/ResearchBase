"""One sandboxed worker attempt with host-bound completion and conservative restart."""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import cast

from scripts.pipeline_executor import run
from scripts.pipeline_faults import classify
from scripts.pipeline_protocol import (
    ID,
    ExecutionReceipt,
    StateStore,
    atomic_write,
    commit,
    decode,
    encoded,
    require,
    text,
)
from scripts.pipeline_sessions import SCRIPTS, run_session


@dataclass(frozen=True)
class WorkerJob:
    task_id: str
    key: str
    checkout: str
    prompt_file: str
    head: str
    base: str

    def validate(self, control: Path, evidence: Path):
        require(ID.fullmatch(self.task_id) is not None, "invalid worker task")
        text(self.key, 256)
        commit(self.head)
        commit(self.base)
        checkout = Path(self.checkout)
        require(checkout.is_absolute() and checkout.is_dir(), "invalid worker checkout")
        checkout = checkout.resolve()
        require(evidence.resolve() == checkout, "worker evidence root must be checkout")
        require(
            not control.resolve().is_relative_to(checkout)
            and not checkout.is_relative_to(control.resolve()),
            "worker/control overlap",
        )
        # A sandbox clone only: never grant a worker write access to ResearchBase source.
        remote = (
            run("git", "remote", "get-url", "origin", cwd=checkout).lower().removesuffix(".git")
        )
        require(remote.startswith("https://github.com/"), "explicit sandbox HTTPS origin required")
        require(remote != "https://github.com/ad1896git/researchbase", "main repo worker denied")
        require(Path(self.prompt_file).is_absolute(), "absolute worker prompt required")


def authority(store: StateStore):
    store.lock.check()
    path = store.directory / "state.json"
    require(not path.is_symlink(), "symlink worker state")
    require(decode(path.read_text()) == store.state, "worker authoritative state changed")
    marker = store.directory / "initialized"
    require(marker.is_file() and not marker.is_symlink(), "worker initialization lost")


def worker_once(
    job: WorkerJob,
    control: Path,
    evidence: Path,
    *,
    timeout=180,
    expected_revision=None,
):
    job.validate(control, evidence)
    checkout = Path(job.checkout).resolve()
    with StateStore(control, evidence) as store:
        if expected_revision is not None:
            require(store.state["revision"] == expected_revision, "stale worker dispatch")
        require(job.task_id in store.state["tasks"], "unknown worker task")
        task = store.state["tasks"][job.task_id]
        prompt = Path(job.prompt_file).read_text()
        binding = encoded({"job": asdict(job), "prompt": prompt})
        bindings = control / "workers"
        bindings.mkdir(exist_ok=True)
        bound = bindings / (job.task_id + ".json")
        if bound.exists():
            require(not bound.is_symlink() and bound.read_bytes() == binding, "worker job changed")
        else:
            require(task["status"] == "ready", "missing established worker binding")
            atomic_write(bound, binding)
        if task["status"] in ("ready", "retry_wait"):
            require(task["attempt"] < 2, "worker attempt limit (2)")
            if task["status"] == "retry_wait":
                require(int(time.time()) >= task["retry_at"], "worker retry not due")
            require(run("git", "rev-parse", "HEAD", cwd=checkout) == job.head, "worker start drift")
            intent = store.begin(
                job.task_id, "worker", job.key, job.head, job.base, now=int(time.time())
            )
            require(intent is not None, "worker budget exhausted")
            fresh = True
        else:
            require(task["status"] in ("running", "done", "failed"), "worker not resumable")
            intent = task["intent"]
            fresh = False
        task = store.state["tasks"][job.task_id]
        intent = cast(dict, intent)
        require(
            (intent["kind"], intent["key"], intent["head"], intent["base"])
            == ("worker", job.key, job.head, job.base),
            "worker intent mismatch",
        )
        if task["status"] in ("done", "failed"):
            return task["status"]
        output = control / "executions" / f"{job.task_id}-{task['attempt']}"
        output.parent.mkdir(exist_ok=True)
        host = output / "host.json"
        if fresh:
            authority(store)
            instruction = (
                "Bounded engineering sandbox worker. No network writes, remote git operations, "
                "scientific execution, labels, merges, or edits to governing harness files. "
                "Operate only inside your checkout. Return the result schema, with task_id="
                f"{job.task_id}, attempt={task['attempt']}. "
                "Evidence paths are relative to checkout. "
                "compute actual SHA256 digests. commit must equal actual git HEAD when done.\n"
                + prompt
            )
            terminal = run_session(
                checkout,
                output,
                instruction,
                SCRIPTS / "pipeline_result.schema.json",
                writable=True,
                timeout=timeout,
            )
            require(terminal["descendants_stopped"], "worker descendants still live")
            authority(store)
            receipt = ExecutionReceipt(
                job.task_id,
                task["attempt"],
                intent["id"],
                run("git", "rev-parse", "HEAD", cwd=checkout),
                124 if terminal["timed_out"] else terminal["exit_code"],
                job.key,
            )
            atomic_write(host, encoded({"receipt": asdict(receipt), "terminal": terminal}))
        else:
            # No host receipt means the old child may still be live. Never relaunch it.
            if not host.exists():
                result = control / f"results/{job.task_id}-{task['attempt']}.json"
                require(result.is_file(), "unknown live worker outcome; operator reconciliation")
                store.recover_result(job.task_id)
                return store.state["tasks"][job.task_id]["status"]
            require(not host.is_symlink(), "symlink host receipt")
            saved = decode(host.read_text())
            require(saved["terminal"]["descendants_stopped"] is True, "unjoined worker")
            receipt = ExecutionReceipt(**saved["receipt"])
        authority(store)
        answer = output / "answer.json"
        saved = decode(host.read_text())
        result = control / f"results/{job.task_id}-{task['attempt']}.json"
        if result.is_file():
            store.recover_result(job.task_id)
            return store.state["tasks"][job.task_id]["status"]
        fault = classify(output, saved["terminal"])
        if (
            receipt.commit == intent["head"]
            and fault is not None
            and (not answer.exists() and not answer.is_symlink())
        ):
            store.worker_fault(
                job.task_id, int(time.time()) + (900 if fault == "quota" else 60), receipt, fault
            )
            return store.state["tasks"][job.task_id]["status"]
        require(
            answer.is_file() and not answer.is_symlink(),
            "worker report absent or unsafe; systemic/unclassified failure; host receipt retained",
        )
        store.finish(answer.read_text(), receipt)
        return store.state["tasks"][job.task_id]["status"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    job = WorkerJob(**decode(args.job.read_text()))
    print(
        json.dumps(
            {
                "status": worker_once(
                    job,
                    args.control.resolve(),
                    args.evidence.resolve(),
                    timeout=args.timeout,
                )
            }
        )
    )


if __name__ == "__main__":
    main()
