"""Offline v1 engineering control protocol. No Codex, GitHub or business DB execution.

Only the trusted controller writes this directory. Worker worktrees must not have
write access to it. Reports are claims; host receipts bind them to actual execution.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast

from scripts.pipeline_safety import ProcessLock

SHA = re.compile(r"[0-9a-f]{40}")
DIGEST = re.compile(r"[0-9a-f]{64}")
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}")
STATUSES = {
    "ready",
    "running",
    "retry_wait",
    "awaiting_merge",
    "blocked",
    "failed",
    "done",
    "budget_exhausted",
}
KINDS = {"worker", "verify", "review", "publish", "ci", "merge", "delete", "architecture"}
EXPECTED_CHECKS = {"static", *(f"checks ({i})" for i in range(6))}


class ProtocolError(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise ProtocolError(message)


def exact(value, keys):
    require(type(value) is dict and set(value) == set(keys), "unexpected/missing fields")


def integer(value, minimum=0):
    require(type(value) is int and value >= minimum, "invalid integer")


def text(value, limit=4096):
    require(type(value) is str and len(value) <= limit and "\x00" not in value, "invalid text")


def commit(value):
    require(type(value) is str and SHA.fullmatch(value) is not None, "invalid commit")


def checks_ready(head, checks):
    names = [c["name"] for c in checks]
    return all(names.count(n) == 1 for n in EXPECTED_CHECKS) and all(
        c["head"] == head and c["conclusion"] == "success" for c in checks
    )


def decode(raw) -> Any:
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON key")
            result[key] = value
        return result

    require(type(raw) is str and len(raw.encode()) <= 1024 * 1024, "output too large")
    try:
        return json.loads(
            raw, object_pairs_hook=pairs, parse_constant=lambda _: require(False, "nonfinite JSON")
        )
    except (ValueError, TypeError) as exc:
        raise ProtocolError("invalid JSON") from exc


def encoded(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode()


def atomic_write(path, data):
    fd, temporary = tempfile.mkstemp(prefix=".state-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def report(raw, evidence_root):
    value = decode(raw)
    exact(value, ("task_id", "attempt", "result", "commit", "evidence", "notes"))
    require(type(value["task_id"]) is str and ID.fullmatch(value["task_id"]), "invalid task id")
    integer(value["attempt"], 1)
    require(value["result"] in ("pass", "fail", "error"), "invalid result")
    commit(value["commit"])
    text(value["notes"])
    evidence = value["evidence"]
    require(type(evidence) is list and 1 <= len(evidence) <= 16, "evidence required")
    seen = set()
    for entry in evidence:
        exact(entry, ("path", "sha256"))
        item = cast(dict[str, Any], entry)
        name, digest = item["path"], item["sha256"]
        text(name, 512)
        require(
            name
            and not Path(name).is_absolute()
            and all(p not in ("", ".", "..") for p in name.split("/")),
            "unsafe evidence path",
        )
        require(name not in seen, "duplicate evidence path")
        seen.add(name)
        require(type(digest) is str and DIGEST.fullmatch(digest), "invalid evidence digest")
        path = evidence_root
        for part in name.split("/"):
            path = path / part
            require(not path.is_symlink(), "symlink evidence denied")
        require(path.is_file() and path.stat().st_size <= 64 * 1024 * 1024, "invalid evidence file")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        require(actual == digest, "evidence hash mismatch")
    return value


@dataclass(frozen=True)
class ExecutionReceipt:
    task_id: str
    attempt: int
    intent_id: str
    commit: str
    exit_code: int


@dataclass(frozen=True)
class Publication:
    key: str
    head: str
    base: str
    pr: int


def validate_state(value):
    exact(value, ("version", "revision", "rounds_used", "tasks"))
    require(type(value["version"]) is int and value["version"] == 1, "unknown protocol version")
    integer(value["revision"])
    integer(value["rounds_used"])
    require(type(value["tasks"]) is dict, "invalid tasks")
    for name, task in value["tasks"].items():
        require(type(name) is str and ID.fullmatch(name), "invalid task id")
        exact(
            task, ("needs", "status", "attempt", "intent", "result", "retry_at", "reason", "merge")
        )
        require(type(task["status"]) is str and task["status"] in STATUSES, "unknown task status")
        integer(task["attempt"])
        require(
            type(task["needs"]) is list
            and all(type(n) is str for n in task["needs"])
            and len(task["needs"]) == len(set(task["needs"])),
            "invalid dependencies",
        )
        require(all(n in value["tasks"] and n != name for n in task["needs"]), "unknown dependency")
        if task["intent"] is not None:
            exact(task["intent"], ("id", "kind", "key", "head", "base"))
            require(
                type(task["intent"]["kind"]) is str and task["intent"]["kind"] in KINDS,
                "unknown action kind",
            )
            text(task["intent"]["id"], 128)
            text(task["intent"]["key"], 256)
            commit(task["intent"]["head"])
            commit(task["intent"]["base"])
        if task["result"] is not None:
            require(
                task["result"] == f"results/{name}-{task['attempt']}.json",
                "invalid result reference",
            )
        if task["retry_at"] is not None:
            integer(task["retry_at"])
        if task["reason"] is not None:
            text(task["reason"])
        if task["merge"] is not None:
            exact(
                task["merge"],
                ("pr", "head", "base", "after_event", "approved_event", "approved_actor"),
            )
            integer(task["merge"]["pr"], 1)
            commit(task["merge"]["head"])
            commit(task["merge"]["base"])
            integer(task["merge"]["after_event"])
            if task["merge"]["approved_event"] is not None:
                integer(task["merge"]["approved_event"], task["merge"]["after_event"] + 1)
                text(task["merge"]["approved_actor"], 128)
        if task["status"] in ("running", "retry_wait"):
            require(task["intent"] is not None and task["attempt"] > 0, "missing execution intent")
        if task["status"] == "awaiting_merge":
            require(task["merge"] is not None, "missing merge binding")
        if task["status"] == "retry_wait":
            require(task["retry_at"] is not None, "missing retry time")
        if task["status"] == "done":
            require(task["result"] is not None, "missing completion receipt")

    checked = set()

    def visit(name, trail):
        require(name not in trail, "dependency cycle")
        if name in checked:
            return
        for parent in value["tasks"][name]["needs"]:
            visit(parent, trail | {name})
        checked.add(name)

    for name in value["tasks"]:
        visit(name, set())


class StateStore:
    def __init__(self, directory: Path, evidence_root: Path, *, merge_approvers=frozenset()):
        self.directory = directory
        self.evidence_root = evidence_root.resolve()
        self.lock = ProcessLock(directory / "control.lock")
        self.state: dict = {}
        self.merge_approvers = merge_approvers

    def __enter__(self):
        self.lock.__enter__()
        try:
            path = self.directory / "state.json"
            require(not path.is_symlink(), "symlink state denied")
            if path.exists():
                self.state = decode(path.read_text())
                validate_state(self.state)
                for name, task in self.state["tasks"].items():
                    if task["status"] == "done":
                        saved = self.directory / task["result"]
                        require(
                            saved.is_file() and not saved.is_symlink(), "missing completion receipt"
                        )
                        self._validate_completion(name, decode(saved.read_text()))
            else:
                self.state = dict(version=1, revision=0, rounds_used=0, tasks={})
                atomic_write(path, encoded(self.state))
            return self
        except BaseException:
            self.lock.close()
            raise

    def __exit__(self, *args):
        self.lock.close()

    def _save(self, value):
        self.lock.check()
        validate_state(value)
        current = decode((self.directory / "state.json").read_text())
        require(current["revision"] == self.state["revision"], "state revision conflict")
        value["revision"] += 1
        atomic_write(self.directory / "state.json", encoded(value))
        self.state = value

    def _copy(self):
        self.lock.check()
        return json.loads(json.dumps(self.state))

    def add(self, name, needs=()):
        value = self._copy()
        require(name not in value["tasks"], "task already exists")
        value["tasks"][name] = dict(
            needs=list(needs),
            status="ready",
            attempt=0,
            intent=None,
            result=None,
            retry_at=None,
            reason=None,
            merge=None,
        )
        self._save(value)

    def eligible(self, now):
        return [
            name
            for name, t in self.state["tasks"].items()
            if (t["status"] == "ready" or (t["status"] == "retry_wait" and t["retry_at"] <= now))
            and all(self.state["tasks"][n]["status"] == "done" for n in t["needs"])
        ]

    def begin(self, name, kind, key, head, base, *, now=0, max_rounds=40):
        require(name in self.eligible(now), "task not eligible")
        require(kind in KINDS, "unknown action kind")
        require(
            not any(
                t["intent"] is not None
                and t["intent"]["key"] == key
                and t["status"] in ("running", "blocked")
                for other, t in self.state["tasks"].items()
                if other != name
            ),
            "resource has unreconciled execution",
        )
        value = self._copy()
        task = value["tasks"][name]
        if kind in ("delete", "architecture"):
            task.update(status="blocked", reason="human decision required")
            self._save(value)
            return None
        require(kind != "merge", "merge requires approved-merge label gate")
        if value["rounds_used"] >= max_rounds:
            task.update(status="budget_exhausted", reason="round budget exhausted")
            self._save(value)
            return None
        task.update(
            status="running",
            attempt=task["attempt"] + 1,
            intent=dict(id=secrets.token_hex(12), kind=kind, key=key, head=head, base=base),
            result=None,
            retry_at=None,
            reason=None,
        )
        value["rounds_used"] += 1
        self._save(value)
        return dict(task["intent"])

    def quota(self, name, retry_at):
        integer(retry_at)
        value = self._copy()
        task = value["tasks"][name]
        require(task["status"] == "running", "no running attempt")
        task.update(status="retry_wait", retry_at=retry_at, reason="quota")
        self._save(value)

    def _receipt(self, name, content):
        task = self.state["tasks"][name]
        relative = f"results/{name}-{task['attempt']}.json"
        target = self.directory / relative
        target.parent.mkdir(exist_ok=True)
        require(
            not target.is_symlink() and not target.parent.is_symlink(), "symlink receipt denied"
        )
        data = encoded(content)
        # Immutable per-attempt receipts allow recovery after result -> state crash.
        if target.exists():
            require(target.read_bytes() == data, "conflicting completion receipt")
        else:
            with target.open("xb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            directory = os.open(target.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        return relative

    def _validate_completion(self, name, content):
        task = self.state["tasks"][name]
        if set(content) == {"report", "receipt"}:
            parsed = report(json.dumps(content["report"]), self.evidence_root)
            receipt = ExecutionReceipt(**content["receipt"])
            require(receipt.task_id == name, "completion task mismatch")
            self._bind_report(parsed, receipt, task)
            require(
                parsed["result"] == "pass" and receipt.exit_code == 0,
                "invalid successful completion",
            )
        else:
            exact(content, ("publication", "intent_id"))
            observed = Publication(**content["publication"])
            if task["intent"] is None:
                raise ProtocolError("missing publication intent")
            expected = cast(dict[str, Any], task["intent"])
            require(
                expected is not None and expected["kind"] == "publish",
                "invalid publication receipt",
            )
            require(
                content["intent_id"] == expected["id"]
                and (observed.key, observed.head, observed.base)
                == (expected["key"], expected["head"], expected["base"]),
                "remote publication mismatch",
            )
            integer(observed.pr, 1)

    def _bind_report(self, parsed, receipt, task):
        require(
            parsed["task_id"] == receipt.task_id
            and parsed["attempt"] == receipt.attempt == task["attempt"],
            "wrong attempt",
        )
        require(
            receipt.intent_id == task["intent"]["id"] and receipt.commit == parsed["commit"],
            "execution binding mismatch",
        )
        require(type(receipt.exit_code) is int, "invalid host exit code")
        if task["intent"]["kind"] != "worker":
            require(receipt.commit == task["intent"]["head"], "wrong checked head")

    def finish(self, raw, receipt: ExecutionReceipt):
        self.lock.check()
        parsed = report(raw, self.evidence_root)
        task = self.state["tasks"][receipt.task_id]
        require(task["status"] == "running", "no running attempt")
        self._bind_report(parsed, receipt, task)
        content = dict(report=parsed, receipt=asdict(receipt))
        relative = self._receipt(receipt.task_id, content)
        value = self._copy()
        value["tasks"][receipt.task_id].update(
            status="done" if parsed["result"] == "pass" and receipt.exit_code == 0 else "failed",
            result=relative,
        )
        self._save(value)

    def recover_result(self, name):
        task = self.state["tasks"][name]
        path = self.directory / f"results/{name}-{task['attempt']}.json"
        require(path.is_file(), "no receipt; reconcile live execution, never blindly relaunch")
        content = decode(path.read_text())
        exact(content, ("report", "receipt"))
        self.finish(json.dumps(content["report"]), ExecutionReceipt(**content["receipt"]))

    def reconcile_publication(self, name, observed: Publication | None):
        value = self._copy()
        task = value["tasks"][name]
        require(
            task["status"] == "running" and task["intent"]["kind"] == "publish",
            "not a pending publication",
        )
        if observed is None:
            task.update(
                status="blocked", reason="publication outcome unknown; reconcile before retry"
            )
        else:
            expected = task["intent"]
            require(
                (observed.key, observed.head, observed.base)
                == (expected["key"], expected["head"], expected["base"]),
                "remote publication mismatch",
            )
            integer(observed.pr, 1)
            relative = self._receipt(
                name, dict(publication=asdict(observed), intent_id=expected["id"])
            )
            task.update(status="done", result=relative)
        self._save(value)

    def await_merge(self, name, publication: Publication, *, after_event: int, checks):
        value = self._copy()
        task = value["tasks"][name]
        require(name in self.eligible(0), "merge task not eligible")
        integer(publication.pr, 1)
        integer(after_event)
        require(checks_ready(publication.head, checks), "CI not ready on exact head")
        task.update(
            status="awaiting_merge",
            merge=dict(
                pr=publication.pr,
                head=publication.head,
                base=publication.base,
                after_event=after_event,
                approved_event=None,
                approved_actor=None,
            ),
        )
        self._save(value)

    def approve_label(self, name, *, event_id, label, pr, head, base, actor):
        value = self._copy()
        task = value["tasks"][name]
        require(task["status"] == "awaiting_merge", "not awaiting merge")
        binding = task["merge"]
        require(actor in self.merge_approvers, "label actor is not authorized")
        require(
            label == "approved-merge"
            and (pr, head, base) == (binding["pr"], binding["head"], binding["base"]),
            "approval scope mismatch",
        )
        integer(event_id, binding["after_event"] + 1)
        binding["approved_event"] = event_id
        binding["approved_actor"] = actor
        self._save(value)

    def merge_allowed(self, name, *, head, base, checks, labels):
        binding = self.state["tasks"][name]["merge"]
        if not binding:
            return False
        if (head, base) != (binding["head"], binding["base"]):
            value = self._copy()
            value["tasks"][name].update(
                status="blocked", reason="head/base changed; approval invalidated"
            )
            value["tasks"][name]["merge"]["approved_event"] = None
            value["tasks"][name]["merge"]["approved_actor"] = None
            self._save(value)
            return False
        if "approved-merge" not in labels:
            if binding["approved_event"] is not None:
                value = self._copy()
                changed = value["tasks"][name]["merge"]
                changed["after_event"] = changed["approved_event"]
                changed["approved_event"] = None
                changed["approved_actor"] = None
                self._save(value)
            return False
        return (
            self.state["tasks"][name]["status"] == "awaiting_merge"
            and binding["approved_event"] is not None
            and binding["approved_actor"] in self.merge_approvers
            and checks_ready(head, checks)
        )
