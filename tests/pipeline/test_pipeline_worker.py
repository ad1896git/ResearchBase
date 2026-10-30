import hashlib
import json
from pathlib import Path

import pytest
from scripts import pipeline_worker as worker
from scripts.pipeline_protocol import ProtocolError, StateStore

A, B = "a" * 40, "b" * 40


@pytest.fixture
def setup(tmp_path, monkeypatch):
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    control = tmp_path / "control"
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("Create a bounded evidence file only.")
    job = worker.WorkerJob("work", "historical", str(checkout), str(prompt), A, B)
    monkeypatch.setattr(
        worker,
        "run",
        lambda *args, **kw: ("https://github.com/test/sandbox.git" if args[1] == "remote" else A),
    )
    with StateStore(control, checkout, create=True) as store:
        store.add("work")
    launches = []

    def session(cwd, output, instruction, schema, **kwargs):
        launches.append(output)
        assert kwargs["writable"]
        output.mkdir()
        (checkout / "proof.txt").write_text("host-observable evidence")
        answer = dict(
            task_id="work",
            attempt=1,
            result="pass",
            commit=A,
            evidence=[
                dict(
                    path="proof.txt",
                    sha256=hashlib.sha256((checkout / "proof.txt").read_bytes()).hexdigest(),
                )
            ],
            notes="test",
        )
        (output / "answer.json").write_text(json.dumps(answer))
        return dict(exit_code=0, timed_out=False, descendants_stopped=True)

    monkeypatch.setattr(worker, "run_session", session)
    return job, control, checkout, launches, session


def test_worker_receipt_restarts_without_second_launch(setup):
    job, control, checkout, launches, _ = setup
    assert worker.worker_once(job, control, checkout) == "done"
    assert worker.worker_once(job, control, checkout) == "done"
    assert len(launches) == 1
    with StateStore(control, checkout) as store:
        assert store.state["rounds_used"] == 1


def test_host_failure_cannot_be_overridden_by_model_pass(setup, monkeypatch):
    job, control, checkout, _, session = setup

    def failed(*args, **kwargs):
        receipt = session(*args, **kwargs)
        receipt["exit_code"] = 7
        return receipt

    monkeypatch.setattr(worker, "run_session", failed)
    assert worker.worker_once(job, control, checkout) == "failed"


def test_unknown_live_worker_never_relaunches(setup, monkeypatch):
    job, control, checkout, launches, _ = setup

    def interrupted(*args, **kwargs):
        raise RuntimeError("driver interrupted with unknown child state")

    monkeypatch.setattr(worker, "run_session", interrupted)
    with pytest.raises(RuntimeError, match="interrupted"):
        worker.worker_once(job, control, checkout)
    with pytest.raises(ProtocolError, match="unknown live worker"):
        worker.worker_once(job, control, checkout)
    assert not launches
    with StateStore(control, checkout) as store:
        assert store.state["rounds_used"] == 1
        assert store.state["tasks"]["work"]["status"] == "running"


def test_durable_host_result_recovers_without_reexecution(setup, monkeypatch):
    job, control, checkout, launches, _ = setup
    original = StateStore.finish

    def interrupted(*args):
        raise RuntimeError("after host receipt")

    monkeypatch.setattr(StateStore, "finish", interrupted)
    with pytest.raises(RuntimeError, match="after host receipt"):
        worker.worker_once(job, control, checkout)
    monkeypatch.setattr(StateStore, "finish", original)
    assert worker.worker_once(job, control, checkout) == "done"
    assert len(launches) == 1


def test_invalid_or_missing_report_does_not_pass(setup, monkeypatch):
    job, control, checkout, _, session = setup

    def malformed(*args, **kwargs):
        terminal = session(*args, **kwargs)
        (args[1] / "answer.json").write_text('{"result":"pass"}')
        return terminal

    monkeypatch.setattr(worker, "run_session", malformed)
    with pytest.raises(ProtocolError):
        worker.worker_once(job, control, checkout)
    with StateStore(control, checkout) as store:
        assert store.state["tasks"]["work"]["status"] == "running"


