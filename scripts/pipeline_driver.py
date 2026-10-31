"""Owned engineering cycle: never leave runnable work behind on a normal exit."""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import threading
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path

from scripts.pipeline_ci import CITarget, wait_ci
from scripts.pipeline_commander import command_once
from scripts.pipeline_protocol import StateStore, atomic_write, decode, encoded, exact, require
from scripts.pipeline_runtime import dispatch
from scripts.pipeline_safety import ProcessLock
from scripts.pipeline_sessions import MAX_SESSION_TIMEOUT, WORKER_TIMEOUTS

TERMINAL = frozenset(("done", "blocked", "budget_exhausted"))


@dataclass(frozen=True)
class Policy:
    round_budget: int = 5
    session_timeout: int = 180
    design_timeout: int = WORKER_TIMEOUTS["design"]
    implementation_timeout: int = WORKER_TIMEOUTS["implementation"]
    review_timeout: int = WORKER_TIMEOUTS["review"]
    ci_timeout: float = 9000
    query_timeout: float = 10
    poll_interval: float = 2
    heartbeat_interval: float = 5
    retry_delay: int = 60
    max_ci_timeouts: int = 3

    def validate(self):
        require(type(self.round_budget) is int and 1 <= self.round_budget <= 40, "round budget")
        require(1 <= self.session_timeout <= MAX_SESSION_TIMEOUT, "session timeout")
        for value in (self.design_timeout, self.implementation_timeout, self.review_timeout):
            require(
                type(value) is int and 1 <= value <= MAX_SESSION_TIMEOUT, "worker phase timeout"
            )
        require(0 < self.ci_timeout <= 86400, "CI total timeout")
        require(0 < self.query_timeout <= 120, "CI query timeout")
        require(0 < self.poll_interval <= 10, "CI poll interval")
        require(0.05 <= self.heartbeat_interval <= 60, "heartbeat interval")
        require(type(self.retry_delay) is int and 1 <= self.retry_delay <= 3600, "retry delay")
        require(type(self.max_ci_timeouts) is int and 1 <= self.max_ci_timeouts <= 10, "CI retries")


class Heartbeat:
    """Independent heartbeat also covers bounded subprocess waits; errors are not ignored."""

    def __init__(self, control: Path, interval: float):
        self.control, self.interval = control, interval
        self.phase = {"phase": "starting", "task_id": ""}
        self.stop = threading.Event()
        self.error: Exception | None = None
        self.thread = threading.Thread(target=self._run, daemon=True)

    def pulse(self):
        self.check()
        payload = encoded(dict(pid=os.getpid(), time=time.time(), **self.phase))
        atomic_write(self.control / "driver-heartbeat.json", payload)
        path = self.control / "driver-heartbeats.jsonl"
        require(not path.is_symlink(), "symlink heartbeat journal")
        with path.open("ab") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())

    def check(self):
        if self.error is not None:
            raise RuntimeError("heartbeat persistence failed") from self.error

    def _run(self):
        try:
            while not self.stop.wait(self.interval):
                self.pulse()
        except Exception as exc:
            self.error = exc

    def __enter__(self):
        self.pulse()
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.stop.set()
        self.thread.join()


def human_gate_wait(tasks):
    """Only dependency chains ending exclusively at a human merge gate can park."""
    if any(t["status"] in ("blocked", "failed", "budget_exhausted") for t in tasks.values()):
        return False
    waiting = {n for n, t in tasks.items() if t["status"] == "awaiting_merge"}
    while True:
        added = {
            n
            for n, t in tasks.items()
            if t["status"] == "ready"
            and t["needs"]
            and any(dep in waiting for dep in t["needs"])
            and all(tasks[dep]["status"] == "done" or dep in waiting for dep in t["needs"])
        }
        if added <= waiting:
            break
        waiting |= added
    unfinished = {n for n, t in tasks.items() if t["status"] not in TERMINAL}
    return bool(waiting) and unfinished <= waiting


