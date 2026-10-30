import copy

import pytest
from scripts import pipeline_ci as ci
from scripts.pipeline_protocol import EXPECTED_CHECKS, ProtocolError, StateStore

A, B = "a" * 40, "b" * 40


def checks() -> list[dict]:
    return [
        dict(
            name=name,
            head_sha=A,
            status="completed",
            conclusion="success",
            app={"slug": "github-actions"},
        )
        for name in sorted(EXPECTED_CHECKS)
    ]


def test_incomplete_and_failed_checks_never_pass():
    rows = checks()
    assert ci.classify(rows, A) == "pass"
    assert ci.classify(rows[:-1], A) == "pending"
    rows[0]["status"] = "in_progress"
    assert ci.classify(rows, A) == "pending"
    rows[0]["status"] = "completed"
    for conclusion in ["failure", "skipped", "cancelled", "neutral", "timed_out", None]:
        rows[0]["conclusion"] = conclusion
        assert ci.classify(rows, A) == "fail"


@pytest.mark.parametrize("damage", ["head", "duplicate", "producer"])
def test_ambiguous_or_wrong_check_binding_denies(damage):
    rows = checks()
    if damage == "head":
        rows[0]["head_sha"] = B
    elif damage == "duplicate":
        rows.append(copy.deepcopy(rows[0]))
    else:
        rows[0]["app"]["slug"] = "other"
    with pytest.raises(ProtocolError):
        ci.classify(rows, A)


def test_timeout_then_resume_preserves_intent_and_one_attempt(tmp_path, monkeypatch):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    control = tmp_path / "control"
    with StateStore(control, evidence, create=True) as store:
        store.add("ci")
    target = ci.CITarget("test/sandbox", 7, "pipeline-test/ci", A, "main", B)
    observation = {"pr": {}, "check_runs": []}
    monkeypatch.setattr(ci.CIObserver, "observe", lambda self: observation)
    assert ci.wait_ci(target, "ci", control, evidence, timeout=0) == "timeout"
    with StateStore(control, evidence) as store:
        intent = store.state["tasks"]["ci"]["intent"]
    observation["check_runs"] = checks()
    assert ci.wait_ci(target, "ci", control, evidence, timeout=0) == "done"
    with StateStore(control, evidence) as store:
        assert store.state["rounds_used"] == 1
        assert store.state["tasks"]["ci"]["intent"] == intent


def test_ci_observer_denies_pr_base_drift(monkeypatch):
    target = ci.CITarget("test/sandbox", 7, "pipeline-test/ci", A, "main", B)
    monkeypatch.setattr(ci, "run", lambda *args: '{"number":7,"headRefName":"wrong"}')
    with pytest.raises(ProtocolError, match="drift"):
        ci.CIObserver(target).observe()


def test_stale_dispatch_cannot_start_ci(tmp_path):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    control = tmp_path / "control"
    with StateStore(control, evidence, create=True) as store:
        store.add("ci")
    target = ci.CITarget("test/sandbox", 7, "pipeline-test/ci", A, "main", B)
    with pytest.raises(ProtocolError, match="stale CI"):
        ci.wait_ci(target, "ci", control, evidence, expected_revision=0)


def test_crash_after_observation_write_recovers_without_new_attempt(tmp_path, monkeypatch):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    control = tmp_path / "control"
    with StateStore(control, evidence, create=True) as store:
        store.add("ci")
    target = ci.CITarget("test/sandbox", 7, "pipeline-test/ci", A, "main", B)
    monkeypatch.setattr(ci.CIObserver, "observe", lambda self: {"pr": {}, "check_runs": checks()})
    original = StateStore.finish

    def interrupted(*args):
        raise RuntimeError("after durable CI evidence, before completion")

    monkeypatch.setattr(StateStore, "finish", interrupted)
    with pytest.raises(RuntimeError, match="after durable"):
        ci.wait_ci(target, "ci", control, evidence, timeout=0)
    before = {p.name: p.read_bytes() for p in evidence.iterdir()}
    assert len(before) == 1
    monkeypatch.setattr(StateStore, "finish", original)
    assert ci.wait_ci(target, "ci", control, evidence, timeout=0) == "done"
    assert {p.name: p.read_bytes() for p in evidence.iterdir()} == before
    with StateStore(control, evidence) as store:
        assert store.state["rounds_used"] == 1
