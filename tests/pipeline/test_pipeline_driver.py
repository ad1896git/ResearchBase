import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
from scripts import pipeline_driver as driver
from scripts.pipeline_ci import CIObserver, CITarget
from scripts.pipeline_protocol import EXPECTED_CHECKS, ExecutionReceipt, StateStore

A, B = "a" * 40, "b" * 40


def checks(success=True):
    return [
        dict(
            name=n,
            head_sha=A,
            status="completed",
            conclusion="success" if success else "failure",
            app={"slug": "github-actions"},
        )
        for n in sorted(EXPECTED_CHECKS)
    ]


def target():
    return dict(
        repository="test/sandbox",
        pr=1,
        branch="pipeline-test/driver",
        head=A,
        base="main",
        base_commit=B,
    )


def complete_worker(control, evidence, name="worker", *, success=True):
    path = evidence / "artifact.txt"
    path.write_text("actual unit evidence")
    import hashlib

    with StateStore(control, evidence) as store:
        intent = store.begin(name, "worker", "unit", A, B)
        assert intent is not None
        store.finish(
            json.dumps(
                dict(
                    task_id=name,
                    attempt=1,
                    result="pass" if success else "fail",
                    commit=A,
                    evidence=[
                        dict(path=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                    ],
                    notes="unit test",
                )
            ),
            ExecutionReceipt(name, 1, intent["id"], A, 0 if success else 1, "unit"),
        )


@pytest.fixture
def case(tmp_path, monkeypatch):
    evidence = tmp_path / "checkout"
    evidence.mkdir()
    control = tmp_path / "control"
    with StateStore(control, evidence, create=True) as store:
        store.add("ci")
        store.add("worker", needs=("ci",))
    jobs = {"ci": dict(kind="ci", config=target()), "worker": dict(kind="worker", config={})}
    monkeypatch.setattr(CITarget, "validate", lambda *args, **kwargs: None)
    return control, evidence, jobs


def propose(control, evidence, action="wait", name=""):
    with StateStore(control, evidence) as store:
        return dict(action=action, task_id=name, revision=store.state["revision"], reason="unit")


@pytest.mark.parametrize("action", ["unknown", "stop", "dispatch", "wait"])
def test_every_decision_has_a_durable_handling_branch(case, monkeypatch, action):
    control, evidence, jobs = case
    if action == "dispatch":
        jobs["ci"]["kind"] = "shell"
    if action == "wait":
        jobs = {}  # A wait without any legitimate CI must explicitly block.
    monkeypatch.setattr(
        driver,
        "command_once",
        lambda *a, **kw: propose(control, evidence, action, "ci" if action == "dispatch" else ""),
    )
    result = driver.run_cycle(control, evidence, evidence, jobs)
    assert result["status"] == "blocked"
    with StateStore(control, evidence) as store:
        assert all(t["status"] == "blocked" for t in store.state["tasks"].values())
    assert list((control / "notifications").glob("*.json"))


def test_commander_error_cannot_exit_with_ready_tasks(case, monkeypatch):
    control, evidence, jobs = case

    def invalid(*args, **kwargs):
        raise ValueError("malformed decision")

    monkeypatch.setattr(driver, "command_once", invalid)
    assert driver.run_cycle(control, evidence, evidence, jobs)["status"] == "blocked"
    with StateStore(control, evidence) as store:
        assert all(t["status"] in driver.TERMINAL for t in store.state["tasks"].values())


def test_real_process_never_exits_pending_or_retry_wait_and_auto_advances(case, tmp_path):
    """IPC invariant: the real process survives pending/retry_wait and starts its dependent task."""
    control, evidence, jobs = case
    config = tmp_path / "config.json"
    config.write_text(json.dumps(jobs))
    source = r"""
import json,sys
from pathlib import Path
from scripts import pipeline_driver as d
from scripts.pipeline_ci import CITarget, CIObserver
from scripts.pipeline_protocol import StateStore
from tests.pipeline.test_pipeline_driver import checks, complete_worker, propose
control,evidence,config=map(Path,sys.argv[1:])
jobs=json.loads(config.read_text()); calls=[]
def command(*args,**kwargs):
    calls.append('commander')
    with StateStore(control,evidence) as s: done=s.state['tasks']['ci']['status']=='done'
    return propose(control,evidence,'dispatch' if done else 'wait','worker' if done else '')
def observe(*args,**kwargs):
    return {'pr':{},'check_runs':checks() if (evidence/'release').exists() else []}
def execute(value,jobs,control,evidence,**kwargs):
    complete_worker(control,evidence)
    return {'decision':value,'status':'done'}
d.command_once=command;d.dispatch=execute;CITarget.validate=lambda *a,**kw:None
CIObserver.observe=observe
result=d.run_cycle(control,evidence,evidence,jobs,policy=d.Policy(
    round_budget=2,ci_timeout=.3,poll_interval=.05,heartbeat_interval=.05,retry_delay=1,
    max_ci_timeouts=4))
(control/'calls.json').write_text(json.dumps(calls))
print(json.dumps(result))
"""
    root = Path(__file__).resolve().parents[2]
    env = {**os.environ, "PYTHONPATH": str(root)}
    process = subprocess.Popen(
        [sys.executable, "-c", source, str(control), str(evidence), str(config)],
        cwd=root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        deadline = time.monotonic() + 8
        while True:
            assert process.poll() is None, process.communicate()
            state = json.loads((control / "state.json").read_text())
            if state["tasks"]["ci"]["status"] == "retry_wait":
                break
            assert time.monotonic() < deadline
            time.sleep(0.02)
        intent = state["tasks"]["ci"]["intent"]
        # The persisted notification and heartbeat prove a live, observable retry wait.
        deadline = time.monotonic() + 2
        while not list((control / "notifications").glob("*.json")):
            assert process.poll() is None and time.monotonic() < deadline
            time.sleep(0.02)
        beats = (control / "driver-heartbeats.jsonl").read_text().splitlines()
        assert len(beats) >= 3
        assert any(json.loads(b)["phase"] == "ci_wait" for b in beats)
        assert process.poll() is None
        (evidence / "release").touch()
        stdout, stderr = process.communicate(timeout=8)
        assert process.returncode == 0, stderr
        result = json.loads(stdout)
        assert result["status"] == "done" and result["rounds_used"] == 2
        assert result["tasks"]["ci"]["intent"] == intent
        assert result["tasks"]["ci"]["attempt"] == 1
        assert json.loads((control / "calls.json").read_text()) == ["commander", "commander"]
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)


def test_ci_failure_is_preserved_and_blocks_dependents(case, monkeypatch):
    control, evidence, jobs = case
    monkeypatch.setattr(driver, "command_once", lambda *a, **kw: propose(control, evidence))
    monkeypatch.setattr(
        CIObserver, "observe", lambda *a, **kw: dict(pr={}, check_runs=checks(False))
    )
    result = driver.run_cycle(control, evidence, evidence, jobs)
    assert result["status"] == "blocked"
    with StateStore(control, evidence) as store:
        assert store.state["tasks"]["ci"]["result"] is not None
        assert store.state["tasks"]["worker"]["attempt"] == 0


def test_timeout_limit_exits_only_after_blocking_and_notification(case, monkeypatch):
    control, evidence, jobs = case
    monkeypatch.setattr(driver, "command_once", lambda *a, **kw: propose(control, evidence))
    monkeypatch.setattr(CIObserver, "observe", lambda *a, **kw: dict(pr={}, check_runs=[]))
    result = driver.run_cycle(
        control,
        evidence,
        evidence,
        jobs,
        policy=driver.Policy(ci_timeout=0.1, poll_interval=0.05, max_ci_timeouts=1),
    )
    assert result["status"] == "blocked"
    assert result["tasks"]["ci"]["attempt"] == 1
    events = [json.loads(p.read_text()) for p in sorted((control / "driver-events").glob("*.json"))]
    assert any(e["kind"] == "retry_wait" for e in events)
    assert list((control / "notifications").glob("ci-*.json"))


def test_pause_reopen_and_resume_never_spends_another_attempt(case):
    control, evidence, _ = case
    with StateStore(control, evidence) as store:
        intent = store.begin("ci", "ci", "pr:1", A, B)
        store.pause_ci("ci", 100)
    with StateStore(control, evidence) as store:
        assert store.eligible(100) == []
        with pytest.raises(RuntimeError, match="not due"):
            store.resume_ci("ci", now=99)
        store.resume_ci("ci", now=100)
        store.recover_ci_pause("ci")
        assert store.state["tasks"]["ci"]["intent"] == intent
        assert store.state["rounds_used"] == 1
        assert store.state["tasks"]["ci"]["status"] == "running"


def test_timeout_receipt_state_crash_is_recovered_before_polling(case, monkeypatch):
    control, evidence, _ = case
    with StateStore(control, evidence) as store:
        store.begin("ci", "ci", "pr:1", A, B)
        monkeypatch.setattr(
            store, "_save", lambda *args: (_ for _ in ()).throw(RuntimeError("crash"))
        )
        with pytest.raises(RuntimeError, match="crash"):
            store.pause_ci("ci", 100)
    with StateStore(control, evidence) as store:
        store.recover_ci_pause("ci")
        assert store.state["tasks"]["ci"]["status"] == "retry_wait"
        assert store.state["rounds_used"] == 1


def test_timeout_receipt_tampering_denies_resume(case):
    control, evidence, _ = case
    with StateStore(control, evidence) as store:
        store.begin("ci", "ci", "pr:1", A, B)
        store.pause_ci("ci", 100)
    path = next(control.glob("ci-retry-*.json"))
    value = json.loads(path.read_text())
    value["intent"]["head"] = B
    path.write_text(json.dumps(value))
    with pytest.raises(RuntimeError, match="drift"):
        with StateStore(control, evidence):
            pytest.fail("corrupt timeout accepted")


def test_budget_exhaustion_never_leaves_ready_work(case, monkeypatch):
    control, evidence, jobs = case
    monkeypatch.setattr(driver, "command_once", lambda *a, **kw: propose(control, evidence))
    monkeypatch.setattr(CIObserver, "observe", lambda *a, **kw: dict(pr={}, check_runs=checks()))
    result = driver.run_cycle(
        control, evidence, evidence, jobs, policy=driver.Policy(round_budget=1)
    )
    assert result["status"] == "budget_exhausted"
    assert result["tasks"]["ci"]["status"] == "done"
    assert result["tasks"]["worker"]["status"] == "budget_exhausted"


def test_worker_failure_receipt_remains_readable_after_blocking(case, monkeypatch):
    control, evidence, jobs = case
    with StateStore(control, evidence) as store:
        store.state["tasks"]["worker"]["needs"] = []
        store._save(store._copy())
    monkeypatch.setattr(
        driver, "command_once", lambda *a, **kw: propose(control, evidence, "dispatch", "worker")
    )

    def failed(value, jobs, control, evidence, **kwargs):
        complete_worker(control, evidence, success=False)
        return dict(decision=value, status="failed")

    monkeypatch.setattr(driver, "dispatch", failed)
    result = driver.run_cycle(control, evidence, evidence, jobs)
    assert result["status"] == "blocked"
    with StateStore(control, evidence) as store:
        task = store.state["tasks"]["worker"]
        assert task["status"] == "blocked" and task["result"] is not None
        saved = json.loads((control / task["result"]).read_text())
        assert saved["receipt"]["exit_code"] == 1


def test_restart_policy_drift_blocks_instead_of_exiting_with_ready_work(case):
    control, evidence, jobs = case
    (control / "driver-binding.json").write_text("{}")
    result = driver.run_cycle(control, evidence, evidence, jobs)
    assert result["status"] == "blocked"
    assert all(t["status"] == "blocked" for t in result["tasks"].values())


def test_missing_timeout_receipt_never_restores_an_unproven_retry(case):
    control, evidence, _ = case
    with StateStore(control, evidence) as store:
        store.begin("ci", "ci", "pr:1", A, B)
        store.pause_ci("ci", 100)
    next(control.glob("ci-retry-*.json")).unlink()
    with pytest.raises(RuntimeError, match="missing CI timeout receipt"):
        with StateStore(control, evidence):
            pytest.fail("unproven retry accepted")


def test_sigterm_persists_blocked_before_process_exit(case):
    control, evidence, _ = case
    root = Path(__file__).resolve().parents[2]
    source = r"""
import json,sys
from pathlib import Path
from scripts import pipeline_driver as d
from scripts.pipeline_ci import CITarget,CIObserver
from tests.pipeline.test_pipeline_driver import target,propose
control,evidence=map(Path,sys.argv[1:])
d.command_once=lambda *a,**kw:propose(control,evidence)
CITarget.validate=lambda *a,**kw:None
CIObserver.observe=lambda *a,**kw:{'pr':{},'check_runs':[]}
print(json.dumps(d.run_cycle(control,evidence,evidence,{'ci':{'kind':'ci','config':target()}},
    policy=d.Policy(heartbeat_interval=.05))))
"""
    process = subprocess.Popen(
        [sys.executable, "-c", source, str(control), str(evidence)],
        cwd=root,
        env={**os.environ, "PYTHONPATH": str(root)},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        deadline = time.monotonic() + 8
        while True:
            assert process.poll() is None, process.communicate()
            state = json.loads((control / "state.json").read_text())
            if state["tasks"]["ci"]["status"] == "running":
                break
            assert time.monotonic() < deadline
            time.sleep(0.02)
        process.terminate()
        stdout, stderr = process.communicate(timeout=5)
        assert process.returncode == 0, stderr
        result = json.loads(stdout)
        assert result["status"] == "blocked"
        with StateStore(control, evidence) as store:
            assert all(t["status"] in driver.TERMINAL for t in store.state["tasks"].values())
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