class Driver:
    def __init__(
        self,
        control: Path,
        evidence: Path,
        checkout: Path,
        jobs: dict,
        policy: Policy,
        *,
        park_human_gates=False,
    ):
        self.control, self.evidence, self.checkout = control, evidence, checkout
        self.jobs, self.policy = jobs, policy
        self.park_human_gates = park_human_gates
        self.events = control / "driver-events"
        self.events.mkdir(exist_ok=True)
        require(not self.events.is_symlink(), "symlink driver events")
        self.sequence = len(list(self.events.glob("*.json")))

    def event(self, kind, **fields):
        self.sequence += 1
        path = self.events / f"{self.sequence:08d}.json"
        require(not path.exists() and not path.is_symlink(), "event sequence conflict")
        atomic_write(path, encoded(dict(kind=kind, time=time.time(), **fields)))

    def worker_timeout(self, name):
        stage = self.jobs[name].get("config", {}).get("stage", "implementation")
        limits = {
            "design": self.policy.design_timeout,
            "implementation": self.policy.implementation_timeout,
            "review": self.policy.review_timeout,
        }
        require(stage in limits, "unknown worker stage")
        return limits[stage]

    def snapshot(self):
        with StateStore(self.control, self.evidence) as store:
            return store.state

    def block(self, reason):
        reason = reason[:4000]
        with StateStore(self.control, self.evidence) as store:
            for name in list(store.state["tasks"]):
                if store.state["tasks"][name]["status"] not in TERMINAL:
                    store.block(name, reason)
        self.event("blocked", reason=reason)
        self.notify("driver", "blocked", reason)

    def notify(self, task_id, key, reason):
        folder = self.control / "notifications"
        folder.mkdir(exist_ok=True)
        require(not folder.is_symlink(), "symlink notifications")
        path = folder / f"{task_id}-{key}.json"
        value = dict(task_id=task_id, status=key, reason=reason)
        if path.exists():
            require(
                not path.is_symlink() and decode(path.read_text()) == value,
                "notification binding drift",
            )
        else:
            atomic_write(path, encoded(value))
            print(json.dumps(value), file=sys.stderr, flush=True)

    def idle_until(self, timestamp, heartbeat):
        while time.time() < timestamp:
            heartbeat.check()
            time.sleep(min(self.policy.heartbeat_interval, max(0, timestamp - time.time())))

    def wait_for_ci(self, name, heartbeat):
        job = self.jobs[name]
        exact(job, ("kind", "config"))
        require(job["kind"] == "ci", "wait executor must be CI")
        target = CITarget(**job["config"])
        with StateStore(self.control, self.evidence) as store:
            task = store.state["tasks"][name]
            if task["status"] == "running":
                store.recover_ci_pause(name)
            task = store.state["tasks"][name]
        if task["status"] == "retry_wait":
            require(task["reason"] == "ci_timeout", "unsupported retry cause")
            self.notify(
                name, str(task["retry_at"]), "CI timeout: retry_wait; same intent will resume"
            )
            count = len(list(self.control.glob(f"ci-retry-{name}-{task['attempt']}-*.json")))
            if count >= self.policy.max_ci_timeouts:
                self.block("CI timeout retry limit reached; operator reconciliation required")
                return
            heartbeat.phase = dict(phase="retry_wait", task_id=name)
            self.idle_until(task["retry_at"], heartbeat)
            with StateStore(self.control, self.evidence) as store:
                store.resume_ci(name, now=int(time.time()))
        heartbeat.phase = dict(phase="ci_wait", task_id=name)
        heartbeat.pulse()
        last = None

        def observed(outcome):
            nonlocal last
            heartbeat.check()
            if outcome != last:
                self.event("ci_observed", task_id=name, outcome=outcome)
                last = outcome

        with StateStore(self.control, self.evidence) as store:
            revision = store.state["revision"]
        status = wait_ci(
            target,
            name,
            self.control,
            self.evidence,
            timeout=self.policy.ci_timeout,
            query_timeout=self.policy.query_timeout,
            interval=self.policy.poll_interval,
            expected_revision=revision,
            on_observation=observed,
        )
        self.event("ci_returned", task_id=name, status=status)
        if status == "timeout":
            with StateStore(self.control, self.evidence) as store:
                # Even a validation-query timeout has a durable read-only wait claim.
                if store.state["tasks"][name]["status"] == "ready":
                    # Validation itself may have exhausted its query budget before
                    # the waiter could bind the target. Persist it before the claim;
                    # a restart must never see an unbound running/paused CI intent.
                    binding = self.control / ("ci-" + name + ".json")
                    expected = encoded(target.__dict__)
                    require(not binding.is_symlink(), "symlink CI target binding")
                    if binding.exists():
                        require(binding.read_bytes() == expected, "CI target drift")
                    else:
                        atomic_write(binding, expected)
                    store.begin(name, "ci", f"pr:{target.pr}", target.head, target.base_commit)
                store.pause_ci(name, int(time.time()) + self.policy.retry_delay)
                task = store.state["tasks"][name]
            self.notify(
                name, str(task["retry_at"]), "CI timeout: retry_wait; same intent will resume"
            )
            self.event(
                "retry_wait",
                task_id=name,
                retry_at=task["retry_at"],
                intent=task["intent"],
                attempt=task["attempt"],
            )
            count = len(list(self.control.glob(f"ci-retry-{name}-{task['attempt']}-*.json")))
            if count >= self.policy.max_ci_timeouts:
                self.block("CI timeout retry limit reached; operator reconciliation required")
        elif status == "failed":
            self.block("CI failed on the frozen head")
        else:
            require(status == "done", "unknown CI outcome")

    def loop(self, heartbeat):
        while True:
            heartbeat.check()
            state = self.snapshot()
            tasks = state["tasks"]
            if all(t["status"] in TERMINAL for t in tasks.values()):
                for name, task in tasks.items():
                    if task["status"] == "blocked":
                        self.notify(name, "blocked", task["reason"])
                return
            if self.park_human_gates and human_gate_wait(tasks):
                self.event("parked", status="awaiting_merge", revision=state["revision"])
                self.notify("driver", "awaiting_merge", "Human merge required; no runnable work")
                return
            if any(t["status"] == "failed" for t in tasks.values()):
                self.block("failed execution needs operator reconciliation")
                continue
            # A resumed read-only CI is host work, not a new model round or attempt.
            active_ci = [
                n
                for n, t in tasks.items()
                if t["status"] in ("running", "retry_wait") and t["intent"]["kind"] == "ci"
            ]
            if active_ci:
                self.wait_for_ci(active_ci[0], heartbeat)
                continue
            paused_workers = [
                n
                for n, t in tasks.items()
                if t["status"] == "retry_wait" and t["intent"]["kind"] == "worker"
            ]
            with StateStore(self.control, self.evidence) as store:
                eligible_now = store.eligible(int(time.time()))
            if paused_workers and not eligible_now:
                name = paused_workers[0]
                task = tasks[name]
                self.notify(
                    name,
                    f"retry-{task['attempt']}",
                    f"{task['reason']}: retry_wait; next fresh attempt after {task['retry_at']}",
                )
                heartbeat.phase = dict(phase="retry_wait", task_id=name)
                self.idle_until(task["retry_at"], heartbeat)
                # Eligible dispatch below consumes the next attempt, never the wait.
            running = [n for n, t in tasks.items() if t["status"] == "running"]
            if running:
                name = running[0]
                require(self.jobs[name]["kind"] == "worker", "unknown running executor")
                heartbeat.phase = dict(phase="recovery", task_id=name)
                result = dispatch(
                    dict(action="dispatch", task_id=name, revision=state["revision"]),
                    self.jobs,
                    self.control,
                    self.evidence,
                    timeout=self.worker_timeout(name),
                )
                require(
                    result["status"] in ("done", "retry_wait", "blocked"),
                    "worker recovery unsuccessful",
                )
                self.event("recovered", task_id=name, result=result)
                continue
            if state["rounds_used"] >= self.policy.round_budget:
                with StateStore(self.control, self.evidence) as store:
                    for name, task in list(store.state["tasks"].items()):
                        if task["status"] == "ready":
                            store.exhaust(name)
                self.block("non-runnable work at budget limit")
                continue
            heartbeat.phase = dict(phase="commander", task_id="")
            value = command_once(
                self.control,
                self.evidence,
                self.checkout,
                now=int(time.time()),
                timeout=self.policy.session_timeout,
            )
            self.event("decision", decision=value, rounds_used=state["rounds_used"])
            action = value["action"]
            if action == "dispatch":
                name = value["task_id"]
                job = self.jobs[name]
                exact(job, ("kind", "config"))
                if job["kind"] == "ci":
                    require(self.snapshot()["revision"] == value["revision"], "stale CI decision")
                    self.wait_for_ci(name, heartbeat)
                elif job["kind"] == "worker":
                    heartbeat.phase = dict(phase="worker", task_id=name)
                    result = dispatch(
                        value,
                        self.jobs,
                        self.control,
                        self.evidence,
                        timeout=self.worker_timeout(name),
                    )
                    self.event("executed", result=result)
                    require(
                        result["status"] in ("done", "retry_wait", "blocked"), "worker unsuccessful"
                    )
                else:
                    self.block("unsupported executor decision")
            elif action == "wait":
                # Reinspect authoritative eligibility, not an arbitrary model-provided task ID.
                with StateStore(self.control, self.evidence) as store:
                    require(store.state["revision"] == value["revision"], "stale wait decision")
                    names = [
                        n
                        for n in store.eligible(int(time.time()))
                        if n in self.jobs and self.jobs[n]["kind"] == "ci"
                    ]
                if names:
                    self.wait_for_ci(names[0], heartbeat)
                else:
                    self.block("wait has no configured resumable CI; human decision required")
            elif action == "stop":
                self.block("premature stop with unfinished tasks")
            else:
                self.block("unknown commander decision")


