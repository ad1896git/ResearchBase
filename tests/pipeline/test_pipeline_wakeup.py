"""Offline wakeup acceptance: no launchctl installation or remote writes."""

import hashlib
import json
import plistlib
import sys
from copy import deepcopy
from pathlib import Path

import pytest
from scripts import pipeline_driver as driver
from scripts import pipeline_wakeup as wakeup
from scripts.pipeline_protocol import (
    EXPECTED_CHECKS,
    ExecutionReceipt,
    ProtocolError,
    Publication,
    StateStore,
)
from scripts.pipeline_safety import ProcessLock, SafetyError

A, B = "a" * 40, "b" * 40
SOURCE_GUARD = wakeup.source_guard


def ci_rows() -> list[dict]:
    return [
        dict(
            name=n,
            head_sha=A,
            status="completed",
            conclusion="success",
            app={"slug": "github-actions"},
        )
        for n in sorted(EXPECTED_CHECKS)
    ]


@pytest.fixture
def merge_case(tmp_path):
    evidence = tmp_path / "merge-evidence"
    evidence.mkdir()
    (evidence / "test.log").write_text("evidence")
    control = tmp_path / "merge-control"
    with StateStore(control, evidence, create=True, merge_approvers=frozenset({"owner"})) as store:
        store.add("publish")
        store.begin("publish", "publish", "topic", A, B)
        store.reconcile_publication("publish", Publication("topic", A, B, 1))
        for kind in ("verify", "review"):
            store.add(kind)
            intent = store.begin(kind, kind, "pr:1", A, B)
            assert intent is not None
            store.finish(
                json.dumps(
                    dict(
                        task_id=kind,
                        attempt=1,
                        result="pass",
                        commit=A,
                        evidence=[
                            dict(path="test.log", sha256=hashlib.sha256(b"evidence").hexdigest())
                        ],
                        notes="unit",
                    )
                ),
                ExecutionReceipt(kind, 1, intent["id"], A, 0, "pr:1"),
            )
        store.add("merge", needs=("publish", "verify", "review"))
        store.await_merge(
            "merge",
            Publication("topic", A, B, 1),
            after_event=5,
            checks=[dict(name=n, head=A, conclusion="success") for n in EXPECTED_CHECKS],
            proofs=("publish", "verify", "review"),
        )
    return control, evidence


def observed(actor="owner", event=6) -> dict:
    return dict(
        pr=dict(number=1, state="OPEN", isDraft=False, headRefOid=A, baseRefOid=B),
        labels={"approved-merge"},
        effective=(event, actor),
        cursor=event,
        checks=[dict(name=n, head=A, conclusion="success") for n in EXPECTED_CHECKS],
        outcome="pass",
    )


@pytest.mark.parametrize(
    "mutation,expected",
    [
        ("none", "manual_merge_ready"),
        ("actor", "awaiting_merge"),
        ("old", "awaiting_merge"),
        ("removed", "awaiting_merge"),
        ("head", "blocked"),
        ("base", "blocked"),
        ("ci", "awaiting_merge"),
        ("pending", "awaiting_merge"),
        ("merged", "manual_reconciliation"),
    ],
)
def test_readonly_approval_requires_actor_new_event_exact_head_base_and_ci(
    merge_case, monkeypatch, mutation, expected
):
    control, evidence = merge_case
    value = observed()
    if mutation == "actor":
        value["effective"] = (6, "stranger")
    elif mutation == "old":
        value["effective"], value["cursor"] = (5, "owner"), 5
    elif mutation == "removed":
        value["effective"], value["labels"] = None, set()
    elif mutation in ("head", "base"):
        value["pr"]["headRefOid" if mutation == "head" else "baseRefOid"] = "c" * 40
    elif mutation == "ci":
        value["checks"][0]["conclusion"] = "failure"
    elif mutation == "pending":
        value["outcome"] = "pending"
    elif mutation == "merged":
        value["pr"]["state"] = "MERGED"
    monkeypatch.setattr(wakeup, "observe", lambda *a: deepcopy(value))
    with StateStore(control, evidence, merge_approvers=frozenset({"owner"})) as store:
        assert wakeup.check_merge(store, "merge", "owner/repo") == expected
        assert store.state["tasks"]["merge"]["status"] != "done"
        if mutation in ("head", "base"):
            assert store.state["tasks"]["merge"]["status"] == "blocked"


