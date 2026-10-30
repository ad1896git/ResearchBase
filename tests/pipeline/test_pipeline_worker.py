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