def test_worker_cannot_share_control_write_root(setup):
    job, _, checkout, launches, _ = setup
    with pytest.raises(ProtocolError, match="overlap"):
        worker.worker_once(job, checkout / "control", checkout)
    assert not launches


def test_changed_job_cannot_restart(setup):
    job, control, checkout, launches, _ = setup
    worker.worker_once(job, control, checkout)
    Path(job.prompt_file).write_text("different work")
    with pytest.raises(ProtocolError, match="job changed"):
        worker.worker_once(job, control, checkout)
    assert len(launches) == 1


def test_timeout_cannot_pass_even_if_child_exits_zero(setup, monkeypatch):
    job, control, checkout, _, session = setup

    def timed_out(*args, **kwargs):
        receipt = session(*args, **kwargs)
        receipt["timed_out"] = True
        return receipt

    monkeypatch.setattr(worker, "run_session", timed_out)
    assert worker.worker_once(job, control, checkout) == "failed"


def test_stale_commander_cannot_start_worker(setup):
    job, control, checkout, launches, _ = setup
    with pytest.raises(ProtocolError, match="stale worker"):
        worker.worker_once(job, control, checkout, expected_revision=0)
    assert not launches


@pytest.mark.parametrize("kind", ["timeout", "quota", "session_exit"])
def test_transient_attempts_are_bounded_and_preserve_evidence(setup, monkeypatch, kind):
    job, control, checkout, launches, _ = setup
    clock = [1000]
    monkeypatch.setattr(worker.time, "time", lambda: clock[0])

    def absent(cwd, output, *args, **kwargs):
        launches.append(output)
        output.mkdir()
        if kind == "quota":
            (output / "stderr.log").write_text("quota exceeded")
        return dict(
            exit_code=1 if kind == "quota" else -15,
            timed_out=kind == "timeout",
            descendants_stopped=True,
        )

    monkeypatch.setattr(worker, "run_session", absent)
    assert worker.worker_once(job, control, checkout) == "retry_wait"
    first = {p: p.read_bytes() for p in (control / "executions/work-1").iterdir()}
    first_receipt = (control / "results/work-1.json").read_bytes()
    with StateStore(control, checkout) as store:
        task = store.state["tasks"]["work"]
        assert task["attempt"] == 1
        assert task["reason"] == ("quota" if kind == "quota" else "worker_transient")
        assert task["retry_at"] == 1000 + (900 if kind == "quota" else 60)
    with pytest.raises(ProtocolError, match="not due"):
        worker.worker_once(job, control, checkout)
    clock[0] = 2000
    assert worker.worker_once(job, control, checkout) == "blocked"
    with StateStore(control, checkout) as store:
        assert store.state["tasks"]["work"]["attempt"] == 2
        assert store.state["rounds_used"] == 2
    assert len(launches) == 2 and launches[0] != launches[1]
    assert all(p.read_bytes() == content for p, content in first.items())
    assert (control / "results/work-1.json").read_bytes() == first_receipt
    with pytest.raises(ProtocolError):
        worker.worker_once(job, control, checkout)
    assert len(launches) == 2


@pytest.mark.parametrize(
    "diagnostic", ["operation not permitted", "invalid schema", "permission denied"]
)
def test_systemic_failure_is_never_retried(setup, monkeypatch, diagnostic):
    job, control, checkout, launches, _ = setup

    def absent(cwd, output, *args, **kwargs):
        launches.append(output)
        output.mkdir()
        (output / "stderr.log").write_text(diagnostic)
        return dict(exit_code=-15, timed_out=True, descendants_stopped=True)

    monkeypatch.setattr(worker, "run_session", absent)
    for _ in range(2):
        with pytest.raises(ProtocolError, match="systemic/unclassified"):
            worker.worker_once(job, control, checkout)
    assert len(launches) == 1