def test_changed_observation_never_claims_ready(merge_case, monkeypatch):
    values = iter([observed(), observed("stranger", 7)])
    monkeypatch.setattr(wakeup, "observe", lambda *a: next(values))
    with StateStore(*merge_case, merge_approvers=frozenset({"owner"})) as store:
        with pytest.raises(ProtocolError, match="changed"):
            wakeup.check_merge(store, "merge", "owner/repo")


@pytest.mark.parametrize("bad", ["duplicate", "producer", "wrong_head", "missing"])
def test_observer_pages_all_events_and_checks_and_fails_closed(monkeypatch, bad):
    rows = ci_rows()
    if bad == "duplicate":
        rows.append(rows[0])
    elif bad == "producer":
        rows[0]["app"]["slug"] = "untrusted"
    elif bad == "wrong_head":
        rows[0]["head_sha"] = B
    elif bad == "missing":
        rows.pop()
    calls = []

    def query(*args):
        calls.append(args)
        if args[0] == "pr":
            return dict(
                number=1,
                state="OPEN",
                isDraft=False,
                headRefOid=A,
                baseRefOid=B,
                headRepository={"nameWithOwner": "owner/repo"},
                labels=[{"name": "approved-merge"}],
            )
        if "events?" in args[1]:
            return [
                [
                    dict(
                        id=5,
                        event="unlabeled",
                        label={"name": "approved-merge"},
                        actor={"login": "owner"},
                    )
                ],
                [
                    dict(
                        id=6,
                        event="labeled",
                        label={"name": "approved-merge"},
                        actor={"login": "owner"},
                    )
                ],
            ]
        for i, row in enumerate(rows):
            row["id"] = i + 1
        return [
            {"check_runs": rows[:3], "total_count": len(rows)},
            {"check_runs": rows[3:], "total_count": len(rows)},
        ]

    monkeypatch.setattr(wakeup, "query", query)
    if bad == "missing":
        assert wakeup.observe("owner/repo", 1)["outcome"] == "pending"
    else:
        with pytest.raises(ProtocolError):
            wakeup.observe("owner/repo", 1)
    assert all("--paginate" in call and "--slurp" in call for call in calls if call[0] == "api")


def test_explicit_human_gate_parking_preserves_default_invariant(merge_case, monkeypatch):
    control, evidence = merge_case
    monkeypatch.setattr(
        driver, "command_once", lambda *a, **k: pytest.fail("no model round needed")
    )
    result = driver.run_cycle(control, evidence, evidence, {}, park_human_gates=True)
    assert result["status"] == "awaiting_merge"
    assert result["rounds_used"] == 3
    assert json.loads((control / "driver-binding.json").read_text())["park_human_gates"] is True
    assert any(
        json.loads(p.read_text())["kind"] == "parked"
        for p in (control / "driver-events").glob("*.json")
    )


def test_default_driver_does_not_park(merge_case, monkeypatch):
    control, evidence = merge_case
    monkeypatch.setattr(driver, "command_once", lambda *a, **k: dict(action="stop"))
    assert driver.run_cycle(control, evidence, evidence, {})["status"] == "blocked"


def test_parking_does_not_hide_runnable_or_unknown_live_work():
    tasks = {
        "merge": dict(status="awaiting_merge", needs=[]),
        "follow": dict(status="ready", needs=["merge"]),
    }
    assert driver.human_gate_wait(tasks)
    tasks["independent"] = dict(status="ready", needs=[])
    assert not driver.human_gate_wait(tasks)
    tasks["independent"]["status"] = "running"
    assert not driver.human_gate_wait(tasks)
    tasks["independent"]["status"] = "blocked"
    tasks["follow"]["needs"].append("independent")
    assert not driver.human_gate_wait(tasks)


