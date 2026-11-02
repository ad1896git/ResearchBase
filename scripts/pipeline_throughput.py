"""Opt-in bounded timer ticks. Model children never own the global wakeup lease."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import cast

from scripts.pipeline_admission import admit, completion, immutable, prepare_stage, sources
from scripts.pipeline_candidate import derive_candidate
from scripts.pipeline_capability import checked_file, validate_capability
from scripts.pipeline_ci import PublishedCITarget, poll_ci
from scripts.pipeline_executor import run
from scripts.pipeline_pg import execute as execute_pg
from scripts.pipeline_pg import isolated_environment, passed_cases, validate_environment
from scripts.pipeline_protocol import (
    ExecutionReceipt,
    StateStore,
    atomic_write,
    decode,
    encoded,
    exact,
    require,
)
from scripts.pipeline_safety import LockBusy, ProcessLock, real_directory
from scripts.pipeline_sessions import WORKER_TIMEOUTS
from scripts.pipeline_worker import WorkerJob, worker_once


def validate_policy(policy):
    exact(
        policy,
        (
            "version",
            "root",
            "worktrees",
            "source_checkout",
            "repository",
            "base_ref",
            "authorization",
            "index",
            "implementation_slots",
            "review_slots",
            "pg_slots",
            "pg_environment",
        ),
    )
    require(policy["version"] == 1, "throughput version")
    require(
        (policy["implementation_slots"], policy["review_slots"], policy["pg_slots"]) == (2, 1, 1),
        "closed resource budget requires 2 implementation/1 review/1 PG",
    )
    for name in ("root", "worktrees", "source_checkout"):
        p = Path(policy[name])
        require(p.is_absolute() and p.resolve() == p and not p.is_symlink(), "scheduler path")
    root, work = Path(policy["root"]), Path(policy["worktrees"])
    require(
        not root.is_relative_to(work) and not work.is_relative_to(root), "control/worktree overlap"
    )
    sources(policy)
    validate_environment(policy["pg_environment"])


def progress(folder, stage, status, **fields):
    atomic_write(folder / "progress.json", encoded(dict(stage=stage, status=status, **fields)))


def policy_revision(root, policy):
    """Owner changes frozen evidence references, never active packet bytes."""
    immutable(
        root / "policy.json",
        {k: v for k, v in policy.items() if k not in ("authorization", "index")},
    )
    revisions = root / "policy-revisions"
    real_directory(revisions)
    sha = hashlib.sha256(encoded(policy)).hexdigest()
    pointer = root / "policy-revision.json"
    previous = decode(pointer.read_text())["sha256"] if pointer.exists() else None
    if previous == sha:
        return
    path = revisions / (sha + ".json")
    immutable(path, dict(policy=policy, parent=previous))
    atomic_write(pointer, encoded(dict(sha256=sha)))


def slot_paths(root, stage):
    kind = "pg" if stage == "pg" else "review" if stage == "review" else "implementation"
    count = 2 if kind == "implementation" else 1
    return [root / "resources" / f"{kind}-{n}.lock" for n in range(count)]


def quarantine(root, value):
    reasons = root / "quarantine-reasons"
    real_directory(reasons)
    sha = hashlib.sha256(encoded(value)).hexdigest()
    immutable(reasons / (sha + ".json"), value)
    atomic_write(root / "quarantine.json", encoded(dict(reasons=str(reasons))))


def audit_unjoined(policy, entries):
    """A free kernel lock alone does not prove orphan descendants have stopped."""
    root = Path(policy["root"])
    controls = [Path(e["control"]) for e in entries]
    controls += [p.parent for p in (root / "generations").glob("*/*/ledger/state.json")]
    for control in controls:
        lease = ProcessLock(control / "driver.lock")
        if not lease.acquire():
            continue
        try:
            state = decode((control / "state.json").read_text())
            for name, task in state["tasks"].items():
                intent = task["intent"]
                if (
                    intent is None
                    or intent["kind"] not in ("worker", "verify")
                    or task["status"] not in ("running", "blocked", "failed")
                ):
                    continue
                output = control / "executions" / f"{name}-{task['attempt']}"
                joined = []
                if (output / "terminal.json").is_file():
                    joined.append(
                        decode((output / "terminal.json").read_text())["descendants_stopped"]
                    )
                if (output / "host.json").is_file():
                    joined.append(
                        decode((output / "host.json").read_text())["terminal"][
                            "descendants_stopped"
                        ]
                    )
                if (control / "pg-terminal.json").is_file():
                    joined.append(
                        decode((control / "pg-terminal.json").read_text())["descendants_stopped"]
                    )
                if not joined or not all(v is True for v in joined):
                    quarantine(
                        root,
                        dict(
                            control=str(control),
                            task=name,
                            reason="unowned executor has unproven descendant termination",
                        ),
                    )
        except Exception as exc:
            quarantine(
                root, dict(control=str(control), reason=f"unreadable ownership evidence: {exc}")
            )
        finally:
            lease.close()


def launch(policy, folder, packet, stage, *, legacy=None):
    """Reserve kernel leases, persist send intent, transfer fds to one child."""
    root = Path(policy["root"])
    if stage == "pg" and not policy["pg_environment"]:
        return "held: PostgreSQL profile/four pins missing"
    if (root / "quarantine.json").exists():
        return "held: unresolved child resources"
    if legacy is None:
        row, checkout, template = prepare_stage(policy, folder, packet, stage)
        task_name = "work"
    else:
        row, checkout, template, task_name = legacy
    control = row / "ledger" if legacy is None else Path(row)
    driver = ProcessLock(control / "driver.lock")
    if not driver.acquire():
        return "running"
    resource = None
    try:
        for path in slot_paths(root, stage):
            candidate = ProcessLock(path)
            if candidate.acquire():
                resource = candidate
                break
        if resource is None:
            return "capacity_wait"
        with StateStore(control, checkout) as store:
            task = store.state["tasks"][task_name]
            if task["status"] in ("done", "blocked", "failed", "budget_exhausted"):
                terminal_status = task["status"]
            else:
                terminal_status = None
            if terminal_status is not None:
                attempt = task["attempt"]
        if terminal_status is not None:
            if terminal_status == "done" and legacy is None and stage == "implementation":
                job = WorkerJob(**decode((row / "job.json").read_text()))
                derive_candidate(job, control)
            return terminal_status
        with StateStore(control, checkout) as store:
            task = store.state["tasks"][task_name]
            if task["status"] == "retry_wait" and task["retry_at"] > time.time():
                return "retry_wait"
            journal = control / f"throughput-launch-{task_name}.json"
            if journal.exists():
                # The kernel driver lease was free. An incomplete host launch may
                # still have unjoined model descendants: quarantine, never retry it.
                if (
                    task["status"] == "running"
                    and (
                        control / "executions" / f"{task_name}-{task['attempt']}" / "host.json"
                    ).is_file()
                ):
                    pass  # worker_once can read-only reconcile this exact attempt.
                elif task["status"] == "retry_wait":
                    pass  # terminated retry receipt is validated by StateStore/worker.
                else:
                    quarantine(
                        root,
                        dict(control=str(control), task=task_name, reason="unknown launch outcome"),
                    )
                    store.block(
                        task_name, "unknown throughput child outcome; resources quarantined"
                    )
                    return "blocked"
            attempt = task["attempt"] + (task["status"] in ("ready", "retry_wait"))
        if legacy is None:
            command = dict(
                kind=stage,
                control=str(control),
                evidence=str(checkout),
                job=decode((row / "job.json").read_text()),
                pg_argv=template["pg_argv"],
            )
        else:
            command = dict(
                kind=stage, control=str(control), evidence=str(checkout), job=template, pg_argv=[]
            )
        command["resource_root"] = str(root)
        command["pg_environment"] = policy["pg_environment"]
        command_file = control / f"throughput-command-{task_name}-{attempt}.json"
        immutable(command_file, command)
        atomic_write(
            control / f"throughput-launch-{task_name}.json",
            encoded(
                dict(
                    command=str(command_file),
                    attempt=attempt,
                    leases=[str(driver.path), str(resource.path)],
                )
            ),
        )
        require(driver.fd is not None and resource.fd is not None, "resource lease lost")
        log = control / f"throughput-child-{task_name}-{attempt}.log"
        with log.open("ab") as output:
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "scripts.pipeline_throughput",
                    "--command",
                    str(command_file),
                    "--lease",
                    f"{driver.fd}:{driver.path}",
                    "--lease",
                    f"{resource.fd}:{resource.path}",
                ],
                cwd=Path(__file__).resolve().parent.parent,
                pass_fds=(cast(int, driver.fd), cast(int, resource.fd)),
                start_new_session=True,
                stdout=output,
                stderr=subprocess.STDOUT,
            )
        immutable(
            control / f"throughput-process-{task_name}-{attempt}.json",
            dict(pid=process.pid, command=str(command_file)),
        )
        return "running"
    finally:
        # Child inherited the same open-file-description locks; closing only this
        # parent's descriptors cannot free them while its child remains alive.
        driver.close()
        if resource is not None:
            resource.close()


def run_command(path, leases):
    """One bounded host executor, never a commander or a network-write adapter."""
    owned = []
    for value in leases:
        raw, name = value.split(":", 1)
        fd = int(raw)
        held, named = os.fstat(fd), Path(name).lstat()
        require(
            (held.st_dev, held.st_ino) == (named.st_dev, named.st_ino) and held.st_nlink == 1,
            "inherited lease changed",
        )
        owned.append(fd)
    require(len(owned) == 2, "driver and resource leases required")
    command = decode(path.read_text())
    control, evidence = Path(command["control"]), Path(command["evidence"])
    job = command["job"]
    try:
        if command["kind"] in ("implementation", "review", "design"):
            worker_job = WorkerJob(**job)
            result = worker_once(
                worker_job,
                control,
                evidence,
                timeout=WORKER_TIMEOUTS[job.get("stage", "implementation")],
            )
            if (
                result == "done"
                and worker_job.capability_file
                and worker_job.stage == "implementation"
            ):
                derive_candidate(worker_job, control)
        elif command["kind"] == "pg":
            pg_job = WorkerJob(**job)
            cap = validate_capability(pg_job, control, host_pg=True)
            template = decode(checked_file(cap["template"]).decode())
            require(command["pg_argv"] == template["pg_argv"], "PG template command drift")
            argv = command["pg_argv"]
            require(
                argv[:3] == [sys.executable, "-m", "pytest"] and len(argv) > 3,
                "unknown heavy-PG command",
            )
            require(
                all(
                    type(a) is str
                    and a.startswith("tests/")
                    and ".." not in a
                    and (evidence / a).resolve() == evidence / a
                    and (evidence / a).is_file()
                    and a.endswith(".py")
                    for a in argv[3:]
                ),
                "unknown PG file/command option",
            )
            require(any("/pg-" in name for name in leases), "PG command without unique PG lease")
            require(command["pg_environment"], "PG test environment not configured")
            with StateStore(control, evidence) as store:
                task = store.state["tasks"]["work"]
                require(task["status"] == "ready", "PG may not blindly resume")
                intent = store.begin("work", "verify", job["key"], job["head"], job["base"])
                require(intent is not None, "PG attempt budget")
                intent = cast(dict, intent)
                saved = control / "pg-requested.json"
                junit = control / "pg-junit.xml"
                require(not junit.exists() and not junit.is_symlink(), "PG evidence already exists")
                argv = [*argv, "--junitxml=" + str(junit)]
                immutable(saved, dict(argv=argv, intent=intent))
                # Fixed host command, no shell. All PG work uses this mandatory
                # lease; model sessions have no DB credentials/network authority.
                env = {
                    k: os.environ[k] for k in ("PATH", "HOME", "USER", "LANG") if k in os.environ
                }
                env["PYTHONPATH"] = str(evidence / "src") + os.pathsep + str(evidence)
                output = evidence / "throughput-pg-output.txt"
                pg_terminal = control / "pg-terminal.json"
                atomic_write(pg_terminal, encoded(dict(descendants_stopped=True, phase="no_child")))
                with isolated_environment(command["pg_environment"]) as pg_env:
                    exit_code = execute_pg(argv, evidence, {**env, **pg_env}, output, pg_terminal)
                count = passed_cases(junit)
                xml_evidence = evidence / "throughput-pg-junit.xml"
                require(not xml_evidence.exists(), "PG evidence output collision")
                atomic_write(xml_evidence, junit.read_bytes())
                require(not run("git", "diff", "HEAD", "--", cwd=evidence), "PG changed source")
                require(
                    run("git", "rev-parse", "HEAD", cwd=evidence) == job["head"], "PG changed HEAD"
                )
                require(
                    not run("git", "diff", "--cached", "HEAD", "--", cwd=evidence),
                    "PG changed staged source",
                )
                store.finish(
                    json.dumps(
                        dict(
                            task_id="work",
                            attempt=1,
                            result="pass" if exit_code == 0 else "fail",
                            commit=job["head"],
                            evidence=[
                                dict(
                                    path=output.name,
                                    sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                                ),
                                dict(
                                    path=xml_evidence.name,
                                    sha256=hashlib.sha256(xml_evidence.read_bytes()).hexdigest(),
                                ),
                            ],
                            notes=(
                                f"Host PG verification: {count} actual cases, "
                                "zero skip, unique lease"
                            ),
                        )
                    ),
                    ExecutionReceipt("work", 1, intent["id"], job["head"], exit_code, job["key"]),
                )
                result = store.state["tasks"]["work"]["status"]
        else:
            raise ValueError("unknown executor/resource")
        atomic_write(path.with_suffix(".result.json"), encoded(dict(status=result)))
    except Exception as exc:
        with StateStore(control, evidence) as store:
            name = job["task_id"]
            task = store.state["tasks"][name]
            terminal = control / "executions" / f"{name}-{task['attempt']}" / "terminal.json"
            if command["kind"] == "pg":
                terminal = control / "pg-terminal.json"
            if (
                task["status"] in ("running", "blocked", "failed")
                and task["intent"] is not None
                and (
                    not terminal.is_file()
                    or decode(terminal.read_text()).get("descendants_stopped") is not True
                )
            ):
                quarantine(
                    Path(command["resource_root"]),
                    dict(control=str(control), task=name, reason="unjoined executor failure"),
                )
            if store.state["tasks"][name]["status"] not in ("done", "blocked", "failed"):
                store.block(name, f"throughput executor: {type(exc).__name__}: {exc}"[:4000])
        raise
    finally:
        for fd in owned:
            os.close(fd)


def generated_tick(policy):
    root = Path(policy["root"])
    rows, _index = sources(policy)
    current_rows = {row["id"]: row for row in rows}
    statuses = {}
    for folder in sorted((root / "generations").iterdir()):
        if folder.resolve() != folder or folder.is_symlink():
            statuses[folder.name] = "blocked: unsafe generation path"
            continue
        if not (folder / "packet.json").is_file():
            statuses[folder.name] = "blocked: incomplete admission; preserve directory"
            continue
        try:
            packet = decode((folder / "packet.json").read_text())
            for spec in (
                packet["authorization"],
                packet["index"],
                packet["contract"],
                packet["template"],
            ):
                checked_file(spec)
            current_row = current_rows.get(packet["backlog_id"])
            require(
                current_row is not None
                and current_row["authorized"] is True
                and current_row["risk"] == packet["risk"],
                "active task revoked/risk changed; original packet preserved",
            )
            current = decode((folder / "progress.json").read_text())
            if current["status"] == "done":
                historical = decode((folder / "external-completion.json").read_text())
                checked_file(historical["index"])
                checked_file(historical["receipt"])
                statuses[folder.name] = "done"
                continue
            if completion(_index, packet["backlog_id"]):
                # An owner/host whole-parent receipt may arrive in a later index
                # revision. Never erase a live or uncertain child to consume it.
                for control in folder.glob("*/ledger"):
                    lease = ProcessLock(control / "driver.lock")
                    require(lease.acquire(), "completion while child still active")
                    try:
                        with StateStore(
                            control,
                            Path(decode((control.parent / "job.json").read_text())["checkout"]),
                        ) as store:
                            require(
                                all(t["status"] == "done" for t in store.state["tasks"].values()),
                                "completion while local child unresolved",
                            )
                    finally:
                        lease.close()
                immutable(
                    folder / "external-completion.json",
                    dict(index=policy["index"], receipt=_index["completed"][packet["backlog_id"]]),
                )
                progress(
                    folder,
                    current["stage"],
                    "done",
                    reason="verified whole-BACKLOG completion receipt",
                )
                statuses[folder.name] = "done"
                continue
            if current["status"] in ("blocked", "awaiting_publication", "done"):
                statuses[folder.name] = current["status"]
                continue
            stage = current["stage"]
            status = launch(policy, folder, packet, stage)
            if status == "done":
                stages = packet["stages"]
                next_index = stages.index(stage) + 1
                if next_index == len(stages):
                    progress(
                        folder,
                        stage,
                        "awaiting_publication",
                        reason="Publication gate: retain author and independent review receipts",
                    )
                else:
                    progress(folder, stages[next_index], "ready")
            elif status in ("failed", "blocked", "budget_exhausted"):
                progress(folder, stage, "blocked", reason=status)
            else:
                require(
                    status in ("running", "capacity_wait", "retry_wait")
                    or status.startswith("held:"),
                    "unknown executor status",
                )
                progress(folder, stage, status)
                if status.startswith("held:"):
                    from scripts.pipeline_wakeup import notify

                    notify(root, dict(backlog=folder.name, stage=stage, status=status))
            statuses[folder.name] = decode((folder / "progress.json").read_text())["status"]
        except Exception as exc:
            statuses[folder.name] = f"blocked: {type(exc).__name__}: {exc}"
            if (folder / "progress.json").exists():
                progress(folder, "unknown", "blocked", reason=statuses[folder.name])
    return statuses


def merge_prepared(config, policy, entry, *, config_path=None):
    """Fresh config, global → merge → driver → state. Never hold these for CI."""
    leases = [
        ProcessLock(Path(config["root"]) / "wakeup.lock"),
        ProcessLock(Path(policy["root"]) / "resources/merge.lock"),
        ProcessLock(Path(entry["control"]) / "driver.lock"),
    ]
    try:
        for lease in leases:
            if not lease.acquire():
                return None
        if config_path is not None:
            from scripts.pipeline_wakeup import load_config

            current = load_config(config_path)
            require(
                current["throughput"] == policy
                and current["root"] == config["root"]
                and current["source_head"] == config["source_head"],
                "merge runtime binding drift",
            )
            config = current
        if not config["merge_policy"]["enabled"]:
            return None
        result = None
        with StateStore(
            Path(entry["control"]),
            Path(entry["evidence"]),
            merge_approvers=frozenset(config["approvers"]),
        ) as store:
            for name, task in list(store.state["tasks"].items()):
                if task["status"] == "awaiting_merge":
                    from scripts.pipeline_merge import execute_merge

                    result = execute_merge(
                        store,
                        name,
                        entry["repository"],
                        policy=config["merge_policy"],
                        entry_id=entry["id"],
                    )
        return result
    finally:
        for lease in reversed(leases):
            lease.close()


def legacy_tick(config, policy, entries, *, config_path=None):
    """Do not silently discard previously prepared generations during opt-in."""
    results = {}
    for entry in entries:
        key = entry["id"]
        try:
            control, evidence = Path(entry["control"]), Path(entry["evidence"])
            jobs_raw = Path(entry["jobs"]).read_bytes()
            require(hashlib.sha256(jobs_raw).hexdigest() == entry["jobs_sha256"], "jobs drift")
            jobs = decode(jobs_raw.decode())
            with StateStore(control, evidence) as store:
                tasks = store.state["tasks"]
                active = [
                    name
                    for name, t in tasks.items()
                    if t["status"] in ("ready", "running", "retry_wait")
                ]
            results[key] = "done" if all(t["status"] == "done" for t in tasks.values()) else "held"
            for name in active:
                job = jobs.get(name)
                require(
                    job is not None and job["kind"] in ("ci", "worker"), "unknown prepared executor"
                )
                job = cast(dict, job)
                with StateStore(control, evidence) as store:
                    if tasks[name]["status"] == "ready" and name not in store.eligible(
                        int(time.time())
                    ):
                        continue
                if job["kind"] == "ci":
                    lease = ProcessLock(control / "driver.lock")
                    if not lease.acquire():
                        results[key] = "running"
                        continue
                    try:
                        results[key] = poll_ci(
                            PublishedCITarget(**job["config"]), name, control, evidence
                        )
                        if results[key] in ("retry_wait", "blocked"):
                            from scripts.pipeline_wakeup import notify

                            notify(
                                Path(config["root"]),
                                dict(
                                    entry=key,
                                    task=name,
                                    status=results[key],
                                    reason="persistent CI window transition",
                                ),
                            )
                    finally:
                        lease.close()
                else:
                    stage = job["config"].get("stage", "implementation")
                    require(
                        stage in ("implementation", "review", "design"), "unknown worker resource"
                    )
                    results[key] = launch(
                        policy, control, {}, stage, legacy=(control, evidence, job["config"], name)
                    )
            merged = merge_prepared(config, policy, entry, config_path=config_path)
            if merged is not None:
                results[key] = merged
        except LockBusy:
            results[key] = "running"
        except Exception as exc:
            results[key] = f"blocked: {type(exc).__name__}: {exc}"
            try:
                with StateStore(Path(entry["control"]), Path(entry["evidence"])) as store:
                    for name, task in list(store.state["tasks"].items()):
                        if task["status"] not in ("done", "failed", "blocked", "budget_exhausted"):
                            store.block(name, results[key][:4000])
            except LockBusy:
                results[key] = "running"
    return results


def tick(config, *, config_path=None) -> dict:
    policy = config["throughput"]
    validate_policy(policy)
    root = Path(policy["root"])
    real_directory(root)
    global_lease = ProcessLock(Path(config["root"]) / "wakeup.lock")
    if not global_lease.acquire():
        return dict(status="busy")
    try:
        policy_revision(root, policy)
        admission = admit(policy)
        queue = decode(Path(config["queue"]).read_text())
        require(queue["version"] == 1 and type(queue["entries"]) is list, "prepared registry")
        controls = set()
        for entry in queue["entries"]:
            exact(
                entry,
                ("id", "control", "evidence", "checkout", "jobs", "jobs_sha256", "repository"),
            )
            require(entry["control"] not in controls, "duplicate prepared control")
            controls.add(entry["control"])
            for key in ("control", "evidence", "checkout", "jobs"):
                path = Path(entry[key])
                require(
                    path.is_absolute() and path.resolve() == path and not path.is_symlink(),
                    "unsafe prepared path",
                )
        bindings = {e["id"]: e for e in queue["entries"]}
        require(len(bindings) == len(queue["entries"]), "duplicate prepared entry")
        admitted = root / "prepared-bindings.json"
        old = decode(admitted.read_text()) if admitted.exists() else {}
        require(
            all(k in bindings and bindings[k] == v for k, v in old.items()),
            "prepared generation removal/binding drift",
        )
        atomic_write(admitted, encoded(bindings))
        atomic_write(
            root / "inventory.json", encoded(dict(admission=admission, prepared=queue["entries"]))
        )
    finally:
        global_lease.close()
    # No CI polling, model lifetime, PG command or retry sleep owns wakeup.lock.
    audit_unjoined(policy, queue["entries"])
    results = legacy_tick(config, policy, queue["entries"], config_path=config_path)
    generated = generated_tick(policy)
    response = dict(status="checked", entries=results, backlog=generated, admission=admission)
    if "daily_report" in config:
        from scripts.pipeline_wakeup import notify

        try:
            from scripts.pipeline_progress import daily_report

            response["daily_report"] = daily_report(
                config["daily_report"], Path(config["root"]), queue["entries"], config["approvers"]
            )
        except Exception as exc:
            issue = dict(
                component="daily_report", status="blocked", reason=f"{type(exc).__name__}: {exc}"
            )
            notify(Path(config["root"]), issue)
            response["daily_report"] = issue
    atomic_write(root / "last-tick.json", encoded(response))
    return response


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--command", type=Path, required=True)
    parser.add_argument("--lease", action="append", default=[])
    args = parser.parse_args()
    run_command(args.command, args.lease)


if __name__ == "__main__":
    main()
