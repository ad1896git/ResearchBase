"""One fresh read-only command decision, with host validation and no dispatch loop."""

from __future__ import annotations

import argparse
import hashlib
import json
import secrets
from pathlib import Path

from scripts.pipeline_protocol import (
    StateStore,
    atomic_write,
    decode,
    encoded,
    exact,
    require,
    text,
)
from scripts.pipeline_sessions import SCRIPTS, run_session


def decision(raw: str, revision: int, eligible: list[str]) -> dict:
    value = decode(raw)
    exact(value, ("revision", "action", "task_id", "reason"))
    require(type(value["revision"]) is int and value["revision"] == revision, "stale decision")
    text(value["reason"])
    require(value["action"] in ("dispatch", "wait", "stop"), "invalid commander action")
    text(value["task_id"], 64)
    if value["action"] == "dispatch":
        require(value["task_id"] in eligible, "ineligible dispatch")
    else:
        require(value["task_id"] == "", "non-dispatch task must be empty")
    return value


def command_once(control: Path, evidence: Path, checkout: Path, *, now=0, timeout=180) -> dict:
    with StateStore(control, evidence) as store:
        snapshot = encoded(store.state)
        revision = store.state["revision"]
        eligible = store.eligible(now)
        # CI polling is read-only and resumes the same intent; never relaunch a running worker.
        eligible += [
            name
            for name, task in store.state["tasks"].items()
            if task["status"] == "running" and task["intent"]["kind"] == "ci"
        ]
        output = control / "decisions" / secrets.token_hex(12)
        output.parent.mkdir(exist_ok=True)
        prompt = (
            "You are a short-session engineering commander. Do not edit files or execute work, "
            "publish, merge, label, or call external services. Return only the schema decision. "
            "Choose an eligible task if any; otherwise wait for running/awaiting_merge tasks, "
            "or stop if all done or human decision is needed. A decision is a proposal only. "
            "Preserve exact revision. For wait/stop task_id must be empty.\n"
            + json.dumps({"state": store.state, "eligible": eligible})
        )
        terminal = run_session(
            checkout,
            output,
            prompt,
            SCRIPTS / "pipeline_commander.schema.json",
            timeout=timeout,
        )
        require(
            terminal["exit_code"] == 0
            and not terminal["timed_out"]
            and terminal["descendants_stopped"],
            "commander session unsuccessful",
        )
        store.lock.check()
        require((control / "state.json").read_bytes() == snapshot, "state changed during command")
        result = decision((output / "answer.json").read_text(), revision, eligible)
        atomic_write(
            output / "validated.json",
            encoded(
                {
                    "decision": result,
                    "state_sha256": hashlib.sha256(snapshot).hexdigest(),
                }
            ),
        )
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--now", type=int, default=0)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    print(
        json.dumps(
            command_once(
                args.control.resolve(),
                args.evidence.resolve(),
                args.checkout.resolve(),
                now=args.now,
                timeout=args.timeout,
            )
        )
    )


if __name__ == "__main__":
    main()