@pytest.fixture
def queue_case(tmp_path, monkeypatch):
    monkeypatch.setattr(wakeup, "source_guard", lambda c: None)
    evidence, control = tmp_path / "evidence", tmp_path / "control"
    evidence.mkdir()
    with StateStore(control, evidence, create=True) as store:
        store.add("work")
    jobs = tmp_path / "jobs.json"
    jobs.write_text("{}")
    entry = dict(
        id="new",
        control=str(control),
        evidence=str(evidence),
        checkout=str(evidence),
        jobs=str(jobs),
        jobs_sha256=hashlib.sha256(jobs.read_bytes()).hexdigest(),
        repository="owner/repo",
    )
    queue = tmp_path / "queue.json"
    queue.write_text(json.dumps(dict(version=1, entries=[entry])))
    config = dict(
        version=1,
        root=str(tmp_path / "timer"),
        queue=str(queue),
        runtime=str(Path(__file__).resolve().parents[2]),
        python=sys.executable,
        source_head=A,
        approvers=["owner"],
        codex_home=str(tmp_path / "auth"),
        executable_dirs=["/opt/homebrew/bin", "/usr/bin", "/bin"],
    )
    return config, queue, entry


def test_each_wake_reloads_new_tasks_and_deduplicates_busy_processes(queue_case, monkeypatch):
    config, queue, entry = queue_case
    seen = []
    monkeypatch.setattr(
        wakeup, "run_cycle", lambda *a, **k: seen.append(a[0]) or {"status": "done"}
    )
    assert wakeup.wake(config)["entries"] == {"new": "done"}
    root = Path(config["root"])
    with ProcessLock(root / "wakeup.lock"):
        assert wakeup.wake(config) == {"status": "busy"}
    with ProcessLock(Path(entry["control"]) / "driver.lock"):
        assert wakeup.wake(config)["entries"] == {"new": "busy"}
    assert seen == [Path(entry["control"])]
    queue.write_text(json.dumps(dict(version=1, entries=[])))
    with pytest.raises(ProtocolError, match="removal"):
        wakeup.wake(config)


def test_jobs_digest_and_generation_identity_cannot_drift(queue_case, monkeypatch):
    config, queue, entry = queue_case
    Path(entry["jobs"]).write_text('{"changed":true}')
    with pytest.raises(ProtocolError, match="digest"):
        wakeup.wake(config)


def test_launchd_has_one_300_second_entry_and_no_watchdog_or_shell(queue_case):
    config, queue, entry = queue_case
    value = plistlib.loads(wakeup.render_plist(config, queue))
    assert value["Label"] == wakeup.LABEL
    assert value["StartInterval"] == 300
    assert "KeepAlive" not in value
    assert value["ProgramArguments"] == [
        sys.executable,
        "-m",
        "scripts.pipeline_wakeup",
        "--config",
        str(queue),
    ]
    assert "sh" not in value["ProgramArguments"]
    assert value["WorkingDirectory"] == config["runtime"]
    assert value["EnvironmentVariables"]["CODEX_HOME"] == config["codex_home"]
    assert value["EnvironmentVariables"]["PATH"] == ":".join(config["executable_dirs"])


def test_source_guard_checks_actual_tool_lookup_in_configured_path(
    queue_case, monkeypatch, tmp_path
):
    config, _, _ = queue_case
    tools = tmp_path / "tools"
    tools.mkdir()
    config["executable_dirs"] = [str(tools)]
    for tool in ("gh", "git", "codex"):
        target = tools / tool
        target.write_text("#!/bin/sh\nexit 0\n")
        target.chmod(0o700)
    monkeypatch.setattr(wakeup, "run", lambda *a, **kw: A if "rev-parse" in a else "")
    SOURCE_GUARD(config)
    (tools / "codex").unlink()
    with pytest.raises(ProtocolError, match="missing executable: codex"):
        SOURCE_GUARD(config)


def test_interpreter_preserves_venv_symlink_without_changing_prefix(tmp_path):
    link = tmp_path / "python3"
    link.symlink_to(Path(sys.executable).resolve())
    assert wakeup.interpreter(str(link)) == link


def test_all_merge_scans_precede_potentially_long_cycle(queue_case, merge_case, monkeypatch):
    config, queue, entry = queue_case
    control, evidence = merge_case
    merge_entry = dict(
        entry, id="approval", control=str(control), evidence=str(evidence), checkout=str(evidence)
    )
    queue.write_text(json.dumps(dict(version=1, entries=[entry, merge_entry])))
    events = []
    monkeypatch.setattr(wakeup, "check_merge", lambda *a: events.append("scan") or "awaiting_merge")
    monkeypatch.setattr(
        wakeup, "run_cycle", lambda *a, **k: events.append("cycle") or {"status": "done"}
    )
    wakeup.wake(config)
    assert events == ["scan", "cycle", "cycle"]


