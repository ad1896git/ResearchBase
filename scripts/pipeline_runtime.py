"""Explicit one-step dispatch, never a replacement for the production loop."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.pipeline_ci import CITarget, wait_ci
from scripts.pipeline_commander import command_once
from scripts.pipeline_protocol import decode, exact, require
from scripts.pipeline_worker import WorkerJob, worker_once


def dispatch(value: dict, jobs: dict, control: Path, evidence: Path, *, timeout=180) -> dict:
    if value["action"] != "dispatch":
        return {"decision": value, "status": value["action"]}
    task_id = value["task_id"]
    require(task_id in jobs, "no configured executor for selected task")
    job = jobs[task_id]
    exact(job, ("kind", "config"))
    if job["kind"] == "worker":
        config = WorkerJob(**job["config"])
        require(config.task_id == task_id, "worker job/task mismatch")
        status = worker_once(
            config,
            control,
            evidence,
            timeout=timeout,
            expected_revision=value["revision"],
        )
    elif job["kind"] == "ci":
        status = wait_ci(
            CITarget(**job["config"]),
            task_id,
            control,
            evidence,
            timeout=timeout,
            expected_revision=value["revision"],
        )
    else:
        raise ValueError("unsupported executor; no shell, publish or merge dispatch")
    return {"decision": value, "status": status}


def step(control: Path, evidence: Path, checkout: Path, jobs: dict, *, timeout=180) -> dict:
    value = command_once(control, evidence, checkout, timeout=timeout)
    return dispatch(value, jobs, control, evidence, timeout=timeout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--jobs", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    print(
        json.dumps(
            step(
                args.control.resolve(),
                args.evidence.resolve(),
                args.checkout.resolve(),
                decode(args.jobs.read_text()),
                timeout=args.timeout,
            )
        )
    )


if __name__ == "__main__":
    main()
