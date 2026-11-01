"""Observed engineering progress, once per local day; never an acceptance writer."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from scripts.pipeline_protocol import StateStore, atomic_write, decode, encoded, exact, require
from scripts.pipeline_safety import LockBusy, ProcessLock, real_directory

TAG = "researchbase-daily-progress"


def regular(raw):
    require(type(raw) is str and Path(raw).is_absolute(), "absolute reporting input required")
    path = Path(raw)
    require(path.resolve() == path and path.is_file() and not path.is_symlink(), "report input")
    return path


def configuration(raw):
    exact(raw, ("plan", "progress", "authorization_file", "authorization_sha256", "timezone"))
    for key in ("plan", "progress", "authorization_file"):
        regular(raw[key])
    require(Path(raw["plan"]).name == "PLAN.md", "report destination must be PLAN.md")
    require(raw["timezone"] == "America/New_York", "reporting timezone")
    require(
        type(raw["authorization_sha256"]) is str
        and re.fullmatch(r"[0-9a-f]{64}", raw["authorization_sha256"]),
        "report authorization digest",
    )
    return raw


def inventory(config) -> dict:
    auth = regular(config["authorization_file"]).read_bytes()
    require(hashlib.sha256(auth).hexdigest() == config["authorization_sha256"], "inventory drift")
    manifest = decode(auth.decode())
    require(manifest["version"] == 1 and type(manifest["tasks"]) is list, "inventory schema")
    risks = {}
    for task in manifest["tasks"]:
        key = task["id"]
        require(type(key) is str and re.fullmatch(r"[A-Z][A-Z0-9-]*", key), "inventory ID")
        require(key not in risks and task["risk"] in ("low", "medium", "high"), "inventory risk")
        risks[key] = task["risk"]
    raw = regular(config["progress"]).read_bytes()
    progress = decode(raw.decode())
    require(progress["authorization_sha256"] == config["authorization_sha256"], "progress binding")
    require(
        type(progress["tasks"]) is dict and set(progress["tasks"]) == set(risks), "task set drift"
    )
    statuses = {}
    for key, task in progress["tasks"].items():
        status = task["status"]
        require(
            type(status) is str and re.fullmatch(r"[a-z][a-z_]{0,63}", status), "inventory status"
        )
        statuses[key] = status
    return dict(
        source_sha256=hashlib.sha256(raw).hexdigest(),
        authorization_sha256=config["authorization_sha256"],
        statuses=statuses,
        risks=risks,
        counts=dict(sorted(Counter(statuses.values()).items())),
        interpretation="Operator inventory only; these counts are not new acceptance decisions.",
    )


def observed_generations(entries, approvers):
    result = {}
    for entry in entries:
        control, evidence = (
            regular_directory(entry["control"]),
            regular_directory(entry["evidence"]),
        )
        lease = ProcessLock(control / "driver.lock")
        if not lease.acquire():
            result[entry["id"]] = dict(observation="busy_unverified")
            continue
        try:
            with StateStore(control, evidence, merge_approvers=frozenset(approvers)) as store:
                # StateStore checks every existing completion, including merge
                # effect/intent/target/proof journals and artifact digests.
                tasks, receipts = {}, {}
                for name, task in store.state["tasks"].items():
                    tasks[name] = dict(status=task["status"], attempt=task["attempt"])
                    if task["status"] == "done":
                        require(task["result"] is not None, "done without receipt")
                        path = regular(str(control / task["result"]))
                        receipts[name] = hashlib.sha256(path.read_bytes()).hexdigest()
                result[entry["id"]] = dict(
                    observation="local_receipts_validated",
                    rounds_used=store.state["rounds_used"],
                    tasks=tasks,
                    receipt_sha256=receipts,
                )
        finally:
            lease.close()
    return result


def regular_directory(raw):
    require(type(raw) is str and Path(raw).is_absolute(), "absolute report directory")
    path = Path(raw)
    require(path.resolve() == path and path.is_dir() and not path.is_symlink(), "report directory")
    return path


def block(snapshot):
    payload = json.dumps(snapshot, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode()).hexdigest()
    day = snapshot["day"]
    return (
        f"<!-- {TAG} {day} {digest} -->\n"
        f"\n### Engineering progress {day} ({snapshot['timezone']})\n\n"
        "Observed inventory and local receipts; no scientific or acceptance state changed.\n\n"
        f"```json\n{payload}\n```\n"
        f"<!-- /{TAG} {day} -->\n"
    ).encode()


def existing_blocks(plan):
    text = plan.decode("utf-8")
    pattern = re.compile(
        rf"<!-- {TAG} (\d{{4}}-\d{{2}}-\d{{2}}) ([0-9a-f]{{64}}) -->\n"
        rf".*?```json\n([^\n]+)\n```\n<!-- /{TAG} \1 -->\n",
        re.DOTALL,
    )
    found = {}
    for match in pattern.finditer(text):
        day, digest, payload = match.groups()
        require(day not in found, "duplicate daily report")
        require(hashlib.sha256(payload.encode()).hexdigest() == digest, "daily payload changed")
        snapshot = decode(payload)
        require(
            snapshot["day"] == day and block(snapshot).decode() == match.group(),
            "daily block drift",
        )
        found[day] = snapshot
    require(
        text.count(f"<!-- {TAG} ") == text.count(f"<!-- /{TAG} ") == len(found),
        "malformed daily report history",
    )
    return found


def daily_report(raw, state_root, entries, approvers, *, now=None):
    config = configuration(raw)
    instant = now if now is not None else datetime.now(UTC)
    require(instant.tzinfo is not None and instant.utcoffset() is not None, "aware report time")
    day = instant.astimezone(ZoneInfo(config["timezone"])).date().isoformat()
    plan = regular(config["plan"])
    try:
        with ProcessLock(plan.with_name(plan.name + ".lock")):
            before = plan.read_bytes()
            history = existing_blocks(before)
            records = state_root / "daily-progress"
            require(
                records.resolve() == records and not records.is_symlink(), "report records path"
            )
            marker = records / (day + ".json")
            require(not marker.is_symlink(), "symlink daily marker")
            if day in history:
                saved = history[day]
                if marker.exists():
                    require(decode(regular(str(marker)).read_text()) == saved, "daily marker drift")
                else:
                    real_directory(records)
                    atomic_write(marker, encoded(saved))
                return dict(status="already_recorded", day=day)
            require(
                not marker.exists() and not marker.is_symlink(), "daily marker without PLAN block"
            )
            observed = inventory(config)
            completed = sorted(k for k, value in observed["statuses"].items() if value == "done")
            previous = history[max(history)] if history else None
            require(previous is None or previous["day"] < day, "report clock moved backwards")
            prior_done = previous["inventory_completed_ids"] if previous else completed
            new_done = sorted(set(completed) - set(prior_done))
            snapshot = dict(
                version=1,
                day=day,
                timezone=config["timezone"],
                inventory=observed,
                inventory_completed_ids=completed,
                newly_observed_inventory_completions=new_done,
                backlog_review_pending=bool(new_done),
                review_note=(
                    "New inventory completions require milestone/ten-item reassessment; "
                    "no automatic replanning."
                ),
                generations=observed_generations(entries, approvers),
            )
            # Do not write a payload the next wake cannot read within the
            # protocol's existing JSON size budget.
            decode(json.dumps(snapshot))
            addition = b"\n" + block(snapshot)
            # Cooperating writers use the stable PLAN lock. Detect edits made
            # before replacement as well; this is not an adversarial file CAS.
            require(plan.read_bytes() == before, "PLAN changed while reporting")
            real_directory(records)
            atomic_write(plan, before + addition)
            # Crash here is recovered from the exact PLAN block next wake.
            atomic_write(marker, encoded(snapshot))
            return dict(status="written", day=day, backlog_review_pending=bool(new_done))
    except LockBusy:
        return dict(status="busy", day=day)