def test_retry_receipt_crash_recovers_original_deadline_without_relaunch(setup, monkeypatch):
    job, control, checkout, launches, _ = setup

    def absent(cwd, output, *args, **kwargs):
        launches.append(output)
        output.mkdir()
        return dict(exit_code=-15, timed_out=True, descendants_stopped=True)

    monkeypatch.setattr(worker, "run_session", absent)
    original = StateStore._save

    def crash(self, value):
        if value["tasks"]["work"]["status"] == "retry_wait":
            raise RuntimeError("receipt persisted")
        return original(self, value)

    monkeypatch.setattr(StateStore, "_save", crash)
    with pytest.raises(RuntimeError, match="receipt persisted"):
        worker.worker_once(job, control, checkout)
    receipt = (control / "results/work-1.json").read_bytes()
    monkeypatch.setattr(StateStore, "_save", original)
    assert worker.worker_once(job, control, checkout) == "retry_wait"
    assert (control / "results/work-1.json").read_bytes() == receipt
    assert len(launches) == 1


def test_owned_driver_automatically_retries_then_advances_without_input(setup, monkeypatch):
    from dataclasses import asdict

    from scripts import pipeline_driver as driver

    job, control, checkout, launches, _ = setup
    clock = [1000]
    monkeypatch.setattr(worker.time, "time", lambda: clock[0])

    def session(cwd, output, instruction, schema, **kwargs):
        launches.append(output)
        output.mkdir()
        if len(launches) == 1:
            return dict(exit_code=-15, timed_out=True, descendants_stopped=True)
        proof = checkout / "second.txt"
        proof.write_text("second attempt fresh session")
        answer = dict(
            task_id="work",
            attempt=2,
            result="pass",
            commit=A,
            evidence=[dict(path=proof.name, sha256=hashlib.sha256(proof.read_bytes()).hexdigest())],
            notes="pass",
        )
        (output / "answer.json").write_text(json.dumps(answer))
        return dict(exit_code=0, timed_out=False, descendants_stopped=True)

    monkeypatch.setattr(worker, "run_session", session)
    waits = []

    def idle(self, timestamp, heartbeat):
        assert len(launches) == 1
        assert self.snapshot()["rounds_used"] == 1
        assert heartbeat.phase["phase"] == "retry_wait"
        heartbeat.pulse()
        waits.append(timestamp)
        clock[0] = timestamp

    monkeypatch.setattr(driver.Driver, "idle_until", idle)
    monkeypatch.setattr(
        driver,
        "command_once",
        lambda *a, **k: dict(
            action="dispatch",
            task_id="work",
            revision=json.loads((control / "state.json").read_text())["revision"],
        ),
    )
    result = driver.run_cycle(
        control, checkout, checkout, {"work": dict(kind="worker", config=asdict(job))}
    )
    assert result["status"] == "done" and result["rounds_used"] == 2
    assert result["tasks"]["work"]["attempt"] == 2
    assert len(waits) == 1 and len(launches) == 2
    assert (control / "executions/work-1/host.json").is_file()
    assert (control / "executions/work-2/answer.json").is_file()


@pytest.mark.parametrize(
    "diagnostic",
    [
        "error: unexpected argument '--bad' found",
        "Error: failed to parse configuration: invalid type: string, expected a sequence",
        "unknown unexplained failure",
    ],
)
def test_unknown_positive_exit_and_configuration_errors_block_without_retry(
    setup, monkeypatch, diagnostic
):
    job, control, checkout, launches, _ = setup

    def absent(cwd, output, *args, **kwargs):
        launches.append(output)
        output.mkdir()
        (output / "stderr.log").write_text(diagnostic)
        return dict(exit_code=2, timed_out=False, descendants_stopped=True)

    monkeypatch.setattr(worker, "run_session", absent)
    for _ in range(2):
        with pytest.raises(ProtocolError, match="systemic/unclassified"):
            worker.worker_once(job, control, checkout)
    assert len(launches) == 1