@contextmanager
def graceful_stop():
    """SIGTERM/interrupt are reconciled to blocked; SIGKILL/host failure require recovery."""
    saved = {}
    if threading.current_thread() is threading.main_thread():

        def interrupted(signum, frame):
            raise KeyboardInterrupt(f"signal {signum}")

        for sig in (signal.SIGTERM, signal.SIGINT):
            saved[sig] = signal.signal(sig, interrupted)
    try:
        yield
    finally:
        for sig, handler in saved.items():
            signal.signal(sig, handler)


def run_cycle(
    control: Path,
    evidence: Path,
    checkout: Path,
    jobs: dict,
    *,
    policy: Policy | None = None,
    park_human_gates: bool = False,
) -> dict:
    policy = policy or Policy()
    policy.validate()
    require((control / "initialized").is_file(), "explicit established ledger required")
    # Entire lifecycle ownership; task adapters still use their own short state locks.
    with ProcessLock(control / "driver.lock"), graceful_stop():
        driver = Driver(
            control, evidence, checkout, jobs, policy, park_human_gates=park_human_gates
        )
        try:
            fields: dict = dict(
                policy=asdict(policy), jobs=jobs, checkout=str(checkout), evidence=str(evidence)
            )
            if park_human_gates:
                fields["park_human_gates"] = True
            binding = encoded(fields)
            bound = control / "driver-binding.json"
            if bound.exists():
                require(
                    not bound.is_symlink() and bound.read_bytes() == binding, "driver binding drift"
                )
            else:
                atomic_write(bound, binding)
            with Heartbeat(control, policy.heartbeat_interval) as heartbeat:
                driver.loop(heartbeat)
                heartbeat.phase = dict(phase="finished", task_id="")
                heartbeat.pulse()
        except (Exception, KeyboardInterrupt) as exc:
            driver.block(f"driver error: {type(exc).__name__}: {exc}")
        state = driver.snapshot()
        require(
            all(t["status"] in TERMINAL for t in state["tasks"].values())
            or (park_human_gates and human_gate_wait(state["tasks"])),
            "driver must not exit with unfinished tasks",
        )
        status = (
            "done" if all(t["status"] == "done" for t in state["tasks"].values()) else "blocked"
        )
        if any(t["status"] == "budget_exhausted" for t in state["tasks"].values()):
            status = "budget_exhausted"
        if park_human_gates and human_gate_wait(state["tasks"]):
            status = "awaiting_merge"
        driver.event("exit", status=status, rounds_used=state["rounds_used"])
        return dict(status=status, rounds_used=state["rounds_used"], tasks=state["tasks"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("control", "evidence", "checkout", "jobs"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--round-budget", type=int, default=5)
    parser.add_argument("--ci-timeout", type=float, default=9000)
    parser.add_argument("--session-timeout", type=int, default=180)
    parser.add_argument("--retry-delay", type=int, default=60)
    parser.add_argument("--max-ci-timeouts", type=int, default=3)
    args = parser.parse_args()
    result = run_cycle(
        args.control.resolve(),
        args.evidence.resolve(),
        args.checkout.resolve(),
        decode(args.jobs.read_text()),
        policy=Policy(
            round_budget=args.round_budget,
            ci_timeout=args.ci_timeout,
            session_timeout=args.session_timeout,
            retry_delay=args.retry_delay,
            max_ci_timeouts=args.max_ci_timeouts,
        ),
    )
    print(json.dumps(result), flush=True)
    return 0 if result["status"] == "done" else 2


if __name__ == "__main__":
    sys.exit(main())