def test_recovery_does_not_start_a_new_attempt(tmp_path, monkeypatch):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "result.log").write_text("actual saved evidence")
    control = tmp_path / "control"
    with StateStore(control, evidence, create=True) as store:
        store.add("worker")
        intent = store.begin("worker", "worker", "saved", A, B)
        assert intent is not None

        # Simulate the precise crash boundary: durable result, ledger still running.
        def crash(value):
            raise RuntimeError("crash before ledger commit")

        store._save = crash
        with pytest.raises(RuntimeError, match="crash"):
            store.finish(
                json.dumps(
                    dict(
                        task_id="worker",
                        attempt=1,
                        result="pass",
                        commit=A,
                        evidence=[
                            dict(
                                path="result.log",
                                sha256=hashlib.sha256(
                                    (evidence / "result.log").read_bytes()
                                ).hexdigest(),
                            )
                        ],
                        notes="unit",
                    )
                ),
                ExecutionReceipt("worker", 1, intent["id"], A, 0, "saved"),
            )
    recovered = []

    def dispatch(value, jobs, control, evidence, **kwargs):
        with StateStore(control, evidence) as store:
            task = store.state["tasks"]["worker"]
            assert task["attempt"] == 1 and value["revision"] == store.state["revision"]
            store.recover_result("worker")
            status = store.state["tasks"]["worker"]["status"]
        recovered.append(value)
        return {"status": status}

    monkeypatch.setattr(driver, "dispatch", dispatch)
    monkeypatch.setattr(driver, "command_once", lambda *a, **k: pytest.fail("fresh commander"))
    result = driver.run_cycle(control, evidence, evidence, {"worker": {"kind": "worker"}})
    assert len(recovered) == 1 and result["rounds_used"] == 1 and result["status"] == "done"


def test_parking_cannot_hide_unrelated_terminal_failure():
    for status in ("blocked", "budget_exhausted", "failed"):
        assert not driver.human_gate_wait(
            {
                "merge": dict(status="awaiting_merge", needs=[]),
                "other": dict(status=status, needs=[]),
            }
        )


def test_invalid_config_emits_structured_blocked(tmp_path, monkeypatch, capsys):
    config = tmp_path / "invalid.json"
    config.write_text("{}")
    monkeypatch.setattr(sys, "argv", ["pipeline_wakeup", "--config", str(config)])
    assert wakeup.main() == 2
    assert json.loads(capsys.readouterr().err)["status"] == "blocked"


def test_scan_to_cycle_lock_race_skips_only_busy_generation(queue_case, merge_case, monkeypatch):
    config, queue, entry = queue_case
    control, evidence = merge_case
    later = dict(
        entry, id="later", control=str(control), evidence=str(evidence), checkout=str(evidence)
    )
    queue.write_text(json.dumps(dict(version=1, entries=[entry, later])))
    monkeypatch.setattr(wakeup, "check_merge", lambda *a: "awaiting_merge")
    actual_run_cycle = wakeup.run_cycle
    competitor = ProcessLock(Path(entry["control"]) / "driver.lock")
    calls = []

    def race(control, evidence, checkout, jobs, **kwargs):
        calls.append(control)
        if control == Path(entry["control"]):
            # Both scans have completed; a different owner wins the admission gap.
            assert competitor.acquire()
            return actual_run_cycle(control, evidence, checkout, jobs, **kwargs)
        return {"status": "done"}

    monkeypatch.setattr(wakeup, "run_cycle", race)
    try:
        result = wakeup.wake(config)
        assert result["entries"] == {"new": "busy", "later": "done"}
        assert calls == [Path(entry["control"]), control]
        assert not (Path(entry["control"]) / "driver-binding.json").exists()
        with StateStore(Path(entry["control"]), Path(entry["evidence"])) as store:
            assert store.state["tasks"]["work"]["attempt"] == 0
    finally:
        competitor.close()


def test_cycle_safety_error_is_not_misclassified_as_busy(queue_case, monkeypatch):
    config, _, _ = queue_case

    def unsafe(*args, **kwargs):
        raise SafetyError("lock inode changed")

    monkeypatch.setattr(wakeup, "run_cycle", unsafe)
    with pytest.raises(SafetyError, match="lock inode changed"):
        wakeup.wake(config)
